# -*- coding: utf-8 -*-
"""认证 API"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from typing import Optional
import jwt
from pydantic import BaseModel

from app.config import settings
from app.dependencies import get_db

auth_router = APIRouter()


class TokenPayload(BaseModel):
    """JWT 载荷"""
    sub: str
    tenant_id: Optional[str] = None
    exp: datetime


class UserLogin(BaseModel):
    """用户登录"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def create_access_token(data: dict) -> str:
    """创建 JWT Token"""
    return jwt.encode(
        data,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )


def verify_token(token: str) -> TokenPayload:
    """验证 JWT Token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@auth_router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """用户登录"""
    # TODO: 实际应该从数据库验证用户
    # 这里暂时使用模拟数据
    if credentials.username == "admin" and credentials.password == "admin123":
        access_token = create_access_token({
            "sub": "admin",
            "tenant_id": "default-tenant",
            "exp": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        })

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=86400
        )

    raise HTTPException(status_code=401, detail="Invalid username or password")


@auth_router.post("/verify")
async def verify_current_user(
    token: str = Depends(lambda: None)
):
    """验证当前用户"""
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    payload = verify_token(token)
    return {"valid": True, "sub": payload.sub}
