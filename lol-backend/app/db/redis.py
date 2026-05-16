import json
import redis.asyncio as redis
from typing import Any, Optional
from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)


class RedisClient:
    def __init__(self, url: str, pool_size: int = 10):
        self.url = url
        self.pool_size = pool_size
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        self._pool = redis.ConnectionPool.from_url(
            self.url,
            max_connections=self.pool_size,
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=self._pool)
        logger.info("redis_connected", url=self.url)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.aclose()
        logger.info("redis_disconnected")

    async def get(self, key: str) -> Optional[Any]:
        if not self._client:
            return None
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("redis_get_error", key=key, error=str(e))
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        if not self._client:
            return False
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)
            return True
        except Exception as e:
            logger.error("redis_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error("redis_delete_error", key=key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        if not self._client:
            return 0
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error("redis_delete_pattern_error", pattern=pattern, error=str(e))
            return 0


@lru_cache
def get_redis_client() -> RedisClient:
    return RedisClient(settings.redis_url, settings.redis_pool_size)


redis_client = get_redis_client()
