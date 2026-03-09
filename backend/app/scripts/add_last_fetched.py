# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 keywords 表添加 last_fetched 字段

运行方式：
cd backend
python -m app.scripts.add_last_fetched
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal, engine
from sqlalchemy import text


def migrate():
    """执行迁移"""
    db = SessionLocal()
    try:
        # 检查字段是否已存在
        result = db.execute(text("SHOW COLUMNS FROM keywords LIKE 'last_fetched'"))
        exists = result.fetchone()

        if exists:
            print("✓ last_fetched 字段已存在，跳过迁移")
            return

        # 添加 last_fetched 字段
        db.execute(text("""
            ALTER TABLE keywords
            ADD COLUMN last_fetched DATETIME NULL
            COMMENT '最近扫描时间'
        """))
        db.commit()
        print("✓ 成功添加 last_fetched 字段")

    except Exception as e:
        db.rollback()
        print(f"✗ 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("开始迁移：添加 last_fetched 字段...")
    migrate()
    print("迁移完成！")
