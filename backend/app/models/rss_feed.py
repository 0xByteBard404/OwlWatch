# -*- coding: utf-8 -*-
"""RSS 订阅源模型"""
from ..utils.timezone import now_cst
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime as SQLDateTime, Integer, Text
from sqlalchemy.orm import relationship
from ..database import Base


class RSSFeed(Base):
    """RSS 订阅源模型（独立数据源）"""
    __tablename__ = "rss_feeds"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=True, index=True)
    
    # 订阅配置
    name = Column(String(200), nullable=False)
    feed_url = Column(String(1000), nullable=False)
    source_type = Column(String(50), nullable=True)  # weibo/zhihu/bilibili/generic
    
    # 关联监控主体（已废弃，请在监控主体中配置）
    keyword_id = Column(String(36), nullable=True, index=True)
    
    # 状态
    is_active = Column(Boolean, default=True)
    last_fetched = Column(SQLDateTime, nullable=True)
    last_etag = Column(String(100), nullable=True)
    last_modified = Column(String(100), nullable=True)
    last_entry_id = Column(String(500), nullable=True)
    fetch_error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    # 配置
    fetch_interval = Column(Integer, default=300)
    
    # 统计
    total_entries = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(SQLDateTime, default=now_cst)
    updated_at = Column(SQLDateTime, default=now_cst, onupdate=now_cst)

    # 关系
    keyword_associations = relationship(
        "KeywordRSSAssociation",
        back_populates="rss_feed",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<RSSFeed {self.name} ({self.feed_url})>"


# 数据库迁移说明
# 
# 迁移步骤:
# 1. 添加 keywords.data_sources 列:
#    ALTER TABLE keywords ADD COLUMN data_sources TEXT;
#
# 2. 清空旧的关联（可选，如果不再需要）:
#    UPDATE rss_feeds SET keyword_id = NULL;
#
# 此字段保留用于向后兼容，但新逻辑通过 keywords.data_sources 管理。
