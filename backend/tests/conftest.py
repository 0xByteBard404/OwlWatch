# -*- coding: utf-8 -*-
"""
测试配置和共享 Fixtures

提供以下功能：
1. 测试数据库配置（内存 SQLite）
2. TestClient 工厂
3. Mock 工具
4. 测试数据生成器
"""
import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient, Response as HttpxResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app.dependencies import get_db
from app.models.keyword import Keyword
from app.models.article import Article


# 延迟导入 FastAPI 应用以避免调度器启动
def get_fastapi_app():
    """延迟获取 FastAPI 应用实例"""
    from app.main import app
    return app


# ==================== 环境配置 ====================
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """设置测试环境变量"""
    original_env = os.environ.copy()

    # 设置测试环境
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["DEBUG"] = "true"

    # 禁用调度器
    os.environ["DISABLE_SCHEDULER"] = "true"

    yield

    # 恢复环境变量
    os.environ.clear()
    os.environ.update(original_env)


# ==================== 数据库 Fixtures ====================
@pytest.fixture(scope="function")
def db_engine():
    """创建测试数据库引擎（内存 SQLite）"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """创建测试数据库会话"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """创建同步测试客户端"""
    fastapi_app = get_fastapi_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """创建异步测试客户端"""
    fastapi_app = get_fastapi_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test"
    ) as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


# ==================== 数据生成 Fixtures ====================
@pytest.fixture
def sample_keyword_data() -> dict:
    """示例关键词数据"""
    return {
        "keyword": "测试关键词",
        "priority": "high",
        "platforms": ["bocha", "tavily"]
    }


@pytest.fixture
def sample_article_data() -> dict:
    """示例文章数据"""
    return {
        "title": "测试文章标题",
        "content": "这是一篇测试文章的内容，用于验证系统的各项功能。",
        "url": "https://example.com/test-article",
        "source": "测试来源",
        "source_api": "bocha",
        "sentiment_score": 0.5,
        "sentiment_label": "positive",
    }


@pytest.fixture
def db_with_keyword(db_session: Session, sample_keyword_data: dict) -> Keyword:
    """创建一个已存在的关键词"""
    keyword = Keyword(
        id="test-keyword-id-001",
        keyword=sample_keyword_data["keyword"],
        priority=sample_keyword_data["priority"],
        platforms=sample_keyword_data["platforms"],
        is_active=True,
    )
    db_session.add(keyword)
    db_session.commit()
    db_session.refresh(keyword)
    return keyword


@pytest.fixture
def db_with_articles(db_session: Session, db_with_keyword: Keyword) -> list[Article]:
    """创建多个文章记录"""
    articles = []
    for i in range(3):
        article = Article(
            id=f"test-article-id-{i:03d}",
            keyword_id=db_with_keyword.id,
            title=f"测试文章 {i+1}",
            content=f"这是第 {i+1} 篇测试文章的内容。",
            url=f"https://example.com/test-{i+1}",
            source="测试来源",
            source_api="bocha",
            sentiment_score=0.5 - i * 0.3,
            sentiment_label="positive" if i == 0 else "neutral" if i == 1 else "negative",
        )
        db_session.add(article)
        articles.append(article)

    db_session.commit()
    for article in articles:
        db_session.refresh(article)
    return articles


# ==================== Mock Fixtures ====================
@pytest.fixture
def mock_httpx_response():
    """创建 Mock HTTP 响应的工厂函数"""

    def _create_mock_response(
        status_code: int = 200,
        json_data: dict = None,
        text: str = "",
    ) -> MagicMock:
        response = MagicMock(spec=HttpxResponse)
        response.status_code = status_code
        response.text = text or str(json_data)
        response.json.return_value = json_data or {}
        return response

    return _create_mock_response


@pytest.fixture
def mock_bocha_response(mock_httpx_response):
    """博查 API 响应 Mock"""
    return mock_httpx_response(
        status_code=200,
        json_data={
            "query": "测试关键词",
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "博查测试结果1",
                            "summary": "这是博查返回的测试内容1",
                            "url": "https://bocha.example.com/1",
                            "siteName": "博查测试站点",
                            "dateLastCrawled": "2026-03-02T10:00:00",
                        },
                        {
                            "name": "博查测试结果2",
                            "summary": "这是博查返回的测试内容2",
                            "url": "https://bocha.example.com/2",
                            "siteName": "博查测试站点",
                            "dateLastCrawled": "2026-03-02T11:00:00",
                        }
                    ]
                }
            }
        }
    )


@pytest.fixture
def mock_tavily_response(mock_httpx_response):
    """Tavily API 响应 Mock"""
    return mock_httpx_response(
        status_code=200,
        json_data={
            "query": "测试关键词",
            "results": [
                {
                    "title": "Tavily测试结果1",
                    "content": "这是Tavily返回的测试内容1",
                    "url": "https://tavily.example.com/1",
                    "source": "Tavily测试源",
                    "published_date": "2026-03-02T10:00:00Z",
                },
                {
                    "title": "Tavily测试结果2",
                    "content": "这是Tavily返回的测试内容2",
                    "url": "https://tavily.example.com/2",
                    "source": "Tavily测试源",
                    "published_date": "2026-03-02T11:00:00Z",
                }
            ]
        }
    )


@pytest.fixture
def mock_sentiment_response(mock_httpx_response):
    """情感分析 API 响应 Mock"""
    return mock_httpx_response(
        status_code=200,
        json_data={
            "choices": [
                {
                    "message": {
                        "content": '{"score": 0.8, "label": "positive", "reason": "内容积极向上"}'
                    }
                }
            ]
        }
    )


# ==================== 事件循环 ====================
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
