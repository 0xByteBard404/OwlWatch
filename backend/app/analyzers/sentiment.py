"""情感分析器 - 基于百炼 qwen3-max"""
import httpx
import logging
import re
from typing import Optional
import json

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """情感分析器"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    async def analyze(self, content: str) -> dict:
        """分析内容情感

        Args:
            content: 待分析文本

        Returns:
            {"score": -1~1, "label": "positive/neutral/negative", "reason": "..."}
        """
        if not content or len(content.strip()) < 10:
            return {"score": 0, "label": "neutral", "reason": "内容太短"}

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
            "model": "qwen3-max",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 200
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    logger.error(f"Sentiment API error: status={response.status_code}, body={response.text[:500]}")
                    return {"score": 0, "label": "neutral", "reason": "API调用失败"}

                data = response.json()

            # 解析响应
            content_text = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")

            # 清理 AI 返回内容（可能包含 ```json ... ```）
            cleaned = self._extract_json(content_text)
            result = json.loads(cleaned)
            return result
        except httpx.TimeoutException:
            logger.error("Sentiment API timeout")
            return {"score": 0, "label": "neutral", "reason": "API超时"}
        except httpx.RequestError as e:
            logger.error(f"Sentiment API request error: {e}")
            return {"score": 0, "label": "neutral", "reason": "网络错误"}
        except json.JSONDecodeError as e:
            logger.error(f"Sentiment JSON decode error: {e}")
            return {"score": 0, "label": "neutral", "reason": "JSON解析失败"}
        except Exception as e:
            logger.error(f"Sentiment analyze error: {e}")
            return {"score": 0, "label": "neutral", "reason": "分析失败"}

    def _extract_json(self, text: str) -> str:
        """从 AI 返回内容中提取 JSON（处理 markdown 代码块）"""
        text = text.strip()

        # 尝试匹配 ```json ... ``` 或 ``` ... ```
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json_match.group(1).strip()

        # 尝试匹配 { ... } 对象
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            return brace_match.group(0)

        return text

    async def batch_analyze(self, contents: list[str]) -> list[dict]:
        """批量分析

        将多条内容合并为一次 API 调用以节省成本
        """
        if not contents:
            return []

        # 合并内容
        combined = "\n---\n".join([f"【{i+1}】{c[:1000]}" for i, c in enumerate(contents)])
        prompt = f"""你是一个专业的舆情分析师。请分析以下{len(contents)}条内容的情感倾向。

重要判断标准：
1. 仅仅是报道事实（如公司财报、产品发布）应判断为"neutral"
2. 只有当文章明确批评、指责、曝光负面问题，或报道该主体的违法违规行为时，才判断为"negative"
3. 当文章赞扬、推荐、正面评价该主体时，判断为"positive"

【内容】
{combined}

请返回严格的 JSON 数组格式（不要包含其他文字）:
[{{"score": -1到1的数字, "label": "positive或neutral或negative"}}, ...]"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "qwen3-max",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    logger.error(f"Sentiment batch API error: status={response.status_code}")
                    return [{"score": 0, "label": "neutral"} for _ in contents]

                data = response.json()

            content_text = data.get("choices", [{}])[0].get("message", {}).get("content", "[]")

            # 清理并解析 JSON
            cleaned = self._extract_json_array(content_text)
            results = json.loads(cleaned)
            return results
        except httpx.TimeoutException:
            logger.error("Sentiment batch API timeout")
            return [{"score": 0, "label": "neutral"} for _ in contents]
        except httpx.RequestError as e:
            logger.error(f"Sentiment batch API request error: {e}")
            return [{"score": 0, "label": "neutral"} for _ in contents]
        except json.JSONDecodeError as e:
            logger.error(f"Sentiment batch JSON decode error: {e}")
            return [{"score": 0, "label": "neutral"} for _ in contents]
        except Exception as e:
            logger.error(f"Sentiment batch analyze error: {e}")
            return [{"score": 0, "label": "neutral"} for _ in contents]

    def _extract_json_array(self, text: str) -> str:
        """从 AI 返回内容中提取 JSON 数组"""
        text = text.strip()

        # 尝试匹配 ```json ... ``` 或 ``` ... ```
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json_match.group(1).strip()

        # 尝试匹配 [ ... ] 数组
        bracket_match = re.search(r'\[[\s\S]*\]', text)
        if bracket_match:
            return bracket_match.group(0)

        return text
