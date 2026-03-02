# -*- coding: utf-8 -*-
"""关键词管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

from app.dependencies import get_db
from app.models.keyword import Keyword

router = APIRouter()


class KeywordCreate(BaseModel):
    """创建关键词请求"""
    keyword: str
    priority: str = Field(default="medium")
    platforms: Optional[List[str]] = Field(default=["bocha", "tavily"])


class KeywordResponse(BaseModel):
    """关键词响应"""
    id: str
    keyword: str
    priority: str
    platforms: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=KeywordResponse)
async def create_keyword(
    data: KeywordCreate,
    db: Session = Depends(get_db)
):
    """创建监控关键词"""
    # 检查是否已存在
    existing = db.query(Keyword).filter(
        Keyword.keyword == data.keyword
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Keyword already exists")

    keyword_obj = Keyword(
        id=str(uuid.uuid4()),
        keyword=data.keyword,
        priority=data.priority,
        platforms=data.platforms,
    )

    db.add(keyword_obj)
    db.commit()
    db.refresh(keyword_obj)

    return keyword_obj


@router.get("/", response_model=List[KeywordResponse])
async def list_keywords(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取关键词列表"""
    query = db.query(Keyword)

    if is_active is not None:
        query = query.filter(Keyword.is_active == is_active)

    keywords = query.offset(skip).limit(limit).all()
    return keywords


@router.put("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: str,
    data: KeywordCreate,
    db: Session = Depends(get_db)
):
    """更新关键词配置"""
    keyword_obj = db.query(Keyword).filter(Keyword.id == keyword_id).first()

    if not keyword_obj:
        raise HTTPException(status_code=404, detail="Keyword not found")

    keyword_obj.keyword = data.keyword
    keyword_obj.priority = data.priority
    keyword_obj.platforms = data.platforms
    keyword_obj.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(keyword_obj)

    return keyword_obj


@router.delete("/{keyword_id}")
async def delete_keyword(
    keyword_id: str,
    db: Session = Depends(get_db)
):
    """删除关键词"""
    keyword_obj = db.query(Keyword).filter(Keyword.id == keyword_id).first()

    if not keyword_obj:
        raise HTTPException(status_code=404, detail="Keyword not found")

    db.delete(keyword_obj)
    db.commit()

    return {"message": "Keyword deleted successfully"}
