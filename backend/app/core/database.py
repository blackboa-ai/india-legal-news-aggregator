"""
Async Database Session & Engine Configuration
India Legal News Aggregator - PostgreSQL 15 + pgvector
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Engine configuration with connection pooling & ping verification
# pool_size=2, max_overflow=3: Conservative pool sizing (5 max connections) for serverless compatibility (e.g. Neon/Supabase free tiers)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development" and settings.LOG_LEVEL == "DEBUG"),
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=3,
    pool_recycle=300,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative Base for ORM models (SQLAlchemy 2.x standard)
class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session per request.
    Automatically commits valid transactions and rolls back on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
