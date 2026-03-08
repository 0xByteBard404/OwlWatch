# -*- coding: utf-8 -*-
"""
默认情感关键词词库

覆盖常见舆情场景：法律风险、财务风险、品牌危机、人事变动等
"""

DEFAULT_SENTIMENT_KEYWORDS = [
    # ==================== 负面关键词 ====================
    # 法律风险
    {"keyword": "投诉", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "维权", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "欺诈", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "诈骗", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "诉讼", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "被告", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "违法", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "违规", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "处罚", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "罚款", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "立案", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "查封", "sentiment_type": "negative", "category": "法律风险"},
    {"keyword": "冻结", "sentiment_type": "negative", "category": "法律风险"},
    
    # 财务风险
    {"keyword": "破产", "sentiment_type": "negative", "category": "财务风险"},
    {"keyword": "亏损", "sentiment_type": "negative", "category": "财务风险"},
    {"keyword": "债务", "sentiment_type": "negative", "category": "财务风险"},
    {"keyword": "违约", "sentiment_type": "negative", "category": "财务风险"},
    {"keyword": "暴雷", "sentiment_type": "negative", "category": "财务风险"},
    {"keyword": "崩盘", "sentiment_type": "negative", "category": "财务风险"},
    {"keyword": "跌停", "sentiment_type": "negative", "category": "财务风险"},
    {"keyword": "退市", "sentiment_type": "negative", "category": "财务风险"},
    {"keyword": "做空", "sentiment_type": "negative", "category": "财务风险"},
    {"keyword": "造假", "sentiment_type": "negative", "category": "财务风险"},
    {"keyword": "虚增", "sentiment_type": "negative", "category": "财务风险"},
    
    # 品牌危机
    {"keyword": "召回", "sentiment_type": "negative", "category": "品牌危机"},
    {"keyword": "质量问题", "sentiment_type": "negative", "category": "品牌危机"},
    {"keyword": "缺陷", "sentiment_type": "negative", "category": "品牌危机"},
    {"keyword": "安全隐患", "sentiment_type": "negative", "category": "品牌危机"},
    {"keyword": "事故", "sentiment_type": "negative", "category": "品牌危机"},
    {"keyword": "虚假宣传", "sentiment_type": "negative", "category": "品牌危机"},
    {"keyword": "误导", "sentiment_type": "negative", "category": "品牌危机"},
    {"keyword": "抄袭", "sentiment_type": "negative", "category": "品牌危机"},
    {"keyword": "侵权", "sentiment_type": "negative", "category": "品牌危机"},
    {"keyword": "抵制", "sentiment_type": "negative", "category": "品牌危机"},
    {"keyword": "下架", "sentiment_type": "negative", "category": "品牌危机"},
    
    # 人事变动
    {"keyword": "裁员", "sentiment_type": "negative", "category": "人事变动"},
    {"keyword": "欠薪", "sentiment_type": "negative", "category": "人事变动"},
    {"keyword": "离职潮", "sentiment_type": "negative", "category": "人事变动"},
    {"keyword": "内斗", "sentiment_type": "negative", "category": "人事变动"},
    {"keyword": "辞职", "sentiment_type": "negative", "category": "人事变动"},
    {"keyword": "解雇", "sentiment_type": "negative", "category": "人事变动"},
    
    # 负面舆论
    {"keyword": "丑闻", "sentiment_type": "negative", "category": "负面舆论"},
    {"keyword": "曝光", "sentiment_type": "negative", "category": "负面舆论"},
    {"keyword": "质疑", "sentiment_type": "negative", "category": "负面舆论"},
    {"keyword": "争议", "sentiment_type": "negative", "category": "负面舆论"},
    {"keyword": "负面", "sentiment_type": "negative", "category": "负面舆论"},
    {"keyword": "危机", "sentiment_type": "negative", "category": "负面舆论"},
    {"keyword": "舆情", "sentiment_type": "negative", "category": "负面舆论"},
    {"keyword": "网暴", "sentiment_type": "negative", "category": "负面舆论"},
    
    # ==================== 正面关键词 ====================
    # 品牌形象
    {"keyword": "创新", "sentiment_type": "positive", "category": "品牌形象"},
    {"keyword": "获奖", "sentiment_type": "positive", "category": "品牌形象"},
    {"keyword": "领先", "sentiment_type": "positive", "category": "品牌形象"},
    {"keyword": "突破", "sentiment_type": "positive", "category": "品牌形象"},
    {"keyword": "首发", "sentiment_type": "positive", "category": "品牌形象"},
    {"keyword": "独家", "sentiment_type": "positive", "category": "品牌形象"},
    {"keyword": "标杆", "sentiment_type": "positive", "category": "品牌形象"},
    {"keyword": "典范", "sentiment_type": "positive", "category": "品牌形象"},
    
    # 财务利好
    {"keyword": "盈利", "sentiment_type": "positive", "category": "财务利好"},
    {"keyword": "增长", "sentiment_type": "positive", "category": "财务利好"},
    {"keyword": "涨停", "sentiment_type": "positive", "category": "财务利好"},
    {"keyword": "翻倍", "sentiment_type": "positive", "category": "财务利好"},
    {"keyword": "新高", "sentiment_type": "positive", "category": "财务利好"},
    {"keyword": "超预期", "sentiment_type": "positive", "category": "财务利好"},
    
    # 商业合作
    {"keyword": "合作", "sentiment_type": "positive", "category": "商业合作"},
    {"keyword": "签约", "sentiment_type": "positive", "category": "商业合作"},
    {"keyword": "战略", "sentiment_type": "positive", "category": "商业合作"},
    {"keyword": "并购", "sentiment_type": "positive", "category": "商业合作"},
    {"keyword": "投资", "sentiment_type": "positive", "category": "商业合作"},
    {"keyword": "融资", "sentiment_type": "positive", "category": "商业合作"},
    
    # 社会责任
    {"keyword": "公益", "sentiment_type": "positive", "category": "社会责任"},
    {"keyword": "捐赠", "sentiment_type": "positive", "category": "社会责任"},
    {"keyword": "环保", "sentiment_type": "positive", "category": "社会责任"},
    {"keyword": "可持续发展", "sentiment_type": "positive", "category": "社会责任"},
    {"keyword": "社会责任", "sentiment_type": "positive", "category": "社会责任"},
]

# 统计信息
KEYWORD_STATS = {
    "total": len(DEFAULT_SENTIMENT_KEYWORDS),
    "negative": len([k for k in DEFAULT_SENTIMENT_KEYWORDS if k["sentiment_type"] == "negative"]),
    "positive": len([k for k in DEFAULT_SENTIMENT_KEYWORDS if k["sentiment_type"] == "positive"]),
    "categories": list(set(k["category"] for k in DEFAULT_SENTIMENT_KEYWORDS)),
}
