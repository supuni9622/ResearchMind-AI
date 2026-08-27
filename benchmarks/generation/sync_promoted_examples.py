"""
Syncs E10's confirmed promotion reviews into the actual dataset JSON
files (EVALUATION_PLAN.md §3/§15's "both directions" promotion loop).

Deliberately separate from the API, mirroring
`persist_golden_set_scores.py`'s own two-step pattern: confirming a
promotion in the review-queue UI only ever writes a `promotion_reviews`
row (`status="confirmed", synced=false`) -- it never touches
`rag_answer_gold.json`/`production_failures.json` directly, so every
change to those checked-in, version-controlled files is a normal,
git-reviewable diff, not a live API mutation. Run this as an explicit,
manual step:

    python -m benchmarks.generation.sync_promoted_examples

`direction="good"` rows are appended to `datasets/golden/rag_answer_gold.json`
with a new `p<N>`-prefixed `example_id` (distinct from the original
hand-curated `g`/`s`/`u` prefixes, so provenance stays visible in the
dataset itself). `direction="failure"` rows are appended to
`datasets/production_failures/production_failures.json` with a new
`pf<N>`-prefixed id.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.core.constants import DATASETS_DIRECTORY
from app.db.session import SessionFactory
from app.models.promotion_review import PromotionReview
from app.repositories.promotion_review import PromotionReviewRepository

from benchmarks.generation.golden_dataset import (
    Difficulty,
    ExpectedBehavior,
    GoldenDataset,
    GoldenExample,
    QueryType,
    Workflow,
    load_golden_dataset,
)

GOLDEN_DATASET_PATH = DATASETS_DIRECTORY / "golden" / "rag_answer_gold.json"
PRODUCTION_FAILURES_PATH = DATASETS_DIRECTORY / "production_failures" / "production_failures.json"

GOOD_PROMOTION_ID_PREFIX = "p"
FAILURE_PROMOTION_ID_PREFIX = "pf"


def _next_example_id(existing_ids: set[str], prefix: str) -> str:
    n = 1
    while f"{prefix}{n}" in existing_ids:
        n += 1
    return f"{prefix}{n}"


def build_golden_example(review: PromotionReview, *, example_id: str) -> GoldenExample:
    """
    Pure construction, no I/O -- `PromotionReview`'s manually-authored
    fields were deliberately shaped to mirror `GoldenExample`'s exactly
    (see that model's own module docstring), so this is a direct
    field-for-field mapping, not a translation.

    `query_type`/`difficulty`/`workflow`/`question` are nullable on the
    ORM model (shared with `status="rejected"` rows, which never set
    them) but `ConfirmPromotionRequest` requires all four -- callers only
    ever pass `status="confirmed"` rows here (see `sync()`), where they
    are guaranteed set; asserted rather than silently defaulted so a
    genuine data-integrity bug fails loudly instead of writing a
    malformed example into a version-controlled dataset file.
    """

    assert review.question, f"{review.id}: confirmed review has no question"
    assert review.query_type, f"{review.id}: confirmed review has no query_type"
    assert review.difficulty, f"{review.id}: confirmed review has no difficulty"
    assert review.workflow, f"{review.id}: confirmed review has no workflow"

    return GoldenExample(
        example_id=example_id,
        question=review.question,
        reference_answer=review.reference_answer,
        reference_context_ids=review.reference_context_ids or [],
        expected_citation_ids=review.expected_citation_ids or [],
        expected_behavior=ExpectedBehavior.ANSWER,
        query_type=QueryType(review.query_type),
        difficulty=Difficulty(review.difficulty),
        workflow=Workflow(review.workflow),
        contexts=review.contexts or [],
        rubric=review.rubric,
        failure_category=review.failure_category,
    )


async def sync(
    *,
    repository: PromotionReviewRepository,
    golden_dataset_path: Path,
    production_failures_path: Path,
) -> tuple[int, int]:
    """
    Returns `(promoted_to_golden, promoted_to_failures)`. Caller owns the
    session/commit boundary (each sync'd row's `synced=true` is flushed,
    not committed, by `mark_synced` -- matches `EvalScoreRepository`'s
    established write-vs-commit split).
    """

    confirmed = await repository.list_confirmed_unsynced()
    if not confirmed:
        return 0, 0

    golden_dataset = load_golden_dataset(golden_dataset_path)
    production_failures = (
        load_golden_dataset(production_failures_path)
        if production_failures_path.exists()
        else GoldenDataset(version="1.0", notes="", examples=[])
    )

    golden_ids = {example.example_id for example in golden_dataset.examples}
    failure_ids = {example.example_id for example in production_failures.examples}

    good_count = 0
    failure_count = 0

    for review in confirmed:
        if review.direction == "good":
            example_id = _next_example_id(golden_ids, GOOD_PROMOTION_ID_PREFIX)
            golden_ids.add(example_id)
            golden_dataset.examples.append(build_golden_example(review, example_id=example_id))
            good_count += 1
        else:
            example_id = _next_example_id(failure_ids, FAILURE_PROMOTION_ID_PREFIX)
            failure_ids.add(example_id)
            production_failures.examples.append(build_golden_example(review, example_id=example_id))
            failure_count += 1
        await repository.mark_synced(review.id)

    if good_count:
        golden_dataset_path.write_text(golden_dataset.model_dump_json(indent=2), encoding="utf-8")
    if failure_count:
        production_failures_path.parent.mkdir(parents=True, exist_ok=True)
        production_failures_path.write_text(
            production_failures.model_dump_json(indent=2), encoding="utf-8"
        )

    return good_count, failure_count


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--golden-dataset",
        default=GOLDEN_DATASET_PATH,
        type=Path,
        help="Path to rag_answer_gold.json.",
    )
    parser.add_argument(
        "--production-failures",
        default=PRODUCTION_FAILURES_PATH,
        type=Path,
        help="Path to production_failures.json.",
    )
    args = parser.parse_args()

    async with SessionFactory() as session:
        good_count, failure_count = await sync(
            repository=PromotionReviewRepository(session),
            golden_dataset_path=args.golden_dataset,
            production_failures_path=args.production_failures,
        )
        await session.commit()

    print(
        f"Promoted {good_count} example(s) into {args.golden_dataset}, "
        f"{failure_count} into {args.production_failures}"
    )


if __name__ == "__main__":
    asyncio.run(main())
