# -*- coding: utf-8 -*-
"""关键词模型"""
from ..utils.timezone import now_cst
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime as SQLDateTime, Text
from sqlalchemy.types import TypeDecorator
import json
from ..database import Base


class JSONEncodedDict(TypeDecorator):
    """JSON 存储类型"""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


class Keyword(Base):
    """关键词监控模型"""
    __tablename__ = "keywords"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=True, index=True)
    keyword = Column(String(100), nullable=False)
    priority = Column(String(10), default="medium")  # high/medium/low
    platforms = Column(JSONEncodedDict, nullable=True)  # JSON: ["bocha", "tavily"]
    is_active = Column(Boolean, default=True)
    created_at = Column(SQLDateTime, default=now_cst)
    updated_at = Column(SQLDateTime, default=now_cst, onupdate=now_cst)
