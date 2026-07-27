from __future__ import annotations

from typing import Any, Protocol, cast

from openai import OpenAI
from openai.types.responses import ResponseInputParam, ToolParam

from app.core.config import Settings
from app.domain.schemas import AgentDraft, ModelToolCall, ModelTurn


class AgentModel(Protocol):
    @property
    def model_name(self) -> str: ...

    def complete(
        self,
        *,
        input_items: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
    ) -> ModelTurn: ...


# function to serialize a Pydantic model to a dict,
# excluding None values and removing the "parsed_arguments" field if present
def _serialize_continuation_item(item: Any) -> dict[str, Any]:

    serialized: dict[str, Any] = item.model_dump(mode="json", exclude_none=True)
    # `responses.parse` adds this Python SDK convenience field. It is not part
    # of the Responses API input schema and must never be sent back.
    serialized.pop("parsed_arguments", None)
    return serialized


# OpenAI Responses adapter with structured final output and strict tools.
class OpenAIResponsesModel:
    def __init__(self, settings: Settings) -> None:
        if settings.openai_api_key is None:
            raise ValueError("RAG_OPENAI_API_KEY is required to invoke the baseline agent")
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.model_timeout_seconds,
            max_retries=settings.model_max_retries,
        )

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
        calls: list[ModelToolCall] = []
        for item in response.output:
            if item.type == "function_call":
                calls.append(
                    ModelToolCall(
                        call_id=item.call_id,
                        name=item.name,
                        arguments_json=item.arguments,
                    )
                )
        continuation = (
            [_serialize_continuation_item(item) for item in response.output] if calls else []
        )
        usage = response.usage
        return ModelTurn(
            tool_calls=calls,
            final=response.output_parsed,
            continuation_items=continuation,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
        )
