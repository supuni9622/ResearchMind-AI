"""
Reranking Platform composition root.
"""

from app.ai.knowledge.reranking.config import (
    CrossEncoderConfig,
    VoyageRerankerConfig,
)
from app.ai.knowledge.reranking.interfaces import (
    RerankingProviderInterface,
)
from app.ai.knowledge.reranking.providers.cross_encoder import (
    CrossEncoderReranker,
)
from app.ai.knowledge.reranking.providers.voyage import (
    VoyageReranker,
)
from app.ai.knowledge.reranking.registry import (
    RerankingRegistry,
)
from app.ai.knowledge.reranking.service import (
    RerankingService,
)
from app.core.settings import (
    settings,
)


def create_reranking_registry() -> RerankingRegistry:
    """
    Create fully configured registry.
    """

    providers: list[RerankingProviderInterface] = [
        CrossEncoderReranker(
            config=CrossEncoderConfig(
                model=(settings.cross_encoder_model),
            ),
        ),
    ]

    #
    # Voyage optional.
    #

    if settings.voyage_api_key:
        providers.append(
            VoyageReranker(
                config=VoyageRerankerConfig(
                    model=(settings.voyage_reranker_model),
                ),
            )
        )

    return RerankingRegistry(
        providers,
    )


def create_reranking_service() -> RerankingService:
    """
    Create reranking service.
    """

    return RerankingService(
        registry=(create_reranking_registry()),
    )
