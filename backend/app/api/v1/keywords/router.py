# -*- coding: utf-8 -*-
"""关键词管理 API"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.dependencies import get_db
from app.models.keyword import Keyword, DEFAULT_ALERT_CONFIG
from app.models.rss_feed import RSSFeed
from app.models.keyword_rss_association import KeywordRSSAssociation
from app.models.user import User
from app.core.security import get_current_active_user
from app.utils.timezone import now_cst

router = APIRouter()


# ============ 预警配置 Schema ============

class NegativeBurstConfig(BaseModel):
    """负面爆发预警配置"""
    enabled: bool = Field(default=True, description="是否启用")
    threshold: float = Field(default=0.3, ge=0, le=1, description="负面情感占比阈值")
    min_count: int = Field(default=3, ge=1, description="最少文章数")


class SensitiveKeywordConfig(BaseModel):
    """敏感词预警配置"""
    enabled: bool = Field(default=True, description="是否启用")
    use_global: bool = Field(default=True, description="使用全局敏感词库")
    custom_keywords: List[str] = Field(default=[], description="自定义敏感词")


class VolumeSpikeConfig(BaseModel):
    """讨论量激增配置"""
    enabled: bool = Field(default=True, description="是否启用")
    threshold: float = Field(default=2.0, ge=1, description="增长倍数阈值")


class AlertConfigSchema(BaseModel):
    """预警配置"""
    negative_burst: NegativeBurstConfig = Field(default_factory=NegativeBurstConfig)
    sensitive_keyword: SensitiveKeywordConfig = Field(default_factory=SensitiveKeywordConfig)
    volume_spike: VolumeSpikeConfig = Field(default_factory=VolumeSpikeConfig)
    notifications: List[str] = Field(default=["email", "webhook"], description="通知渠道")


# ============ 数据源配置 Schema ============

class DataSourcesSchema(BaseModel):
    """数据源配置"""
    rss_ids: Optional[List[str]] = Field(default=[], description="RSS 订阅 ID 列表")
    search_apis: Optional[List[str]] = Field(default=["bocha", "tavily"], description="搜索 API 列表")


# ============ 关键词 Schema ============

class KeywordCreate(BaseModel):
    """创建关键词请求"""
    keyword: str
    priority: str = Field(default="medium")
    platforms: Optional[List[str]] = Field(default=["bocha", "tavily"])
    data_sources: Optional[DataSourcesSchema] = Field(default=None, description="数据源配置")
    alert_config: Optional[AlertConfigSchema] = Field(default=None, description="预警配置")
    fetch_interval: Optional[int] = Field(default=300, description="更新间隔（秒），默认 5 分钟")


class KeywordUpdate(BaseModel):
    """更新关键词请求"""
    keyword: Optional[str] = None
    priority: Optional[str] = None
    platforms: Optional[List[str]] = None
    data_sources: Optional[DataSourcesSchema] = Field(default=None, description="数据源配置")
    alert_config: Optional[AlertConfigSchema] = Field(default=None, description="预警配置")
    fetch_interval: Optional[int] = Field(default=None, description="更新间隔（秒）")
    is_active: Optional[bool] = None


class KeywordResponse(BaseModel):
    """关键词响应"""
    id: str
    keyword: str
    priority: str
    platforms: List[str]
    data_sources: Optional[Dict[str, Any]] = None
    alert_config: Optional[Dict[str, Any]] = None
    fetch_interval: int = 300  # 更新间隔（秒），默认 5 分钟
    last_fetched: Optional[datetime] = None  # 最近扫描时间
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ RSS 关联 Schema ============

class FilterRulesSchema(BaseModel):
    """过滤规则"""
    include_keywords: Optional[List[str]] = Field(default=[], description="包含关键词")
    exclude_keywords: Optional[List[str]] = Field(default=[], description="排除关键词")
    match_mode: Optional[str] = Field(default="any", description="匹配模式: any/all")
    title_only: Optional[bool] = Field(default=False, description="仅匹配标题")


class RSSAssociationCreate(BaseModel):
    """创建 RSS 关联请求"""
    rss_feed_id: str = Field(..., description="RSS Feed ID")
    filter_rules: Optional[FilterRulesSchema] = Field(default=None, description="过滤规则")
    is_active: Optional[bool] = Field(default=True)
    priority: Optional[str] = Field(default="medium")


class RSSAssociationUpdate(BaseModel):
    """更新 RSS 关联请求"""
    filter_rules: Optional[FilterRulesSchema] = None
    is_active: Optional[bool] = None
    priority: Optional[str] = None


class RSSAssociationResponse(BaseModel):
    """RSS 关联响应"""
    keyword_id: str
    rss_feed_id: str
    rss_feed_name: Optional[str] = None
    rss_feed_url: Optional[str] = None
    filter_rules: Optional[Dict[str, Any]] = None
    is_active: bool
    priority: str
    created_at: Optional[datetime] = None
    last_matched_at: Optional[datetime] = None
    match_count: int = 0

    class Config:
        from_attributes = True


class KeywordWithRSSResponse(BaseModel):
    """关键词详情（包含 RSS 关联）"""
    id: str
    keyword: str
    priority: str
    platforms: List[str]
    data_sources: Optional[Dict[str, Any]] = None
    fetch_interval: int = 300  # 更新间隔（秒），默认 5 分钟
    last_fetched: Optional[datetime] = None  # 最近扫描时间
    is_active: bool
    created_at: datetime
    rss_associations: List[RSSAssociationResponse] = []

    class Config:
        from_attributes = True


# ============ 关键词 CRUD ============

def _sync_rss_associations(keyword_id: str, rss_ids: List[str], db: Session):
    """
    同步 RSS 关联：确保 data_sources.rss_ids 与 KeywordRSSAssociation 一致

    Args:
        keyword_id: 监控主体 ID
        rss_ids: RSS Feed ID 列表
        db: 数据库会话
    """
    # 获取现有关联
    existing_assocs = db.query(KeywordRSSAssociation).filter(
        KeywordRSSAssociation.keyword_id == keyword_id
    ).all()
    existing_feed_ids = {assoc.rss_feed_id for assoc in existing_assocs}
    new_feed_ids = set(rss_ids)

    # 删除不再需要的关联
    to_delete = existing_feed_ids - new_feed_ids
    if to_delete:
        db.query(KeywordRSSAssociation).filter(
            KeywordRSSAssociation.keyword_id == keyword_id,
            KeywordRSSAssociation.rss_feed_id.in_(to_delete)
        ).delete(synchronize_session=False)

    # 添加新的关联（使用复合主键，不需要 id 字段）
    to_add = new_feed_ids - existing_feed_ids
    for feed_id in to_add:
        # 检查 RSS Feed 是否存在
        feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
        if feed:
            assoc = KeywordRSSAssociation(
                keyword_id=keyword_id,
                rss_feed_id=feed_id,
                is_active=True,
                priority="medium",
                filter_rules=None,  # 使用默认规则（匹配所有）
            )
            db.add(assoc)


@router.post("/", response_model=KeywordResponse)
async def create_keyword(
    data: KeywordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建监控关键词（需要认证）"""
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

    # 处理预警配置
    alert_config_dict = None
    if data.alert_config:
        alert_config_dict = data.alert_config.model_dump()

    keyword_obj = Keyword(
        id=str(uuid.uuid4()),
        keyword=data.keyword,
        priority=data.priority,
        platforms=data.platforms,
        data_sources=data_sources_dict,
        alert_config=alert_config_dict,
        fetch_interval=data.fetch_interval,
    )

    db.add(keyword_obj)
    db.commit()
    db.refresh(keyword_obj)

    # 同步 RSS 关联
    rss_ids = data_sources_dict.get("rss_ids", []) if data_sources_dict else []
    if rss_ids:
        _sync_rss_associations(keyword_obj.id, rss_ids, db)
        db.commit()

    return keyword_obj


@router.get("/", response_model=List[KeywordResponse])
async def list_keywords(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取关键词列表（需要认证）"""
    query = db.query(Keyword)

    if is_active is not None:
        query = query.filter(Keyword.is_active == is_active)

    keywords = query.offset(skip).limit(limit).all()
    return keywords


@router.get("/{keyword_id}", response_model=KeywordWithRSSResponse)
async def get_keyword(
    keyword_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取单个关键词详情（包含 RSS 关联）"""
    keyword_obj = db.query(Keyword).filter(Keyword.id == keyword_id).first()

    if not keyword_obj:
        raise HTTPException(status_code=404, detail="Keyword not found")

    # 获取 RSS 关联
    associations = db.query(KeywordRSSAssociation).options(
        joinedload(KeywordRSSAssociation.rss_feed)
    ).filter(KeywordRSSAssociation.keyword_id == keyword_id).all()

    # 构造响应
    rss_assocs = []
    for assoc in associations:
        rss_assocs.append(RSSAssociationResponse(
            keyword_id=assoc.keyword_id,
            rss_feed_id=assoc.rss_feed_id,
            rss_feed_name=assoc.rss_feed.name if assoc.rss_feed else None,
            rss_feed_url=assoc.rss_feed.feed_url if assoc.rss_feed else None,
            filter_rules=assoc.filter_rules,
            is_active=assoc.is_active,
            priority=assoc.priority,
            created_at=assoc.created_at,
            last_matched_at=assoc.last_matched_at,
            match_count=assoc.match_count or 0,
        ))

    return KeywordWithRSSResponse(
        id=keyword_obj.id,
        keyword=keyword_obj.keyword,
        priority=keyword_obj.priority,
        platforms=keyword_obj.platforms or [],
        data_sources=keyword_obj.data_sources,
        fetch_interval=keyword_obj.fetch_interval or 300,
        is_active=keyword_obj.is_active,
        created_at=keyword_obj.created_at,
        rss_associations=rss_assocs,
    )


@router.put("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: str,
    data: KeywordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新关键词配置（需要认证）"""
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
        # 同步 RSS 关联
        rss_ids = data.data_sources.rss_ids or []
        _sync_rss_associations(keyword_id, rss_ids, db)
    if data.alert_config is not None:
        keyword_obj.alert_config = data.alert_config.model_dump()
    if data.fetch_interval is not None:
        keyword_obj.fetch_interval = data.fetch_interval
    if data.is_active is not None:
        keyword_obj.is_active = data.is_active

    keyword_obj.updated_at = now_cst()

    db.commit()
    db.refresh(keyword_obj)

    return keyword_obj


@router.delete("/{keyword_id}")
async def delete_keyword(
    keyword_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除关键词（需要认证）"""
    keyword_obj = db.query(Keyword).filter(Keyword.id == keyword_id).first()

    if not keyword_obj:
        raise HTTPException(status_code=404, detail="Keyword not found")

    db.delete(keyword_obj)
    db.commit()

    return {"message": "Keyword deleted successfully"}


# ============ RSS 关联管理 ============

@router.post("/{keyword_id}/rss-associations", response_model=RSSAssociationResponse)
async def create_rss_association(
    keyword_id: str,
    data: RSSAssociationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """为监控主体添加 RSS 关联"""
    # 检查监控主体是否存在
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    # 检查 RSS Feed 是否存在
    rss_feed = db.query(RSSFeed).filter(RSSFeed.id == data.rss_feed_id).first()
    if not rss_feed:
        raise HTTPException(status_code=404, detail="RSS Feed not found")

    # 检查是否已存在关联
    existing = db.query(KeywordRSSAssociation).filter(
        KeywordRSSAssociation.keyword_id == keyword_id,
        KeywordRSSAssociation.rss_feed_id == data.rss_feed_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Association already exists")

    # 创建关联
    filter_rules = data.filter_rules.model_dump() if data.filter_rules else {
        "include_keywords": [],
        "exclude_keywords": [],
        "match_mode": "any",
        "title_only": False,
    }

    association = KeywordRSSAssociation(
        keyword_id=keyword_id,
        rss_feed_id=data.rss_feed_id,
        filter_rules=filter_rules,
        is_active=data.is_active,
        priority=data.priority,
    )

    db.add(association)
    db.commit()
    db.refresh(association)

    return RSSAssociationResponse(
        keyword_id=association.keyword_id,
        rss_feed_id=association.rss_feed_id,
        rss_feed_name=rss_feed.name,
        rss_feed_url=rss_feed.feed_url,
        filter_rules=association.filter_rules,
        is_active=association.is_active,
        priority=association.priority,
        created_at=association.created_at,
        last_matched_at=association.last_matched_at,
        match_count=association.match_count or 0,
    )


@router.get("/{keyword_id}/rss-associations", response_model=List[RSSAssociationResponse])
async def list_rss_associations(
    keyword_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取监控主体的 RSS 关联列表"""
    # 检查监控主体是否存在
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    associations = db.query(KeywordRSSAssociation).options(
        joinedload(KeywordRSSAssociation.rss_feed)
    ).filter(KeywordRSSAssociation.keyword_id == keyword_id).all()

    result = []
    for assoc in associations:
        result.append(RSSAssociationResponse(
            keyword_id=assoc.keyword_id,
            rss_feed_id=assoc.rss_feed_id,
            rss_feed_name=assoc.rss_feed.name if assoc.rss_feed else None,
            rss_feed_url=assoc.rss_feed.feed_url if assoc.rss_feed else None,
            filter_rules=assoc.filter_rules,
            is_active=assoc.is_active,
            priority=assoc.priority,
            created_at=assoc.created_at,
            last_matched_at=assoc.last_matched_at,
            match_count=assoc.match_count or 0,
        ))

    return result


@router.put("/{keyword_id}/rss-associations/{rss_feed_id}", response_model=RSSAssociationResponse)
async def update_rss_association(
    keyword_id: str,
    rss_feed_id: str,
    data: RSSAssociationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新 RSS 关联配置"""
    association = db.query(KeywordRSSAssociation).options(
        joinedload(KeywordRSSAssociation.rss_feed)
    ).filter(
        KeywordRSSAssociation.keyword_id == keyword_id,
        KeywordRSSAssociation.rss_feed_id == rss_feed_id
    ).first()

    if not association:
        raise HTTPException(status_code=404, detail="Association not found")

    if data.filter_rules is not None:
        association.filter_rules = data.filter_rules.model_dump()
    if data.is_active is not None:
        association.is_active = data.is_active
    if data.priority is not None:
        association.priority = data.priority

    db.commit()
    db.refresh(association)

    return RSSAssociationResponse(
        keyword_id=association.keyword_id,
        rss_feed_id=association.rss_feed_id,
        rss_feed_name=association.rss_feed.name if association.rss_feed else None,
        rss_feed_url=association.rss_feed.feed_url if association.rss_feed else None,
        filter_rules=association.filter_rules,
        is_active=association.is_active,
        priority=association.priority,
        created_at=association.created_at,
        last_matched_at=association.last_matched_at,
        match_count=association.match_count or 0,
    )


@router.delete("/{keyword_id}/rss-associations/{rss_feed_id}")
async def delete_rss_association(
    keyword_id: str,
    rss_feed_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除 RSS 关联"""
    association = db.query(KeywordRSSAssociation).filter(
        KeywordRSSAssociation.keyword_id == keyword_id,
        KeywordRSSAssociation.rss_feed_id == rss_feed_id
    ).first()

    if not association:
        raise HTTPException(status_code=404, detail="Association not found")

    db.delete(association)
    db.commit()

    return {"message": "Association deleted successfully"}


# ============ 批量操作 ============

class BatchRSSAssociationRequest(BaseModel):
    """批量创建/更新 RSS 关联请求"""
    rss_feed_ids: List[str] = Field(..., description="RSS Feed ID 列表")
    filter_rules: Optional[FilterRulesSchema] = Field(default=None, description="统一过滤规则")
    is_active: Optional[bool] = Field(default=True)


@router.post("/{keyword_id}/rss-associations/batch")
async def batch_create_rss_associations(
    keyword_id: str,
    data: BatchRSSAssociationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """批量创建 RSS 关联"""
    # 检查监控主体是否存在
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    created_count = 0
    skipped_count = 0

    filter_rules = data.filter_rules.model_dump() if data.filter_rules else {
        "include_keywords": [],
        "exclude_keywords": [],
        "match_mode": "any",
        "title_only": False,
    }

    for rss_feed_id in data.rss_feed_ids:
        # 检查 RSS Feed 是否存在
        rss_feed = db.query(RSSFeed).filter(RSSFeed.id == rss_feed_id).first()
        if not rss_feed:
            skipped_count += 1
            continue

        # 检查是否已存在关联
        existing = db.query(KeywordRSSAssociation).filter(
            KeywordRSSAssociation.keyword_id == keyword_id,
            KeywordRSSAssociation.rss_feed_id == rss_feed_id
        ).first()

        if existing:
            # 更新现有关联
            existing.filter_rules = filter_rules
            existing.is_active = data.is_active
            created_count += 1
        else:
            # 创建新关联
            association = KeywordRSSAssociation(
                keyword_id=keyword_id,
                rss_feed_id=rss_feed_id,
                filter_rules=filter_rules,
                is_active=data.is_active,
            )
            db.add(association)
            created_count += 1

    db.commit()

    return {
        "message": f"成功处理 {created_count} 个关联，跳过 {skipped_count} 个无效 Feed"
    }


# ============ 立即刷新接口 ============

class RefreshResponse(BaseModel):
    """刷新响应"""
    task_id: str
    message: str
    keyword: str


@router.post("/{keyword_id}/refresh", response_model=RefreshResponse)
async def refresh_keyword(
    keyword_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """立即触发数据更新（使用默认参数）

    默认参数：
    - time_range: oneDay（最近 24 小时）
    - negative_mode: False（关闭负面模式）
    """
    from app.api.v1.collect.router import run_collect_task
    from app.services.redis_service import get_task_store

    # 查找关键词
    keyword_obj = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword_obj:
        raise HTTPException(status_code=404, detail="Keyword not found")

    # 获取任务存储
    task_store = await get_task_store()

    # 使用原子锁防止并发创建任务
    if not await task_store.acquire_lock(keyword_id):
        # 获取锁失败，说明已有任务在运行
        existing_task = await task_store.get_running_by_keyword_id(keyword_id)
        if existing_task:
            return RefreshResponse(
                task_id=existing_task["task_id"],
                message="该监控主体已有任务正在运行中",
                keyword=keyword_obj.keyword
            )
        # 如果没有找到运行中的任务，可能是锁残留，返回错误
        raise HTTPException(status_code=429, detail="请稍后重试，系统正在处理中")

    try:
        # 从 data_sources 提取 rss_ids
        rss_ids = []
        if keyword_obj.data_sources and isinstance(keyword_obj.data_sources, dict):
            rss_ids = keyword_obj.data_sources.get("rss_ids", [])

        # 创建任务
        task_id = str(uuid.uuid4())
        await task_store.create(task_id, {
            "task_id": task_id,
            "keyword_id": keyword_id,
            "keyword": keyword_obj.keyword,
            "status": "pending",
            "collected_count": 0,
            "message": "刷新任务已创建，等待执行",
            "created_at": now_cst().isoformat(),
            "finished_at": None,
        })

        # 更新最近扫描时间
        keyword_obj.last_fetched = now_cst()
        db.commit()

        # 添加后台任务（使用默认参数）
        background_tasks.add_task(
            run_collect_task,
            task_id,
            keyword_id,
            keyword_obj.keyword,
            keyword_obj.platforms or ["bocha", "tavily"],
            "oneDay",  # 默认时间范围：最近 24 小时
            False,     # 默认负面模式：关闭
            rss_ids
        )

        return RefreshResponse(
            task_id=task_id,
            message="刷新任务已创建",
            keyword=keyword_obj.keyword
        )
    except Exception as e:
        # 发生异常时释放锁
        await task_store.release_lock(keyword_id)
        raise
