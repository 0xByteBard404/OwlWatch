# -*- coding: utf-8 -*-
"""监控主体调度器

核心理念：
1. 根据 fetch_interval 定期检查每个监控主体
2. 到达间隔时间后，自动触发 API 搜索采集
3. 更新 last_fetched 时间戳
"""
import asyncio
import logging
from datetime import datetime
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.keyword import Keyword
from ..utils.timezone import now_cst

logger = logging.getLogger(__name__)

# 监控主体调度器
keyword_scheduler = AsyncIOScheduler()


def _get_keywords_to_fetch(db: Session) -> List[Keyword]:
    """
    获取需要采集的监控主体列表

    筛选条件：
    1. is_active = True
    2. 配置了数据源（RSS 或 API 平台）
    3. 距离上次采集时间 >= fetch_interval

    Returns:
        需要采集的监控主体列表
    """
    now = now_cst()

    # 获取所有活跃的监控主体
    active_keywords = db.query(Keyword).filter(
        Keyword.is_active == True
    ).all()

    logger.debug(f"[Keyword Scheduler] 发现 {len(active_keywords)} 个活跃的监控主体")

    result = []
    for keyword in active_keywords:
        # 检查是否配置了数据源（RSS 或 API 平台）
        has_platforms = keyword.platforms and len(keyword.platforms) > 0
        has_rss = (
            keyword.data_sources
            and isinstance(keyword.data_sources, dict)
            and keyword.data_sources.get("rss_ids")
            and len(keyword.data_sources.get("rss_ids", [])) > 0
        )

        if not has_platforms and not has_rss:
            # 没有配置任何数据源，跳过
            logger.debug(f"[Keyword Scheduler] 跳过 {keyword.keyword}: 未配置数据源")
            continue

        if keyword.last_fetched is None:
            # 从未采集过
            logger.debug(f"[Keyword Scheduler] {keyword.keyword}: 从未采集，加入队列")
            result.append(keyword)
        else:
            # 检查是否到达采集间隔
            elapsed = (now - keyword.last_fetched).total_seconds()
            interval = keyword.fetch_interval or 300
            if elapsed >= interval:
                logger.debug(f"[Keyword Scheduler] {keyword.keyword}: 已过间隔 ({int(elapsed)}s >= {interval}s)，加入队列")
                result.append(keyword)
            else:
                logger.debug(f"[Keyword Scheduler] {keyword.keyword}: 未到间隔 ({int(elapsed)}s < {interval}s)，跳过")

    return result


async def _fetch_keyword(keyword: Keyword, db: Session):
    """
    触发单个监控主体的数据采集

    Args:
        keyword: 监控主体对象
        db: 数据库会话
    """
    try:
        from app.api.v1.collect.router import run_collect_task
        from app.services.redis_service import get_task_store
        import uuid

        # 获取任务存储
        task_store = await get_task_store()

        # 使用原子锁防止并发创建任务
        if not await task_store.acquire_lock(keyword.id):
            logger.info(f"[Keyword Scheduler] 跳过 {keyword.keyword}: 无法获取锁，已有任务运行中")
            return

        try:
            # 创建任务 ID
            task_id = str(uuid.uuid4())

            # 从 data_sources 提取 rss_ids
            rss_ids = []
            if keyword.data_sources and isinstance(keyword.data_sources, dict):
                rss_ids = keyword.data_sources.get("rss_ids", [])

            logger.info(f"[Keyword Scheduler] 触发采集: {keyword.keyword}, platforms={keyword.platforms}, rss_count={len(rss_ids)}")

            # 在 Redis 中创建任务记录
            await task_store.create(task_id, {
                "task_id": task_id,
                "keyword_id": keyword.id,
                "keyword": keyword.keyword,
                "status": "pending",
                "collected_count": 0,
                "message": "调度器触发采集任务",
                "created_at": now_cst().isoformat(),
                "finished_at": None,
            })

            # 如果没有配置 API 平台，只获取 RSS 数据
            platforms_to_use = keyword.platforms if keyword.platforms and len(keyword.platforms) > 0 else []

            await run_collect_task(
                task_id=task_id,
                keyword_id=keyword.id,
                keyword_text=keyword.keyword,
                platforms=platforms_to_use,
                time_range="oneDay",  # 默认采集最近 24 小时
                negative_mode=False,
                rss_ids=rss_ids
            )

            # 更新 last_fetched
            keyword.last_fetched = now_cst()
            db.commit()

            logger.info(f"[Keyword Scheduler] 采集完成: {keyword.keyword}")

        finally:
            # 注意：锁会在 run_collect_task 完成后自动释放
            # 这里不需要再次释放，避免重复释放
            pass

    except Exception as e:
        logger.error(f"[Keyword Scheduler] 采集失败: {keyword.keyword} - {str(e)}", exc_info=True)


async def fetch_all_keywords():
    """
    检查并触发需要采集的监控主体

    核心逻辑：
    1. 获取所有活跃的监控主体
    2. 筛选出到达采集间隔的
    3. 逐个触发采集（限制并发数）
    """
    db = SessionLocal()
    try:
        logger.debug("[Keyword Scheduler] 开始检查监控主体...")

        # 1. 获取需要采集的监控主体
        keywords_to_fetch = _get_keywords_to_fetch(db)

        if not keywords_to_fetch:
            logger.debug("没有需要采集的监控主体")
            return

        logger.info(f"[{datetime.now()}] 发现 {len(keywords_to_fetch)} 个需要采集的监控主体")

        # 2. 限制并发数，逐个执行
        semaphore = asyncio.Semaphore(2)  # 最多同时 2 个采集任务

        async def fetch_with_limit(keyword):
            async with semaphore:
                # 每个任务使用独立的数据库会话
                task_db = SessionLocal()
                try:
                    # 重新查询以获取绑定到当前会话的对象
                    kw = task_db.query(Keyword).filter(Keyword.id == keyword.id).first()
                    if kw:
                        await _fetch_keyword(kw, task_db)
                finally:
                    task_db.close()

        tasks = [fetch_with_limit(kw) for kw in keywords_to_fetch]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"[{datetime.now()}] 监控主体调度完成")

    finally:
        db.close()


def start_keyword_scheduler():
    """启动监控主体调度器"""
    # 每 2 分钟检查一次需要采集的监控主体
    keyword_scheduler.add_job(
        fetch_all_keywords,
        IntervalTrigger(minutes=2),
        id="fetch_keywords",
        replace_existing=True,
    )

    keyword_scheduler.start()
    logger.info("=" * 50)
    logger.info("监控主体调度器已启动")
    logger.info("- 检查周期: 每 2 分钟")
    logger.info("- 触发条件: last_fetched 为空 或 >= fetch_interval")
    logger.info("=" * 50)


def stop_keyword_scheduler():
    """停止监控主体调度器"""
    if keyword_scheduler.running:
        keyword_scheduler.shutdown()
        logger.info("监控主体调度器已停止")
