# -*- coding: utf-8 -*-
"""数据采集模块"""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from urllib.parse import urlparse

from ..utils.timezone import now_cst


def extract_domain_from_url(url: str) -> str:
    """从 URL 中提取域名作为来源"""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # 移除 www. 前缀
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


class CollectResult(BaseModel):
    """统一采集结果格式"""
    keyword: str = Field(..., description="搜索关键词")
    title: str = Field(..., description="标题")
    content: str = Field(default="", description="内容摘要")
    url: str = Field(..., description="原文链接")
    source: str = Field(default="", description="来源平台")
    source_type: str = Field(..., description="API来源")
    publish_time: Optional[datetime] = Field(default=None, description="发布时间")
    collect_time: datetime = Field(default_factory=now_cst, description="采集时间")
    sentiment_score: Optional[float] = Field(default=None, description="情感分数")
    extra: Optional[dict] = Field(default=None, description="扩展字段")


class CollectRequest(BaseModel):
    """采集请求参数"""
    keyword: str = Field(..., description="搜索关键词")
    max_results: int = Field(default=50, description="最大返回结果数")
    time_range: Optional[str] = Field(default="noLimit", description="时间范围")
    platforms: Optional[List[str]] = Field(default=None, description="指定平台")
