"""Tests for Phase 2 efficiency helpers: read-dedup (8e) and Anthropic caching (8d)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.copilot_orchestrator import _dedupe_read_result, _truncate_tool_result  # noqa: E402


def test_truncate_tool_result_caps_long_output():
    assert _truncate_tool_result("abc", 10) == "abc"
    out = _truncate_tool_result("x" * 100, 10)
    assert out.startswith("x" * 10)
    assert "truncated for context" in out


def test_dedupe_collapses_identical_idempotent_read():
    seen: dict[str, str] = {}
    args = {"appliance_name": "ns01"}
    payload = '{"ips": ["10.0.0.1", "10.0.0.2"]}'

    # First call: full (truncated) payload, recorded.
    first = _dedupe_read_result("netscaler_list_ip_addresses", args, payload, seen, 10_000)
    assert first == payload

    # Second identical call: collapsed to a pointer (no re-feed of the same data).
    second = _dedupe_read_result("netscaler_list_ip_addresses", args, payload, seen, 10_000)
    assert "identical to the earlier" in second
    assert "netscaler_list_ip_addresses" in second


def test_dedupe_does_not_collapse_when_result_changed():
    seen: dict[str, str] = {}
    args = {"appliance_name": "ns01"}
    _dedupe_read_result("netscaler_list_service_status", args, "DOWN: svc1", seen, 10_000)
    # Different result for the same call → must not collapse (state changed).
    out = _dedupe_read_result("netscaler_list_service_status", args, "UP: svc1", seen, 10_000)
    assert out == "UP: svc1"


def test_dedupe_only_applies_to_idempotent_reads():
    seen: dict[str, str] = {}
    args = {"appliance_name": "ns01", "commands": ["add lb vserver x"]}
    payload = '{"ok": true}'
    # A write tool is never deduped even on an exact repeat.
    first = _dedupe_read_result("netscaler_run_cli_commands", args, payload, seen, 10_000)
    second = _dedupe_read_result("netscaler_run_cli_commands", args, payload, seen, 10_000)
    assert first == payload
    assert second == payload


def test_anthropic_system_prompt_is_marked_cacheable():
    # 8d: the Anthropic payload wraps a non-empty system prompt in a cacheable content block.
    import inspect

    from app.services import copilot_service

    src = inspect.getsource(copilot_service.chat_anthropic)
    assert "cache_control" in src
    assert "ephemeral" in src
