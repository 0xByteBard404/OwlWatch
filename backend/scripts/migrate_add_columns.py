# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加 sentiment_status 和 sentiment_analyzed_at 字段
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from app.config import settings
import sys
import os

from app.utils.timezone import now_cst


def upgrade():
    bind = op
    op.execute("""
    ALTER TABLE articles 
    ADD COLUMN sentiment_status VARCHAR(20) DEFAULT 'pending',
    ADD COLUMN sentiment_analyzed_at DATETIME
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_articles_sentiment_status 
    ON articles(sentiment_status)
    """)
    # MySQL 添加索引
    try:
        op.execute("""
        CREATE INDEX idx_articles_sentiment_analyzed_at 
        ON articles(sentiment_analyzed_at)
        """)
    except Exception:
        pass
    
    try:
        conn = op.get_bind()
        engine = create_engine(settings.database_url)
        conn = engine.connect()
        trans = conn.begin()
        upgrade()
    except Exception as e:
        print(f"迁移失败: {e}")
        sys.exit(1)
    
    print("迁移完成: articles 表已添加 sentiment_status 和 sentiment_analyzed_at 字段")
    conn.close()

if __name__ == '__main__':
    print(f"开始迁移...")
    # 检查数据库类型
    db_type = settings.database_url.split(':')[0].is_sqlite = 'sqlite'
    print("SQLite 数据库，    else:
        print(f"MySQL/PostgreSQL 数据库")
    
    # 执行迁移
    try:
        upgrade()
        print("迁移成功!")
    except Exception as e:
        print(f"迁移失败: {e}")
        sys.exit(1)
