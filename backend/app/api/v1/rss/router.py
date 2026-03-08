# -*- coding: utf-8 -*-
"""RSS 订阅管理 API"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import uuid
import json
import os

from app.dependencies import get_db
from app.models.rss_feed import RSSFeed
from app.models.rsshub_config import RSSHubConfig
from app.schedulers.rss_scheduler import fetch_feed
from app.utils.timezone import now_cst

router = APIRouter()


# ==================== Schemas ====================

class RSSFeedCreate(BaseModel):
    """创建 RSS 订阅请求"""
    name: str = Field(..., description="订阅名称")
    feed_url: str = Field(..., description="RSS 订阅地址")
    source_type: Optional[str] = Field(default="generic", description="来源类型: weibo/zhihu/bilibili/generic")
    # keyword_id 已废弃，请在监控主体中配置数据源
    fetch_interval: int = Field(default=300, description="轮询间隔（秒）")


class RSSFeedUpdate(BaseModel):
    """更新 RSS 订阅请求"""
    name: Optional[str] = None
    feed_url: Optional[str] = None
    source_type: Optional[str] = None
    fetch_interval: Optional[int] = None
    is_active: Optional[bool] = None


class RSSFeedResponse(BaseModel):
    """RSS 订阅响应"""
    id: str
    name: str
    feed_url: str
    source_type: Optional[str]
    # keyword_id 已废弃
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
    route_path: str = Field(default="", description="路由路径")
    params: dict = Field(default={}, description="参数")


# ==================== RSSHub 配置 Schemas ====================

class RSSHubConfigCreate(BaseModel):
    """创建 RSSHub 配置"""
    platform: str = Field(..., description="平台标识")
    display_name: str = Field(..., description="显示名称")
    config_type: str = Field(default="cookie", description="配置类型: cookie/api_key/token/custom")
    config_value: str = Field(..., description="配置值")
    description: Optional[str] = Field(default=None, description="使用说明")


class RSSHubConfigUpdate(BaseModel):
    """更新 RSSHub 配置"""
    display_name: Optional[str] = None
    config_type: Optional[str] = None
    config_value: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RSSHubConfigResponse(BaseModel):
    """RSSHub 配置响应"""
    id: str
    platform: str
    display_name: str
    config_type: str
    config_value: str  # 前端显示时脱敏
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# RSSHub 平台配置模板（定义哪些平台需要什么配置）
RSSHUB_CONFIG_TEMPLATES = {
    "wechat": {
        "display_name": "微信公众号",
        "config_type": "none",
        "description": "不需要任何配置！推荐使用搜狗搜索，直接输入公众号名称即可订阅",
        "env_key": "",
    },
    "weibo": {
        "display_name": "微博",
        "config_type": "cookie",
        "description": "需要微博 Cookie 以获取更多内容。获取方法：登录 weibo.com，复制 Cookie",
        "env_key": "WEIBO_COOKIE",
    },
    "zhihu": {
        "display_name": "知乎",
        "config_type": "cookie",
        "description": "需要知乎 Cookie 以获取更多内容。获取方法：登录 zhihu.com，复制 Cookie",
        "env_key": "ZHIHU_COOKIE",
    },
    "bilibili": {
        "display_name": "B站",
        "config_type": "cookie",
        "description": "需要 B站 Cookie 以获取更多内容。获取方法：登录 bilibili.com，复制 Cookie",
        "env_key": "BILIBILI_COOKIE",
    },
    "xiaohongshu": {
        "display_name": "小红书",
        "config_type": "cookie",
        "description": "需要小红书 Cookie。获取方法：登录 xiaohongshu.com，复制 Cookie",
        "env_key": "XIAOHONGSHU_COOKIE",
    },
    "twitter": {
        "display_name": "Twitter/X",
        "config_type": "custom",
        "description": "需要 Twitter 认证信息。格式: {\"auth_token\": \"xxx\", \"ct0\": \"xxx\"}",
        "env_key": "TWITTER_AUTH",
    },
    "instagram": {
        "display_name": "Instagram",
        "config_type": "custom",
        "description": "需要 Instagram Cookie。获取方法：登录 instagram.com，复制 Cookie",
        "env_key": "INSTAGRAM_COOKIE",
    },
    "youtube": {
        "display_name": "YouTube",
        "config_type": "api_key",
        "description": "需要 YouTube API Key。获取方法：Google Cloud Console 创建项目获取",
        "env_key": "YOUTUBE_KEY",
    },
    "github": {
        "display_name": "GitHub",
        "config_type": "token",
        "description": "可选 GitHub Token 提高 API 限制。获取方法：GitHub Settings > Developer settings > Personal access tokens",
        "env_key": "GITHUB_TOKEN",
    },
}


# ==================== RSSHub 配置管理 API ====================

def mask_config_value(value: str, show_length: int = 8) -> str:
    """脱敏显示配置值"""
    if not value:
        return ""
    if len(value) <= show_length:
        return "*" * len(value)
    return value[:show_length//2] + "*" * (len(value) - show_length) + value[-show_length//2:]


@router.get("/configs/templates")
async def get_config_templates():
    """获取需要配置的平台模板列表"""
    return RSSHUB_CONFIG_TEMPLATES


@router.get("/configs", response_model=List[RSSHubConfigResponse])
async def list_configs(db: Session = Depends(get_db)):
    """获取所有 RSSHub 配置"""
    configs = db.query(RSSHubConfig).all()
    # 脱敏处理
    result = []
    for config in configs:
        config_dict = {
            "id": config.id,
            "platform": config.platform,
            "display_name": config.display_name,
            "config_type": config.config_type,
            "config_value": mask_config_value(config.config_value) if config.config_value else "",
            "description": config.description,
            "is_active": config.is_active,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }
        result.append(RSSHubConfigResponse(**config_dict))
    return result


@router.post("/configs", response_model=RSSHubConfigResponse)
async def create_config(
    data: RSSHubConfigCreate,
    db: Session = Depends(get_db)
):
    """创建或更新 RSSHub 配置"""
    # 检查是否已存在
    existing = db.query(RSSHubConfig).filter(
        RSSHubConfig.platform == data.platform
    ).first()

    if existing:
        # 更新
        existing.display_name = data.display_name
        existing.config_type = data.config_type
        existing.config_value = data.config_value
        existing.description = data.description
        existing.updated_at = now_cst()
        db.commit()
        db.refresh(existing)
        config = existing
    else:
        # 创建
        config = RSSHubConfig(
            id=str(uuid.uuid4()),
            platform=data.platform,
            display_name=data.display_name,
            config_type=data.config_type,
            config_value=data.config_value,
            description=data.description,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return RSSHubConfigResponse(
        id=config.id,
        platform=config.platform,
        display_name=config.display_name,
        config_type=config.config_type,
        config_value=mask_config_value(config.config_value) if config.config_value else "",
        description=config.description,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """删除 RSSHub 配置"""
    config = db.query(RSSHubConfig).filter(RSSHubConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    db.delete(config)
    db.commit()
    return {"message": "删除成功"}


@router.post("/configs/{config_id}/test")
async def test_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """测试 RSSHub 配置是否有效"""
    config = db.query(RSSHubConfig).filter(RSSHubConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 根据平台构建测试 URL
    test_urls = {
        "wechat": "/wechat/mp/msgalbum/MzU1MTE1MjU5Nw%3D%3D",
        "weibo": "/weibo/user/haoyunyizhou",
        "zhihu": "/zhihu/hotlist",
        "bilibili": "/bilibili/ranking/0/3",
        "xiaohongshu": "/xiaohongshu/user/5e1568321e87dd0001c4cc4f",
        "twitter": "/twitter/user/elonmusk",
        "youtube": "/youtube/user/MrBeast",
        "github": "/github/trending/daily/javascript",
    }

    platform = config.platform
    test_path = test_urls.get(platform, f"/{platform}")

    # 调用 RSSHub 测试
    import httpx
    from app.config import settings

    rsshub_url = getattr(settings, 'rsshub_url', 'http://rsshub:1200')

    # 构建请求头，注入配置
    headers = {}
    if config.config_type == "cookie":
        headers["Cookie"] = config.config_value
    elif config.config_type == "api_key":
        headers["X-API-Key"] = config.config_value
    elif config.config_type == "token":
        headers["Authorization"] = f"Bearer {config.config_value}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{rsshub_url}{test_path}", headers=headers)

            if response.status_code == 200:
                return {"success": True, "message": "配置有效，连接成功"}
            else:
                return {"success": False, "message": f"配置可能无效，HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


# ==================== RSS 订阅 Routes ====================

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

    feed.updated_at = now_cst()
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
    # ==================== 社交媒体 ====================
    "weibo": {
        "name": "微博",
        "category": "社交媒体",
        "routes": [
            {"path": "/weibo/keyword/{keyword}", "name": "关键词订阅", "params": ["keyword"]},
            {"path": "/weibo/user/{uid}", "name": "用户动态", "params": ["uid"]},
            {"path": "/weibo/super_index/{id}", "name": "超话", "params": ["id"]},
            {"path": "/weibo/search/{keyword}", "name": "搜索", "params": ["keyword"]},
        ]
    },
    "zhihu": {
        "name": "知乎",
        "category": "社交媒体",
        "routes": [
            {"path": "/zhihu/hotlist", "name": "热榜", "params": []},
            {"path": "/zhihu/collection/{id}", "name": "收藏夹", "params": ["id"]},
            {"path": "/zhihu/people/{id}/answers", "name": "用户回答", "params": ["id"]},
            {"path": "/zhihu/people/{id}/posts", "name": "用户文章", "params": ["id"]},
            {"path": "/zhihu/topic/{id}/hot", "name": "话题热门", "params": ["id"]},
        ]
    },
    "bilibili": {
        "name": "B站",
        "category": "社交媒体",
        "routes": [
            {"path": "/bilibili/user/dynamic/{uid}", "name": "用户动态", "params": ["uid"]},
            {"path": "/bilibili/user/video/{uid}", "name": "用户视频", "params": ["uid"]},
            {"path": "/bilibili/search/{keyword}", "name": "关键词搜索", "params": ["keyword"]},
            {"path": "/bilibili/ranking/0/3", "name": "排行榜", "params": []},
            {"path": "/bilibili/popular", "name": "综合热门", "params": []},
        ]
    },
    "xiaohongshu": {
        "name": "小红书",
        "category": "社交媒体",
        "routes": [
            {"path": "/xiaohongshu/user/{user_id}", "name": "用户笔记", "params": ["user_id"]},
            {"path": "/xiaohongshu/search/{keyword}", "name": "关键词搜索", "params": ["keyword"]},
        ]
    },
    "douyin": {
        "name": "抖音",
        "category": "社交媒体",
        "routes": [
            {"path": "/douyin/user/{uid}", "name": "用户视频", "params": ["uid"]},
        ]
    },
    "twitter": {
        "name": "Twitter/X",
        "category": "社交媒体",
        "routes": [
            {"path": "/twitter/user/{id}", "name": "用户推文", "params": ["id"]},
            {"path": "/twitter/search/{keyword}", "name": "关键词搜索", "params": ["keyword"]},
            {"path": "/twitter/list/{id}", "name": "列表", "params": ["id"]},
        ]
    },
    "instagram": {
        "name": "Instagram",
        "category": "社交媒体",
        "routes": [
            {"path": "/instagram/user/{username}", "name": "用户动态", "params": ["username"]},
            {"path": "/instagram/tag/{tag}", "name": "标签", "params": ["tag"]},
        ]
    },
    "threads": {
        "name": "Threads",
        "category": "社交媒体",
        "routes": [
            {"path": "/threads/{username}", "name": "用户动态", "params": ["username"]},
        ]
    },

    # ==================== 即时通讯/资讯 ====================
    "wechat": {
        "name": "微信公众号",
        "category": "资讯平台",
        "routes": [
            {"path": "/wechat/sogou/{id}", "name": "搜狗搜索（推荐）", "params": ["id"], "help": "无需任何配置！直接输入公众号名称即可订阅，例如：人民日报、央视新闻"},
            {"path": "/wechat/mp/msgalbum/{biz}/{aid}", "name": "公众号文章话题", "params": ["biz", "aid"], "help": "从公众号文章Tag链接获取：album_id=xxx，biz 和 aid 分别对应这两个值"},
            {"path": "/wechat/mp/homepage/{biz}/{hid}", "name": "公众号栏目", "params": ["biz", "hid"], "help": "从公众号首页链接获取：__biz=xxx&hid=yyy"},
        ]
    },
    "toutiao": {
        "name": "今日头条",
        "category": "资讯平台",
        "routes": [
            {"path": "/toutiao/user/{uid}", "name": "用户文章", "params": ["uid"]},
            {"path": "/toutiao/keyword/{keyword}", "name": "关键词", "params": ["keyword"]},
        ]
    },
    "dianping": {
        "name": "大众点评",
        "category": "生活服务",
        "routes": [
            {"path": "/dianping/user/{uid}", "name": "用户点评", "params": ["uid"]},
        ]
    },

    # ==================== 视频平台 ====================
    "youtube": {
        "name": "YouTube",
        "category": "视频平台",
        "routes": [
            {"path": "/youtube/user/{username}", "name": "用户视频", "params": ["username"]},
            {"path": "/youtube/channel/{id}", "name": "频道视频", "params": ["id"]},
            {"path": "/youtube/playlist/{id}", "name": "播放列表", "params": ["id"]},
        ]
    },
    "tiktok": {
        "name": "TikTok",
        "category": "视频平台",
        "routes": [
            {"path": "/tiktok/user/{uid}", "name": "用户视频", "params": ["uid"]},
        ]
    },

    # ==================== 财经科技 ====================
    "36kr": {
        "name": "36氪",
        "category": "财经科技",
        "routes": [
            {"path": "/36kr/newsflashes", "name": "快讯", "params": []},
            {"path": "/36kr/news", "name": "资讯", "params": []},
            {"path": "/36kr/motif/{id}", "name": "专题", "params": ["id"]},
        ]
    },
    "wallstreetcn": {
        "name": "华尔街见闻",
        "category": "财经科技",
        "routes": [
            {"path": "/wallstreetcn/news/global", "name": "全球市场", "params": []},
            {"path": "/wallstreetcn/news/a-shares", "name": "A股", "params": []},
        ]
    },
    "cls": {
        "name": "财联社",
        "category": "财经科技",
        "routes": [
            {"path": "/cls/telegraph", "name": "电报", "params": []},
            {"path": "/cls/depth", "name": "深度", "params": []},
        ]
    },
    "solidot": {
        "name": "奇客Solidot",
        "category": "财经科技",
        "routes": [
            {"path": "/solidot", "name": "全部", "params": []},
        ]
    },
    "hackernews": {
        "name": "Hacker News",
        "category": "财经科技",
        "routes": [
            {"path": "/hackernews/best", "name": "最佳", "params": []},
            {"path": "/hackernews/newest", "name": "最新", "params": []},
        ]
    },
    "producthunt": {
        "name": "Product Hunt",
        "category": "财经科技",
        "routes": [
            {"path": "/producthunt/today", "name": "今日热门", "params": []},
        ]
    },

    # ==================== 社区论坛 ====================
    "tieba": {
        "name": "百度贴吧",
        "category": "社区论坛",
        "routes": [
            {"path": "/tieba/forum/{kw}", "name": "吧内帖子", "params": ["kw"]},
            {"path": "/tieba/forum/{kw}/good", "name": "吧内精品", "params": ["kw"]},
        ]
    },
    "douban": {
        "name": "豆瓣",
        "category": "社区论坛",
        "routes": [
            {"path": "/douban/movie/playing", "name": "正在上映", "params": []},
            {"path": "/douban/group/{id}", "name": "小组话题", "params": ["id"]},
            {"path": "/douban/people/{id}/notes", "name": "用户日记", "params": ["id"]},
        ]
    },
    "reddit": {
        "name": "Reddit",
        "category": "社区论坛",
        "routes": [
            {"path": "/reddit/subreddit/{subreddit}", "name": "子版块", "params": ["subreddit"]},
            {"path": "/reddit/search/{keyword}", "name": "搜索", "params": ["keyword"]},
        ]
    },
    "v2ex": {
        "name": "V2EX",
        "category": "社区论坛",
        "routes": [
            {"path": "/v2ex/topics/hot", "name": "热门", "params": []},
            {"path": "/v2ex/topics/latest", "name": "最新", "params": []},
            {"path": "/v2ex/tab/{tab}", "name": "节点", "params": ["tab"]},
        ]
    },
    "discourse": {
        "name": "Discourse 论坛",
        "category": "社区论坛",
        "routes": [
            {"path": "/discourse/{domain}/latest", "name": "最新话题", "params": ["domain"]},
        ]
    },

    # ==================== 新闻媒体 ====================
    "bbc": {
        "name": "BBC",
        "category": "新闻媒体",
        "routes": [
            {"path": "/bbc/chinese", "name": "中文网", "params": []},
        ]
    },
    "cnn": {
        "name": "CNN",
        "category": "新闻媒体",
        "routes": [
            {"path": "/cnn", "name": "最新", "params": []},
        ]
    },
    "nytimes": {
        "name": "纽约时报",
        "category": "新闻媒体",
        "routes": [
            {"path": "/nytimes/dual_language", "name": "中英双语", "params": []},
        ]
    },
    "reuters": {
        "name": "路透社",
        "category": "新闻媒体",
        "routes": [
            {"path": "/reuters/theWire", "name": "最新", "params": []},
        ]
    },
    "dw": {
        "name": "德国之声",
        "category": "新闻媒体",
        "routes": [
            {"path": "/dw/chinese", "name": "中文网", "params": []},
        ]
    },
    "rfi": {
        "name": "法广",
        "category": "新闻媒体",
        "routes": [
            {"path": "/rfi/china", "name": "中国", "params": []},
        ]
    },
    "thepaper": {
        "name": "澎湃新闻",
        "category": "新闻媒体",
        "routes": [
            {"path": "/thepaper/featured", "name": "头条", "params": []},
            {"path": "/thepaper/list/{id}", "name": "栏目", "params": ["id"]},
        ]
    },
    "sina": {
        "name": "新浪新闻",
        "category": "新闻媒体",
        "routes": [
            {"path": "/sina/rollnews", "name": "滚动新闻", "params": []},
        ]
    },
    "netease": {
        "name": "网易新闻",
        "category": "新闻媒体",
        "routes": [
            {"path": "/netease/news/rank", "name": "排行榜", "params": []},
        ]
    },
    "ifeng": {
        "name": "凤凰网",
        "category": "新闻媒体",
        "routes": [
            {"path": "/ifeng/hot", "name": "热点", "params": []},
        ]
    },
    "caixin": {
        "name": "财新网",
        "category": "新闻媒体",
        "routes": [
            {"path": "/caixin/headlines", "name": "头条", "params": []},
        ]
    },
    "guancha": {
        "name": "观察者网",
        "category": "新闻媒体",
        "routes": [
            {"path": "/guancha/headline", "name": "头条", "params": []},
        ]
    },

    # ==================== 开发者 ====================
    "github": {
        "name": "GitHub",
        "category": "开发者",
        "routes": [
            {"path": "/github/trending/daily/{language}", "name": "趋势", "params": ["language"]},
            {"path": "/github/repos/{user}", "name": "用户仓库", "params": ["user"]},
            {"path": "/github/starred_repos/{user}", "name": "用户 Star", "params": ["user"]},
            {"path": "/github/issue/{user}/{repo}", "name": "Issues", "params": ["user", "repo"]},
        ]
    },
    "npm": {
        "name": "NPM",
        "category": "开发者",
        "routes": [
            {"path": "/npm/package/{pkg}", "name": "包更新", "params": ["pkg"]},
        ]
    },
    "pypi": {
        "name": "PyPI",
        "category": "开发者",
        "routes": [
            {"path": "/pypi/package/{pkg}", "name": "包更新", "params": ["pkg"]},
        ]
    },
    "dockerhub": {
        "name": "Docker Hub",
        "category": "开发者",
        "routes": [
            {"path": "/dockerhub/build/{namespace}/{repo}", "name": "构建状态", "params": ["namespace", "repo"]},
        ]
    },

    # ==================== 学术 ====================
    "arxiv": {
        "name": "arXiv",
        "category": "学术",
        "routes": [
            {"path": "/arxiv/{query}", "name": "搜索", "params": ["query"]},
        ]
    },
    "scholar": {
        "name": "Google Scholar",
        "category": "学术",
        "routes": [
            {"path": "/google/scholar/{keyword}", "name": "关键词", "params": ["keyword"]},
        ]
    },

    # ==================== 设计 ====================
    "dribbble": {
        "name": "Dribbble",
        "category": "设计",
        "routes": [
            {"path": "/dribbble/popular", "name": "热门", "params": []},
        ]
    },
    "behance": {
        "name": "Behance",
        "category": "设计",
        "routes": [
            {"path": "/behance/search/{keyword}", "name": "搜索", "params": ["keyword"]},
        ]
    },
    "pinterest": {
        "name": "Pinterest",
        "category": "设计",
        "routes": [
            {"path": "/pinterest/search/{keyword}", "name": "搜索", "params": ["keyword"]},
        ]
    },
    "weread": {
        "name": "微信读书",
        "category": "阅读",
        "routes": [
            {"path": "/weread/user/{id}", "name": "用户书架", "params": ["id"], "help": "用户 ID 获取方法：微信读书 App > 我的 > 点击头像 > 复制个人主页链接中的数字 ID"},
        ]
    },
}


@router.get("/rsshub/platforms")
async def get_rsshub_platforms():
    """获取 RSSHub 支持的平台列表"""
    return {
        platform: {
            "name": info["name"],
            "category": info.get("category", "其他"),
            "routes": info["routes"]
        }
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
    route_path = data.route_path
    params = data.params

    if platform not in RSSHUB_TEMPLATES:
        raise HTTPException(status_code=400, detail="不支持的平台")

    # 查找匹配的路由模板
    template = None
    for route in RSSHUB_TEMPLATES[platform]["routes"]:
        if route["path"] == route_path:
            template = route
            break

    # 如果没有匹配的路由，使用第一个
    if not template:
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
