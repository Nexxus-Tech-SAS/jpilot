"""JPilot chat roles: Architect, Operator, and Analyst."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.services.calibration_sync_service import (
    list_installed_personas as personas_installed_on_disk,
    prune_orphan_persona_index,
    read_installed_persona_manifest,
)
from app.services.prompt_loader import load_operator_design_implementation_suffix, load_role_prompt
from app.services.vendor_registry import DEFAULT_VENDOR_ID, get_vendor_manifest

PERSONA_COLLECTION = "stack_personas"

_VALID_BASE_ROLES = {"architect", "operator", "analyst"}

# User-facing capability label for each base role. Personas (built-in or custom)
# surface this so users understand what a persona can/can't do without the role
# itself being separately selectable.
PERSONA_CAPABILITY = {
    "architect": "Plan-only",
    "operator": "Full control",
    "analyst": "Read-only",
}


class JPilotRole(StrEnum):
    ARCHITECT = "architect"
    OPERATOR = "operator"
    ANALYST = "analyst"


DEFAULT_ROLE = JPilotRole.OPERATOR


class CopilotRoleInfo(BaseModel):
    id: str
    label: str
    description: str
    requiresAppliance: bool
    suggestedPaneLabel: str
    handoffTarget: str | None = None


ROLE_CATALOG: list[CopilotRoleInfo] = [
    CopilotRoleInfo(
        id=JPilotRole.ARCHITECT,
        label="Architect",
        description="Plan deployments, HA, migrations, and designs without a live appliance.",
        requiresAppliance=False,
        suggestedPaneLabel="Plan",
        handoffTarget=JPilotRole.OPERATOR,
    ),
    CopilotRoleInfo(
        id=JPilotRole.OPERATOR,
        label="Operator",
        description="Build and change configuration on a connected NetScaler.",
        requiresAppliance=True,
        suggestedPaneLabel="Operate",
        handoffTarget=None,
    ),
    CopilotRoleInfo(
        id=JPilotRole.ANALYST,
        label="Analyst",
        description="Troubleshoot incidents with read-first checks on a connected appliance.",
        requiresAppliance=True,
        suggestedPaneLabel="Analyze",
        handoffTarget=JPilotRole.OPERATOR,
    ),
]

# Tools that never touch a specific appliance (Architect + Analyst baseline).
_PLANNING_TOOLS = frozenset(
    {
        "search_netscaler_nextgen_api",
        "search_netscaler_cli_reference",
        "search_jpilot_architect_resources",
        "jpilot_check_doc_connectivity",
        "netscaler_list_inventory",
        "list_official_blueprint_catalog",
        "search_stack_calibration_memory",
    }
)

# Analyst: planning tools plus read/diagnostic MCP tools (no provisioning writes).
_ANALYST_TOOLS = _PLANNING_TOOLS | frozenset(
    {
        "netscaler_test_connection",
        "netscaler_get_system_info",
        "netscaler_list_applications",
        "netscaler_list_virtual_servers",
        "netscaler_list_virtual_ips",
        "netscaler_list_ip_addresses",
        "netscaler_list_service_status",
        "netscaler_nextgen_get",
        "netscaler_run_diagnostic",
        "netscaler_telnet",
        "netscaler_collect_nsconmsg",
        "netscaler_ssh_run_command",
        "netscaler_run_cli_command",
    }
)

_ANALYST_BLOCKED = frozenset(
    {
        "netscaler_create_application",
        "netscaler_add_ip_address",
        "netscaler_nextgen_request",
        "netscaler_run_cli_commands",
    }
)


def operator_design_implementation_suffix(appliance_name: str, vendor: str | None = None) -> str:
    return load_operator_design_implementation_suffix(appliance_name, vendor)


def normalize_role(role: str | None) -> JPilotRole:
    if not role:
        return DEFAULT_ROLE
    normalized = role.strip().lower()
    if normalized == "investigator":
        normalized = JPilotRole.ANALYST.value
    try:
        return JPilotRole(normalized)
    except ValueError:
        return DEFAULT_ROLE


def role_requires_appliance(role: JPilotRole | str | None) -> bool:
    parsed = role if isinstance(role, JPilotRole) else normalize_role(role if isinstance(role, str) else None)
    return parsed != JPilotRole.ARCHITECT


def capability_for_role(role: JPilotRole | str | None) -> str:
    """Human-facing capability label derived from the (base) role."""
    parsed = role if isinstance(role, JPilotRole) else normalize_role(role if isinstance(role, str) else None)
    return PERSONA_CAPABILITY.get(parsed.value, "")


def get_role_catalog() -> list[dict[str, Any]]:
    return [item.model_dump() for item in ROLE_CATALOG]


def build_system_prompt(
    role: JPilotRole | str | None,
    appliance_name: str = "",
    vendor: str | None = DEFAULT_VENDOR_ID,
) -> str:
    parsed = role if isinstance(role, JPilotRole) else normalize_role(role if isinstance(role, str) else None)
    chat_vendor = (vendor or DEFAULT_VENDOR_ID).strip().lower()
    manifest = get_vendor_manifest(chat_vendor)
    ssh_vendor = bool(manifest and manifest.connect_mode == "ssh")

    if parsed == JPilotRole.ARCHITECT:
        base = load_role_prompt(JPilotRole.ARCHITECT.value, vendor)
        if appliance_name:
            return (
                f"{base}\n"
                f"Reference appliance (planning context only, do not run appliance tools): {appliance_name}\n"
            )
        return (
            f"{base}\n"
            "No appliance is connected. Use inventory and documentation only.\n"
        )
    if parsed == JPilotRole.ANALYST:
        base = load_role_prompt(JPilotRole.ANALYST.value, vendor)
        if ssh_vendor:
            suffix = (
                f"Active appliance: {appliance_name}\n"
                f"SSH connectivity is confirmed. Always pass appliance_name \"{appliance_name}\" to tool calls.\n"
            )
        else:
            suffix = (
                f"Active appliance: {appliance_name}\n"
                f"Next-Gen API login is confirmed. Always pass appliance_name \"{appliance_name}\" to NetScaler tools.\n"
            )
        return f"{base}\n{suffix}"

    base = load_role_prompt(JPilotRole.OPERATOR.value, vendor)
    if ssh_vendor:
        return (
            f"{base}\n"
            f"Active appliance: {appliance_name}\n"
            f"SSH connectivity is confirmed. Always pass appliance_name \"{appliance_name}\" to tool calls.\n"
            "Official CLI behavioral rules are loaded on demand — do not assume syntax without searching first.\n"
            "When a dedicated tool exists (netscaler_create_lb, netscaler_modify_lb, netscaler_delete_lb, "
            "netscaler_create_cs, netscaler_modify_cs, netscaler_delete_cs, netscaler_create_rewrite, "
            "netscaler_modify_rewrite, netscaler_delete_rewrite, netscaler_create_responder, "
            "netscaler_modify_responder, netscaler_delete_responder, netscaler_get_logs, "
            "netscaler_search_config, netscaler_force_failover), use it instead of raw "
            "netscaler_run_cli_command(s) or the search tools."
        )
    return (
        f"{base}\n"
        f"Active appliance: {appliance_name}\n"
        f"Next-Gen API login is confirmed. Always pass appliance_name \"{appliance_name}\" to NetScaler tools.\n"
        "Official CLI/API behavioral rules are loaded on demand — do not assume syntax without searching first.\n"
        "When a dedicated tool exists (netscaler_create_lb, netscaler_modify_lb, netscaler_delete_lb, "
        "netscaler_create_cs, netscaler_modify_cs, netscaler_delete_cs, netscaler_create_rewrite, "
        "netscaler_modify_rewrite, netscaler_delete_rewrite, netscaler_create_responder, "
        "netscaler_modify_responder, netscaler_delete_responder, netscaler_get_logs, "
        "netscaler_search_config, netscaler_force_failover), use it instead of raw "
        "netscaler_run_cli_command(s) or the search tools."
    )


def filter_tools_for_role(
    tools: list[dict[str, Any]],
    role: JPilotRole | str | None,
    vendor: str | None = None,
) -> list[dict[str, Any]]:
    parsed = role if isinstance(role, JPilotRole) else normalize_role(role if isinstance(role, str) else None)
    chat_vendor = (vendor or DEFAULT_VENDOR_ID).strip().lower()
    manifest = get_vendor_manifest(chat_vendor)

    if parsed == JPilotRole.OPERATOR:
        return tools

    if parsed == JPilotRole.ARCHITECT:
        allowed = manifest.planning_tool_names if manifest else _PLANNING_TOOLS
        return [tool for tool in tools if tool.get("name") in allowed]

    allowed = manifest.analyst_tool_names if manifest else _ANALYST_TOOLS
    return [tool for tool in tools if tool.get("name") in allowed]


def assert_tool_allowed_for_role(
    name: str,
    role: JPilotRole | str | None,
    vendor: str | None = None,
) -> None:
    parsed = role if isinstance(role, JPilotRole) else normalize_role(role if isinstance(role, str) else None)
    if parsed == JPilotRole.OPERATOR:
        return
    chat_vendor = (vendor or DEFAULT_VENDOR_ID).strip().lower()
    manifest = get_vendor_manifest(chat_vendor)
    if parsed == JPilotRole.ARCHITECT:
        allowed = manifest.planning_tool_names if manifest else _PLANNING_TOOLS
    else:
        allowed = manifest.analyst_tool_names if manifest else _ANALYST_TOOLS
    if name not in allowed:
        raise ValueError(
            f"Tool '{name}' is not available in {parsed.value} role for vendor '{chat_vendor}'. "
            f"Switch to Operator to make configuration changes."
        )
    if parsed == JPilotRole.ANALYST and manifest and name in manifest.analyst_blocked:
        raise ValueError(
            f"Tool '{name}' is not allowed for Analyst (read/diagnostic only). "
            "Use Operator role to apply changes."
        )
    if parsed == JPilotRole.ANALYST and not manifest and name in _ANALYST_BLOCKED:
        raise ValueError(
            f"Tool '{name}' is not allowed for Analyst (read/diagnostic only). "
            "Use Operator role to apply changes."
        )


class CustomPersonaInfo(BaseModel):
    """Runtime info for a resolved persona (built-in or installed custom)."""

    personaId: str
    label: str
    baseRole: str
    systemPrompt: str
    objectives: list[str] = []
    kind: str = "custom"
    capability: str = ""


async def resolve_custom_persona(
    db: AsyncIOMotorDatabase,
    persona_id: str | None,
) -> CustomPersonaInfo | None:
    """Return info for an installed custom persona, or None if not found / persona_id is unset.

    The returned baseRole is guaranteed to be a valid JPilotRole value.
    """
    if not persona_id:
        return None
    cleaned = persona_id.strip()
    if not cleaned:
        return None

    on_disk = personas_installed_on_disk()
    disk_version = on_disk.get(cleaned)
    if not disk_version:
        return None

    doc = await db[PERSONA_COLLECTION].find_one(
        {"personaId": cleaned, "enabled": True, "version": disk_version},
    ) or await db[PERSONA_COLLECTION].find_one(
        {"personaId": cleaned, "enabled": True},
        sort=[("installedAt", -1)],
    )
    manifest = read_installed_persona_manifest(cleaned, disk_version)
    if doc is None and not manifest:
        return None

    raw_base_role = str(
        (doc or {}).get("baseRole") or manifest.get("baseRole") or ""
    ).strip().lower()
    if raw_base_role not in _VALID_BASE_ROLES:
        raw_base_role = JPilotRole.OPERATOR.value  # safe fallback

    behavior = (doc or {}).get("behavior") or manifest.get("behavior") or {}
    return CustomPersonaInfo(
        personaId=cleaned,
        label=str((doc or {}).get("label") or manifest.get("label") or cleaned),
        baseRole=raw_base_role,
        systemPrompt=str(behavior.get("systemPrompt") or ""),
        objectives=list(behavior.get("objectives") or []),
        kind="custom",
        capability=capability_for_role(raw_base_role),
    )


def _persona_catalog_entry(
    persona_id: str,
    *,
    doc: dict[str, Any] | None,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    raw_base_role = str(
        (doc or {}).get("baseRole") or manifest.get("baseRole") or ""
    ).strip().lower()
    if raw_base_role not in _VALID_BASE_ROLES:
        raw_base_role = JPilotRole.OPERATOR.value
    behavior = (doc or {}).get("behavior") or manifest.get("behavior") or {}
    label = str((doc or {}).get("label") or manifest.get("label") or persona_id)
    description_source = str(behavior.get("systemPrompt") or manifest.get("description") or "")
    return {
        "id": persona_id,
        "label": label,
        "description": description_source[:120] or f"Custom persona (base: {raw_base_role})",
        "baseRole": raw_base_role,
        "requiresAppliance": raw_base_role != JPilotRole.ARCHITECT.value,
        "suggestedPaneLabel": label or "Custom",
        "handoffTarget": None,
        "isCustomPersona": True,
        "kind": "custom",
        "capability": capability_for_role(raw_base_role),
    }


async def list_installed_personas(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    """Return custom personas installed on disk for the roles catalog."""
    await prune_orphan_persona_index(db)
    on_disk = personas_installed_on_disk()
    results: list[dict[str, Any]] = []
    for persona_id in sorted(on_disk):
        if persona_id in _VALID_BASE_ROLES:
            continue
        disk_version = on_disk[persona_id]
        manifest = read_installed_persona_manifest(persona_id, disk_version)
        if not manifest:
            continue
        doc = await db[PERSONA_COLLECTION].find_one(
            {"personaId": persona_id, "enabled": True, "version": disk_version},
        ) or await db[PERSONA_COLLECTION].find_one(
            {"personaId": persona_id, "enabled": True},
            sort=[("installedAt", -1)],
        )
        results.append(_persona_catalog_entry(persona_id, doc=doc, manifest=manifest))
    return results


def builtin_personas() -> list[dict[str, Any]]:
    """The three base roles, presented as built-in personas (persona-first model).

    These live in the same unified list as installed custom personas. They have no
    custom systemPrompt overlay and their baseRole equals their identity.
    """
    personas: list[dict[str, Any]] = []
    for item in ROLE_CATALOG:
        role_id = str(item.id)
        personas.append(
            {
                "id": role_id,
                "label": item.label,
                "description": item.description,
                "requiresAppliance": item.requiresAppliance,
                "suggestedPaneLabel": item.suggestedPaneLabel,
                "handoffTarget": item.handoffTarget,
                "baseRole": role_id,
                "isCustomPersona": False,
                "kind": "builtin",
                "capability": capability_for_role(role_id),
            }
        )
    return personas


async def list_all_personas(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    """Unified persona list: built-in base-role personas + installed custom personas.

    Custom personas whose id collides with a base role are skipped by
    ``list_installed_personas`` so a custom persona can never shadow a built-in.
    """
    return builtin_personas() + await list_installed_personas(db)


def _builtin_persona_info(role: str | None) -> CustomPersonaInfo:
    """Build runtime info for a built-in (base-role) persona with an empty overlay."""
    parsed = normalize_role(role)
    info = next((r for r in ROLE_CATALOG if str(r.id) == parsed.value), None)
    return CustomPersonaInfo(
        personaId=parsed.value,
        label=info.label if info else parsed.value.capitalize(),
        baseRole=parsed.value,
        systemPrompt="",
        objectives=[],
        kind="builtin",
        capability=capability_for_role(parsed.value),
    )


async def resolve_persona(
    db: AsyncIOMotorDatabase,
    persona_id: str | None,
    fallback_role: str | None = None,
) -> CustomPersonaInfo:
    """Resolve any persona id to runtime info. Never returns ``None``.

    - Empty/None or a built-in base-role id → the built-in persona for that role
      (defaulting to OPERATOR), with an empty overlay.
    - A custom persona id → delegates to :func:`resolve_custom_persona`.
    - A custom id that is no longer installed (uninstalled / orphan-pruned) →
      graceful fallback to the built-in of ``fallback_role`` (else the default role),
      so a turn never fails on a stale persona selection.
    """
    cleaned = (persona_id or "").strip()
    if not cleaned:
        # No persona id (legacy client / empty) → use the provided role, else default.
        return _builtin_persona_info(fallback_role or DEFAULT_ROLE.value)
    if cleaned.lower() in _VALID_BASE_ROLES:
        return _builtin_persona_info(cleaned)

    custom = await resolve_custom_persona(db, cleaned)
    if custom is not None:
        return custom

    # Stale/removed custom persona → fall back to the built-in of the legacy role.
    return _builtin_persona_info(fallback_role)
