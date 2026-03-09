# -*- coding: utf-8 -*-
"""
数据迁移脚本：从 Keyword.data_sources.rss_ids 迁移到 KeywordRSSAssociation 关联表

使用方法:
    cd backend
    python -m app.scripts.migrate_rss_associations
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models.keyword import Keyword
from app.models.rss_feed import RSSFeed
from app.models.keyword_rss_association import KeywordRSSAssociation
from app.utils.timezone import now_cst


def migrate():
    """从 Keyword.data_sources.rss_ids 迁移到关联表"""
    db = SessionLocal()

    try:
        print("=" * 60)
        print("RSS 关联数据迁移脚本")
        print("=" * 60)

        # 1. 获取所有有 data_sources 配置的监控主体
        keywords = db.query(Keyword).filter(
            Keyword.data_sources.isnot(None)
        ).all()

        print(f"\n发现 {len(keywords)} 个监控主体有数据源配置")

        # 2. 迁移数据
        created_count = 0
        skipped_count = 0
        error_count = 0

        for keyword in keywords:
            data_sources = keyword.data_sources or {}
            rss_ids = data_sources.get("rss_ids", [])

            if not rss_ids:
                continue

            print(f"\n处理监控主体: {keyword.keyword} ({keyword.id})")
            print(f"  关联的 RSS IDs: {rss_ids}")

            for rss_id in rss_ids:
                # 检查 RSS Feed 是否存在
                feed = db.query(RSSFeed).filter(RSSFeed.id == rss_id).first()
                if not feed:
                    print(f"  [跳过] RSS Feed 不存在: {rss_id}")
                    skipped_count += 1
                    continue

                # 检查是否已存在关联
                existing = db.query(KeywordRSSAssociation).filter(
                    KeywordRSSAssociation.keyword_id == keyword.id,
                    KeywordRSSAssociation.rss_feed_id == rss_id
                ).first()

                if existing:
                    print(f"  [已存在] 关联已存在: {feed.name}")
                    skipped_count += 1
                    continue

                # 创建新关联
                # 如果 RSS Feed 有旧的 keyword_id，同步设置 is_active
                is_active = feed.is_active and keyword.is_active

                association = KeywordRSSAssociation(
                    keyword_id=keyword.id,
                    rss_feed_id=rss_id,
                    is_active=is_active,
                    filter_rules={
                        "include_keywords": [keyword.keyword],  # 使用监控主体关键词作为默认过滤
                        "exclude_keywords": [],
                        "match_mode": "any",
                        "title_only": False,
                    },
                    created_at=now_cst(),
                )
                db.add(association)
                created_count += 1
                print(f"  [创建] 关联创建成功: {feed.name}")

        # 3. 提交事务
        db.commit()

        # 4. 输出统计
        print("\n" + "=" * 60)
        print("迁移完成!")
        print(f"  创建关联: {created_count}")
        print(f"  跳过: {skipped_count}")
        print(f"  错误: {error_count}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n[错误] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


def verify():
    """验证迁移结果"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 60)
        print("验证迁移结果")
        print("=" * 60)

        # 统计关联表
        total_associations = db.query(KeywordRSSAssociation).count()
        active_associations = db.query(KeywordRSSAssociation).filter(
            KeywordRSSAssociation.is_active == True
        ).count()

        print(f"\n关联表统计:")
        print(f"  总关联数: {total_associations}")
        print(f"  活跃关联数: {active_associations}")

        # 显示每个监控主体的关联
        keywords = db.query(Keyword).all()
        for keyword in keywords:
            assocs = db.query(KeywordRSSAssociation).filter(
                KeywordRSSAssociation.keyword_id == keyword.id
            ).all()

            if assocs:
                print(f"\n监控主体: {keyword.keyword}")
                for assoc in assocs:
                    feed = db.query(RSSFeed).filter(RSSFeed.id == assoc.rss_feed_id).first()
                    status = "活跃" if assoc.is_active else "禁用"
                    print(f"  - {feed.name if feed else assoc.rss_feed_id} ({status})")

        print("\n" + "=" * 60)

    finally:
        db.close()


def create_table():
    """创建关联表（如果不存在）"""
    from sqlalchemy import text
    from app.database import engine

    print("检查并创建关联表...")

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS keyword_rss_associations (
        keyword_id VARCHAR(36) NOT NULL,
        rss_feed_id VARCHAR(36) NOT NULL,
        filter_rules TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        priority VARCHAR(10) DEFAULT 'medium',
        created_at DATETIME,
        last_matched_at DATETIME,
        match_count INTEGER DEFAULT 0,
        PRIMARY KEY (keyword_id, rss_feed_id),
        FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE,
        FOREIGN KEY (rss_feed_id) REFERENCES rss_feeds(id) ON DELETE CASCADE
    );
    """

    create_index_sql = """
    CREATE INDEX IF NOT EXISTS ix_keyword_rss_associations_is_active
    ON keyword_rss_associations(is_active);
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.execute(text(create_index_sql))
            conn.commit()
        print("关联表创建/检查完成")
    except Exception as e:
        print(f"创建表时出错: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RSS 关联数据迁移")
    parser.add_argument("--verify", action="store_true", help="只验证迁移结果")
    parser.add_argument("--create-table", action="store_true", help="只创建表")

    args = parser.parse_args()

    if args.create_table:
        create_table()
    elif args.verify:
        verify()
    else:
        # 先创建表，再迁移
        create_table()
        migrate()
        verify()
