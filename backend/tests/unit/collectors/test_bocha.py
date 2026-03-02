# -*- coding: utf-8 -*-
"""
博查采集器单元测试

测试内容：
1. 成功采集场景
2. API 错误处理
3. 超时处理
4. 空结果处理
5. 数据解析正确性
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.collectors.bocha import BochaCollector
from app.collectors.base import CollectRequest
from tests.fixtures.collectors import CollectorTestData, ExpectedResults
from tests.mocks.external_apis import BochaAPIMock, mock_httpx_client


class TestBochaCollector:
    """博查采集器测试类"""

    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        return BochaCollector(api_key="test-api-key")

    @pytest.fixture
    def collect_request(self):
        """创建采集请求"""
        return CollectRequest(
            keyword="阿里云",
            max_results=20,
            time_range="oneDay"
        )

    # ==================== 成功场景测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_success(self, collector, collect_request):
        """测试成功采集"""
        mock_response = BochaAPIMock.success_response()

        with mock_httpx_client([mock_response]):
            results = await collector.collect(collect_request)

        assert len(results) == 1
        assert results[0].title == "测试新闻标题"
        assert results[0].source_type == "bocha"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_with_real_data(self, collector, collect_request):
        """测试使用真实数据格式采集"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = CollectorTestData.BOCHA_SUCCESS_DATA

        with mock_httpx_client([mock_response]):
            results = await collector.collect(collect_request)

        assert len(results) == ExpectedResults.BOCHA_PARSED_COUNT
        assert "阿里云" in results[0].title

    # ==================== 错误处理测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_api_error_500(self, collector, collect_request):
        """测试 API 500 错误"""
        mock_response = BochaAPIMock.error_response(500, "Internal Server Error")

        with mock_httpx_client([mock_response]):
            results = await collector.collect(collect_request)

        assert results == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_api_error_401(self, collector, collect_request):
        """测试 API 认证错误"""
        mock_response = BochaAPIMock.error_response(401, "Unauthorized")

        with mock_httpx_client([mock_response]):
            results = await collector.collect(collect_request)

        assert results == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_api_error_429(self, collector, collect_request):
        """测试 API 限流错误"""
        mock_response = BochaAPIMock.error_response(429, "Rate limit exceeded")

        with mock_httpx_client([mock_response]):
            results = await collector.collect(collect_request)

        assert results == []

    # ==================== 超时测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_timeout(self, collector, collect_request):
        """测试请求超时"""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            results = await collector.collect(collect_request)

        assert results == []

    # ==================== 网络错误测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_network_error(self, collector, collect_request):
        """测试网络连接错误"""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            results = await collector.collect(collect_request)

        assert results == []

    # ==================== 空结果测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_empty_results(self, collector, collect_request):
        """测试空结果"""
        mock_response = BochaAPIMock.empty_response()

        with mock_httpx_client([mock_response]):
            results = await collector.collect(collect_request)

        assert results == []

    # ==================== 数据解析测试 ====================
    @pytest.mark.unit
    def test_parse_response_correct_fields(self, collector):
        """测试响应解析字段正确性"""
        response_data = CollectorTestData.BOCHA_SUCCESS_DATA
        results = collector._parse_response(response_data)

        assert len(results) == 2

        # 验证第一条数据
        first = results[0]
        assert first.keyword == "阿里云"
        assert first.title == "阿里云发布新产品"
        assert "云原生" in first.content
        assert first.url == "https://www.aliyun.com/announce/new-product"
        assert first.source == "阿里云官网"
        assert first.source_type == "bocha"

    @pytest.mark.unit
    def test_parse_response_with_missing_fields(self, collector):
        """测试缺失字段的响应解析"""
        response_data = {
            "query": "测试",
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "只有标题",
                            "url": "https://example.com",
                            # 缺少 summary, siteName, dateLastCrawled
                        }
                    ]
                }
            }
        }

        results = collector._parse_response(response_data)

        assert len(results) == 1
        assert results[0].title == "只有标题"
        assert results[0].content == ""  # 应该有默认值

    # ==================== 时间解析测试 ====================
    @pytest.mark.unit
    def test_parse_time_iso_format(self, collector):
        """测试 ISO 格式时间解析"""
        time_str = "2026-03-02T10:30:00"
        result = collector._parse_time(time_str)

        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 2

    @pytest.mark.unit
    def test_parse_time_empty(self, collector):
        """测试空时间字符串"""
        result = collector._parse_time("")
        assert result is None

        result = collector._parse_time(None)
        assert result is None

    @pytest.mark.unit
    def test_parse_time_invalid_format(self, collector):
        """测试无效时间格式"""
        result = collector._parse_time("invalid-time-string")
        assert result is None

    # ==================== 边界条件测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_with_special_keyword(self, collector):
        """测试特殊字符关键词"""
        request = CollectRequest(
            keyword=CollectorTestData.EDGE_CASES["special_chars"],
            max_results=10,
        )
        mock_response = BochaAPIMock.empty_response()

        with mock_httpx_client([mock_response]):
            results = await collector.collect(request)

        # 应该正常处理，不应抛出异常
        assert isinstance(results, list)
