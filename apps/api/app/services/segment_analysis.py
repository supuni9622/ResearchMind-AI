"""
Content-segment aggregation for E9's offline half
(EVALUATION_IMPLEMENTATION_TRACKER.md E9, EVALUATION_PLAN.md §16 phase
10).

`GenerationUsage`'s config-fingerprint fields (surface, prompt_version,
...) only exist for online-sampled traffic -- offline-benchmark rows
have no `generation_usage` row at all (see
`EvalScoreRepository.aggregate_online_by_fingerprint`'s docstring). The
offline side's equivalent segmentation dimension is the golden dataset's
own `query_type`/`difficulty`/`workflow` fields, which live in
`datasets/golden/rag_answer_gold.json`, not Postgres -- so this grouping
has to happen in Python after fetching the raw rows, not in SQL.

Deliberate app/`benchmarks` boundary crossing, same kind
`bootstrap/worker.py` and `app/services/benchmark_reports.py` already
make -- this file's whole purpose is bridging the golden dataset's
schema into the eval dashboard.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.constants import DATASETS_DIRECTORY
from app.models.eval_score import EvalScore
from benchmarks.generation.golden_dataset import load_golden_dataset

GOLDEN_DATASET_PATH = DATASETS_DIRECTORY / "golden" / "rag_answer_gold.json"

CONTENT_SEGMENT_FIELDS = ("query_type", "difficulty", "workflow")
"""
The golden-example fields E9's offline segment analysis can group by --
a closed list, not an arbitrary caller-supplied attribute name, mirroring
`ONLINE_FINGERPRINT_FIELDS`'s same safety rationale.
"""


class ContentSegmentAggregate(BaseModel):
    segment_value: str
    count: int
    avg_score: float | None
    pass_rate: float | None


def aggregate_offline_by_content_segment(
    rows: list[EvalScore],
    *,
    segment_field: str,
) -> list[ContentSegmentAggregate]:
    """
    Groups offline-benchmark `eval_scores` rows by one golden-example
    field (`segment_field`, one of `CONTENT_SEGMENT_FIELDS`) -- e.g. "is
    average `faithfulness` worse for `query_type=comparison` than for
    `query_type=factual`." A row whose `dataset_example_id` no longer
    matches any current golden example (the dataset changed since that
    row was recorded) is silently skipped rather than raising -- the
    golden set is explicitly allowed to grow/change over time (see
    `GoldenExample`'s own versioning notes), and a handful of orphaned
    historical rows shouldn't break this view.
    """

    dataset = load_golden_dataset(GOLDEN_DATASET_PATH)

    segment_by_example_id = {
        example.example_id: str(getattr(example, segment_field)) for example in dataset.examples
    }

    grouped: dict[str, list[EvalScore]] = {}

    for row in rows:
        if row.dataset_example_id is None:
            continue

        segment_value = segment_by_example_id.get(row.dataset_example_id)

        if segment_value is None:
            continue

        grouped.setdefault(segment_value, []).append(row)

    aggregates: list[ContentSegmentAggregate] = []

    for segment_value, segment_rows in sorted(grouped.items()):
        scores = [row.score for row in segment_rows if row.score is not None]
        passed_flags = [row.passed for row in segment_rows if row.passed is not None]

        aggregates.append(
            ContentSegmentAggregate(
                segment_value=segment_value,
                count=len(segment_rows),
                avg_score=(sum(scores) / len(scores)) if scores else None,
                pass_rate=(sum(passed_flags) / len(passed_flags)) if passed_flags else None,
            )
        )

    return aggregates
