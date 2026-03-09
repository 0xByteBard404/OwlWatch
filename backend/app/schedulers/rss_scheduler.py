# -*- coding: utf-8 -*-
"""RSS 订阅调度器（独立运行版）

核心理念：
1. RSS 订阅是独立的数据采集通道，不依赖监控主体
2. 只要添加了 RSS 订阅并启用，就会自动定时获取数据
3. 获取到的文章存入数据池，然后根据关联规则分发给匹配的监控主体
"""
import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional, List, Dict, Set

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from ..database import SessionLocal
from ..models.rss_feed import RSSFeed
from ..models.article import Article
from ..models.keyword import Keyword
from ..models.article_keyword import ArticleKeyword
from ..models.keyword_rss_association import KeywordRSSAssociation
from ..collectors.rss_collector import RSSCollector
from ..config import settings
from ..utils.timezone import now_cst

logger = logging.getLogger(__name__)

# RSS 调度器
rss_scheduler = AsyncIOScheduler()

# 采集器实例（延迟初始化）
_rss_collector: Optional[RSSCollector] = None


def get_rss_collector() -> RSSCollector:
    """获取 RSS 采集器实例"""
    global _rss_collector
    if _rss_collector is None:
        _rss_collector = RSSCollector()
    return _rss_collector


def _get_all_active_feeds(db: Session) -> List[RSSFeed]:
    """
    获取所有活跃的 RSS Feed（不依赖关联）

    Returns:
        活跃的 RSS Feed 列表
    """
    return db.query(RSSFeed).filter(
        RSSFeed.is_active == True
    ).all()


def _get_feed_associations(db: Session) -> Dict[str, List[KeywordRSSAssociation]]:
    """
    获取所有 RSS Feed 与监控主体的关联关系（预加载）

    Returns:
        {feed_id: [KeywordRSSAssociation]}
    """
    associations = db.query(KeywordRSSAssociation).options(
        joinedload(KeywordRSSAssociation.keyword)
    ).filter(
        KeywordRSSAssociation.is_active == True
    ).all()

    # 按 Feed 分组
    feed_associations = defaultdict(list)
    for assoc in associations:
        feed_associations[assoc.rss_feed_id].append(assoc)

    return dict(feed_associations)


def _filter_feeds_by_interval(feeds: List[RSSFeed]) -> List[RSSFeed]:
    """
    过滤到达获取间隔的 Feed

    Returns:
        需要获取的 Feed 列表
    """
    now = now_cst()
    result = []

    for feed in feeds:
        if feed.last_fetched is None:
            # 从未获取过
            result.append(feed)
        else:
            # 检查是否到达获取间隔
            elapsed = (now - feed.last_fetched).total_seconds()
            if elapsed >= (feed.fetch_interval or 300):
                result.append(feed)

    return result


async def _fetch_and_distribute(
    feed: RSSFeed,
    associations: List[KeywordRSSAssociation],
    db: Session
) -> List[str]:
    """
    获取单个 RSS Feed 并分发给匹配的监控主体

    核心改进：
    1. 不管有没有关联，都获取 RSS 数据
    2. 获取到的文章存入数据池（article 表）
    3. 根据关联规则分发给匹配的监控主体

    Args:
        feed: RSS Feed 对象
        associations: 该 Feed 的关联列表（可能为空）
        db: 数据库会话

    Returns:
        保存的文章 ID 列表
    """
    collector = get_rss_collector()
    saved_article_ids = []

    try:
        # 获取新内容（不管有没有关联都要获取）
        results, new_etag, new_last_modified, new_last_entry_id = await collector.fetch_feed(
            feed_url=feed.feed_url,
            etag=feed.last_etag,
            last_modified=feed.last_modified,
            last_entry_id=feed.last_entry_id,
        )

        logger.info(f"RSS {feed.name} 获取到 {len(results)} 条内容")

        for item in results:
            # 检查是否已存在（基于 URL）
            existing = db.query(Article).filter(
                Article.url == item.url
            ).first()

            if existing:
                # 文章已存在，检查是否需要添加新的关联
                if associations:
                    for assoc in associations:
                        if not assoc.keyword or not assoc.keyword.is_active:
                            continue

                        # 检查过滤规则
                        if assoc.should_match(item.title or "", item.content or ""):
                            existing_link = db.query(ArticleKeyword).filter(
                                ArticleKeyword.article_id == existing.id,
                                ArticleKeyword.keyword_id == assoc.keyword.id
                            ).first()

                            if not existing_link:
                                new_link = ArticleKeyword(
                                    id=str(uuid.uuid4()),
                                    article_id=existing.id,
                                    keyword_id=assoc.keyword.id,
                                    match_type="rss"
                                )
                                db.add(new_link)
                                assoc.match_count = (assoc.match_count or 0) + 1
                                assoc.last_matched_at = now_cst()

                logger.debug(f"跳过已存在的文章: {item.url}")
                continue

            # 收集匹配的监控主体（仅用于记录关联）
            matched_keyword_ids: Set[str] = set()

            if associations:
                for assoc in associations:
                    if not assoc.keyword or not assoc.keyword.is_active:
                        continue

                    # 使用关联的过滤规则进行匹配
                    if assoc.should_match(item.title or "", item.content or ""):
                        matched_keyword_ids.add(assoc.keyword.id)

            # 创建文章记录（不管有没有匹配都保存到数据池）
            article = Article(
                id=str(uuid.uuid4()),
                keyword_id=None,  # 不绑定到特定监控主体，存入数据池
                title=item.title,
                content=item.content,
                url=item.url,
                source=item.source,
                source_api="rss",
                sentiment_status="pending",
                publish_time=item.publish_time,
                extra=str(item.extra) if item.extra else None
            )
            db.add(article)
            db.flush()  # 获取 article.id

            # 为匹配的监控主体创建关联
            for keyword_id in matched_keyword_ids:
                link = ArticleKeyword(
                    id=str(uuid.uuid4()),
                    article_id=article.id,
                    keyword_id=keyword_id,
                    match_type="rss"
                )
                db.add(link)

                # 更新关联统计
                assoc = next((a for a in associations if a.keyword_id == keyword_id), None)
                if assoc:
                    assoc.match_count = (assoc.match_count or 0) + 1
                    assoc.last_matched_at = now_cst()

            saved_article_ids.append(article.id)

        # 提交事务，捕获唯一约束冲突
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.warning(f"RSS 提交时检测到重复URL，已回滚: {feed.name}")
            saved_article_ids = []

        # 更新 Feed 状态
        feed.last_fetched = now_cst()
        feed.fetch_error_count = 0
        feed.last_error = None
        if new_etag:
            feed.last_etag = new_etag
        if new_last_modified:
            feed.last_modified = new_last_modified
        if new_last_entry_id:
            feed.last_entry_id = new_last_entry_id
        feed.total_entries = (feed.total_entries or 0) + len(saved_article_ids)

        db.commit()
        logger.info(f"RSS fetch success: {feed.name}, saved={len(saved_article_ids)}, matched={sum(1 for a in associations if a.match_count)}")

    except Exception as e:
        logger.error(f"RSS fetch error: {feed.name} - {str(e)}", exc_info=True)
        feed.fetch_error_count = (feed.fetch_error_count or 0) + 1
        feed.last_error = str(e)[:500]
        db.commit()

    return saved_article_ids


async def fetch_all_feeds():
    """
    获取所有活跃的 RSS Feed

    核心逻辑：
    1. 获取所有启用的 RSS 订阅（不依赖监控主体关联）
    2. 独立获取数据并存入数据池
    3. 根据关联规则分发给匹配的监控主体
    """
    db = SessionLocal()
    try:
        # 1. 获取所有活跃的 RSS Feed（不依赖关联）
        all_feeds = _get_all_active_feeds(db)

        if not all_feeds:
            logger.debug("没有活跃的 RSS 订阅")
            return

        logger.info(f"[{datetime.now()}] 发现 {len(all_feeds)} 个活跃的 RSS 订阅")

        # 2. 获取所有关联关系（用于分发，可能为空）
        feed_associations = _get_feed_associations(db)

        # 3. 过滤到达获取间隔的 Feed
        feeds_to_fetch = _filter_feeds_by_interval(all_feeds)

        if not feeds_to_fetch:
            logger.debug("没有需要获取的 RSS 订阅（未到间隔）")
            return

        logger.info(f"需要获取 {len(feeds_to_fetch)} 个订阅")

        # 4. 并发获取（限制并发数）
        semaphore = asyncio.Semaphore(5)

        async def fetch_with_limit(feed):
            async with semaphore:
                associations = feed_associations.get(feed.id, [])
                return await _fetch_and_distribute(feed, associations, db)

        tasks = [fetch_with_limit(feed) for feed in feeds_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 5. 收集所有保存的文章 ID 并推送到情感分析队列
        all_article_ids = []
        for r in results:
            if isinstance(r, list):
                all_article_ids.extend(r)

        total_saved = len(all_article_ids)
        logger.info(f"[{datetime.now()}] RSS 获取完成，共保存 {total_saved} 条文章")

        # 推送到情感分析队列
        if all_article_ids:
            try:
                from ..services.redis_service import get_sentiment_queue
                queue = await get_sentiment_queue()
                await queue.push_batch(all_article_ids)
                logger.info(f"已推送 {len(all_article_ids)} 篇文章到情感分析队列")
            except Exception as e:
                logger.warning(f"推送情感分析队列失败: {e}，文章将在下次调度时处理")

    finally:
        db.close()


def start_rss_scheduler():
    """启动 RSS 调度器"""
    # 每 2 分钟检查一次需要获取的 Feed
    rss_scheduler.add_job(
        fetch_all_feeds,
        IntervalTrigger(minutes=2),
        id="fetch_rss_feeds",
        replace_existing=True,
    )

    rss_scheduler.start()
    logger.info("RSS 订阅调度器已启动（独立运行版）")


def stop_rss_scheduler():
    """停止 RSS 调度器"""
    if rss_scheduler.running:
        rss_scheduler.shutdown()
        logger.info("RSS 订阅调度器已停止")


# ============ 兼容旧接口 ============

async def fetch_feed(feed: RSSFeed, db: Session) -> List[str]:
    """
    获取单个 RSS Feed 的新内容并保存（兼容旧接口）

    注意：推荐使用 fetch_all_feeds() 进行批量获取

    Returns:
        保存的文章ID列表
    """
    feed_associations = _get_feed_associations(db)
    associations = feed_associations.get(feed.id, [])
    return await _fetch_and_distribute(feed, associations, db)
