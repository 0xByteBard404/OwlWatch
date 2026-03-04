"""FastAPI 主应用"""
import asyncio
import sys
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Windows 上需要设置事件循环策略以支持子进程
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def _setup_file_logging():
    """设置文件日志和控制台日志"""
    # 检查是否已配置
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            return

    log_format = "%(asctime)s %(levelname)s %(name)s %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    root_logger.setLevel(logging.DEBUG)

    # 控制台日志（Docker 需要输出到 stdout）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(console_handler)

    # 文件日志（仅在非 Docker 环境或目录可写时启用）
    try:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"owlwatch_{today}.log")

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=7,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
        root_logger.addHandler(file_handler)
    except Exception as e:
        # 文件日志创建失败时仅使用控制台日志
        root_logger.warning(f"Failed to create log file: {e}")

    # 降低第三方库日志级别
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


_setup_file_logging()
logger = logging.getLogger(__name__)

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

    # 初始化 Redis 连接（用于任务状态存储）
    try:
        from .services.redis_service import get_redis
        await get_redis()
        logger.info("Redis 连接已初始化")
    except Exception as e:
        logger.warning(f"Redis 连接失败，任务状态将无法跨进程共享: {e}")

    logger.info("OwlWatch 舆情监控系统已启动")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    # 关闭 Redis 连接
    try:
        from .services.redis_service import close_redis
        await close_redis()
    except Exception as e:
        logger.debug(f"关闭 Redis 连接时出错: {e}")

    logger.info("OwlWatch 舆情监控系统正在关闭...")
