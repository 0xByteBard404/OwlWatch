# -*- coding: utf-8 -*-
"""监控主体情感统计模型（按日期聚合）"""
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, UniqueConstraint, Index
from ..database import Base
from ..utils.timezone import now_cst


class KeywordSentimentStats(Base):
    """
    监控主体情感统计表（按日期）

    设计目标：
    - 查询性能：大屏/趋势图直接读取，无需 JOIN + GROUP BY
    - 实时性：情感分析完成后立即增量更新
    - 存储效率：每天每个主体仅一行记录
    """
    __tablename__ = "keyword_sentiment_stats"
    __table_args__ = (
        UniqueConstraint('keyword_id', 'stats_date', name='uq_keyword_stats_date'),
        Index('ix_keyword_sentiment_stats_date', 'stats_date'),
    )

    id = Column(String(36), primary_key=True)
    keyword_id = Column(String(36), nullable=False, index=True)
    stats_date = Column(Date, nullable=False)  # 统计日期

    # 情感计数
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)

    # 标题匹配 vs 内容匹配（可选，用于精细化分析）
    title_match_count = Column(Integer, default=0)
    content_match_count = Column(Integer, default=0)
    both_match_count = Column(Integer, default=0)

    # 平均情感分数（用于趋势分析）
    avg_sentiment_score = Column(Float, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=now_cst)
    updated_at = Column(DateTime, default=now_cst, onupdate=now_cst)

    def __repr__(self):
        return f"<KeywordSentimentStats keyword={self.keyword_id} date={self.stats_date}>"
