# -*- coding: utf-8 -*-
"""文章与监控主体关联模型（多对多）"""
from sqlalchemy import Column, String, DateTime, Text, UniqueConstraint, Index
from ..database import Base
from ..utils.timezone import now_cst


class ArticleKeyword(Base):
    """文章与监控主体关联表"""
    __tablename__ = "article_keywords"
    __table_args__ = (
        UniqueConstraint('article_id', 'keyword_id', name='uq_article_keyword'),
        Index('ix_article_keywords_keyword_id', 'keyword_id'),
        Index('ix_article_keywords_article_id', 'article_id'),
    )

    id = Column(String(36), primary_key=True)
    article_id = Column(String(36), nullable=False)
    keyword_id = Column(String(36), nullable=False)
    match_type = Column(String(20), nullable=True)  # title_only / content_only / both
    matched_at = Column(DateTime, default=now_cst)

    def __repr__(self):
        return f"<ArticleKeyword article={self.article_id} keyword={self.keyword_id}>"
