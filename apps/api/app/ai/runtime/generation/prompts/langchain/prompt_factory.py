from __future__ import annotations

from app.ai.runtime.generation.prompts.models import (
    PromptTemplate,
)
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.prompts.chat import MessageLikeRepresentation


class PromptFactory:
    @staticmethod
    def build(
        template: PromptTemplate,
        examples: list[dict] | None = None,
    ) -> ChatPromptTemplate:

        messages: list[MessageLikeRepresentation] = []

        messages.append(
            SystemMessagePromptTemplate.from_template(
                template.template,
            )
        )

        if examples:
            example_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "human",
                        "{input}",
                    ),
                    (
                        "ai",
                        "{output}",
                    ),
                ]
            )

            messages.append(
                FewShotChatMessagePromptTemplate(
                    examples=examples,
                    example_prompt=example_prompt,
                )
            )

        messages.append(
            HumanMessagePromptTemplate.from_template(
                "{user_input}",
            )
        )

        return ChatPromptTemplate.from_messages(
            messages,
        )
