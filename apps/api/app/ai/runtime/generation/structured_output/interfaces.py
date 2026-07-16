from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class OutputParserInterface(
    ABC,
):
    @abstractmethod
    async def parse(
        self,
        text: str,
        schema: type[BaseModel] | None = None,
    ) -> Any:
        pass
