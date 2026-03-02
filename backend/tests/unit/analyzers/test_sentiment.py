# -*- coding: utf-8 -*-
"""
情感分析器单元测试

测试内容：
1. 成功分析场景
2. JSON 解析容错（Markdown 代码块）
3. API 错误处理
4. 边界条件处理
5. 批量分析功能
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.analyzers.sentiment import SentimentAnalyzer
from tests.fixtures.collectors import CollectorTestData
from tests.mocks.external_apis import SentimentAPIMock, mock_httpx_client


class TestSentimentAnalyzer:
    """情感分析器测试类"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return SentimentAnalyzer(api_key="test-bailian-api-key")

    # ==================== 成功场景测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_positive_text(self, analyzer):
        """测试正面文本分析"""
        mock_response = SentimentAPIMock.success_response(
            score=0.8, label="positive", reason="内容积极向上"
        )

        with mock_httpx_client([mock_response]):
            result = await analyzer.analyze(CollectorTestData.POSITIVE_TEXT)

        assert result["label"] == "positive"
        assert result["score"] > 0
        assert "reason" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_negative_text(self, analyzer):
        """测试负面文本分析"""
        mock_response = SentimentAPIMock.success_response(
            score=-0.7, label="negative", reason="内容消极负面"
        )

        with mock_httpx_client([mock_response]):
            result = await analyzer.analyze(CollectorTestData.NEGATIVE_TEXT)

        assert result["label"] == "negative"
        assert result["score"] < 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_neutral_text(self, analyzer):
        """测试中性文本分析"""
        mock_response = SentimentAPIMock.success_response(
            score=0.0, label="neutral", reason="内容无明显情感倾向"
        )

        with mock_httpx_client([mock_response]):
            result = await analyzer.analyze(CollectorTestData.NEUTRAL_TEXT)

        assert result["label"] == "neutral"

    # ==================== JSON 解析容错测试 ====================
    @pytest.mark.unit
    def test_extract_json_plain(self, analyzer):
        """测试直接 JSON 提取"""
        text = '{"score": 0.5, "label": "positive", "reason": "测试"}'
        result = analyzer._extract_json(text)

        parsed = json.loads(result)
        assert parsed["score"] == 0.5

    @pytest.mark.unit
    def test_extract_json_with_markdown_block(self, analyzer):
        """测试 Markdown 代码块中的 JSON 提取"""
        text = '''这是一些额外的文本
```json
{"score": 0.8, "label": "positive", "reason": "积极内容"}
```
更多文本'''

        result = analyzer._extract_json(text)
        parsed = json.loads(result)

        assert parsed["score"] == 0.8
        assert parsed["label"] == "positive"

    @pytest.mark.unit
    def test_extract_json_with_plain_block(self, analyzer):
        """测试普通代码块中的 JSON 提取"""
        text = '''```
{"score": -0.5, "label": "negative"}
```'''

        result = analyzer._extract_json(text)
        parsed = json.loads(result)

        assert parsed["label"] == "negative"

    @pytest.mark.unit
    def test_extract_json_embedded_in_text(self, analyzer):
        """测试嵌入文本中的 JSON 提取"""
        text = 'AI 返回的结果是 {"score": 0.3, "label": "neutral"} 请查收'
        result = analyzer._extract_json(text)

        parsed = json.loads(result)
        assert parsed["score"] == 0.3

    @pytest.mark.unit
    def test_extract_json_array(self, analyzer):
        """测试 JSON 数组提取"""
        text = '''```json
[
    {"score": 0.5, "label": "positive"},
    {"score": -0.3, "label": "negative"}
]
```'''

        result = analyzer._extract_json_array(text)
        parsed = json.loads(result)

        assert isinstance(parsed, list)
        assert len(parsed) == 2

    # ==================== 错误处理测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_api_error(self, analyzer):
        """测试 API 错误"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with mock_httpx_client([mock_response]):
            result = await analyzer.analyze(CollectorTestData.POSITIVE_TEXT)

        # 应该返回默认值而不是抛出异常
        assert result["label"] == "neutral"
        assert result["score"] == 0
        assert "失败" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_timeout(self, analyzer):
        """测试请求超时"""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze(CollectorTestData.POSITIVE_TEXT)

        assert result["label"] == "neutral"
        assert "超时" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_network_error(self, analyzer):
        """测试网络错误"""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze(CollectorTestData.POSITIVE_TEXT)

        assert result["label"] == "neutral"
        assert "网络" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_json_decode_error(self, analyzer):
        """测试 JSON 解析失败"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "这不是有效的JSON"}}]
        }

        with mock_httpx_client([mock_response]):
            result = await analyzer.analyze(CollectorTestData.POSITIVE_TEXT)

        assert result["label"] == "neutral"
        assert "解析" in result["reason"]

    # ==================== 边界条件测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_empty_content(self, analyzer):
        """测试空内容"""
        result = await analyzer.analyze("")

        assert result["label"] == "neutral"
        assert result["score"] == 0
        assert result["reason"] == "内容太短"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_short_content(self, analyzer):
        """测试过短内容"""
        result = await analyzer.analyze(CollectorTestData.SHORT_TEXT)

        assert result["label"] == "neutral"
        assert result["reason"] == "内容太短"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_whitespace_only(self, analyzer):
        """测试仅空白字符"""
        result = await analyzer.analyze("   \n\t  ")

        assert result["label"] == "neutral"
        assert result["reason"] == "内容太短"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_special_characters(self, analyzer):
        """测试特殊字符"""
        mock_response = SentimentAPIMock.success_response()

        with mock_httpx_client([mock_response]):
            result = await analyzer.analyze(CollectorTestData.EDGE_CASES["special_chars"])

        # 不应抛出异常
        assert "label" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_unicode_content(self, analyzer):
        """测试 Unicode 内容"""
        mock_response = SentimentAPIMock.success_response()

        with mock_httpx_client([mock_response]):
            result = await analyzer.analyze(CollectorTestData.EDGE_CASES["unicode_content"])

        assert "label" in result

    # ==================== 批量分析测试 ====================
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_analyze_success(self, analyzer):
        """测试批量分析成功"""
        contents = [
            CollectorTestData.POSITIVE_TEXT,
            CollectorTestData.NEGATIVE_TEXT,
            CollectorTestData.NEUTRAL_TEXT,
        ]
        mock_response = SentimentAPIMock.batch_response(len(contents))

        with mock_httpx_client([mock_response]):
            results = await analyzer.batch_analyze(contents)

        assert len(results) == len(contents)
        for r in results:
            assert "score" in r
            assert "label" in r

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_analyze_empty_list(self, analyzer):
        """测试空列表批量分析"""
        results = await analyzer.batch_analyze([])
        assert results == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_analyze_api_error(self, analyzer):
        """测试批量分析 API 错误"""
        contents = ["内容1", "内容2"]
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"

        with mock_httpx_client([mock_response]):
            results = await analyzer.batch_analyze(contents)

        # 应该返回默认值
        assert len(results) == len(contents)
        for r in results:
            assert r["label"] == "neutral"

    @pytest.mark.unit
    def test_extract_json_array_from_text(self, analyzer):
        """测试从文本中提取 JSON 数组"""
        text = '结果为 [{"score": 0.5}, {"score": -0.3}]'
        result = analyzer._extract_json_array(text)

        parsed = json.loads(result)
        assert isinstance(parsed, list)
