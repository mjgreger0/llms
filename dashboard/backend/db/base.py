"""
SQLAlchemy declarative base and common model mixins.

This module provides the base classes for all database models in the application.
It uses SQLAlchemy 2.0 patterns with async support.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    This class uses SQLAlchemy 2.0's DeclarativeBase and provides
    the foundation for all database models in the application.
    """
    pass


class TimestampMixin:
    """
    Mixin that adds timestamp columns to models.

    Provides created_at and updated_at columns with automatic
    timestamp management using database-level defaults.

    Attributes:
        created_at: Timestamp when the record was created (set once on insert)
        updated_at: Timestamp when the record was last modified (updated on each change)
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the record was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when the record was last updated"
    )
