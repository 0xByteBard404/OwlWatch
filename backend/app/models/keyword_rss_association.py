# -*- coding: utf-8 -*-
"""监控主体与 RSS 订阅源关联模型（多对多）"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
import json

from ..database import Base
from ..utils.timezone import now_cst


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


class KeywordRSSAssociation(Base):
    """监控主体与 RSS 订阅源的多对多关联"""
    __tablename__ = "keyword_rss_associations"

    # 主键（复合主键）
    keyword_id = Column(String(36), ForeignKey("keywords.id"), primary_key=True)
    rss_feed_id = Column(String(36), ForeignKey("rss_feeds.id"), primary_key=True)

    # 过滤规则
    filter_rules = Column(
        JSONEncodedDict,
        default={
            "include_keywords": [],
            "exclude_keywords": [],
            "match_mode": "any",  # any: 任一匹配 / all: 全部匹配
            "title_only": False,
        }
    )

    # 状态
    is_active = Column(Boolean, default=True, index=True)
    priority = Column(String(10), default="medium")  # high/medium/low

    # 统计
    created_at = Column(DateTime, default=now_cst)
    last_matched_at = Column(DateTime, nullable=True)
    match_count = Column(Integer, default=0)

    # 关系
    keyword = relationship("Keyword", back_populates="rss_associations")
    rss_feed = relationship("RSSFeed", back_populates="keyword_associations")

    def __repr__(self):
        return f"<KeywordRSSAssociation keyword={self.keyword_id} rss={self.rss_feed_id}>"

    def should_match(self, title: str, content: str = "") -> bool:
        """
        根据过滤规则判断是否匹配

        Args:
            title: 文章标题
            content: 文章内容

        Returns:
            是否匹配
        """
        # 获取要检查的文本
        text_to_check = f"{title} {content}"

        # 如果没有配置过滤规则，使用监控主体的关键词进行匹配
        if not self.filter_rules:
            # 获取监控主体的关键词
            keyword_text = self.keyword.keyword if self.keyword else None
            if keyword_text:
                # 默认：文章标题或内容必须包含监控主体的关键词
                return keyword_text.lower() in text_to_check.lower()
            # 如果没有关键词，匹配所有
            return True

        rules = self.filter_rules
        include_keywords = rules.get("include_keywords", [])
        exclude_keywords = rules.get("exclude_keywords", [])
        match_mode = rules.get("match_mode", "any")
        title_only = rules.get("title_only", False)

        # 重新计算要检查的文本
        text_to_check = title if title_only else f"{title} {content}"

        # 检查排除关键词
        for exclude_kw in exclude_keywords:
            if exclude_kw and exclude_kw.lower() in text_to_check.lower():
                return False

        # 如果没有包含关键词，使用监控主体的关键词
        if not include_keywords:
            keyword_text = self.keyword.keyword if self.keyword else None
            if keyword_text:
                return keyword_text.lower() in text_to_check.lower()
            return True

        # 检查包含关键词
        if match_mode == "all":
            # 全部匹配
            return all(kw.lower() in text_to_check.lower() for kw in include_keywords if kw)
        else:
            # 任一匹配
            return any(kw.lower() in text_to_check.lower() for kw in include_keywords if kw)
