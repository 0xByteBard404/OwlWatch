"""舆情监控调度器"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.keyword import Keyword
from ..models.article import Article
from ..collectors.bocha import BochaCollector
from ..collectors.tavily import TavilyCollector
from ..collectors.anspire import AnspireCollector
from ..collectors.base import CollectRequest
from ..config import settings
from ..analyzers.sentiment import SentimentAnalyzer
from ..services.alert_service import AlertService

logger = logging.getLogger(__name__)

# 初始化调度器
scheduler = AsyncIOScheduler()

# 采集器缓存（延迟初始化）
_collectors = {}


def get_bocha_collector():
    """获取博查采集器实例"""
    if "bocha" not in _collectors:
        if settings.bocha_api_key:
            try:
                _collectors["bocha"] = BochaCollector(settings.bocha_api_key)
                logger.info("Bocha collector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Bocha collector: {e}")
                _collectors["bocha"] = None
        else:
            _collectors["bocha"] = None
    return _collectors.get("bocha")


def get_tavily_collector():
    """获取 Tavily 采集器实例"""
    if "tavily" not in _collectors:
        if settings.tavily_api_key:
            try:
                _collectors["tavily"] = TavilyCollector(settings.tavily_api_key)
                logger.info("Tavily collector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Tavily collector: {e}")
                _collectors["tavily"] = None
        else:
            _collectors["tavily"] = None
    return _collectors.get("tavily")


def get_anspire_collector():
    """获取 Anspire 采集器实例"""
    if "anspire" not in _collectors:
        if settings.anspire_api_key:
            try:
                _collectors["anspire"] = AnspireCollector(settings.anspire_api_key)
                logger.info("Anspire collector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Anspire collector: {e}")
                _collectors["anspire"] = None
        else:
            _collectors["anspire"] = None
    return _collectors.get("anspire")


def get_sentiment_analyzer():
    """获取情感分析器实例（默认使用本地免费模式）"""
    if "sentiment" not in _collectors:
        try:
            # 使用本地免费分析，无需 API Key
            _collectors["sentiment"] = SentimentAnalyzer(use_local=True)
            logger.info("Sentiment analyzer initialized (local mode)")
        except Exception as e:
            logger.error(f"Failed to initialize Sentiment analyzer: {e}")
            _collectors["sentiment"] = None
    return _collectors.get("sentiment")


async def collect_keyword(keyword: Keyword, db: Session):
    """采集单个关键词的舆情数据"""
    platforms = keyword.platforms or ["bocha", "tavily"]
    results = []

    # 采集器映射
    collector_map = {
        "bocha": get_bocha_collector,
        "tavily": get_tavily_collector,
        "anspire": get_anspire_collector,
    }

    for platform in platforms:
        collector_func = collector_map.get(platform)
        if not collector_func:
            continue

        collector = collector_func()
        if not collector:
            logger.warning(f"Collector not available: {platform}")
            continue

        try:
            # 精确匹配：给关键词加双引号
            search_keyword = f'"{keyword.keyword}"'

            request = CollectRequest(
                keyword=search_keyword,
                max_results=20,
                time_range="oneDay"
            )
            items = await collector.collect(request)
            results.extend(items)
        except Exception as e:
            logger.error(f"采集失败 [{platform}]: {keyword.keyword} - {str(e)}")
            continue

    # 获取情感分析器
    sentiment_analyzer = get_sentiment_analyzer()

    # 保存结果到数据库
    saved_count = 0
    filtered_count = 0

    for item in results:
        # 严格过滤：标题或内容必须精确包含关键词
        title_match = keyword.keyword in (item.title or "")
        content_match = keyword.keyword in (item.content or "")

        if not title_match and not content_match:
            filtered_count += 1
            continue

        # 检查是否已存在
        existing = db.query(Article).filter(
            Article.keyword_id == keyword.id,
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

        # 创建文章记录
        article = Article(
            id=str(__import__("uuid").uuid4()),
            keyword_id=keyword.id,
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
        saved_count += 1

    db.commit()
    logger.info(f"[{datetime.now()}] 采集完成: {keyword.keyword} - 采集{len(results)}条, 过滤{filtered_count}条, 保存{saved_count}条")

    # 采集完成后触发预警检测
    if results:
        try:
            alert_service = AlertService(db)
            await alert_service.check_and_alert(keyword.id)
        except Exception as e:
            logger.error(f"预警检测失败: {keyword.keyword} - {str(e)}")


async def collect_all_keywords():
    """采集所有活跃关键词"""
    db = SessionLocal()
    try:
        keywords = db.query(Keyword).filter(Keyword.is_active == True).all()
        logger.info(f"[{datetime.now()}] 开始采集 {len(keywords)} 个关键词")

        # 根据优先级分组处理
        high_priority = [k for k in keywords if k.priority == "high"]
        medium_priority = [k for k in keywords if k.priority == "medium"]
        low_priority = [k for k in keywords if k.priority == "low"]

        # 并发采集高优先级关键词
        if high_priority:
            tasks = [collect_keyword(k, db) for k in high_priority]
            await asyncio.gather(*tasks, return_exceptions=True)

        # 采集中优先级
        if medium_priority:
            for keyword in medium_priority:
                await collect_keyword(keyword, db)

        # 采集低优先级
        if low_priority:
            for keyword in low_priority:
                await collect_keyword(keyword, db)

        logger.info(f"[{datetime.now()}] 全部采集完成")
    finally:
        db.close()


def start_scheduler():
    """启动调度器"""
    # 高优先级: 每 5 分钟
    scheduler.add_job(
        collect_high_priority,
        IntervalTrigger(minutes=5),
        id="collect_high_priority"
    )

    # 中优先级: 每 15 分钟
    scheduler.add_job(
        collect_medium_priority,
        IntervalTrigger(minutes=15),
        id="collect_medium_priority"
    )

    # 低优先级: 每 30 分钟
    scheduler.add_job(
        collect_low_priority,
        IntervalTrigger(minutes=30),
        id="collect_low_priority"
    )

    # 全量采集: 每小时
    scheduler.add_job(
        collect_all_keywords,
        IntervalTrigger(hours=1),
        id="collect_all"
    )

    scheduler.start()
    logger.info("舆情监控调度器已启动")


async def collect_high_priority():
    """采集高优先级关键词"""
    db = SessionLocal()
    try:
        keywords = db.query(Keyword).filter(
            Keyword.is_active == True,
            Keyword.priority == "high"
        ).all()

        tasks = [collect_keyword(k, db) for k in keywords]
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        db.close()


async def collect_medium_priority():
    """采集中优先级关键词"""
    db = SessionLocal()
    try:
        keywords = db.query(Keyword).filter(
            Keyword.is_active == True,
            Keyword.priority == "medium"
        ).all()

        for keyword in keywords:
            await collect_keyword(keyword, db)
    finally:
        db.close()


async def collect_low_priority():
    """采集低优先级关键词"""
    db = SessionLocal()
    try:
        keywords = db.query(Keyword).filter(
            Keyword.is_active == True,
            Keyword.priority == "low"
        ).all()

        for keyword in keywords:
            await collect_keyword(keyword, db)
    finally:
        db.close()
