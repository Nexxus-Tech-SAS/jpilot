"""
Appliance-free pytest suite for NetScaler write/inspect tool functions.

Strategy:
- Dry-run / confirm=False paths return a preview dict WITHOUT hitting any appliance.
- Validation/input-sanitisation paths raise ValueError before any network call.
- get_logs and search_config happy-paths are tested with unittest.mock.patch so no
  SSH connection is attempted.
- All async functions are called via asyncio.run() — no pytest-asyncio needed.
"""

import asyncio
import sys
import types
import unittest.mock as mock

# Make sure /app is on the path when running inside the container
sys.path.insert(0, "/app")

from app.services.netscaler_service import (
    _ALLOWED_LOG_FILES,
    _KEYWORD_SAFE_RE,
    _detect_ha_configured,
    create_cs,
    create_lb,
    create_responder,
    create_rewrite,
    delete_cs,
    delete_lb,
    delete_responder,
    delete_rewrite,
    get_logs,
    search_config,
)

# ---------------------------------------------------------------------------
# Fake credentials — never actually used (dry_run or confirm=False prevents
# any network call from being made).
# ---------------------------------------------------------------------------
H, U, P = "fake-host", "admin", "secret"


# ===========================================================================
# 1. create_lb — dry_run gate
# ===========================================================================

def test_create_lb_dry_run_returns_preview():
    """dry_run=True must return dryRun:True, commands list, no 'applied'."""
    result = asyncio.run(
        create_lb(H, U, P, "my_lb", "10.0.0.1", ["192.168.1.1", "192.168.1.2"],
                  lb_method="ROUNDROBIN", dry_run=True)
    )
    assert result.get("dryRun") is True
    assert isinstance(result.get("commands"), list)
    assert len(result["commands"]) > 0
    assert result.get("applied") is not True


def test_create_lb_dry_run_command_order():
    """Commands appear in the correct order and contain the expected substrings."""
    result = asyncio.run(
        create_lb(H, U, P, "my_lb", "10.0.0.1", ["192.168.1.1"],
                  service_type="HTTP", port=80, lb_method="ROUNDROBIN", dry_run=True)
    )
    cmds = result["commands"]

    # enable LB must be first
    assert cmds[0] == "enable ns feature LB"

    # one service group, members bound by IP (no per-backend named server)
    assert any(c.startswith("add serviceGroup my_lb_sg HTTP") for c in cmds)
    assert any(c.startswith("bind serviceGroup my_lb_sg 192.168.1.1 80") for c in cmds)
    assert not any(c.startswith("add server ") for c in cmds)

    # add lb vserver
    assert any("add lb vserver my_lb HTTP 10.0.0.1 80" in c for c in cmds)

    # bind the service group to the lb vserver
    assert any(c.startswith("bind lb vserver my_lb my_lb_sg") for c in cmds)

    # set lb vserver lbMethod
    set_cmd = next((c for c in cmds if c.startswith("set lb vserver my_lb")), None)
    assert set_cmd is not None
    assert "-lbMethod ROUNDROBIN" in set_cmd


def test_create_lb_confirm_false_also_previews():
    """confirm=False (default) must also return a preview without executing."""
    result = asyncio.run(
        create_lb(H, U, P, "vip1", "10.1.2.3", ["10.0.0.5"])
        # dry_run defaults to False, confirm defaults to False → still preview
    )
    assert result.get("dryRun") is True
    assert "commands" in result


def test_create_lb_monitor_binds_to_service_group():
    """When monitor is provided, it binds once to the service group (not per service)."""
    result = asyncio.run(
        create_lb(H, U, P, "my_lb", "10.0.0.1", ["192.168.1.1", "192.168.1.2"],
                  monitor="tcp-default", dry_run=True)
    )
    cmds = result["commands"]

    # Monitor binds exactly once, to the service group
    bind_mon_cmds = [c for c in cmds if "-monitorName tcp-default" in c]
    assert len(bind_mon_cmds) == 1, f"Expected 1 monitor bind, got {len(bind_mon_cmds)}: {cmds}"
    assert "bind serviceGroup my_lb_sg -monitorName tcp-default" in bind_mon_cmds[0]

    # both backends are bound (by IP) as members of the same service group
    assert any("bind serviceGroup my_lb_sg 192.168.1.1 80" in c for c in cmds)
    assert any("bind serviceGroup my_lb_sg 192.168.1.2 80" in c for c in cmds)

    # the monitor bind must come after the service group is created
    sg_idx = next(j for j, c in enumerate(cmds) if c.startswith("add serviceGroup my_lb_sg"))
    mon_idx = next(j for j, c in enumerate(cmds) if "-monitorName tcp-default" in c)
    assert sg_idx < mon_idx, "monitor bind must come after add serviceGroup"


def test_create_lb_no_monitor_omits_bind_service_monitorname():
    """When monitor is omitted, no bind service -monitorName line is emitted."""
    result = asyncio.run(
        create_lb(H, U, P, "my_lb", "10.0.0.1", ["192.168.1.1"],
                  lb_method="ROUNDROBIN", dry_run=True)
    )
    cmds = result["commands"]
    assert not any("-monitorName" in c for c in cmds), (
        f"Expected no -monitorName in commands, got: {cmds}"
    )


def test_create_lb_monitor_single_backend():
    """Single backend with monitor: exactly one bind service -monitorName line."""
    result = asyncio.run(
        create_lb(H, U, P, "lb1", "10.1.1.1", ["10.2.2.2"],
                  monitor="http", dry_run=True)
    )
    cmds = result["commands"]
    bind_mon_cmds = [c for c in cmds if "-monitorName http" in c]
    assert len(bind_mon_cmds) == 1
    assert "bind serviceGroup lb1_sg -monitorName http" in bind_mon_cmds[0]


# ===========================================================================
# 2. create_cs — dry_run with single-quoting of rules
# ===========================================================================

def test_create_cs_dry_run_single_quotes_rule():
    """Policy rule containing double-quotes must be wrapped in single quotes."""
    rule = 'HTTP.REQ.HEADER("Host").CONTAINS("api.example.com")'
    result = asyncio.run(
        create_cs(
            H, U, P, "cs_vs", "10.0.0.5",
            service_type="HTTP", port=80,
            policies=[{
                "policy_name": "cs_pol1",
                "rule": rule,
                "target_lb_vserver": "backend_lb",
                "priority": 10,
            }],
            dry_run=True,
        )
    )
    cmds = result["commands"]

    assert any("add cs vserver cs_vs" in c for c in cmds)
    policy_cmd = next((c for c in cmds if "add cs policy cs_pol1" in c), None)
    assert policy_cmd is not None
    # The rule must be wrapped in single quotes
    assert f"-rule '{rule}'" in policy_cmd

    bind_cmd = next((c for c in cmds if "bind cs vserver cs_vs" in c and "cs_pol1" in c), None)
    assert bind_cmd is not None
    assert "-targetLBVserver backend_lb" in bind_cmd
    assert "-priority 10" in bind_cmd


# ===========================================================================
# 3. create_rewrite — dry_run: single-quoting and bind with -type RESPONSE
# ===========================================================================

def test_create_rewrite_dry_run_insert_header():
    """insert_http_header: expression must be single-quoted; bind -type present."""
    expr = '"SAMEORIGIN"'
    result = asyncio.run(
        create_rewrite(
            H, U, P,
            action_name="rw_act1",
            action_type="insert_http_header",
            target="X-Frame-Options",
            policy_name="rw_pol1",
            rule="true",
            expression=expr,
            bind_to={"entity_type": "lb", "vserver": "my_lb", "bind_point": "RESPONSE", "priority": 100},
            dry_run=True,
        )
    )
    cmds = result["commands"]

    action_cmd = next((c for c in cmds if "add rewrite action rw_act1" in c), None)
    assert action_cmd is not None
    assert f"'{expr}'" in action_cmd

    bind_cmd = next((c for c in cmds if "bind lb vserver my_lb" in c), None)
    assert bind_cmd is not None
    assert "-type RESPONSE" in bind_cmd


# ===========================================================================
# 4. create_responder — dry_run: redirect bind has NO -type
# ===========================================================================

def test_create_responder_dry_run_redirect_no_type():
    """Responder bind command must NOT contain -type flag."""
    result = asyncio.run(
        create_responder(
            H, U, P,
            action_name="resp_act1",
            action_type="redirect",
            policy_name="resp_pol1",
            rule='HTTP.REQ.URL.STARTSWITH("/old")',
            expression='"https://example.com/new"',
            bind_to={"entity_type": "lb", "vserver": "my_lb", "priority": 50},
            dry_run=True,
        )
    )
    cmds = result["commands"]

    bind_cmd = next((c for c in cmds if "bind lb vserver my_lb" in c), None)
    assert bind_cmd is not None
    # Responder bindings must NOT have -type
    assert "-type" not in bind_cmd

    # Policy command present
    assert any("add responder policy resp_pol1" in c for c in cmds)


# ===========================================================================
# 5. delete_* — safe deletion order
# ===========================================================================

def test_delete_lb_order():
    """disable comes before rm; services are unbound before rm lb vserver."""
    result = asyncio.run(
        delete_lb(
            H, U, P, "my_lb",
            services=["svc1", "svc2"],
            servers=["srv1"],
            remove_backends=True,
            dry_run=True,
        )
    )
    cmds = result["commands"]

    disable_idx = next(i for i, c in enumerate(cmds) if "disable lb vserver" in c)
    rm_vs_idx = next(i for i, c in enumerate(cmds) if c == "rm lb vserver my_lb")
    unbind_idx = next(i for i, c in enumerate(cmds) if "unbind lb vserver" in c)

    assert disable_idx < unbind_idx < rm_vs_idx


def test_delete_cs_order():
    """disable before unbind, unbind before rm vserver, rm vserver before rm policy."""
    result = asyncio.run(
        delete_cs(
            H, U, P, "cs_vs",
            policies=["cs_pol1"],
            remove_policies=True,
            dry_run=True,
        )
    )
    cmds = result["commands"]

    disable_idx = next(i for i, c in enumerate(cmds) if "disable cs vserver" in c)
    unbind_idx = next(i for i, c in enumerate(cmds) if "unbind cs vserver" in c)
    rm_vs_idx = next(i for i, c in enumerate(cmds) if c == "rm cs vserver cs_vs")
    rm_pol_idx = next(i for i, c in enumerate(cmds) if "rm cs policy" in c)

    assert disable_idx < unbind_idx < rm_vs_idx < rm_pol_idx


def test_delete_rewrite_order():
    """unbind before rm policy, rm policy before rm action."""
    result = asyncio.run(
        delete_rewrite(
            H, U, P, "rw_pol1",
            action_name="rw_act1",
            unbind_from=[{"entity_type": "lb", "vserver": "my_lb", "bind_point": "REQUEST"}],
            dry_run=True,
        )
    )
    cmds = result["commands"]

    unbind_idx = next(i for i, c in enumerate(cmds) if "unbind lb vserver" in c)
    rm_pol_idx = next(i for i, c in enumerate(cmds) if c == "rm rewrite policy rw_pol1")
    rm_act_idx = next(i for i, c in enumerate(cmds) if c == "rm rewrite action rw_act1")

    assert unbind_idx < rm_pol_idx < rm_act_idx


def test_delete_responder_order():
    """unbind before rm policy, rm policy before rm action (no -type in unbind)."""
    result = asyncio.run(
        delete_responder(
            H, U, P, "resp_pol1",
            action_name="resp_act1",
            unbind_from=[{"entity_type": "lb", "vserver": "my_lb"}],
            dry_run=True,
        )
    )
    cmds = result["commands"]

    unbind_cmd = next((c for c in cmds if "unbind lb vserver my_lb" in c), None)
    assert unbind_cmd is not None
    # Responder unbind must have no -type
    assert "-type" not in unbind_cmd

    unbind_idx = next(i for i, c in enumerate(cmds) if "unbind lb vserver" in c)
    rm_pol_idx = next(i for i, c in enumerate(cmds) if c == "rm responder policy resp_pol1")
    rm_act_idx = next(i for i, c in enumerate(cmds) if c == "rm responder action resp_act1")

    assert unbind_idx < rm_pol_idx < rm_act_idx


# ===========================================================================
# 6. get_logs — validation and clamping
# ===========================================================================

def test_get_logs_rejects_bad_logfile():
    """Path-traversal / non-allowlisted file must raise ValueError immediately."""
    import pytest
    with pytest.raises(ValueError, match="not allowed"):
        asyncio.run(get_logs(H, U, P, logfile="etc/passwd", lines=10))


def test_get_logs_rejects_unknown_logfile():
    """An arbitrary unknown log name must raise ValueError."""
    import pytest
    with pytest.raises(ValueError):
        asyncio.run(get_logs(H, U, P, logfile="access.log", lines=10))


def test_get_logs_happy_path_command(monkeypatch):
    """Valid logfile builds 'shell tail -n <lines> /var/log/ns.log'; lines clamped."""
    captured = {}

    async def fake_run_prevalidated(command, host, username, password, *, port, timeout):
        captured["command"] = command
        return {"success": True, "output": "fake log line"}

    async def fake_get_logs_inner():
        # Patch run_prevalidated_command inside the module
        import app.services.netscaler_service as svc
        with mock.patch.object(svc, "run_prevalidated_command", side_effect=fake_run_prevalidated):
            # Also patch get_runtime_config to avoid real config loading
            fake_config = types.SimpleNamespace(
                ssh_fallback_enabled=True, ssh_port=22, ssh_timeout_seconds=30
            )
            with mock.patch("app.services.netscaler_service.get_runtime_config", return_value=fake_config):
                # But get_runtime_config is imported locally inside get_logs,
                # so we need to patch the right symbol.
                # Patch it in the config_service module path instead
                pass
        # Re-do with direct patching of the function itself
        return captured

    # We need to patch lazily-imported symbols. Patch at the call site.
    import app.services.netscaler_service as ns_svc

    async def run():
        fake_config = types.SimpleNamespace(
            ssh_fallback_enabled=True, ssh_port=22, ssh_timeout_seconds=30
        )
        # get_logs does: from app.services.config_service import get_runtime_config
        # and:           from app.services.ssh_service import run_prevalidated_command
        # Both are imported INSIDE the function, so we patch the modules.
        import app.services.config_service as cfg_svc
        import app.services.ssh_service as ssh_svc

        with mock.patch.object(cfg_svc, "get_runtime_config", return_value=fake_config):
            with mock.patch.object(ssh_svc, "run_prevalidated_command", side_effect=fake_run_prevalidated):
                result = await get_logs(H, U, P, logfile="ns.log", lines=100)
                return result

    result = asyncio.run(run())
    cmd = captured.get("command", "")
    assert cmd.startswith("shell tail -n 100 /var/log/ns.log"), f"Got: {cmd}"
    assert result.get("logFile") == "/var/log/ns.log"
    assert result.get("requestedLines") == 100


def test_get_logs_clamps_lines():
    """Lines > 2000 must be clamped to 2000."""
    captured = {}

    async def fake_run_prevalidated(command, host, username, password, *, port, timeout):
        captured["command"] = command
        return {"success": True, "output": "line"}

    async def run():
        import app.services.config_service as cfg_svc
        import app.services.ssh_service as ssh_svc
        fake_config = types.SimpleNamespace(
            ssh_fallback_enabled=True, ssh_port=22, ssh_timeout_seconds=30
        )
        with mock.patch.object(cfg_svc, "get_runtime_config", return_value=fake_config):
            with mock.patch.object(ssh_svc, "run_prevalidated_command", side_effect=fake_run_prevalidated):
                return await get_logs(H, U, P, logfile="ns.log", lines=9999)

    asyncio.run(run())
    cmd = captured.get("command", "")
    assert "tail -n 2000" in cmd, f"Expected lines clamped to 2000, got: {cmd}"


# ===========================================================================
# 7. search_config — injection rejection and happy path
# ===========================================================================

def test_search_config_rejects_injection():
    """Keywords with shell-unsafe characters must raise ValueError."""
    import pytest
    with pytest.raises(ValueError, match="unsafe"):
        asyncio.run(search_config(H, U, P, "a; rm -rf /"))


def test_search_config_rejects_space():
    """Space in keyword is not in the safe charset."""
    import pytest
    with pytest.raises(ValueError):
        asyncio.run(search_config(H, U, P, "lb vserver"))


def test_search_config_happy_path():
    """Safe keyword builds 'show ns runningConfig | grep -i <kw>'."""
    captured = {}

    async def fake_run_cli(host, username, password, command):
        captured["command"] = command
        return {"success": True, "output": "lb vserver myvs\n"}

    async def run():
        import app.services.netscaler_service as ns_svc
        with mock.patch.object(ns_svc, "run_cli_command", side_effect=fake_run_cli):
            return await search_config(H, U, P, "myvs")

    result = asyncio.run(run())
    cmd = captured.get("command", "")
    assert "show ns runningConfig | grep -i myvs" in cmd
    assert result.get("keyword") == "myvs"
    assert result.get("matchCount") == 1


# ===========================================================================
# 8. _detect_ha_configured — standalone vs HA pair
# ===========================================================================

_STANDALONE_OUTPUT = """\

Node ID:                 0
IP:                      192.168.1.10
State:                   Primary
INC State:               DISABLED
Sync State:              SUCCESS
Propogation Timeout:     YES
Enabled Interfaces :     0/1 0/2
Disabled Interfaces:
HA MON ON Interfaces:    0/1 0/2
Interfaces on which heartbeats are not seen:
Ssl Card Status:         NOT PRESENT
Master State:            Primary
Hello Interval:          200
Dead Interval:           3
Node in this Master State for:  00:00:01  [HH:MM:SS]
Synchronization in progress...
Total Probe Failure:     0
Total Probe Success:     2
Current time:            Thu Jun 24 00:00:00 2026

Done
"""

_HA_PAIR_OUTPUT = """\

Node ID:                 0
IP:                      192.168.1.10
State:                   Primary
INC State:               DISABLED

Node ID:                 1
IP:                      192.168.1.11 (peer)
State:                   Secondary
INC State:               DISABLED

Done
"""


def test_detect_ha_configured_standalone_returns_false():
    # A standalone appliance lists exactly one "Node ID:" entry (its own, ID 0), even
    # though the output contains "Master State: Primary" and "Node in this Master State
    # for:". The detector must NOT treat any of those as a second node.
    assert _detect_ha_configured(_STANDALONE_OUTPUT) is False


def test_detect_ha_configured_ha_pair_returns_true():
    assert _detect_ha_configured(_HA_PAIR_OUTPUT) is True


def test_detect_ha_configured_empty_returns_false():
    assert _detect_ha_configured("") is False


def test_detect_ha_configured_standalone_primary_not_false_positive():
    """Regression: a standalone node showing 'Master State: Primary' must NOT be
    misread as HA. Only a second 'Node ID:' entry (or an explicit peer) means HA."""
    output = (
        "1)\tNode ID:      0\n\tIP:  192.168.20.220\n"
        "\tNode State: UP\n\tMaster State: Primary\n"
        "\tNode in this Master State for: 2:10:25:9\n Done\n"
    )
    assert _detect_ha_configured(output) is False


def test_detect_ha_configured_peer_node_keyword():
    """Explicit 'peer node' indicator is treated as HA configured."""
    assert _detect_ha_configured("Peer Node Information:\nIP: 192.168.1.11\n") is True
