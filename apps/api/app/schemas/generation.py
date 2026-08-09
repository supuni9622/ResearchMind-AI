"""Generation capability response models."""

from pydantic import BaseModel

from app.ai.runtime.generation.enums import GenerationProvider


class GenerationProvidersResponse(BaseModel):
    providers: list[GenerationProvider]
