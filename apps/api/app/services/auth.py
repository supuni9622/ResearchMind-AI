from __future__ import annotations

import base64

import httpx
import structlog

from app.core.settings import settings
from app.exceptions.base import AppException

logger = structlog.get_logger()


class AuthService:
    """
    Handles OAuth token exchange with the configured identity provider.
    """

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> dict:
        """
        Exchange a Cognito authorization code for tokens.
        Returns the raw token response from Cognito.
        """

        if not settings.cognito_domain:
            raise AppException(
                code="AUTH_MISCONFIGURED",
                message="Authentication provider is not configured.",
                status_code=500,
            )

        if not settings.cognito_app_client_id:
            raise AppException(
                code="AUTH_MISCONFIGURED",
                message="Authentication provider is not configured.",
                status_code=500,
            )

        token_url = f"{settings.cognito_domain.rstrip('/')}/oauth2/token"

        payload: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": settings.cognito_app_client_id,
        }

        if code_verifier:
            payload["code_verifier"] = code_verifier

        headers: dict[str, str] = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Confidential clients must send credentials via Basic auth.
        if settings.cognito_client_secret:
            credentials = base64.b64encode(
                f"{settings.cognito_app_client_id}:{settings.cognito_client_secret}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

        logger.info("auth.code_exchange_started", redirect_uri=redirect_uri)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=payload,
                headers=headers,
            )

        if response.status_code != 200:
            cognito_error = response.json().get("error")
            logger.warning("auth.code_exchange_failed", cognito_error=cognito_error)
            raise AppException(
                code="AUTH_CODE_EXCHANGE_FAILED",
                message="Failed to exchange authorization code.",
                status_code=401,
                details={"cognito_error": cognito_error},
            )

        logger.info("auth.code_exchange_succeeded")
        return dict(response.json())
