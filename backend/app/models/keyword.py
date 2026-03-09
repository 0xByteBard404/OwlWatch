# -*- coding: utf-8 -*-
"""关键词模型"""
from ..utils.timezone import now_cst
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime as SQLDateTime, Text, Integer, Float
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
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

    # 数据源配置（核心字段）
    # 示例: {"rss_ids": ["uuid1", "uuid2"], "search_apis": ["bocha", "tavily"]}
    data_sources = Column(JSONEncodedDict, nullable=True)

    # 预警配置
    # 示例: {
    #   "negative_burst": {"enabled": true, "threshold": 0.3, "min_count": 5},
    #   "sensitive_keyword": {"enabled": true, "keywords": ["投诉", "维权"]},
    #   "volume_spike": {"enabled": true, "threshold": 2.0},
    #   "notifications": ["email", "wechat"]
    # }
    alert_config = Column(JSONEncodedDict, nullable=True)

    # 更新间隔（秒），默认 5 分钟
    fetch_interval = Column(Integer, default=300)

    # 最近扫描时间
    last_fetched = Column(SQLDateTime, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(SQLDateTime, default=now_cst)
    updated_at = Column(SQLDateTime, default=now_cst, onupdate=now_cst)

    # 关系
    rss_associations = relationship(
        "KeywordRSSAssociation",
        back_populates="keyword",
        cascade="all, delete-orphan"
    )


# 预警配置默认值
DEFAULT_ALERT_CONFIG = {
    "negative_burst": {
        "enabled": True,
        "threshold": 0.3,  # 负面情感占比超过 30% 触发
        "min_count": 3,     # 最少 3 篇文章
    },
    "sensitive_keyword": {
        "enabled": True,
        "use_global": True,  # 使用全局敏感词库
        "custom_keywords": [],  # 自定义敏感词
    },
    "volume_spike": {
        "enabled": True,
        "threshold": 2.0,  # 讨论量增长超过 200% 触发
    },
    "notifications": ["email", "webhook"],  # 通知渠道
}
