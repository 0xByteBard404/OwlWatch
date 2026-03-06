# -*- coding: utf-8 -*-
"""RSSHub 配置模型"""
from sqlalchemy import Column, String, Text, DateTime, Boolean
from datetime import datetime
import uuid

from app.database import Base


class RSSHubConfig(Base):
    """RSSHub 平台配置（Cookie、API Key 等）"""
    __tablename__ = "rsshub_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    platform = Column(String, unique=True, index=True, nullable=False)  # 平台标识
    display_name = Column(String, nullable=False)  # 显示名称
    config_type = Column(String, default="cookie")  # 配置类型: cookie/api_key/token/custom
    config_value = Column(Text, nullable=True)  # 配置值
    description = Column(Text, nullable=True)  # 使用说明
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
