"""趋势分析器"""
import httpx
from typing import List, Dict
from datetime import datetime, timedelta
import json


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    async def analyze(
        self,
        articles: List[Dict],
        time_range: str = "oneWeek"
    ) -> Dict:
        """分析舆情趋势

        Args:
            articles: 文章列表 [{"title": "...", "sentiment_score": 0.5, "publish_time": "..."}]
            time_range: 时间范围 oneDay/oneWeek/oneMonth

        Returns:
            {
                "trend": "rising/falling/stable",
                "summary": "趋势描述",
                "key_events": ["事件1", "事件2"],
                "sentiment_change": "+0.2,
                "recommendation": "建议"
            }
        """
        if not articles:
            return {
                "trend": "stable",
                "summary": "暂无数据",
                "key_events": [],
                "sentiment_change": 0,
                "recommendation": "暂无建议"
            }

        # 统计基础数据
        total = len(articles)
        avg_sentiment = sum(a.get("sentiment_score", 0) for a in articles if a.get("sentiment_score")) / total

        negative_count = sum(1 for a in articles if a.get("sentiment_score", 0) < -0.3)
        positive_count = sum(1 for a in articles if a.get("sentiment_score", 0) > 0.3)

        # 准备 AI 分析的内容
        articles_summary = "\n".join([
            f"【{i+1}】{a.get('title', '')} (情感分数: {a.get('sentiment_score', 0):.1f})"
            for i, a in enumerate(articles[:20])
        ])

        prompt = f"""你是一个舆情分析专家。请分析以下舆情数据的趋势。

【时间范围】{time_range}

【舆情数据】
共 {total} 条信息
平均情感分数: {avg_sentiment:.2f}
负面信息数: {negative_count}
正面信息数: {positive_count}

【文章列表】
{articles_summary}

请返回 JSON 格式的趋势分析:
{{
    "trend": "rising/falling/stable (热度趋势),
    "summary": "趋势描述(100字以内)",
    "key_events": ["关键事件1", "关键事件2"],
    "sentiment_change": 情感变化值(-1到1),
    "recommendation": "应对建议(50字以内)"
}}
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "qwen3-max",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            data = response.json()

        content_text = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")

        try:
            result = json.loads(content_text)
            return result
        except json.JSONDecodeError:
            return {
                "trend": "stable",
                "summary": "分析失败",
                "key_events": [],
                "sentiment_change": 0,
                "recommendation": "请重新分析"
            }
