from __future__ import annotations

import json
import re
from typing import Any


class StructuredOutputRepair:
    """
    Attempts to repair common LLM
    structured output mistakes.

    Supported repairs:

    - remove markdown code blocks
    - extract embedded json
    - fix trailing commas
    - fix single quotes
    - fix missing braces
    """

    @classmethod
    def clean(
        cls,
        text: str,
    ) -> str:

        text = cls.remove_code_blocks(
            text,
        )

        text = cls.extract_json(
            text,
        )

        text = cls.fix_missing_braces(
            text,
        )

        text = cls.fix_trailing_commas(
            text,
        )

        text = cls.fix_quotes(
            text,
        )

        return text.strip()

    ####################################################################
    # Markdown
    ####################################################################

    @staticmethod
    def remove_code_blocks(
        text: str,
    ) -> str:

        text = re.sub(
            r"```json",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"```",
            "",
            text,
        )

        return text.strip()

    ####################################################################
    # Embedded JSON
    ####################################################################

    @staticmethod
    def extract_json(
        text: str,
    ) -> str:

        text = text.strip()

        #
        # object
        #

        object_match = re.search(
            r"(\{.*\})",
            text,
            flags=re.DOTALL,
        )

        if object_match:
            return object_match.group(
                1,
            )

        #
        # array
        #

        array_match = re.search(
            r"(\[.*\])",
            text,
            flags=re.DOTALL,
        )

        if array_match:
            return array_match.group(
                1,
            )

        return text

    ####################################################################
    # Trailing commas
    ####################################################################

    @staticmethod
    def fix_trailing_commas(
        text: str,
    ) -> str:
        """
        Converts:

        {
            "a":1,
        }

        into:

        {
            "a":1
        }
        """

        return re.sub(
            r",(\s*[}\]])",
            r"\1",
            text,
        )

    ####################################################################
    # Single quotes
    ####################################################################

    @staticmethod
    def fix_quotes(
        text: str,
    ) -> str:
        """
        Converts:

        {'a':'b'}

        into:

        {"a":"b"}

        This is intentionally conservative.
        """

        try:
            json.loads(
                text,
            )

            return text

        except Exception:
            pass

        #
        # only run if invalid
        #

        text = re.sub(
            r"'([^']*)'",
            r'"\1"',
            text,
        )

        return text

    ####################################################################
    # Missing braces
    ####################################################################

    @staticmethod
    def fix_missing_braces(
        text: str,
    ) -> str:

        stripped = text.strip()

        #
        # object
        #

        if ":" in stripped and not stripped.startswith(
            "{",
        ):
            stripped = "{" + stripped

        if stripped.startswith(
            "{",
        ) and not stripped.endswith(
            "}",
        ):
            stripped += "}"

        #
        # array
        #

        if stripped.startswith(
            "[",
        ) and not stripped.endswith(
            "]",
        ):
            stripped += "]"

        return stripped

    ####################################################################
    # Parsing
    ####################################################################

    @classmethod
    def try_parse_json(
        cls,
        text: str,
    ) -> dict[str, Any]:

        cleaned = cls.clean(
            text,
        )

        parsed = json.loads(
            cleaned,
        )

        if not isinstance(parsed, dict):
            raise ValueError("Expected a JSON object.")

        return parsed
