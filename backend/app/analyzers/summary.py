"""摘要生成器"""
import httpx
from typing import List
import json


class SummaryGenerator:
    """摘要生成器"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    async def generate(self, articles: List[dict], max_length: int = 200) -> str:
        """生成舆情摘要

        Args:
            articles: 文章列表 [{"title": "...", "content": "..."}]
            max_length: 最大长度

        Returns:
            摘要文本
        """
        if not articles:
            return "暂无数据"

        # 拼接文章内容
        content_text = "\n".join([
            f"【{i+1}】标题: {a.get('title', '')}\n内容: {a.get('content', '')[:500]}"
            for i, a in enumerate(articles[:10])  # 最多10条
        ])

        prompt = f"""你是一个舆情分析专家。请根据以下舆情内容生成一份简洁的摘要。

【舆情内容】
{content_text}

要求:
1. 总结核心观点和趋势
2. 突出重要事件或变化
3. 字数控制在{max_length}字以内

只输出摘要内容，不要其他解释。"""

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
            "max_tokens": max_length * 2
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            data = response.json()

        return data.get("choices", [{}])[0].get("message", {}).get("content", "生成失败")
