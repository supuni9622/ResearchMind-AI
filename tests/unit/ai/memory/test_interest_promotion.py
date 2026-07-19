from uuid import uuid4

from app.ai.memory.policy.interest_promotion import (
    RepeatedInterestPromotionService,
    _topic_tokens,
)


class _FakePipeline:
    def __init__(self, store: dict[str, set[str]], claims: set[str]) -> None:
        self._store = store
        self._claims = claims
        self._commands: list[tuple[str, tuple[object, ...]]] = []

    def sadd(self, key: str, member: str) -> None:
        self._commands.append(("sadd", (key, member)))

    def scard(self, key: str) -> None:
        self._commands.append(("scard", (key,)))

    def expire(self, key: str, seconds: int) -> None:
        self._commands.append(("expire", (key, seconds)))

    def set(self, key: str, value: str, *, ex: int, nx: bool) -> None:
        self._commands.append(("set", (key, value, ex, nx)))

    async def execute(self) -> list[int | bool]:
        results: list[int | bool] = []
        for command, values in self._commands:
            key = str(values[0])
            if command == "sadd":
                members = self._store.setdefault(key, set())
                member = str(values[1])
                added = member not in members
                members.add(member)
                results.append(int(added))
            elif command == "scard":
                results.append(len(self._store.get(key, set())))
            elif command == "expire":
                results.append(True)
            else:
                added = key not in self._claims
                self._claims.add(key)
                results.append(added)
        return results


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, set[str]] = {}
        self._claims: set[str] = set()

    def pipeline(self, *, transaction: bool) -> _FakePipeline:
        assert transaction is False
        return _FakePipeline(self._store, self._claims)


def test_topic_tokens_are_compact_and_ignore_generic_words() -> None:
    assert _topic_tokens("What is RAG and how can I use it for research?") == ["rag", "research"]


def test_topic_tokens_keep_an_acronym_candidate() -> None:
    assert _topic_tokens("Explain RAG") == ["explain", "rag"]


async def test_promotes_a_topic_on_the_second_session_only_once() -> None:
    redis = _FakeRedis()
    service = RepeatedInterestPromotionService(redis)  # type: ignore[arg-type]
    owner_id = uuid4()

    assert (
        await service.promoted_topics(
            owner_id=owner_id,
            session_id=uuid4(),
            user_message="What is RAG?",
        )
        == []
    )
    assert await service.promoted_topics(
        owner_id=owner_id,
        session_id=uuid4(),
        user_message="How does RAG work?",
    ) == ["rag"]
    assert (
        await service.promoted_topics(
            owner_id=owner_id,
            session_id=uuid4(),
            user_message="Can RAG cite sources?",
        )
        == []
    )
