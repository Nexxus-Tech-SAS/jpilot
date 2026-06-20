from app.services.copilot_retry import build_tool_retry_hint


def test_build_tool_retry_hint_jpilot_form_tool_name():
    hint = build_tool_retry_hint("jpilot-form", "Tool blocked", "Planning inputs for: Topology")
    assert hint is not None
    assert "NOT an MCP tool" in hint


def test_build_tool_retry_hint_jpilot_form_unavailable_message():
    hint = build_tool_retry_hint(
        "search_jpilot_architect_resources",
        "Tool 'jpilot-form' is not available in architect role",
        "hello",
    )
    assert hint is not None
    assert "NOT an MCP tool" in hint
