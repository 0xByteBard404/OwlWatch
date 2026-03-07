# -*- coding: utf-8 -*-
"""预警模型"""
from ..utils.timezone import now_cst
from datetime import datetime
from sqlalchemy import Column, String, DateTime as SQLDateTime
from ..database import Base


class Alert(Base):
    """预警模型"""
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=True, index=True)
    keyword_id = Column(String(36), nullable=False, index=True)
    article_id = Column(String(36), nullable=True)
    alert_type = Column(String(50), nullable=True, index=True)  # negative_burst/sensitive_keyword/volume_spike
    alert_level = Column(String(20), default="info")  # info/warning/critical
    status = Column(String(20), default="pending")  # pending/handled/ignored
    message = Column(String(500), nullable=True)
    created_at = Column(SQLDateTime, default=now_cst)
    handled_at = Column(SQLDateTime, nullable=True)
