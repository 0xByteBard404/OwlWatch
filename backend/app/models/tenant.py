# -*- coding: utf-8 -*-
"""租户模型"""
from ..utils.timezone import now_cst
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime as SQLDateTime
from ..database import Base


class Tenant(Base):
    """租户/客户模型"""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    plan_type = Column(String(20), default="basic")  # starter/basic/pro
    max_keywords = Column(Integer, default=100)
    is_active = Column(String(10), default="active")
    created_at = Column(SQLDateTime, default=now_cst)
    updated_at = Column(SQLDateTime, default=now_cst, onupdate=now_cst)
