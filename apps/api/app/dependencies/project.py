from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.project_authorization import ProjectAuthorizationService


def get_project_authorization_service(
    session: AsyncSession = Depends(get_db),
) -> ProjectAuthorizationService:
    return ProjectAuthorizationService(session)
