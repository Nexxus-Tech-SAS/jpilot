"""Blueprint-first gate: consult installed stack calibration skills before vendor tools."""

from __future__ import annotations

import json
from typing import Any

from app.services.copilot_memory_gate import (
    CISCO_CLI_MEMORY_SEARCH_TOOL,
    CLI_MEMORY_SEARCH_TOOL,
    F5_CLI_MEMORY_SEARCH_TOOL,
    MEMORY_SEARCH_TOOL,
    SDX_CLI_MEMORY_SEARCH_TOOL,
    cli_memory_review_required,
    nextgen_memory_review_required,
)

STACK_CALIBRATION_MEMORY_TOOL = "search_stack_calibration_memory"
BLUEPRINT_CATALOG_TOOL = "list_official_blueprint_catalog"

BLUEPRINT_GATE_EXEMPT_TOOLS = frozenset(
    {
        STACK_CALIBRATION_MEMORY_TOOL,
        BLUEPRINT_CATALOG_TOOL,
        "jpilot_check_doc_connectivity",
        "netscaler_test_connection",
        "cisco_test_connection",
        "sdx_test_connection",
        "f5_test_connection",
        "netscaler_list_inventory",
        "search_jpilot_architect_resources",
        "search_f5_documentation",
    }
)


def blueprint_action_review_required(tool_name: str) -> bool:
    """True when this tool should wait until installed blueprint context is loaded."""
    if tool_name in BLUEPRINT_GATE_EXEMPT_TOOLS:
        return False
    if tool_name in {
        MEMORY_SEARCH_TOOL,
        CLI_MEMORY_SEARCH_TOOL,
        CISCO_CLI_MEMORY_SEARCH_TOOL,
        SDX_CLI_MEMORY_SEARCH_TOOL,
        F5_CLI_MEMORY_SEARCH_TOOL,
    }:
        return True
    if nextgen_memory_review_required(tool_name):
        return True
    if cli_memory_review_required(tool_name):
        return True
    return False


def block_result_for_missing_blueprint_review(tool_name: str) -> str:
    return json.dumps(
        {
            "success": False,
            "blocked": True,
            "message": (
                f"Tool '{tool_name}' blocked: this request matches an installed stack calibration "
                "blueprint. Read the injected blueprint guidance (or call "
                f"{STACK_CALIBRATION_MEMORY_TOOL}) before using generic CLI/API tools."
            ),
            "requiredAction": (
                f"Follow the matched blueprint playbook, or call {STACK_CALIBRATION_MEMORY_TOOL} "
                "with the user's question, then retry."
            ),
        },
        indent=2,
    )


def apply_blueprint_review_gate(
    tool_name: str,
    *,
    blueprint_relevant: bool,
    stack_calibration_reviewed: bool,
) -> tuple[bool, str | None]:
    if blueprint_relevant and not stack_calibration_reviewed and blueprint_action_review_required(tool_name):
        return False, block_result_for_missing_blueprint_review(tool_name)
    return True, None


def apply_tool_review_gates(
    tool_name: str,
    *,
    blueprint_relevant: bool,
    stack_calibration_reviewed: bool,
    nextgen_memory_reviewed: bool,
    cli_memory_reviewed: bool,
) -> tuple[bool, str | None]:
    allowed, blocked = apply_blueprint_review_gate(
        tool_name,
        blueprint_relevant=blueprint_relevant,
        stack_calibration_reviewed=stack_calibration_reviewed,
    )
    if not allowed:
        return allowed, blocked

    from app.services.copilot_memory_gate import apply_memory_review_gates

    return apply_memory_review_gates(tool_name, nextgen_memory_reviewed, cli_memory_reviewed)
