# -*- coding: utf-8 -*-
"""
数据库初始化脚本

功能:
1. 创建所有数据库表
2. 创建默认租户
3. 创建初始管理员账号
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.tenant import Tenant
from app.config import settings
from app.core.security import get_password_hash
from app.utils.timezone import now_cst
import uuid


def create_tables():
    """创建所有数据库表"""
    print("Creating database tables...")
    
    # 导入所有模型以确保它们被注册
    from app.models import (
        Keyword, Article, ArticleKeyword, Alert, 
        Tenant, Report, RSSFeed, KeywordSentimentStats
    )
    from app.models.user import User
    from app.models.sentiment_keyword import SentimentKeyword
    from app.models.negative_keyword import NegativeKeyword
    from app.models.rsshub_config import RSSHubConfig
    
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")


def init_tenant(db):
    """初始化默认租户"""
    tenant = db.query(Tenant).filter(Tenant.id == settings.default_tenant_id).first()

    if tenant:
        print(f"✓ Tenant '{tenant.name}' already exists")
        return tenant

    tenant = Tenant(
        id=settings.default_tenant_id,
        name=settings.default_tenant_name,
        plan_type="basic",
        max_keywords=100
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    print(f"✓ Tenant '{tenant.name}' created successfully")
    return tenant


def init_admin_user(db, tenant):
    """初始化管理员用户"""
    # 检查是否已存在管理员
    admin = db.query(User).filter(
        User.username == settings.initial_admin_username
    ).first()
    
    if admin:
        print(f"✓ Admin user '{settings.initial_admin_username}' already exists")
        return admin
    
    # 确定管理员密码
    admin_password = settings.initial_admin_password

    if not admin_password:
        # 开发环境生成随机密码
        if settings.app_env == "development":
            import secrets as sec
            admin_password = sec.token_urlsafe(12)
            print("⚠ WARNING: INITIAL_ADMIN_PASSWORD not set. Generated random password for development.")
            print(f"   Generated password: {admin_password}")
            print("   Please set INITIAL_ADMIN_PASSWORD in your .env file for persistence!")
        else:
            print("✗ ERROR: INITIAL_ADMIN_PASSWORD not set in environment")
            print("   Please set INITIAL_ADMIN_PASSWORD in your .env file")
            print("   Example: INITIAL_ADMIN_PASSWORD=YourSecurePassword123!")
            sys.exit(1)
    
    # 创建管理员用户
    admin_user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        username=settings.initial_admin_username,
        email=settings.initial_admin_email,
        hashed_password=get_password_hash(admin_password),
        full_name="System Administrator",
        role="admin",
        is_active=True,
        is_superuser=True,
        created_at=now_cst(),
        updated_at=now_cst()
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    print(f"✓ Admin user '{settings.initial_admin_username}' created successfully")
    print(f"  - Email: {settings.initial_admin_email}")
    print(f"  - Role: admin (superuser)")
    
    return admin_user


def init_db():
    """初始化数据库"""
    print("=" * 50)
    print("OwlWatch Database Initialization")
    print("=" * 50)
    print(f"Environment: {settings.app_env}")
    print()
    
    # 1. 创建表
    create_tables()
    
    # 2. 初始化数据
    db = SessionLocal()
    try:
        # 创建默认租户
        tenant = init_tenant(db)
        
        # 创建管理员用户
        init_admin_user(db, tenant)
        
        print()
        print("=" * 50)
        print("✓ Database initialization completed!")
        print("=" * 50)
        
        print()
        print("=" * 50)
        print("Login credentials are configured in your .env file")
        print(f"  Username: {settings.initial_admin_username}")
        print("  Password: [CHECK YOUR .env FILE]")
        print()
        
    except Exception as e:
        print(f"✗ Error during initialization: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
