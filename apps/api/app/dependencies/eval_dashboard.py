"""
Access control for the internal eval dashboard (E7, EVALUATION_PLAN.md
§16 phase 8).

Settings-based email allowlist, not a `User.is_admin` column -- this is
internal engineering tooling with no admin-management UI, not a
customer-facing feature needing real RBAC. See `settings.
eval_dashboard_admin_emails`'s own docstring for the full reasoning.
"""

from __future__ import annotations

from fastapi import Depends

from app.auth.dependencies import get_current_user
from app.core.settings import settings
from app.exceptions.base import ForbiddenException
from app.models.user import User


async def require_eval_dashboard_access(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Raises `ForbiddenException` (403) unless `current_user.email` is on
    `settings.eval_dashboard_admin_emails`. Authentication itself
    (`get_current_user`) already ran and would have raised 401 for an
    unauthenticated request -- this only adds the allowlist check on
    top, for a route every other endpoint in this codebase leaves open
    to any authenticated user.
    """

    if not settings.is_eval_dashboard_admin(current_user.email):
        raise ForbiddenException(
            message="You do not have access to the internal eval dashboard.",
        )

    return current_user
