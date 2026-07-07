"""
Verify the Voyage AI SDK is wired up end-to-end.

Exercises registry registration, dependency injection, API key loading,
and Voyage client creation without making an embedding call.
"""

from app.ai.knowledge.embeddings.create import create_embedding_registry
from app.ai.knowledge.embeddings.enums import EmbeddingProvider

registry = create_embedding_registry()

provider = registry.get(EmbeddingProvider.VOYAGE_AI)

print(provider.provider)
print(provider.model)
