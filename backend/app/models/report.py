# -*- coding: utf-8 -*-
"""报告模型"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime as SQLDateTime
from ..database import Base


class Report(Base):
    """分析报告模型"""
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    report_type = Column(String(20), default="daily")  # daily/weekly/monthly
    generated_at = Column(SQLDateTime, default=datetime.utcnow)
