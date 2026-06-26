from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AuthenticationProvider(ABC):
    """
    Base contract for authentication providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def issuer(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def audience(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def algorithms(self) -> list[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def jwks_url(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def normalize_claims(
        self,
        claims: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert provider-specific claims into the
        application's normalized identity format.
        """
        raise NotImplementedError
