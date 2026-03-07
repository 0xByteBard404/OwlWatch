# -*- coding: utf-8 -*-
"""情感关键词管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.dependencies import get_db
from app.models.sentiment_keyword import SentimentKeyword
from pydantic import BaseModel

router = APIRouter(tags=["sentiment-keywords"])


# Schemas
class SentimentKeywordCreate(BaseModel):
    keyword: str
    sentiment_type: str  # positive / negative
    category: Optional[str] = None


class SentimentKeywordUpdate(BaseModel):
    keyword: Optional[str] = None
    sentiment_type: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class SentimentKeywordResponse(BaseModel):
    id: str
    keyword: str
    sentiment_type: str
    category: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[SentimentKeywordResponse])
async def list_keywords(
    sentiment_type: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """获取情感关键词列表"""
    query = db.query(SentimentKeyword)

    if sentiment_type:
        query = query.filter(SentimentKeyword.sentiment_type == sentiment_type)
    if category:
        query = query.filter(SentimentKeyword.category == category)
    if is_active is not None:
        query = query.filter(SentimentKeyword.is_active == is_active)

    keywords = query.order_by(SentimentKeyword.created_at.desc()).all()

    return [
        SentimentKeywordResponse(
            id=kw.id,
            keyword=kw.keyword,
            sentiment_type=kw.sentiment_type,
            category=kw.category,
            is_active=kw.is_active,
            created_at=kw.created_at.isoformat() if kw.created_at else None,
            updated_at=kw.updated_at.isoformat() if kw.updated_at else None,
        )
        for kw in keywords
    ]


@router.post("", response_model=SentimentKeywordResponse)
async def create_keyword(
    data: SentimentKeywordCreate,
    db: Session = Depends(get_db),
):
    """创建情感关键词"""
    # 检查是否已存在
    existing = db.query(SentimentKeyword).filter(
        SentimentKeyword.keyword == data.keyword
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="关键词已存在")

    keyword = SentimentKeyword(
        id=str(uuid.uuid4()),
        keyword=data.keyword,
        sentiment_type=data.sentiment_type,
        category=data.category,
        is_active=True,
    )

    db.add(keyword)
    db.commit()
    db.refresh(keyword)

    return SentimentKeywordResponse(
        id=keyword.id,
        keyword=keyword.keyword,
        sentiment_type=keyword.sentiment_type,
        category=keyword.category,
        is_active=keyword.is_active,
        created_at=keyword.created_at.isoformat() if keyword.created_at else None,
        updated_at=keyword.updated_at.isoformat() if keyword.updated_at else None,
    )


@router.put("/{keyword_id}", response_model=SentimentKeywordResponse)
async def update_keyword(
    keyword_id: str,
    data: SentimentKeywordUpdate,
    db: Session = Depends(get_db),
):
    """更新情感关键词"""
    keyword = db.query(SentimentKeyword).filter(
        SentimentKeyword.id == keyword_id
    ).first()

    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    if data.keyword is not None:
        # 检查关键词是否重复
        existing = db.query(SentimentKeyword).filter(
            SentimentKeyword.keyword == data.keyword,
            SentimentKeyword.id != keyword_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="关键词已存在")
        keyword.keyword = data.keyword

    if data.sentiment_type is not None:
        keyword.sentiment_type = data.sentiment_type
    if data.category is not None:
        keyword.category = data.category
    if data.is_active is not None:
        keyword.is_active = data.is_active

    db.commit()
    db.refresh(keyword)

    return SentimentKeywordResponse(
        id=keyword.id,
        keyword=keyword.keyword,
        sentiment_type=keyword.sentiment_type,
        category=keyword.category,
        is_active=keyword.is_active,
        created_at=keyword.created_at.isoformat() if keyword.created_at else None,
        updated_at=keyword.updated_at.isoformat() if keyword.updated_at else None,
    )


@router.delete("/{keyword_id}")
async def delete_keyword(
    keyword_id: str,
    db: Session = Depends(get_db),
):
    """删除情感关键词"""
    keyword = db.query(SentimentKeyword).filter(
        SentimentKeyword.id == keyword_id
    ).first()

    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    db.delete(keyword)
    db.commit()

    return {"message": "删除成功"}


@router.get("/categories", response_model=List[str])
async def get_categories(db: Session = Depends(get_db)):
    """获取所有分类"""
    from sqlalchemy import func

    results = db.query(SentimentKeyword.category).filter(
        SentimentKeyword.category.isnot(None)
    ).distinct().all()

    return [r[0] for r in results if r[0]]


@router.put("/{keyword_id}/toggle")
async def toggle_keyword(
    keyword_id: str,
    db: Session = Depends(get_db),
):
    """切换情感关键词状态"""
    keyword = db.query(SentimentKeyword).filter(
        SentimentKeyword.id == keyword_id
    ).first()

    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    keyword.is_active = not keyword.is_active
    db.commit()

    return {"message": "状态切换成功", "is_active": keyword.is_active}
