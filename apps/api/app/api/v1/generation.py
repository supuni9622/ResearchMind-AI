"""Generation platform capability endpoints."""

from fastapi import APIRouter, Depends

from app.ai.runtime.generation.service import GenerationService
from app.dependencies.generation import get_generation_service
from app.schemas.common import SuccessResponse
from app.schemas.generation import GenerationProvidersResponse

router = APIRouter(
    prefix="/generation",
    tags=["Generation"],
)


@router.get(
    "/providers",
    response_model=SuccessResponse[GenerationProvidersResponse],
    summary="List configured generation providers",
)
async def providers(
    generation_service: GenerationService = Depends(get_generation_service),
) -> SuccessResponse[GenerationProvidersResponse]:
    return SuccessResponse(
        data=GenerationProvidersResponse(
            providers=generation_service.registry.providers,
        )
    )
