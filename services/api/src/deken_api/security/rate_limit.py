"""Limitación de intentos con ventana fija.

Usa Redis si está disponible. Si Redis falla, cae a un contador en memoria del
proceso: la protección se mantiene (por instancia) en vez de desactivarse.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError

from deken_api.logs import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    count: int
    retry_after: int


class RateLimiter:
    def __init__(self, redis: Redis | None, *, prefix: str = "rl") -> None:
        self._redis = redis
        self._prefix = prefix
        self._memory: dict[str, tuple[int, float]] = {}

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        full_key = f"{self._prefix}:{key}"
        if self._redis is not None:
            try:
                async with self._redis.pipeline(transaction=True) as pipe:
                    pipe.incr(full_key)
                    pipe.expire(full_key, window_seconds, nx=True)
                    pipe.ttl(full_key)
                    count, _, ttl = await pipe.execute()
                ttl = int(ttl) if int(ttl) > 0 else window_seconds
                return RateLimitResult(int(count) <= limit, int(count), ttl)
            except RedisError as exc:
                log.warning("rate_limit.redis_unavailable", error=str(exc))
        return self._hit_memory(full_key, limit, window_seconds)

    async def reset(self, key: str) -> None:
        full_key = f"{self._prefix}:{key}"
        self._memory.pop(full_key, None)
        if self._redis is not None:
            try:
                await self._redis.delete(full_key)
            except RedisError as exc:
                log.warning("rate_limit.redis_unavailable", error=str(exc))

    def _hit_memory(self, key: str, limit: int, window: int) -> RateLimitResult:
        now = time.monotonic()
        count, started = self._memory.get(key, (0, now))
        if now - started >= window:
            count, started = 0, now
        count += 1
        self._memory[key] = (count, started)
        if len(self._memory) > 10_000:  # evita crecimiento ilimitado
            cutoff = now - window
            self._memory = {k: v for k, v in self._memory.items() if v[1] > cutoff}
        retry = max(1, int(window - (now - started)))
        return RateLimitResult(count <= limit, count, retry)
