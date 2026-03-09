# -*- coding: utf-8 -*-
"""情感统计查询 API"""
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.dependencies import get_db
from app.models.keyword_sentiment_stats import KeywordSentimentStats
from app.models.user import User
from app.core.security import get_current_active_user

router = APIRouter()


class SentimentStatsResponse(BaseModel):
    """情感统计响应"""
    id: str
    keyword_id: str
    stats_date: str
    positive_count: int
    negative_count: int
    neutral_count: int
    total_count: int
    title_match_count: int
    content_match_count: int
    both_match_count: int
    avg_sentiment_score: Optional[float] = None


class SentimentSummaryResponse(BaseModel):
    """情感汇总响应"""
    keyword_id: str
    start_date: str
    end_date: str
    total_positive: int
    total_negative: int
    total_neutral: int
    total_articles: int
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    avg_sentiment_score: Optional[float] = None
    daily_stats: List[SentimentStatsResponse]


@router.get("/keywords/{keyword_id}/stats", response_model=SentimentSummaryResponse)
async def get_keyword_sentiment_stats(
    keyword_id: str,
    days: int = Query(7, ge=1, le=90, description="查询天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取监控主体的情感统计（按日期范围）

    - days=1: 今日统计
    - days=7: 近7天趋势
    - days=30: 近30天趋势
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    # 查询日期范围内的统计数据
    stats = db.query(KeywordSentimentStats).filter(
        KeywordSentimentStats.keyword_id == keyword_id,
        KeywordSentimentStats.stats_date >= start_date,
        KeywordSentimentStats.stats_date <= end_date
    ).order_by(KeywordSentimentStats.stats_date).all()

    # 汇总计算
    total_positive = sum(s.positive_count or 0 for s in stats)
    total_negative = sum(s.negative_count or 0 for s in stats)
    total_neutral = sum(s.neutral_count or 0 for s in stats)
    total_articles = total_positive + total_negative + total_neutral

    # 计算比率
    positive_ratio = round(total_positive / total_articles * 100, 1) if total_articles > 0 else 0
    negative_ratio = round(total_negative / total_articles * 100, 1) if total_articles > 0 else 0
    neutral_ratio = round(total_neutral / total_articles * 100, 1) if total_articles > 0 else 0

    # 计算加权平均情感分数
    valid_stats = [(s.avg_sentiment_score, s.total_count) for s in stats if s.avg_sentiment_score is not None]
    if valid_stats:
        total_weight = sum(count for _, count in valid_stats)
        weighted_sum = sum(score * count for score, count in valid_stats)
        avg_score = round(weighted_sum / total_weight, 3) if total_weight > 0 else None
    else:
        avg_score = None

    return SentimentSummaryResponse(
        keyword_id=keyword_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        total_positive=total_positive,
        total_negative=total_negative,
        total_neutral=total_neutral,
        total_articles=total_articles,
        positive_ratio=positive_ratio,
        negative_ratio=negative_ratio,
        neutral_ratio=neutral_ratio,
        avg_sentiment_score=avg_score,
        daily_stats=[
            SentimentStatsResponse(
                id=s.id,
                keyword_id=s.keyword_id,
                stats_date=s.stats_date.isoformat(),
                positive_count=s.positive_count or 0,
                negative_count=s.negative_count or 0,
                neutral_count=s.neutral_count or 0,
                total_count=s.total_count or 0,
                title_match_count=s.title_match_count or 0,
                content_match_count=s.content_match_count or 0,
                both_match_count=s.both_match_count or 0,
                avg_sentiment_score=s.avg_sentiment_score
            )
            for s in stats
        ]
    )


@router.get("/keywords/{keyword_id}/stats/today")
async def get_keyword_today_stats(
    keyword_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取监控主体今日实时统计（用于大屏展示）"""
    today = date.today()

    stats = db.query(KeywordSentimentStats).filter(
        KeywordSentimentStats.keyword_id == keyword_id,
        KeywordSentimentStats.stats_date == today
    ).first()

    if not stats:
        return {
            "keyword_id": keyword_id,
            "date": today.isoformat(),
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "total_count": 0,
            "positive_ratio": 0,
            "negative_ratio": 0,
            "neutral_ratio": 0
        }

    total = stats.total_count or 0
    return {
        "keyword_id": keyword_id,
        "date": today.isoformat(),
        "positive_count": stats.positive_count or 0,
        "negative_count": stats.negative_count or 0,
        "neutral_count": stats.neutral_count or 0,
        "total_count": total,
        "positive_ratio": round((stats.positive_count or 0) / total * 100, 1) if total > 0 else 0,
        "negative_ratio": round((stats.negative_count or 0) / total * 100, 1) if total > 0 else 0,
        "neutral_ratio": round((stats.neutral_count or 0) / total * 100, 1) if total > 0 else 0,
        "avg_sentiment_score": stats.avg_sentiment_score
    }


@router.get("/keywords/{keyword_id}/stats/trend")
async def get_sentiment_trend(
    keyword_id: str,
    days: int = Query(7, ge=7, le=30, description="查询天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取情感趋势数据（用于图表展示）

    返回格式适合 ECharts：
    - dates: 日期列表
    - positive: 正面数量列表
    - negative: 负面数量列表
    - neutral: 中性数量列表
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    stats = db.query(KeywordSentimentStats).filter(
        KeywordSentimentStats.keyword_id == keyword_id,
        KeywordSentimentStats.stats_date >= start_date,
        KeywordSentimentStats.stats_date <= end_date
    ).order_by(KeywordSentimentStats.stats_date).all()

    # 构建日期映射
    stats_map = {s.stats_date: s for s in stats}

    # 填充所有日期（包括没有数据的日期）
    dates = []
    positive = []
    negative = []
    neutral = []
    total = []

    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.isoformat())
        if current_date in stats_map:
            s = stats_map[current_date]
            positive.append(s.positive_count or 0)
            negative.append(s.negative_count or 0)
            neutral.append(s.neutral_count or 0)
            total.append(s.total_count or 0)
        else:
            positive.append(0)
            negative.append(0)
            neutral.append(0)
            total.append(0)
        current_date += timedelta(days=1)

    return {
        "keyword_id": keyword_id,
        "dates": dates,
        "series": {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "total": total
        }
    }
