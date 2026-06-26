from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    All database entities in ResearchMind inherit from this class.
    """

    pass


# Import all models so Base.metadata is populated for Alembic and tests.
# Must stay at the bottom to avoid a circular import (models import Base above).
from app import models as _models  # noqa: F401, E402
