# -*- coding: utf-8 -*-
"""
数据库迁移：添加 URL 唯一约束

步骤：
1. 删除重复的 URL 记录（保留最早的一条）
2. 添加唯一约束

使用方法：
    cd backend
    python scripts/migrate_add_unique_url.py
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine, SessionLocal


def remove_duplicates(db):
    """删除重复记录，保留最早的一条"""
    print("=" * 50)
    print("步骤 1: 检查并删除重复 URL")
    print("=" * 50)

    # 查找重复的 URL
    result = db.execute(text("""
        SELECT url, COUNT(*) as cnt
        FROM articles
        GROUP BY url
        HAVING COUNT(*) > 1
    """))
    duplicates = result.fetchall()

    if not duplicates:
        print("✓ 没有发现重复 URL")
        return 0

    print(f"发现 {len(duplicates)} 个重复 URL")
    total_deleted = 0

    for url, count in duplicates:
        # 获取该 URL 的所有记录，按采集时间排序
        result = db.execute(text("""
            SELECT id, collect_time
            FROM articles
            WHERE url = :url
            ORDER BY collect_time ASC
        """), {"url": url})
        records = result.fetchall()

        # 保留第一条，删除其余的
        ids_to_delete = [r[0] for r in records[1:]]
        if ids_to_delete:
            # 构建 IN 子句
            placeholders = ",".join([f"'{id}'" for id in ids_to_delete])
            db.execute(text(f"""
                DELETE FROM articles
                WHERE id IN ({placeholders})
            """))
            total_deleted += len(ids_to_delete)
            print(f"  删除 {len(ids_to_delete)} 条重复: {url[:60]}...")

    db.commit()
    print(f"✓ 共删除 {total_deleted} 条重复记录")
    return total_deleted


def add_unique_constraint(db):
    """添加唯一约束"""
    print("\n" + "=" * 50)
    print("步骤 2: 添加唯一约束")
    print("=" * 50)

    if engine.dialect.name == "sqlite":
        # SQLite: 检查是否已有约束
        result = db.execute(text("""
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name='articles'
        """))
        table_sql = result.fetchone()
        if table_sql and 'uq_articles_url' in (table_sql[0] or ''):
            print("✓ 唯一约束已存在")
            return True

        print("SQLite 需要重建表来添加唯一约束...")

        try:
            # 创建新表（带唯一约束）
            db.execute(text("""
                CREATE TABLE articles_new (
                    id VARCHAR(36) PRIMARY KEY,
                    keyword_id VARCHAR(36),
                    title VARCHAR(500) NOT NULL,
                    content TEXT,
                    url VARCHAR(500) NOT NULL,
                    source VARCHAR(100),
                    source_api VARCHAR(20),
                    sentiment_score FLOAT,
                    sentiment_label VARCHAR(20),
                    publish_time DATETIME,
                    collect_time DATETIME,
                    extra TEXT,
                    CONSTRAINT uq_articles_url UNIQUE (url)
                )
            """))

            # 复制数据
            db.execute(text("""
                INSERT INTO articles_new
                SELECT id, keyword_id, title, content, url, source,
                       source_api, sentiment_score, sentiment_label,
                       publish_time, collect_time, extra
                FROM articles
            """))

            # 删除旧表
            db.execute(text("DROP TABLE articles"))

            # 重命名新表
            db.execute(text("ALTER TABLE articles_new RENAME TO articles"))

            # 重建索引
            db.execute(text("CREATE INDEX ix_articles_keyword_id ON articles(keyword_id)"))

            db.commit()
            print("✓ 唯一约束已添加（SQLite 重建表完成）")
            return True

        except Exception as e:
            db.rollback()
            print(f"✗ 添加约束失败: {e}")
            raise

    elif engine.dialect.name == "postgresql":
        # PostgreSQL: 检查约束是否存在
        result = db.execute(text("""
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name='articles'
            AND constraint_type='UNIQUE'
            AND constraint_name='uq_articles_url'
        """))
        if result.fetchone():
            print("✓ 唯一约束已存在")
            return True

        print("添加唯一约束...")
        db.execute(text("""
            ALTER TABLE articles
            ADD CONSTRAINT uq_articles_url UNIQUE (url)
        """))
        db.commit()
        print("✓ 唯一约束已添加")
        return True

    else:
        print(f"✗ 不支持的数据库类型: {engine.dialect.name}")
        print("请手动执行以下 SQL:")
        print("  ALTER TABLE articles ADD CONSTRAINT uq_articles_url UNIQUE (url);")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("OwlWatch 数据库迁移: 添加 URL 唯一约束")
    print("=" * 50 + "\n")

    db = SessionLocal()

    try:
        # 步骤 1: 删除重复
        remove_duplicates(db)

        # 步骤 2: 添加约束
        success = add_unique_constraint(db)

        if success:
            print("\n" + "=" * 50)
            print("✓ 迁移完成!")
            print("=" * 50)
        else:
            print("\n" + "=" * 50)
            print("✗ 迁移需要手动完成")
            print("=" * 50)

    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
