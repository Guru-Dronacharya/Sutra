"""Database engine, sessions, and base model declarations.
Supports PostgreSQL (asyncpg) in Docker/Production and zero-latency SQLite locally.
Traceability: REQ-3.1, REQ-3.4, REQ-4.1, REQ-5.1
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from services.common.config import settings


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy entities."""
    pass


is_postgres = "postgresql" in settings.DATABASE_URL

if is_postgres:
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    # Always ensure sync_url has no +asyncpg or +aiosqlite driver tags
    raw_sync = settings.SYNC_DATABASE_URL or settings.DATABASE_URL
    sync_url = raw_sync.replace("+asyncpg", "").replace("+aiosqlite", "")
    try:
        sync_engine = create_engine(sync_url, echo=False)
    except Exception:
        if sync_url.startswith("postgresql://"):
            sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            sync_engine = create_engine(sync_url, echo=False)
        else:
            raise
    SyncSessionLocal = sessionmaker(
        bind=sync_engine,
        expire_on_commit=False,
        autoflush=False,
    )
else:
    # Synchronous SQLite engine with zero-overhead async wrapper
    sync_url = settings.DATABASE_URL.replace("sqlite+aiosqlite:", "sqlite:")
    engine = create_engine(
        sync_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
    SyncSessionLocal = sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )

    class SQLiteAsyncSessionWrapper:
        """Transparent wrapper allowing async/await syntax over synchronous SQLite."""
        def __init__(self, sync_session):
            self._session = sync_session
            self.sync_session = sync_session

        async def execute(self, stmt, *args, **kwargs):
            return self._session.execute(stmt, *args, **kwargs)

        async def scalars(self, stmt, *args, **kwargs):
            return self._session.scalars(stmt, *args, **kwargs)

        async def scalar(self, stmt, *args, **kwargs):
            return self._session.scalar(stmt, *args, **kwargs)

        def add(self, instance):
            self._session.add(instance)

        def add_all(self, instances):
            self._session.add_all(instances)

        async def commit(self):
            self._session.commit()

        async def rollback(self):
            self._session.rollback()

        async def close(self):
            self._session.close()

        async def refresh(self, instance):
            self._session.refresh(instance)

        async def delete(self, instance):
            self._session.delete(instance)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self._session.rollback()
            else:
                self._session.commit()
            self._session.close()

    class AsyncSessionLocalFactory:
        def __call__(self):
            return SQLiteAsyncSessionWrapper(SyncSessionLocal())

    AsyncSessionLocal = AsyncSessionLocalFactory()


async def get_db() -> AsyncGenerator[Any, None]:
    """FastAPI dependency for yielding transactional database sessions."""
    if is_postgres:
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    else:
        session = SQLiteAsyncSessionWrapper(SyncSessionLocal())
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[Any, None]:
    """Context manager for standalone scripts, background workers, and evaluation runs."""
    if is_postgres:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    else:
        session = SQLiteAsyncSessionWrapper(SyncSessionLocal())
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def init_db(retries: int = 5, delay: float = 2.0) -> None:
    """Initialize database tables and register immutable triggers with retry resiliency."""
    import time
    raw_sync = settings.SYNC_DATABASE_URL or settings.DATABASE_URL
    sync_url = raw_sync.replace("+asyncpg", "").replace("+aiosqlite", "")
    try:
        sync_engine = create_engine(
            sync_url,
            echo=False,
            connect_args={"check_same_thread": False} if "sqlite" in sync_url else {},
        )
    except Exception:
        if sync_url.startswith("postgresql://"):
            sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            sync_engine = create_engine(sync_url, echo=False)
        else:
            raise
    for attempt in range(retries):
        try:
            Base.metadata.create_all(bind=sync_engine)
            if "postgresql" in sync_url:
                try:
                    with sync_engine.begin() as conn:
                        conn.execute(text("""
                        CREATE OR REPLACE FUNCTION prevent_audit_tampering() RETURNS TRIGGER AS $$
                        BEGIN
                            RAISE EXCEPTION 'Audit entries are cryptographically immutable. UPDATE and DELETE are prohibited.';
                        END;
                        $$ LANGUAGE plpgsql;
                        """))
                        conn.execute(text("DROP TRIGGER IF EXISTS trg_audit_entries_immutable ON audit_entries;"))
                        conn.execute(text("""
                        CREATE TRIGGER trg_audit_entries_immutable
                        BEFORE UPDATE OR DELETE ON audit_entries
                        FOR EACH ROW EXECUTE FUNCTION prevent_audit_tampering();
                        """))
                except Exception as trigger_err:
                    print(f"[Warning] Trigger creation skipped/handled: {trigger_err}")
            break
        except Exception as e:
            if attempt == retries - 1:
                print(f"[Database Error] init_db failed after {retries} attempts: {e}")
                raise
            time.sleep(delay)
