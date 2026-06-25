"""Regression tests for the tool-argument error catch in the chat orchestrator.

When the model calls a write tool with a missing/misnamed required argument (e.g.
`netscaler_delete_lb` with `vs_name` instead of `name`), `execute_copilot_tool`
raises a plain `ValueError("name is required")`. v0.104 added a catch in
`_execute_tool_with_memory_gate` that turns that into a clean
`{"success": false, "error": ..., "hint": ...}` tool result the model can retry
from — instead of an unhandled exception that logs a misleading ERROR + traceback
every turn.

These tests lock that behavior in so it can't silently regress: a bad-argument call
must NOT propagate an exception, and must return a clean failure result.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import copilot_orchestrator  # noqa: E402


def _run_gate(monkeypatch_target_raises, *, name, arguments):
    """Invoke _execute_tool_with_memory_gate with execute_copilot_tool patched.

    `monkeypatch_target_raises` is the exception instance the patched
    execute_copilot_tool should raise. Gates are pre-satisfied so the call reaches
    execute_copilot_tool. Returns the (result_json, *_) tuple.
    """

    async def _fake_execute(*args, **kwargs):
        raise monkeypatch_target_raises

    original = copilot_orchestrator.execute_copilot_tool
    copilot_orchestrator.execute_copilot_tool = _fake_execute
    try:
        return asyncio.run(
            copilot_orchestrator._execute_tool_with_memory_gate(
                db=None,
                name=name,
                arguments=arguments,
                appliance_name="NetScaler",
                nextgen_memory_reviewed=True,
                cli_memory_reviewed=True,
                stack_calibration_reviewed=True,
                blueprint_relevant=False,
                role="operator",
                vendor="netscaler",
            )
        )
    finally:
        copilot_orchestrator.execute_copilot_tool = original


def test_delete_lb_missing_name_returns_clean_error_no_raise():
    """delete_lb with a misnamed arg (vs_name) must not raise — returns clean error.

    Reproduces the live signature: model called netscaler_delete_lb with
    {"vs_name": ..., "confirm": true} (no `name`). The destructive gate is bypassed by
    confirm=true, the call reaches execute_copilot_tool, which raises
    ValueError("name is required"). The gate must catch it.
    """
    result, *_ = _run_gate(
        ValueError("name is required"),
        name="netscaler_delete_lb",
        arguments={"vs_name": "o6_lb1_vs", "appliance_name": "NetScaler", "confirm": True},
    )
    payload = json.loads(result)
    assert payload["success"] is False
    assert "name is required" in payload["error"]
    assert "hint" in payload  # model is told to re-call with required args


def test_generic_value_error_is_caught_for_read_tool():
    """A ValueError from any tool (here a read) is turned into a clean result."""
    result, *_ = _run_gate(
        ValueError("query is required"),
        name="netscaler_list_virtual_servers",
        arguments={"appliance_name": "NetScaler"},
    )
    payload = json.loads(result)
    assert payload["success"] is False
    assert "query is required" in payload["error"]


def test_non_value_error_still_propagates():
    """Only ValueError (bad args) is swallowed; real bugs must still surface.

    A RuntimeError (e.g. a genuine code defect) should NOT be masked as a clean tool
    result — it should propagate so the outer loop logs it and we notice. This guards
    against the catch being widened to bare `except Exception`.
    """
    raised = False
    try:
        _run_gate(
            RuntimeError("boom"),
            name="netscaler_list_virtual_servers",
            arguments={"appliance_name": "NetScaler"},
        )
    except RuntimeError:
        raised = True
    assert raised, "RuntimeError must propagate, not be swallowed as a clean result"
