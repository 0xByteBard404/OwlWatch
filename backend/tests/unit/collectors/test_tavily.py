# -*- coding: utf-8 -*-
"""
Tavily 采集器单元测试

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

from app.collectors.tavily import TavilyCollector
from app.collectors.base import CollectRequest
from tests.fixtures.collectors import CollectorTestData, ExpectedResults
from tests.mocks.external_apis import TavilyAPIMock, mock_httpx_client


class TestTavilyCollector:
    """Tavily 采集器测试类"""

    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        return TavilyCollector(api_key="test-tavily-api-key")

    @pytest.fixture
    def collect_request(self):
        """创建采集请求"""
        return CollectRequest(
            keyword="云计算",
            max_results=10,
        )

    # ==================== 成功场景测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_success(self, collector, collect_request):
        """测试成功采集"""
        mock_response = TavilyAPIMock.success_response()

        with mock_httpx_client([mock_response]):
            results = await collector.collect(collect_request)

        assert len(results) == 1
        assert results[0].source_type == "tavily"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_with_real_data(self, collector, collect_request):
        """测试使用真实数据格式采集"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = CollectorTestData.TAVILY_SUCCESS_DATA

        with mock_httpx_client([mock_response]):
            results = await collector.collect(collect_request)

        assert len(results) == ExpectedResults.TAVILY_PARSED_COUNT

    # ==================== 错误处理测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_api_error_401(self, collector, collect_request):
        """测试 API 认证错误"""
        mock_response = TavilyAPIMock.error_response(401)

        with mock_httpx_client([mock_response]):
            results = await collector.collect(collect_request)

        assert results == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_api_error_500(self, collector, collect_request):
        """测试 API 服务器错误"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

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

    # ==================== 数据解析测试 ====================
    @pytest.mark.unit
    def test_parse_response_correct_fields(self, collector):
        """测试响应解析字段正确性"""
        response_data = CollectorTestData.TAVILY_SUCCESS_DATA
        results = collector._parse_response(response_data)

        assert len(results) == 2

        first = results[0]
        assert first.keyword == "阿里云"
        assert first.title == "阿里云市场表现强劲"
        assert "市场份额" in first.content
        assert first.source_type == "tavily"

    @pytest.mark.unit
    def test_parse_response_with_missing_fields(self, collector):
        """测试缺失字段的响应解析"""
        response_data = {
            "query": "测试",
            "results": [
                {
                    "title": "只有标题",
                    "url": "https://example.com",
                    # 缺少 content, source, published_date
                }
            ]
        }

        results = collector._parse_response(response_data)

        assert len(results) == 1
        assert results[0].title == "只有标题"
        assert results[0].content == ""

    @pytest.mark.unit
    def test_parse_response_empty_results(self, collector):
        """测试空结果列表"""
        response_data = {"query": "测试", "results": []}
        results = collector._parse_response(response_data)

        assert results == []

    # ==================== 时间解析测试 ====================
    @pytest.mark.unit
    def test_parse_time_iso_format_with_z(self, collector):
        """测试 ISO 格式时间（带 Z）"""
        time_str = "2026-03-02T10:00:00Z"
        result = collector._parse_time(time_str)

        assert result is not None

    @pytest.mark.unit
    def test_parse_time_iso_format_with_timezone(self, collector):
        """测试 ISO 格式时间（带时区）"""
        time_str = "2026-03-02T10:00:00+08:00"
        result = collector._parse_time(time_str)

        assert result is not None

    @pytest.mark.unit
    def test_parse_time_none(self, collector):
        """测试空时间"""
        result = collector._parse_time(None)
        assert result is None

    @pytest.mark.unit
    def test_parse_time_invalid(self, collector):
        """测试无效时间格式"""
        result = collector._parse_time("not-a-date")
        assert result is None
