# -*- coding: utf-8 -*-
"""
安全工具模块 - 密码加密、JWT处理、认证依赖注入

功能:
1. bcrypt 密码哈希和验证
2. JWT Token 创建和解码
3. 认证依赖注入 (get_current_user)
4. 密码强度验证
"""
from datetime import datetime, timedelta
from typing import Optional
import logging
import bcrypt  # 直接使用 bcrypt，避免 passlib 兼容性问题
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config import settings
from app.dependencies import get_db
from app.models.user import User
from app.utils.timezone import now_cst

# 调试日志
logger = logging.getLogger(__name__)


# OAuth2 Bearer Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class TokenData(BaseModel):
    """Token数据"""
    username: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    role: Optional[str] = None


# ===== 密码处理 =====

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def validate_password_strength(password: str) -> bool:
    """
    验证密码强度
    
    要求：
    - 至少8个字符
    - 至少1个大写字母
    - 至少1个小写字母
    - 至少1个数字
    - 至少1个特殊字符
    """
    if len(password) < 8:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    return all([has_upper, has_lower, has_digit, has_special])


# ===== JWT 处理 =====

def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = now_cst() + expires_delta
    else:
        expire = now_cst() + timedelta(
            hours=getattr(settings, 'jwt_access_token_expire_hours', 24)
        )
    
    to_encode.update({
        "exp": expire,
        "iat": now_cst()
    })
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret, 
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """解码JWT令牌"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        tenant_id: str = payload.get("tenant_id")
        role: str = payload.get("role")

        if username is None:
            logger.warning("Token decoded but no username (sub) found")
            return None

        logger.debug(f"Token decoded successfully for user: {username}")
        return TokenData(
            username=username,
            user_id=user_id,
            tenant_id=tenant_id,
            role=role
        )
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        return None


# ===== 认证依赖注入 =====

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """获取当前用户（依赖注入）- 允许未认证访问"""
    if token is None:
        return None
    
    token_data = decode_access_token(token)
    if token_data is None:
        return None
    
    user = db.query(User).filter(
        User.username == token_data.username
    ).first()
    
    return user


async def get_current_user_required(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户（必须认证）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        logger.warning("Authentication failed: No token provided")
        raise credentials_exception

    token_data = decode_access_token(token)
    if token_data is None:
        logger.warning("Authentication failed: Token decode returned None")
        raise credentials_exception

    user = db.query(User).filter(
        User.username == token_data.username
    ).first()

    if user is None:
        logger.warning(f"Authentication failed: User '{token_data.username}' not found in database")
        raise credentials_exception

    logger.debug(f"User authenticated: {user.username}")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user_required)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """获取当前超级用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
