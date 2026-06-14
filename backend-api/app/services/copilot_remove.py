"""Auto-remove load balancers and linked services from explicit operator requests."""

from __future__ import annotations

import json
import re
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.copilot import ToolCallTrace
from app.services.copilot_form import is_form_submission

_REMOVE_VERB_RE = re.compile(
    r"\b(?:remove|delete|uninstall|tear\s*down|clean\s*up|cleanup|rm)\b",
    re.IGNORECASE,
)
_TARGET_NAME_RE = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b", re.IGNORECASE)
_STOPWORDS = frozenset(
    {
        "service_groups",
        "service_group",
        "services_groups",
        "services_group",
    }
)


def parse_lb_removal_targets(user_message: str) -> list[str]:
    if not user_message:
        return []
    seen: set[str] = set()
    targets: list[str] = []
    for match in _TARGET_NAME_RE.finditer(user_message):
        name = match.group(1).lower()
        if name in _STOPWORDS:
            continue
        if name not in seen:
            seen.add(name)
            targets.append(name)
    return targets


def detect_lb_removal_request(user_message: str) -> bool:
    if is_form_submission(user_message):
        return False
    if not _REMOVE_VERB_RE.search(user_message or ""):
        return False
    targets = parse_lb_removal_targets(user_message)
    if not targets:
        return False
    lowered = (user_message or "").lower()
    lb_context = any(
        term in lowered
        for term in (
            "lb",
            "load balanc",
            "vserver",
            "virtual server",
            "application",
            "service group",
            "servicegroup",
            "services and",
            "services groups",
        )
    )
    return lb_context or len(targets) >= 1


def _parse_tool_result(result: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else None


def _infer_service_groups(vserver_name: str, bound: list[str]) -> list[str]:
    groups = [name for name in bound if name]
    if groups:
        return groups
    if vserver_name.endswith("_vs"):
        return [f"{vserver_name[:-3]}_sg"]
    return [f"{vserver_name}_sg"]


def build_classic_vserver_removal_commands(
    vserver_name: str,
    *,
    bound_service_groups: list[str],
    service_groups: list[dict[str, Any]],
    vip: str | None = None,
) -> list[str]:
    commands: list[str] = []
    groups_by_name = {str(group.get("name") or ""): group for group in service_groups}

    for group_name in _infer_service_groups(vserver_name, bound_service_groups):
        commands.append(f"unbind lb vserver {vserver_name} -serviceGroupName {group_name}")

    commands.append(f"rm lb vserver {vserver_name}")

    for group_name in _infer_service_groups(vserver_name, bound_service_groups):
        group = groups_by_name.get(group_name) or {"members": []}
        for member in group.get("members") or []:
            ip_address = str(member.get("ipAddress") or "").strip()
            port = member.get("port")
            service_name = str(member.get("name") or "").strip()
            if ip_address and port:
                commands.append(f"unbind serviceGroup {group_name} {ip_address} {port}")
            if service_name:
                commands.append(f"rm service {service_name}")
        commands.append(f"rm serviceGroup {group_name}")

    if vip:
        commands.append(f"rm ns ip {vip}")
    return commands


def build_lb_removal_commands(
    targets: list[str],
    inventory: dict[str, Any],
    service_status: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Return (classic_cli_commands, nextgen_app_names) for the requested targets."""
    virtual_servers = inventory.get("virtualServers") or []
    by_name = {str(item.get("name") or "").lower(): item for item in virtual_servers}
    service_groups = service_status.get("serviceGroups") or []

    classic_commands: list[str] = []
    nextgen_apps: list[str] = []

    for target in targets:
        item = by_name.get(target.lower())
        if not item:
            continue
        source = str(item.get("source") or item.get("type") or "").lower()
        if "nextgen" in source:
            nextgen_apps.append(str(item.get("name") or target))
            continue

        bound = item.get("servers") or []
        if isinstance(bound, dict):
            bound = list(bound.values())
        bound_groups = [str(name) for name in bound if isinstance(name, str)]
        vip = str(item.get("virtualIp") or item.get("virtual_ip") or "").strip() or None
        classic_commands.extend(
            build_classic_vserver_removal_commands(
                str(item.get("name") or target),
                bound_service_groups=bound_groups,
                service_groups=service_groups,
                vip=vip,
            )
        )

    # Explicit service-group targets (e.g. exchange_sg without vserver in message)
    group_names = {str(group.get("name") or "").lower() for group in service_groups}
    for target in targets:
        if target.lower() not in group_names:
            continue
        if any(f"serviceGroup {target}" in command for command in classic_commands):
            continue
        group = next((row for row in service_groups if str(row.get("name") or "").lower() == target.lower()), None)
        if not group:
            classic_commands.append(f"rm serviceGroup {target}")
            continue
        for member in group.get("members") or []:
            ip_address = str(member.get("ipAddress") or "").strip()
            port = member.get("port")
            service_name = str(member.get("name") or "").strip()
            if ip_address and port:
                classic_commands.append(f"unbind serviceGroup {target} {ip_address} {port}")
            if service_name:
                classic_commands.append(f"rm service {service_name}")
        classic_commands.append(f"rm serviceGroup {target}")

    if classic_commands and classic_commands[-1] != "save ns config":
        classic_commands.append("save ns config")
    return classic_commands, nextgen_apps


def _remaining_targets(targets: list[str], inventory: dict[str, Any]) -> list[str]:
    present = {str(item.get("name") or "").lower() for item in inventory.get("virtualServers") or []}
    return [name for name in targets if name.lower() in present]


def format_lb_removal_response(
    appliance_name: str,
    *,
    targets: list[str],
    inventory: dict[str, Any],
    removed_nextgen: list[str],
    classic_commands: list[str],
) -> str:
    remaining = _remaining_targets(targets, inventory)
    lines = [
        f"**{appliance_name}** — removed load balancer target(s): {', '.join(f'`{name}`' for name in targets)}.",
        "",
    ]
    if removed_nextgen:
        lines.append(f"- Next-Gen uninstalled: {', '.join(f'`{name}`' for name in removed_nextgen)}")
    if classic_commands:
        lines.append(f"- Classic CLI: {len(classic_commands)} command(s) including `save ns config`")
    if remaining:
        lines.extend(
            [
                "",
                f"Still present in inventory: {', '.join(f'`{name}`' for name in remaining)}. "
                "Some bindings may need manual cleanup if the appliance returned dependency errors.",
            ]
        )
    else:
        lines.append("- Inventory check: requested targets are no longer listed.")
    return "\n".join(lines)


async def try_auto_remove_lb_targets(
    db: AsyncIOMotorDatabase,
    *,
    user_message: str,
    appliance_name: str,
    enabled_tool_names: set[str],
) -> tuple[list[ToolCallTrace], str | None]:
    if not appliance_name:
        return [], None
    if not detect_lb_removal_request(user_message):
        return [], None

    targets = parse_lb_removal_targets(user_message)
    if not targets:
        return [], None

    from app.services.copilot_service import execute_copilot_tool

    traces: list[ToolCallTrace] = []

    async def _run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await execute_copilot_tool(
                db,
                name,
                arguments,
                default_appliance_name=appliance_name,
            )
        except Exception as exc:
            result = json.dumps({"success": False, "message": str(exc)}, indent=2)
        traces.append(ToolCallTrace(name=name, arguments=arguments, result=result))
        return _parse_tool_result(result) or {}

    inventory = await _run_tool(
        "netscaler_list_virtual_servers",
        {"appliance_name": appliance_name},
    )
    if inventory.get("blocked"):
        return traces, inventory.get("message") or "Inventory read was blocked."

    service_status = await _run_tool(
        "netscaler_list_service_status",
        {"appliance_name": appliance_name, "down_only": False},
    )

    classic_commands, nextgen_apps = build_lb_removal_commands(targets, inventory, service_status)
    removed_nextgen: list[str] = []

    if nextgen_apps and "netscaler_nextgen_request" in enabled_tool_names:
        for app_name in nextgen_apps:
            payload = await _run_tool(
                "netscaler_nextgen_request",
                {
                    "appliance_name": appliance_name,
                    "method": "POST",
                    "path": f"applications/{app_name}/actions/uninstall",
                    "confirmed": True,
                },
            )
            if payload.get("blocked"):
                return traces, payload.get("message") or f"Uninstall blocked for `{app_name}`."
            if payload.get("success") is not False:
                removed_nextgen.append(app_name)

    if classic_commands:
        if "netscaler_run_cli_commands" not in enabled_tool_names:
            return traces, (
                "**Removal requires classic CLI** — enable `netscaler_run_cli_commands` and retry."
            )
        cli_payload = await _run_tool(
            "netscaler_run_cli_commands",
            {
                "appliance_name": appliance_name,
                "commands": classic_commands,
                "confirmed": True,
            },
        )
        if cli_payload.get("blocked"):
            return traces, cli_payload.get("message") or "Classic removal was blocked."
        if cli_payload.get("success") is False or cli_payload.get("commandFailed"):
            message = str(cli_payload.get("message") or cli_payload.get("error") or "Classic removal failed.")
            return traces, f"**LB removal failed** — {message}"

    verify_inventory = await _run_tool(
        "netscaler_list_virtual_servers",
        {"appliance_name": appliance_name},
    )

    if not removed_nextgen and not classic_commands:
        return traces, (
            f"**No matching load balancers found** for: "
            f"{', '.join(f'`{name}`' for name in targets)}. "
            "Check names with `netscaler_list_virtual_servers`."
        )

    return traces, format_lb_removal_response(
        appliance_name,
        targets=targets,
        inventory=verify_inventory,
        removed_nextgen=removed_nextgen,
        classic_commands=classic_commands,
    )
