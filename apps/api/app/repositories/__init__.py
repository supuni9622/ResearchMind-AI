"""
ResearchMind repositories.

Repositories encapsulate all database access and are responsible
only for persistence operations.

Business logic belongs in the service layer.
"""

from app.repositories.user import UserRepository

__all__ = [
    "UserRepository",
]
