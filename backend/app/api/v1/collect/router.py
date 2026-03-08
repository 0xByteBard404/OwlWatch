# -*- coding: utf-8 -*-
"""手动采集触发端点"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.dependencies import get_db
from app.database import SessionLocal
from app.models.keyword import Keyword
from app.models.article import Article
from app.models.article_keyword import ArticleKeyword
from app.models.negative_keyword import NegativeKeyword
from app.models.rss_feed import RSSFeed
from app.collectors.bocha import BochaCollector
from app.collectors.tavily import TavilyCollector
from app.collectors.anspire import AnspireCollector
from app.collectors.bing import BingCollector
from app.collectors.rss_collector import RSSCollector
from app.utils.timezone import now_cst
from app.collectors.baidu import BaiduCollector
from app.collectors.base import CollectRequest
from app.config import settings
from app.analyzers.sentiment import SentimentAnalyzer
from app.services.redis_service import get_task_store

logger = logging.getLogger(__name__)

router = APIRouter()


class CollectTriggerResponse(BaseModel):
    """采集触发响应"""
    task_id: str
    message: str
    keyword: str


class CollectStatusResponse(BaseModel):
    """采集状态响应"""
    task_id: str
    keyword: str
    status: str  # pending/running/completed/failed
    collected_count: int
    message: Optional[str] = None
    created_at: str
    finished_at: Optional[str] = None


# 延迟初始化采集器
_collectors = {}


def get_bocha_collector():
    """获取博查采集器实例"""
    if "bocha" not in _collectors and settings.bocha_api_key:
        _collectors["bocha"] = BochaCollector(settings.bocha_api_key)
    return _collectors.get("bocha")


def get_tavily_collector():
    """获取 Tavily 采集器实例"""
    if "tavily" not in _collectors and settings.tavily_api_key:
        _collectors["tavily"] = TavilyCollector(settings.tavily_api_key)
    return _collectors.get("tavily")


def get_anspire_collector():
    """获取 Anspire 采集器实例"""
    if "anspire" not in _collectors and settings.anspire_api_key:
        _collectors["anspire"] = AnspireCollector(settings.anspire_api_key)
    return _collectors.get("anspire")


def get_bing_collector():
    """获取 Bing 采集器实例（每次创建新实例避免状态污染）"""
    return BingCollector()


def get_baidu_collector():
    """获取百度采集器实例（每次创建新实例避免状态污染）"""
    return BaiduCollector()


def get_sentiment_analyzer():
    """获取情感分析器实例（默认使用本地免费模式）"""
    if "sentiment" not in _collectors:
        # 默认使用本地免费模式（snownlp）
        _collectors["sentiment"] = SentimentAnalyzer(use_local=True)
    return _collectors.get("sentiment")


async def run_collect_task(
    task_id: str,
    keyword_id: str,
    keyword_text: str,
    platforms: List[str],
    time_range: str,
    negative_mode: bool,
    rss_ids: List[str] = None
):
    """后台执行采集任务"""
    # Windows 上设置事件循环策略以支持 Playwright
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    db = SessionLocal()
    task_collectors = {}  # 本任务使用的采集器实例（用于清理）
    task_store = await get_task_store()

    try:
        await task_store.update(task_id, {"status": "running"})

        results = []
        seen_urls = set()  # 去重

        # ==================== 1. 从配置的 RSS 数据源获取文章 ====================
        if rss_ids:
            logger.info(f"[Task {task_id}] Fetching from {len(rss_ids)} RSS feeds")
            await task_store.update(task_id, {"message": "正在获取 RSS 订阅..."})

            rss_collector = RSSCollector()
            time_range_map = {
                "oneDay": 1,
                "threeDays": 3,
                "oneWeek": 7,
                "oneMonth": 30,
                "threeMonths": 90,
            }
            days = time_range_map.get(time_range, 1)
            cutoff_time = now_cst() - timedelta(days=days)

            for feed_id in rss_ids:
                try:
                    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
                    if not feed or not feed.is_active:
                        continue

                    # 获取 RSS 内容
                    feed_results, _, _, _ = await rss_collector.fetch_feed(
                        feed_url=feed.feed_url,
                        etag=None,  # 强制获取最新
                        last_modified=None,
                        last_entry_id=None,
                    )

                    # 过滤：标题或内容包含关键词，且在时间范围内
                    for item in feed_results:
                        # 时间过滤
                        if item.publish_time and item.publish_time < cutoff_time:
                            continue

                        # 关键词过滤
                        title_match = keyword_text in (item.title or "")
                        content_match = keyword_text in (item.content or "")

                        # 负面模式：额外匹配负面关键词
                        if negative_mode and not (title_match or content_match):
                            negative_keyword_records = db.query(NegativeKeyword).filter(
                                NegativeKeyword.is_active == True
                            ).all()
                            negative_keywords = [kw.keyword for kw in negative_keyword_records]
                            if not negative_keywords:
                                negative_keywords = ["违规", "违法", "投诉", "通报", "处罚", "曝光", "被查", "立案", "调查", "维权"]
                            for neg_word in negative_keywords:
                                if neg_word in (item.title or "") or neg_word in (item.content or ""):
                                    title_match = True
                                    break

                        if title_match or content_match:
                            if item.url not in seen_urls:
                                seen_urls.add(item.url)
                                item.source_type = "rss"
                                results.append(item)

                    logger.info(f"[Task {task_id}][RSS:{feed.name}] Got {len(feed_results)} items, matched {len([i for i in feed_results if keyword_text in (i.title or '') or keyword_text in (i.content or '')])}")

                except Exception as e:
                    logger.error(f"[Task {task_id}][RSS:{feed_id}] Error: {e}")

            logger.info(f"[Task {task_id}] RSS total matched: {len(results)}")

        # ==================== 2. API 搜索采集 ====================
        # 采集器映射
        collector_map = {
            "baidu": get_baidu_collector,
            "bing": get_bing_collector,
            "bocha": get_bocha_collector,
            "tavily": get_tavily_collector,
            "anspire": get_anspire_collector,
        }

        # 构建搜索关键词列表
        search_keywords = [keyword_text]  # 基础搜索

        if negative_mode:
            # 从数据库读取启用的负面关键词
            negative_keyword_records = db.query(NegativeKeyword).filter(
                NegativeKeyword.is_active == True
            ).all()
            negative_keywords = [kw.keyword for kw in negative_keyword_records]

            # 如果数据库没有配置，使用默认值
            if not negative_keywords:
                negative_keywords = ["违规", "违法", "投诉", "通报", "处罚", "曝光", "被查", "立案", "调查", "维权"]

            for neg_word in negative_keywords:
                search_keywords.append(f"{keyword_text} {neg_word}")
            # 也加一个组合搜索
            search_keywords.append(f"{keyword_text} 违规 违法 通报")

        logger.info(f"[Task {task_id}] Search keywords: {search_keywords}")
        logger.info(f"[Task {task_id}] Platforms: {platforms}, Negative mode: {negative_mode}")

        # 为本任务创建独立的采集器实例（避免并发冲突）
        task_collectors = {}  # platform -> collector instance

        for platform in platforms:
            collector_func = collector_map.get(platform)
            if not collector_func:
                continue

            collector = collector_func()
            if not collector:
                logger.warning(f"Collector not available: {platform}")
                continue

            # 保存采集器实例，用于后续清理
            task_collectors[platform] = collector

            # 多轮搜索（使用同一个采集器实例）
            for search_keyword in search_keywords:
                try:
                    request = CollectRequest(
                        keyword=search_keyword,
                        max_results=15,
                        time_range=time_range
                    )
                    items = await collector.collect(request)

                    # 去重
                    new_items = [item for item in items if item.url not in seen_urls]
                    for item in new_items:
                        seen_urls.add(item.url)

                    results.extend(new_items)
                    logger.info(f"[Task {task_id}][{platform}] Search '{search_keyword}': {len(new_items)} new items")

                    # 更新进度
                    await task_store.update(task_id, {"message": f"正在搜索: {search_keyword[:20]}..."})

                except Exception as e:
                    logger.error(f"[Task {task_id}] Collect error [{platform}] '{search_keyword}': {e}")
                    continue

        # 保存结果到数据库
        saved_count = 0
        filtered_count = 0
        deep_fetch_count = 0
        max_deep_fetch = 10  # 限制深度抓取数量
        sentiment_analyzer = get_sentiment_analyzer()

        # 使用本任务的采集器进行深度抓取
        baidu_collector = task_collectors.get("baidu")
        bing_collector = task_collectors.get("bing")

        logger.info(f"[Task {task_id}] Processing {len(results)} results...")

        for idx, item in enumerate(results):
            # 更新进度
            if idx % 5 == 0:
                await task_store.update(task_id, {"message": f"处理中: {idx+1}/{len(results)}"})

            # 严格过滤：标题或摘要必须精确包含关键词
            title_match = keyword_text in (item.title or "")
            snippet_match = keyword_text in (item.content or "")

            # 如果标题和摘要都不匹配，尝试获取页面实际内容（限制数量）
            if not title_match and not snippet_match and deep_fetch_count < max_deep_fetch:
                # 对于百度/Bing结果，尝试深度抓取页面内容
                collector = baidu_collector or bing_collector
                if collector and item.url:
                    # 跳过百度重定向URL
                    if 'baidu.com/link' in item.url:
                        logger.debug(f"Skip deep fetch for Baidu redirect URL: {item.url[:50]}")
                        filtered_count += 1
                        continue

                    try:
                        deep_fetch_count += 1
                        page_result = await collector.collect_page_content(item.url)
                        page_content = page_result.get('content', '')

                        # 检查内容有效性
                        if page_content and len(page_content.strip()) > 100:
                            if keyword_text in page_content:
                                # 更新内容为实际页面内容
                                item.content = page_content[:5000]  # 限制长度
                                snippet_match = True
                                # 如果从页面提取到发布时间，更新 item
                                if page_result.get('publish_time'):
                                    try:
                                        item.publish_time = datetime.fromisoformat(page_result['publish_time'])
                                        logger.debug(f"Extracted publish_time: {page_result['publish_time']} for {item.title[:30]}")
                                    except Exception:
                                        pass
                                logger.info(f"Deep match found in page: {item.title[:30]}")
                            else:
                                # 页面内容中没有关键词，过滤掉
                                filtered_count += 1
                                logger.debug(f"Filtered (deep fetch no match): {item.title[:30] if item.title else 'N/A'}")
                                continue
                        else:
                            # 内容太短或为空，过滤掉
                            filtered_count += 1
                            continue
                    except Exception as e:
                        logger.debug(f"Deep fetch error: {e}")
                        filtered_count += 1
                        continue

            if not title_match and not snippet_match:
                filtered_count += 1
                logger.debug(f"Filtered (no exact match): {item.title[:50] if item.title else 'N/A'}")
                continue

            # 检查是否已存在（使用 no_autoflush 避免自动刷新）
            with db.no_autoflush:
                existing = db.query(Article).filter(
                    Article.keyword_id == keyword_id,
                    Article.url == item.url
                ).first()

            if existing:
                continue

            # AI 情感分析
            sentiment_score = None
            sentiment_label = None
            if sentiment_analyzer and item.content and len(item.content.strip()) >= 10:
                try:
                    analysis = await sentiment_analyzer.analyze(item.content)
                    sentiment_score = analysis.get("score")
                    sentiment_label = analysis.get("label")
                    logger.debug(f"Sentiment analyzed for '{item.title[:30]}...': score={sentiment_score}, label={sentiment_label}")
                except Exception as e:
                    logger.error(f"Sentiment analyze error: {e}")
            elif not sentiment_analyzer:
                logger.debug("Sentiment analyzer not available (bailian_api_key not configured)")
            elif not item.content or len(item.content.strip()) < 10:
                logger.debug(f"Skip sentiment analysis: content too short for '{item.title[:30] if item.title else 'N/A'}...")

            # 确定匹配类型
            match_type = "both" if title_match and snippet_match else ("title_only" if title_match else "content_only")

            # 检查文章是否已存在（基于 URL）
            existing_article = db.query(Article).filter(Article.url == item.url).first()

            if existing_article:
                article = existing_article
                # 检查关联是否已存在
                existing_link = db.query(ArticleKeyword).filter(
                    ArticleKeyword.article_id == article.id,
                    ArticleKeyword.keyword_id == keyword_id
                ).first()
                if existing_link:
                    continue
            else:
                # 创建文章记录（不设置 keyword_id，文章是独立的）
                article = Article(
                    id=str(uuid.uuid4()),
                    title=item.title,
                    content=item.content,
                    url=item.url,
                    source=item.source,
                    source_api=item.source_type,
                    sentiment_score=sentiment_score,
                    sentiment_label=sentiment_label,
                    publish_time=item.publish_time,
                    extra=str(item.extra) if item.extra else None
                )
                db.add(article)
                db.flush()  # 获取 article.id

            # 创建文章-关键词关联
            article_keyword = ArticleKeyword(
                id=str(uuid.uuid4()),
                article_id=article.id,
                keyword_id=keyword_id,
                match_type=match_type,
                matched_at=now_cst()
            )
            db.add(article_keyword)
            saved_count += 1

            # 每10条提交一次，减少锁竞争
            if saved_count % 10 == 0:
                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Batch commit error: {e}")
                    db.rollback()

        # 最终提交
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Final commit error: {e}")
            db.rollback()

        logger.info(f"[Task {task_id}] Done: searched {len(search_keywords)} queries, collected {len(results)}, deep_fetch {deep_fetch_count}, filtered {filtered_count}, saved {saved_count}")

        # 触发预警检测
        try:
            from app.services.alert_service import AlertService
            alert_service = AlertService(db)
            await alert_service.check_and_alert(keyword_id)
        except Exception as e:
            logger.error(f"Alert check error: {e}")

        # 更新任务状态
        await task_store.update(task_id, {
            "status": "completed",
            "collected_count": saved_count,
            "finished_at": now_cst().isoformat(),
            "message": f"采集完成，新增 {saved_count} 条文章"
        })

    except Exception as e:
        logger.error(f"Collect task failed: {e}")
        await task_store.update(task_id, {
            "status": "failed",
            "message": str(e),
            "finished_at": now_cst().isoformat()
        })
    finally:
        db.close()
        # 关闭本任务创建的所有浏览器采集器
        for platform, collector in task_collectors.items():
            if platform in ["baidu", "bing"] and hasattr(collector, 'close'):
                try:
                    await collector.close()
                    logger.debug(f"[Task {task_id}] Closed {platform} collector")
                except Exception as e:
                    logger.debug(f"[Task {task_id}] Close {platform} collector error: {e}")


@router.post("/trigger", response_model=CollectTriggerResponse)
async def trigger_collect(
    background_tasks: BackgroundTasks,
    keyword_id: str = Query(..., description="关键词ID"),
    time_range: str = Query(default="oneDay", description="时间范围"),
    negative_mode: bool = Query(default=False, description="负面舆情模式"),
    db: Session = Depends(get_db)
):
    """触发异步采集任务"""
    # 查找关键词
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    # 从 data_sources 提取 rss_ids
    rss_ids = []
    if keyword.data_sources and isinstance(keyword.data_sources, dict):
        rss_ids = keyword.data_sources.get("rss_ids", [])

    # 创建任务（存储到 Redis）
    task_id = str(uuid.uuid4())
    task_store = await get_task_store()
    await task_store.create(task_id, {
        "task_id": task_id,
        "keyword_id": keyword_id,
        "keyword": keyword.keyword,
        "status": "pending",
        "collected_count": 0,
        "message": "任务已创建，等待执行",
        "created_at": now_cst().isoformat(),
        "finished_at": None,
    })

    # 添加后台任务
    background_tasks.add_task(
        run_collect_task,
        task_id,
        keyword_id,
        keyword.keyword,
        keyword.platforms or ["bocha", "tavily"],
        time_range,
        negative_mode,
        rss_ids  # 传递 RSS 数据源 IDs
    )

    return CollectTriggerResponse(
        task_id=task_id,
        message="采集任务已创建",
        keyword=keyword.keyword
    )


@router.get("/status/{task_id}", response_model=CollectStatusResponse)
async def get_collect_status(task_id: str):
    """查询采集任务状态"""
    task_store = await get_task_store()
    task = await task_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return CollectStatusResponse(
        task_id=task["task_id"],
        keyword=task["keyword"],
        status=task["status"],
        collected_count=task["collected_count"],
        message=task.get("message"),
        created_at=task["created_at"],
        finished_at=task.get("finished_at"),
    )


@router.get("/running")
async def get_running_tasks():
    """获取所有正在运行的任务"""
    task_store = await get_task_store()
    running = await task_store.get_all_running()
    return {"tasks": running}


@router.post("/trigger-all")
async def trigger_collect_all(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """触发所有活跃关键词的采集"""
    keywords = db.query(Keyword).filter(Keyword.is_active == True).all()
    task_store = await get_task_store()

    task_ids = []
    for keyword in keywords:
        # 从 data_sources 提取 rss_ids
        rss_ids = []
        if keyword.data_sources and isinstance(keyword.data_sources, dict):
            rss_ids = keyword.data_sources.get("rss_ids", [])

        task_id = str(uuid.uuid4())
        await task_store.create(task_id, {
            "task_id": task_id,
            "keyword_id": keyword.id,
            "keyword": keyword.keyword,
            "status": "pending",
            "collected_count": 0,
            "message": "任务已创建",
            "created_at": now_cst().isoformat(),
            "finished_at": None,
        })

        background_tasks.add_task(
            run_collect_task,
            task_id,
            keyword.id,
            keyword.keyword,
            keyword.platforms or ["bocha", "tavily"],
            "oneDay",
            False,
            rss_ids  # 传递 RSS 数据源 IDs
        )
        task_ids.append({"keyword": keyword.keyword, "task_id": task_id})

    return {
        "message": f"已创建 {len(keywords)} 个采集任务",
        "tasks": task_ids
    }
