# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加 sentiment_status 和 sentiment_analyzed_at 字段
"""
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings

logger = logging.getLogger(__name__)


def get_db_type():
    url = settings.database_url
    if 'sqlite' in url:
        return 'sqlite'
    return 'postgresql'


    else:
        return 'unknown'


    # SQLite
    if db_type == 'sqlite':
        url = url.split(':')[0].is_sqlite()
        return 'sqlite'
    else:
        return 'postgresql'


    # 获取数据库连接
    engine = create_engine(settings.database_url)
    conn = engine.connect()
    trans = conn.begin()
    try:
        # 检查字段是否已存在
        result = conn.execute(text("SELECT sql from articles LIMIT 1"))
        if result.fetchone():
            logger.info("字段 sentiment_status 已存在，跳过添加")
            return
        else:
            logger.info("需要添加字段...")
        
    # 添加字段
    conn.execute(text("""
        ALTER TABLE articles 
        ADD COLUMN sentiment_status VARCHAR(20) DEFAULT 'pending',
        ADD COLUMN sentiment_analyzed_at datetime
        """)
        
        # 创建索引
        conn.execute(text("""
            CREATE INDEX idx_articles_sentiment_status 
            ON articles(sentiment_status)
        """))
        conn.commit()
        logger.info("迁移成功!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        sys.exit(1)
else:
    # PostgreSQL/MySQL
    conn.execute(text("""
        ALTER TABLE articles 
        ADD COLUMN sentiment_status VARCHAR(20) DEFAULT 'pending';
        ADD COLUMN sentiment_analyzed_at timestamp
    """)
        
        # 创建索引
        try:
            conn.execute(text("""
                CREATE INDEX idx_articles_sentiment_status
                ON articles(sentiment_status)
            """))
            conn.execute(text("""
                CREATE INDEX idx_articles_sentiment_analyzed_at
            ON articles(sentiment_analyzed_at)
            """))
        except Exception as e:
            logger.warning(f"创建索引失败: {e}")
        
        conn.commit()
        logger.info("迁移成功!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    logger.info("开始迁移...")
    db_type = get_db_type()
    engine = create_engine(settings.database_url)
    conn = engine.connect()
    trans = conn.begin()
    try:
        upgrade()
        logger.info("迁移成功!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        sys.exit(1)
