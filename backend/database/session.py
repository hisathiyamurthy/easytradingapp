"""Database session and base configuration."""
from typing import Optional

import redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.config import get_settings
from database.base import Base

# Import all models to ensure they are registered with SQLAlchemy
# Order matters - models with relationships must be imported after their dependencies
import models.broker_account_models  # noqa: F401
import models.auth_models  # noqa: F401
import models.order_models  # noqa: F401
import models.strategy_models  # noqa: F401
import models.strategy_version_models  # noqa: F401
import models.notification_models  # noqa: F401

settings = get_settings()

# Create async engine
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=False,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Redis client
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client instance."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def async_session():
    """Get async session (alternative)."""
    async with AsyncSessionLocal() as session:
        yield session
