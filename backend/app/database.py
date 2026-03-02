"""数据库连接模块"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import settings

# 数据库引擎（增加超时时间）
engine = create_engine(
    settings.database_url,
    echo=settings.debug if hasattr(settings, 'debug') else False,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False, "timeout": 30}  # SQLite 专用配置
)


# 启用 WAL 模式支持并发读写
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """设置 SQLite PRAGMA 以支持并发"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30秒超时
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


# 会话工厂
SessionLocal = sessionmaker(autocommit=False, bind=engine)


# 声明式基类
Base = declarative_base()


def get_db():
    """获取数据库会话（用于依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
