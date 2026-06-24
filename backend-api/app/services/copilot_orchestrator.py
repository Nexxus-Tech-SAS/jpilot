import base64
import json
import logging
import re
import sys
import time
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette.requests import Request

logger = logging.getLogger("copilot.tools")
# Uvicorn does not configure app loggers, so attach our own stdout handler once
# to guarantee the tool-call audit trail shows up in `docker compose logs`.
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False

from app.schemas.copilot import ChatResponse, ChatAttachment, CopilotSettings, DeploymentContinuation, ToolCallTrace
from app.services.copilot_attachment_service import (
    build_anthropic_user_content,
    build_gemini_user_parts,
    build_openai_user_content,
    validate_attachments,
)
from app.services.ai_provider_service import (
    lm_studio_endpoint_candidates,
    normalize_azure_resource_endpoint,
    OPENAI_COMPAT_CHAT_PROVIDER_TYPES,
    resolve_base_url,
    resolve_bedrock_openai_base,
)
from app.services.copilot_service import (
    chat_anthropic,
    chat_gemini,
    chat_openai_compatible,
    execute_copilot_tool,
    get_enabled_copilot_tools,
    to_anthropic_tools,
    to_gemini_tools,
    to_openai_tools,
)
from app.services.copilot_form import (
    attach_default_lb_form_if_missing,
    parse_input_form,
    to_response_input_form,
    user_requests_design_implementation,
)
from app.services.model_usage_service import UsageAccumulator, flush_usage_accumulator, record_provider_usage
from app.services.copilot_memory_gate import (
    CLI_MEMORY_SEARCH_TOOL,
    CISCO_CLI_MEMORY_SEARCH_TOOL,
    F5_CLI_MEMORY_SEARCH_TOOL,
    MEMORY_SEARCH_TOOL,
    SDX_CLI_MEMORY_SEARCH_TOOL,
    block_result_for_unconfirmed_destructive,
    destructive_confirmation_required,
)
from app.services.copilot_architect_discovery import (
    architect_discovery_should_retry,
    architect_tools_enabled,
    block_architect_tool_during_discovery,
    build_architect_session_nudge,
    sanitize_architect_reply,
)
from app.services.copilot_retry import build_tool_retry_hint
from app.services.copilot_roles import (
    JPilotRole,
    build_system_prompt,
    normalize_role,
    role_requires_appliance,
)
from app.services.copilot_tool_router import route_copilot_tools
from app.services.copilot_vendors import copilot_vendor_is_supported
from app.services.vendor_registry import resolve_chat_vendor
from app.services.encryption_service import decrypt_value

from app.services.calibration_matcher import (
    BLUEPRINT_FIRST_NUDGE,
    resolve_blueprint_turn_context,
)
from app.services.calibration_sync_service import list_installed_skills
from app.services.copilot_calibration_gate import (
    STACK_CALIBRATION_MEMORY_TOOL,
    apply_tool_review_gates,
)
from app.services.context_limits import ContextLimits, resolve_context_limits
from app.services.copilot_orchestration import (
    OrchestrationRuntime,
    OrchestrationSettings,
    build_deployment_subtasks,
    build_orchestration_runtime,
    build_progress_subtasks,
    check_loop_breakers,
    continuation_for_tool_limit,
    deliverable_ready_from_content,
    deployment_write_complete,
    had_successful_state_change,
    orchestration_settings_from_document,
    should_offer_long_task_consent,
    trace_executed_successfully,
    trace_is_state_changing,
)
from app.services.copilot_progress import QueueChatProgressReporter

# Tool-loop limits live on OrchestrationSettings (DEFAULT_MAX_TOOL_ITERATIONS /
# DEFAULT_MAX_TOOL_CONTINUATION_PHASES, overridable via the orchestration settings doc) and
# are read at runtime as runtime.max_tool_iterations / runtime.max_continuation_phases. The
# former module-level MAX_TOOL_ITERATIONS=40 / MAX_TOOL_CONTINUATION_PHASES=3 constants were
# dead (and the 3 disagreed with the real default of 4) — removed to keep one source of truth.

TOOL_ITERATION_LIMIT_MESSAGE = "I reached the maximum number of tool calls. Please try a simpler request."

CONTINUATION_NUDGE = (
    "TOOL ITERATION LIMIT — continue this deployment in the same turn. "
    "Do NOT ask the user to retry or confirm again. "
    "Review successful and failed tool results above, then finish remaining work. "
    "Prefer netscaler_run_cli_commands (one call with all remaining CLI + save ns config) "
    "or the vendor batch write tool. "
    "For removals, batch every unbind/rm/uninstall in as few calls as possible (confirmed=true). "
    "Before claiming success, run netscaler_list_virtual_servers and confirm the vserver is UP "
    "with backends bound (serverCount > 0), or absent after a removal. Reply briefly when verified."
)

_USER_CONFIRM_WORDS = (
    "proceed",
    "procede",
    "proceda",
    "yes",
    "confirm",
    "confirmed",
    "go ahead",
    "do it",
    "apply",
    "execute",
    "sí",
    "si",
    "dale",
    "continua",
    "continúa",
)


class ChatCancelledError(Exception):
    """Raised when the client closes the connection before chat completes."""


async def raise_if_chat_cancelled(request: Request | None) -> None:
    if request is not None and await request.is_disconnected():
        raise ChatCancelledError()

# Tools that change appliance state. Used to detect fabricated execution claims.
WRITE_EXEC_TOOL_NAMES = frozenset(
    {
        "netscaler_create_application",
        "netscaler_add_ip_address",
        "netscaler_run_cli_command",
        "netscaler_run_cli_commands",
        "netscaler_nextgen_request",
        "netscaler_create_lb",
        "netscaler_modify_lb",
        "netscaler_delete_lb",
        "netscaler_create_cs",
        "netscaler_modify_cs",
        "netscaler_delete_cs",
        "netscaler_create_rewrite",
        "netscaler_modify_rewrite",
        "netscaler_delete_rewrite",
        "netscaler_create_responder",
        "netscaler_modify_responder",
        "netscaler_delete_responder",
        "netscaler_force_failover",
    }
)

# Phrases that assert a configuration change was completed (not instructions/how-to).
_ACTION_CLAIM_PATTERN = re.compile(
    r"\b(executed successfully|commands? (were )?executed|running the following commands?|"
    r"the following commands? (will be |were )?(run|executed)|"
    r"successfully "
    r"(created|added|bound|deleted|removed|configured|applied|saved|updated|enabled|disabled)|"
    r"(have|has) been (created|added|bound|deleted|removed|configured|applied|saved|updated|enabled|disabled)|"
    r"i('ve| have)?\s*(created|added|bound|deleted|removed|configured|applied|saved|updated|enabled|disabled|run|ran)|"
    r"config(uration)? saved|saved (the )?config)\b",
    re.IGNORECASE,
)

# Prose that lists CLI verbs without a successful tool run — treat as unexecuted.
_CLI_LISTING_PATTERN = re.compile(
    r"(?m)^\s*(add|bind|set|enable|disable|rm|clear|save)\s+(lb|service|servicegroup|ns|vlan|route)\b",
    re.IGNORECASE,
)

CONFIG_CHANGE_VERBS = (
    "create",
    "add",
    "bind",
    "configure",
    "set up",
    "setup",
    "delete",
    "remove",
    "enable",
    "disable",
    "modify",
    "update",
)
CONFIG_CHANGE_NOUNS = (
    "vserver",
    "virtual server",
    "service group",
    "servicegroup",
    "lb ",
    "load balancer",
    "load-balancer",
    "backend",
    "service",
    "vip",
    "application",
    "monitor",
    "vlan",
    "route",
    "certificate",
    "policy",
)

FORCE_TOOL_EXECUTION_MESSAGE = (
    "STOP — you must EXECUTE the configuration with tools, not describe CLI commands in prose. "
    "If search_netscaler_cli_reference has not run yet, call it first. "
    "Then call netscaler_run_cli_commands with the full command list in order "
    "(preferred for multi-step LB setup), or netscaler_run_cli_command once per command. "
    "Include 'save ns config' at the end for classic config. "
    "Do not reply to the user until every command has succeeded."
)

UNEXECUTED_ACTION_BANNER = (
    "> ⚠️ **No changes were applied to the appliance.** The reply below claims a "
    "configuration change, but no NetScaler tool ran successfully this turn — so nothing "
    "was actually sent to the appliance. This usually means the current model is not reliably "
    "emitting tool calls. Switch to a more capable model (Anthropic Claude or a GPT-4o-class "
    "model) in **AI Providers**, retry, and verify on the appliance."
)

UNVERIFIED_READ_BANNER = (
    "> ⚠️ **Unverified read.** Tool calls failed this turn, so the details below may be "
    "invented from earlier chat context rather than live appliance data. Retry with "
    "netscaler_list_service_status or the exact official CLI from search_netscaler_cli_reference."
)

_STATUS_ANSWER_PATTERN = re.compile(
    r"\b(down|unhealthy|out of service|root cause|bound to|service group|backend target)\b",
    re.IGNORECASE,
)


def _claims_config_change(content: str) -> bool:
    if not content:
        return False
    if _ACTION_CLAIM_PATTERN.search(content):
        return True
    return bool(_CLI_LISTING_PATTERN.search(content))


def _user_requests_config_change(user_message: str) -> bool:
    lowered = user_message.lower()
    has_verb = any(verb in lowered for verb in CONFIG_CHANGE_VERBS)
    has_noun = any(noun in lowered for noun in CONFIG_CHANGE_NOUNS)
    return has_verb and has_noun


def _user_wants_discovery_first(user_message: str) -> bool:
    lowered = user_message.lower()
    return any(
        phrase in lowered
        for phrase in (
            "ask me",
            "ask questions",
            "questions you need",
            "what do you need",
            "tell me what you need",
            "before you configure",
            "before configuring",
            "what information",
            "what details",
        )
    )


def _assistant_is_gathering_requirements(content: str) -> bool:
    if not content or not content.strip():
        return False
    lowered = content.lower()
    if "?" in content:
        return True
    return any(
        phrase in lowered
        for phrase in (
            "please provide",
            "please share",
            "please confirm",
            "i need the following",
            "could you provide",
            "can you provide",
            "let me know",
            "before i configure",
            "before i can configure",
            "missing information",
            "still need",
        )
    )


def _response_has_input_form(content: str) -> bool:
    _, form = parse_input_form(content)
    return form is not None


def _apply_blueprint_context(
    system_prompt: str,
    *,
    user_message: str,
    role: str,
    vendor: str | None,
) -> tuple[str, bool, bool]:
    from app.services.knowledge_pack_runtime import resolve_knowledge_pack_turn_context
    from app.services.knowledge_pack_service import get_active_pack_dir

    if get_active_pack_dir():
        ctx, _tool_policy = resolve_knowledge_pack_turn_context(
            user_message=user_message,
            role=role,
            vendor=vendor or "netscaler",
        )
    else:
        ctx = resolve_blueprint_turn_context(
            user_message=user_message,
            role=role,
            vendor=vendor or "netscaler",
            installed=list_installed_skills(),
        )
    if ctx.injection_block:
        system_prompt = f"{system_prompt}\n\n{ctx.injection_block}"
    if ctx.relevant:
        system_prompt = f"{system_prompt}\n\n{BLUEPRINT_FIRST_NUDGE}"
    reviewed = ctx.stack_calibration_reviewed
    if ctx.relevant and ctx.injection_block:
        reviewed = True
    return system_prompt, ctx.relevant, reviewed


def _append_skill_calibration(
    system_prompt: str,
    *,
    user_message: str,
    role: str,
    vendor: str | None,
) -> str:
    prompt, _, _ = _apply_blueprint_context(
        system_prompt,
        user_message=user_message,
        role=role,
        vendor=vendor,
    )
    return prompt


def _architect_effective_system_prompt(
    system_prompt: str,
    user_message: str,
    history: list[dict],
) -> str:
    nudge = build_architect_session_nudge(
        user_message,
        conversation_text=_conversation_text(history, user_message),
    )
    if not nudge:
        return system_prompt
    return f"{system_prompt}\n\n{nudge}"


def _llm_tools_for_turn(
    enabled_tools: list[dict[str, Any]],
    jpilot_role: str | None,
    user_message: str,
    history: list[dict],
    to_tools_fn: Any,
) -> list[dict[str, Any]] | None:
    if not architect_tools_enabled(
        jpilot_role,
        user_message,
        conversation_text=_conversation_text(history, user_message),
    ):
        return None
    return to_tools_fn(enabled_tools)


async def _execute_chat_tool(
    db: AsyncIOMotorDatabase,
    name: str,
    arguments: dict[str, Any],
    appliance_name: str,
    nextgen_memory_reviewed: bool,
    cli_memory_reviewed: bool,
    stack_calibration_reviewed: bool,
    blueprint_relevant: bool,
    *,
    role: str | None,
    vendor: str | None,
    user_message: str,
    history: list[dict],
    tool_traces: list[ToolCallTrace],
) -> tuple[str, bool, bool, bool]:
    blocked = block_architect_tool_during_discovery(
        name,
        role=role,
        user_message=user_message,
        tool_traces=tool_traces,
        conversation_text=_conversation_text(history, user_message),
    )
    if blocked:
        logger.info("tool_call name=%s BLOCKED (architect discovery guard)", name)
        return blocked, nextgen_memory_reviewed, cli_memory_reviewed, stack_calibration_reviewed

    return await _execute_tool_with_memory_gate(
        db,
        name,
        arguments,
        appliance_name,
        nextgen_memory_reviewed,
        cli_memory_reviewed,
        stack_calibration_reviewed,
        blueprint_relevant,
        role=role,
        vendor=vendor,
    )


def _architect_discovery_retry_nudge(
    content: str,
    user_message: str,
    role: str | None,
    vendor: str | None,
    history: list[dict] | None = None,
) -> str | None:
    conversation_parts = [user_message]
    for item in history or []:
        conversation_parts.append(item.get("content") or "")
    conversation_text = "\n".join(conversation_parts)
    return architect_discovery_should_retry(
        content,
        user_message,
        role,
        vendor,
        conversation_text=conversation_text,
    )


def _should_force_tool_execution(
    user_message: str,
    tool_traces: list[ToolCallTrace],
    content: str,
    role: str | None = None,
) -> bool:
    if normalize_role(role) == JPilotRole.ARCHITECT:
        return False

    if content and _response_has_input_form(content):
        return False

    if _user_wants_discovery_first(user_message):
        return bool(content and (_CLI_LISTING_PATTERN.search(content) or _ACTION_CLAIM_PATTERN.search(content)))

    if content and _assistant_is_gathering_requirements(content) and not _had_successful_action(tool_traces):
        return False

    if not _user_requests_config_change(user_message):
        return False
    if _had_successful_action(tool_traces):
        return False
    if content and (_CLI_LISTING_PATTERN.search(content) or _ACTION_CLAIM_PATTERN.search(content)):
        return True
    exec_tools = {trace.name for trace in tool_traces} & WRITE_EXEC_TOOL_NAMES
    if not exec_tools and tool_traces:
        if content and _assistant_is_gathering_requirements(content):
            return False
        return True
    if not tool_traces:
        if _user_wants_discovery_first(user_message):
            return False
        return True
    return False


def _user_confirmed_execution(user_message: str) -> bool:
    lowered = user_message.lower()
    return any(word in lowered for word in _USER_CONFIRM_WORDS)


def _trace_includes_save_ns_config(trace: ToolCallTrace) -> bool:
    arguments = trace.arguments or {}
    if trace.name == "netscaler_run_cli_command":
        return "save ns config" in str(arguments.get("command", "")).lower()
    if trace.name == "netscaler_run_cli_commands":
        commands = arguments.get("commands") or []
        return any("save ns config" in str(command).lower() for command in commands)
    return False


def _classic_config_saved(tool_traces: list[ToolCallTrace]) -> bool:
    for trace in tool_traces:
        if trace.name not in {"netscaler_run_cli_command", "netscaler_run_cli_commands"}:
            continue
        if not _trace_includes_save_ns_config(trace):
            continue
        try:
            payload = json.loads(trace.result)
        except (json.JSONDecodeError, TypeError):
            return True
        if isinstance(payload, dict) and payload.get("success") is False:
            continue
        return True
    return False


def _deployment_may_be_incomplete(
    tool_traces: list[ToolCallTrace],
    user_message: str,
    role: str | None,
) -> bool:
    if normalize_role(role) != JPilotRole.OPERATOR:
        return False

    config_requested = _user_requests_config_change(user_message)
    confirmed = _user_confirmed_execution(user_message)
    state_changing_traces = [trace for trace in tool_traces if trace_is_state_changing(trace)]

    if not config_requested and not confirmed:
        return False
    if confirmed and not config_requested and not state_changing_traces:
        return False
    if not tool_traces:
        return config_requested
    if not had_successful_state_change(tool_traces):
        return config_requested or bool(state_changing_traces)
    if deployment_write_complete(tool_traces):
        return False
    return bool(state_changing_traces)


def _inject_continuation_nudge(messages: list[dict[str, Any]], *, provider: str) -> None:
    if provider == "anthropic":
        messages.append({"role": "user", "content": [{"type": "text", "text": CONTINUATION_NUDGE}]})
        return
    if provider == "gemini":
        messages.append({"role": "user", "parts": [{"text": CONTINUATION_NUDGE}]})
        return
    messages.append({"role": "system", "content": CONTINUATION_NUDGE})


def _had_successful_action(tool_traces: list[ToolCallTrace]) -> bool:
    """True if at least one state-changing tool actually executed successfully this turn."""
    return had_successful_state_change(tool_traces)


_LB_SUCCESS_CLAIM_RE = re.compile(
    r"\b(fully configured|is fully|accepting traffic|both backend.*\bUP\b|vserver.*\bUP\b)\b",
    re.IGNORECASE,
)


def guard_incomplete_lb_success(
    content: str,
    tool_traces: list[ToolCallTrace],
    role: str | None = None,
) -> str:
    """Warn when the reply claims LB success but inventory shows DOWN or zero backends."""
    if normalize_role(role) != JPilotRole.OPERATOR:
        return content
    if not content or not _LB_SUCCESS_CLAIM_RE.search(content):
        return content

    inventory: dict[str, Any] | None = None
    for trace in reversed(tool_traces):
        if trace.name != "netscaler_list_virtual_servers":
            continue
        try:
            payload = json.loads(trace.result)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            inventory = payload["data"]
        elif isinstance(payload, dict):
            inventory = payload
        break

    if not inventory:
        return content

    unhealthy = [
        item
        for item in inventory.get("virtualServers") or []
        if str(item.get("state") or "").upper() == "DOWN"
        or int(item.get("serverCount") or 0) == 0
    ]
    if not unhealthy:
        return content

    names = ", ".join(f"`{item.get('name')}`" for item in unhealthy[:3] if item.get("name"))
    banner = (
        "> ⚠️ **Deployment may be incomplete.** The reply claims success, but inventory shows "
        f"{names or 'a vserver'} DOWN or with zero backends bound. "
        "Finish binding backends and run `save ns config`, then verify with "
        "`netscaler_list_virtual_servers`."
    )
    logger.warning(
        "incomplete_lb_success_guard fired — claimed success but inventory unhealthy (vservers=%s)",
        names,
    )
    return f"{banner}\n\n---\n\n{content}"


def guard_fabricated_execution(
    content: str,
    tool_traces: list[ToolCallTrace],
    role: str | None = None,
) -> str:
    """Prepend a warning when the reply claims a config change that no tool actually performed."""
    if normalize_role(role) == JPilotRole.ARCHITECT:
        return content

    # A successful read-only turn that merely echoes config/log lines is not a fabricated
    # write. When every tool that ran was non-state-changing AND at least one read succeeded,
    # the model is quoting fetched data — do not fire the unexecuted-action banner.
    if (
        tool_traces
        and not any(trace_is_state_changing(t) for t in tool_traces)
        and any(trace_executed_successfully(t) for t in tool_traces)
    ):
        return content

    if _claims_config_change(content) and not _had_successful_action(tool_traces):
        logger.warning(
            "fabricated_execution_guard fired — response claims a config change but no "
            "write/exec tool ran successfully (toolCalls=%d)",
            len(tool_traces),
        )
        return f"{UNEXECUTED_ACTION_BANNER}\n\n---\n\n{content}"
    return content


def guard_unverified_read(
    content: str,
    tool_traces: list[ToolCallTrace],
    role: str | None = None,
) -> str:
    """Prepend a warning when the reply looks like live status data but every tool failed."""
    if normalize_role(role) == JPilotRole.ARCHITECT:
        return content
    if not tool_traces or not (content or "").strip():
        return content
    if any(trace_executed_successfully(trace) for trace in tool_traces):
        return content
    if not _STATUS_ANSWER_PATTERN.search(content):
        return content
    logger.warning(
        "unverified_read_guard fired — response looks like service/status data but all tools failed (toolCalls=%d)",
        len(tool_traces),
    )
    return f"{UNVERIFIED_READ_BANNER}\n\n---\n\n{content}"

def trim_chat_history(history: list[dict], max_messages: int) -> list[dict]:
    if max_messages <= 0 or len(history) <= max_messages:
        return history
    return history[-max_messages:]


def _truncate_tool_result(result: str, max_chars: int) -> str:
    if max_chars <= 0 or len(result) <= max_chars:
        return result
    return result[:max_chars] + "\n...[truncated for context]"


# Idempotent read tools: calling them again with identical args yields identical data, so an
# exact in-turn duplicate can be collapsed to a pointer without losing information (the prior
# result is still in the conversation). Never includes writes/searches/diagnostics.
_DEDUP_READ_TOOLS = frozenset(
    {
        "netscaler_get_system_info",
        "netscaler_test_connection",
        "netscaler_list_applications",
        "netscaler_list_virtual_servers",
        "netscaler_list_virtual_ips",
        "netscaler_list_ip_addresses",
        "netscaler_list_service_status",
        "netscaler_nextgen_get",
        "netscaler_list_inventory",
    }
)


def _dedupe_read_result(
    name: str,
    arguments: dict[str, Any],
    result: str,
    seen: dict[str, str],
    max_chars: int,
) -> str:
    """Truncate a tool result; collapse an exact in-turn duplicate of an idempotent read to a
    short pointer so the same payload isn't re-fed to the model on repeated identical calls."""
    if name in _DEDUP_READ_TOOLS:
        key = f"{name}|{json.dumps(arguments, sort_keys=True, default=str)}"
        if seen.get(key) == result:
            return f"[identical to the earlier `{name}` result in this turn — see above]"
        seen[key] = result
    return _truncate_tool_result(result, max_chars)


# ---------------------------------------------------------------------------
# R1 + R6: Dedicated dry_run plan marker — embed + recover
# ---------------------------------------------------------------------------
# When a dedicated tool (create_*/modify_*/delete_*) runs with dry_run=true and
# succeeds, we embed a hidden HTML comment in the assistant's text response so
# the next affirmation turn can recover the exact tool+args and re-execute with
# confirm=true — without relying on the model to re-derive the call.
# ---------------------------------------------------------------------------

_PLAN_MARKER_PREFIX = "<!-- jpilot-plan: "
_PLAN_MARKER_SUFFIX = " -->"
_PLAN_MARKER_RE = re.compile(
    r"<!--\s*jpilot-plan:\s*([A-Za-z0-9+/=]+)\s*-->", re.IGNORECASE
)

# Dedicated tools that support dry_run → confirm flow (R1/R6).
_DEDICATED_DRY_RUN_TOOLS = frozenset(
    {
        "netscaler_create_lb",
        "netscaler_modify_lb",
        "netscaler_delete_lb",
        "netscaler_create_cs",
        "netscaler_modify_cs",
        "netscaler_delete_cs",
        "netscaler_create_rewrite",
        "netscaler_modify_rewrite",
        "netscaler_delete_rewrite",
        "netscaler_create_responder",
        "netscaler_modify_responder",
        "netscaler_delete_responder",
    }
)


def _embed_dry_run_plan_marker(content: str, tool_traces: list[ToolCallTrace]) -> str:
    """R6: Append a hidden marker to the response when a dedicated dry_run preview ran.

    The marker encodes the tool name + arguments so the next affirmation turn can
    recover them deterministically (R1) and call the same tool with confirm=true.
    """
    for trace in reversed(tool_traces):
        if trace.name not in _DEDICATED_DRY_RUN_TOOLS:
            continue
        args = trace.arguments or {}
        if not args.get("dry_run"):
            continue  # only mark a dry_run preview
        # Verify the dry_run actually produced a non-blocked result
        try:
            payload = json.loads(trace.result)
            if isinstance(payload, dict) and (
                payload.get("blocked") or payload.get("success") is False
            ):
                continue
        except (json.JSONDecodeError, TypeError):
            pass
        # Encode: strip dry_run flag so the confirm call has clean args
        confirm_args = {k: v for k, v in args.items() if k != "dry_run"}
        confirm_args["confirm"] = True
        plan_payload = json.dumps({"tool": trace.name, "args": confirm_args})
        encoded = base64.b64encode(plan_payload.encode("utf-8")).decode("ascii")
        marker = f"{_PLAN_MARKER_PREFIX}{encoded}{_PLAN_MARKER_SUFFIX}"
        return f"{content}\n{marker}" if content else marker
    return content


def _extract_prior_dedicated_plan(history: list[dict]) -> tuple[str, dict] | None:
    """R1: Scan recent history for a dry_run plan marker in the last assistant message.

    Returns (tool_name, arguments_with_confirm_true) or None if not found.
    """
    for item in reversed(history):
        if str(item.get("role") or "").lower() != "assistant":
            continue
        content = str(item.get("content") or "")
        m = _PLAN_MARKER_RE.search(content)
        if m:
            try:
                decoded = base64.b64decode(m.group(1).encode("ascii")).decode("utf-8")
                payload = json.loads(decoded)
                tool = str(payload.get("tool") or "")
                args = dict(payload.get("args") or {})
                if tool in _DEDICATED_DRY_RUN_TOOLS:
                    return tool, args
            except (ValueError, KeyError, json.JSONDecodeError):
                pass
        break  # only check the last assistant message
    return None


# ---------------------------------------------------------------------------
# End R1+R6 helpers
# ---------------------------------------------------------------------------


def _finalize_chat_response(
    content: str,
    *,
    provider_name: str,
    provider_type: str,
    model: str,
    tool_traces: list[ToolCallTrace],
    user_message: str = "",
    role: str | None = None,
    deployment_continuation: DeploymentContinuation | None = None,
) -> ChatResponse:
    if normalize_role(role) == JPilotRole.ARCHITECT:
        content = sanitize_architect_reply(content)
    # R6: embed a hidden plan marker when a dedicated dry_run preview ran, so the next
    # affirmation turn can deterministically recover the tool+args and confirm (R1).
    content = _embed_dry_run_plan_marker(content, tool_traces)
    cleaned, input_form = parse_input_form(content)
    cleaned, input_form = attach_default_lb_form_if_missing(
        user_message, cleaned, input_form, role=role
    )
    return ChatResponse(
        content=cleaned,
        providerName=provider_name,
        providerType=provider_type,
        model=model,
        toolCalls=tool_traces,
        inputForm=to_response_input_form(input_form),
        deploymentContinuation=deployment_continuation,
    )


async def _emit_progress_subtasks(
    progress: QueueChatProgressReporter | None,
    tool_traces: list[ToolCallTrace],
    *,
    role: str | None = None,
    user_message: str = "",
    conversation_text: str = "",
    attachment_names: list[str] | None = None,
    deliverable_ready: bool = False,
) -> None:
    if progress is None:
        return
    bundle = build_progress_subtasks(
        tool_traces,
        role=role,
        user_message=user_message,
        conversation_text=conversation_text,
        attachment_names=attachment_names,
        deliverable_ready=deliverable_ready,
    )
    await progress.subtasks_updated(
        [item.model_dump() for item in bundle.subtasks],
        title=bundle.title,
    )


def _conversation_text(history: list[dict], user_message: str) -> str:
    parts = [user_message]
    for item in history:
        if item.get("role") == "user":
            parts.append(item.get("content") or "")
    return "\n".join(parts)


def _progress_context(
    history: list[dict],
    user_message: str,
    attachments: list[ChatAttachment],
) -> dict[str, Any]:
    return {
        "conversation_text": _conversation_text(history, user_message),
        "attachment_names": [attachment.name for attachment in attachments],
    }


def _maybe_pause_for_long_task(
    orchestration: OrchestrationRuntime,
    *,
    role: str | None,
    user_message: str,
    tool_traces: list[ToolCallTrace],
    continuation_phase: int,
    conversation_text: str = "",
    attachment_names: list[str] | None = None,
) -> bool:
    deployment_incomplete = _deployment_may_be_incomplete(tool_traces, user_message, role)
    if not should_offer_long_task_consent(
        orchestration,
        role=role,
        user_message=user_message,
        tool_traces=tool_traces,
        deployment_incomplete=deployment_incomplete,
        continuation_phase=continuation_phase,
    ):
        return False
    orchestration.request_pause(
        reason="long_task",
        subtasks=build_deployment_subtasks(
            tool_traces,
            role=role,
            user_message=user_message,
            conversation_text=conversation_text,
            attachment_names=attachment_names,
        ),
    )
    return True


def _handle_tool_iteration_limit(
    orchestration: OrchestrationRuntime,
    tool_traces: list[ToolCallTrace],
    user_message: str,
    role: str | None,
    *,
    conversation_text: str = "",
    attachment_names: list[str] | None = None,
) -> str:
    deployment_incomplete = _deployment_may_be_incomplete(tool_traces, user_message, role)
    continuation = continuation_for_tool_limit(
        tool_traces,
        deployment_incomplete=deployment_incomplete,
        role=role,
        user_message=user_message,
        conversation_text=conversation_text,
        attachment_names=attachment_names,
    )
    if continuation is not None:
        orchestration.pause = continuation
        return continuation.message
    return TOOL_ITERATION_LIMIT_MESSAGE


async def _execute_tool_with_memory_gate(
    db: AsyncIOMotorDatabase,
    name: str,
    arguments: dict[str, Any],
    appliance_name: str,
    nextgen_memory_reviewed: bool,
    cli_memory_reviewed: bool,
    stack_calibration_reviewed: bool,
    blueprint_relevant: bool,
    role: str | None = None,
    vendor: str | None = None,
) -> tuple[str, bool, bool, bool]:
    logger.info("tool_call name=%s args=%s", name, json.dumps(arguments, default=str)[:500])

    allowed, blocked = apply_tool_review_gates(
        name,
        blueprint_relevant=blueprint_relevant,
        stack_calibration_reviewed=stack_calibration_reviewed,
        nextgen_memory_reviewed=nextgen_memory_reviewed,
        cli_memory_reviewed=cli_memory_reviewed,
        tool_arguments=arguments,
    )
    if not allowed and blocked:
        logger.info("tool_call name=%s BLOCKED (memory/blueprint review not satisfied)", name)
        return blocked, nextgen_memory_reviewed, cli_memory_reviewed, stack_calibration_reviewed

    if destructive_confirmation_required(name, arguments):
        logger.info("tool_call name=%s BLOCKED (awaiting destructive-op confirmation)", name)
        return (
            block_result_for_unconfirmed_destructive(name, arguments),
            nextgen_memory_reviewed,
            cli_memory_reviewed,
            stack_calibration_reviewed,
        )

    result = await execute_copilot_tool(
        db, name, arguments, default_appliance_name=appliance_name, role=role, vendor=vendor
    )
    logger.info("tool_call name=%s executed result=%s", name, (result or "")[:600])
    if name == MEMORY_SEARCH_TOOL:
        nextgen_memory_reviewed = True
    if name in {
        CLI_MEMORY_SEARCH_TOOL,
        CISCO_CLI_MEMORY_SEARCH_TOOL,
        SDX_CLI_MEMORY_SEARCH_TOOL,
        F5_CLI_MEMORY_SEARCH_TOOL,
    }:
        cli_memory_reviewed = True
    if name == STACK_CALIBRATION_MEMORY_TOOL:
        stack_calibration_reviewed = True
    return result, nextgen_memory_reviewed, cli_memory_reviewed, stack_calibration_reviewed


async def resolve_appliance_vendor(db: AsyncIOMotorDatabase, appliance_name: str) -> str:
    if not appliance_name:
        return "netscaler"
    appliance = await db.appliances.find_one({"name": appliance_name})
    if appliance is None:
        return "netscaler"
    return str(appliance.get("vendor") or "netscaler")


async def get_default_provider(db: AsyncIOMotorDatabase, role: str | None = None) -> dict | None:
    from app.models.ai_provider import provider_supports_role

    providers = await db.aiProviders.find({"enabled": True}).sort("providerName", 1).to_list(length=None)
    if role:
        providers = [provider for provider in providers if provider_supports_role(provider, role)]
    if not providers:
        return None
    for provider in providers:
        if provider.get("isDefault"):
            return provider
    return providers[0]


async def resolve_chat_provider(
    db: AsyncIOMotorDatabase,
    provider_id: str | None,
    role: str | None = None,
) -> dict | None:
    """Pick the provider for this chat: explicit choice, else role-matched default."""
    if provider_id:
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            chosen = await db.aiProviders.find_one(
                {"_id": ObjectId(provider_id), "enabled": True}
            )
        except (InvalidId, TypeError):
            chosen = None
        if chosen is not None:
            return chosen
    return await get_default_provider(db, role=role)


async def run_copilot_chat(
    db: AsyncIOMotorDatabase,
    user_message: str,
    history: list[dict],
    attachments: list[ChatAttachment] | None = None,
    settings: CopilotSettings | None = None,
    appliance_name: str = "",
    provider_id: str | None = None,
    web_search: bool = True,
    role: str | None = None,
    request: Request | None = None,
    progress: QueueChatProgressReporter | None = None,
    deployment_continuation: bool = False,
    long_task_approved: bool = False,
    design_document_context: str | None = None,
    include_design_revision: bool = False,
    persona_system_prompt: str | None = None,
) -> ChatResponse:
    from app.services.copilot_service import set_web_search_allowed

    set_web_search_allowed(web_search)
    await raise_if_chat_cancelled(request)
    provider = await resolve_chat_provider(db, provider_id, role=role)
    if provider is None:
        raise ValueError("No enabled AI provider configured. Add one and set it as default.")

    chat_settings = settings or CopilotSettings()
    attachment_list = attachments or []
    validate_attachments(attachment_list, chat_settings)

    if not user_message.strip() and not attachment_list:
        raise ValueError("Message or attachments are required")

    api_key = decrypt_value(provider["encryptedApiKey"])
    provider_type = provider["providerType"]
    model = provider["model"]
    endpoint = provider.get("endpoint", "")

    chat_role = normalize_role(role)

    if chat_role == JPilotRole.ARCHITECT and design_document_context:
        from app.services.copilot_architect_discovery import append_architect_panel_context

        user_message = append_architect_panel_context(
            user_message,
            design_document_context,
            include_revision=include_design_revision,
        )

    appliance_vendor = await resolve_appliance_vendor(db, appliance_name)
    chat_vendor = resolve_chat_vendor(
        appliance_vendor=appliance_vendor,
        role=chat_role.value,
        appliance_name=appliance_name,
    )
    tool_traces: list[ToolCallTrace] = []
    enabled_tools = await get_enabled_copilot_tools(
        db,
        role=chat_role.value,
        vendor=chat_vendor,
    )
    enabled_tools = route_copilot_tools(
        enabled_tools,
        role=chat_role.value,
        user_message=user_message,
        attachment_names=[a.name for a in attachment_list],
        vendor=chat_vendor,
    )
    enabled_tool_names = {tool["name"] for tool in enabled_tools}
    logger.info(
        "copilot_tools role=%s vendor=%s appliance_vendor=%s routed=%d names=%s",
        chat_role.value,
        chat_vendor,
        appliance_vendor,
        len(enabled_tools),
        sorted(enabled_tool_names),
    )
    if appliance_name and not copilot_vendor_is_supported(appliance_vendor) and chat_role != JPilotRole.ARCHITECT:
        raise ValueError(
            f"JPilot chat for Operator/Analyst is not yet available for vendor '{appliance_vendor}'. "
            "Connect a supported appliance or use Architect role for planning."
        )
    system_prompt = build_system_prompt(chat_role, appliance_name, vendor=chat_vendor)
    # Layer the custom persona's system prompt on top of the base role prompt.
    if persona_system_prompt and persona_system_prompt.strip():
        system_prompt = f"{system_prompt}\n\n## Custom Persona Instructions\n{persona_system_prompt.strip()}"
    system_prompt, blueprint_relevant, stack_calibration_reviewed = _apply_blueprint_context(
        system_prompt,
        user_message=user_message,
        role=chat_role.value,
        vendor=chat_vendor,
    )
    from app.services.copilot_platform_service import ensure_default_settings

    await ensure_default_settings(db)
    platform_doc = await db.copilotPlatformSettings.find_one({"_id": "default"}) or {}
    orchestration = build_orchestration_runtime(
        settings=orchestration_settings_from_document(platform_doc),
        user_message=user_message,
        deployment_continuation=deployment_continuation,
        long_task_approved=long_task_approved,
    )
    if orchestration.long_task_approved and chat_role == JPilotRole.OPERATOR:
        system_prompt += f"\n\n{CONTINUATION_NUDGE}"
    attachment_names = [a.name for a in attachment_list]
    if (
        chat_role == JPilotRole.OPERATOR
        and appliance_name
        and user_requests_design_implementation(user_message, attachment_names)
    ):
        from app.services.copilot_roles import operator_design_implementation_suffix

        system_prompt += "\n" + operator_design_implementation_suffix(appliance_name, vendor=chat_vendor)
    ctx_limits = resolve_context_limits(model, provider_type)
    history = trim_chat_history(history, ctx_limits.max_history_messages)

    if progress is not None:
        await progress.status(phase="preparing", label="Preparing request…")

    from app.services.copilot_deploy import (
        detect_natural_language_lb_request,
        format_classic_lb_plan,
        parse_natural_language_lb_request,
        try_auto_create_application,
        try_auto_deploy_classic_lb,
        try_auto_deploy_http_lb,
        try_auto_deploy_lb_from_message,
    )
    from app.services.copilot_remove import (
        detect_lb_removal_request,
        format_lb_removal_plan,
        parse_lb_removal_targets,
        try_auto_remove_lb_targets,
    )
    from app.services.copilot_form import is_affirmation, is_form_submission, last_user_message
    from app.services.copilot_port_check import try_auto_appliance_internet_check, try_auto_tcp_port_check
    from app.services.copilot_inventory import try_auto_ip_inventory
    from app.services.copilot_service_status import try_auto_service_status

    auto_traces: list[ToolCallTrace] = []
    auto_response = None
    if appliance_name and role_requires_appliance(chat_role):
        if is_form_submission(user_message):
            auto_traces, auto_response = await try_auto_deploy_http_lb(
                db,
                user_message=user_message,
                appliance_name=appliance_name,
                enabled_tool_names=enabled_tool_names,
            )
            if not auto_traces:
                auto_traces, auto_response = await try_auto_create_application(
                    db,
                    user_message=user_message,
                    appliance_name=appliance_name,
                    enabled_tool_names=enabled_tool_names,
                )
            if not auto_traces:
                auto_traces, auto_response = await try_auto_deploy_classic_lb(
                    db,
                    user_message=user_message,
                    appliance_name=appliance_name,
                    enabled_tool_names=enabled_tool_names,
                )
        else:
            # Confirm-before-mutate gate: mutating auto-paths (deploy/remove) bypass the
            # LLM and write directly, so prompt rules can't gate them. On first contact we
            # present a plan and wait; a short "yes" confirms and we recover the original
            # request from the prior user turn, then execute. Read-only auto-paths are
            # never gated.
            confirmed = is_affirmation(user_message)
            effective_msg = last_user_message(history) if confirmed else user_message
            provider_name = provider["providerName"]

            # R1: On a short affirmation turn, check whether the prior assistant reply
            # contained a hidden dry_run plan marker (R6). If so, re-execute the same
            # dedicated tool with confirm=true (deterministic recovery — no model
            # re-derivation needed), mirroring the copilot_deploy confirm recovery path.
            if confirmed:
                prior_plan = _extract_prior_dedicated_plan(history)
                if prior_plan is not None:
                    plan_tool_name, plan_args = prior_plan
                    # Inject the appliance name if the stored plan carries a placeholder
                    if appliance_name and not plan_args.get("appliance_name"):
                        plan_args = {**plan_args, "appliance_name": appliance_name}
                    logger.info(
                        "r1_confirm_dedicated_plan tool=%s args=%s",
                        plan_tool_name,
                        json.dumps(plan_args, default=str)[:400],
                    )
                    try:
                        confirm_result, _, _, _ = await _execute_tool_with_memory_gate(
                            db,
                            plan_tool_name,
                            plan_args,
                            appliance_name,
                            True,   # nextgen_memory_reviewed — dedicated tools don't need search
                            True,   # cli_memory_reviewed
                            stack_calibration_reviewed,
                            blueprint_relevant,
                            role=chat_role.value,
                            vendor=chat_vendor,
                        )
                    except Exception as exc:
                        logger.exception("r1_confirm_dedicated_plan tool=%s failed", plan_tool_name)
                        confirm_result = json.dumps({"success": False, "errorMessage": str(exc)})
                    auto_traces.append(
                        ToolCallTrace(name=plan_tool_name, arguments=plan_args, result=confirm_result)
                    )
                    try:
                        result_payload = json.loads(confirm_result)
                        if isinstance(result_payload, dict) and result_payload.get("success") is False:
                            confirm_summary = (
                                f"**{plan_tool_name} failed.** "
                                + (result_payload.get("errorMessage") or result_payload.get("message") or "")
                            )
                        else:
                            confirm_summary = f"**Configuration applied** via `{plan_tool_name}`."
                    except (json.JSONDecodeError, TypeError):
                        confirm_summary = f"**Configuration applied** via `{plan_tool_name}`."
                    tool_traces.extend(auto_traces)
                    return _finalize_chat_response(
                        confirm_summary,
                        provider_name=provider_name,
                        provider_type=provider_type,
                        model=model,
                        tool_traces=tool_traces,
                        user_message=user_message,
                        role=chat_role.value,
                    )

            lb_fields = parse_natural_language_lb_request(effective_msg)
            if detect_natural_language_lb_request(effective_msg, lb_fields):
                if not confirmed:
                    # First contact → present the deploy plan, perform no writes.
                    return _finalize_chat_response(
                        format_classic_lb_plan(appliance_name, lb_fields),
                        provider_name=provider_name,
                        provider_type=provider_type,
                        model=model,
                        tool_traces=tool_traces,
                        user_message=user_message,
                        role=chat_role.value,
                    )
                auto_traces, auto_response = await try_auto_deploy_lb_from_message(
                    db,
                    user_message=effective_msg,
                    appliance_name=appliance_name,
                    enabled_tool_names=enabled_tool_names,
                )
                tool_traces.extend(auto_traces)
                return _finalize_chat_response(
                    auto_response
                    or "**Classic LB deploy failed** — no response was produced. Check MCP tool enablement.",
                    provider_name=provider_name,
                    provider_type=provider_type,
                    model=model,
                    tool_traces=tool_traces,
                    user_message=user_message,
                    role=chat_role.value,
                )

            if detect_lb_removal_request(effective_msg):
                if not confirmed:
                    # First contact → present the removal plan, perform no deletes.
                    return _finalize_chat_response(
                        format_lb_removal_plan(
                            appliance_name, parse_lb_removal_targets(effective_msg)
                        ),
                        provider_name=provider_name,
                        provider_type=provider_type,
                        model=model,
                        tool_traces=tool_traces,
                        user_message=user_message,
                        role=chat_role.value,
                    )
                auto_traces, auto_response = await try_auto_remove_lb_targets(
                    db,
                    user_message=effective_msg,
                    appliance_name=appliance_name,
                    enabled_tool_names=enabled_tool_names,
                )

            # Read-only auto-paths — never gated, only on the original (non-confirmation) turn.
            if not auto_traces and not confirmed:
                auto_traces, auto_response = await try_auto_service_status(
                    db,
                    user_message=user_message,
                    appliance_name=appliance_name,
                    enabled_tool_names=enabled_tool_names,
                )
            if not auto_traces and not confirmed:
                auto_traces, auto_response = await try_auto_ip_inventory(
                    db,
                    user_message=user_message,
                    appliance_name=appliance_name,
                    enabled_tool_names=enabled_tool_names,
                )
            if not auto_traces and not confirmed:
                auto_traces, auto_response = await try_auto_appliance_internet_check(
                    db,
                    user_message=user_message,
                    appliance_name=appliance_name,
                    enabled_tool_names=enabled_tool_names,
                )
            if not auto_traces and not confirmed:
                auto_traces, auto_response = await try_auto_tcp_port_check(
                    db,
                    user_message=user_message,
                    appliance_name=appliance_name,
                    enabled_tool_names=enabled_tool_names,
                )
    if auto_traces:
        tool_traces.extend(auto_traces)
    if auto_response and auto_traces:
        provider_name = provider["providerName"]
        if auto_response.startswith("**") and (
            "Verdict:" in auto_response
            or "Internet access" in auto_response
            or "IP address(es)" in auto_response
            or "DOWN backend" in auto_response
            or "no DOWN backend" in auto_response
            or "created via Next-Gen API" in auto_response
            or "classic load balancer" in auto_response
            or "Classic LB deploy failed" in auto_response
            or "removed load balancer" in auto_response
            or "LB removal failed" in auto_response
            or "No matching load balancers found" in auto_response
            or "Application create failed" in auto_response
            or "Configuration form received" in auto_response
        ):
            return _finalize_chat_response(
                auto_response,
                provider_name=provider_name,
                provider_type=provider_type,
                model=model,
                tool_traces=tool_traces,
                user_message=user_message,
            )
        system_prompt += auto_response

    provider_name = provider["providerName"]
    provider_id_str = str(provider["_id"])
    usage_accumulator = UsageAccumulator()

    if provider_type == "Anthropic":
        content = await _run_anthropic_loop(
            db,
            api_key,
            model,
            user_message,
            history,
            tool_traces,
            attachment_list,
            enabled_tools,
            system_prompt,
            appliance_name,
            provider_type,
            provider_name,
            usage_accumulator,
            jpilot_role=chat_role.value,
            chat_vendor=chat_vendor,
            request=request,
            context_limits=ctx_limits,
            progress=progress,
            orchestration=orchestration,
            blueprint_relevant=blueprint_relevant,
            stack_calibration_reviewed=stack_calibration_reviewed,
        )
    elif provider_type == "Gemini":
        content = await _run_gemini_loop(
            db,
            api_key,
            model,
            user_message,
            history,
            tool_traces,
            attachment_list,
            enabled_tools,
            system_prompt,
            appliance_name,
            provider_type,
            provider_name,
            usage_accumulator,
            jpilot_role=chat_role.value,
            chat_vendor=chat_vendor,
            request=request,
            context_limits=ctx_limits,
            progress=progress,
            orchestration=orchestration,
            blueprint_relevant=blueprint_relevant,
            stack_calibration_reviewed=stack_calibration_reviewed,
        )
    elif provider_type in OPENAI_COMPAT_CHAT_PROVIDER_TYPES:
        if provider_type == "LM Studio":
            lm_base_urls = lm_studio_endpoint_candidates(endpoint.strip())
            base_url = lm_base_urls[0]
            base_url_candidates = lm_base_urls
        elif provider_type == "AWS Bedrock":
            base_url = resolve_bedrock_openai_base(endpoint.strip())
            base_url_candidates = None
        elif provider_type == "Azure OpenAI":
            base_url = normalize_azure_resource_endpoint(endpoint.strip())
            base_url_candidates = None
        else:
            base_url = resolve_base_url(provider_type, endpoint)
            base_url_candidates = None
        content = await _run_openai_loop(
            db,
            base_url,
            api_key,
            model,
            user_message,
            history,
            tool_traces,
            attachment_list,
            enabled_tools,
            system_prompt,
            appliance_name,
            base_url_candidates,
            provider_type,
            provider_name,
            usage_accumulator,
            jpilot_role=chat_role.value,
            chat_vendor=chat_vendor,
            request=request,
            endpoint=endpoint,
            context_limits=ctx_limits,
            progress=progress,
            orchestration=orchestration,
            blueprint_relevant=blueprint_relevant,
            stack_calibration_reviewed=stack_calibration_reviewed,
        )
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")

    await flush_usage_accumulator(db, provider_id_str, usage_accumulator)
    if usage_accumulator.requests == 0 and (content or "").strip():
        await record_provider_usage(db, provider_id=provider_id_str, tokens=0, requests=1)

    logger.info(
        "chat_complete provider=%s model=%s toolCalls=%d names=%s",
        provider_type,
        model,
        len(tool_traces),
        [t.name for t in tool_traces],
    )
    if not tool_traces:
        logger.warning(
            "chat_complete produced an answer with ZERO tool calls — if it claims it changed "
            "the appliance, the model fabricated execution (no MCP tool ran). provider=%s model=%s",
            provider_type,
            model,
        )

    content = guard_fabricated_execution(content, tool_traces, role=chat_role.value)
    content = guard_incomplete_lb_success(content, tool_traces, role=chat_role.value)
    content = guard_unverified_read(content, tool_traces, role=chat_role.value)
    if orchestration.pause is not None:
        content = orchestration.pause.message

    if progress is not None and normalize_role(chat_role) == JPilotRole.ARCHITECT:
        await _emit_progress_subtasks(
            progress,
            tool_traces,
            role=chat_role.value,
            conversation_text=_conversation_text(history, user_message),
            deliverable_ready=deliverable_ready_from_content(content),
        )

    return _finalize_chat_response(
        content,
        provider_name=provider["providerName"],
        provider_type=provider_type,
        model=model,
        tool_traces=tool_traces,
        user_message=user_message,
        role=chat_role.value,
        deployment_continuation=orchestration.pause,
    )


async def _run_openai_loop(
    db: AsyncIOMotorDatabase,
    base_url: str,
    api_key: str,
    model: str,
    user_message: str,
    history: list[dict],
    tool_traces: list[ToolCallTrace],
    attachments: list[ChatAttachment],
    enabled_tools: list[dict[str, Any]],
    system_prompt: str,
    appliance_name: str,
    base_url_candidates: list[str] | None = None,
    provider_type: str = "OpenAI-Compatible",
    provider_name: str = "",
    usage_accumulator: UsageAccumulator | None = None,
    jpilot_role: str | None = None,
    chat_vendor: str | None = None,
    request: Request | None = None,
    endpoint: str = "",
    context_limits: ContextLimits | None = None,
    progress: QueueChatProgressReporter | None = None,
    orchestration: OrchestrationRuntime | None = None,
    blueprint_relevant: bool = False,
    stack_calibration_reviewed: bool = True,
) -> str:
    limits = context_limits or resolve_context_limits(model, provider_type)
    runtime = orchestration or OrchestrationRuntime(
        settings=orchestration_settings_from_document({}),
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _architect_effective_system_prompt(system_prompt, user_message, history)}
    ]
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append(
        {
            "role": "user",
            "content": build_openai_user_content(user_message, attachments),
        }
    )

    active_tools = _llm_tools_for_turn(enabled_tools, jpilot_role, user_message, history, to_openai_tools)
    active_base_url = base_url
    fallback_candidates = base_url_candidates
    from app.services.copilot_deploy import detect_nextgen_application_form_submission

    nextgen_memory_reviewed = detect_nextgen_application_form_submission(user_message)
    cli_memory_reviewed = False
    blueprint_reviewed = stack_calibration_reviewed
    progress_ctx = _progress_context(history, user_message, attachments)
    seen_reads: dict[str, str] = {}  # in-turn idempotent-read dedup (8e)

    for continuation_phase in range(runtime.max_continuation_phases + 1):
        if continuation_phase > 0:
            if _maybe_pause_for_long_task(
                runtime,
                role=jpilot_role,
                user_message=user_message,
                tool_traces=tool_traces,
                continuation_phase=continuation_phase,
                **progress_ctx,
            ):
                break
            logger.info(
                "tool_continuation phase=%d toolCalls=%d",
                continuation_phase,
                len(tool_traces),
            )
            _inject_continuation_nudge(messages, provider="openai")

        paused = False
        for _ in range(runtime.max_tool_iterations):
            runtime.tool_rounds += 1
            await raise_if_chat_cancelled(request)
            if progress is not None:
                await progress.llm_started()
            llm_started_at = time.perf_counter()
            data, active_base_url = await chat_openai_compatible(
                base_url=active_base_url,
                api_key=api_key,
                model=model,
                messages=messages,
                tools=active_tools,
                base_url_candidates=fallback_candidates,
                provider_type=provider_type,
                provider_name=provider_name,
                endpoint=endpoint,
            )
            if progress is not None:
                await progress.llm_finished(
                    duration_ms=int((time.perf_counter() - llm_started_at) * 1000),
                    provider_type=provider_type,
                    data=data,
                )
            fallback_candidates = None
            if usage_accumulator is not None:
                usage_accumulator.add_llm_response(provider_type, data)
            choice = data["choices"][0]["message"]
            tool_calls = choice.get("tool_calls") or []

            if not tool_calls:
                content = sanitize_architect_reply(choice.get("content") or "")
                architect_nudge = _architect_discovery_retry_nudge(
                    content, user_message, jpilot_role, chat_vendor, history
                )
                if architect_nudge:
                    logger.warning("architect_discovery_nudge — checklist or missing jpilot-form")
                    if content.strip():
                        messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "system", "content": architect_nudge})
                    continue
                if _should_force_tool_execution(user_message, tool_traces, content, role=jpilot_role):
                    logger.warning(
                        "execution_nudge — model replied without running write tools; forcing another iteration"
                    )
                    if content.strip():
                        messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "system", "content": FORCE_TOOL_EXECUTION_MESSAGE})
                    continue
                return content or "I couldn't generate a response."

            messages.append(choice)

            retry_hints: list[str] = []
            for tool_call in tool_calls:
                fn = tool_call.get("function") or {}
                name = fn.get("name") or ""
                raw_arguments = fn.get("arguments") or "{}"
                try:
                    arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else dict(raw_arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}
                try:
                    if progress is not None:
                        await progress.tool_started(name)
                    result, nextgen_memory_reviewed, cli_memory_reviewed, blueprint_reviewed = await _execute_chat_tool(
                        db,
                        name,
                        arguments,
                        appliance_name,
                        nextgen_memory_reviewed,
                        cli_memory_reviewed,
                        blueprint_reviewed,
                        blueprint_relevant,
                        role=jpilot_role,
                        vendor=chat_vendor,
                        user_message=user_message,
                        history=history,
                        tool_traces=tool_traces,
                    )
                    if progress is not None:
                        await progress.tool_finished(name)
                except Exception as exc:
                    logger.exception("tool_call name=%s failed", name)
                    result = json.dumps({"success": False, "errorMessage": str(exc)})

                tool_traces.append(ToolCallTrace(name=name, arguments=arguments, result=result))
                loop_break = check_loop_breakers(runtime, name=name, arguments=arguments, result=result)
                if loop_break is not None:
                    return loop_break.message
                tool_call_id = tool_call.get("id") or f"call_{len(tool_traces)}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": _dedupe_read_result(name, arguments, result, seen_reads, limits.max_tool_result_chars),
                    }
                )
                retry_hint = build_tool_retry_hint(
                    name, result, user_message, [a.name for a in attachments]
                )
                if retry_hint:
                    retry_hints.append(retry_hint)

            if retry_hints:
                messages.append({"role": "system", "content": "\n\n".join(retry_hints)})

            await _emit_progress_subtasks(
                progress,
                tool_traces,
                role=jpilot_role,
                user_message=user_message,
                **progress_ctx,
            )
            if _maybe_pause_for_long_task(
                runtime,
                role=jpilot_role,
                user_message=user_message,
                tool_traces=tool_traces,
                continuation_phase=continuation_phase,
                **progress_ctx,
            ):
                paused = True
                break

        if paused or runtime.pause is not None:
            break
        if continuation_phase >= runtime.max_continuation_phases:
            break
        if not _deployment_may_be_incomplete(tool_traces, user_message, jpilot_role):
            break

    return _handle_tool_iteration_limit(
        runtime,
        tool_traces,
        user_message,
        jpilot_role,
        **progress_ctx,
    )


async def _run_gemini_loop(
    db: AsyncIOMotorDatabase,
    api_key: str,
    model: str,
    user_message: str,
    history: list[dict],
    tool_traces: list[ToolCallTrace],
    attachments: list[ChatAttachment],
    enabled_tools: list[dict[str, Any]],
    system_prompt: str,
    appliance_name: str,
    provider_type: str = "Gemini",
    provider_name: str = "",
    usage_accumulator: UsageAccumulator | None = None,
    jpilot_role: str | None = None,
    chat_vendor: str | None = None,
    request: Request | None = None,
    context_limits: ContextLimits | None = None,
    progress: QueueChatProgressReporter | None = None,
    orchestration: OrchestrationRuntime | None = None,
    blueprint_relevant: bool = False,
    stack_calibration_reviewed: bool = True,
) -> str:
    limits = context_limits or resolve_context_limits(model, provider_type)
    runtime = orchestration or OrchestrationRuntime(
        settings=orchestration_settings_from_document({}),
    )
    contents: list[dict[str, Any]] = []
    for item in history:
        gemini_role = "model" if item["role"] == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": item["content"]}]})
    contents.append(
        {
            "role": "user",
            "parts": build_gemini_user_parts(user_message, attachments),
        }
    )

    active_tools = _llm_tools_for_turn(enabled_tools, jpilot_role, user_message, history, to_gemini_tools)
    from app.services.copilot_deploy import detect_nextgen_application_form_submission

    nextgen_memory_reviewed = detect_nextgen_application_form_submission(user_message)
    cli_memory_reviewed = False
    blueprint_reviewed = stack_calibration_reviewed
    progress_ctx = _progress_context(history, user_message, attachments)
    seen_reads: dict[str, str] = {}  # in-turn idempotent-read dedup (8e)

    for continuation_phase in range(runtime.max_continuation_phases + 1):
        if continuation_phase > 0:
            if _maybe_pause_for_long_task(
                runtime,
                role=jpilot_role,
                user_message=user_message,
                tool_traces=tool_traces,
                continuation_phase=continuation_phase,
                **progress_ctx,
            ):
                break
            logger.info(
                "tool_continuation phase=%d toolCalls=%d",
                continuation_phase,
                len(tool_traces),
            )
            _inject_continuation_nudge(contents, provider="gemini")

        paused = False
        for _ in range(runtime.max_tool_iterations):
            runtime.tool_rounds += 1
            await raise_if_chat_cancelled(request)
            if progress is not None:
                await progress.llm_started()
            llm_started_at = time.perf_counter()
            data = await chat_gemini(
                api_key=api_key,
                model=model,
                system=_architect_effective_system_prompt(system_prompt, user_message, history),
                contents=contents,
                tools=active_tools,
                provider_name=provider_name,
            )
            if progress is not None:
                await progress.llm_finished(
                    duration_ms=int((time.perf_counter() - llm_started_at) * 1000),
                    provider_type=provider_type,
                    data=data,
                )
            if usage_accumulator is not None:
                usage_accumulator.add_llm_response(provider_type, data)

            candidate = (data.get("candidates") or [{}])[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            function_calls = [part["functionCall"] for part in parts if part.get("functionCall")]
            text_parts = [part.get("text", "") for part in parts if part.get("text")]

            if not function_calls:
                content = sanitize_architect_reply("\n".join(text_parts).strip())
                architect_nudge = _architect_discovery_retry_nudge(
                    content, user_message, jpilot_role, chat_vendor, history
                )
                if architect_nudge:
                    logger.warning("architect_discovery_nudge — checklist or missing jpilot-form")
                    if content:
                        contents.append({"role": "model", "parts": [{"text": content}]})
                    contents.append({"role": "user", "parts": [{"text": architect_nudge}]})
                    continue
                if _should_force_tool_execution(user_message, tool_traces, content, role=jpilot_role):
                    logger.warning(
                        "execution_nudge — model replied without running write tools; forcing another iteration"
                    )
                    if content:
                        contents.append({"role": "model", "parts": [{"text": content}]})
                    contents.append({"role": "user", "parts": [{"text": FORCE_TOOL_EXECUTION_MESSAGE}]})
                    continue
                return content or "I couldn't generate a response."

            contents.append({"role": "model", "parts": parts})

            response_parts = []
            for function_call in function_calls:
                name = function_call["name"]
                arguments = function_call.get("args", {})
                if progress is not None:
                    await progress.tool_started(name)
                result, nextgen_memory_reviewed, cli_memory_reviewed, blueprint_reviewed = await _execute_chat_tool(
                    db,
                    name,
                    arguments,
                    appliance_name,
                    nextgen_memory_reviewed,
                    cli_memory_reviewed,
                    blueprint_reviewed,
                    blueprint_relevant,
                    role=jpilot_role,
                    vendor=chat_vendor,
                    user_message=user_message,
                    history=history,
                    tool_traces=tool_traces,
                )
                if progress is not None:
                    await progress.tool_finished(name)
                tool_traces.append(ToolCallTrace(name=name, arguments=arguments, result=result))
                loop_break = check_loop_breakers(runtime, name=name, arguments=arguments, result=result)
                if loop_break is not None:
                    return loop_break.message
                truncated = _dedupe_read_result(name, arguments, result, seen_reads, limits.max_tool_result_chars)
                response_parts.append(
                    {
                        "functionResponse": {
                            "name": name,
                            "response": {"result": truncated},
                        }
                    }
                )
                retry_hint = build_tool_retry_hint(
                    name, result, user_message, [a.name for a in attachments]
                )
                if retry_hint:
                    response_parts.append({"text": retry_hint})

            contents.append({"role": "user", "parts": response_parts})

            await _emit_progress_subtasks(
                progress,
                tool_traces,
                role=jpilot_role,
                user_message=user_message,
                **progress_ctx,
            )
            if _maybe_pause_for_long_task(
                runtime,
                role=jpilot_role,
                user_message=user_message,
                tool_traces=tool_traces,
                continuation_phase=continuation_phase,
                **progress_ctx,
            ):
                paused = True
                break

        if paused or runtime.pause is not None:
            break
        if continuation_phase >= runtime.max_continuation_phases:
            break
        if not _deployment_may_be_incomplete(tool_traces, user_message, jpilot_role):
            break

    return _handle_tool_iteration_limit(
        runtime,
        tool_traces,
        user_message,
        jpilot_role,
        **progress_ctx,
    )


async def _run_anthropic_loop(
    db: AsyncIOMotorDatabase,
    api_key: str,
    model: str,
    user_message: str,
    history: list[dict],
    tool_traces: list[ToolCallTrace],
    attachments: list[ChatAttachment],
    enabled_tools: list[dict[str, Any]],
    system_prompt: str,
    appliance_name: str,
    provider_type: str = "Anthropic",
    provider_name: str = "",
    usage_accumulator: UsageAccumulator | None = None,
    jpilot_role: str | None = None,
    chat_vendor: str | None = None,
    request: Request | None = None,
    context_limits: ContextLimits | None = None,
    progress: QueueChatProgressReporter | None = None,
    orchestration: OrchestrationRuntime | None = None,
    blueprint_relevant: bool = False,
    stack_calibration_reviewed: bool = True,
) -> str:
    limits = context_limits or resolve_context_limits(model, provider_type)
    runtime = orchestration or OrchestrationRuntime(
        settings=orchestration_settings_from_document({}),
    )
    messages: list[dict[str, Any]] = []
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append(
        {
            "role": "user",
            "content": build_anthropic_user_content(user_message, attachments),
        }
    )

    active_tools = _llm_tools_for_turn(enabled_tools, jpilot_role, user_message, history, to_anthropic_tools)
    from app.services.copilot_deploy import detect_nextgen_application_form_submission

    nextgen_memory_reviewed = detect_nextgen_application_form_submission(user_message)
    cli_memory_reviewed = False
    blueprint_reviewed = stack_calibration_reviewed
    progress_ctx = _progress_context(history, user_message, attachments)
    seen_reads: dict[str, str] = {}  # in-turn idempotent-read dedup (8e)

    for continuation_phase in range(runtime.max_continuation_phases + 1):
        if continuation_phase > 0:
            if _maybe_pause_for_long_task(
                runtime,
                role=jpilot_role,
                user_message=user_message,
                tool_traces=tool_traces,
                continuation_phase=continuation_phase,
                **progress_ctx,
            ):
                break
            logger.info(
                "tool_continuation phase=%d toolCalls=%d",
                continuation_phase,
                len(tool_traces),
            )
            _inject_continuation_nudge(messages, provider="anthropic")

        paused = False
        for _ in range(runtime.max_tool_iterations):
            runtime.tool_rounds += 1
            await raise_if_chat_cancelled(request)
            if progress is not None:
                await progress.llm_started()
            llm_started_at = time.perf_counter()
            data = await chat_anthropic(
                api_key=api_key,
                model=model,
                system=_architect_effective_system_prompt(system_prompt, user_message, history),
                messages=messages,
                tools=active_tools,
                provider_name=provider_name,
            )
            if progress is not None:
                await progress.llm_finished(
                    duration_ms=int((time.perf_counter() - llm_started_at) * 1000),
                    provider_type=provider_type,
                    data=data,
                )
            if usage_accumulator is not None:
                usage_accumulator.add_llm_response(provider_type, data)

            content_blocks = data.get("content", [])
            tool_uses = [block for block in content_blocks if block.get("type") == "tool_use"]
            text_blocks = [block.get("text", "") for block in content_blocks if block.get("type") == "text"]
            stop_reason = data.get("stop_reason")

            if stop_reason != "tool_use" and not tool_uses:
                content = sanitize_architect_reply("\n".join(text_blocks).strip())
                architect_nudge = _architect_discovery_retry_nudge(
                    content, user_message, jpilot_role, chat_vendor, history
                )
                if architect_nudge:
                    logger.warning("architect_discovery_nudge — checklist or missing jpilot-form")
                    if content:
                        messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": [{"type": "text", "text": architect_nudge}]})
                    continue
                if _should_force_tool_execution(user_message, tool_traces, content, role=jpilot_role):
                    logger.warning(
                        "execution_nudge — model replied without running write tools; forcing another iteration"
                    )
                    if content_blocks:
                        messages.append({"role": "assistant", "content": content_blocks})
                    messages.append({"role": "user", "content": [{"type": "text", "text": FORCE_TOOL_EXECUTION_MESSAGE}]})
                    continue
                return content or "I couldn't generate a response."

            messages.append({"role": "assistant", "content": content_blocks})

            tool_results = []
            for tool_use in tool_uses:
                name = tool_use["name"]
                arguments = tool_use.get("input", {})
                if progress is not None:
                    await progress.tool_started(name)
                result, nextgen_memory_reviewed, cli_memory_reviewed, blueprint_reviewed = await _execute_chat_tool(
                    db,
                    name,
                    arguments,
                    appliance_name,
                    nextgen_memory_reviewed,
                    cli_memory_reviewed,
                    blueprint_reviewed,
                    blueprint_relevant,
                    role=jpilot_role,
                    vendor=chat_vendor,
                    user_message=user_message,
                    history=history,
                    tool_traces=tool_traces,
                )
                if progress is not None:
                    await progress.tool_finished(name)
                tool_traces.append(ToolCallTrace(name=name, arguments=arguments, result=result))
                loop_break = check_loop_breakers(runtime, name=name, arguments=arguments, result=result)
                if loop_break is not None:
                    return loop_break.message
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use["id"],
                        "content": _dedupe_read_result(name, arguments, result, seen_reads, limits.max_tool_result_chars),
                    }
                )
                retry_hint = build_tool_retry_hint(
                    name, result, user_message, [a.name for a in attachments]
                )
                if retry_hint:
                    tool_results.append({"type": "text", "text": retry_hint})

            messages.append({"role": "user", "content": tool_results})

            await _emit_progress_subtasks(
                progress,
                tool_traces,
                role=jpilot_role,
                user_message=user_message,
                **progress_ctx,
            )
            if _maybe_pause_for_long_task(
                runtime,
                role=jpilot_role,
                user_message=user_message,
                tool_traces=tool_traces,
                continuation_phase=continuation_phase,
                **progress_ctx,
            ):
                paused = True
                break

        if paused or runtime.pause is not None:
            break
        if continuation_phase >= runtime.max_continuation_phases:
            break
        if not _deployment_may_be_incomplete(tool_traces, user_message, jpilot_role):
            break

    return _handle_tool_iteration_limit(
        runtime,
        tool_traces,
        user_message,
        jpilot_role,
        **progress_ctx,
    )
