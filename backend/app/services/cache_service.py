"""
Redis Cache Service with In-Memory Fallback
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)

Provides distributed caching via Upstash / Local Redis with automatic, graceful
in-memory fallback when Redis is offline or unreachable. Prevents network failures
from interrupting API request fulfillment.
"""

import asyncio
import json
import logging
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger("app.services.cache")


class CacheService:
    """
    Robust cache client supporting Redis and in-memory TTL caching.
    Ensures zero downtime or unhandled exceptions when cache layer is degraded.
    """

    def __init__(self, redis_url: str | None = None, default_ttl: int = 300):
        self.redis_url = redis_url or settings.REDIS_URL
        self.default_ttl = default_ttl
        self._redis_client: Any | None = None
        self._redis_available: bool | None = None
        self._memory_cache: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    async def _get_redis(self) -> Any | None:
        if self._redis_available is False:
            return None

        if self._redis_client is not None:
            return self._redis_client

        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            # Test ping
            await client.ping()
            self._redis_client = client
            self._redis_available = True
            logger.info("Connected to Redis cache at %s", self.redis_url)
            return self._redis_client
        except Exception as err:
            logger.debug("Redis unavailable (%s), operating in in-memory fallback cache mode", err)
            self._redis_available = False
            self._redis_client = None
            return None

    async def get(self, key: str) -> str | None:
        """
        Retrieves a string value by key from Redis or in-memory fallback.
        """
        redis_client = await self._get_redis()
        if redis_client:
            try:
                return await redis_client.get(key)
            except Exception as e:
                logger.warning("Redis GET failed for key '%s': %s; checking in-memory fallback", key, e)

        # Check in-memory fallback
        async with self._lock:
            if key in self._memory_cache:
                val, expires_at = self._memory_cache[key]
                if time.time() < expires_at:
                    return val
                else:
                    del self._memory_cache[key]

        return None

    async def get_json(self, key: str) -> Any | None:
        """
        Retrieves and decodes JSON from cache.
        """
        raw = await self.get(key)
        if raw is not None:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> bool:
        """
        Stores a string key-value pair with TTL (seconds).
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        success = False

        redis_client = await self._get_redis()
        if redis_client:
            try:
                await redis_client.set(key, value, ex=ttl)
                success = True
            except Exception as e:
                logger.warning("Redis SET failed for key '%s': %s; falling back to in-memory", key, e)

        # Always maintain in-memory fallback
        async with self._lock:
            self._memory_cache[key] = (value, time.time() + ttl)
            success = True

        return success

    async def set_json(self, key: str, data: Any, ttl_seconds: int | None = None) -> bool:
        """
        Serializes data to JSON and stores in cache.
        """
        try:
            val_str = json.dumps(data, default=str)
            return await self.set(key, val_str, ttl_seconds)
        except Exception as err:
            logger.warning("Failed to serialize cache value for key '%s': %s", key, err)
            return False

    async def delete(self, key: str) -> bool:
        """
        Removes a key from cache.
        """
        redis_client = await self._get_redis()
        if redis_client:
            try:
                await redis_client.delete(key)
            except Exception:
                pass

        async with self._lock:
            self._memory_cache.pop(key, None)

        return True

    async def clear(self) -> None:
        """
        Clears in-memory cache and resets state.
        """
        async with self._lock:
            self._memory_cache.clear()


# Singleton cache instance
cache_service = CacheService()
