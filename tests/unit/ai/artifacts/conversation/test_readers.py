from __future__ import annotations

from uuid import uuid4

from app.ai.artifacts.conversation.builders import ConversationTurnArtifactBuilder
from app.ai.artifacts.conversation.readers import ConversationArtifactReader
from app.ai.artifacts.conversation.writers import ConversationArtifactWriter

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage


async def test_list_turns_returns_oldest_first(fake_storage: FakeDocumentStorage) -> None:
    writer = ConversationArtifactWriter(storage_provider=fake_storage)
    reader = ConversationArtifactReader(storage_provider=fake_storage)

    conversation_id = uuid4()
    builder = ConversationTurnArtifactBuilder()

    first = builder.build(
        conversation_id=conversation_id,
        owner_id=uuid4(),
        user_prompt="first",
        assistant_content="first reply",
    )
    await writer.write_turn(first)

    second = builder.build(
        conversation_id=conversation_id,
        owner_id=uuid4(),
        user_prompt="second",
        assistant_content="second reply",
    )
    await writer.write_turn(second)

    turns = await reader.list_turns(conversation_id)

    assert [turn.user_prompt for turn in turns] == ["first", "second"]


async def test_list_turns_empty_when_no_turns_written(
    fake_storage: FakeDocumentStorage,
) -> None:
    reader = ConversationArtifactReader(storage_provider=fake_storage)

    turns = await reader.list_turns(uuid4())

    assert turns == []
