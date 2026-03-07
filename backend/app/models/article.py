# -*- coding: utf-8 -*-
"""舆情文章模型"""
from sqlalchemy import Column, String, Float, Text, DateTime as SQLDateTime, UniqueConstraint
from ..database import Base
from ..utils.timezone import now_cst


class Article(Base):
    """舆情文章模型"""
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint('url', name='uq_articles_url'),
    )

    id = Column(String(36), primary_key=True)
    keyword_id = Column(String(36), nullable=True, index=True)  # RSS 订阅可以为空
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    url = Column(String(500), nullable=False)
    source = Column(String(100), nullable=True)  # 微博/抖音/今日头条等
    source_api = Column(String(20), nullable=True)  # bocha/tavily/anspire
    sentiment_score = Column(Float, nullable=True)  # -1 到 1
    sentiment_label = Column(String(20), nullable=True)  # positive/negative/neutral
    publish_time = Column(SQLDateTime, nullable=True)
    collect_time = Column(SQLDateTime, default=now_cst)
    extra = Column(Text, nullable=True)  # JSON 扩展字段
