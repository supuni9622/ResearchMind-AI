from __future__ import annotations

from typing import Any

import jwt
from jwt import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
    PyJWKClient,
)

from app.auth.providers.base import AuthenticationProvider
from app.exceptions.base import UnauthorizedException


class JWTVerifier:
    """
    Generic JWT verifier.

    Provider-specific configuration is supplied by
    the authentication provider.
    """

    def __init__(
        self,
        provider: AuthenticationProvider,
    ) -> None:
        self.provider = provider

        self.jwks_client = PyJWKClient(
            provider.jwks_url,
        )

    async def verify(
        self,
        token: str,
    ) -> dict[str, Any]:
        """
        Verify a JWT and return normalized claims.
        """

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(
                token,
            )

            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.provider.algorithms,
                audience=self.provider.audience,
                issuer=self.provider.issuer,
            )

        except ExpiredSignatureError as exc:
            raise UnauthorizedException(
                message="Authentication token has expired.",
            ) from exc

        except InvalidAudienceError as exc:
            raise UnauthorizedException(
                message="Invalid token audience.",
            ) from exc

        except InvalidIssuerError as exc:
            raise UnauthorizedException(
                message="Invalid token issuer.",
            ) from exc

        except InvalidTokenError as exc:
            raise UnauthorizedException(
                message="Invalid authentication token.",
            ) from exc

        token_use = claims.get("token_use")

        if token_use != "id":
            raise UnauthorizedException(
                message="Invalid token type.",
            )

        return self.provider.normalize_claims(
            claims,
        )
