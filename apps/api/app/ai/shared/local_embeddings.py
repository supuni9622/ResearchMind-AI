from functools import lru_cache

from sentence_transformers import (
    SentenceTransformer,
)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_local_embedding_model() -> SentenceTransformer:
    # sentence_transformers' top-level re-export resolves to `Any` under
    # mypy (see SentenceTransformerEmbeddingProvider._get_model for the
    # same pattern), so the constructor result is laundered through an
    # explicitly annotated local before returning.
    model: SentenceTransformer = SentenceTransformer(
        MODEL_NAME,
    )

    return model
