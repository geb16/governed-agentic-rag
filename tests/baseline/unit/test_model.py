"""Provider-adapter serialization regression tests."""

from typing import Any

from app.infrastructure.llm.openai_responses import serialize_continuation_item


class ParsedFunctionCallDouble:
    """Represent an SDK item containing a local-only parsed-arguments field."""

    def model_dump(self, **_: Any) -> dict[str, Any]:
        """Return the provider item plus the SDK-only convenience field."""
        return {
            "type": "function_call",
            "call_id": "call_1",
            "name": "ticket_lookup",
            "arguments": '{"ticket_id":"TKT-1001"}',
            "parsed_arguments": {"ticket_id": "TKT-1001"},
        }


def test_parsed_sdk_only_fields_are_not_sent_back_to_responses_api() -> None:
    """Remove SDK-only parsed arguments before replaying continuation input."""
    serialized = serialize_continuation_item(ParsedFunctionCallDouble())

    assert serialized == {
        "type": "function_call",
        "call_id": "call_1",
        "name": "ticket_lookup",
        "arguments": '{"ticket_id":"TKT-1001"}',
    }
