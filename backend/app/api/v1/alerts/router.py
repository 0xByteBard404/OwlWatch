# -*- coding: utf-8 -*-
"""预警管理 API"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.dependencies import get_db
from app.models.alert import Alert
from app.models.user import User
from app.core.security import get_current_active_user
from app.services.alert_service import AlertService
from app.utils.timezone import now_cst

router = APIRouter()
logger = logging.getLogger(__name__)


class AlertResponse(BaseModel):
    """预警响应"""
    id: str
    keyword_id: str
    article_id: Optional[str]
    alert_type: Optional[str]
    alert_level: str
    status: str
    message: Optional[str]
    created_at: datetime
    handled_at: Optional[datetime]

    class Config:
        from_attributes = True


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
    by_level: dict
    by_type: dict


class BatchHandleRequest(BaseModel):
    """批量处理请求"""
    alert_ids: List[str] = Field(..., description="预警ID列表")


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    alert_level: Optional[str] = Query(default=None, description="Filter by level"),
    alert_type: Optional[str] = Query(default=None, description="Filter by type"),
    keyword_id: Optional[str] = Query(default=None, description="Filter by keyword"),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get alerts with filters"""
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
    items = query.order_by(Alert.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return AlertListResponse(items=items, total=total)


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    keyword_id: Optional[str] = Query(default=None, description="Filter by keyword"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get alert statistics"""
    base_query = db.query(Alert)
    if keyword_id:
        base_query = base_query.filter(Alert.keyword_id == keyword_id)

    # 总数和状态统计
    total = base_query.count()
    pending = base_query.filter(Alert.status == "pending").count()
    handled = base_query.filter(Alert.status == "handled").count()
    ignored = base_query.filter(Alert.status == "ignored").count()

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
        by_level=by_level,
        by_type=by_type
    )


@router.put("/{alert_id}/handle")
async def handle_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark alert as handled"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "handled"
    alert.handled_at = now_cst()

    db.commit()

    return {"message": "Alert handled successfully", "alert_id": alert_id}


@router.put("/{alert_id}/ignore")
async def ignore_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark alert as ignored"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "ignored"
    alert.handled_at = now_cst()

    db.commit()

    return {"message": "Alert ignored successfully", "alert_id": alert_id}


@router.post("/batch-handle")
async def batch_handle_alerts(
    request: BatchHandleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Batch handle alerts"""
    if not request.alert_ids:
        raise HTTPException(status_code=400, detail="No alert IDs provided")

    updated = db.query(Alert).filter(
        Alert.id.in_(request.alert_ids)
    ).update(
        {"status": "handled", "handled_at": now_cst()},
        synchronize_session=False
    )

    db.commit()

    return {
        "message": f"Successfully handled {updated} alerts",
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
        # 如果没有后台任务支持，直接发送
        alert_service = AlertService(db)
        try:
            await alert_service.send_notification(alert)
        except Exception as e:
            logger.error(f"Test notification failed: {e}")
        finally:
            await alert_service.close()

    return {
        "message": "Test alert created and notification triggered",
        "alert_id": alert.id,
        "alert_level": alert_level,
        "alert_type": alert_type
    }


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.delete(alert)
    db.commit()

    return {"message": "Alert deleted successfully", "alert_id": alert_id}
