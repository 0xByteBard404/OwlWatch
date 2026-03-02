# -*- coding: utf-8 -*-
"""分析报告 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.dependencies import get_db
from app.models.report import Report

router = APIRouter()


class ReportCreate(BaseModel):
    """创建报告请求"""
    report_type: str = Field(default="daily", description="Report type: daily/weekly/monthly")
    keywords: List[str] = Field(default=[], description="Keyword IDs to include")


class ReportResponse(BaseModel):
    """报告响应"""
    id: str
    tenant_id: str
    title: str
    content: Optional[str]
    report_type: str
    generated_at: datetime

    class Config:
        from_attributes = True


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    data: ReportCreate,
    db: Session = Depends(get_db)
):
    """Generate analysis report"""
    # TODO: Implement actual report generation logic
    import uuid
    report = Report(
        id=str(uuid.uuid4()),
        tenant_id="default-tenant",
        title=f"Sentiment Analysis Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
        content="Report generation in progress...",
        report_type=data.report_type,
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    report_type: Optional[str] = Query(default=None, description="Filter by type"),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=10, ge=1, le=50, description="Page size"),
    db: Session = Depends(get_db)
):
    """Get reports list"""
    query = db.query(Report)

    if report_type:
        query = query.filter(Report.report_type == report_type)

    reports = query.order_by(Report.generated_at.desc()).offset((page - 1) * size).limit(size).all()
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """Get report details"""
    report = db.query(Report).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return report
