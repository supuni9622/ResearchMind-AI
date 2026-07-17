from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.runtime.generation.routing.models import (
    RoutingDecision,
    RoutingRequest,
)


class RoutingServiceInterface(
    ABC,
):
    """
    Canonical contract for resolving a `RoutingRequest` into a
    `RoutingDecision`. Deliberately synchronous — routing is a pure,
    in-memory decision over catalog metadata, not an I/O call.
    """

    @abstractmethod
    def route(
        self,
        request: RoutingRequest,
    ) -> RoutingDecision:
        pass
