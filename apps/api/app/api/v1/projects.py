from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.dependencies.project import get_project_service
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.project import ProjectService

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


def _to_response(project: Project, role: str) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        role=role,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
async def create_project(
    payload: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = await project_service.create(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    return _to_response(project, "owner")


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List every project the current user can access",
)
async def list_projects(
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    projects = await project_service.list_for_user(user_id=current_user.id)
    return ProjectListResponse(
        projects=[_to_response(project, role) for project, role in projects],
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project",
)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = await project_service.get_for_user(user_id=current_user.id, project_id=project_id)
    role = "owner" if project.owner_id == current_user.id else "member"
    return _to_response(project, role)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project (owner-only)",
)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = await project_service.update(
        owner_id=current_user.id,
        project_id=project_id,
        name=payload.name,
        description=payload.description,
    )
    return _to_response(project, "owner")


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project (owner-only)",
)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
) -> None:
    await project_service.delete(owner_id=current_user.id, project_id=project_id)
