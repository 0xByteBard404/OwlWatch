# -*- coding: utf-8 -*-
"""
数据库测试数据 Fixtures

提供数据库模型相关的测试数据和工厂函数。
"""
import uuid
from datetime import datetime
from typing import Optional

from app.models.keyword import Keyword
from app.models.article import Article


class KeywordFactory:
    """关键词数据工厂"""

    @staticmethod
    def create(
        keyword: str = "测试关键词",
        priority: str = "medium",
        platforms: list[str] = None,
        is_active: bool = True,
        id: str = None,
    ) -> Keyword:
        """创建关键词实例"""
        return Keyword(
            id=id or str(uuid.uuid4()),
            keyword=keyword,
            priority=priority,
            platforms=platforms or ["bocha", "tavily"],
            is_active=is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @staticmethod
    def create_high_priority(keyword: str = "高优先级关键词") -> Keyword:
        """创建高优先级关键词"""
        return KeywordFactory.create(keyword=keyword, priority="high")

    @staticmethod
    def create_low_priority(keyword: str = "低优先级关键词") -> Keyword:
        """创建低优先级关键词"""
        return KeywordFactory.create(keyword=keyword, priority="low")

    @staticmethod
    def create_inactive(keyword: str = "停用关键词") -> Keyword:
        """创建停用的关键词"""
        return KeywordFactory.create(keyword=keyword, is_active=False)


class ArticleFactory:
    """文章数据工厂"""

    @staticmethod
    def create(
        keyword_id: str,
        title: str = "测试文章",
        content: str = "这是测试文章的内容。",
        url: str = None,
        source: str = "测试来源",
        source_api: str = "bocha",
        sentiment_score: Optional[float] = None,
        sentiment_label: Optional[str] = None,
        id: str = None,
    ) -> Article:
        """创建文章实例"""
        return Article(
            id=id or str(uuid.uuid4()),
            keyword_id=keyword_id,
            title=title,
            content=content,
            url=url or f"https://example.com/article/{uuid.uuid4()}",
            source=source,
            source_api=source_api,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            publish_time=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

    @staticmethod
    def create_positive(
        keyword_id: str,
        title: str = "正面文章",
        content: str = "这是一个非常好的消息，令人振奋。",
    ) -> Article:
        """创建正面情感文章"""
        return ArticleFactory.create(
            keyword_id=keyword_id,
            title=title,
            content=content,
            sentiment_score=0.8,
            sentiment_label="positive",
        )

    @staticmethod
    def create_negative(
        keyword_id: str,
        title: str = "负面文章",
        content: str = "这是一个令人失望的消息，问题严重。",
    ) -> Article:
        """创建负面情感文章"""
        return ArticleFactory.create(
            keyword_id=keyword_id,
            title=title,
            content=content,
            sentiment_score=-0.7,
            sentiment_label="negative",
        )

    @staticmethod
    def create_neutral(
        keyword_id: str,
        title: str = "中性文章",
        content: str = "这是一个普通的消息，没有明显情感倾向。",
    ) -> Article:
        """创建中性情感文章"""
        return ArticleFactory.create(
            keyword_id=keyword_id,
            title=title,
            content=content,
            sentiment_score=0.0,
            sentiment_label="neutral",
        )


class TestDataPresets:
    """预定义的测试数据集合"""

    @staticmethod
    def get_keywords_for_collection_test() -> list[Keyword]:
        """获取用于采集测试的关键词列表"""
        return [
            KeywordFactory.create_high_priority("阿里云"),
            KeywordFactory.create(priority="medium", keyword="腾讯云"),
            KeywordFactory.create_low_priority("华为云"),
            KeywordFactory.create_inactive("百度云"),  # 不应被采集
        ]

    @staticmethod
    def get_articles_for_analysis_test(keyword_id: str) -> list[Article]:
        """获取用于分析测试的文章列表"""
        return [
            ArticleFactory.create_positive(keyword_id, "云市场增长强劲"),
            ArticleFactory.create_negative(keyword_id, "云计算服务中断"),
            ArticleFactory.create_neutral(keyword_id, "云厂商发布更新"),
            ArticleFactory.create(keyword_id, "无分析文章"),  # 无情感分析
        ]

    @staticmethod
    def get_sentiment_distribution() -> dict:
        """获取情感分布统计的预期结果"""
        return {
            "positive": 1,
            "negative": 1,
            "neutral": 2,
            "none": 1,
        }
