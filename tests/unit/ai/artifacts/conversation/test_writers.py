from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.ai.artifacts.conversation.builders import ConversationTurnArtifactBuilder
from app.ai.artifacts.conversation.models import ConversationIdentity
from app.ai.artifacts.conversation.writers import ConversationArtifactWriter

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage


async def test_write_identity_persists_once(fake_storage: FakeDocumentStorage) -> None:
    writer = ConversationArtifactWriter(storage_provider=fake_storage)

    conversation_id = uuid4()
    identity = ConversationIdentity(
        conversation_id=conversation_id,
        owner_id=uuid4(),
        title=None,
        created_at=datetime.now(UTC),
    )

    await writer.write_identity(identity)

    key = f"artifacts/conversations/{conversation_id}/conversation.json"
    assert key in fake_storage.uploads


async def test_write_identity_is_a_noop_when_already_written(
    fake_storage: FakeDocumentStorage,
) -> None:
    writer = ConversationArtifactWriter(storage_provider=fake_storage)

    conversation_id = uuid4()
    identity = ConversationIdentity(
        conversation_id=conversation_id,
        owner_id=uuid4(),
        title="original",
        created_at=datetime.now(UTC),
    )

    await writer.write_identity(identity)
    key = f"artifacts/conversations/{conversation_id}/conversation.json"
    first_write = fake_storage.uploads[key]

    await writer.write_identity(
        identity.model_copy(update={"title": "changed"}),
    )

    assert fake_storage.uploads[key] == first_write


async def test_write_turn_uses_a_fresh_key_per_call(fake_storage: FakeDocumentStorage) -> None:
    writer = ConversationArtifactWriter(storage_provider=fake_storage)

    conversation_id = uuid4()
    builder = ConversationTurnArtifactBuilder()

    turn_one = builder.build(
        conversation_id=conversation_id,
        owner_id=uuid4(),
        user_prompt="hi",
        assistant_content="hello",
    )
    turn_two = builder.build(
        conversation_id=conversation_id,
        owner_id=uuid4(),
        user_prompt="hi again",
        assistant_content="hello again",
    )

    await writer.write_turn(turn_one)
    await writer.write_turn(turn_two)

    prefix = f"artifacts/conversations/{conversation_id}/turns/"
    keys = [key for key in fake_storage.uploads if key.startswith(prefix)]
    assert len(keys) == 2
