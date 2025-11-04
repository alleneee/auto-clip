"""
Redis客户端
提供任务存储、缓存等功能
"""
import json
from typing import Optional, Dict, Any, List
import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis客户端封装"""

    def __init__(self):
        """初始化Redis客户端"""
        self._client: Optional[Redis] = None

    async def get_client(self) -> Redis:
        """
        获取Redis客户端（懒加载）

        Returns:
            Redis: Redis客户端实例
        """
        if self._client is None:
            self._client = await aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(
                "redis_client_initialized",
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB
            )

        return self._client

    async def close(self):
        """关闭Redis连接"""
        if self._client:
            await self._client.close()
            logger.info("redis_client_closed")

    # ===== 任务存储方法 =====

    async def set_task(self, task_id: str, task_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        存储任务数据

        Args:
            task_id: 任务ID
            task_data: 任务数据字典
            ttl: 过期时间（秒），None表示永不过期

        Returns:
            bool: 是否成功
        """
        try:
            client = await self.get_client()
            key = f"task:{task_id}"

            # 序列化为JSON
            value = json.dumps(task_data, ensure_ascii=False, default=str)

            if ttl:
                await client.setex(key, ttl, value)
            else:
                await client.set(key, value)

            logger.debug("task_stored_in_redis", task_id=task_id)
            return True

        except Exception as e:
            logger.error("redis_set_task_failed", task_id=task_id, error=str(e))
            return False

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务数据

        Args:
            task_id: 任务ID

        Returns:
            Optional[Dict]: 任务数据，不存在返回None
        """
        try:
            client = await self.get_client()
            key = f"task:{task_id}"

            value = await client.get(key)

            if value is None:
                return None

            # 反序列化JSON
            task_data = json.loads(value)

            logger.debug("task_retrieved_from_redis", task_id=task_id)
            return task_data

        except Exception as e:
            logger.error("redis_get_task_failed", task_id=task_id, error=str(e))
            return None

    async def delete_task(self, task_id: str) -> bool:
        """
        删除任务数据

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功
        """
        try:
            client = await self.get_client()
            key = f"task:{task_id}"

            await client.delete(key)

            logger.debug("task_deleted_from_redis", task_id=task_id)
            return True

        except Exception as e:
            logger.error("redis_delete_task_failed", task_id=task_id, error=str(e))
            return False

    async def list_tasks(
        self,
        pattern: str = "task:*",
        count: int = 100
    ) -> List[str]:
        """
        列出所有任务ID

        Args:
            pattern: Redis key匹配模式
            count: 每次扫描返回的数量

        Returns:
            List[str]: 任务ID列表
        """
        try:
            client = await self.get_client()
            task_ids = []

            async for key in client.scan_iter(match=pattern, count=count):
                # 提取task_id（移除"task:"前缀）
                task_id = key.replace("task:", "")
                task_ids.append(task_id)

            logger.debug("tasks_listed_from_redis", count=len(task_ids))
            return task_ids

        except Exception as e:
            logger.error("redis_list_tasks_failed", error=str(e))
            return []

    # ===== 缓存方法 =====

    async def set_cache(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值（会自动JSON序列化）
            ttl: 过期时间（秒），默认1小时

        Returns:
            bool: 是否成功
        """
        try:
            client = await self.get_client()
            cache_key = f"cache:{key}"

            # 序列化
            serialized_value = json.dumps(value, ensure_ascii=False, default=str)

            await client.setex(cache_key, ttl, serialized_value)

            logger.debug("cache_set_in_redis", key=key, ttl=ttl)
            return True

        except Exception as e:
            logger.error("redis_set_cache_failed", key=key, error=str(e))
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            Optional[Any]: 缓存值，不存在返回None
        """
        try:
            client = await self.get_client()
            cache_key = f"cache:{key}"

            value = await client.get(cache_key)

            if value is None:
                return None

            # 反序列化
            return json.loads(value)

        except Exception as e:
            logger.error("redis_get_cache_failed", key=key, error=str(e))
            return None

    async def delete_cache(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            bool: 是否成功
        """
        try:
            client = await self.get_client()
            cache_key = f"cache:{key}"

            await client.delete(cache_key)

            logger.debug("cache_deleted_from_redis", key=key)
            return True

        except Exception as e:
            logger.error("redis_delete_cache_failed", key=key, error=str(e))
            return False


# 单例实例
redis_client = RedisClient()
