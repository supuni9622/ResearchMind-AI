from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
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
    }
