"""情感分析器 - 支持本地免费分析（snownlp）和 API 分析"""
import logging
from typing import Optional
from snownlp import SnowNLP

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """情感分析器 - 默认使用本地免费方案"""

    def __init__(self, api_key: Optional[str] = None, use_local: bool = True):
        """
        初始化情感分析器

        Args:
            api_key: API密钥（可选，用于云服务）
            use_local: 是否使用本地分析（默认True，完全免费）
        """
        self.api_key = api_key
        self.use_local = use_local

    async def analyze(self, content: str) -> dict:
        """分析内容情感

        Args:
            content: 待分析文本

        Returns:
            {"score": -1~1, "label": "positive/neutral/negative", "reason": "..."}
        """
        if not content or len(content.strip()) < 10:
            return {"score": 0, "label": "neutral", "reason": "内容太短"}

        if self.use_local:
            return await self._local_analyze(content)
        else:
            return await self._api_analyze(content)

    async def _local_analyze(self, content: str) -> dict:
        """使用 snownlp 本地分析（免费）"""
        try:
            # 清理 HTML 标签
            import re
            clean_content = re.sub(r'<[^>]+>', '', content)

            s = SnowNLP(clean_content[:2000])  # 限制长度
            score = s.sentiments  # 返回 0-1，0.5 为中性

            # 转换为 -1 到 1 的范围
            normalized_score = (score - 0.5) * 2

            # 判断标签
            if score > 0.6:
                label = "positive"
                reason = "正面情感"
            elif score < 0.4:
                label = "negative"
                reason = "负面情感"
            else:
                label = "neutral"
                reason = "中性情感"

            return {
                "score": round(normalized_score, 3),
                "label": label,
                "reason": reason
            }
        except Exception as e:
            logger.error(f"Local sentiment analyze error: {e}")
            return {"score": 0, "label": "neutral", "reason": "分析失败"}

    async def _api_analyze(self, content: str) -> dict:
        """使用 API 分析（需要 api_key）"""
        import httpx
        import json

        if not self.api_key:
            logger.warning("No API key provided, falling back to local analysis")
            return await self._local_analyze(content)

        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

        prompt = f"""你是一个专业的舆情分析师。请分析以下新闻报道或文章的情感倾向。

重要判断标准：
1. 判断这篇文章对文中提到的主要主体（公司/品牌/人物）的态度是正面、中性还是负面
2. 仅仅是报道事实（如公司财报、产品发布、行业动态）应判断为"neutral"
3. 只有当文章明确批评、指责、曝光负面问题，或报道该主体的违法违规行为时，才判断为"negative"
4. 当文章赞扬、推荐、正面评价该主体时，判断为"positive"
5. 不要仅仅因为文章中出现"违规"、"处罚"等词汇就判断为负面，要看这些是否针对监控的主体

【内容】
{content[:3000]}

请返回严格的 JSON 格式（不要包含其他文字）:
{{"score": 情感分数(-1到1的数字，-1最负面，0中性，1最正面), "label": "positive或neutral或negative", "reason": "判断理由(20字以内)"}}"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "qwen-turbo",  # 使用更便宜的 qwen-turbo
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 200
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(base_url, headers=headers, json=payload)

                if response.status_code != 200:
                    logger.error(f"Sentiment API error: status={response.status_code}")
                    return {"score": 0, "label": "neutral", "reason": "API调用失败"}

                data = response.json()

            content_text = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            cleaned = self._extract_json(content_text)
            result = json.loads(cleaned)
            return result
        except Exception as e:
            logger.error(f"Sentiment API analyze error: {e}")
            return {"score": 0, "label": "neutral", "reason": "分析失败"}

    def _extract_json(self, text: str) -> str:
        """从 AI 返回内容中提取 JSON"""
        import re
        text = text.strip()

        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json_match.group(1).strip()

        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            return brace_match.group(0)

        return text

    async def batch_analyze(self, contents: list[str]) -> list[dict]:
        """批量分析"""
        if not contents:
            return []

        # 使用本地分析处理批量（更快且免费）
        results = []
        for content in contents:
            result = await self._local_analyze(content)
            results.append({"score": result["score"], "label": result["label"]})
        return results
