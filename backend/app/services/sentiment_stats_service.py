# -*- coding: utf-8 -*-
"""情感统计增量更新服务"""
import logging
import uuid
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.keyword_sentiment_stats import KeywordSentimentStats
from app.utils.timezone import now_cst

logger = logging.getLogger(__name__)


def increment_sentiment_stats(
    db: Session,
    keyword_id: str,
    sentiment_label: str,
    sentiment_score: float = None,
    match_type: str = None,
    stats_date: date = None
) -> None:
    """
    增量更新监控主体的情感统计

    Args:
        db: 数据库会话
        keyword_id: 监控主体ID
        sentiment_label: 情感标签 (positive/negative/neutral)
        sentiment_score: 情感分数 (-1 到 1)，可选
        match_type: 匹配类型 (title_only/content_only/both)，可选
        stats_date: 统计日期，默认今天
    """
    if stats_date is None:
        stats_date = date.today()

    try:
        # 查找当天的统计记录
        stats = db.query(KeywordSentimentStats).filter(
            KeywordSentimentStats.keyword_id == keyword_id,
            KeywordSentimentStats.stats_date == stats_date
        ).first()

        if not stats:
            # 创建新的统计记录
            stats = KeywordSentimentStats(
                id=str(uuid.uuid4()),
                keyword_id=keyword_id,
                stats_date=stats_date,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                total_count=0,
                title_match_count=0,
                content_match_count=0,
                both_match_count=0
            )
            db.add(stats)
            db.flush()

        # 增量更新情感计数
        stats.total_count += 1

        if sentiment_label == "positive":
            stats.positive_count += 1
        elif sentiment_label == "negative":
            stats.negative_count += 1
        else:
            stats.neutral_count += 1

        # 更新匹配类型计数
        if match_type == "title_only":
            stats.title_match_count += 1
        elif match_type == "content_only":
            stats.content_match_count += 1
        elif match_type == "both":
            stats.both_match_count += 1

        # 更新平均情感分数（增量计算）
        if sentiment_score is not None:
            if stats.avg_sentiment_score is None:
                stats.avg_sentiment_score = sentiment_score
            else:
                # 增量计算平均值
                stats.avg_sentiment_score = (
                    (stats.avg_sentiment_score * (stats.total_count - 1) + sentiment_score)
                    / stats.total_count
                )

        stats.updated_at = now_cst()
        # 注意：不在这里 commit，让调用方控制事务

    except Exception as e:
        logger.error(f"Failed to increment sentiment stats for keyword {keyword_id}: {e}")
        # 不抛出异常，避免影响主流程


def batch_increment_sentiment_stats(
    db: Session,
    keyword_id: str,
    stats_list: list
) -> None:
    """
    批量增量更新统计（用于批量采集后一次性更新）

    Args:
        db: 数据库会话
        keyword_id: 监控主体ID
        stats_list: 统计列表 [{"sentiment_label": "positive", "sentiment_score": 0.8, "match_type": "title_only"}, ...]
    """
    if not stats_list:
        return

    today = date.today()

    # 汇总今天的统计
    positive_count = sum(1 for s in stats_list if s.get("sentiment_label") == "positive")
    negative_count = sum(1 for s in stats_list if s.get("sentiment_label") == "negative")
    neutral_count = len(stats_list) - positive_count - negative_count

    title_match_count = sum(1 for s in stats_list if s.get("match_type") == "title_only")
    content_match_count = sum(1 for s in stats_list if s.get("match_type") == "content_only")
    both_match_count = sum(1 for s in stats_list if s.get("match_type") == "both")

    # 计算平均情感分数
    scores = [s.get("sentiment_score") for s in stats_list if s.get("sentiment_score") is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    try:
        # 使用 PostgreSQL 的 UPSERT (ON CONFLICT)
        stmt = text("""
            INSERT INTO keyword_sentiment_stats
                (id, keyword_id, stats_date, positive_count, negative_count, neutral_count,
                 total_count, title_match_count, content_match_count, both_match_count,
                 avg_sentiment_score, created_at, updated_at)
            VALUES
                (:id, :keyword_id, :stats_date, :positive_count, :negative_count, :neutral_count,
                 :total_count, :title_match_count, :content_match_count, :both_match_count,
                 :avg_sentiment_score, NOW(), NOW())
            ON CONFLICT (keyword_id, stats_date) DO UPDATE SET
                positive_count = keyword_sentiment_stats.positive_count + EXCLUDED.positive_count,
                negative_count = keyword_sentiment_stats.negative_count + EXCLUDED.negative_count,
                neutral_count = keyword_sentiment_stats.neutral_count + EXCLUDED.neutral_count,
                total_count = keyword_sentiment_stats.total_count + EXCLUDED.total_count,
                title_match_count = keyword_sentiment_stats.title_match_count + EXCLUDED.title_match_count,
                content_match_count = keyword_sentiment_stats.content_match_count + EXCLUDED.content_match_count,
                both_match_count = keyword_sentiment_stats.both_match_count + EXCLUDED.both_match_count,
                avg_sentiment_score = CASE
                    WHEN keyword_sentiment_stats.avg_sentiment_score IS NULL THEN EXCLUDED.avg_sentiment_score
                    WHEN EXCLUDED.avg_sentiment_score IS NULL THEN keyword_sentiment_stats.avg_sentiment_score
                    ELSE (keyword_sentiment_stats.avg_sentiment_score * keyword_sentiment_stats.total_count + EXCLUDED.avg_sentiment_score * EXCLUDED.total_count)
                         / (keyword_sentiment_stats.total_count + EXCLUDED.total_count)
                END,
                updated_at = NOW()
        """)

        db.execute(stmt, {
            "id": str(uuid.uuid4()),
            "keyword_id": keyword_id,
            "stats_date": today,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "total_count": len(stats_list),
            "title_match_count": title_match_count,
            "content_match_count": content_match_count,
            "both_match_count": both_match_count,
            "avg_sentiment_score": avg_score
        })

        logger.info(f"Batch updated sentiment stats for keyword {keyword_id}: +{len(stats_list)} articles")

    except Exception as e:
        logger.error(f"Failed to batch update sentiment stats for keyword {keyword_id}: {e}")
