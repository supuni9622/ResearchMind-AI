"""
Embedding batching utilities.

Provides reusable batching helpers for embedding providers.

Batching is intentionally separated from provider implementations so
that all embedding providers share the same batching behavior while
remaining free to choose their own batch sizes.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TypeVar

T = TypeVar("T")


class EmbeddingBatcher:
    """
    Splits an iterable into fixed-size batches.

    Batches are generated lazily to avoid loading all batches into memory
    at once, making this suitable for processing large collections.
    """

    def __init__(self, batch_size: int) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero.")

        self._batch_size = batch_size

    @property
    def batch_size(self) -> int:
        """
        Configured batch size.
        """
        return self._batch_size

    def batch(self, items: Iterable[T]) -> Iterator[list[T]]:
        """
        Yield batches of items.

        Args:
            items:
                Iterable of items to batch.

        Yields:
            Lists containing up to ``batch_size`` items.
        """

        batch: list[T] = []

        for item in items:
            batch.append(item)

            if len(batch) == self._batch_size:
                yield batch
                batch = []

        if batch:
            yield batch
