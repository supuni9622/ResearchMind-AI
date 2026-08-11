from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.core.settings import settings
from app.models.user import User
from app.schemas.auth import CallbackRequest, TokenResponse
from app.services.auth import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/callback", response_model=TokenResponse)
async def callback(body: CallbackRequest) -> TokenResponse:
    """
    Exchange a Cognito authorization code for tokens.

    The frontend calls this after Cognito redirects to
    /auth/callback?code=<code>. Returns the id_token to use
    as a Bearer token for all subsequent API requests.
    """

    tokens = await AuthService().exchange_code(
        code=body.code,
        redirect_uri=body.redirect_uri,
        code_verifier=body.code_verifier,
    )

    return TokenResponse(
        id_token=tokens["id_token"],
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        token_type=tokens.get("token_type", "Bearer"),
        expires_in=tokens["expires_in"],
    )


@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),
):
    """
    Return the authenticated user.
    """

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "avatar_url": current_user.avatar_url,
        "provider": current_user.auth_provider,
        "verified": current_user.is_verified,
        # Lets the frontend show/hide the internal eval dashboard nav
        # link without duplicating the allowlist client-side (E7,
        # EVALUATION_IMPLEMENTATION_TRACKER.md) -- the real access
        # check still happens server-side on every
        # /api/v1/eval-dashboard/* request via
        # require_eval_dashboard_access; this is presentation only.
        "eval_dashboard_access": settings.is_eval_dashboard_admin(current_user.email),
    }
