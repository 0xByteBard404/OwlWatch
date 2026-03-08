# -*- coding: utf-8 -*-
"""情感分析 Worker - 异步批量处理文章情感"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.article import Article
from ..models.sentiment_keyword import SentimentKeyword
from ..analyzers.sentiment import SentimentAnalyzer
from ..services.alert_service import AlertService
from ..services.redis_service import get_sentiment_queue
from ..utils.timezone import now_cst

from ..config import settings

import logging

logger = logging.getLogger(__name__)

# Worker 调度器
sentiment_scheduler = AsyncIOScheduler()

# 分析器实例（延迟初始化)
_sentiment_analyzer: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """获取情感分析器实例"""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        try:
            _sentiment_analyzer = SentimentAnalyzer(use_local=True)
            logger.info("Sentiment analyzer initialized (local mode)")
        except Exception as e:
            logger.error(f"Failed to initialize Sentiment analyzer: {e}")
            raise
    return _sentiment_analyzer
async def process_sentiment_batch():
    """
    批量处理情感分析队列
    
    流程:
    1. 从 Redis 队列批量取出 article_id
    2. 查询文章内容
    3. 加载情感关键词（正面/负面）
    4. 批量进行情感分析
    5. 更新文章情感状态
    6. 检查是否需要触发预警
    """
    db = SessionLocal()
    try:
        # 获取队列
        try:
            queue = await get_sentiment_queue()
        except Exception as e:
            logger.warning(f"Redis 连接失败，跳过本次处理: {e}")
            return
        # 批量取出文章 ID
        article_ids = await queue.pop_batch(batch_size=20)
        if not article_ids:
            logger.debug("情感分析队列为空，跳过")
            return
        logger.info(f"开始处理 {len(article_ids)} 篇文章的情感分析")
        # 查询文章
        articles = db.query(Article).filter(
            Article.id.in_(article_ids),
            Article.sentiment_status == "pending"
        ).all()
        if not articles:
            logger.warning("未找到待分析的文章")
            return
        # 获取情感分析器
        analyzer = get_sentiment_analyzer()
        # 加载情感关键词
        positive_keywords = []
        negative_keywords = []
        try:
            positive_kws = db.query(SentimentKeyword).filter(
                SentimentKeyword.sentiment_type == 'positive',
                SentimentKeyword.is_active == True
            ).all()
            positive_keywords = [kw.keyword for kw in positive_kws]
            negative_kws = db.query(SentimentKeyword).filter(
                SentimentKeyword.sentiment_type == 'negative',
                SentimentKeyword.is_active == True
            ).all()
            negative_keywords = [kw.keyword for kw in negative_kws]
        except Exception as e:
            logger.warning(f"加载情感关键词失败: {e}")
        # 批量分析
        processed_count = 0
        for article in articles:
            try:
                # 更新状态为处理中
                article.sentiment_status = "processing"
                db.commit()
                # 进行情感分析
                if article.content and len(article.content.strip()) >= 10:
                    analysis = await analyzer.analyze(
                        article.content,
                        positive_keywords=positive_keywords,
                        negative_keywords=negative_keywords
                    )
                    article.sentiment_score = analysis.get("score")
                    article.sentiment_label = analysis.get("label")
                else:
                    article.sentiment_score = 0
                    article.sentiment_label = "neutral"
                article.sentiment_status = "done"
                article.sentiment_analyzed_at = now_cst()
                db.commit()
                processed_count += 1
                # 检查是否需要触发预警
                if article.sentiment_label == "negative" and article.keyword_id:
                    try:
                        alert_service = AlertService(db)
                        await alert_service.check_and_alert(article.keyword_id)
                    except Exception as e:
                        logger.error(f"预警检测失败: {article.id} - {e}")
                logger.debug(f"文章情感分析完成: {article.id} -> {article.sentiment_label}")
            except Exception as e:
                logger.error(f"文章情感分析失败: {article.id} - {e}")
                article.sentiment_status = "failed"
                db.commit()
        logger.info(f"情感分析批次完成: 处理 {processed_count}/{len(articles)} 篇")
    except Exception as e:
        logger.error(f"情感分析批次处理异常: {e}")
    finally:
        db.close()
async def process_pending_articles():
    """
    处理数据库中 pending 状态的文章（兜底机制）
    
    用于处理 Redis 队列可能遗漏的文章
    """
    db = SessionLocal()
    try:
        # 查找 pending 状态的文章（限制 50 篇）
        pending_articles = db.query(Article).filter(
            Article.sentiment_status == "pending"
        ).limit(50).all()
        if not pending_articles:
            return
        logger.info(f"发现 {len(pending_articles)} 篇待处理文章")
        # 获取队列
        try:
            queue = await get_sentiment_queue()
            article_ids = [a.id for a in pending_articles]
            await queue.push_batch(article_ids)
            logger.info(f"已将 {len(article_ids)} 篇文章重新推送到队列")
        except Exception as e:
            logger.warning(f"重新推送队列失败， 直接处理: {e}")
            # 如果队列不可用， 直接处理
            await process_sentiment_batch()
    finally:
        db.close()
async def _log_queue_size():
    """异步获取并记录队列大小"""
    try:
        queue = await get_sentiment_queue()
        size = await queue.size()
        logger.info(f"情感分析 Worker 已启动, 当前队列大小: {size}")
    except Exception as e:
        logger.info(f"情感分析 Worker 已启动 (Redis 未连接: {e})")

def start_sentiment_worker():
    """启动情感分析 Worker"""
    # 每 30 秒处理一次队列
    sentiment_scheduler.add_job(
        process_sentiment_batch,
        IntervalTrigger(seconds=30),
        id="process_sentiment_batch",
        replace_existing=True,
    )
    # 每 5 分钟检查一次 pending 文章（兜底）
    sentiment_scheduler.add_job(
        process_pending_articles,
        IntervalTrigger(minutes=5),
        id="process_pending_articles",
        replace_existing=True,
    )
    sentiment_scheduler.start()
    # 异步获取队列大小用于日志
    try:
        asyncio.run(_log_queue_size())
    except RuntimeError:
        # 事件循环已在运行（如 APScheduler 环境），跳过队列大小日志
        logger.info("情感分析 Worker 已启动")
def stop_sentiment_worker():
    """停止情感分析 Worker"""
    if sentiment_scheduler.running:
        sentiment_scheduler.shutdown()
        logger.info("情感分析 Worker 已停止")
