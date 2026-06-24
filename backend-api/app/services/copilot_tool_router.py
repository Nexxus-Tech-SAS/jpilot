"""Intent-based tool selection to reduce tokens sent to the LLM on each request."""

from __future__ import annotations

from typing import Any

from app.services.copilot_architect_discovery import user_wants_deliverable_now
from app.services.calibration_matcher import has_installed_skills_for_chat
from app.services.copilot_form import is_form_submission, user_requests_design_implementation
from app.services.copilot_inventory import detect_ip_inventory_request
from app.services.copilot_service_status import detect_service_status_request

# Pack names map to tool names included when that intent is detected.
PACK_TOOLS: dict[str, frozenset[str]] = {
    "core_read": frozenset(
        {
            "netscaler_get_system_info",
            "netscaler_test_connection",
        }
    ),
    "inventory": frozenset({"netscaler_list_inventory"}),
    "read": frozenset(
        {
            "netscaler_list_applications",
            "netscaler_list_virtual_servers",
            "netscaler_list_virtual_ips",
            "netscaler_list_ip_addresses",
            "netscaler_list_service_status",
            "netscaler_nextgen_get",
            "netscaler_run_cli_command",
        }
    ),
    "ip_inventory": frozenset({"netscaler_list_ip_addresses"}),
    "service_status": frozenset({"netscaler_list_service_status"}),
    "diagnostic": frozenset(
        {
            "netscaler_run_diagnostic",
            "netscaler_telnet",
            "netscaler_collect_nsconmsg",
        }
    ),
    "cli_write": frozenset(
        {
            "netscaler_run_cli_commands",
            "netscaler_add_ip_address",
            "netscaler_ssh_run_command",
        }
    ),
    "nextgen_write": frozenset(
        {
            "netscaler_create_application",
            "netscaler_nextgen_request",
        }
    ),
    "lb_config": frozenset(
        {
            "netscaler_create_lb",
            "netscaler_modify_lb",
            "netscaler_delete_lb",
        }
    ),
    "cs_config": frozenset(
        {
            "netscaler_create_cs",
            "netscaler_modify_cs",
            "netscaler_delete_cs",
        }
    ),
    "rewrite_config": frozenset(
        {
            "netscaler_create_rewrite",
            "netscaler_modify_rewrite",
            "netscaler_delete_rewrite",
        }
    ),
    "responder_config": frozenset(
        {
            "netscaler_create_responder",
            "netscaler_modify_responder",
            "netscaler_delete_responder",
        }
    ),
    "logs": frozenset({"netscaler_get_logs"}),
    "config_search": frozenset({"netscaler_search_config"}),
    # Verification-only subset of "read": no raw CLI write tool (netscaler_run_cli_command).
    # Used when a dedicated config pack is matched so the model cannot fall into the
    # gated raw-CLI trap (RC-1 in operator-findings).
    "read_safe": frozenset(
        {
            "netscaler_list_virtual_servers",
            "netscaler_list_service_status",
            "netscaler_list_ip_addresses",
            "netscaler_nextgen_get",
        }
    ),
    "ha_failover": frozenset({"netscaler_force_failover"}),
    "cli_search": frozenset({"search_netscaler_cli_reference"}),
    "nextgen_search": frozenset({"search_netscaler_nextgen_api"}),
    "doc_connectivity": frozenset({"jpilot_check_doc_connectivity"}),
    "architect_search": frozenset({"search_jpilot_architect_resources"}),
    "stack_calibration": frozenset(
        {
            "search_stack_calibration_memory",
            "list_official_blueprint_catalog",
        }
    ),
}

ROLE_BASE_PACKS: dict[str, frozenset[str]] = {
    "architect": frozenset({"inventory"}),
    "analyst": frozenset({"core_read", "read", "diagnostic", "cli_search", "nextgen_search"}),
    "operator": frozenset({"core_read", "read"}),
}

CISCO_PACK_TOOLS: dict[str, frozenset[str]] = {
    "core_read": frozenset({"cisco_test_connection"}),
    "read": frozenset({"cisco_ssh_run_command"}),
    "cli_write": frozenset({"cisco_run_cli_command", "cisco_run_cli_commands"}),
    "cli_search": frozenset({"search_cisco_cli_reference"}),
    "doc_connectivity": frozenset({"jpilot_check_doc_connectivity"}),
    "inventory": frozenset({"netscaler_list_inventory"}),
    "stack_calibration": frozenset(
        {
            "search_stack_calibration_memory",
            "list_official_blueprint_catalog",
        }
    ),
}

CISCO_ROLE_BASE_PACKS: dict[str, frozenset[str]] = {
    "analyst": frozenset({"core_read", "read", "cli_search"}),
    "operator": frozenset({"core_read", "read", "cli_search"}),
}

SDX_PACK_TOOLS: dict[str, frozenset[str]] = {
    "core_read": frozenset({"sdx_test_connection"}),
    "read": frozenset({"sdx_ssh_run_command"}),
    "cli_write": frozenset({"sdx_run_cli_command", "sdx_run_cli_commands"}),
    "cli_search": frozenset({"search_sdx_cli_reference"}),
    "doc_connectivity": frozenset({"jpilot_check_doc_connectivity"}),
    "inventory": frozenset({"netscaler_list_inventory"}),
    "stack_calibration": frozenset(
        {
            "search_stack_calibration_memory",
            "list_official_blueprint_catalog",
        }
    ),
}

SDX_ROLE_BASE_PACKS: dict[str, frozenset[str]] = {
    "analyst": frozenset({"core_read", "read", "cli_search"}),
    "operator": frozenset({"core_read", "read", "cli_search"}),
}

F5_PACK_TOOLS: dict[str, frozenset[str]] = {
    "core_read": frozenset({"f5_test_connection"}),
    "read": frozenset({"f5_ssh_run_command"}),
    "cli_write": frozenset({"f5_run_tmsh_command", "f5_run_tmsh_commands"}),
    "cli_search": frozenset({"search_f5_tmsh_reference"}),
    "architect_search": frozenset({"search_f5_documentation"}),
    "doc_connectivity": frozenset({"jpilot_check_doc_connectivity"}),
    "inventory": frozenset({"netscaler_list_inventory"}),
    "stack_calibration": frozenset(
        {
            "search_stack_calibration_memory",
            "list_official_blueprint_catalog",
        }
    ),
}

F5_ROLE_BASE_PACKS: dict[str, frozenset[str]] = {
    "architect": frozenset({"architect_search", "doc_connectivity", "inventory"}),
    "analyst": frozenset({"core_read", "read", "cli_search"}),
    "operator": frozenset({"core_read", "read", "cli_search"}),
}

MIN_ROUTED_TOOLS = 3


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def classify_tool_packs(
    user_message: str,
    *,
    role: str,
    attachment_names: list[str] | None = None,
    vendor: str = "netscaler",
) -> set[str]:
    lowered = (user_message or "").lower()
    attachments = attachment_names or []
    if vendor == "cisco":
        packs: set[str] = set(CISCO_ROLE_BASE_PACKS.get(role, CISCO_ROLE_BASE_PACKS["operator"]))
    elif vendor == "f5":
        packs = set(F5_ROLE_BASE_PACKS.get(role, F5_ROLE_BASE_PACKS["operator"]))
    elif vendor == "sdx":
        packs = set(SDX_ROLE_BASE_PACKS.get(role, SDX_ROLE_BASE_PACKS["operator"]))
    else:
        packs = set(ROLE_BASE_PACKS.get(role, ROLE_BASE_PACKS["operator"]))

    if has_installed_skills_for_chat(role=role, vendor=vendor):
        packs.add("stack_calibration")

    # Precise single-intent reads route tightly (core_read + the one read tool), not the
    # whole read pack — fewer, more precise tools per turn. Keep blueprint tools if present.
    if vendor == "netscaler" and role != "architect" and detect_service_status_request(user_message):
        tight = {"core_read", "service_status"}
        if "stack_calibration" in packs:
            tight.add("stack_calibration")
        return tight
    if vendor == "netscaler" and role != "architect" and detect_ip_inventory_request(user_message):
        tight = {"core_read", "ip_inventory"}
        if "stack_calibration" in packs:
            tight.add("stack_calibration")
        return tight

    if role == "architect" and vendor == "netscaler":
        architect_packs: set[str] = set()
        if user_wants_deliverable_now(user_message):
            architect_packs.update({"architect_search", "cli_search", "nextgen_search"})
        if has_installed_skills_for_chat(role=role, vendor=vendor):
            architect_packs.add("stack_calibration")
        return architect_packs

    if _contains_any(
        lowered,
        (
            "can you reach",
            "can jpilot reach",
            "doc connectivity",
            "documentation site",
            "reach the documentation",
        ),
    ):
        packs.add("doc_connectivity")

    if _contains_any(
        lowered,
        (
            "internet access",
            "internet connectivity",
            "reach the internet",
            "outbound internet",
            "has internet",
            "access the internet",
            "connect to the internet",
            "external connectivity",
        ),
    ):
        if _contains_any(
            lowered,
            (
                "netscaler",
                "adc",
                "appliance",
                "nsip",
                "the box",
                "this box",
                "vpx",
            ),
        ) or not _contains_any(
            lowered,
            (
                "can you reach",
                "can jpilot",
                "jpilot reach",
                "your server",
                "the backend",
                "documentation site",
            ),
        ):
            packs.add("diagnostic")
        else:
            packs.add("doc_connectivity")

    if _contains_any(
        lowered,
        (
            "ping",
            "traceroute",
            "telnet",
            "reachable",
            "tcp port",
            "port check",
            "nsconmsg",
            "cpu",
            "memory util",
            "performance counter",
            "diag",
        ),
    ):
        packs.add("diagnostic")

    if _contains_any(
        lowered,
        (
            "show ",
            "list ",
            "get ",
            "stat ",
            "how many",
            "what is the",
            "inventory",
            "version",
            "firmware",
            "hostname",
            "serial",
        ),
    ):
        packs.add("read")

    if _contains_any(
        lowered,
        (
            "nsip",
            "snip",
            "all ip",
            "list ip",
            "every ip",
            "ip address",
            "ip addresses",
            "show ns ip",
        ),
    ):
        packs.add("read")

    # ------------------------------------------------------------------
    # Dedicated NetScaler config tools — tightly routed by intent.
    # When any of these match, search tools are demoted (removed below).
    # ------------------------------------------------------------------
    _dedicated_config_packs: set[str] = set()

    _config_verb = _contains_any(
        lowered,
        (
            "create",
            "add ",
            "configure",
            "set up",
            "setup",
            "modify",
            "change",
            "update",
            "edit",
            "delete",
            "remove",
            "replace",
            "implement",
        ),
    )

    if _contains_any(
        lowered,
        (
            "load balanc",
            "lb vserver",
            "lbvserver",
            "create an lb",
            "new lb",
            "lb method",
        ),
    ) or (
        _config_verb
        and _contains_any(lowered, ("service group", "vip ", "virtual server"))
        and _contains_any(lowered, ("lb", "load balanc"))
    ):
        _dedicated_config_packs.add("lb_config")

    if _contains_any(
        lowered,
        (
            "content switch",
            "cs vserver",
            "csvserver",
            "cs policy",
        ),
    ):
        _dedicated_config_packs.add("cs_config")

    if _contains_any(
        lowered,
        (
            "rewrite policy",
            "rewrite action",
            "insert header",
            "hsts",
            "x-frame-options",
        ),
    ):
        _dedicated_config_packs.add("rewrite_config")

    if _contains_any(
        lowered,
        (
            "responder",
            "redirect to https",
            "http to https",
            "respond with",
            "maintenance page",
        ),
    ):
        _dedicated_config_packs.add("responder_config")

    if _contains_any(
        lowered,
        (
            "ns.log",
            "/var/log",
            "tail the log",
            "show me the logs",
            "messages log",
            "get logs",
            "fetch logs",
        ),
    ):
        _dedicated_config_packs.add("logs")

    if _contains_any(
        lowered,
        (
            "search the config",
            "grep the config",
            "find in running config",
            "running config",
            "search config",
            "grep config",
            "find in the config",
        ),
    ):
        _dedicated_config_packs.add("config_search")

    if _contains_any(
        lowered,
        (
            "force failover",
            "failover",
            "ha failover",
            "force ha",
        ),
    ):
        _dedicated_config_packs.add("ha_failover")

    if _dedicated_config_packs:
        packs.update(_dedicated_config_packs)
        # Add verification reads but NOT the full "read" pack — the full pack contains
        # netscaler_run_cli_command (a gated write tool) which would let the model fall into
        # the gated raw-CLI trap instead of using dedicated create/modify/delete tools.
        # read_safe gives the model show-command verification without the raw write tool.
        packs.add("read_safe")
        packs.discard("read")
        # Demote search tools: dedicated tools cover the request
        packs.discard("cli_search")
        packs.discard("nextgen_search")

    if role == "architect" and user_wants_deliverable_now(user_message):
        packs.update({"architect_search", "cli_search", "nextgen_search"})

    if is_form_submission(user_message):
        if role == "architect":
            packs.discard("architect_search")
            packs.discard("cli_search")
            packs.discard("nextgen_search")
            packs.discard("cli_write")
            packs.discard("nextgen_write")
            packs.discard("read")
            packs.discard("inventory")
        elif _dedicated_config_packs:
            # Dedicated config intent on a form-submission turn: keep dedicated tools +
            # read_safe for verification but do NOT re-add the raw "read" pack (which
            # carries netscaler_run_cli_command and would reopen the gated-CLI trap).
            packs.update({"cli_write", "cli_search", "nextgen_write", "nextgen_search"})
        else:
            packs.update({"cli_write", "cli_search", "nextgen_write", "nextgen_search", "read"})

    if role == "architect":
        return packs

    cli_write_signal = _contains_any(
        lowered,
        (
            "add ",
            "set ",
            "bind ",
            "unbind",
            "rm ",
            "remove ",
            "delete ",
            "create lb",
            "create a lb",
            "new lb",
            "new vip",
            "save ns config",
            "configure",
            "implement",
            "route",
            "static route",
            "routing",
            "vlan",
            "interface",
            "provision",
            "run cli",
            "cli command",
        ),
    )
    nextgen_write_signal = _contains_any(
        lowered,
        (
            "application",
            "next-gen",
            "nextgen",
            "config-set",
            "config set",
            "/applications",
            "post application",
        ),
    )

    if user_requests_design_implementation(user_message, attachments):
        packs.update({"cli_write", "cli_search", "read", "core_read"})

    if cli_write_signal:
        packs.update({"cli_write", "cli_search", "read"})

    if nextgen_write_signal:
        packs.update({"nextgen_write", "nextgen_search", "read"})

    if role in {"operator", "analyst"} and not packs.intersection(
        {"diagnostic", "cli_write", "nextgen_write", "read", "doc_connectivity"}
    ):
        packs.add("read")

    # Final demotion pass: if any dedicated config pack was matched, strip search tools
    # and the raw "read" pack (which carries netscaler_run_cli_command) even if the
    # cli_write/nextgen_write signals or the fallback re-added them above.
    if _dedicated_config_packs:
        packs.discard("cli_search")
        packs.discard("nextgen_search")
        packs.discard("read")  # read_safe was added earlier; raw read not needed here

    return packs


def pack_tool_names(packs: set[str], vendor: str = "netscaler") -> set[str]:
    names: set[str] = set()
    if vendor == "cisco":
        source = CISCO_PACK_TOOLS
    elif vendor == "f5":
        source = F5_PACK_TOOLS
    elif vendor == "sdx":
        source = SDX_PACK_TOOLS
    else:
        source = PACK_TOOLS
    for pack in packs:
        names.update(source.get(pack, frozenset()))
    return names


def should_use_full_tool_set(user_message: str, role: str) -> bool:
    """Fallback to all role-enabled tools when routing would be unreliable."""
    text = (user_message or "").strip()
    if len(text) < 3:
        return True
    if role == "architect":
        return False
    lowered = text.lower()
    if _contains_any(lowered, ("and also", "then ", "after that", "multi-step", "step 1")):
        return True
    if lowered.count(",") >= 3:
        return True
    # Short confirmation/approval turns (e.g. "Yes, apply it", "yes proceed", "confirm",
    # "go ahead") cannot be reliably routed — use the full tool set so the model retains
    # access to whatever dedicated tool the prior turn used (e.g. netscaler_create_lb).
    if _contains_any(
        lowered,
        (
            "yes, apply",
            "yes apply",
            "apply it",
            "go ahead",
            "proceed",
            "confirm",
            "sí",
            "procede",
            "yes, proceed",
            "yes proceed",
            "yes, confirm",
            "approved",
        ),
    ):
        return True
    return False


def route_copilot_tools(
    enabled_tools: list[dict[str, Any]],
    *,
    role: str,
    user_message: str,
    attachment_names: list[str] | None = None,
    vendor: str = "netscaler",
) -> list[dict[str, Any]]:
    """Return a subset of enabled_tools matching detected intents."""
    if not enabled_tools:
        return enabled_tools

    if vendor in {"cisco", "sdx", "f5"}:
        return enabled_tools

    if vendor != "netscaler":
        return enabled_tools

    packs = classify_tool_packs(
        user_message, role=role, attachment_names=attachment_names, vendor=vendor
    )
    # Precise single-intent reads route tightly even for comma-heavy phrasing; only fall
    # back to the full tool set for genuinely ambiguous/multi-step requests.
    precise_intent = bool(
        packs
        & {
            "ip_inventory",
            "service_status",
            # Dedicated config/goal intents route tightly to their own tools instead of
            # falling through to the full 45-tool set (which dilutes selection — e.g. the
            # model picking netscaler_telnet for "create a load balancer").
            "lb_config",
            "cs_config",
            "rewrite_config",
            "responder_config",
            "logs",
            "config_search",
            "ha_failover",
        }
    )
    if not precise_intent and should_use_full_tool_set(user_message, role):
        return enabled_tools
    allowed_names = pack_tool_names(packs, vendor=vendor)
    enabled_names = {tool["name"] for tool in enabled_tools}
    selected_names = allowed_names & enabled_names

    if role == "architect":
        return [tool for tool in enabled_tools if tool["name"] in selected_names]

    if "ip_inventory" in packs:
        selected = [tool for tool in enabled_tools if tool["name"] in selected_names]
        return selected or enabled_tools

    if "service_status" in packs:
        selected = [tool for tool in enabled_tools if tool["name"] in selected_names]
        return selected or enabled_tools

    if len(selected_names) < MIN_ROUTED_TOOLS:
        return enabled_tools

    selected = [tool for tool in enabled_tools if tool["name"] in selected_names]
    return selected or enabled_tools
