"""配置管理模块"""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # 忽略 .env 中的额外字段
    )

    # 数据库配置
    database_url: str = Field(
        default="sqlite:///./owlwatch.db",
        alias="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    # API 密钥
    bocha_api_key: str = Field(default="")
    tavily_api_key: str = Field(default="")
    anspire_api_key: str = Field(default="")

    # 百炼平台
    bailian_api_key: str = Field(default="")

    # JWT 配置
    jwt_secret: str = Field(default="your-super-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256")

    # 应用配置
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)

    # 采集调度配置
    collect_interval_high: int = Field(default=300)  # 高优先级 5 分钟
    collect_interval_medium: int = Field(default=900)  # 中优先级 15 分钟
    collect_interval_low: int = Field(default=1800)  # 低优先级 30 分钟

    # 预警配置
    alert_negative_threshold: float = Field(default=0.3)
    alert_volume_threshold: int = Field(default=200)

    # 负面关键词配置（用于负面舆情搜索）
    negative_keywords: str = Field(
        default="违规,违法,投诉,通报,处罚,曝光,被查,立案,调查,维权",
        description="负面关键词，逗号分隔"
    )

    # 通知配置
    alert_webhook_url: Optional[str] = Field(default=None)
    wechat_webhook_url: Optional[str] = Field(default=None)
    sms_access_key: Optional[str] = Field(default=None)
    email_smtp_host: Optional[str] = Field(default=None)
    email_smtp_user: Optional[str] = Field(default=None)
    email_smtp_password: Optional[str] = Field(default=None)

    # RSS/RSSHub 配置
    rsshub_url: str = Field(
        default="https://rsshub.app",
        description="RSSHub 实例地址，可自建"
    )


# 全局配置实例
settings = Settings()
