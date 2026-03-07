# -*- coding: utf-8 -*-
"""舆情文章 API"""
import jieba
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from app.dependencies import get_db
from app.models.article import Article
from app.utils.timezone import now_cst

router = APIRouter()


class ArticleResponse(BaseModel):
    """文章响应"""
    id: str
    keyword_id: Optional[str] = None  # RSS 订阅可以为空
    title: str
    content: Optional[str]
    url: str
    source: Optional[str]
    source_api: Optional[str]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    publish_time: Optional[datetime]
    collect_time: datetime

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """文章列表响应"""
    items: List[ArticleResponse]
    total: int
    page: int
    size: int


@router.get("/", response_model=ArticleListResponse)
async def list_articles(
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Page size"),
    keyword_id: Optional[str] = Query(default=None, description="Filter by keyword ID"),
    sentiment: Optional[str] = Query(default=None, description="Filter by sentiment"),
    source: Optional[str] = Query(default=None, description="Filter by source"),
    start_date: Optional[datetime] = Query(default=None, description="Start date"),
    end_date: Optional[datetime] = Query(default=None, description="End date"),
    db: Session = Depends(get_db)
):
    """Get articles with filters"""
    query = db.query(Article)

    if keyword_id:
        query = query.filter(Article.keyword_id == keyword_id)
    if sentiment:
        query = query.filter(Article.sentiment_label == sentiment)
    if source:
        query = query.filter(Article.source == source)
    if start_date:
        query = query.filter(Article.publish_time >= start_date)
    if end_date:
        query = query.filter(Article.publish_time <= end_date)

    total = query.count()
    # 按发布时间倒序排列（发布时间为空则用采集时间）
    items = query.order_by(
        func.coalesce(Article.publish_time, Article.collect_time).desc()
    ).offset((page - 1) * size).limit(size).all()

    return ArticleListResponse(
        items=items,
        total=total,
        page=page,
        size=size
    )


@router.get("/sources", response_model=List[str])
async def get_sources(db: Session = Depends(get_db)):
    """获取所有来源列表（用于筛选器）"""
    results = db.query(Article.source).filter(
        Article.source.isnot(None)
    ).distinct().order_by(Article.source).all()
    return [r[0] for r in results if r[0]]


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str,
    db: Session = Depends(get_db)
):
    """Get article details"""
    article = db.query(Article).filter(Article.id == article_id).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return article


# ==================== 统计 API ====================

class TrendPoint(BaseModel):
    """趋势数据点"""
    date: str
    count: int
    positive: int
    negative: int
    neutral: int


class TrendResponse(BaseModel):
    """趋势响应"""
    data: List[TrendPoint]


class SourceDistribution(BaseModel):
    """来源分布"""
    source: str
    count: int


class WordFrequency(BaseModel):
    """词频"""
    word: str
    count: int


class StatsResponse(BaseModel):
    """综合统计响应"""
    total: int
    today: int
    week: int
    positive_ratio: float
    negative_ratio: float


@router.get("/stats/overview", response_model=StatsResponse)
async def get_stats_overview(db: Session = Depends(get_db)):
    """获取概览统计"""
    now = now_cst()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    total = db.query(Article).count()
    today = db.query(Article).filter(Article.collect_time >= today_start).count()
    week = db.query(Article).filter(Article.collect_time >= week_start).count()

    # 情感比例
    sentiment_counts = db.query(
        Article.sentiment_label,
        func.count(Article.id)
    ).filter(Article.sentiment_label.isnot(None)).group_by(Article.sentiment_label).all()

    sentiment_dict = {label: count for label, count in sentiment_counts}
    total_with_sentiment = sum(sentiment_dict.values()) or 1

    return StatsResponse(
        total=total,
        today=today,
        week=week,
        positive_ratio=sentiment_dict.get("positive", 0) / total_with_sentiment,
        negative_ratio=sentiment_dict.get("negative", 0) / total_with_sentiment,
    )


@router.get("/stats/trend", response_model=TrendResponse)
async def get_trend(
    days: int = Query(default=7, ge=1, le=30, description="天数"),
    keyword_id: Optional[str] = Query(default=None, description="关键词ID"),
    db: Session = Depends(get_db)
):
    """获取舆情趋势数据"""
    now = now_cst()
    start_date = now - timedelta(days=days)

    query = db.query(Article).filter(Article.collect_time >= start_date)
    if keyword_id:
        query = query.filter(Article.keyword_id == keyword_id)

    articles = query.all()

    # 按日期分组
    daily_data: Dict[str, Dict] = {}
    for i in range(days):
        date = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        daily_data[date] = {"count": 0, "positive": 0, "negative": 0, "neutral": 0}

    for article in articles:
        date = article.collect_time.strftime("%Y-%m-%d")
        if date in daily_data:
            daily_data[date]["count"] += 1
            if article.sentiment_label:
                daily_data[date][article.sentiment_label] += 1

    data = [
        TrendPoint(
            date=date,
            count=vals["count"],
            positive=vals["positive"],
            negative=vals["negative"],
            neutral=vals["neutral"]
        )
        for date, vals in sorted(daily_data.items())
    ]

    return TrendResponse(data=data)


@router.get("/sources", response_model=List[str])
async def get_sources(db: Session = Depends(get_db)):
    """获取所有来源列表（用于筛选器）"""
    results = db.query(Article.source).filter(
        Article.source.isnot(None)
    ).distinct().order_by(Article.source).all()
    return [r[0] for r in results if r[0]]


@router.get("/stats/sources", response_model=List[SourceDistribution])
async def get_source_distribution(
    keyword_id: Optional[str] = Query(default=None, description="关键词ID"),
    limit: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """获取来源分布"""
    query = db.query(
        Article.source,
        func.count(Article.id).label("count")
    ).filter(Article.source.isnot(None))

    if keyword_id:
        query = query.filter(Article.keyword_id == keyword_id)

    results = query.group_by(Article.source).order_by(func.count(Article.id).desc()).limit(limit).all()

    return [SourceDistribution(source=r[0] or "未知", count=r[1]) for r in results]


@router.get("/stats/words", response_model=List[WordFrequency])
async def get_word_frequency(
    keyword_id: Optional[str] = Query(default=None, description="关键词ID"),
    days: int = Query(default=7, ge=1, le=30, description="天数"),
    limit: int = Query(default=50, ge=10, le=100),
    db: Session = Depends(get_db)
):
    """获取高频词统计（用于词云）"""
    now = now_cst()
    start_date = now - timedelta(days=days)

    query = db.query(Article).filter(Article.collect_time >= start_date)
    if keyword_id:
        query = query.filter(Article.keyword_id == keyword_id)

    articles = query.all()

    # 扩充停用词表
    stopwords = {
        # 常用虚词
        "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
        "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
        "自己", "这", "那", "么", "什么", "他", "她", "它", "们", "这个", "那个", "可以",
        "没", "啊", "但", "还", "而", "且", "或", "与", "及", "等", "把", "被", "让",
        "对", "为", "以", "由", "从", "向", "跟", "比", "更", "最", "能", "得", "地",
        # 常见无意义词
        "之", "其", "者", "所", "则", "即", "因", "于", "来", "又", "已", "过",
        "这里", "那里", "哪里", "怎样", "如何", "为何", "多少", "几个", "某个",
        "一些", "一种", "一样", "一边", "一方面", "另一方面",
        # 网站来源相关
        "微信", "公众号", "订阅号", "服务号", "APP", "app", "com", "www", "http",
        "财富股研", "通报", "财经", "资讯", "信息", "消息", "报道", "新闻",
        # 时间词
        "今天", "明天", "昨天", "今年", "去年", "明年", "近日", "近期", "目前",
        "以后", "之前", "之后", "现在", "当时", "此时", "届时",
        # 数量词
        "第一", "第二", "第三", "首先", "其次", "最后", "再次",
        "千万", "百万", "千万亿", "亿元", "万元",
    }

    # 分词统计
    word_counter = Counter()
    for article in articles:
        # 只分析标题，标题更能反映关键词
        text = article.title or ""
        words = jieba.cut(text)
        for word in words:
            word = word.strip()
            # 过滤条件：长度2-8、是中文、不在停用词表、不含数字
            if (2 <= len(word) <= 8 and
                word not in stopwords and
                not any(c.isdigit() for c in word) and
                all('\u4e00' <= c <= '\u9fff' or c.isalpha() for c in word)):
                word_counter[word] += 1

    # 过滤掉只出现1次的词，返回高频词
    return [
        WordFrequency(word=w, count=c)
        for w, c in word_counter.most_common(limit)
        if c >= 2  # 至少出现2次
    ][:limit]
