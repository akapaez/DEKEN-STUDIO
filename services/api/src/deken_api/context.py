"""Recursos compartidos de la aplicación (creados en el arranque, cerrados al parar)."""

from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from deken_api.config import Settings
from deken_api.db.session import create_engine, create_sessionmaker
from deken_api.integrations.storage import Audience, ObjectStorage
from deken_api.security.rate_limit import RateLimiter


@dataclass
class AppContext:
    settings: Settings
    engine: AsyncEngine
    sessionmaker: async_sessionmaker[AsyncSession]
    redis: Redis
    storage: ObjectStorage
    rate_limiter: RateLimiter

    @classmethod
    def create(cls, settings: Settings) -> AppContext:
        engine = create_engine(settings.database_url, pool_size=settings.database_pool_size)
        redis = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=35,  # > espera máxima del long-poll de workers
            health_check_interval=30,
        )
        storage = ObjectStorage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            access_key=settings.s3_access_key.get_secret_value(),
            secret_key=settings.s3_secret_key.get_secret_value(),
            endpoints={
                Audience.INTERNAL: settings.s3_endpoint_url,
                Audience.BROWSER: settings.public_endpoint,
                Audience.WORKER: settings.worker_endpoint,
            },
            force_path_style=settings.s3_force_path_style,
        )
        return cls(
            settings=settings,
            engine=engine,
            sessionmaker=create_sessionmaker(engine),
            redis=redis,
            storage=storage,
            rate_limiter=RateLimiter(redis),
        )

    async def close(self) -> None:
        await self.redis.aclose()
        await self.engine.dispose()
