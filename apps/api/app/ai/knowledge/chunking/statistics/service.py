"""
Chunk statistics service.

Responsibilities:

- character_count
- word_count
- sentence_count
- estimated_token_count
- average_token_length

This service centralizes all chunk statistics calculations.

Every chunking provider (Fixed, Recursive, Markdown, Hierarchical,
Semantic, LLM, Adaptive) should delegate statistics generation to this
service rather than implementing the logic themselves.

Keeping statistics independent from chunking algorithms avoids code
duplication and ensures consistent statistics across every chunking
strategy.
"""

from __future__ import annotations

import re

from app.ai.knowledge.chunking.models import ChunkStatistics


class ChunkStatisticsService:
    """
    Service responsible for generating statistics for a chunk.

    The service is intentionally stateless and reusable across all
    chunking providers.
    """

    _TOKEN_ESTIMATION_RATIO = 4

    _SENTENCE_PATTERN = re.compile(r"[.!?]+")

    @classmethod
    def build(
        cls,
        text: str,
    ) -> ChunkStatistics:
        """
        Build statistics for a chunk.

        Args:
            text:
                Chunk text.

        Returns:
            Calculated ChunkStatistics.
        """

        words = text.split()

        word_count = len(words)

        character_count = len(text)

        sentence_count = cls._count_sentences(text)

        estimated_token_count = cls._estimate_tokens(character_count)

        average_token_length = cls._calculate_average_token_length(words)

        return ChunkStatistics(
            character_count=character_count,
            word_count=word_count,
            sentence_count=sentence_count,
            estimated_token_count=estimated_token_count,
            average_token_length=average_token_length,
        )

    @classmethod
    def _count_sentences(
        cls,
        text: str,
    ) -> int:
        """
        Estimate the number of sentences within a chunk.

        This is intentionally lightweight for the baseline chunker.
        Future milestones may replace this with tokenizer- or NLP-based
        sentence segmentation.
        """

        matches = cls._SENTENCE_PATTERN.findall(text)

        return len(matches)

    @classmethod
    def _estimate_tokens(
        cls,
        character_count: int,
    ) -> int:
        """
        Estimate token count.

        Uses the common approximation that one token is roughly four
        characters for English text.

        This heuristic will be replaced by tokenizer-aware estimation in
        a future milestone.
        """

        if character_count == 0:
            return 0

        return max(
            1,
            round(character_count / cls._TOKEN_ESTIMATION_RATIO),
        )

    @staticmethod
    def _calculate_average_token_length(
        words: list[str],
    ) -> float:
        """
        Calculate the average token length.

        Returns:
            Average number of characters per token.
        """

        if not words:
            return 0.0

        return sum(len(word) for word in words) / len(words)
