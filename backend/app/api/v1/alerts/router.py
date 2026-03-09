# -*- coding: utf-8 -*-
"""预警管理 API"""
import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.dependencies import get_db
from app.models.alert import Alert
from app.models.article import Article
from app.models.keyword import Keyword
from app.models.user import User
from app.core.security import get_current_active_user
from app.services.alert_service import AlertService
from app.utils.timezone import now_cst

router = APIRouter()
logger = logging.getLogger(__name__)


# ============ Schema 定义 ============

class ArticleBrief(BaseModel):
    """文章简要信息"""
    id: str
    title: str
    url: str
    source: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    publish_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    """预警响应"""
    id: str
    keyword_id: str
    keyword_name: Optional[str] = None
    article_id: Optional[str] = None
    related_article_ids: List[str] = []
    alert_type: Optional[str]
    alert_level: str
    status: str
    message: Optional[str]
    # 处理信息
    handler_id: Optional[str] = None
    handler_name: Optional[str] = None
    handle_note: Optional[str] = None
    is_false_positive: bool = False
    # 时间
    created_at: datetime
    handled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertDetailResponse(BaseModel):
    """预警详情响应（包含关联文章）"""
    id: str
    keyword_id: str
    keyword_name: Optional[str] = None
    article_id: Optional[str] = None
    related_article_ids: List[str] = []
    related_articles: List[ArticleBrief] = []
    alert_type: Optional[str]
    alert_level: str
    status: str
    message: Optional[str]
    # 处理信息
    handler_id: Optional[str] = None
    handler_name: Optional[str] = None
    handle_note: Optional[str] = None
    is_false_positive: bool = False
    # 时间
    created_at: datetime
    handled_at: Optional[datetime] = None


class AlertListResponse(BaseModel):
    """预警列表响应"""
    items: List[AlertResponse]
    total: int


class AlertStatsResponse(BaseModel):
    """预警统计响应"""
    total: int
    pending: int
    handled: int
    ignored: int
    false_positive: int
    by_level: dict
    by_type: dict


class HandleRequest(BaseModel):
    """处理预警请求"""
    note: Optional[str] = Field(default=None, description="处理备注")


class BatchHandleRequest(BaseModel):
    """批量处理请求"""
    alert_ids: List[str] = Field(..., description="预警ID列表")
    note: Optional[str] = Field(default=None, description="处理备注")


class FalsePositiveRequest(BaseModel):
    """标记误报请求"""
    reason: Optional[str] = Field(default=None, description="误报原因")


# ============ 辅助函数 ============

def _parse_article_ids(article_ids_json: Optional[str]) -> List[str]:
    """解析关联文章ID列表"""
    if not article_ids_json:
        return []
    try:
        return json.loads(article_ids_json)
    except:
        return []


def _get_keyword_name(db: Session, keyword_id: str) -> Optional[str]:
    """获取监控主体名称"""
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    return keyword.keyword if keyword else None


def _build_alert_response(alert: Alert, db: Session) -> AlertResponse:
    """构建预警响应"""
    return AlertResponse(
        id=alert.id,
        keyword_id=alert.keyword_id,
        keyword_name=_get_keyword_name(db, alert.keyword_id),
        article_id=alert.article_id,
        related_article_ids=_parse_article_ids(alert.related_article_ids),
        alert_type=alert.alert_type,
        alert_level=alert.alert_level,
        status=alert.status,
        message=alert.message,
        handler_id=alert.handler_id,
        handler_name=alert.handler_name,
        handle_note=alert.handle_note,
        is_false_positive=alert.is_false_positive or False,
        created_at=alert.created_at,
        handled_at=alert.handled_at,
    )


# ============ API 端点 ============

@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = Query(default=None, description="状态筛选"),
    alert_level: Optional[str] = Query(default=None, description="级别筛选"),
    alert_type: Optional[str] = Query(default=None, description="类型筛选"),
    keyword_id: Optional[str] = Query(default=None, description="监控主体筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取预警列表"""
    query = db.query(Alert)

    if status:
        query = query.filter(Alert.status == status)
    if alert_level:
        query = query.filter(Alert.alert_level == alert_level)
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    if keyword_id:
        query = query.filter(Alert.keyword_id == keyword_id)

    total = query.count()
    alerts = query.order_by(Alert.created_at.desc()).offset((page - 1) * size).limit(size).all()

    items = [_build_alert_response(alert, db) for alert in alerts]

    return AlertListResponse(items=items, total=total)


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    keyword_id: Optional[str] = Query(default=None, description="监控主体筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取预警统计"""
    base_query = db.query(Alert)
    if keyword_id:
        base_query = base_query.filter(Alert.keyword_id == keyword_id)

    # 状态统计
    total = base_query.count()
    pending = base_query.filter(Alert.status == "pending").count()
    handled = base_query.filter(Alert.status == "handled").count()
    ignored = base_query.filter(Alert.status == "ignored").count()
    false_positive = base_query.filter(Alert.status == "false_positive").count()

    # 按级别统计
    level_stats = db.query(
        Alert.alert_level,
        func.count(Alert.id)
    ).group_by(Alert.alert_level).all()
    by_level = {level: count for level, count in level_stats}

    # 按类型统计
    type_stats = db.query(
        Alert.alert_type,
        func.count(Alert.id)
    ).filter(Alert.alert_type.isnot(None)).group_by(Alert.alert_type).all()
    by_type = {alert_type: count for alert_type, count in type_stats}

    return AlertStatsResponse(
        total=total,
        pending=pending,
        handled=handled,
        ignored=ignored,
        false_positive=false_positive,
        by_level=by_level,
        by_type=by_type
    )


@router.get("/{alert_id}", response_model=AlertDetailResponse)
async def get_alert_detail(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取预警详情（包含关联文章）"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")

    # 解析关联文章ID
    article_ids = _parse_article_ids(alert.related_article_ids)

    # 如果主文章ID存在但不在关联列表中，添加进去
    if alert.article_id and alert.article_id not in article_ids:
        article_ids.insert(0, alert.article_id)

    # 查询关联文章
    related_articles = []
    if article_ids:
        articles = db.query(Article).filter(Article.id.in_(article_ids)).all()
        # 按原始顺序排序
        article_map = {a.id: a for a in articles}
        for aid in article_ids:
            if aid in article_map:
                a = article_map[aid]
                related_articles.append(ArticleBrief(
                    id=a.id,
                    title=a.title,
                    url=a.url,
                    source=a.source,
                    sentiment_score=a.sentiment_score,
                    sentiment_label=a.sentiment_label,
                    publish_time=a.publish_time,
                ))

    return AlertDetailResponse(
        id=alert.id,
        keyword_id=alert.keyword_id,
        keyword_name=_get_keyword_name(db, alert.keyword_id),
        article_id=alert.article_id,
        related_article_ids=article_ids,
        related_articles=related_articles,
        alert_type=alert.alert_type,
        alert_level=alert.alert_level,
        status=alert.status,
        message=alert.message,
        handler_id=alert.handler_id,
        handler_name=alert.handler_name,
        handle_note=alert.handle_note,
        is_false_positive=alert.is_false_positive or False,
        created_at=alert.created_at,
        handled_at=alert.handled_at,
    )


@router.put("/{alert_id}/handle")
async def handle_alert(
    alert_id: str,
    request: HandleRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """标记预警为已处理"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")

    alert.status = "handled"
    alert.handled_at = now_cst()
    alert.handler_id = current_user.id
    alert.handler_name = current_user.username

    if request and request.note:
        alert.handle_note = request.note

    db.commit()

    logger.info(f"Alert {alert_id} handled by {current_user.username}")

    return {
        "message": "预警已处理",
        "alert_id": alert_id,
        "handler": current_user.username
    }


@router.put("/{alert_id}/ignore")
async def ignore_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """忽略预警"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")

    alert.status = "ignored"
    alert.handled_at = now_cst()
    alert.handler_id = current_user.id
    alert.handler_name = current_user.username

    db.commit()

    return {"message": "预警已忽略", "alert_id": alert_id}


@router.put("/{alert_id}/false-positive")
async def mark_false_positive(
    alert_id: str,
    request: FalsePositiveRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """标记为误报"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")

    alert.status = "false_positive"
    alert.is_false_positive = True
    alert.handled_at = now_cst()
    alert.handler_id = current_user.id
    alert.handler_name = current_user.username

    if request and request.reason:
        alert.handle_note = f"[误报] {request.reason}"

    db.commit()

    logger.info(f"Alert {alert_id} marked as false positive by {current_user.username}")

    return {
        "message": "已标记为误报",
        "alert_id": alert_id,
        "handler": current_user.username
    }


@router.post("/batch-handle")
async def batch_handle_alerts(
    request: BatchHandleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """批量处理预警"""
    if not request.alert_ids:
        raise HTTPException(status_code=400, detail="未提供预警ID")

    update_data = {
        "status": "handled",
        "handled_at": now_cst(),
        "handler_id": current_user.id,
        "handler_name": current_user.username,
    }

    if request.note:
        update_data["handle_note"] = request.note

    updated = db.query(Alert).filter(
        Alert.id.in_(request.alert_ids)
    ).update(update_data, synchronize_session=False)

    db.commit()

    return {
        "message": f"成功处理 {updated} 条预警",
        "updated_count": updated
    }


@router.post("/test")
async def test_alert(
    keyword_id: str = Query(..., description="关键词ID"),
    alert_level: str = Query(default="warning", description="预警级别"),
    alert_type: str = Query(default="negative_burst", description="预警类型"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """手动触发测试预警"""
    # 创建测试预警
    alert = Alert(
        id=str(uuid.uuid4()),
        keyword_id=keyword_id,
        alert_type=alert_type,
        alert_level=alert_level,
        status="pending",
        message="[测试] 这是一条测试预警"
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    logger.info(f"Test alert created: {alert.id}")

    # 触发通知（后台任务）
    async def send_test_notification():
        alert_service = AlertService(db)
        try:
            await alert_service.send_notification(alert)
        except Exception as e:
            logger.error(f"Test notification failed: {e}")
        finally:
            await alert_service.close()

    if background_tasks:
        background_tasks.add_task(send_test_notification)
    else:
        alert_service = AlertService(db)
        try:
            await alert_service.send_notification(alert)
        except Exception as e:
            logger.error(f"Test notification failed: {e}")
        finally:
            await alert_service.close()

    return {
        "message": "测试预警已创建",
        "alert_id": alert.id,
        "alert_level": alert_level,
        "alert_type": alert_type
    }


@router.post("/check/{keyword_id}")
async def check_keyword_alerts(
    keyword_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="检查最近多少小时的文章"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """手动触发预警检查（用于测试预警功能）"""
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="监控主体不存在")

    alert_service = AlertService(db)
    try:
        await alert_service.check_and_alert(keyword_id, hours=hours)
        return {
            "message": f"预警检查已完成",
            "keyword_id": keyword_id,
            "keyword": keyword.keyword,
            "hours": hours
        }
    except Exception as e:
        logger.error(f"Alert check failed: {e}")
        raise HTTPException(status_code=500, detail=f"预警检查失败: {str(e)}")
    finally:
        await alert_service.close()


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除预警"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")

    db.delete(alert)
    db.commit()

    return {"message": "预警已删除", "alert_id": alert_id}
