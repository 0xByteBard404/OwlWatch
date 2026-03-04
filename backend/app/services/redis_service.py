# -*- coding: utf-8 -*-
"""Redis 服务模块 - 用于分布式任务状态存储"""
import json
import logging
from typing import Optional, Any, Dict
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

# Redis 连接池
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """获取 Redis 客户端（单例模式）"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # 测试连接
            await _redis_client.ping()
            logger.info(f"Redis connected: {settings.redis_url}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    return _redis_client


async def close_redis():
    """关闭 Redis 连接"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


class TaskStore:
    """任务状态存储（基于 Redis）"""

    KEY_PREFIX = "owlwatch:task:"
    KEY_TTL = 86400  # 24 小时过期

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _key(self, task_id: str) -> str:
        """生成 Redis key"""
        return f"{self.KEY_PREFIX}{task_id}"

    async def create(self, task_id: str, data: Dict[str, Any]) -> bool:
        """创建任务"""
        key = self._key(task_id)
        try:
            # 过滤 None 值，Redis 不接受 None
            mapping = {
                "task_id": task_id,
                "keyword_id": data.get("keyword_id") or "",
                "keyword": data.get("keyword") or "",
                "status": data.get("status") or "pending",
                "collected_count": str(data.get("collected_count") or 0),
                "message": data.get("message") or "",
                "created_at": data.get("created_at") or "",
                "finished_at": data.get("finished_at") or "",
            }
            await self.redis.hset(key, mapping=mapping)
            await self.redis.expire(key, self.KEY_TTL)
            return True
        except Exception as e:
            logger.error(f"Redis create task error: {e}")
            return False

    async def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务"""
        key = self._key(task_id)
        try:
            data = await self.redis.hgetall(key)
            if not data:
                return None
            # 转换类型
            return {
                "task_id": data.get("task_id", task_id),
                "keyword_id": data.get("keyword_id", ""),
                "keyword": data.get("keyword", ""),
                "status": data.get("status", "pending"),
                "collected_count": int(data.get("collected_count", 0)),
                "message": data.get("message", ""),
                "created_at": data.get("created_at", ""),
                "finished_at": data.get("finished_at") or None,
            }
        except Exception as e:
            logger.error(f"Redis get task error: {e}")
            return None

    async def update(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """更新任务"""
        key = self._key(task_id)
        try:
            mapping = {}
            for k, v in updates.items():
                if v is not None:
                    mapping[k] = str(v) if not isinstance(v, str) else v
            if mapping:
                await self.redis.hset(key, mapping=mapping)
            return True
        except Exception as e:
            logger.error(f"Redis update task error: {e}")
            return False

    async def delete(self, task_id: str) -> bool:
        """删除任务"""
        key = self._key(task_id)
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete task error: {e}")
            return False

    async def get_all_running(self) -> list:
        """获取所有运行中的任务"""
        try:
            keys = await self.redis.keys(f"{self.KEY_PREFIX}*")
            running = []
            for key in keys:
                data = await self.redis.hgetall(key)
                if data and data.get("status") in ["pending", "running"]:
                    running.append({
                        "task_id": data.get("task_id"),
                        "keyword_id": data.get("keyword_id", ""),
                        "keyword": data.get("keyword", ""),
                        "status": data.get("status"),
                        "collected_count": int(data.get("collected_count", 0)),
                        "message": data.get("message", ""),
                        "created_at": data.get("created_at", ""),
                    })
            return running
        except Exception as e:
            logger.error(f"Redis get running tasks error: {e}")
            return []


# 全局任务存储实例
_task_store: Optional[TaskStore] = None


async def get_task_store() -> TaskStore:
    """获取任务存储实例"""
    global _task_store
    if _task_store is None:
        redis_client = await get_redis()
        _task_store = TaskStore(redis_client)
    return _task_store
