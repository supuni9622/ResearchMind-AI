from __future__ import annotations

from typing import Any

from app.auth.providers.base import AuthenticationProvider
from app.core.settings import settings


class CognitoAuthenticationProvider(AuthenticationProvider):
    """
    AWS Cognito authentication provider.
    """

    @property
    def provider_name(self) -> str:
        return "cognito"

    @property
    def issuer(self) -> str:
        return (
            f"https://cognito-idp."
            f"{settings.aws_region}.amazonaws.com/"
            f"{settings.cognito_user_pool_id}"
        )

    @property
    def audience(self) -> str:
        return settings.cognito_app_client_id or ""

    @property
    def algorithms(self) -> list[str]:
        return ["RS256"]

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"

    def normalize_claims(
        self,
        claims: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize Cognito JWT claims into the application's
        provider-independent identity format.
        """

        return {
            "provider": self.provider_name,
            "provider_user_id": claims["sub"],
            "email": claims.get("email"),
            "email_verified": claims.get("email_verified", False),
            "full_name": claims.get("name"),
            "username": claims.get("cognito:username"),
            "avatar_url": claims.get("picture"),
        }
