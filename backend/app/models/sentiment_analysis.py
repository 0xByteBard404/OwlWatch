# -*- coding: utf-8 -*-
"""情感分析结果模型"""
from sqlalchemy import Column, String, DateTime as SQLDateTime, Numeric, JSON
from sqlalchemy.dialects.postgresql import JSONB
from ..database import Base
from ..utils.timezone import now_cst


from sqlalchemy import ForeignKey


class SentimentAnalysis(Base):
    """情感分析结果"""
    __tablename__ = "sentiment_analysis"

    id = Column(String(36), primary_key=True)
    article_id = Column(String(36), ForeignKey('articles.id'), nullable=True, index=True)

    # 情感类型: positive / negative / neutral
    sentiment_type = Column(String(20), nullable=False, index=True)

    # 情感分数 (-1.0 ~ 1.0)
    sentiment_score = Column(Numeric(3, 2), nullable=False)

    # 热情度 (0.0 ~ 1.0)
    confidence = Column(Numeric(3, 2), default=0.5)

    # 匹配的正面关键词 (JSON 数组)
    matched_positive_keywords = Column(JSON, nullable=True)

    # 匹配的负面关键词 (JSON 数组)
    matched_negative_keywords = Column(JSON, nullable=True)

    # 命名实体 (JSON 对象)
    named_entities = Column(JSON, nullable=True)

    # Cemotion 原始分数
    raw_emotion_score = Column(Numeric(3, 2), nullable=True)

    # 分析时间
    analyzed_at = Column(SQLDateTime, default=now_cst)

    # 创建和更新时间
    created_at = Column(SQLDateTime, default=now_cst)
    updated_at = Column(SQLDateTime, default=now_cst, onupdate=now_cst)
