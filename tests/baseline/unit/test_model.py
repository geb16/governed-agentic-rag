from typing import Any

from app.infrastructure.llm.openai_responses import serialize_continuation_item


class ParsedFunctionCallDouble:
    def model_dump(self, **_: Any) -> dict[str, Any]:
        return {
            "type": "function_call",
            "call_id": "call_1",
            "name": "ticket_lookup",
            "arguments": '{"ticket_id":"TKT-1001"}',
            "parsed_arguments": {"ticket_id": "TKT-1001"},
        }


def test_parsed_sdk_only_fields_are_not_sent_back_to_responses_api() -> None:
    serialized = serialize_continuation_item(ParsedFunctionCallDouble())

    assert serialized == {
        "type": "function_call",
        "call_id": "call_1",
        "name": "ticket_lookup",
        "arguments": '{"ticket_id":"TKT-1001"}',
    }
