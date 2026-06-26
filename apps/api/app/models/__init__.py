"""
ResearchMind ORM models.

Import all ORM models here so SQLAlchemy metadata
is populated for Alembic autogeneration.
"""

from app.models.user import User

__all__ = [
    "User",
]
