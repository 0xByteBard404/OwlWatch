# -*- coding: utf-8 -*-
"""Redis 服务模块 - 用于分布式任务状态存储和消息队列"""
import json
import logging
from typing import Optional, Any, Dict, List
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

# Redis 连接池
_redis_client: Optional[redis.Redis] = None

# 队列名称
SENTIMENT_QUEUE = "owlwatch:sentiment_queue"


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


class SentimentQueue:
    """情感分析消息队列"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.queue_key = SENTIMENT_QUEUE

    async def push(self, article_id: str) -> bool:
        """推送文章ID到队列"""
        try:
            await self.redis.rpush(self.queue_key, article_id)
            logger.debug(f"Pushed article {article_id} to sentiment queue")
            return True
        except Exception as e:
            logger.error(f"Failed to push to sentiment queue: {e}")
            return False

    async def push_batch(self, article_ids: List[str]) -> bool:
        """批量推送文章ID到队列"""
        if not article_ids:
            return True
        try:
            await self.redis.rpush(self.queue_key, *article_ids)
            logger.debug(f"Pushed {len(article_ids)} articles to sentiment queue")
            return True
        except Exception as e:
            logger.error(f"Failed to push batch to sentiment queue: {e}")
            return False

    async def pop_batch(self, batch_size: int = 20, timeout: int = 5) -> List[str]:
        """
        批量取出文章ID（阻塞式）

        Args:
            batch_size: 批量大小
            timeout: 阻塞超时时间（秒）

        Returns:
            文章ID列表
        """
        try:
            # 使用 pipeline 批量获取
            article_ids = []
            for _ in range(batch_size):
                # 非阻塞式从队列左侧取出
                result = await self.redis.lpop(self.queue_key)
                if result is None:
                    break
                article_ids.append(result)

            if article_ids:
                logger.debug(f"Popped {len(article_ids)} articles from sentiment queue")
            return article_ids
        except Exception as e:
            logger.error(f"Failed to pop from sentiment queue: {e}")
            return []

    async def size(self) -> int:
        """获取队列长度"""
        try:
            return await self.redis.llen(self.queue_key)
        except Exception as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0

    async def clear(self) -> bool:
        """清空队列"""
        try:
            await self.redis.delete(self.queue_key)
            return True
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            return False


# 全局队列实例
_sentiment_queue: Optional[SentimentQueue] = None


async def get_sentiment_queue() -> SentimentQueue:
    """获取情感分析队列实例"""
    global _sentiment_queue
    if _sentiment_queue is None:
        redis_client = await get_redis()
        _sentiment_queue = SentimentQueue(redis_client)
    return _sentiment_queue


class TaskStore:
    """任务状态存储（基于 Redis）"""

    KEY_PREFIX = "owlwatch:task:"
    LOCK_PREFIX = "owlwatch:keyword_lock:"
    KEY_TTL = 86400  # 24 小时过期
    LOCK_TTL = 3600  # 锁过期时间 1 小时

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _key(self, task_id: str) -> str:
        """生成 Redis key"""
        return f"{self.KEY_PREFIX}{task_id}"

    def _lock_key(self, keyword_id: str) -> str:
        """生成锁 key"""
        return f"{self.LOCK_PREFIX}{keyword_id}"

    async def acquire_lock(self, keyword_id: str) -> bool:
        """
        获取监控主体的任务锁（原子操作）

        Args:
            keyword_id: 监控主体 ID

        Returns:
            True 表示成功获取锁，False 表示锁已被占用
        """
        try:
            lock_key = self._lock_key(keyword_id)
            # SET NX: 仅当 key 不存在时才设置
            result = await self.redis.set(lock_key, "1", nx=True, ex=self.LOCK_TTL)
            return result is not None
        except Exception as e:
            logger.error(f"Redis acquire lock error: {e}")
            return False

    async def release_lock(self, keyword_id: str) -> bool:
        """
        释放监控主体的任务锁

        Args:
            keyword_id: 监控主体 ID

        Returns:
            是否成功释放
        """
        try:
            lock_key = self._lock_key(keyword_id)
            await self.redis.delete(lock_key)
            return True
        except Exception as e:
            logger.error(f"Redis release lock error: {e}")
            return False

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
                    task_id = data.get("task_id")
                    # 跳过无效的 task_id
                    if not task_id:
                        continue
                    running.append({
                        "task_id": task_id,
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

    async def get_running_by_keyword_id(self, keyword_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定监控主体的运行中任务

        Args:
            keyword_id: 监控主体 ID

        Returns:
            如果有运行中的任务，返回任务信息；否则返回 None
        """
        try:
            keys = await self.redis.keys(f"{self.KEY_PREFIX}*")
            for key in keys:
                data = await self.redis.hgetall(key)
                if data and data.get("status") in ["pending", "running"]:
                    if data.get("keyword_id") == keyword_id:
                        task_id = data.get("task_id")
                        if task_id:  # 确保task_id有效
                            return {
                                "task_id": task_id,
                                "keyword_id": data.get("keyword_id", ""),
                                "keyword": data.get("keyword", ""),
                                "status": data.get("status"),
                                "collected_count": int(data.get("collected_count", 0)),
                                "message": data.get("message", ""),
                                "created_at": data.get("created_at", ""),
                            }
            return None
        except Exception as e:
            logger.error(f"Redis get running by keyword_id error: {e}")
            return None


# 全局任务存储实例
_task_store: Optional[TaskStore] = None


async def get_task_store() -> TaskStore:
    """获取任务存储实例"""
    global _task_store
    if _task_store is None:
        redis_client = await get_redis()
        _task_store = TaskStore(redis_client)
    return _task_store
