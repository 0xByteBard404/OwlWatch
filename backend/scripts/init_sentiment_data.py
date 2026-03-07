# -*- coding: utf-8 -*-
"""初始化情感关键词数据"""
import uuid
import sys
sys.path.insert(0, '/app')
from app.database import SessionLocal
from app.models.sentiment_keyword import SentimentKeyword

def init_data():
    db = SessionLocal()

    # 创建正面关键词
    positive_data = [
        ('融资', '财务'),
        ('上市', '财务'),
        ('并购', '财务'),
        ('收购', '财务'),
        ('盈利', '财务'),
        ('增长', '经营'),
        ('突破', '技术'),
        ('创新', '技术'),
        ('获奖', '荣誉'),
        ('合作', '经营'),
        ('签约', '经营'),
        ('投资', '财务'),
    ]

    for keyword, category in positive_data:
        kw = SentimentKeyword(
            id=str(uuid.uuid4()),
            keyword=keyword,
            sentiment_type='positive',
            category=category,
            is_active=True
        )
        db.add(kw)

    # 创建负面关键词
    negative_data = [
        ('违约', '法律'),
        ('投诉', '法律'),
        ('诈骗', '法律'),
        ('欺诈', '法律'),
        ('跑路', '经营'),
        ('倒闭', '经营'),
        ('破产', '经营'),
        ('起诉', '法律'),
        ('违法', '法律'),
        ('违规', '法律'),
        ('非法', '法律'),
        ('涉案', '法律'),
        ('被查', '法律'),
        ('处罚', '法律'),
        ('罚款', '法律'),
        ('曝光', '舆情'),
        ('黑幕', '舆情'),
        ('内幕', '舆情'),
        ('传销', '经营'),
    ]

    for keyword, category in negative_data:
        kw = SentimentKeyword(
            id=str(uuid.uuid4()),
            keyword=keyword,
            sentiment_type='negative',
            category=category,
            is_active=True
        )
        db.add(kw)

    db.commit()
    print(f'✓ 创建了 {len(positive_data)} 个正面关键词')
    print(f'✓ 创建了 {len(negative_data)} 个负面关键词')
    print('✓ 数据迁移完成')


if __name__ == '__main__':
    init_data()
