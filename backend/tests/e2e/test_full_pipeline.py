# -*- coding: utf-8 -*-
"""
端到端链路测试

测试完整流程：采集 → 分析 → 存储 → 展示

验证内容：
1. 创建关键词
2. 触发采集
3. 验证情感分析
4. 验证数据库存储
5. 通过 API 查询结果
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.keyword import Keyword
from app.models.article import Article
from app.collectors.base import CollectRequest
from app.collectors.bocha import BochaCollector
from app.analyzers.sentiment import SentimentAnalyzer
from tests.fixtures.collectors import CollectorTestData
from tests.fixtures.database import KeywordFactory, ArticleFactory


class TestEndToEndPipeline:
    """端到端链路测试类"""

    @pytest.mark.e2e
    def test_full_pipeline_success(
        self, client: TestClient, db_session: Session
    ):
        """
        测试完整的端到端流程

        流程：
        1. 创建关键词
        2. 触发采集
        3. 验证文章已保存
        4. 验证情感分析结果
        5. 通过 API 查询文章
        """
        # ========== Step 1: 创建关键词 ==========
        keyword_data = {
            "keyword": "阿里云",
            "priority": "high",
            "platforms": ["bocha"]
        }
        create_response = client.post("/api/v1/keywords/", json=keyword_data)

        assert create_response.status_code == 200
        keyword_id = create_response.json()["id"]
        print(f"✓ Step 1: 创建关键词成功, ID={keyword_id}")

        # ========== Step 2: 触发采集 ==========
        # Mock 博查 API 响应
        mock_bocha_response = MagicMock()
        mock_bocha_response.status_code = 200
        mock_bocha_response.json.return_value = {
            "query": "阿里云",
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "阿里云发布新产品",
                            "summary": "阿里云今日发布了全新的云原生产品线，这是一条非常积极的新闻。",
                            "url": "https://www.aliyun.com/new-product",
                            "siteName": "阿里云官网",
                            "dateLastCrawled": "2026-03-02T10:00:00",
                        }
                    ]
                }
            }
        }

        # Mock 情感分析响应
        mock_sentiment_response = MagicMock()
        mock_sentiment_response.status_code = 200
        mock_sentiment_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"score": 0.8, "label": "positive", "reason": "产品发布是积极消息"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            responses = [mock_bocha_response, mock_sentiment_response]
            response_iter = iter(responses)

            async def mock_post(*args, **kwargs):
                try:
                    return next(response_iter)
                except StopIteration:
                    return responses[-1]

            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            trigger_response = client.post(
                f"/api/v1/collect/trigger?keyword_id={keyword_id}"
            )

        assert trigger_response.status_code == 200
        trigger_data = trigger_response.json()
        print(f"✓ Step 2: 采集完成, 获取 {trigger_data['collected_count']} 条文章")

        # ========== Step 3: 验证数据库存储 ==========
        db_session.expire_all()  # 刷新会话
        articles = db_session.query(Article).filter(
            Article.keyword_id == keyword_id
        ).all()

        assert len(articles) > 0
        print(f"✓ Step 3: 数据库存储验证, 保存了 {len(articles)} 条文章")

        # ========== Step 4: 验证情感分析结果 ==========
        article = articles[0]
        assert article.sentiment_score is not None
        assert article.sentiment_label in ["positive", "negative", "neutral"]
        print(f"✓ Step 4: 情感分析验证, score={article.sentiment_score}, label={article.sentiment_label}")

        # ========== Step 5: 通过 API 查询文章 ==========
        articles_response = client.get("/api/v1/articles/")
        assert articles_response.status_code == 200
        articles_data = articles_response.json()

        # 验证可以找到我们采集的文章（返回格式为 {"items": [...], "total": N, ...}）
        items = articles_data.get("items", articles_data)
        found = any(a["title"] == "阿里云发布新产品" for a in items)
        assert found
        print(f"✓ Step 5: API 查询验证, 找到目标文章")

        print("\n✅ 端到端链路测试通过!")

    @pytest.mark.e2e
    def test_pipeline_with_negative_sentiment(
        self, client: TestClient, db_session: Session
    ):
        """测试负面情感文章的完整流程"""
        # 创建关键词
        create_response = client.post(
            "/api/v1/keywords/",
            json={"keyword": "测试负面", "priority": "medium", "platforms": ["bocha"]}
        )
        keyword_id = create_response.json()["id"]

        # Mock 负面新闻采集
        mock_bocha_response = MagicMock()
        mock_bocha_response.status_code = 200
        mock_bocha_response.json.return_value = {
            "query": "测试负面",
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "公司遭遇严重危机",
                            "summary": "该公司今日遭遇严重的服务中断，大量用户受影响，这是一条非常消极的新闻。",
                            "url": "https://example.com/crisis",
                            "siteName": "新闻网站",
                            "dateLastCrawled": "2026-03-02T10:00:00",
                        }
                    ]
                }
            }
        }

        mock_sentiment_response = MagicMock()
        mock_sentiment_response.status_code = 200
        mock_sentiment_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"score": -0.7, "label": "negative", "reason": "服务中断是负面消息"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            responses = [mock_bocha_response, mock_sentiment_response]
            response_iter = iter(responses)

            async def mock_post(*args, **kwargs):
                try:
                    return next(response_iter)
                except StopIteration:
                    return responses[-1]

            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            trigger_response = client.post(
                f"/api/v1/collect/trigger?keyword_id={keyword_id}"
            )

        assert trigger_response.status_code == 200

        # 验证负面情感
        db_session.expire_all()
        article = db_session.query(Article).filter(
            Article.keyword_id == keyword_id
        ).first()

        assert article is not None
        assert article.sentiment_label == "negative"
        assert article.sentiment_score < 0
        print("✅ 负面情感链路测试通过!")

    @pytest.mark.e2e
    def test_pipeline_handles_duplicate_articles(
        self, client: TestClient, db_session: Session
    ):
        """测试重复文章处理"""
        # 创建关键词
        create_response = client.post(
            "/api/v1/keywords/",
            json={"keyword": "重复测试", "priority": "low", "platforms": ["bocha"]}
        )
        keyword_id = create_response.json()["id"]

        # 第一次采集
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": "重复测试",
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "测试文章",
                            "summary": "这是测试内容",
                            "url": "https://example.com/duplicate-test",
                            "siteName": "测试网站",
                            "dateLastCrawled": "2026-03-02T10:00:00",
                        }
                    ]
                }
            }
        }

        mock_sentiment = MagicMock()
        mock_sentiment.status_code = 200
        mock_sentiment.json.return_value = {
            "choices": [{"message": {"content": '{"score": 0, "label": "neutral"}'}}]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            responses = [mock_response, mock_sentiment]
            response_iter = iter(responses)

            async def mock_post(*args, **kwargs):
                try:
                    return next(response_iter)
                except StopIteration:
                    return responses[-1]

            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            # 第一次采集
            client.post(f"/api/v1/collect/trigger?keyword_id={keyword_id}")

            # 重置 mock
            mock_client.post = AsyncMock(return_value=mock_sentiment)

            # 第二次采集（相同文章）
            client.post(f"/api/v1/collect/trigger?keyword_id={keyword_id}")

        # 验证只有一篇文章
        db_session.expire_all()
        articles = db_session.query(Article).filter(
            Article.keyword_id == keyword_id
        ).all()

        assert len(articles) == 1  # 不应重复保存
        print("✅ 重复文章处理测试通过!")


@pytest.mark.asyncio
class TestEndToEndAsync:
    """端到端异步测试类"""

    @pytest.mark.e2e
    async def test_full_pipeline_async(
        self, async_client: AsyncClient, db_session: Session
    ):
        """测试异步端到端流程"""
        # 创建关键词
        create_response = await async_client.post(
            "/api/v1/keywords/",
            json={"keyword": "异步测试", "priority": "high", "platforms": ["bocha"]}
        )
        assert create_response.status_code == 200
        keyword_id = create_response.json()["id"]

        # Mock 采集
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": "异步测试",
            "data": {"webPages": {"value": []}}
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            # 触发采集
            trigger_response = await async_client.post(
                f"/api/v1/collect/trigger?keyword_id={keyword_id}"
            )

        assert trigger_response.status_code == 200

        # 查询文章
        articles_response = await async_client.get("/api/v1/articles/")
        assert articles_response.status_code == 200

        print("✅ 异步端到端测试通过!")


class TestPipelineResilience:
    """链路弹性测试"""

    @pytest.mark.e2e
    def test_pipeline_handles_collector_failure(
        self, client: TestClient, db_session: Session
    ):
        """测试采集器失败的弹性处理"""
        # 创建关键词
        create_response = client.post(
            "/api/v1/keywords/",
            json={"keyword": "故障测试", "priority": "high", "platforms": ["bocha"]}
        )
        keyword_id = create_response.json()["id"]

        # Mock 采集器失败
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_error_response)
            mock_client_class.return_value = mock_client

            # 触发采集
            trigger_response = client.post(
                f"/api/v1/collect/trigger?keyword_id={keyword_id}"
            )

        # 应该优雅处理错误，不抛出异常
        assert trigger_response.status_code == 200
        assert trigger_response.json()["collected_count"] == 0
        print("✅ 采集器故障弹性测试通过!")

    @pytest.mark.e2e
    def test_pipeline_handles_analyzer_failure(
        self, client: TestClient, db_session: Session
    ):
        """测试分析器失败的弹性处理"""
        # 创建关键词
        create_response = client.post(
            "/api/v1/keywords/",
            json={"keyword": "分析故障", "priority": "high", "platforms": ["bocha"]}
        )
        keyword_id = create_response.json()["id"]

        # Mock 成功采集
        mock_bocha_response = MagicMock()
        mock_bocha_response.status_code = 200
        mock_bocha_response.json.return_value = {
            "query": "分析故障",
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "测试文章",
                            "summary": "这是测试内容，需要足够长以便触发分析。",
                            "url": "https://example.com/test",
                            "siteName": "测试网站",
                            "dateLastCrawled": "2026-03-02T10:00:00",
                        }
                    ]
                }
            }
        }

        # Mock 分析器失败
        mock_sentiment_error = MagicMock()
        mock_sentiment_error.status_code = 500
        mock_sentiment_error.text = "API Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            responses = [mock_bocha_response, mock_sentiment_error]
            response_iter = iter(responses)

            async def mock_post(*args, **kwargs):
                try:
                    return next(response_iter)
                except StopIteration:
                    return responses[-1]

            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            # 触发采集
            trigger_response = client.post(
                f"/api/v1/collect/trigger?keyword_id={keyword_id}"
            )

        # 应该成功保存文章（即使分析失败）
        assert trigger_response.status_code == 200

        db_session.expire_all()
        article = db_session.query(Article).filter(
            Article.keyword_id == keyword_id
        ).first()

        assert article is not None
        # 情感分析可能为 None（分析失败时）
        print("✅ 分析器故障弹性测试通过!")
