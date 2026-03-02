# -*- coding: utf-8 -*-
"""
关键词 API 集成测试

测试内容：
1. 创建关键词
2. 查询关键词列表
3. 更新关键词
4. 删除关键词
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.keyword import Keyword
from tests.fixtures.database import KeywordFactory


class TestKeywordsAPI:
    """关键词 API 测试类"""

    # ==================== 创建关键词测试 ====================
    @pytest.mark.integration
    def test_create_keyword_success(self, client: TestClient, sample_keyword_data: dict):
        """测试成功创建关键词"""
        response = client.post("/api/v1/keywords/", json=sample_keyword_data)

        assert response.status_code == 200
        data = response.json()
        assert data["keyword"] == sample_keyword_data["keyword"]
        assert data["priority"] == sample_keyword_data["priority"]
        assert "id" in data

    @pytest.mark.integration
    def test_create_keyword_with_defaults(self, client: TestClient):
        """测试使用默认值创建关键词"""
        response = client.post("/api/v1/keywords/", json={"keyword": "默认测试关键词"})

        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "medium"  # 默认值

    @pytest.mark.integration
    def test_create_duplicate_keyword(self, client: TestClient, sample_keyword_data: dict):
        """测试创建重复关键词"""
        # 第一次创建
        client.post("/api/v1/keywords/", json=sample_keyword_data)

        # 第二次创建应该失败
        response = client.post("/api/v1/keywords/", json=sample_keyword_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    # ==================== 查询关键词测试 ====================
    @pytest.mark.integration
    def test_list_keywords_empty(self, client: TestClient):
        """测试空关键词列表"""
        response = client.get("/api/v1/keywords/")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.integration
    def test_list_keywords_with_data(self, client: TestClient, db_with_keyword: Keyword):
        """测试有关键词的列表"""
        response = client.get("/api/v1/keywords/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(k["keyword"] == db_with_keyword.keyword for k in data)

    @pytest.mark.integration
    def test_list_keywords_filter_by_active(
        self, client: TestClient, db_session: Session
    ):
        """测试按激活状态过滤"""
        # 创建激活和停用的关键词
        active = KeywordFactory.create(keyword="激活关键词", is_active=True)
        inactive = KeywordFactory.create(keyword="停用关键词", is_active=False)
        db_session.add_all([active, inactive])
        db_session.commit()

        # 只查询激活的
        response = client.get("/api/v1/keywords/?is_active=true")

        assert response.status_code == 200
        data = response.json()
        assert all(k["is_active"] for k in data)

    @pytest.mark.integration
    def test_list_keywords_pagination(self, client: TestClient, db_session: Session):
        """测试分页"""
        # 创建多个关键词
        for i in range(15):
            keyword = KeywordFactory.create(keyword=f"关键词{i}")
            db_session.add(keyword)
        db_session.commit()

        # 测试第一页
        response = client.get("/api/v1/keywords/?skip=0&limit=10")
        assert response.status_code == 200
        assert len(response.json()) == 10

        # 测试第二页
        response = client.get("/api/v1/keywords/?skip=10&limit=10")
        assert response.status_code == 200
        assert len(response.json()) >= 5

    # ==================== 更新关键词测试 ====================
    @pytest.mark.integration
    def test_update_keyword_success(
        self, client: TestClient, db_with_keyword: Keyword
    ):
        """测试成功更新关键词"""
        update_data = {
            "keyword": "更新后的关键词",
            "priority": "low",
            "platforms": ["tavily"],
        }

        response = client.put(
            f"/api/v1/keywords/{db_with_keyword.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["keyword"] == update_data["keyword"]
        assert data["priority"] == update_data["priority"]

    @pytest.mark.integration
    def test_update_keyword_not_found(self, client: TestClient):
        """测试更新不存在的关键词"""
        response = client.put(
            "/api/v1/keywords/non-existent-id",
            json={"keyword": "测试", "priority": "high"},
        )

        assert response.status_code == 404

    # ==================== 删除关键词测试 ====================
    @pytest.mark.integration
    def test_delete_keyword_success(
        self, client: TestClient, db_with_keyword: Keyword
    ):
        """测试成功删除关键词"""
        response = client.delete(f"/api/v1/keywords/{db_with_keyword.id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # 验证已删除
        response = client.get("/api/v1/keywords/")
        assert not any(k["id"] == db_with_keyword.id for k in response.json())

    @pytest.mark.integration
    def test_delete_keyword_not_found(self, client: TestClient):
        """测试删除不存在的关键词"""
        response = client.delete("/api/v1/keywords/non-existent-id")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestKeywordsAPIAsync:
    """关键词 API 异步测试类"""

    @pytest.mark.integration
    async def test_create_keyword_async(
        self, async_client: AsyncClient, sample_keyword_data: dict
    ):
        """测试异步创建关键词"""
        response = await async_client.post(
            "/api/v1/keywords/", json=sample_keyword_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["keyword"] == sample_keyword_data["keyword"]

    @pytest.mark.integration
    async def test_list_keywords_async(self, async_client: AsyncClient):
        """测试异步查询关键词列表"""
        response = await async_client.get("/api/v1/keywords/")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
