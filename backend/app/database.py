"""数据库连接模块"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import settings

# 根据数据库类型配置连接参数
database_url = settings.database_url
is_sqlite = database_url.startswith("sqlite")
is_postgresql = database_url.startswith("postgresql")

# 配置引擎参数
engine_kwargs = {
    "echo": settings.debug if hasattr(settings, 'debug') else False,
    "pool_pre_ping": True,
}

# SQLite 专用配置
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
# PostgreSQL 专用配置
elif is_postgresql:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 3600

# 创建数据库引擎
engine = create_engine(database_url, **engine_kwargs)


# SQLite WAL 模式支持并发读写
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """设置 SQLite PRAGMA 以支持并发"""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
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
