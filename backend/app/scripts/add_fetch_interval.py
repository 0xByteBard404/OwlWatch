# -*- coding: utf-8 -*-
"""添加 fetch_interval 字段的数据库迁移脚本"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.database import engine


def migrate():
    """添加 fetch_interval 字段到 keywords 表"""
    with engine.connect() as conn:
        # 检查字段是否已存在
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'keywords' AND column_name = 'fetch_interval'
        """))
        if result.fetchone():
            print("fetch_interval 字段已存在，跳过迁移")
            return

        # 添加字段
        conn.execute(text("""
            ALTER TABLE keywords
            ADD COLUMN fetch_interval INTEGER DEFAULT 300
        """))
        conn.commit()
        print("成功添加 fetch_interval 字段")


if __name__ == "__main__":
    migrate()
