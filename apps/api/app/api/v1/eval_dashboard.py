"""Internal eval dashboard read endpoints (E7, EVALUATION_PLAN.md §16 phase 8).

Every route here is gated by `require_eval_dashboard_access` on top of
normal authentication -- an internal engineering tool, not a
customer-facing surface. See `dependencies/eval_dashboard.py`'s own
docstring for why that's a settings-based allowlist, not a schema change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies.eval_dashboard import require_eval_dashboard_access
from app.dependencies.eval_score import get_eval_score_repository
from app.dependencies.research import get_research_run_repository
from app.models.user import User
from app.repositories.eval_score import EvalScoreRepository
from app.repositories.research_run import ResearchRunRepository
from app.schemas.eval_dashboard import (
    ContentSegmentAnalysisResponse,
    EvalScoreListResponse,
    EvalScoreResponse,
    FingerprintSegmentAggregate,
    FingerprintSegmentAnalysisResponse,
    OfflineExampleListResponse,
    OfflineExampleSummary,
    OwnerListResponse,
    OwnerSummary,
    ReviewDecisionDistributionResponse,
)
from app.services.benchmark_reports import list_benchmark_reports, list_offline_summaries
from app.services.segment_analysis import aggregate_offline_by_content_segment
from benchmarks.models.report import BenchmarkReport

router = APIRouter(prefix="/eval-dashboard", tags=["Eval Dashboard"])


@router.get(
    "/owners",
    response_model=OwnerListResponse,
    summary="Search owners who have eval_scores data",
)
async def list_owners(
    search: str | None = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_eval_dashboard_access),
    repository: EvalScoreRepository = Depends(get_eval_score_repository),
) -> OwnerListResponse:
    """
    The "pick a user" step before drilling into their eval trend.
    `search` matches email/username (case-insensitive substring).
    """

    rows, total = await repository.search_owners_with_scores(
        search=search,
        limit=limit,
        offset=offset,
    )

    return OwnerListResponse(
        items=[
            OwnerSummary(
                owner_id=user.id,
                email=user.email,
                username=user.username,
                score_count=count,
            )
            for user, count in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/scores",
    response_model=EvalScoreListResponse,
    summary="One owner's eval_scores, paginated",
)
async def list_scores(
    owner_id: UUID = Query(...),
    metric_name: str | None = Query(default=None, min_length=1, max_length=50),
    source: str | None = Query(default=None, min_length=1, max_length=30),
    since: datetime | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_eval_dashboard_access),
    repository: EvalScoreRepository = Depends(get_eval_score_repository),
) -> EvalScoreListResponse:
    """
    Every signal for one owner in one place -- online-sampled automated
    scores, mirrored human feedback, all sliceable by `metric_name`/
    `source`/`since`. Answers "what's this user's recent quality trend"
    without a raw SQL query (E7's acceptance criterion).
    """

    rows, total = await repository.list_for_owner_page(
        owner_id,
        metric_name=metric_name,
        source=source,
        since=since,
        limit=limit,
        offset=offset,
    )

    return EvalScoreListResponse(
        items=[EvalScoreResponse.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


FingerprintField = Literal[
    "surface",
    "prompt_version",
    "chunking_strategy",
    "embedding_model",
    "reranker",
    "routing_strategy",
]
"""Must stay in sync with `ONLINE_FINGERPRINT_FIELDS` (eval_score repository)."""

ContentSegmentField = Literal["query_type", "difficulty", "workflow"]
"""Must stay in sync with `CONTENT_SEGMENT_FIELDS` (segment_analysis service)."""


@router.get(
    "/segment-analysis/online",
    response_model=FingerprintSegmentAnalysisResponse,
    summary="Online eval_scores grouped by one config-fingerprint field (E9)",
)
async def segment_analysis_online(
    metric_name: str = Query(..., min_length=1, max_length=50),
    fingerprint_field: FingerprintField = Query(...),
    _current_user: User = Depends(require_eval_dashboard_access),
    repository: EvalScoreRepository = Depends(get_eval_score_repository),
) -> FingerprintSegmentAnalysisResponse:
    """
    "Did average `faithfulness` differ between `prompt_version` X and
    Y" -- groups online-sampled scores by a `GenerationUsage`
    config-fingerprint field. Only meaningful for online traffic:
    offline-benchmark rows have no `generation_usage` row to join
    against (see `EvalScoreRepository.aggregate_online_by_fingerprint`'s
    docstring). No before/after diffing here, same as every other view
    in this dashboard -- read the rows for each fingerprint value and
    compare by eye.
    """

    rows = await repository.aggregate_online_by_fingerprint(
        metric_name=metric_name,
        fingerprint_field=fingerprint_field,
    )

    return FingerprintSegmentAnalysisResponse(
        metric_name=metric_name,
        fingerprint_field=fingerprint_field,
        items=[
            FingerprintSegmentAggregate(
                fingerprint_value=value,
                count=count,
                avg_score=avg_score,
                pass_rate=pass_rate,
            )
            for value, count, avg_score, pass_rate in rows
        ],
    )


@router.get(
    "/segment-analysis/offline",
    response_model=ContentSegmentAnalysisResponse,
    summary="Offline eval_scores grouped by a golden-example field (E9)",
)
async def segment_analysis_offline(
    metric_name: str = Query(..., min_length=1, max_length=50),
    segment_field: ContentSegmentField = Query(...),
    _current_user: User = Depends(require_eval_dashboard_access),
    repository: EvalScoreRepository = Depends(get_eval_score_repository),
) -> ContentSegmentAnalysisResponse:
    """
    "Is average `faithfulness` worse for `query_type=comparison` than
    for `query_type=factual`" -- groups offline-benchmark scores by a
    golden-example field. `query_type`/`difficulty`/`workflow` live in
    `datasets/golden/rag_answer_gold.json`, not Postgres, so the join
    happens in Python (`aggregate_offline_by_content_segment`), not SQL.
    """

    rows = await repository.list_offline_scores_for_metric(metric_name=metric_name)

    return ContentSegmentAnalysisResponse(
        metric_name=metric_name,
        segment_field=segment_field,
        items=aggregate_offline_by_content_segment(rows, segment_field=segment_field),
    )


@router.get(
    "/benchmark-reports",
    response_model=list[BenchmarkReport],
    summary="Latest report.json for every engineering benchmark on disk",
)
async def benchmark_reports(
    _current_user: User = Depends(require_eval_dashboard_access),
    reports: list[BenchmarkReport] = Depends(list_benchmark_reports),
) -> list[BenchmarkReport]:
    """
    Chunking/embeddings/retrieval/reranking/generation-provider-comparison
    benchmarks each produce a `BenchmarkReport` under `benchmarks/reports/`
    but were never visible anywhere but the filesystem before this --
    unlike `GoldenSetGeneration`, none of them are persisted to
    `eval_scores`. This is a read-only view of whatever's on disk from
    each benchmark's last run: no history, no trends, just "what does
    the latest run say right now."
    """

    return reports


@router.get(
    "/offline-summary",
    response_model=list[BenchmarkReport],
    summary="Latest aggregate metrics for GoldenSetGeneration/ProductionFailuresRegression",
)
async def offline_summary(
    _current_user: User = Depends(require_eval_dashboard_access),
    reports: list[BenchmarkReport] = Depends(list_offline_summaries),
) -> list[BenchmarkReport]:
    """
    The mirror image of `/benchmark-reports` (above): those exclude
    `GoldenSetGeneration`/`ProductionFailuresRegression` since their
    per-example detail already has a dedicated, DB-backed view
    (`/offline-examples` + `/offline-scores`) -- but that view has no
    place to show the *aggregate* numbers from the latest run (e.g.
    `rubric_adherence: 0.71` across the whole golden set). `notes`
    stripped from every candidate here (see `list_offline_summaries`),
    same "what does the latest run say right now" freshness contract as
    `/benchmark-reports`.
    """

    return reports


@router.get(
    "/review-decisions",
    response_model=ReviewDecisionDistributionResponse,
    summary="Distribution of Deep Research review decisions for one owner",
)
async def review_decisions(
    owner_id: UUID = Query(...),
    _current_user: User = Depends(require_eval_dashboard_access),
    repository: ResearchRunRepository = Depends(get_research_run_repository),
) -> ReviewDecisionDistributionResponse:
    """
    `ResearchReview.decision` (PASS/REVISE_SYNTHESIS/...) is computed on
    every Deep Research run but was never rolled into a per-owner view
    before E7 -- the Wave-0 Grafana panel is aggregate-only, not
    owner-scoped (EVALUATION_PLAN.md §10).
    """

    counts = await repository.review_decision_counts_for_owner(owner_id)

    return ReviewDecisionDistributionResponse(owner_id=owner_id, counts=counts)


@router.get(
    "/offline-examples",
    response_model=OfflineExampleListResponse,
    summary="Search golden-set examples that have offline-benchmark scores",
)
async def list_offline_examples(
    search: str | None = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_eval_dashboard_access),
    repository: EvalScoreRepository = Depends(get_eval_score_repository),
) -> OfflineExampleListResponse:
    """
    The "pick an example" step before drilling into a golden-set
    example's `GoldenSetBenchmark` run history. Deliberately not
    owner-scoped -- offline rows have no `owner_id`, so `/scores`
    (which requires one) can never return them; this is the read path
    that was missing until now.
    """

    rows, total = await repository.search_offline_examples(
        search=search,
        limit=limit,
        offset=offset,
    )

    return OfflineExampleListResponse(
        items=[
            OfflineExampleSummary(
                dataset_example_id=example_id,
                score_count=count,
                latest_run_at=latest_run_at,
            )
            for example_id, count, latest_run_at in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/offline-scores",
    response_model=EvalScoreListResponse,
    summary="Offline-benchmark eval_scores, paginated",
)
async def list_offline_scores(
    dataset_example_id: str | None = Query(default=None, min_length=1, max_length=100),
    metric_name: str | None = Query(default=None, min_length=1, max_length=50),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_eval_dashboard_access),
    repository: EvalScoreRepository = Depends(get_eval_score_repository),
) -> EvalScoreListResponse:
    """
    `GoldenSetBenchmark` run history -- append-only (E6), so a given
    `dataset_example_id`/`metric_name` pair can have many rows over
    time, one per benchmark run. Omitting `dataset_example_id` shows the
    most recent offline scores across every example.
    """

    rows, total = await repository.list_offline_page(
        dataset_example_id=dataset_example_id,
        metric_name=metric_name,
        limit=limit,
        offset=offset,
    )

    return EvalScoreListResponse(
        items=[EvalScoreResponse.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
