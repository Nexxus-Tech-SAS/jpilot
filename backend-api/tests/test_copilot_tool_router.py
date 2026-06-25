"""Tests for intent-based copilot tool routing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.copilot_tool_router import (  # noqa: E402
    classify_tool_packs,
    pack_tool_names,
    route_copilot_tools,
)


def _tools(*names: str) -> list[dict]:
    return [{"name": name, "description": name, "parameters": {"type": "object", "properties": {}}} for name in names]


ALL_OPERATOR = _tools(
    "netscaler_get_system_info",
    "netscaler_list_virtual_servers",
    "netscaler_list_ip_addresses",
    "netscaler_run_diagnostic",
    "netscaler_telnet",
    "netscaler_run_cli_command",
    "netscaler_run_cli_commands",
    "search_netscaler_cli_reference",
    "search_netscaler_nextgen_api",
    "netscaler_create_application",
    "jpilot_check_doc_connectivity",
)

# Richer operator set that includes the dedicated LB tool (as a real deployment would).
ALL_OPERATOR_WITH_LB = _tools(
    "netscaler_get_system_info",
    "netscaler_list_virtual_servers",
    "netscaler_list_ip_addresses",
    "netscaler_run_diagnostic",
    "netscaler_telnet",
    "netscaler_run_cli_command",
    "netscaler_run_cli_commands",
    "search_netscaler_cli_reference",
    "search_netscaler_nextgen_api",
    "netscaler_create_application",
    "netscaler_create_lb",
    "netscaler_modify_lb",
    "netscaler_delete_lb",
    "jpilot_check_doc_connectivity",
)

# Hidden dry_run plan marker as embedded by the orchestrator after a create_lb dry_run.
_LB_PLAN_MARKER = "<!-- jpilot-plan: eyJ0b29sIjogIm5ldHNjYWxlcl9jcmVhdGVfbGIiLCAiYXJncyI6IHsibmFtZSI6ICJ0ZXN0X2xiIiwgImNvbmZpcm0iOiB0cnVlfX0= -->"


def test_ping_routes_diagnostic_not_cli_write():
    packs = classify_tool_packs("Can the appliance ping 10.0.0.1?", role="operator")
    names = pack_tool_names(packs)
    assert "netscaler_run_diagnostic" in names
    assert "netscaler_run_cli_commands" not in names

    routed = route_copilot_tools(ALL_OPERATOR, role="operator", user_message="ping 10.0.0.1")
    routed_names = {t["name"] for t in routed}
    assert "netscaler_run_diagnostic" in routed_names
    assert "netscaler_run_cli_commands" not in routed_names


def test_create_lb_intent_routes_to_dedicated_tool_not_raw_cli():
    """§4.1 — LB create intent uses dedicated lb_config pack; raw CLI is absent."""
    routed = route_copilot_tools(
        ALL_OPERATOR_WITH_LB,
        role="operator",
        user_message="Create an HTTP load balancer o6_lb1 on VIP 192.168.100.50 port 80 with backends 192.168.100.61 and 192.168.100.62",
    )
    routed_names = {t["name"] for t in routed}
    assert "netscaler_create_lb" in routed_names
    assert "netscaler_run_cli_command" not in routed_names
    assert "netscaler_run_cli_commands" not in routed_names


def test_lb_confirm_turn_with_prior_plan_strips_raw_cli():
    """§4.1 — Affirmation turn with a prior dry_run plan marker must not expose raw CLI."""
    history = [
        {"role": "user", "content": "Create an HTTP load balancer o6_lb1 on VIP 192.168.100.50"},
        {"role": "assistant", "content": f"Here is the plan:\n- add lb vserver...\n{_LB_PLAN_MARKER}"},
    ]
    for affirmation in ("yes", "yes apply it", "go ahead", "confirm", "apply it"):
        routed = route_copilot_tools(
            ALL_OPERATOR_WITH_LB,
            role="operator",
            user_message=affirmation,
            history=history,
        )
        routed_names = {t["name"] for t in routed}
        assert "netscaler_run_cli_command" not in routed_names, (
            f"affirmation '{affirmation}': netscaler_run_cli_command should be absent"
        )
        assert "netscaler_run_cli_commands" not in routed_names, (
            f"affirmation '{affirmation}': netscaler_run_cli_commands should be absent"
        )
        # Dedicated LB tool must still be available
        assert "netscaler_create_lb" in routed_names, (
            f"affirmation '{affirmation}': netscaler_create_lb must be present"
        )


def test_affirmation_without_prior_lb_plan_keeps_full_tool_set():
    """§4.1 over-strip guard: affirmation with NO prior LB plan returns full set (including raw CLI)."""
    history = [
        {"role": "user", "content": "show me the service status"},
        {"role": "assistant", "content": "Here is the service status..."},
    ]
    routed = route_copilot_tools(
        ALL_OPERATOR_WITH_LB,
        role="operator",
        user_message="yes",
        history=history,
    )
    routed_names = {t["name"] for t in routed}
    # No plan marker in history → full tool set returned → raw CLI present
    assert "netscaler_run_cli_command" in routed_names


def test_add_lb_intent_routes_lb_config_not_raw_cli():
    """§4.1 — 'add lb vserver' phrasing now routes to lb_config (dedicated) not raw CLI.

    This test replaces the former test_add_lb_routes_cli_write_pack which expected
    raw CLI to be returned for 'add lb vserver' messages.  Since the O6 reconciliation,
    lb_config (netscaler_create_lb) is the single LB executor and raw CLI is stripped.
    """
    routed = route_copilot_tools(
        ALL_OPERATOR_WITH_LB,
        role="operator",
        user_message="add lb vserver web_example HTTP 10.0.0.50 80",
    )
    routed_names = {t["name"] for t in routed}
    # lb_config pack selected: dedicated tool present, raw CLI absent
    assert "netscaler_create_lb" in routed_names
    assert "netscaler_run_cli_commands" not in routed_names
    assert "netscaler_run_cli_command" not in routed_names


def test_show_vserver_routes_read_only():
    routed = route_copilot_tools(
        ALL_OPERATOR,
        role="operator",
        user_message="show lb vserver",
    )
    routed_names = {t["name"] for t in routed}
    assert "netscaler_list_virtual_servers" in routed_names or "netscaler_run_cli_command" in routed_names
    assert "netscaler_run_cli_commands" not in routed_names


def test_appliance_internet_routes_diagnostic_not_doc_check():
    packs = classify_tool_packs("does the netscaler have internet access?", role="operator")
    names = pack_tool_names(packs)
    assert "netscaler_run_diagnostic" in names
    assert "jpilot_check_doc_connectivity" not in names

    routed = route_copilot_tools(
        ALL_OPERATOR,
        role="operator",
        user_message="does the netscaler have internet access?",
    )
    routed_names = {t["name"] for t in routed}
    assert "netscaler_run_diagnostic" in routed_names
    assert "jpilot_check_doc_connectivity" not in routed_names


def test_jpilot_doc_internet_routes_doc_check():
    packs = classify_tool_packs("can you reach the documentation site?", role="operator")
    names = pack_tool_names(packs)
    assert "jpilot_check_doc_connectivity" in names


def test_list_all_ip_addresses_routes_list_ip_tool():
    routed = route_copilot_tools(
        ALL_OPERATOR,
        role="operator",
        user_message=(
            "List all IP addresses on the connected appliance with their types "
            "(NSIP, SNIP, VIP, etc.)."
        ),
    )
    routed_names = {t["name"] for t in routed}
    assert routed_names == {"netscaler_get_system_info", "netscaler_list_ip_addresses"}


def test_ambiguous_short_message_uses_full_tool_set():
    routed = route_copilot_tools(ALL_OPERATOR, role="operator", user_message="ok")
    assert len(routed) == len(ALL_OPERATOR)


def test_architect_design_adds_architect_search():
    tools = _tools(
        "netscaler_list_inventory",
        "search_netscaler_cli_reference",
        "search_netscaler_nextgen_api",
        "search_jpilot_architect_resources",
        "jpilot_check_doc_connectivity",
    )
    routed = route_copilot_tools(
        tools,
        role="architect",
        user_message="Generate the design document now",
    )
    routed_names = {t["name"] for t in routed}
    assert "search_jpilot_architect_resources" in routed_names


def test_architect_form_submission_excludes_search_tools():
    tools = _tools(
        "netscaler_list_inventory",
        "search_netscaler_cli_reference",
        "search_jpilot_architect_resources",
        "netscaler_run_cli_commands",
    )
    routed = route_copilot_tools(
        tools,
        role="architect",
        user_message="Planning inputs for: Network model\n- topology: one_arm",
    )
    assert routed == []


def test_architect_vlan_form_does_not_enable_cli_write():
    tools = _tools(
        "netscaler_list_inventory",
        "search_netscaler_cli_reference",
        "netscaler_run_cli_commands",
    )
    routed = route_copilot_tools(
        tools,
        role="architect",
        user_message="Planning inputs for: VIP\n- Client-facing VLAN: 100\n- VIP: 192.168.20.55",
    )
    assert routed == []
