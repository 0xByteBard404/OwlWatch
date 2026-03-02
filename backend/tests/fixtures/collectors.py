# -*- coding: utf-8 -*-
"""
采集器测试数据 Fixtures

提供各种采集器所需的测试数据。
"""
from datetime import datetime
from typing import List


class CollectorTestData:
    """采集器测试数据集合"""

    # ==================== 博查 API 数据 ====================
    BOCHA_SUCCESS_DATA = {
        "query": "阿里云",
        "data": {
            "webPages": {
                "value": [
                    {
                        "name": "阿里云发布新产品",
                        "summary": "阿里云今日发布了全新的云原生产品线，包括容器服务和函数计算。",
                        "url": "https://www.aliyun.com/announce/new-product",
                        "siteName": "阿里云官网",
                        "dateLastCrawled": "2026-03-02T10:30:00",
                    },
                    {
                        "name": "阿里云计算大会精彩回顾",
                        "summary": "2026年阿里云计算大会在上海成功举办，吸引了众多开发者参与。",
                        "url": "https://news.example.com/aliyun-summit",
                        "siteName": "科技新闻",
                        "dateLastCrawled": "2026-03-01T15:00:00",
                    },
                ]
            }
        }
    }

    BOCHA_EMPTY_DATA = {
        "query": "不存在的关键词xyz123",
        "data": {
            "webPages": {
                "value": []
            }
        }
    }

    BOCHA_ERROR_DATA = {
        "error": "Rate limit exceeded",
        "code": 429
    }

    # ==================== Tavily API 数据 ====================
    TAVILY_SUCCESS_DATA = {
        "query": "阿里云",
        "results": [
            {
                "title": "阿里云市场表现强劲",
                "content": "阿里云在亚太地区市场份额持续领先，同比增长20%。",
                "url": "https://www.example.com/aliyun-market",
                "source": "市场分析网",
                "published_date": "2026-03-02T08:00:00Z",
            },
            {
                "title": "阿里云技术更新",
                "content": "阿里云发布了多项技术更新，包括数据库和存储服务。",
                "url": "https://tech.example.com/aliyun-update",
                "source": "技术媒体",
                "published_date": "2026-03-01T12:00:00Z",
            },
        ]
    }

    TAVILY_ERROR_DATA = {
        "error": "Invalid API key",
        "code": "unauthorized"
    }

    # ==================== Anspire API 数据 ====================
    ANSPIRE_SUCCESS_DATA = {
        "content": {
            "title": "完整文章标题",
            "text": "这是通过深度爬取获取的完整文章内容。文章详细介绍了阿里云的最新发展动态和技术创新。",
            "url": "https://www.target-site.com/full-article",
            "source": "目标网站",
        }
    }

    # ==================== 情感分析测试数据 ====================
    POSITIVE_TEXT = """
    阿里云今日发布了令人振奋的季度财报，营收增长超过预期。
    云计算业务表现优异，客户满意度达到历史新高。
    公司对未来发展充满信心，预计下季度将继续保持强劲增长。
    """

    NEGATIVE_TEXT = """
    阿里云遭遇严重服务中断，持续时间超过4小时。
    大量客户受到影响，纷纷投诉服务质量问题。
    公司股价应声下跌，投资者信心受到严重打击。
    """

    NEUTRAL_TEXT = """
    阿里云今日宣布了组织架构调整，涉及多个业务部门。
    公司表示此次调整是为了更好地适应市场变化。
    业内分析师认为这是正常的业务调整。
    """

    SHORT_TEXT = "阿里云"  # 太短的文本

    # ==================== 边界测试数据 ====================
    EDGE_CASES = {
        "empty_content": "",
        "only_whitespace": "   \n\t  ",
        "very_long_content": "测试内容" * 10000,
        "special_chars": "阿里云发布<>\"'&特殊字符测试",
        "unicode_content": "阿里云 🚀 云计算 \u4e2d\u6587测试",
        "mixed_language": "Aliyun阿里云 Cloud云计算 2026",
    }


class ExpectedResults:
    """预期结果集合"""

    # 解析后的博查结果数量
    BOCHA_PARSED_COUNT = 2

    # 解析后的 Tavily 结果数量
    TAVILY_PARSED_COUNT = 2

    # 情感分析默认值
    DEFAULT_SENTIMENT = {
        "score": 0,
        "label": "neutral",
        "reason": "分析失败"
    }

    # 内容太短的情感分析结果
    SHORT_TEXT_SENTIMENT = {
        "score": 0,
        "label": "neutral",
        "reason": "内容太短"
    }
