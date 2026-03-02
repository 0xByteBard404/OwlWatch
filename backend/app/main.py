"""FastAPI 主应用"""
import asyncio
import sys

# Windows 上需要设置事件循环策略以支持子进程
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base

# 导入模型以注册到 SQLAlchemy
from .models.keyword import Keyword
from .models.article import Article
from .models.alert import Alert
from .models.report import Report
from .models.negative_keyword import NegativeKeyword

# 导入路由
from .api.v1.auth import auth_router
from .api.v1.keywords.router import router as keywords_router
from .api.v1.articles.router import router as articles_router
from .api.v1.alerts.router import router as alerts_router
from .api.v1.reports.router import router as reports_router
from .api.v1.collect.router import router as collect_router
from .api.v1.negative_keywords.router import router as negative_keywords_router

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OwlWatch 舆情监控系统",
    description="基于 Tavily、Anspire、Bocha API 的舆情监控平台",
    version="0.1.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(keywords_router, prefix="/api/v1/keywords")
app.include_router(articles_router, prefix="/api/v1/articles")
app.include_router(alerts_router, prefix="/api/v1/alerts")
app.include_router(reports_router, prefix="/api/v1/reports")
app.include_router(collect_router, prefix="/api/v1/collect")
app.include_router(negative_keywords_router, prefix="/api/v1/negative-keywords")


@app.get("/")
async def root():
    return {"message": "OwlWatch API is running", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    import os
    # 测试环境禁用调度器
    if os.environ.get("DISABLE_SCHEDULER") != "true":
        from .schedulers import start_scheduler
        # 启动调度器
        start_scheduler()
    print("OwlWatch 舆情监控系统已启动")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    print("OwlWatch 舆情监控系统正在关闭...")
