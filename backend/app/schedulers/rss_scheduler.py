"""RSS 订阅调度器"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.rss_feed import RSSFeed
from ..models.article import Article
from ..models.keyword import Keyword
from ..collectors.rss_collector import RSSCollector
from ..analyzers.sentiment import SentimentAnalyzer
from ..services.alert_service import AlertService
from ..config import settings

logger = logging.getLogger(__name__)

# RSS 调度器
rss_scheduler = AsyncIOScheduler()

# 采集器和分析器实例（延迟初始化）
_rss_collector: Optional[RSSCollector] = None
_sentiment_analyzer: Optional[SentimentAnalyzer] = None


def get_rss_collector() -> RSSCollector:
    """获取 RSS 采集器实例"""
    global _rss_collector
    if _rss_collector is None:
        _rss_collector = RSSCollector()
    return _rss_collector


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """获取情感分析器实例（默认使用本地免费模式）"""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        try:
            # 默认使用本地免费分析，无需 API Key
            _sentiment_analyzer = SentimentAnalyzer(use_local=True)
            logger.info("Sentiment analyzer initialized (local mode)")
        except Exception as e:
            logger.error(f"Failed to initialize Sentiment analyzer: {e}")
    return _sentiment_analyzer


async def fetch_feed(feed: RSSFeed, db: Session) -> int:
    """
    获取单个 RSS Feed 的新内容并保存
    
    Returns:
        保存的文章数量
    """
    collector = get_rss_collector()
    saved_count = 0

    try:
        # 获取新内容
        results, new_etag, new_last_modified, new_last_entry_id = await collector.fetch_feed(
            feed_url=feed.feed_url,
            etag=feed.last_etag,
            last_modified=feed.last_modified,
            last_entry_id=feed.last_entry_id,
        )

        # 获取关联的关键词（用于过滤和情感分析）
        keyword = None
        if feed.keyword_id:
            keyword = db.query(Keyword).filter(Keyword.id == feed.keyword_id).first()

        # 获取情感分析器
        sentiment_analyzer = get_sentiment_analyzer()

        # 保存结果到数据库
        for item in results:
            # 如果关联了关键词，进行过滤
            if keyword:
                title_match = keyword.keyword in (item.title or "")
                content_match = keyword.keyword in (item.content or "")
                if not title_match and not content_match:
                    continue

            # 检查是否已存在（基于 URL）
            existing = db.query(Article).filter(
                Article.url == item.url
            ).first()

            if existing:
                continue

            # AI 情感分析
            sentiment_score = None
            sentiment_label = None
            if sentiment_analyzer and item.content:
                try:
                    analysis = await sentiment_analyzer.analyze(item.content)
                    sentiment_score = analysis.get("score")
                    sentiment_label = analysis.get("label")
                except Exception as e:
                    logger.error(f"情感分析失败: {str(e)}")

            # 填充关键词
            item.keyword = keyword.keyword if keyword else feed.name

            # 创建文章记录
            article = Article(
                id=str(__import__("uuid").uuid4()),
                keyword_id=feed.keyword_id,
                title=item.title,
                content=item.content,
                url=item.url,
                source=item.source,
                source_api="rss",
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                publish_time=item.publish_time,
                extra=str(item.extra) if item.extra else None
            )
            db.add(article)
            saved_count += 1

        # 更新 Feed 状态
        feed.last_fetched = datetime.utcnow()
        feed.fetch_error_count = 0
        feed.last_error = None
        if new_etag:
            feed.last_etag = new_etag
        if new_last_modified:
            feed.last_modified = new_last_modified
        if new_last_entry_id:
            feed.last_entry_id = new_last_entry_id
        feed.total_entries = (feed.total_entries or 0) + saved_count

        db.commit()
        logger.info(f"RSS fetch success: {feed.name}, saved={saved_count}")

        # 触发预警检测
        if saved_count > 0 and feed.keyword_id:
            try:
                alert_service = AlertService(db)
                await alert_service.check_and_alert(feed.keyword_id)
            except Exception as e:
                logger.error(f"预警检测失败: {feed.name} - {str(e)}")

    except Exception as e:
        logger.error(f"RSS fetch error: {feed.name} - {str(e)}")
        feed.fetch_error_count = (feed.fetch_error_count or 0) + 1
        feed.last_error = str(e)[:500]
        db.commit()

    return saved_count


async def fetch_all_feeds():
    """获取所有活跃的 RSS Feed"""
    db = SessionLocal()
    try:
        # 获取所有活跃的 Feed
        feeds = db.query(RSSFeed).filter(RSSFeed.is_active == True).all()
        logger.info(f"[{datetime.now()}] 开始获取 {len(feeds)} 个 RSS 订阅")

        # 根据 fetch_interval 过滤出需要获取的 Feed
        now = datetime.utcnow()
        feeds_to_fetch = []
        for feed in feeds:
            if feed.last_fetched is None:
                # 从未获取过
                feeds_to_fetch.append(feed)
            else:
                # 检查是否到达获取间隔
                elapsed = (now - feed.last_fetched).total_seconds()
                if elapsed >= (feed.fetch_interval or 300):
                    feeds_to_fetch.append(feed)

        logger.info(f"需要获取 {len(feeds_to_fetch)} 个订阅")

        # 并发获取（限制并发数）
        semaphore = asyncio.Semaphore(5)  # 最多同时 5 个请求

        async def fetch_with_limit(feed):
            async with semaphore:
                return await fetch_feed(feed, db)

        tasks = [fetch_with_limit(feed) for feed in feeds_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_saved = sum(r for r in results if isinstance(r, int))
        logger.info(f"[{datetime.now()}] RSS 获取完成，共保存 {total_saved} 条文章")

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
    logger.info("RSS 订阅调度器已启动")


def stop_rss_scheduler():
    """停止 RSS 调度器"""
    if rss_scheduler.running:
        rss_scheduler.shutdown()
        logger.info("RSS 订阅调度器已停止")
