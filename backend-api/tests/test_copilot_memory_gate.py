"""Tests for copilot memory review gates."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.copilot_memory_gate import (  # noqa: E402
    apply_memory_review_gates,
    block_result_for_lb_provision_backstop,
    lb_provision_backstop_blocked,
    nextgen_memory_review_required,
)


def test_list_ip_addresses_does_not_require_nextgen_memory_search():
    assert nextgen_memory_review_required("netscaler_list_ip_addresses") is False


def test_curated_inventory_reads_skip_nextgen_memory_gate():
    for tool_name in (
        "netscaler_get_system_info",
        "netscaler_list_applications",
        "netscaler_list_virtual_servers",
        "netscaler_list_virtual_ips",
        "netscaler_list_ip_addresses",
        "netscaler_list_service_status",
    ):
        assert nextgen_memory_review_required(tool_name) is False


def test_nextgen_get_is_curated_no_memory_search():
    # netscaler_nextgen_get is a read-only GET wrapper with a user-supplied path; it was
    # moved into NEXTGEN_CURATED_READ_TOOLS so it no longer forces a Next-Gen memory search.
    assert nextgen_memory_review_required("netscaler_nextgen_get") is False


def test_list_ip_addresses_allowed_without_prior_search():
    allowed, blocked = apply_memory_review_gates(
        "netscaler_list_ip_addresses",
        nextgen_memory_reviewed=False,
        cli_memory_reviewed=True,
    )
    assert allowed is True
    assert blocked is None


# ---------------------------------------------------------------------------
# §4.2 — LB-provisioning backstop tests
# ---------------------------------------------------------------------------

def test_lb_backstop_blocks_add_lb_vserver_single():
    """§4.2 — raw netscaler_run_cli_command with 'add lb vserver' is blocked."""
    assert lb_provision_backstop_blocked(
        "netscaler_run_cli_command",
        {"command": "add lb vserver o6_lb1 HTTP 192.168.100.50 80"},
    ) is True


def test_lb_backstop_blocks_add_lb_vserver_batch():
    """§4.2 — batch with 'add lb vserver' is blocked."""
    assert lb_provision_backstop_blocked(
        "netscaler_run_cli_commands",
        {
            "commands": [
                "add serviceGroup o6_sg HTTP",
                "add lb vserver o6_lb1 HTTP 192.168.100.50 80",
                "bind lb vserver o6_lb1 o6_sg",
            ]
        },
    ) is True


def test_lb_backstop_blocks_add_servicegroup():
    """§4.2 — 'add serviceGroup' is a provisioning verb and is blocked."""
    assert lb_provision_backstop_blocked(
        "netscaler_run_cli_commands",
        {"commands": ["add serviceGroup o6_sg HTTP"]},
    ) is True


def test_lb_backstop_blocks_bind_lb_vserver():
    """§4.2 — 'bind lb vserver' is a provisioning verb and is blocked."""
    assert lb_provision_backstop_blocked(
        "netscaler_run_cli_command",
        {"command": "bind lb vserver o6_lb1 o6_sg"},
    ) is True


def test_lb_backstop_does_not_block_show_lb_vserver():
    """§4.2 — read-only 'show lb vserver' must NOT be blocked."""
    assert lb_provision_backstop_blocked(
        "netscaler_run_cli_command",
        {"command": "show lb vserver o6_lb1"},
    ) is False


def test_lb_backstop_does_not_block_show_lb_vserver_batch():
    """§4.2 — batch of read-only show commands must NOT be blocked."""
    assert lb_provision_backstop_blocked(
        "netscaler_run_cli_commands",
        {"commands": ["show lb vserver", "show serviceGroup"]},
    ) is False


def test_lb_backstop_does_not_block_non_lb_write():
    """§4.2 — unrelated write commands (e.g. add ns ip) must NOT be blocked."""
    assert lb_provision_backstop_blocked(
        "netscaler_run_cli_command",
        {"command": "add ns ip 10.0.0.1 255.255.255.0 -type SNIP"},
    ) is False


def test_lb_backstop_does_not_apply_to_other_tools():
    """§4.2 — backstop only fires for the two raw CLI tools, not netscaler_create_lb etc."""
    assert lb_provision_backstop_blocked(
        "netscaler_create_lb",
        {"name": "o6_lb1", "vip": "192.168.100.50"},
    ) is False


def test_lb_backstop_block_result_has_redirect_hint():
    """§4.2 — blocked result contains the corrective redirect message."""
    import json
    result = block_result_for_lb_provision_backstop(
        "netscaler_run_cli_command",
        {"command": "add lb vserver o6_lb1 HTTP 192.168.100.50 80"},
    )
    payload = json.loads(result)
    assert payload["success"] is False
    assert payload.get("lbProvisioningBlocked") is True
    assert "netscaler_create_lb" in payload["message"]
    assert "-purpose" in payload["message"]  # the known hallucination is called out
