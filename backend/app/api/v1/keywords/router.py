# -*- coding: utf-8 -*-
"""关键词管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.dependencies import get_db
from app.models.keyword import Keyword
from app.utils.timezone import now_cst

router = APIRouter()


class DataSourcesSchema(BaseModel):
    """数据源配置"""
    rss_ids: Optional[List[str]] = Field(default=[], description="RSS 订阅 ID 列表")
    search_apis: Optional[List[str]] = Field(default=["bocha", "tavily"], description="搜索 API 列表")


class KeywordCreate(BaseModel):
    """创建关键词请求"""
    keyword: str
    priority: str = Field(default="medium")
    platforms: Optional[List[str]] = Field(default=["bocha", "tavily"])
    data_sources: Optional[DataSourcesSchema] = Field(default=None, description="数据源配置")


class KeywordUpdate(BaseModel):
    """更新关键词请求"""
    keyword: Optional[str] = None
    priority: Optional[str] = None
    platforms: Optional[List[str]] = None
    data_sources: Optional[DataSourcesSchema] = Field(default=None, description="数据源配置")
    is_active: Optional[bool] = None


class KeywordResponse(BaseModel):
    """关键词响应"""
    id: str
    keyword: str
    priority: str
    platforms: List[str]
    data_sources: Optional[Dict[str, Any]] = None
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

    # 处理数据源配置
    data_sources_dict = None
    if data.data_sources:
        data_sources_dict = data.data_sources.model_dump()

    keyword_obj = Keyword(
        id=str(uuid.uuid4()),
        keyword=data.keyword,
        priority=data.priority,
        platforms=data.platforms,
        data_sources=data_sources_dict,
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


@router.get("/{keyword_id}", response_model=KeywordResponse)
async def get_keyword(
    keyword_id: str,
    db: Session = Depends(get_db)
):
    """获取单个关键词详情"""
    keyword_obj = db.query(Keyword).filter(Keyword.id == keyword_id).first()

    if not keyword_obj:
        raise HTTPException(status_code=404, detail="Keyword not found")

    return keyword_obj


@router.put("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: str,
    data: KeywordUpdate,
    db: Session = Depends(get_db)
):
    """更新关键词配置"""
    keyword_obj = db.query(Keyword).filter(Keyword.id == keyword_id).first()

    if not keyword_obj:
        raise HTTPException(status_code=404, detail="Keyword not found")

    if data.keyword is not None:
        keyword_obj.keyword = data.keyword
    if data.priority is not None:
        keyword_obj.priority = data.priority
    if data.platforms is not None:
        keyword_obj.platforms = data.platforms
    if data.data_sources is not None:
        keyword_obj.data_sources = data.data_sources.model_dump()
    if data.is_active is not None:
        keyword_obj.is_active = data.is_active

    keyword_obj.updated_at = now_cst()

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
