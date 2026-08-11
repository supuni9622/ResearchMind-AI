"""Integration tests for `EvalScoreRepository` against a real Postgres row (E5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.models.enums import EvalScoreSource
from app.models.eval_score import EvalScore
from app.models.generation_usage import GenerationUsage
from app.models.user import User
from app.repositories.eval_score import EvalScoreRepository
from sqlalchemy import select


async def _make_owner(
    session, *, email: str | None = None, username: str | None = None
) -> uuid.UUID:
    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email=email or f"{uuid.uuid4()}@example.com",
        username=username,
    )
    session.add(user)
    await session.flush()
    return user.id


@pytest.mark.asyncio
async def test_record_inserts_a_score_row(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    inserted = await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="all citation checks passed",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    row = (
        await db_session.execute(select(EvalScore).where(EvalScore.generation_id == generation_id))
    ).scalar_one()

    assert row.owner_id == owner_id
    assert row.metric_name == "citation_validity"
    assert row.score == pytest.approx(1.0)
    assert row.passed is True
    assert row.source == "online_sampled"
    assert row.sample_category == "baseline_sampled"

    # The LangSmith sync follow-up (E5) needs record()'s return value to
    # look up the inserted row's id -- confirmed here against a real
    # Postgres RETURNING, not just the mocked unit tests.
    assert inserted is not None
    assert inserted.id == row.id


@pytest.mark.asyncio
async def test_record_returns_none_when_the_insert_conflicts(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="first",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    second = await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=0.0,
        passed=False,
        reason="second, should be ignored",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )

    assert second is None


@pytest.mark.asyncio
async def test_record_allows_multiple_metrics_for_the_same_generation(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="ok",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="answer_relevancy",
        score=0.87,
        passed=True,
        reason="relevant",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    statement = select(EvalScore).where(EvalScore.generation_id == generation_id)
    rows = (await db_session.execute(statement)).scalars().all()

    assert {row.metric_name for row in rows} == {"citation_validity", "answer_relevancy"}


@pytest.mark.asyncio
async def test_record_is_a_no_op_on_conflict_for_the_same_generation_metric_source(
    db_session,
) -> None:
    """Defensive backstop against a race between two concurrent job ticks
    (`EvalScoreRepository.record()`'s own docstring) -- a second `record()`
    call for the same `(generation_id, metric_name, source)` must not
    raise, and must not overwrite the first score."""

    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="first",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=0.0,
        passed=False,
        reason="second, should be ignored",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    statement = select(EvalScore).where(EvalScore.generation_id == generation_id)
    rows = (await db_session.execute(statement)).scalars().all()

    assert len(rows) == 1
    assert rows[0].reason == "first"


@pytest.mark.asyncio
async def test_upsert_inserts_a_new_score_row(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    score = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="user_rating",
        score=1.0,
        passed=True,
        reason="great answer",
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
    )

    assert score.owner_id == owner_id
    assert score.metric_name == "user_rating"
    assert score.score == pytest.approx(1.0)
    assert score.passed is True
    assert score.source == "human_feedback"
    assert score.sample_category is None


@pytest.mark.asyncio
async def test_upsert_updates_the_existing_row_on_conflict(db_session) -> None:
    """E6: a user changing their vote (thumbs down -> thumbs up) must
    update the same mirrored row, not accumulate a second one -- matches
    `FeedbackRepository.upsert()`'s own semantics exactly."""

    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    first = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="user_rating",
        score=0.0,
        passed=False,
        reason="wrong citation",
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
    )
    second = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="user_rating",
        score=1.0,
        passed=True,
        reason=None,
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
    )

    assert first.id == second.id
    assert second.score == pytest.approx(1.0)
    assert second.passed is True
    assert second.reason is None

    statement = select(EvalScore).where(EvalScore.generation_id == generation_id)
    rows = (await db_session.execute(statement)).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_upsert_and_record_coexist_for_the_same_generation_under_different_sources(
    db_session,
) -> None:
    """A human-feedback mirror (`upsert`) and an online-scoring free check
    (`record`) for the *same* generation must both survive -- the unique
    constraint is scoped to `(generation_id, metric_name, source)`, and
    `metric_name` differs here (`user_rating` vs `citation_validity`), so
    this also covers the same-metric-different-source case implicitly via
    the constraint's third column."""

    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="ok",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="user_rating",
        score=1.0,
        passed=True,
        reason="nice",
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
    )
    await db_session.flush()

    statement = select(EvalScore).where(EvalScore.generation_id == generation_id)
    rows = (await db_session.execute(statement)).scalars().all()

    assert {(row.metric_name, row.source) for row in rows} == {
        ("citation_validity", "online_sampled"),
        ("user_rating", "human_feedback"),
    }


@pytest.mark.asyncio
async def test_record_offline_example_inserts_a_row_with_no_owner_or_generation(
    db_session,
) -> None:
    """E6: an offline-benchmark row scores a fixed golden-dataset example,
    not a live production generation -- owner_id/generation_id must both
    be persistable as NULL (the check constraint requires only that
    dataset_example_id is set instead)."""

    repository = EvalScoreRepository(db_session)
    await repository.record_offline_example(
        dataset_example_id="a1",
        metric_name="faithfulness",
        score=0.9,
        passed=True,
        reason="grounded in context",
    )
    await db_session.flush()

    row = (
        await db_session.execute(select(EvalScore).where(EvalScore.dataset_example_id == "a1"))
    ).scalar_one()

    assert row.owner_id is None
    assert row.generation_id is None
    assert row.metric_name == "faithfulness"
    assert row.score == pytest.approx(0.9)
    assert row.source == "offline_benchmark"
    assert row.sample_category is None


@pytest.mark.asyncio
async def test_record_offline_example_is_append_only_across_repeated_runs(db_session) -> None:
    """Unlike record()/upsert(), a second offline score for the same
    example+metric must produce a SECOND row, not overwrite the first --
    each benchmark run is a distinct trend data point for E9's future
    segment-analysis, not a replacement of the last one."""

    repository = EvalScoreRepository(db_session)
    await repository.record_offline_example(
        dataset_example_id="a1",
        metric_name="faithfulness",
        score=0.9,
        passed=True,
        reason="run 1",
    )
    await repository.record_offline_example(
        dataset_example_id="a1",
        metric_name="faithfulness",
        score=0.7,
        passed=True,
        reason="run 2 -- regressed slightly",
    )
    await db_session.flush()

    rows = (
        (await db_session.execute(select(EvalScore).where(EvalScore.dataset_example_id == "a1")))
        .scalars()
        .all()
    )

    assert len(rows) == 2
    assert {row.reason for row in rows} == {"run 1", "run 2 -- regressed slightly"}


@pytest.mark.asyncio
async def test_list_for_owner_page_returns_only_that_owners_rows_newest_first(
    db_session,
) -> None:
    """Rows are built directly with explicit, distinct `created_at`
    values rather than via `record()` -- Postgres's `now()` returns the
    *transaction* start time, constant for every statement in the test
    fixture's single wrapping transaction, so two `record()` calls in a
    row would otherwise tie on `created_at` and make "newest first"
    unverifiable."""

    owner_id = await _make_owner(db_session)
    other_owner_id = await _make_owner(db_session)

    older = datetime(2026, 1, 1, tzinfo=UTC)
    newer = datetime(2026, 1, 2, tzinfo=UTC)
    db_session.add_all(
        [
            EvalScore(
                owner_id=owner_id,
                generation_id=uuid.uuid4(),
                metric_name="citation_validity",
                score=1.0,
                passed=True,
                reason="first",
                source=EvalScoreSource.ONLINE_SAMPLED.value,
                created_at=older,
            ),
            EvalScore(
                owner_id=owner_id,
                generation_id=uuid.uuid4(),
                metric_name="answer_relevancy",
                score=0.5,
                passed=False,
                reason="second",
                source=EvalScoreSource.ONLINE_SAMPLED.value,
                created_at=newer,
            ),
            EvalScore(
                owner_id=other_owner_id,
                generation_id=uuid.uuid4(),
                metric_name="citation_validity",
                score=1.0,
                passed=True,
                reason="other owner's row",
                source=EvalScoreSource.ONLINE_SAMPLED.value,
                created_at=newer,
            ),
        ]
    )
    await db_session.flush()

    repository = EvalScoreRepository(db_session)
    rows, total = await repository.list_for_owner_page(owner_id, limit=10, offset=0)

    assert total == 2
    assert [row.reason for row in rows] == ["second", "first"]


@pytest.mark.asyncio
async def test_list_for_owner_page_filters_by_metric_and_source(db_session) -> None:
    owner_id = await _make_owner(db_session)

    repository = EvalScoreRepository(db_session)
    await repository.record(
        owner_id=owner_id,
        generation_id=uuid.uuid4(),
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="automated",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await repository.upsert(
        owner_id=owner_id,
        generation_id=uuid.uuid4(),
        metric_name="user_rating",
        score=1.0,
        passed=True,
        reason="thumbs up",
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
    )
    await db_session.flush()

    rows, total = await repository.list_for_owner_page(
        owner_id,
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
        limit=10,
        offset=0,
    )

    assert total == 1
    assert rows[0].reason == "thumbs up"


@pytest.mark.asyncio
async def test_search_owners_with_scores_matches_email_and_orders_by_row_count(
    db_session,
) -> None:
    frequent_owner = await _make_owner(db_session, email="frequent@example.com")
    rare_owner = await _make_owner(db_session, email="rare@example.com")
    no_scores_owner = await _make_owner(db_session, email="unrelated@example.com")
    assert no_scores_owner  # created only to prove it's excluded below

    repository = EvalScoreRepository(db_session)
    for i in range(2):
        await repository.record(
            owner_id=frequent_owner,
            generation_id=uuid.uuid4(),
            metric_name="citation_validity",
            score=1.0,
            passed=True,
            reason=f"row {i}",
            source=EvalScoreSource.ONLINE_SAMPLED.value,
            sample_category="baseline_sampled",
        )
    await repository.record(
        owner_id=rare_owner,
        generation_id=uuid.uuid4(),
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="only row",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    rows, total = await repository.search_owners_with_scores(limit=10, offset=0)

    matched = {user.id: count for user, count in rows}
    assert total == 2
    assert matched[frequent_owner] == 2
    assert matched[rare_owner] == 1
    assert no_scores_owner not in matched
    # Most rows first.
    assert rows[0][0].id == frequent_owner


@pytest.mark.asyncio
async def test_search_owners_with_scores_filters_by_search_term(db_session) -> None:
    matching_owner = await _make_owner(db_session, email="findme@example.com")
    other_owner = await _make_owner(db_session, email="somebody-else@example.com")

    repository = EvalScoreRepository(db_session)
    for owner_id in (matching_owner, other_owner):
        await repository.record(
            owner_id=owner_id,
            generation_id=uuid.uuid4(),
            metric_name="citation_validity",
            score=1.0,
            passed=True,
            reason="row",
            source=EvalScoreSource.ONLINE_SAMPLED.value,
            sample_category="baseline_sampled",
        )
    await db_session.flush()

    rows, total = await repository.search_owners_with_scores(
        search="findme",
        limit=10,
        offset=0,
    )

    assert total == 1
    assert rows[0][0].id == matching_owner


@pytest.mark.asyncio
async def test_list_offline_page_excludes_online_and_human_feedback_rows(db_session) -> None:
    """The gap that motivated this method: filtering `list_for_owner_page()`
    by source=offline_benchmark can never work (offline rows have no
    owner_id), so this is a separate, non-owner-scoped read path."""

    owner_id = await _make_owner(db_session)
    repository = EvalScoreRepository(db_session)
    await repository.record(
        owner_id=owner_id,
        generation_id=uuid.uuid4(),
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="online row",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await repository.record_offline_example(
        dataset_example_id="g14",
        metric_name="faithfulness",
        score=0.9,
        passed=True,
        reason="offline row",
    )
    await db_session.flush()

    rows, total = await repository.list_offline_page(limit=10, offset=0)

    assert total == 1
    assert rows[0].reason == "offline row"
    assert rows[0].owner_id is None


@pytest.mark.asyncio
async def test_list_offline_page_filters_by_dataset_example_id_and_metric(db_session) -> None:
    repository = EvalScoreRepository(db_session)
    await repository.record_offline_example(
        dataset_example_id="g14",
        metric_name="faithfulness",
        score=0.9,
        passed=True,
        reason="g14 faithfulness",
    )
    await repository.record_offline_example(
        dataset_example_id="g14",
        metric_name="answer_relevancy",
        score=0.8,
        passed=True,
        reason="g14 relevancy",
    )
    await repository.record_offline_example(
        dataset_example_id="g15",
        metric_name="faithfulness",
        score=0.7,
        passed=True,
        reason="g15 faithfulness",
    )
    await db_session.flush()

    rows, total = await repository.list_offline_page(
        dataset_example_id="g14",
        metric_name="faithfulness",
        limit=10,
        offset=0,
    )

    assert total == 1
    assert rows[0].reason == "g14 faithfulness"


@pytest.mark.asyncio
async def test_list_offline_page_is_append_only_across_runs_newest_first(db_session) -> None:
    repository = EvalScoreRepository(db_session)
    older = datetime(2026, 1, 1, tzinfo=UTC)
    newer = datetime(2026, 1, 2, tzinfo=UTC)
    db_session.add_all(
        [
            EvalScore(
                dataset_example_id="g14",
                metric_name="faithfulness",
                score=0.7,
                passed=True,
                reason="run 1",
                source=EvalScoreSource.OFFLINE_BENCHMARK.value,
                created_at=older,
            ),
            EvalScore(
                dataset_example_id="g14",
                metric_name="faithfulness",
                score=0.9,
                passed=True,
                reason="run 2",
                source=EvalScoreSource.OFFLINE_BENCHMARK.value,
                created_at=newer,
            ),
        ]
    )
    await db_session.flush()

    rows, total = await repository.list_offline_page(dataset_example_id="g14", limit=10, offset=0)

    assert total == 2
    assert [row.reason for row in rows] == ["run 2", "run 1"]


@pytest.mark.asyncio
async def test_search_offline_examples_groups_by_example_with_counts(db_session) -> None:
    repository = EvalScoreRepository(db_session)
    await repository.record_offline_example(
        dataset_example_id="g14",
        metric_name="faithfulness",
        score=0.9,
        passed=True,
        reason="a",
    )
    await repository.record_offline_example(
        dataset_example_id="g14",
        metric_name="answer_relevancy",
        score=0.8,
        passed=True,
        reason="b",
    )
    await repository.record_offline_example(
        dataset_example_id="g15",
        metric_name="faithfulness",
        score=0.7,
        passed=True,
        reason="c",
    )
    await db_session.flush()

    rows, total = await repository.search_offline_examples(limit=10, offset=0)

    counts = {example_id: count for example_id, count, _ in rows}
    assert total == 2
    assert counts == {"g14": 2, "g15": 1}


@pytest.mark.asyncio
async def test_search_offline_examples_filters_by_search_term(db_session) -> None:
    repository = EvalScoreRepository(db_session)
    await repository.record_offline_example(
        dataset_example_id="findme-example",
        metric_name="faithfulness",
        score=0.9,
        passed=True,
        reason="a",
    )
    await repository.record_offline_example(
        dataset_example_id="other-example",
        metric_name="faithfulness",
        score=0.9,
        passed=True,
        reason="b",
    )
    await db_session.flush()

    rows, total = await repository.search_offline_examples(search="findme", limit=10, offset=0)

    assert total == 1
    assert rows[0][0] == "findme-example"


# -- aggregate_online_by_fingerprint (E9) ---------------------------------


async def _make_usage(
    session, *, owner_id: uuid.UUID, prompt_version: str, generation_id: uuid.UUID | None = None
) -> uuid.UUID:
    generation_id = generation_id or uuid.uuid4()
    usage = GenerationUsage(
        request_id=uuid.uuid4(),
        generation_id=generation_id,
        owner_id=owner_id,
        provider="groq",
        model="test-model",
        surface="chat",
        prompt_version=prompt_version,
        chunking_strategy="markdown",
        embedding_model="voyage-3-lite",
        reranker="voyage_ai",
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
        estimated_cost_usd=0.001,
    )
    session.add(usage)
    await session.flush()
    return generation_id


@pytest.mark.asyncio
async def test_aggregate_online_by_fingerprint_groups_by_prompt_version(db_session) -> None:
    owner_id = await _make_owner(db_session)
    repository = EvalScoreRepository(db_session)

    v1_a = await _make_usage(db_session, owner_id=owner_id, prompt_version="chat-v1")
    v1_b = await _make_usage(db_session, owner_id=owner_id, prompt_version="chat-v1")
    v2_a = await _make_usage(db_session, owner_id=owner_id, prompt_version="chat-v2")

    for generation_id, score, passed in [(v1_a, 0.9, True), (v1_b, 0.7, True), (v2_a, 0.3, False)]:
        await repository.record(
            owner_id=owner_id,
            generation_id=generation_id,
            metric_name="faithfulness",
            score=score,
            passed=passed,
            reason="r",
            source=EvalScoreSource.ONLINE_SAMPLED.value,
            sample_category="baseline_sampled",
        )
    await db_session.flush()

    rows = await repository.aggregate_online_by_fingerprint(
        metric_name="faithfulness", fingerprint_field="prompt_version"
    )
    by_value = {value: (count, avg_score, pass_rate) for value, count, avg_score, pass_rate in rows}

    assert by_value["chat-v1"][0] == 2
    assert by_value["chat-v1"][1] == pytest.approx(0.8)
    assert by_value["chat-v1"][2] == pytest.approx(1.0)
    assert by_value["chat-v2"][0] == 1
    assert by_value["chat-v2"][1] == pytest.approx(0.3)
    assert by_value["chat-v2"][2] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_aggregate_online_by_fingerprint_ignores_offline_rows(db_session) -> None:
    repository = EvalScoreRepository(db_session)
    await repository.record_offline_example(
        dataset_example_id="g1",
        metric_name="faithfulness",
        score=0.5,
        passed=True,
        reason="offline row, should never join to generation_usage",
    )
    await db_session.flush()

    rows = await repository.aggregate_online_by_fingerprint(
        metric_name="faithfulness", fingerprint_field="prompt_version"
    )

    assert rows == []


# -- list_offline_scores_for_metric (E9) ----------------------------------


@pytest.mark.asyncio
async def test_list_offline_scores_for_metric_excludes_online_rows(db_session) -> None:
    owner_id = await _make_owner(db_session)
    repository = EvalScoreRepository(db_session)

    await repository.record_offline_example(
        dataset_example_id="g1",
        metric_name="faithfulness",
        score=0.8,
        passed=True,
        reason="offline",
    )
    await repository.record(
        owner_id=owner_id,
        generation_id=uuid.uuid4(),
        metric_name="faithfulness",
        score=0.6,
        passed=True,
        reason="online",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    rows = await repository.list_offline_scores_for_metric(metric_name="faithfulness")

    assert len(rows) == 1
    assert rows[0].dataset_example_id == "g1"
