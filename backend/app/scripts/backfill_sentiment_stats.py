# -*- coding: utf-8 -*-
"""
历史数据回填脚本：将已有文章数据聚合统计并填充到 keyword_sentiment_stats 表

使用方法：
    cd backend
    python -m app.scripts.backfill_sentiment_stats
"""
import sys
import os
import uuid
from datetime import date, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.database import SessionLocal
from app.utils.timezone import now_cst


def backfill_sentiment_stats():
    """回填历史情感统计数据"""
    db = SessionLocal()

    try:
        print("开始回填历史情感统计数据...")

        # 1. 按关键词+日期聚合统计
        aggregate_sql = text("""
            SELECT
                ak.keyword_id,
                DATE(a.collect_time) as stats_date,
                COUNT(*) as total_count,
                SUM(CASE WHEN a.sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
                SUM(CASE WHEN a.sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count,
                SUM(CASE WHEN a.sentiment_label = 'neutral' OR a.sentiment_label IS NULL THEN 1 ELSE 0 END) as neutral_count,
                SUM(CASE WHEN ak.match_type = 'title_only' THEN 1 ELSE 0 END) as title_match_count,
                SUM(CASE WHEN ak.match_type = 'content_only' THEN 1 ELSE 0 END) as content_match_count,
                SUM(CASE WHEN ak.match_type = 'both' THEN 1 ELSE 0 END) as both_match_count,
                AVG(a.sentiment_score) as avg_sentiment_score
            FROM articles a
            JOIN article_keywords ak ON a.id = ak.article_id
            GROUP BY ak.keyword_id, DATE(a.collect_time)
            ORDER BY ak.keyword_id, DATE(a.collect_time)
        """)

        result = db.execute(aggregate_sql)
        rows = result.fetchall()

        print(f"找到 {len(rows)} 条聚合记录")

        if not rows:
            print("没有需要回填的数据")
            return

        # 2. 清空现有统计数据（如果有）
        db.execute(text("TRUNCATE TABLE keyword_sentiment_stats"))
        print("已清空现有统计数据")

        # 3. 批量插入统计数据
        insert_sql = text("""
            INSERT INTO keyword_sentiment_stats
                (id, keyword_id, stats_date, positive_count, negative_count, neutral_count,
                 total_count, title_match_count, content_match_count, both_match_count,
                 avg_sentiment_score, created_at, updated_at)
            VALUES
                (:id, :keyword_id, :stats_date, :positive_count, :negative_count, :neutral_count,
                 :total_count, :title_match_count, :content_match_count, :both_match_count,
                 :avg_sentiment_score, NOW(), NOW())
        """)

        batch_size = 100
        batch_data = []

        for row in rows:
            keyword_id, stats_date, total_count, positive_count, negative_count, neutral_count, \
                title_match_count, content_match_count, both_match_count, avg_sentiment_score = row

            batch_data.append({
                "id": str(uuid.uuid4()),
                "keyword_id": keyword_id,
                "stats_date": stats_date,
                "positive_count": positive_count or 0,
                "negative_count": negative_count or 0,
                "neutral_count": neutral_count or 0,
                "total_count": total_count or 0,
                "title_match_count": title_match_count or 0,
                "content_match_count": content_match_count or 0,
                "both_match_count": both_match_count or 0,
                "avg_sentiment_score": float(avg_sentiment_score) if avg_sentiment_score else None
            })

            if len(batch_data) >= batch_size:
                db.execute(insert_sql, batch_data)
                db.commit()
                print(f"已插入 {len(batch_data)} 条记录...")
                batch_data = []

        # 插入剩余数据
        if batch_data:
            db.execute(insert_sql, batch_data)
            db.commit()
            print(f"已插入 {len(batch_data)} 条记录...")

        print(f"\n回填完成！共插入 {len(rows)} 条统计记录")

        # 4. 验证结果
        verify_sql = text("""
            SELECT keyword_id, COUNT(*) as days
            FROM keyword_sentiment_stats
            GROUP BY keyword_id
        """)
        verify_result = db.execute(verify_sql)
        print("\n各监控主体的统计天数：")
        for row in verify_result:
            print(f"  关键词 {row[0]}: {row[1]} 天")

    except Exception as e:
        print(f"回填失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill_sentiment_stats()
