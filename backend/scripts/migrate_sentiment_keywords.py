# -*- coding: utf-8 -*-
"""
数据库迁移：负面关键词改造为情感关键词

使用 SQLAlchemy ORM 实现，支持 PostgreSQL 和 SQLite

使用方法：
    cd backend
    python scripts/migrate_sentiment_keywords.py
"""
import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.sentiment_keyword import SentimentKeyword


def migrate():
    """执行迁移"""
    print("=" * 50)
    print("情感关键词迁移脚本")
    print("=" * 50)

    db = SessionLocal()

    try:
        # 检查表是否存在，如果不存在则创建
        from app.database import Base
        Base.metadata.create_all(bind=engine)
        print("✓ 数据表检查/创建完成")

        # 检查是否已有数据
        existing_count = db.query(SentimentKeyword).count()
        if existing_count > 0:
            print(f"✓ sentiment_keywords 表已有 {existing_count} 条数据")

            # 检查是否有正面关键词
            positive_count = db.query(SentimentKeyword).filter(
                SentimentKeyword.sentiment_type == 'positive'
            ).count()

            if positive_count == 0:
                print("添加默认正面关键词...")
                _add_positive_keywords(db)
            else:
                print(f"✓ 已有 {positive_count} 条正面关键词")
        else:
            print("初始化情感关键词数据...")
            _add_positive_keywords(db)
            _add_negative_keywords(db)

        db.commit()
        print("\n" + "=" * 50)
        print("✓ 迁移完成!")

        # 显示统计
        positive = db.query(SentimentKeyword).filter(
            SentimentKeyword.sentiment_type == 'positive'
        ).count()
        negative = db.query(SentimentKeyword).filter(
            SentimentKeyword.sentiment_type == 'negative'
        ).count()
        print(f"  正面关键词: {positive} 条")
        print(f"  负面关键词: {negative} 条")
        print("=" * 50)

    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def _add_positive_keywords(db):
    """添加默认正面关键词"""
    positive_keywords = [
        ("融资", "财务"),
        ("上市", "财务"),
        ("并购", "财务"),
        ("收购", "财务"),
        ("盈利", "财务"),
        ("增长", "经营"),
        ("突破", "技术"),
        ("创新", "技术"),
        ("获奖", "荣誉"),
        ("合作", "经营"),
        ("签约", "经营"),
        ("投资", "财务"),
    ]

    added = 0
    for keyword, category in positive_keywords:
        existing = db.query(SentimentKeyword).filter(
            SentimentKeyword.keyword == keyword,
            SentimentKeyword.sentiment_type == 'positive'
        ).first()
        if not existing:
            kw = SentimentKeyword(
                id=str(uuid.uuid4()),
                keyword=keyword,
                sentiment_type='positive',
                category=category,
                is_active=True
            )
            db.add(kw)
            added += 1

    if added > 0:
        print(f"✓ 添加了 {added} 个正面关键词")


def _add_negative_keywords(db):
    """添加默认负面关键词"""
    negative_keywords = [
        ("违约", "法律"),
        ("投诉", "法律"),
        ("诈骗", "法律"),
        ("欺诈", "法律"),
        ("跑路", "经营"),
        ("倒闭", "经营"),
        ("破产", "经营"),
        ("起诉", "法律"),
        ("违法", "法律"),
        ("违规", "法律"),
        ("非法", "法律"),
        ("涉案", "法律"),
        ("被查", "法律"),
        ("处罚", "法律"),
        ("罚款", "法律"),
        ("曝光", "舆情"),
        ("黑幕", "舆情"),
        ("内幕", "舆情"),
        ("传销", "经营"),
    ]

    added = 0
    for keyword, category in negative_keywords:
        existing = db.query(SentimentKeyword).filter(
            SentimentKeyword.keyword == keyword,
            SentimentKeyword.sentiment_type == 'negative'
        ).first()
        if not existing:
            kw = SentimentKeyword(
                id=str(uuid.uuid4()),
                keyword=keyword,
                sentiment_type='negative',
                category=category,
                is_active=True
            )
            db.add(kw)
            added += 1

    if added > 0:
        print(f"✓ 添加了 {added} 个负面关键词")


if __name__ == "__main__":
    migrate()
