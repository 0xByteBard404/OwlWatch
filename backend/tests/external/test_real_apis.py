# -*- coding: utf-8 -*-
"""
真实外部 API 测试

这些测试会调用真实的 API，需要：
1. 在 .env 中配置有效的 API Key
2. 使用 pytest -m external 手动运行

运行方式：
    pytest tests/external/test_real_apis.py -v -m external
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.collectors.bocha import BochaCollector
from app.collectors.tavily import TavilyCollector
from app.analyzers.sentiment import SentimentAnalyzer
from app.collectors.base import CollectRequest
from app.config import settings


# ==================== 博查 API 真实测试 ====================
@pytest.mark.external
@pytest.mark.asyncio
@pytest.mark.skipif(not settings.bocha_api_key, reason="需要配置 BOCHA_API_KEY")
async def test_bocha_real_api():
    """测试真实的博查 API"""
    collector = BochaCollector(settings.bocha_api_key)

    request = CollectRequest(
        keyword="阿里云",
        max_results=5,
        time_range="oneDay"
    )

    results = await collector.collect(request)

    print(f"\n博查 API 返回 {len(results)} 条结果")
    for r in results[:3]:
        print(f"  - {r.title[:50]}...")

    assert isinstance(results, list)
    # 注意：真实 API 可能返回空结果，所以不强制要求 len > 0


# ==================== Tavily API 真实测试 ====================
@pytest.mark.external
@pytest.mark.asyncio
@pytest.mark.skipif(not settings.tavily_api_key, reason="需要配置 TAVILY_API_KEY")
async def test_tavily_real_api():
    """测试真实的 Tavily API"""
    collector = TavilyCollector(settings.tavily_api_key)

    request = CollectRequest(
        keyword="云计算",
        max_results=5
    )

    results = await collector.collect(request)

    print(f"\nTavily API 返回 {len(results)} 条结果")
    for r in results[:3]:
        print(f"  - {r.title[:50]}...")

    assert isinstance(results, list)


# ==================== 情感分析 API 真实测试 ====================
@pytest.mark.external
@pytest.mark.asyncio
@pytest.mark.skipif(not settings.bailian_api_key, reason="需要配置 BAILIAN_API_KEY")
async def test_sentiment_real_api():
    """测试真实的百炼情感分析 API"""
    analyzer = SentimentAnalyzer(settings.bailian_api_key)

    test_text = """
    阿里云今日发布了季度财报，营收增长超过预期。
    云计算业务表现优异，客户满意度达到历史新高。
    """

    result = await analyzer.analyze(test_text)

    print(f"\n情感分析结果:")
    print(f"  - 分数: {result['score']}")
    print(f"  - 标签: {result['label']}")
    print(f"  - 理由: {result.get('reason', 'N/A')}")

    assert "score" in result
    assert "label" in result
    assert result["label"] in ["positive", "negative", "neutral"]


# ==================== 完整链路真实测试 ====================
@pytest.mark.external
@pytest.mark.asyncio
@pytest.mark.skipif(
    not all([settings.bocha_api_key, settings.bailian_api_key]),
    reason="需要配置 BOCHA_API_KEY 和 BAILIAN_API_KEY"
)
async def test_full_pipeline_real_apis():
    """测试完整的真实链路：采集 → 分析"""
    collector = BochaCollector(settings.bocha_api_key)
    analyzer = SentimentAnalyzer(settings.bailian_api_key)

    # Step 1: 采集
    request = CollectRequest(keyword="人工智能", max_results=3)
    results = await collector.collect(request)

    print(f"\n采集到 {len(results)} 条文章")

    # Step 2: 分析
    for i, article in enumerate(results[:2]):
        if article.content and len(article.content) > 20:
            analysis = await analyzer.analyze(article.content)
            print(f"\n文章 {i+1}: {article.title[:30]}...")
            print(f"  情感: {analysis['label']} ({analysis['score']})")

    print("\n[OK] 真实 API 链路测试完成")
