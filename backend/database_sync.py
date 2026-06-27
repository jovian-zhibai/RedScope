"""Shared sync database session for Celery tasks and sync operations."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config import get_settings

settings = get_settings()
_sync_url = settings.database_url.replace("+asyncpg", "")
sync_engine = create_engine(_sync_url, pool_size=3, max_overflow=3)
SyncSession = sessionmaker(sync_engine)
