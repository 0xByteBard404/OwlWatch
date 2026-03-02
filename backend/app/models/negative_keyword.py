# -*- coding: utf-8 -*-
"""负面关键词模型"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime as SQLDateTime, Boolean
from ..database import Base


class NegativeKeyword(Base):
    """负面关键词模型"""
    __tablename__ = "negative_keywords"

    id = Column(String(36), primary_key=True)
    keyword = Column(String(50), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(SQLDateTime, default=datetime.utcnow)
    updated_at = Column(SQLDateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
