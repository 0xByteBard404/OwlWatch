# -*- coding: utf-8 -*-
"""情感关键词模型（支持正面和负面）"""
from ..utils.timezone import now_cst
from sqlalchemy import Column, String, DateTime as SQLDateTime, Boolean
from ..database import Base


class SentimentKeyword(Base):
    """情感关键词模型"""
    __tablename__ = "sentiment_keywords"

    id = Column(String(36), primary_key=True)
    keyword = Column(String(100), nullable=False)
    sentiment_type = Column(String(20), nullable=False)  # positive / negative
    category = Column(String(50), nullable=True)  # 分类：法律、财务、品牌等
    is_active = Column(Boolean, default=True)
    created_at = Column(SQLDateTime, default=now_cst)
    updated_at = Column(SQLDateTime, default=now_cst, onupdate=now_cst)

