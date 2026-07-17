from __future__ import annotations

from uuid import uuid4

from app.ai.artifacts.conversation.builders import ConversationTurnArtifactBuilder


def test_build_produces_a_fresh_turn_id_each_call() -> None:
    conversation_id = uuid4()
    owner_id = uuid4()

    builder = ConversationTurnArtifactBuilder()

    first = builder.build(
        conversation_id=conversation_id,
        owner_id=owner_id,
        user_prompt="hi",
        assistant_content="hello",
    )
    second = builder.build(
        conversation_id=conversation_id,
        owner_id=owner_id,
        user_prompt="hi again",
        assistant_content="hello again",
    )

    assert first.turn_id != second.turn_id
    assert first.metadata.conversation_id == conversation_id
    assert first.metadata.owner_id == owner_id
