# -*- coding: utf-8 -*-
"""预警模型"""
from ..utils.timezone import now_cst
from datetime import datetime
from sqlalchemy import Column, String, DateTime as SQLDateTime, Text, Boolean
from ..database import Base


class Alert(Base):
    """预警模型"""
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=True, index=True)
    keyword_id = Column(String(36), nullable=False, index=True)
    article_id = Column(String(36), nullable=True)  # 主文章ID（兼容旧数据）
    related_article_ids = Column(Text, nullable=True)  # JSON: 关联文章ID列表
    alert_type = Column(String(50), nullable=True, index=True)  # negative_burst/sensitive_keyword/volume_spike
    alert_level = Column(String(20), default="info")  # info/warning/critical
    status = Column(String(20), default="pending")  # pending/handled/ignored/false_positive
    message = Column(String(500), nullable=True)
    # 处理相关字段
    handler_id = Column(String(36), nullable=True)  # 处理人ID
    handler_name = Column(String(100), nullable=True)  # 处理人名称
    handle_note = Column(Text, nullable=True)  # 处理备注
    is_false_positive = Column(Boolean, default=False)  # 是否误报
    # 时间字段
    created_at = Column(SQLDateTime, default=now_cst)
    handled_at = Column(SQLDateTime, nullable=True)
