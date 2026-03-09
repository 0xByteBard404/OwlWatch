# -*- coding: utf-8 -*-
"""
认证 API - 完整重写版

功能:
1. 用户注册 (密码强度验证)
2. OAuth2 兼容登录
3. Token 刷新
4. 获取当前用户信息
5. 修改密码
6. Token 验证 (修复依赖注入)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from datetime import timedelta
import uuid

from app.config import settings
from app.dependencies import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_active_user,
    get_current_user_required,
    validate_password_strength
)
from app.utils.timezone import now_cst

auth_router = APIRouter()


# ===== Pydantic 模型 =====

class UserCreate(BaseModel):
    """用户注册"""
    username: str
    email: EmailStr
    password: str
    full_name: str = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be at least 8 characters with "
                "uppercase, lowercase, digit, and special character"
            )
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be between 3 and 50 characters")
        if not v.isalnum() and '_' not in v:
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return v


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    username: str
    email: str
    full_name: str = None
    role: str
    is_active: bool
    tenant_id: str
    created_at: str
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordChange(BaseModel):
    """修改密码"""
    old_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be at least 8 characters with "
                "uppercase, lowercase, digit, and special character"
            )
        return v


# ===== API 端点 =====

@auth_router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册"""
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 创建或获取默认租户
    tenant = db.query(Tenant).filter(Tenant.id == settings.default_tenant_id).first()
    if not tenant:
        tenant = Tenant(
            id=settings.default_tenant_id,
            name=settings.default_tenant_name,
            plan_type="basic"
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    
    # 创建用户
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role="user",
        is_active=True,
        is_superuser=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        tenant_id=user.tenant_id,
        created_at=user.created_at.isoformat() if user.created_at else ""
    )


@auth_router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录 (OAuth2兼容)"""
    # 查找用户
    user = db.query(User).filter(
        User.username == form_data.username
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证密码
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    # 更新最后登录时间
    user.last_login_at = now_cst()
    db.commit()
    
    # 创建访问令牌
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "role": user.role
        }
    )
    
    expires_in = getattr(settings, 'jwt_access_token_expire_hours', 24) * 3600
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )


@auth_router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
):
    """刷新访问令牌"""
    access_token = create_access_token(
        data={
            "sub": current_user.username,
            "user_id": current_user.id,
            "tenant_id": current_user.tenant_id,
            "role": current_user.role
        }
    )
    
    expires_in = getattr(settings, 'jwt_access_token_expire_hours', 24) * 3600
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        tenant_id=current_user.tenant_id,
        created_at=current_user.created_at.isoformat() if current_user.created_at else ""
    )


@auth_router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # 更新密码
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.updated_at = now_cst()
    db.commit()
    
    return {"message": "Password updated successfully"}


@auth_router.post("/verify")
async def verify_token(
    current_user: User = Depends(get_current_user_required)
):
    """验证当前Token（已修复）"""
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }