# -*- coding: utf-8 -*-
"""RSS 订阅管理 API"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

from app.dependencies import get_db
from app.models.rss_feed import RSSFeed
from app.schedulers.rss_scheduler import fetch_feed

router = APIRouter()


# ==================== Schemas ====================

class RSSFeedCreate(BaseModel):
    """创建 RSS 订阅请求"""
    name: str = Field(..., description="订阅名称")
    feed_url: str = Field(..., description="RSS 订阅地址")
    source_type: Optional[str] = Field(default="generic", description="来源类型: weibo/zhihu/bilibili/generic")
    keyword_id: Optional[str] = Field(default=None, description="关联的监控主体 ID")
    fetch_interval: int = Field(default=300, description="轮询间隔（秒）")


class RSSFeedUpdate(BaseModel):
    """更新 RSS 订阅请求"""
    name: Optional[str] = None
    feed_url: Optional[str] = None
    source_type: Optional[str] = None
    keyword_id: Optional[str] = None
    fetch_interval: Optional[int] = None
    is_active: Optional[bool] = None


class RSSFeedResponse(BaseModel):
    """RSS 订阅响应"""
    id: str
    name: str
    feed_url: str
    source_type: Optional[str]
    keyword_id: Optional[str]
    is_active: bool
    last_fetched: Optional[datetime]
    fetch_error_count: int
    last_error: Optional[str]
    fetch_interval: int
    total_entries: int
    created_at: datetime

    class Config:
        from_attributes = True


class RSSFeedTestResponse(BaseModel):
    """RSS 订阅测试响应"""
    success: bool
    message: str
    entry_count: int = 0
    sample_titles: List[str] = []


class RSSHubURLBuild(BaseModel):
    """RSSHub URL 构建请求"""
    platform: str = Field(..., description="平台: weibo/zhihu/bilibili/xiaohongshu")
    params: dict = Field(default={}, description="参数")


# ==================== Routes ====================

@router.post("/", response_model=RSSFeedResponse)
async def create_feed(
    data: RSSFeedCreate,
    db: Session = Depends(get_db)
):
    """创建 RSS 订阅"""
    # 检查是否已存在相同 URL
    existing = db.query(RSSFeed).filter(
        RSSFeed.feed_url == data.feed_url
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="该 RSS 订阅已存在")

    feed = RSSFeed(
        id=str(uuid.uuid4()),
        name=data.name,
        feed_url=data.feed_url,
        source_type=data.source_type,
        keyword_id=data.keyword_id,
        fetch_interval=data.fetch_interval,
    )

    db.add(feed)
    db.commit()
    db.refresh(feed)

    return feed


@router.get("/", response_model=List[RSSFeedResponse])
async def list_feeds(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    source_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取 RSS 订阅列表"""
    query = db.query(RSSFeed)

    if is_active is not None:
        query = query.filter(RSSFeed.is_active == is_active)

    if source_type:
        query = query.filter(RSSFeed.source_type == source_type)

    feeds = query.order_by(RSSFeed.created_at.desc()).offset(skip).limit(limit).all()
    return feeds


@router.get("/{feed_id}", response_model=RSSFeedResponse)
async def get_feed(
    feed_id: str,
    db: Session = Depends(get_db)
):
    """获取单个 RSS 订阅详情"""
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()

    if not feed:
        raise HTTPException(status_code=404, detail="订阅不存在")

    return feed


@router.put("/{feed_id}", response_model=RSSFeedResponse)
async def update_feed(
    feed_id: str,
    data: RSSFeedUpdate,
    db: Session = Depends(get_db)
):
    """更新 RSS 订阅配置"""
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()

    if not feed:
        raise HTTPException(status_code=404, detail="订阅不存在")

    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(feed, key, value)

    feed.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(feed)

    return feed


@router.delete("/{feed_id}")
async def delete_feed(
    feed_id: str,
    db: Session = Depends(get_db)
):
    """删除 RSS 订阅"""
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()

    if not feed:
        raise HTTPException(status_code=404, detail="订阅不存在")

    db.delete(feed)
    db.commit()

    return {"message": "删除成功"}


@router.post("/{feed_id}/test", response_model=RSSFeedTestResponse)
async def test_feed(
    feed_id: str,
    db: Session = Depends(get_db)
):
    """测试 RSS 订阅是否可用"""
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()

    if not feed:
        raise HTTPException(status_code=404, detail="订阅不存在")

    try:
        from app.collectors.rss_collector import RSSCollector

        collector = RSSCollector()
        results, _, _, _ = await collector.fetch_feed(feed.feed_url)
        await collector.close()

        sample_titles = [r.title for r in results[:5]]

        return RSSFeedTestResponse(
            success=True,
            message=f"订阅正常，获取到 {len(results)} 条内容",
            entry_count=len(results),
            sample_titles=sample_titles
        )
    except Exception as e:
        return RSSFeedTestResponse(
            success=False,
            message=f"订阅失败: {str(e)}",
            entry_count=0,
            sample_titles=[]
        )


@router.post("/{feed_id}/fetch")
async def trigger_fetch(
    feed_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """手动触发获取 RSS 订阅"""
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()

    if not feed:
        raise HTTPException(status_code=404, detail="订阅不存在")

    # 后台执行获取任务
    from app.schedulers.rss_scheduler import fetch_feed as do_fetch
    saved_count = await do_fetch(feed, db)

    return {"message": f"获取完成，保存 {saved_count} 条文章"}


# ==================== RSSHub URL Builder ====================

RSSHUB_TEMPLATES = {
    "weibo": {
        "name": "微博",
        "routes": [
            {"path": "/weibo/keyword/{keyword}", "name": "关键词订阅", "params": ["keyword"]},
            {"path": "/weibo/user/{uid}", "name": "用户动态", "params": ["uid"]},
            {"path": "/weibo/super_index/{id}", "name": "超话", "params": ["id"]},
        ]
    },
    "zhihu": {
        "name": "知乎",
        "routes": [
            {"path": "/zhihu/hotlist", "name": "热榜", "params": []},
            {"path": "/zhihu/collection/{id}", "name": "收藏夹", "params": ["id"]},
            {"path": "/zhihu/people/{id}/answers", "name": "用户回答", "params": ["id"]},
        ]
    },
    "bilibili": {
        "name": "B站",
        "routes": [
            {"path": "/bilibili/user/dynamic/{uid}", "name": "用户动态", "params": ["uid"]},
            {"path": "/bilibili/search/{keyword}", "name": "关键词搜索", "params": ["keyword"]},
            {"path": "/bilibili/ranking/0/3", "name": "排行榜", "params": []},
        ]
    },
    "xiaohongshu": {
        "name": "小红书",
        "routes": [
            {"path": "/xiaohongshu/user/{user_id}", "name": "用户笔记", "params": ["user_id"]},
        ]
    },
    "douyin": {
        "name": "抖音",
        "routes": [
            {"path": "/douyin/user/{uid}", "name": "用户视频", "params": ["uid"]},
        ]
    },
    "toutiao": {
        "name": "今日头条",
        "routes": [
            {"path": "/toutiao/user/{uid}", "name": "用户文章", "params": ["uid"]},
        ]
    },
    "36kr": {
        "name": "36氪",
        "routes": [
            {"path": "/36kr/newsflashes", "name": "快讯", "params": []},
            {"path": "/36kr/news", "name": "资讯", "params": []},
        ]
    },
}


@router.get("/rsshub/platforms")
async def get_rsshub_platforms():
    """获取 RSSHub 支持的平台列表"""
    return {
        platform: {"name": info["name"], "routes": info["routes"]}
        for platform, info in RSSHUB_TEMPLATES.items()
    }


@router.post("/rsshub/build")
async def build_rsshub_url(
    data: RSSHubURLBuild,
    db: Session = Depends(get_db)
):
    """构建 RSSHub 订阅 URL"""
    from urllib.parse import quote
    from app.config import settings

    platform = data.platform
    params = data.params

    if platform not in RSSHUB_TEMPLATES:
        raise HTTPException(status_code=400, detail="不支持的平台")

    # 获取第一个路由模板
    template = RSSHUB_TEMPLATES[platform]["routes"][0]
    path = template["path"]

    # 替换参数
    for key, value in params.items():
        path = path.replace(f"{{{key}}}", quote(str(value)))

    # 使用配置的 RSSHub 实例或公共实例
    base_url = getattr(settings, 'rsshub_url', 'https://rsshub.app')
    full_url = f"{base_url}{path}"

    return {
        "url": full_url,
        "platform": platform,
        "route_name": template["name"]
    }
