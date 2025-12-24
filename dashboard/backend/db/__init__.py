"""Database package for LLM Serve Dashboard.

Contains SQLAlchemy base classes, session management, and migrations.
"""

from dashboard.backend.db.base import Base, TimestampMixin
from dashboard.backend.db.session import get_db, init_db, close_db

__all__ = ["Base", "TimestampMixin", "get_db", "init_db", "close_db"]
