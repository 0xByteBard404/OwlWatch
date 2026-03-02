"""依赖注入模块"""
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from .database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
