"""
Authentication Alias & Rate Limiter Module
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Re-exports JWT security primitives and implements Upstash Redis / In-Memory rate limiting.
Satisfies Master Execution Plan v2.0 contracts.
"""

import logging
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_active_superuser,
    get_current_user,
    get_optional_user,
    get_password_hash,
    oauth2_scheme,
    verify_password,
)
from app.services.cache_service import cache_service

logger = logging.getLogger("app.auth")


class RateLimiter:
    """
    Sliding window / token bucket rate limiter dependency (default 100 req/min).
    Employs Upstash Redis when available, gracefully falling back to in-memory tracking.
    """

    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self._memory_timestamps: dict[str, list[float]] = defaultdict(list)

    def reset(self) -> None:
        """Clears in-memory sliding window timestamps."""
        self._memory_timestamps.clear()

    async def is_allowed(self, identifier: str) -> bool:
        """
        Evaluates whether an identifier (e.g. IP) is allowed under the rate limit.
        Returns True if allowed, False if throttled.
        """
        key = f"ratelimit:{identifier}"
        now = time.time()
        window_start = now - 60.0

        # 1. Try Redis cache if available
        try:
            if getattr(cache_service, "_redis_available", False) is True:
                redis_client = await cache_service._get_redis()
                if redis_client:
                    pipe = redis_client.pipeline()
                    pipe.incr(key)
                    pipe.expire(key, 60)
                    results = await pipe.execute()
                    count = int(results[0])
                    if count > self.requests_per_minute:
                        return False
                    return True
        except Exception as exc:
            logger.debug(f"Redis rate limiting bypassed, using in-memory: {exc}")

        # 2. In-memory sliding window fallback
        timestamps = self._memory_timestamps[identifier]
        valid_timestamps = [t for t in timestamps if t > window_start]
        if len(valid_timestamps) >= self.requests_per_minute:
            self._memory_timestamps[identifier] = valid_timestamps
            return False

        valid_timestamps.append(now)
        self._memory_timestamps[identifier] = valid_timestamps
        return True

    async def __call__(self, request: Request) -> bool:
        client_host = request.client.host if request.client else "127.0.0.1"
        allowed = await self.is_allowed(client_host)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and retry in 60 seconds.",
                headers={"Retry-After": "60"},
            )
        return True


# Default instance for route dependency injection
rate_limiter = RateLimiter(requests_per_minute=100)

__all__ = [
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "ALGORITHM",
    "SECRET_KEY",
    "RateLimiter",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_active_superuser",
    "get_current_user",
    "get_optional_user",
    "get_password_hash",
    "oauth2_scheme",
    "rate_limiter",
    "verify_password",
]
