"""Intent-based tool selection to reduce tokens sent to the LLM on each request."""

from __future__ import annotations

import re
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
    # analyst always has the dedicated read-only log-tail and config-grep tools so the model
    # can use them without falling back to raw SSH.  logs → netscaler_get_logs;
    # config_search → netscaler_search_config.
    "analyst": frozenset({"core_read", "read", "diagnostic", "cli_search", "nextgen_search", "logs", "config_search"}),
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

# ---------------------------------------------------------------------------
# §4.1 — Raw-CLI strip for LB-intent and LB-confirm turns.
#
# When a dedicated LB intent is active (this turn or the prior turn), these
# tools must never appear in the active set so the model cannot freelance
# raw `add lb vserver` / `add serviceGroup` CLI.
# ---------------------------------------------------------------------------

_RAW_CLI_TOOLS_TO_STRIP_ON_LB = frozenset(
    {
        "netscaler_run_cli_command",
        "netscaler_run_cli_commands",
    }
)

# Matches the hidden dry_run plan marker embedded by the orchestrator in the
# prior assistant reply (<!-- jpilot-plan: <base64> -->).  We detect it here
# without importing from copilot_orchestrator to avoid a circular dependency.
_PLAN_MARKER_RE = re.compile(
    r"<!--\s*jpilot-plan:\s*[A-Za-z0-9+/=]+\s*-->", re.IGNORECASE
)

# Short affirmation tokens — mirrors is_affirmation() in copilot_form.py but
# without the word-count cap so we can keep it import-free.
_AFFIRMATION_RE = re.compile(
    r"^\s*(yes|yeah|yep|yup|sure|ok|okay|go\s+ahead|do\s+it|apply\s+it|confirm|"
    r"proceed|approved|correct|right|affirmative|si|s[íi])\s*[.,!]?\s*$",
    re.IGNORECASE,
)


def _prior_assistant_has_dedicated_plan(history: list[dict] | None) -> bool:
    """Return True when the most recent assistant message contains a dry_run plan marker.

    The marker is embedded by _embed_dry_run_plan_marker (copilot_orchestrator) after a
    successful dedicated-tool (create_lb / modify_lb / …) dry_run preview.  Its presence
    means the next affirmation turn should re-invoke the same tool with confirm=true, and
    the model must not be offered raw run_cli_command(s).
    """
    for item in reversed(history or []):
        if str(item.get("role") or "").lower() != "assistant":
            continue
        content = str(item.get("content") or "")
        return bool(_PLAN_MARKER_RE.search(content))
    return False


def _is_short_affirmation(user_message: str) -> bool:
    """Lightweight affirmation detection for routing purposes."""
    stripped = (user_message or "").strip()
    # Word-count guard: short affirmations only (same spirit as is_affirmation)
    if not stripped or len(stripped.split()) > 5:
        return False
    return bool(_AFFIRMATION_RE.match(stripped))


# Affirmation phrases matched by should_use_full_tool_set (but not _is_short_affirmation).
# Used separately to detect confirm turns without triggering on multi-step/comma signals.
_AFFIRMATION_PHRASES = frozenset(
    {
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
    }
)


def _is_affirmation_phrase(user_message: str) -> bool:
    """Return True when the message contains an affirmation phrase (same set as
    should_use_full_tool_set) but is NOT a multi-step/comma-heavy request.

    This covers compound affirmations like "yes apply it", "go ahead", "confirm"
    that are not matched by _is_short_affirmation's strict word-count+regex check.
    We guard against multi-step signals so we don't mistake "create LB, then CS, and also
    bind the policy" for a confirm turn.
    """
    lowered = (user_message or "").strip().lower()
    if not lowered:
        return False
    # Exclude multi-step / comma-heavy messages that happen to contain a phrase
    if lowered.count(",") >= 3:
        return False
    if any(s in lowered for s in ("and also", "then ", "after that", "multi-step", "step 1")):
        return False
    return any(phrase in lowered for phrase in _AFFIRMATION_PHRASES)


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

    # LB member/persistence edits handled by netscaler_modify_lb (no explicit "lb" word needed)
    if _contains_any(
        lowered,
        (
            "persistence",
            "persistency",
            "backend server",
            "add server",
            "add a backend",
            "remove backend",
        ),
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
            "rewrite",
            "rewrite policy",
            "rewrite action",
            "insert header",
            "x-forwarded",
            "forwarded-for",
            "xff",
            "client ip into",
            "real client ip",
            "security header",
            "response header",
            "server header",
            "remove header",
            "delete header",
            "strip header",
            "hsts",
            "x-frame-options",
            "x-content-type",
            "referrer-policy",
            "permissions-policy",
            "strict-transport",
        ),
    ):
        _dedicated_config_packs.add("rewrite_config")

    if _contains_any(
        lowered,
        (
            "responder",
            "redirect to https",
            "http to https",
            "http traffic to https",
            "redirect http",
            "https redirect",
            "respond with",
            "maintenance page",
        ),
    ) or ("redirect" in lowered and ("https" in lowered or "ssl" in lowered)):
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
            # read_safe for verification; do NOT add cli_write / raw "read" (which carry
            # netscaler_run_cli_command and would reopen the gated-CLI trap — R7 fix).
            # cli_search / nextgen_search are also unnecessary: the dedicated tools encode
            # correct syntax internally and need no pre-search.
            pass  # dedicated packs + read_safe already in packs from the block above
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
    history: list[dict] | None = None,
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

    # §4.1 — Confirm-turn LB strip.
    #
    # A short affirmation ("yes", "apply it", "go ahead", …) triggers
    # should_use_full_tool_set → True, which would return ALL enabled tools and
    # re-expose netscaler_run_cli_command(s) even on an LB-confirm turn.
    #
    # Guard: when the current message is a short affirmation AND the prior assistant
    # turn embedded a dedicated dry_run plan marker (lb_config / cs_config / …), we
    # know this is a confirm turn for a dedicated tool — NOT a generic multi-step
    # request.  Keep the narrow pack set and ensure raw CLI is absent.
    #
    # Over-strip guard: we only activate this when a prior dedicated plan is present.
    # Genuine multi-step non-LB requests have no plan marker and are unaffected.
    # An "affirmation turn" is any short approval message — covers both bare "yes"
    # (_is_short_affirmation) and compound phrases "yes apply it" / "go ahead" etc.
    # (which trigger should_use_full_tool_set but not our short-form regex).
    is_affirmation_turn = _is_short_affirmation(user_message) or _is_affirmation_phrase(user_message)
    has_prior_dedicated_plan = _prior_assistant_has_dedicated_plan(history)

    # Determine whether LB (or other dedicated) intent is in play this turn or from prior.
    _dedicated_packs_in_play = packs & {
        "lb_config", "cs_config", "rewrite_config", "responder_config", "ha_failover"
    }
    lb_confirm_turn = (
        # Case A: this is an affirmation AND a prior dry_run plan marker exists
        (is_affirmation_turn and has_prior_dedicated_plan)
        # Case B: this turn itself matched lb_config (belt-and-suspenders)
        or "lb_config" in packs
    )

    if not precise_intent and should_use_full_tool_set(user_message, role):
        if lb_confirm_turn:
            # Return full tool set MINUS raw CLI tools — the dedicated tool from the
            # prior plan is still available; the model cannot fall into raw `add lb vserver`.
            return [
                tool for tool in enabled_tools
                if tool["name"] not in _RAW_CLI_TOOLS_TO_STRIP_ON_LB
            ]
        return enabled_tools

    allowed_names = pack_tool_names(packs, vendor=vendor)
    enabled_names = {tool["name"] for tool in enabled_tools}
    selected_names = allowed_names & enabled_names

    # §4.1 — Confirm-turn enrichment: when this is an affirmation turn with a prior
    # dedicated plan (lb_confirm_turn via Case A), the narrow pack for "yes" doesn't
    # include lb_config tools (no LB keyword on a bare affirmation).  Inject the
    # lb_config + read_safe packs so the dedicated tool remains accessible on the
    # confirm turn.  This is the mirror of what should_use_full_tool_set does for
    # "yes, apply it"-style phrases — here we do it surgically for the LB case.
    if is_affirmation_turn and has_prior_dedicated_plan:
        lb_confirm_pack_names = pack_tool_names({"lb_config", "cs_config", "read_safe"}, vendor=vendor)
        selected_names |= lb_confirm_pack_names & enabled_names

    # §4.1 final hard-strip: even when the narrow-pack path is taken, ensure raw CLI
    # is absent when LB/dedicated intent is in play (this turn or prior confirm turn).
    if lb_confirm_turn or _dedicated_packs_in_play:
        selected_names -= _RAW_CLI_TOOLS_TO_STRIP_ON_LB

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


# ---------------------------------------------------------------------------
# Intent helpers for blueprint suggestion gating.
# ---------------------------------------------------------------------------

_DEDICATED_INTENT_PACKS = frozenset(
    {
        "lb_config",
        "cs_config",
        "rewrite_config",
        "responder_config",
        "logs",
        "config_search",
        "ha_failover",
    }
)


def has_dedicated_config_or_read_intent(user_message: str, role: str) -> bool:
    """Return True when the message maps to a dedicated config/read pack for operator/analyst.

    Used to gate blueprint suggestion cards for operator and analyst roles: only surface
    a suggestion when the user is clearly asking about a specific NetScaler object/domain
    (not a generic question).
    """
    if role == "architect":
        return False
    packs = classify_tool_packs(user_message, role=role, vendor="netscaler")
    return bool(packs & _DEDICATED_INTENT_PACKS)
