# -*- coding: utf-8 -*-
"""
情感分析器 - 整合 HanLP + Cemotion + 情感关键词库

功能:
1. HanLP: 分词、命名实体识别、关键词提取
2. Cemotion: 整体情感倾向分析
3. 情感关键词库: 正面/负面关键词匹配
4. 综合评分: 结合多维度给出最终情感判断
"""
import logging
import re
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """情感分析器 - 整合 HanLP + Cemotion + 情感关键词库"""

    def __init__(self, api_key: Optional[str] = None, use_local: bool = True):
        """
        初始化情感分析器

        Args:
            api_key: API密钥（保留兼容性，但优先使用本地方案）
            use_local: 是否使用本地分析（默认True）
        """
        self.api_key = api_key
        self.use_local = use_local
        self.hanlp = None
        self.cemotion = None
        self._initialized = False

    def _init(self):
        """延迟初始化 - 首次使用时加载模型"""
        if self._initialized:
            return

        try:
            import hanlp
            # 使用轻量级模型
            self.hanlp = hanlp.load(
                model='FINE_ELECTRA_SMALL_ZH',
                tasks=['ner', 'pos', 'tok', 'lemma'],
            )
            logger.info("HanLP 初始化成功")
        except Exception as e:
            logger.warning(f"HanLP 初始化失败: {e}")
            self.hanlp = None

        try:
            from Cemotion import Cemotion
            self.cemotion = Cemotion()
            logger.info("Cemotion 初始化成功")
        except Exception as e:
            logger.warning(f"Cemotion 初始化失败: {e}")
            self.cemotion = None

        self._initialized = True

    async def analyze(self, content: str, positive_keywords: List[str] = None, negative_keywords: List[str] = None) -> dict:
        """
        分析内容情感

        Args:
            content: 待分析文本
            positive_keywords: 正面关键词列表（从数据库加载）
            negative_keywords: 负面关键词列表（从数据库加载）

        Returns:
            {
                "score": -1~1,
                "label": "positive/neutral/negative",
                "reason": "...",
                "matched_positive": [...],
                "matched_negative": [...],
                "entities": [...]
            }
        """
        # 凶迟初始化
        self._init()

        if not content or len(content.strip()) < 10:
            return {"score": 0, "label": "neutral", "reason": "内容太短"}

        # 文本预处理
        text = self._preprocess_text(content)

        # 1. HanLP 分析
        hanlp_result = self._hanlp_analyze(text)

        # 2. 关键词匹配
        matched_positive, matched_negative = self._match_keywords(
            text, positive_keywords or [], negative_keywords or []
        )

        # 3. Cemotion 情感分析
        emotion_result = self._cemotion_analyze(text)

        # 4. 综合评分
        final_result = self._calculate_final_score(
            matched_positive, matched_negative, emotion_result, hanlp_result
        )

        return {
            "score": final_result["score"],
            "label": final_result["label"],
            "reason": final_result["reason"],
            "matched_positive": matched_positive,
            "matched_negative": matched_negative,
            "entities": hanlp_result.get("entities", []),
        }

    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        if not text:
            return ""
        # 去除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 去除特殊字符，保留中文、英文、数字、标点
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\u3000-\u303f\uff0c.,!?;:\'""]+', ' ', text)
        # 合并多个空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _hanlp_analyze(self, text: str) -> dict:
        """HanLP 分析 - 分词 + 命名实体识别"""
        result = {
            'tokens': [],
            'entities': [],
            'pos_tags': [],
        }

        if not text or not self.hanlp:
            return result

        try:
            # 分词
            tokens = list(self.hanlp.segment(text))
            result['tokens'] = [str(t) for t in tokens]

            # 命名实体识别
            try:
                ner_result = self.hanlp.ner(text)
                for entity in ner_result:
                    entity_text = entity.get('text', '') or entity.get('entity', '')
                    entity_type = entity.get('type', 'UNKNOWN')
                    if entity_text:
                        result['entities'].append({
                            'text': entity_text,
                            'type': entity_type
                        })
            except Exception as e:
                logger.debug(f"NER failed: {e}")

            # 词性标注
            try:
                pos_result = self.hanlp.pos(text)
                result['pos_tags'] = [(str(w), tag) for w, tag in zip(pos_result, pos_result[1])]
            except Exception as e:
                logger.debug(f"POS failed: {e}")

        except Exception as e:
            logger.error(f"HanLP analyze error: {e}")

        return result

    def _match_keywords(
        self,
        text: str,
        positive_keywords: List[str],
        negative_keywords: List[str]
    ) -> tuple:
        """关键词匹配"""
        matched_positive = []
        matched_negative = []

        if not text:
            return matched_positive, matched_negative

        text_lower = text.lower()

        # 匹配正面关键词
        for kw in positive_keywords:
            if kw.lower() in text_lower:
                matched_positive.append(kw)

        # 匹配负面关键词
        for kw in negative_keywords:
            if kw.lower() in text_lower:
                matched_negative.append(kw)

        return matched_positive, matched_negative

    def _cemotion_analyze(self, text: str) -> dict:
        """Cemotion 情感分析"""
        if not text or not self.cemotion:
            return {"score": 0, "label": "neutral", "confidence": 0}

        try:
            # Cemotion 的 predict() 返回字符串: "正面", "负面", "中性"
            sentiment_str = self.cemotion.predict(text)

            # 将字符串结果转换为数值分数
            if sentiment_str == "正面":
                return {"score": 0.6, "label": "positive", "confidence": 0.7}
            elif sentiment_str == "负面":
                return {"score": -0.6, "label": "negative", "confidence": 0.7}
            else:
                return {"score": 0, "label": "neutral", "confidence": 0.5}
        except Exception as e:
            logger.error(f"Cemotion analyze error: {e}")
            return {"score": 0, "label": "neutral", "confidence": 0}

    def _calculate_final_score(
        self,
        matched_positive: List[str],
        matched_negative: List[str],
        emotion_result: dict,
        hanlp_result: dict
    ) -> dict:
        """
        综合评分算法

        权重分配:
        - 关键词匹配: 40%
        - Cemotion情感分: 60%
        """
        # 1. 关键词得分
        keyword_score = 0.0
        keyword_score += len(matched_positive) * 0.15  # 每个正面词 +0.15
        keyword_score -= len(matched_negative) * 0.15  # 每个负面词 -0.15
        keyword_score = max(-1.0, min(1.0, keyword_score))  # 限制在 -1.0 ~ 1.0

        # 2. 情感分
        emotion_score = emotion_result.get('score', 0.0)

        # 3. 综合计算
        # 权重: 关键词 40%, 情感 60%
        final_score = keyword_score * 0.4 + emotion_score * 0.6

        # 4. 置信度计算
        confidence = 0.5  # 基础置信度
        if matched_positive or matched_negative:
            confidence += 0.2
        if emotion_result.get('score', 0) != 0:
            confidence += 0.2
        if hanlp_result.get('entities'):
            confidence += 0.1
        confidence = min(1.0, confidence)

        # 5. 最终判断
        if final_score > 0.2:
            sentiment_type = 'positive'
            reason = f"综合评分 {final_score:.2f}，正面关键词: {matched_positive}"
        elif final_score < -0.2:
            sentiment_type = 'negative'
            reason = f"综合评分 {final_score:.2f}，负面关键词: {matched_negative}"
        else:
            sentiment_type = 'neutral'
            reason = f"综合评分 {final_score:.2f}"

        return {
            'score': round(final_score, 3),
            'label': sentiment_type,
            'reason': reason,
            'confidence': round(confidence, 2)
        }

    async def batch_analyze(self, contents: List[str]) -> List[dict]:
        """批量分析"""
        if not contents:
            return []

        results = []
        for content in contents:
            result = await self.analyze(content)
            results.append(result)
        return results

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
