"""Canonical enums for the Web Search Tool Platform (web_search_tool_platform_prd.md)."""

from __future__ import annotations

from enum import StrEnum


class WebSearchDepth(StrEnum):
    BASIC = "basic"
    ADVANCED = "advanced"
