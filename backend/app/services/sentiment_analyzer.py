# -*- coding: utf-8 -*-
"""
情感分析服务 - 整合 HanLP + Cemotion + 情感关键词库

功能:
1. HanLP: 分词、命名实体识别、关键词提取
2. Cemotion: 整体情感倾向分析
3. 情感关键词库: 正面/负面关键词匹配
4. 综合评分: 结合多维度给出最终情感判断
"""
import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """情感分析器 - 整合 HanLP + Cemotion + 情感关键词库"""

    def __init__(self):
        self.hanlp = None
        self.cemotion = None
        self._initialized = False

    def _init(self):
        """延迟初始化 (首次使用时加载)"""
        if self._initialized:
            return

        try:
            import hanlp
            self.hanlp = hanlp.load(
                model='FINE_ELECTRA_SMALL_ZH',
                tasks=['ner', 'pos', 'tok', 'lemma'],
            )
            logger.info("HanLP 初始化成功")
        except Exception as e:
            logger.warning(f"HanLP 初始化失败，使用备用方案: {e}")
            self.hanlp = None

        try:
            from Cemotion import Cemotion
            self.cemotion = Cemotion()
            logger.info("Cemotion 初始化成功")
        except Exception as e:
            logger.warning(f"Cemotion 初始化失败，使用备用方案: {e}")
            self.cemotion = None

        self._initialized = True

    def analyze(
        self,
        text: str,
        positive_keywords: List[str] = None,
        negative_keywords: List[str] = None,
        company_names: List[str] = None,
    ) -> Dict[str, Any]:
        """
        综合情感分析

        Args:
            text: 待分析文本
            positive_keywords: 正面关键词列表
            negative_keywords: 负面关键词列表
            company_names: 公司名称列表 (用于实体识别)

        Returns:
            {
                'sentiment_type': 'positive' | 'negative' | 'neutral',
                'sentiment_score': float (-1.0 ~ 1.0),
                'confidence': float (0.0 ~ 1.0),
                'matched_positive': List[str],
                'matched_negative': List[str],
                'named_entities': List[Dict],
                'analysis_details': Dict
            }
        """
        self._init()

        # 1. 文本预处理
        cleaned_text = self._preprocess_text(text)

        # 2. HanLP 分词和命名实体识别
        hanlp_result = self._hanlp_analyze(cleaned_text)

        # 3. 情感关键词匹配
        matched_positive = self._match_keywords(cleaned_text, positive_keywords or [])
        matched_negative = self._match_keywords(cleaned_text, negative_keywords or [])

        # 4. Cemotion 情感分析
        emotion_result = self._cemotion_analyze(cleaned_text)

        # 5. 综合评分
        final_result = self._calculate_final_score(
            matched_positive=matched_positive,
            matched_negative=matched_negative,
            emotion_result=emotion_result,
            hanlp_result=hanlp_result,
        )

        return {
            'sentiment_type': final_result['sentiment_type'],
            'sentiment_score': final_result['sentiment_score'],
            'confidence': final_result['confidence'],
            'matched_positive': matched_positive,
            'matched_negative': matched_negative,
            'named_entities': hanlp_result.get('entities', []),
            'analysis_details': {
                'emotion_score': emotion_result.get('score', 00),
                'positive_count': len(matched_positive),
                'negative_count': len(matched_negative),
                'entity_count': len(hanlp_result.get('entities', [])),
            }
        }

    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        if not text:
            return ""

        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 去除特殊字符， 保留中文、英文、数字和标点
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\u3000-\u303f\uff0c.,!?;:\'""]+', ' ', text)
        # 合并多个空格
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _hanlp_analyze(self, text: str) -> Dict:
        """HanLP 分析: 分词 + 命名实体识别"""
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
                            'type': entity_type,
                        })
            except Exception as e:
                logger.debug(f"NER 分析失败: {e}")

        except Exception as e:
            logger.warning(f"HanLP 分析失败: {e}")

        return result

    def _cemotion_analyze(self, text: str) -> Dict:
        """Cemotion 情感分析"""
        result = {
            'score': 0.0,
            'sentiment': 'neutral',
        }

        if not text or not self.cemotion:
            return result

        try:
            # Cemotion 的 predict() 返回字符串: "正面", "负面", "中性"
            sentiment_str = self.cemotion.predict(text)

            # 将字符串结果转换为数值分数
            if sentiment_str == "正面":
                result['score'] = 0.6
                result['sentiment'] = 'positive'
            elif sentiment_str == "负面":
                result['score'] = -0.6
                result['sentiment'] = 'negative'
            else:
                result['score'] = 0.0
                result['sentiment'] = 'neutral'

        except Exception as e:
            logger.warning(f"Cemotion 分析失败: {e}")

        return result

    def _match_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """匹配情感关键词"""
        matched = []
        if not text or not keywords:
            return matched

        text_lower = text.lower()
        for keyword in keywords:
            if not keyword:
                continue
            keyword_lower = keyword.lower().strip()
            if keyword_lower in text_lower:
                matched.append(keyword)

        return list(set(matched))  # 去重

    def _calculate_final_score(
        self,
        matched_positive: List[str],
        matched_negative: List[str],
        emotion_result: Dict,
        hanlp_result: Dict,
    ) -> Dict:
        """
        综合评分算法

        评分维度:
        1. 关键词匹配 (权重 40%)
           - 正面关键词 +0.1 每个
           - 负面关键词 -0.1 每个
        2. Cemotion 情感分 (权重 40%)
           - 直接使用原始分数 (-1.0 ~ 1.0)
        3. 命名实体影响 (权重 20%)
           - 如果实体出现在上下文中，影响最终判断
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
            confidence += 0.2  # 有关键词匹配增加置信度
        if emotion_result.get('score', 0) != 0:
            confidence += 0.2  # 有情感分析结果增加置信度
        if hanlp_result.get('entities'):
            confidence += 0.1  # 有实体识别增加置信度
        confidence = min(1.0, confidence)

        # 5. 最终判断
        if final_score > 0.2:
            sentiment_type = 'positive'
        elif final_score < -0.2:
            sentiment_type = 'negative'
        else:
            sentiment_type = 'neutral'

        return {
            'sentiment_type': sentiment_type,
            'sentiment_score': round(final_score, 3),
            'confidence': round(confidence, 2),
        }


# 单例实例
_analyzer_instance: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """获取情感分析器单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = SentimentAnalyzer()
    return _analyzer_instance
