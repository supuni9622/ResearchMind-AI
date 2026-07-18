from __future__ import annotations

import structlog
import tiktoken
from anthropic import AsyncAnthropic
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.core.settings import (
    settings,
)
from google import genai

logger = structlog.get_logger()


class TokenCounter:
    """
    Provider-aware token counter.

    Accuracy:

    OpenAI  -> Excellent
    Groq    -> Excellent
    Claude  -> Good
    Gemini  -> Excellent
    Ollama  -> Approximation
    """

    def __init__(
        self,
    ) -> None:

        self._anthropic = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
        )

        self._gemini = genai.Client(
            api_key=settings.gemini_api_key,
        )

    ####################################################################
    # Public
    ####################################################################

    async def count(
        self,
        provider: GenerationProvider,
        model: str,
        text: str,
    ) -> int:

        try:
            match provider:
                case GenerationProvider.OPENAI:
                    return self._count_openai(
                        model,
                        text,
                    )

                case GenerationProvider.GROQ:
                    return self._count_groq(
                        model,
                        text,
                    )

                case GenerationProvider.CLAUDE:
                    return await self._count_claude(
                        text,
                    )

                case GenerationProvider.GEMINI:
                    return await self._count_gemini(
                        model,
                        text,
                    )

                case GenerationProvider.OLLAMA:
                    return self._count_ollama(
                        text,
                    )

        except Exception:
            logger.exception(
                "token_count.failed",
                provider=provider.value,
                model=model,
            )

        #
        # Safe fallback
        #

        return self._count_approximate(
            text,
        )

    ####################################################################
    # OpenAI
    ####################################################################

    def _count_openai(
        self,
        model: str,
        text: str,
    ) -> int:

        try:
            encoding = tiktoken.encoding_for_model(
                model,
            )

        except Exception:
            encoding = tiktoken.get_encoding(
                "cl100k_base",
            )

        return len(
            encoding.encode(
                text,
            )
        )

    ####################################################################
    # Groq
    ####################################################################

    def _count_groq(
        self,
        model: str,
        text: str,
    ) -> int:
        """
        Groq uses OpenAI compatible tokenization.
        """

        return self._count_openai(
            model,
            text,
        )

    ####################################################################
    # Claude
    ####################################################################

    async def _count_claude(
        self,
        text: str,
    ) -> int:

        #
        # Anthropic SDK token counting APIs
        # change frequently.
        #
        # Keep fallback.

        try:
            response = await self._anthropic.messages.count_tokens(
                model="claude-sonnet-5",
                messages=[
                    {
                        "role": "user",
                        "content": text,
                    }
                ],
            )

            return response.input_tokens

        except Exception:
            logger.warning(
                "token_count.claude_fallback",
            )

            return self._count_approximate(
                text,
            )

    ####################################################################
    # Gemini
    ####################################################################

    async def _count_gemini(
        self,
        model: str,
        text: str,
    ) -> int:

        try:
            response = await self._gemini.aio.models.count_tokens(
                model=model,
                contents=text,
            )

            if response.total_tokens is None:
                raise ValueError("Gemini count_tokens response missing total_tokens")

            return response.total_tokens

        except Exception:
            logger.warning(
                "token_count.gemini_fallback",
            )

            return self._count_approximate(
                text,
            )

    ####################################################################
    # Ollama
    ####################################################################

    def _count_ollama(
        self,
        text: str,
    ) -> int:
        """
        Local models differ.

        Approximation is safest.
        """

        return self._count_approximate(
            text,
        )

    ####################################################################
    # Fallback
    ####################################################################

    def _count_approximate(
        self,
        text: str,
    ) -> int:
        """
        Rough estimate:

        1 token ≈ 0.75 words
        """

        words = len(
            text.split(),
        )

        return max(
            1,
            int(
                words * 1.3,
            ),
        )
