"""Authenticated staging capture adapter for the real Memory API."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from benchmarks.memory.dataset import MemoryEvaluationDataset, load_memory_evaluation_dataset
from benchmarks.memory.results import MemoryCandidateResults, MemoryQueryResult


class MemoryCaptureConfig(BaseModel):
    """External UUID/token mapping. Keep this file out of source control."""

    model_config = ConfigDict(extra="forbid")

    candidate: str
    version: str
    credentials: dict[str, str]
    projects: dict[str, str]
    sessions: dict[str, str]
    memory_ids: dict[str, str]


def load_capture_config(path: Path) -> MemoryCaptureConfig:
    return MemoryCaptureConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _memory_ids(payload: dict[str, Any]) -> list[str]:
    groups = (
        payload.get("session_memories", []),
        payload.get("user_memories", []),
        payload.get("semantic_memories", []),
        payload.get("research_memories", []),
    )
    return [str(item["id"]) for group in groups for item in group]


def _selected_tokens(payload: dict[str, Any]) -> int:
    groups = (
        payload.get("session_memories", []),
        payload.get("user_memories", []),
        payload.get("semantic_memories", []),
        payload.get("research_memories", []),
    )
    # Matches the Memory formatter's documented conservative approximation.
    return sum(max(1, len(str(item.get("content", ""))) // 4) for group in groups for item in group)


async def capture_live_memory_results(
    *,
    dataset: MemoryEvaluationDataset,
    config: MemoryCaptureConfig,
    base_url: str,
    client: httpx.AsyncClient | None = None,
) -> MemoryCandidateResults:
    reverse_ids = {real_id: logical_id for logical_id, real_id in config.memory_ids.items()}
    owns_client = client is None
    http = client or httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=60)
    captured: list[MemoryQueryResult] = []

    try:
        for query in dataset.queries:
            token = config.credentials.get(query.credential_key)
            session_id = config.sessions.get(query.session_key)
            project_id = config.projects.get(query.project_key) if query.project_key else None
            if (
                token is None
                or session_id is None
                or (query.project_key is not None and project_id is None)
            ):
                raise ValueError(f"Capture config is incomplete for query {query.query_id!r}")

            headers = {"Authorization": f"Bearer {token}"}
            search_started = perf_counter()
            search = await http.post(
                "/api/v1/memory/search",
                headers=headers,
                json={
                    "query": query.query,
                    "memory_types": query.memory_types,
                    "top_k": query.top_k,
                    "scope_type": query.scope_type,
                    "project_id": project_id,
                },
            )
            search.raise_for_status()
            search_payload = search.json()

            context = await http.get(
                "/api/v1/memory/context",
                headers=headers,
                params={
                    "session_id": session_id,
                    "semantic_query": query.query,
                    "top_k": query.top_k,
                    "scope_type": query.scope_type,
                    "project_id": project_id,
                    "inherit_personal_user_memory": str(query.inherit_personal_user_memory).lower(),
                },
            )
            context.raise_for_status()

            retrieved_real = [str(item["id"]) for item in search_payload["memories"]]
            context_payload = context.json()
            selected_real = _memory_ids(context_payload)
            captured.append(
                MemoryQueryResult(
                    query_id=query.query_id,
                    retrieved_memory_ids=[
                        reverse_ids.get(memory_id, f"unmapped:{memory_id}")
                        for memory_id in retrieved_real
                    ],
                    selected_memory_ids=[
                        reverse_ids.get(memory_id, f"unmapped:{memory_id}")
                        for memory_id in selected_real
                    ],
                    latency_ms=(perf_counter() - search_started) * 1000,
                    selected_tokens=_selected_tokens(context_payload),
                )
            )
    finally:
        if owns_client:
            await http.aclose()

    return MemoryCandidateResults(
        candidate=config.candidate,
        version=config.version,
        dataset_version=dataset.version,
        results=captured,
    )


async def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = await capture_live_memory_results(
        dataset=load_memory_evaluation_dataset(args.dataset),
        config=load_capture_config(args.config),
        base_url=args.base_url,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"Captured {len(result.results)} memory scenarios to {args.output}")


if __name__ == "__main__":
    asyncio.run(_main())
