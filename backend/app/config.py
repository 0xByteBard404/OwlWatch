"""配置管理模块"""
import secrets
from typing import List, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # 忽略 .env 中的额外字段
    )

    # ==================== 数据库配置 ====================
    database_url: str = Field(
        alias="DATABASE_URL"
    )
    redis_url: str = Field(alias="REDIS_URL")

    # Docker 环境下用于覆盖数据库主机名
    database_host: Optional[str] = Field(default=None, alias="DATABASE_HOST")

    # ==================== API 密钥（可选） ====================
    bocha_api_key: str = Field(default="")
    tavily_api_key: str = Field(default="")
    anspire_api_key: str = Field(default="")

    # 百炼平台（可选）
    bailian_api_key: str = Field(default="")

    # ==================== JWT 配置 ====================
    jwt_secret: Optional[str] = Field(default=None, alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_hours: int = Field(default=24)

    # ==================== 应用配置 ====================
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)

    # ==================== CORS 配置 ====================
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Allowed CORS origins, comma separated"
    )

    # ==================== 初始管理员配置 ====================
    initial_admin_username: str = Field(
        default="admin",
        alias="INITIAL_ADMIN_USERNAME"
    )
    initial_admin_password: Optional[str] = Field(
        default=None,
        alias="INITIAL_ADMIN_PASSWORD"
    )
    initial_admin_email: str = Field(
        default="admin@owlwatch.local",
        alias="INITIAL_ADMIN_EMAIL"
    )

    # ==================== 默认租户配置 ====================
    default_tenant_id: str = Field(
        default="default-tenant",
        alias="DEFAULT_TENANT_ID"
    )
    default_tenant_name: str = Field(
        default="Default Tenant",
        alias="DEFAULT_TENANT_NAME"
    )

    # ==================== 采集调度配置 ====================
    collect_interval_high: int = Field(default=300)  # 高优先级 5 分钟
    collect_interval_medium: int = Field(default=900)  # 中优先级 15 分钟
    collect_interval_low: int = Field(default=1800)  # 低优先级 30 分钟

    # ==================== 预警配置 ====================
    alert_negative_threshold: float = Field(default=0.3)
    alert_volume_threshold: int = Field(default=200)

    # ==================== 负面关键词配置 ====================
    negative_keywords: str = Field(
        default="违规,违法,投诉,通报,处罚,曝光,被查,立案,调查,维权",
        description="负面关键词，逗号分隔"
    )

    # ==================== 通知配置（可选） ====================
    alert_webhook_url: Optional[str] = Field(default=None)
    wechat_webhook_url: Optional[str] = Field(default=None)
    sms_access_key: Optional[str] = Field(default=None)
    email_smtp_host: Optional[str] = Field(default=None)
    email_smtp_user: Optional[str] = Field(default=None)
    email_smtp_password: Optional[str] = Field(default=None)

    # ==================== RSS/RSSHub 配置 ====================
    rsshub_url: str = Field(
        default="https://rsshub.app",
        description="RSSHub 实例地址，可自建"
    )

    # ==================== 验证器 ====================

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """强制要求配置数据库连接"""
        if not v:
            raise ValueError(
                "DATABASE_URL is required. "
                "Example: postgresql://user:password@localhost:5432/owlwatch"
            )
        return v

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """强制要求配置Redis连接"""
        if not v:
            raise ValueError(
                "REDIS_URL is required. "
                "Example: redis://localhost:6379/0"
            )
        return v

    @model_validator(mode="after")
    def apply_database_host_override(self):
        """如果设置了 DATABASE_HOST，替换 DATABASE_URL 中的主机名（用于 Docker 环境）"""
        if self.database_host and self.database_url:
            # 解析 DATABASE_URL 并替换主机名
            # 格式: postgresql://user:password@host:port/database
            import re
            pattern = r"(postgresql://[^:]+:[^@]+@)([^:/]+)(:\d+/.+)"
            match = re.match(pattern, self.database_url)
            if match:
                self.database_url = f"{match.group(1)}{self.database_host}{match.group(3)}"
        return self

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: Optional[str], info) -> str:
        """验证JWT密钥 - 生产环境必须设置，开发环境自动生成"""
        app_env = info.data.get("app_env", "development")

        # 生产环境必须手动设置
        if app_env == "production":
            if not v:
                raise ValueError(
                    "JWT_SECRET is required in production! "
                    "Generate one: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            if len(v) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters in production")
            # 检查弱密钥
            weak_secrets = ["secret", "password", "key", "jwt", "token", "change-me", "admin"]
            if any(weak in v.lower() for weak in weak_secrets):
                raise ValueError("JWT_SECRET appears to be weak. Use a securely generated random key.")
            return v

        # 开发环境：如果未设置，自动生成
        if not v:
            generated = secrets.token_urlsafe(32)
            import warnings
            warnings.warn(
                "JWT_SECRET not set. Generated temporary key for development. "
                "Set JWT_SECRET in .env for persistent sessions."
            )
            return generated

        return v

    @field_validator("initial_admin_password")
    @classmethod
    def validate_admin_password(cls, v: Optional[str], info) -> Optional[str]:
        """验证管理员密码"""
        app_env = info.data.get("app_env", "development")

        # 生产环境必须设置密码
        if app_env == "production" and not v:
            raise ValueError(
                "INITIAL_ADMIN_PASSWORD is required in production environment. "
                "Set it in your .env file or docker-compose.yml"
            )

        # 如果设置了密码，进行强度检查
        if v:
            if len(v) < 8:
                raise ValueError("INITIAL_ADMIN_PASSWORD must be at least 8 characters")
            # 生产环境额外检查
            if app_env == "production" and len(v) < 12:
                import warnings
                warnings.warn(
                    "INITIAL_ADMIN_PASSWORD is less than 12 characters. "
                    "Consider using a stronger password for production."
                )

        return v

    def get_cors_origins(self) -> List[str]:
        """获取CORS允许的源列表"""
        if self.app_env == "development":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def generate_secure_jwt_secret(self) -> str:
        """生成安全的JWT密钥（用于首次部署）"""
        return secrets.token_urlsafe(32)


# 全局配置实例
settings = Settings()
