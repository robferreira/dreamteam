import json
from functools import lru_cache
from typing import Any

import redis.asyncio as redis

from src.logging_config import get_logger
from src.settings import get_settings

logger = get_logger(__name__)


class RedisCache:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    async def connect(self) -> redis.Redis:
        if self._client is None:
            settings = get_settings()
            self._client = redis.from_url(settings.redis_url, decode_responses=True)
        return self._client

    async def get(self, key: str) -> str | None:
        try:
            client = await self.connect()
            return await client.get(key)
        except Exception as e:
            logger.warning("redis_get_failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        try:
            client = await self.connect()
            await client.setex(key, ttl, value)
        except Exception as e:
            logger.warning("redis_set_failed", key=key, error=str(e))

    async def get_json(self, key: str) -> Any | None:
        raw = await self.get(key)
        if raw:
            return json.loads(raw)
        return None

    async def set_json(self, key: str, value: Any, ttl: int = 3600) -> None:
        await self.set(key, json.dumps(value), ttl=ttl)

    async def acquire_lock(self, key: str, ttl: int = 30) -> bool:
        try:
            client = await self.connect()
            return bool(await client.set(f"lock:{key}", "1", nx=True, ex=ttl))
        except Exception:
            return True

    async def release_lock(self, key: str) -> None:
        try:
            client = await self.connect()
            await client.delete(f"lock:{key}")
        except Exception:
            pass

    async def publish_event(self, channel: str, event: dict[str, Any]) -> None:
        try:
            client = await self.connect()
            await client.publish(channel, json.dumps(event))
        except Exception as e:
            logger.warning("redis_publish_failed", channel=channel, error=str(e))

    def task_heartbeat_key(self, task_id: str) -> str:
        return f"task:{task_id}:heartbeat"

    async def set_task_heartbeat(self, task_id: str, ttl: int) -> None:
        await self.set(self.task_heartbeat_key(task_id), "1", ttl=ttl)

    async def has_task_heartbeat(self, task_id: str) -> bool:
        return await self.get(self.task_heartbeat_key(task_id)) is not None

    async def clear_task_heartbeat(self, task_id: str) -> None:
        try:
            client = await self.connect()
            await client.delete(self.task_heartbeat_key(task_id))
        except Exception:
            pass


@lru_cache
def get_redis_cache() -> RedisCache:
    return RedisCache()
