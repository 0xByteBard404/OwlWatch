# -*- coding: utf-8 -*-
"""
外部 API Mock 工具

提供统一的外部 API 模拟功能，用于测试采集器和分析器。
"""
import json
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import contextmanager


class APIMockFactory:
    """API Mock 工厂类"""

    @staticmethod
    def create_response(
        status_code: int = 200,
        json_data: Any = None,
        text: str = "",
        headers: dict = None,
    ) -> MagicMock:
        """创建 Mock HTTP 响应"""
        response = MagicMock()
        response.status_code = status_code
        response.text = text or (json.dumps(json_data) if json_data else "")
        response.headers = headers or {}
        response.json.return_value = json_data if json_data is not None else {}
        return response

    @staticmethod
    def create_async_client_mock(
        responses: list[MagicMock],
        raise_on_status: bool = False,
    ) -> MagicMock:
        """创建 Mock AsyncClient"""
        client_mock = MagicMock()
        client_mock.__aenter__ = AsyncMock(return_value=client_mock)
        client_mock.__aexit__ = AsyncMock(return_value=None)

        # 创建响应迭代器
        response_iter = iter(responses)

        async def mock_post(*args, **kwargs):
            try:
                return next(response_iter)
            except StopIteration:
                return responses[-1] if responses else APIMockFactory.create_response()

        client_mock.post = mock_post
        return client_mock


class BochaAPIMock:
    """博查 API Mock"""

    @staticmethod
    def success_response(items: list[dict] = None) -> MagicMock:
        """成功的博查响应"""
        default_items = [
            {
                "name": "测试新闻标题",
                "summary": "这是测试新闻的内容摘要，包含重要信息。",
                "url": "https://example.com/news/1",
                "siteName": "测试新闻网",
                "dateLastCrawled": "2026-03-02T10:00:00",
            }
        ]
        items = items or default_items

        return APIMockFactory.create_response(
            status_code=200,
            json_data={
                "query": "测试关键词",
                "data": {
                    "webPages": {
                        "value": items
                    }
                }
            }
        )

    @staticmethod
    def error_response(status_code: int = 500, message: str = "Internal Server Error") -> MagicMock:
        """错误的博查响应"""
        return APIMockFactory.create_response(
            status_code=status_code,
            json_data={"error": message},
            text=message,
        )

    @staticmethod
    def empty_response() -> MagicMock:
        """空结果响应"""
        return APIMockFactory.create_response(
            status_code=200,
            json_data={
                "query": "测试关键词",
                "data": {"webPages": {"value": []}}
            }
        )


class TavilyAPIMock:
    """Tavily API Mock"""

    @staticmethod
    def success_response(items: list[dict] = None) -> MagicMock:
        """成功的 Tavily 响应"""
        default_items = [
            {
                "title": "Tavily 测试文章",
                "content": "这是 Tavily 返回的测试内容。",
                "url": "https://example.com/tavily/1",
                "source": "测试来源",
                "published_date": "2026-03-02T10:00:00Z",
            }
        ]
        items = items or default_items

        return APIMockFactory.create_response(
            status_code=200,
            json_data={
                "query": "测试关键词",
                "results": items
            }
        )

    @staticmethod
    def error_response(status_code: int = 401) -> MagicMock:
        """错误的 Tavily 响应"""
        return APIMockFactory.create_response(
            status_code=status_code,
            json_data={"error": "Unauthorized"},
        )


class AnspireAPIMock:
    """Anspire API Mock"""

    @staticmethod
    def success_response(content: dict = None) -> MagicMock:
        """成功的 Anspire 响应"""
        default_content = {
            "title": "Anspire 深度爬取结果",
            "text": "这是通过 Anspire 深度爬取的完整内容。",
            "url": "https://example.com/deep-content",
            "source": "目标网站",
        }
        content = content or default_content

        return APIMockFactory.create_response(
            status_code=200,
            json_data={"content": content}
        )


class SentimentAPIMock:
    """情感分析 API Mock"""

    @staticmethod
    def success_response(
        score: float = 0.5,
        label: str = "positive",
        reason: str = "内容积极向上"
    ) -> MagicMock:
        """成功的情感分析响应"""
        return APIMockFactory.create_response(
            status_code=200,
            json_data={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "score": score,
                                "label": label,
                                "reason": reason
                            })
                        }
                    }
                ]
            }
        )

    @staticmethod
    def markdown_wrapped_response(
        score: float = 0.5,
        label: str = "positive",
        reason: str = "内容积极向上"
    ) -> MagicMock:
        """Markdown 代码块包装的响应"""
        content = f"""```json
{{
    "score": {score},
    "label": "{label}",
    "reason": "{reason}"
}}
```"""
        return APIMockFactory.create_response(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": content}}]
            }
        )

    @staticmethod
    def batch_response(count: int = 3) -> MagicMock:
        """批量情感分析响应"""
        results = []
        for i in range(count):
            results.append({
                "score": 0.5 - i * 0.3,
                "label": ["positive", "neutral", "negative"][min(i, 2)]
            })

        return APIMockFactory.create_response(
            status_code=200,
            json_data={
                "choices": [
                    {"message": {"content": json.dumps(results)}}
                ]
            }
        )


# ==================== 便捷上下文管理器 ====================
@contextmanager
def mock_httpx_client(responses: list[MagicMock]):
    """Mock httpx.AsyncClient 的上下文管理器"""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = APIMockFactory.create_async_client_mock(responses)
        mock_client_class.return_value = mock_client
        yield mock_client


@contextmanager
def mock_collector_api(api_mock_class: type, method_name: str = "success_response"):
    """Mock 采集器 API 的上下文管理器"""
    mock_response = getattr(api_mock_class, method_name)()
    with mock_httpx_client([mock_response]) as mock_client:
        yield mock_client
