# -*- coding: utf-8 -*-
"""负面关键词管理 API"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.dependencies import get_db
from app.models.negative_keyword import NegativeKeyword

router = APIRouter()


class NegativeKeywordCreate(BaseModel):
    """创建负面关键词"""
    keyword: str


class NegativeKeywordResponse(BaseModel):
    """负面关键词响应"""
    id: str
    keyword: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[NegativeKeywordResponse])
async def list_negative_keywords(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取负面关键词列表"""
    query = db.query(NegativeKeyword)
    if is_active is not None:
        query = query.filter(NegativeKeyword.is_active == is_active)
    return query.order_by(NegativeKeyword.created_at.desc()).all()


@router.post("/", response_model=NegativeKeywordResponse)
async def create_negative_keyword(
    data: NegativeKeywordCreate,
    db: Session = Depends(get_db)
):
    """创建负面关键词"""
    # 检查是否已存在
    existing = db.query(NegativeKeyword).filter(
        NegativeKeyword.keyword == data.keyword
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="关键词已存在")

    keyword = NegativeKeyword(
        id=str(uuid.uuid4()),
        keyword=data.keyword,
        is_active=True
    )
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


@router.put("/{keyword_id}", response_model=NegativeKeywordResponse)
async def update_negative_keyword(
    keyword_id: str,
    data: NegativeKeywordCreate,
    db: Session = Depends(get_db)
):
    """更新负面关键词"""
    keyword = db.query(NegativeKeyword).filter(NegativeKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    # 检查是否与其他关键词重复
    existing = db.query(NegativeKeyword).filter(
        NegativeKeyword.keyword == data.keyword,
        NegativeKeyword.id != keyword_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="关键词已存在")

    keyword.keyword = data.keyword
    keyword.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(keyword)
    return keyword


@router.put("/{keyword_id}/toggle")
async def toggle_negative_keyword(
    keyword_id: str,
    db: Session = Depends(get_db)
):
    """启用/禁用负面关键词"""
    keyword = db.query(NegativeKeyword).filter(NegativeKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    keyword.is_active = not keyword.is_active
    keyword.updated_at = datetime.utcnow()
    db.commit()
    return {"message": f"关键词已{'启用' if keyword.is_active else '禁用'}", "is_active": keyword.is_active}


@router.delete("/{keyword_id}")
async def delete_negative_keyword(
    keyword_id: str,
    db: Session = Depends(get_db)
):
    """删除负面关键词"""
    keyword = db.query(NegativeKeyword).filter(NegativeKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    db.delete(keyword)
    db.commit()
    return {"message": "删除成功"}


@router.post("/init-defaults")
async def init_default_keywords(db: Session = Depends(get_db)):
    """初始化默认负面关键词"""
    defaults = ["违规", "违法", "投诉", "通报", "处罚", "曝光", "被查", "立案", "调查", "维权"]

    added = 0
    for kw in defaults:
        existing = db.query(NegativeKeyword).filter(NegativeKeyword.keyword == kw).first()
        if not existing:
            keyword = NegativeKeyword(
                id=str(uuid.uuid4()),
                keyword=kw,
                is_active=True
            )
            db.add(keyword)
            added += 1

    db.commit()
    return {"message": f"初始化完成，新增 {added} 个关键词"}
