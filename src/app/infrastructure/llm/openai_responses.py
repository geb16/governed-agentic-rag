from __future__ import annotations

from typing import Any, cast

from openai import OpenAI
from openai.types.responses import ResponseInputParam, ToolParam

from app.core.config import Settings
from app.domain.schemas import AgentDraft, ModelToolCall, ModelTurn


def serialize_continuation_item(item: Any) -> dict[str, Any]:
    """Convert an SDK output item into provider-valid continuation input."""

    serialized: dict[str, Any] = item.model_dump(mode="json", exclude_none=True)
    # ``responses.parse`` adds this local convenience field. It is not accepted
    # by the Responses API when an output item is submitted as subsequent input.
    serialized.pop("parsed_arguments", None)
    return serialized


class OpenAIResponsesModel:
    """OpenAI Responses implementation of the application model gateway."""

    def __init__(self, settings: Settings, *, client: OpenAI | None = None) -> None:
        if settings.openai_api_key is None:
            raise ValueError("RAG_OPENAI_API_KEY is required to invoke the baseline agent")
        self._settings = settings
        self._client = client or OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.model_timeout_seconds,
            max_retries=settings.model_max_retries,
        )

    @property
    def model_name(self) -> str:
        return self._settings.openai_model

    def complete(
        self,
        *,
        input_items: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
    ) -> ModelTurn:
        response = self._client.responses.parse(
            model=self._settings.openai_model,
            instructions=instructions,
            input=cast(ResponseInputParam, input_items),
            tools=cast(list[ToolParam], tools),
            tool_choice="auto",
            parallel_tool_calls=False,
            max_tool_calls=1,
            max_output_tokens=self._settings.model_max_output_tokens,
            text_format=AgentDraft,
            safety_identifier=safety_identifier,
            store=False,
            timeout=self._settings.model_timeout_seconds,
        )
        calls = [
            ModelToolCall(
                call_id=item.call_id,
                name=item.name,
                arguments_json=item.arguments,
            )
            for item in response.output
            if item.type == "function_call"
        ]
        continuation = (
            [serialize_continuation_item(item) for item in response.output] if calls else []
        )
        usage = response.usage
        return ModelTurn(
            tool_calls=calls,
            final=response.output_parsed,
            continuation_items=continuation,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
        )
