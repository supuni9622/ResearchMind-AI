from fastapi import APIRouter, Request

from app.core.health import get_health_status
from app.schemas.common import SuccessResponse
from app.schemas.health import (
    HealthServices,
    HealthStatus,
    LiveResponse,
    ReadyResponse,
)

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "/live",
    response_model=SuccessResponse[LiveResponse],
    summary="Liveness probe",
)
async def live() -> SuccessResponse[LiveResponse]:
    return SuccessResponse(
        data=LiveResponse(
            status="alive",
        )
    )


@router.get(
    "/ready",
    response_model=SuccessResponse[ReadyResponse],
    summary="Readiness probe",
)
async def ready() -> SuccessResponse[ReadyResponse]:
    return SuccessResponse(
        data=ReadyResponse(
            status="ready",
        )
    )


@router.get(
    "",
    response_model=SuccessResponse[HealthStatus],
    summary="Infrastructure health check",
)
async def health(
    request: Request,
) -> SuccessResponse[HealthStatus]:
    result = await get_health_status(request)

    return SuccessResponse(
        data=HealthStatus(
            status=result["status"],
            services=HealthServices(
                postgres=result["services"]["postgres"],
                valkey=result["services"]["valkey"],
                qdrant=result["services"]["qdrant"],
            ),
        )
    )
