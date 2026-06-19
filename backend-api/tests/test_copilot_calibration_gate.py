"""Tests for blueprint-first calibration gate."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.copilot_calibration_gate import (  # noqa: E402
    apply_blueprint_review_gate,
    apply_tool_review_gates,
    blueprint_action_review_required,
)


def test_blueprint_gate_blocks_cli_before_blueprint_review():
    allowed, blocked = apply_blueprint_review_gate(
        "netscaler_run_cli_command",
        blueprint_relevant=True,
        stack_calibration_reviewed=False,
    )
    assert allowed is False
    assert blocked is not None
    assert "search_stack_calibration_memory" in blocked


def test_blueprint_gate_allows_after_review():
    allowed, blocked = apply_blueprint_review_gate(
        "netscaler_run_cli_command",
        blueprint_relevant=True,
        stack_calibration_reviewed=True,
    )
    assert allowed is True
    assert blocked is None


def test_blueprint_gate_exempts_catalog_and_blueprint_search():
    for tool_name in ("search_stack_calibration_memory", "list_official_blueprint_catalog"):
        assert blueprint_action_review_required(tool_name) is False


def test_tool_gates_apply_blueprint_before_cli_memory():
    allowed, blocked = apply_tool_review_gates(
        "search_netscaler_cli_reference",
        blueprint_relevant=True,
        stack_calibration_reviewed=False,
        nextgen_memory_reviewed=True,
        cli_memory_reviewed=True,
    )
    assert allowed is False
    assert "blueprint" in (blocked or "").lower()
