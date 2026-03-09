# -*- coding: utf-8 -*-
"""用户模型"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from ..utils.timezone import now_cst
from ..database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default="user")  # admin, user, viewer
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now_cst)
    updated_at = Column(DateTime, default=now_cst, onupdate=now_cst)
    last_login_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.username}>"
