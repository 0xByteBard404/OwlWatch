# -*- coding: utf-8 -*-
"""RSS 订阅源模型"""
from ..utils.timezone import now_cst
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime as SQLDateTime, Integer, Text
from ..database import Base


class RSSFeed(Base):
    """RSS 订阅源模型"""
    __tablename__ = "rss_feeds"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=True, index=True)
    
    # 订阅配置
    name = Column(String(200), nullable=False)  # 订阅名称，如 "微博-特斯拉"
    feed_url = Column(String(1000), nullable=False)  # RSS URL
    source_type = Column(String(50), nullable=True)  # weibo/zhihu/bilibili/generic
    
    # 关联监控主体（可选）
    keyword_id = Column(String(36), nullable=True, index=True)
    
    # 状态
    is_active = Column(Boolean, default=True)
    last_fetched = Column(SQLDateTime, nullable=True)  # 最后获取时间
    last_etag = Column(String(100), nullable=True)  # HTTP ETag 缓存
    last_modified = Column(String(100), nullable=True)  # HTTP Last-Modified 缓存
    last_entry_id = Column(String(500), nullable=True)  # 最后一条条目的 ID（用于增量获取）
    fetch_error_count = Column(Integer, default=0)  # 连续错误次数
    last_error = Column(Text, nullable=True)  # 最后一次错误信息
    
    # 配置
    fetch_interval = Column(Integer, default=300)  # 轮询间隔（秒），默认 5 分钟
    
    # 统计
    total_entries = Column(Integer, default=0)  # 累计获取条目数
    
    # 时间戳
    created_at = Column(SQLDateTime, default=now_cst)
    updated_at = Column(SQLDateTime, default=now_cst, onupdate=now_cst)
