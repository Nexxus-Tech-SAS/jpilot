"""Auto-deploy load balancers from configuration form submissions."""

from __future__ import annotations

import json
import re
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.copilot import ToolCallTrace
from app.services.copilot_form import is_form_submission

_IP_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
_IP_IN_TEXT_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
_BACKEND_PORT_LABEL_RE = re.compile(r"backend\s+port", re.IGNORECASE)
_LB_CREATE_RE = re.compile(
    r"\b(?:create|configure|set\s*up|setup|provision|add|build|deploy)\b.*\b(?:load\s*balanc|lb\b)",
    re.IGNORECASE,
)

_FORM_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "name": (
        "application name",
        "app name",
    ),
    "virtual_ip": (
        "vip address",
        "virtual ip",
        "vip",
    ),
    "port": (
        "port",
        "vip port",
        "front-end port",
        "frontend port",
        "front end port",
    ),
    "servers_port": (
        "backend server port",
        "backend port",
        "servers port",
        "server port",
    ),
    "protocol": (
        "protocol",
        "service type",
    ),
    "servers": (
        "backend storefront server",
        "backend server ip",
        "backend ip addresses",
        "backend ip",
        "backend iis",
        "backend server",
        "backend",
        "server ip",
    ),
}

_FIELD_PARSE_ORDER = (
    "name",
    "virtual_ip",
    "servers_port",
    "servers",
    "port",
    "protocol",
)

_CLASSIC_LB_LABELS = (
    "virtual server name",
    "vserver name",
    "lb vserver",
)


def _normalize_label(label: str) -> str:
    return " ".join(label.strip().lower().split())


def _label_matches(key: str, normalized_label: str) -> bool:
    aliases = _FORM_FIELD_ALIASES.get(key, ())
    if normalized_label in aliases:
        return True
    return any(" " in alias and alias in normalized_label for alias in aliases)


def parse_configuration_form_fields(user_message: str) -> dict[str, str]:
    """Parse `- Label: value` lines from a Configuration inputs submission."""
    if not is_form_submission(user_message):
        return {}

    fields: dict[str, str] = {}
    for line in user_message.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        body = stripped[2:].strip()
        if ": " not in body:
            continue
        label, _, value = body.partition(": ")
        value = value.strip()
        if not value or value == "(not provided)":
            continue
        normalized_label = _normalize_label(label)
        if any(marker in normalized_label for marker in _CLASSIC_LB_LABELS):
            return {}
        matched = False
        for key in _FIELD_PARSE_ORDER:
            if _label_matches(key, normalized_label):
                fields[key] = value
                matched = True
                break
        if not matched and normalized_label.endswith(" name") and "name" not in fields:
            fields["name"] = value
    return fields


def parse_backend_server_endpoints(raw: str, *, default_port: int = 80) -> list[tuple[str, int]]:
    """Parse backend list entries: plain IPs or IP:PORT (calibration HTTP LB forms)."""
    endpoints: list[tuple[str, int]] = []
    for part in re.split(r"[,;\n]+", raw or ""):
        candidate = part.strip()
        if not candidate:
            continue
        if ":" in candidate:
            ip, _, port_text = candidate.partition(":")
            ip = ip.strip()
            try:
                port = int(port_text.strip())
            except ValueError:
                continue
            if _IP_RE.match(ip) and 0 < port <= 65535:
                endpoints.append((ip, port))
            continue
        token = candidate.split()[0].strip()
        if _IP_RE.match(token):
            endpoints.append((token, default_port))
    return endpoints


def parse_backend_servers(raw: str) -> list[str]:
    endpoints = parse_backend_server_endpoints(raw)
    if endpoints:
        return [ip for ip, _ in endpoints]
    servers: list[str] = []
    for part in re.split(r"[,;\n]+", raw or ""):
        candidate = part.strip()
        if not candidate:
            continue
        token = candidate.split()[0].strip()
        if _IP_RE.match(token):
            servers.append(token)
    return servers


def _http_lb_resource_names(name: str) -> tuple[str, str, str]:
    cleaned = re.sub(r"[^\w-]", "_", (name or "").strip()).strip("_") or "http_lb"
    base = cleaned[:-3] if cleaned.endswith("_vs") else cleaned
    vserver = cleaned if cleaned.endswith("_vs") else f"{base}_vs"
    service_group = f"{base}_sg"
    return base, vserver, service_group


def detect_http_lb_form_submission(user_message: str) -> bool:
    if not is_form_submission(user_message):
        return False
    title = (user_message.splitlines()[0] if user_message else "").lower()
    if "http load balancer" not in title:
        return False
    fields = parse_configuration_form_fields(user_message)
    if not fields.get("name") or not fields.get("virtual_ip"):
        return False
    return len(parse_backend_server_endpoints(fields.get("servers", ""))) >= 1


def build_http_lb_commands(fields: dict[str, Any], *, skip_vip_add: bool = False) -> list[str]:
    """Classic ADC workflow: server objects → service group → lb vserver → save."""
    base, vserver, service_group = _http_lb_resource_names(str(fields["name"]))
    vip = str(fields["virtual_ip"]).strip()
    frontend_port = int(str(fields.get("port") or "80").strip() or 80)
    protocol = str(fields.get("protocol") or "HTTP").strip().upper()
    default_backend_port = frontend_port
    if fields.get("servers_port"):
        try:
            default_backend_port = int(str(fields["servers_port"]).strip())
        except ValueError:
            pass
    endpoints = parse_backend_server_endpoints(
        fields.get("servers", ""),
        default_port=default_backend_port,
    )

    commands: list[str] = []
    if not skip_vip_add:
        commands.append(f"add ns ip {vip} 255.255.255.255 -type VIP")
    for index, (ip, port) in enumerate(endpoints, start=1):
        server_name = f"{base}_srv{index}"
        commands.append(f"add server {server_name} {ip}")
    commands.append(f"add serviceGroup {service_group} {protocol}")
    for index, (_, port) in enumerate(endpoints, start=1):
        commands.append(f"bind serviceGroup {service_group} {base}_srv{index} {port}")
    commands.append(f"add lb vserver {vserver} {protocol} {vip} {frontend_port}")
    commands.append(f"bind lb vserver {vserver} {service_group}")
    commands.append("save ns config")
    return commands


def detect_nextgen_application_form_submission(user_message: str) -> bool:
    if detect_http_lb_form_submission(user_message):
        return False
    fields = parse_configuration_form_fields(user_message)
    if not fields.get("name") or not fields.get("virtual_ip"):
        return False
    return bool(parse_backend_servers(fields.get("servers", "")))


def _parse_tool_result(result: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else None


def format_create_application_response(appliance_name: str, data: dict[str, Any]) -> str:
    app = data.get("application") or {}
    name = str(app.get("name") or "").strip()
    vip = str(app.get("virtual_ip") or "").strip()
    port = app.get("port", 80)
    protocol = str(app.get("protocol") or "HTTP").strip()
    servers = app.get("servers") or []
    server_text = ", ".join(f"`{server}:{port}`" for server in servers) if servers else "none"
    lines = [
        f"**{appliance_name}** — application `{name}` created via Next-Gen API.",
        "",
        f"- VIP: `{vip}:{port}` ({protocol})",
        f"- Backends: {server_text}",
        "",
        "Verify health with `netscaler_list_service_status` if backends stay UNKNOWN or the vserver is DOWN.",
    ]
    return "\n".join(lines)


async def try_auto_create_application(
    db: AsyncIOMotorDatabase,
    *,
    user_message: str,
    appliance_name: str,
    enabled_tool_names: set[str],
) -> tuple[list[ToolCallTrace], str | None]:
    """POST /applications when the user submits a Next-Gen configuration form."""
    if not appliance_name:
        return [], None
    if not detect_nextgen_application_form_submission(user_message):
        return [], None
    if "netscaler_create_application" not in enabled_tool_names:
        return [], (
            "**Configuration form received** — `netscaler_create_application` is not enabled. "
            "Enable it in MCP settings and retry."
        )

    fields = parse_configuration_form_fields(user_message)
    servers = parse_backend_servers(fields.get("servers", ""))
    port_raw = fields.get("port", "80")
    try:
        port = int(str(port_raw).strip())
    except ValueError:
        port = 80
    servers_port = None
    if fields.get("servers_port"):
        try:
            servers_port = int(str(fields["servers_port"]).strip())
        except ValueError:
            servers_port = None

    from app.services.copilot_service import execute_copilot_tool

    arguments: dict[str, Any] = {
        "appliance_name": appliance_name,
        "name": fields["name"].strip(),
        "virtual_ip": fields["virtual_ip"].strip(),
        "port": port,
        "protocol": (fields.get("protocol") or "HTTP").strip().upper(),
        "servers": servers,
    }
    if servers_port is not None:
        arguments["servers_port"] = servers_port
    try:
        result = await execute_copilot_tool(
            db,
            "netscaler_create_application",
            arguments,
            default_appliance_name=appliance_name,
        )
    except Exception as exc:
        result = json.dumps({"success": False, "message": str(exc)}, indent=2)

    trace = ToolCallTrace(name="netscaler_create_application", arguments=arguments, result=result)
    data = _parse_tool_result(result) or {}
    if data.get("blocked"):
        return [trace], data.get("message") or "Application create was blocked."

    if data.get("success") is False:
        message = str(data.get("message") or data.get("error") or "Application create failed.")
        return [trace], f"**Application create failed** — {message}"

    if data.get("success") is True or data.get("application"):
        return [trace], format_create_application_response(appliance_name, data)

    return [trace], None


_CLASSIC_LB_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "vserver_name": ("lb vserver name", "virtual server name", "vserver name"),
    "service_group": ("service group name", "service group"),
    "vip": ("vip address", "virtual ip", "frontend vip", "front-end vip", "frontend address"),
    "frontend_port": (
        "front-end port",
        "frontend port",
        "front-end (vip) port",
        "vip port",
        "front end port",
    ),
    "backend_ip": (
        "backend server ip",
        "backend ip addresses",
        "backend ip",
        "backend server",
        "backend ips",
    ),
    "lb_method": ("load balancing method", "lb method", "load balancing algorithm"),
    "monitor": ("health monitor", "monitor"),
    "ssl_cert": ("ssl certificate to bind", "ssl certificate", "certificate to bind", "certificate"),
    "backend_protocol": ("backend protocol", "servers protocol"),
    "vserver_protocol": ("frontend protocol", "service type"),
}


def _classic_label_matches(key: str, normalized_label: str) -> bool:
    aliases = _CLASSIC_LB_FIELD_ALIASES.get(key, ())
    if normalized_label in aliases:
        return True
    return any(" " in alias and alias in normalized_label for alias in aliases)


def parse_classic_lb_form_fields(user_message: str) -> dict[str, Any]:
    """Parse classic LB vserver/service-group form submissions."""
    if not is_form_submission(user_message):
        return {}

    fields: dict[str, str] = {}
    backend_ports: list[int] = []
    for line in user_message.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        body = stripped[2:].strip()
        if ": " not in body:
            continue
        label, _, value = body.partition(": ")
        value = value.strip()
        if not value or value == "(not provided)":
            continue
        normalized_label = _normalize_label(label)
        if _BACKEND_PORT_LABEL_RE.search(normalized_label):
            try:
                backend_ports.append(int(value.split()[0]))
            except ValueError:
                continue
            continue
        for key in _CLASSIC_LB_FIELD_ALIASES:
            if _classic_label_matches(key, normalized_label):
                fields[key] = value
                break

    if backend_ports:
        fields["backend_ports"] = backend_ports

    backend_ips = parse_backend_servers(fields.get("backend_ip", ""))
    if backend_ips:
        fields["backend_ip"] = backend_ips[0]

    if not fields.get("vip"):
        for key, value in fields.items():
            if key in {"backend_ports", "backend_ip"} or not isinstance(value, str):
                continue
            token = value.split()[0].strip()
            if _IP_RE.match(token) and token != fields.get("backend_ip"):
                fields["vip"] = token
                break

    return fields


def detect_classic_lb_form_submission(user_message: str) -> bool:
    if detect_nextgen_application_form_submission(user_message):
        return False
    fields = parse_classic_lb_form_fields(user_message)
    if not fields.get("vserver_name") or not fields.get("vip"):
        return False
    if not fields.get("backend_ip"):
        return False
    backend_ports = fields.get("backend_ports") or []
    if not backend_ports and fields.get("backend_port"):
        try:
            backend_ports = [int(str(fields["backend_port"]).strip())]
        except ValueError:
            backend_ports = []
    return bool(backend_ports)


def _resolve_vserver_protocol(fields: dict[str, Any]) -> str:
    backend_protocol = str(fields.get("backend_protocol") or "HTTP").strip().upper()
    explicit = str(fields.get("vserver_protocol") or "").strip().upper()
    ssl_cert = str(fields.get("ssl_cert") or "").strip()
    frontend_port = int(fields.get("frontend_port") or 443)

    if explicit in {"SSL_TCP", "SSL_BRIDGE", "TCP", "HTTP", "SSL"}:
        if explicit == "SSL" and backend_protocol == "TCP":
            return "SSL_TCP"
        return explicit
    if ssl_cert or frontend_port == 443:
        return "SSL_TCP" if backend_protocol == "TCP" else "SSL"
    return backend_protocol


def _normalize_monitor_name(monitor: str) -> str:
    cleaned = (monitor or "").strip().lower()
    if cleaned in {"tcp", "tcp monitor", "tcp-default"}:
        return "tcp"
    if cleaned in {"ping", "ping monitor"}:
        return "ping"
    if cleaned in {"http", "http monitor"}:
        return "http"
    return monitor.strip()


def finalize_classic_lb_fields(fields: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(fields)
    if resolved.get("monitor"):
        resolved["monitor"] = _normalize_monitor_name(str(resolved["monitor"]))
    if "tcp monitor" in str(resolved.get("monitor") or "").lower():
        resolved["backend_protocol"] = "TCP"
    resolved["vserver_protocol"] = _resolve_vserver_protocol(resolved)
    backend_protocol = str(resolved.get("backend_protocol") or "HTTP").strip().upper()
    vserver_protocol = str(resolved["vserver_protocol"]).upper()
    if vserver_protocol == "SSL_TCP":
        resolved["backend_protocol"] = "TCP"
    elif vserver_protocol == "SSL" and backend_protocol == "TCP":
        resolved["backend_protocol"] = "HTTP"
    return resolved


def build_classic_lb_commands(fields: dict[str, Any], *, skip_vip_add: bool = False) -> list[str]:
    fields = finalize_classic_lb_fields(fields)
    vip = str(fields["vip"]).strip()
    vserver = str(fields["vserver_name"]).strip()
    base_name = vserver[:-3] if vserver.endswith("_vs") else vserver
    sg = str(fields.get("service_group") or f"{base_name}_sg").strip()
    frontend_port = int(fields.get("frontend_port") or 443)
    backend_ip = str(fields["backend_ip"]).strip()
    backend_ports = [int(port) for port in fields.get("backend_ports") or []]
    lb_method = str(fields.get("lb_method") or "LEASTCONNECTION").strip().upper()
    monitor = str(fields.get("monitor") or "ping").strip()
    ssl_cert = str(fields.get("ssl_cert") or "").strip()
    backend_protocol = str(fields.get("backend_protocol") or "HTTP").strip().upper()
    persistence = str(fields.get("persistence") or "NONE").strip().upper()
    vserver_protocol = str(fields["vserver_protocol"]).strip().upper()

    commands: list[str] = []
    if not skip_vip_add:
        commands.append(f"add ns ip {vip} 255.255.255.255 -type VIP")
    commands.append(f"add serviceGroup {sg} {backend_protocol}")
    for port in backend_ports:
        commands.append(f"bind serviceGroup {sg} {backend_ip} {port}")
    if monitor:
        commands.append(f"bind serviceGroup {sg} -monitorName {monitor}")
    commands.append(
        f"add lb vserver {vserver} {vserver_protocol} {vip} {frontend_port} "
        f"-lbMethod {lb_method} -persistenceType {persistence}"
    )
    commands.append(f"bind lb vserver {vserver} {sg}")
    if ssl_cert and vserver_protocol in {"SSL", "SSL_BRIDGE", "SSL_TCP"}:
        commands.append(f"bind ssl vserver {vserver} -certkeyName {ssl_cert}")
    commands.append("save ns config")
    return commands


def _vserver_state_from_list(data: dict[str, Any], vserver_name: str) -> tuple[str, int]:
    for item in data.get("virtualServers") or []:
        if str(item.get("name") or "").lower() == vserver_name.lower():
            state = str(item.get("state") or "")
            count = int(item.get("serverCount") or 0)
            return state, count
    return "", 0


def _normalize_vserver_name(raw: str) -> str:
    cleaned = re.sub(r"[^\w-]", "", (raw or "").strip().lower())
    if not cleaned:
        return ""
    return cleaned if cleaned.endswith("_vs") else f"{cleaned}_vs"


def _parse_backend_ports_from_text(lowered: str) -> list[int]:
    pair = re.search(r"ports?\s+(\d+)\s+and\s+(\d+)", lowered)
    if pair:
        return [int(pair.group(1)), int(pair.group(2))]
    listed = re.search(r"ports?\s+([\d,\sand]+)", lowered)
    if listed:
        ports: list[int] = []
        for token in re.findall(r"\d+", listed.group(1)):
            value = int(token)
            if 0 < value <= 65535:
                ports.append(value)
        return ports
    return []


def parse_natural_language_lb_request(user_message: str) -> dict[str, Any]:
    """Extract classic LB parameters from a single-sentence operator request."""
    if not user_message or is_form_submission(user_message):
        return {}

    lowered = user_message.lower()
    fields: dict[str, Any] = {}

    name_match = re.search(
        r"load\s+balanc(?:er)?(?:\s+\w+){0,4}\s+for\s+([a-z][\w-]+)",
        lowered,
    )
    if not name_match:
        name_match = re.search(r"\bfor\s+([a-z][\w-]+)\b", lowered)
    if name_match:
        fields["vserver_name"] = _normalize_vserver_name(name_match.group(1))

    backend_match = re.search(
        r"backend(?:\s+server)?s?\s+(\d{1,3}(?:\.\d{1,3}){3})",
        lowered,
    )
    if backend_match:
        fields["backend_ip"] = backend_match.group(1)

    backend_ports = _parse_backend_ports_from_text(lowered)
    if backend_ports:
        fields["backend_ports"] = backend_ports

    frontend_match = re.search(
        r"front(?:\s*|-)?end\s*(?:ip\s+)?(\d{1,3}(?:\.\d{1,3}){3})",
        lowered,
    )
    if frontend_match:
        fields["vip"] = frontend_match.group(1)
    else:
        backend_ip = fields.get("backend_ip")
        for ip in _IP_IN_TEXT_RE.findall(user_message):
            if ip != backend_ip:
                fields["vip"] = ip
                break

    if "ssl" in lowered:
        fields["frontend_port"] = 443
    if "wildcard" in lowered:
        fields["ssl_cert"] = "wildcard-cert"

    if "tcp monitor" in lowered or "tcp-default" in lowered or re.search(r"\btcp\b", lowered):
        fields["monitor"] = "tcp"
        fields["backend_protocol"] = "TCP"
    elif "http monitor" in lowered:
        fields["monitor"] = "http"
    elif "ping monitor" in lowered or re.search(r"\bping\b", lowered):
        fields["monitor"] = "ping"

    if "no persistence" in lowered or "persistence none" in lowered or "without persistence" in lowered:
        fields["persistence"] = "NONE"

    if fields.get("vserver_name"):
        base = str(fields["vserver_name"]).replace("_vs", "")
        fields.setdefault("service_group", f"{base}_sg")
    fields.setdefault("lb_method", "LEASTCONNECTION")
    return finalize_classic_lb_fields(fields)


def detect_natural_language_lb_request(
    user_message: str,
    fields: dict[str, Any] | None = None,
) -> bool:
    if is_form_submission(user_message):
        return False
    parsed = fields or parse_natural_language_lb_request(user_message)
    if not parsed.get("vserver_name") or not parsed.get("vip") or not parsed.get("backend_ip"):
        return False
    if not parsed.get("backend_ports"):
        return False
    lowered = (user_message or "").lower()
    if _LB_CREATE_RE.search(lowered):
        return True
    return "load balanc" in lowered or re.search(r"\blb\b", lowered)


async def _existing_vip_addresses(
    db: AsyncIOMotorDatabase,
    *,
    appliance_name: str,
    enabled_tool_names: set[str],
    traces: list[ToolCallTrace],
) -> set[str]:
    if "netscaler_list_ip_addresses" not in enabled_tool_names:
        return set()

    from app.services.copilot_service import execute_copilot_tool

    arguments = {"appliance_name": appliance_name}
    try:
        result = await execute_copilot_tool(
            db,
            "netscaler_list_ip_addresses",
            arguments,
            default_appliance_name=appliance_name,
        )
    except Exception:
        return set()

    traces.append(ToolCallTrace(name="netscaler_list_ip_addresses", arguments=arguments, result=result))
    data = _parse_tool_result(result) or {}
    vips: set[str] = set()
    for row in data.get("addresses") or []:
        ip_address = str(row.get("ipAddress") or row.get("ipaddress") or "").strip()
        row_type = str(row.get("type") or "").upper()
        if ip_address and row_type == "VIP":
            vips.add(ip_address)
    return vips


async def _cleanup_commands_for_existing_lb(
    db: AsyncIOMotorDatabase,
    *,
    appliance_name: str,
    fields: dict[str, Any],
    enabled_tool_names: set[str],
    traces: list[ToolCallTrace],
) -> list[str]:
    if "netscaler_list_virtual_servers" not in enabled_tool_names:
        return []

    from app.services.copilot_remove import build_classic_vserver_removal_commands
    from app.services.copilot_service import execute_copilot_tool

    vserver = str(fields.get("vserver_name") or "").strip()
    if not vserver:
        return []

    arguments = {"appliance_name": appliance_name}
    try:
        vs_result = await execute_copilot_tool(
            db,
            "netscaler_list_virtual_servers",
            arguments,
            default_appliance_name=appliance_name,
        )
    except Exception:
        return []

    traces.append(ToolCallTrace(name="netscaler_list_virtual_servers", arguments=arguments, result=vs_result))
    inventory = _parse_tool_result(vs_result) or {}
    present = {
        str(item.get("name") or "").lower()
        for item in inventory.get("virtualServers") or []
    }
    if vserver.lower() not in present:
        return []

    service_groups: list[dict[str, Any]] = []
    if "netscaler_list_service_status" in enabled_tool_names:
        sg_args = {"appliance_name": appliance_name, "down_only": False}
        try:
            sg_result = await execute_copilot_tool(
                db,
                "netscaler_list_service_status",
                sg_args,
                default_appliance_name=appliance_name,
            )
            traces.append(
                ToolCallTrace(name="netscaler_list_service_status", arguments=sg_args, result=sg_result)
            )
            service_groups = (_parse_tool_result(sg_result) or {}).get("serviceGroups") or []
        except Exception:
            service_groups = []

    item = next(
        (
            row
            for row in inventory.get("virtualServers") or []
            if str(row.get("name") or "").lower() == vserver.lower()
        ),
        {},
    )
    bound = item.get("servers") or []
    if isinstance(bound, dict):
        bound = list(bound.values())
    vip = str(item.get("virtualIp") or fields.get("vip") or "").strip() or None
    return build_classic_vserver_removal_commands(
        vserver,
        bound_service_groups=[str(name) for name in bound if isinstance(name, str)],
        service_groups=service_groups,
        vip=vip,
    )


async def _deploy_classic_lb(
    db: AsyncIOMotorDatabase,
    *,
    appliance_name: str,
    fields: dict[str, Any],
    enabled_tool_names: set[str],
) -> tuple[list[ToolCallTrace], str | None]:
    if "netscaler_run_cli_commands" not in enabled_tool_names:
        return [], (
            "**Load balancer request** — enable `netscaler_run_cli_commands` in MCP settings and retry."
        )

    from app.services.copilot_service import execute_copilot_tool

    traces: list[ToolCallTrace] = []
    fields = finalize_classic_lb_fields(fields)
    vip = str(fields.get("vip") or "").strip()
    existing_vips = await _existing_vip_addresses(
        db,
        appliance_name=appliance_name,
        enabled_tool_names=enabled_tool_names,
        traces=traces,
    )
    cleanup = await _cleanup_commands_for_existing_lb(
        db,
        appliance_name=appliance_name,
        fields=fields,
        enabled_tool_names=enabled_tool_names,
        traces=traces,
    )
    commands = cleanup + build_classic_lb_commands(fields, skip_vip_add=vip in existing_vips)
    arguments = {"appliance_name": appliance_name, "commands": commands}
    try:
        result = await execute_copilot_tool(
            db,
            "netscaler_run_cli_commands",
            arguments,
            default_appliance_name=appliance_name,
        )
    except Exception as exc:
        result = json.dumps({"success": False, "message": str(exc)}, indent=2)

    traces.append(ToolCallTrace(name="netscaler_run_cli_commands", arguments=arguments, result=result))
    data = _parse_tool_result(result) or {}
    if data.get("blocked"):
        return traces, data.get("message") or "Classic LB deploy was blocked."

    if data.get("success") is False or data.get("commandFailed"):
        message = str(data.get("message") or data.get("error") or "Classic LB deploy failed.")
        return traces, f"**Classic LB deploy failed** — {message}"

    verify_data: dict[str, Any] | None = None
    if "netscaler_list_virtual_servers" in enabled_tool_names:
        verify_args = {"appliance_name": appliance_name}
        try:
            verify_result = await execute_copilot_tool(
                db,
                "netscaler_list_virtual_servers",
                verify_args,
                default_appliance_name=appliance_name,
            )
        except Exception:
            verify_result = ""
        if verify_result:
            traces.append(
                ToolCallTrace(
                    name="netscaler_list_virtual_servers",
                    arguments=verify_args,
                    result=verify_result,
                )
            )
            verify_data = _parse_tool_result(verify_result) or {}

    return traces, format_classic_lb_response(
        appliance_name,
        fields=fields,
        verify_data=verify_data,
    )


async def try_auto_deploy_lb_from_message(
    db: AsyncIOMotorDatabase,
    *,
    user_message: str,
    appliance_name: str,
    enabled_tool_names: set[str],
) -> tuple[list[ToolCallTrace], str | None]:
    """Deploy classic LB directly from a complete natural-language operator request."""
    if not appliance_name:
        return [], None
    fields = parse_natural_language_lb_request(user_message)
    if not detect_natural_language_lb_request(user_message, fields):
        return [], None
    return await _deploy_classic_lb(
        db,
        appliance_name=appliance_name,
        fields=fields,
        enabled_tool_names=enabled_tool_names,
    )


def format_classic_lb_response(
    appliance_name: str,
    *,
    fields: dict[str, Any],
    verify_data: dict[str, Any] | None,
) -> str:
    vserver = str(fields["vserver_name"]).strip()
    vip = str(fields["vip"]).strip()
    frontend_port = int(fields.get("frontend_port") or 443)
    ssl_cert = str(fields.get("ssl_cert") or "").strip()
    backend_ip = str(fields["backend_ip"]).strip()
    backend_ports = fields.get("backend_ports") or []
    backend_text = ", ".join(f"`{backend_ip}:{port}`" for port in backend_ports)

    state, server_count = _vserver_state_from_list(verify_data or {}, vserver)
    state_upper = state.upper()
    healthy = state_upper == "UP" and server_count > 0

    lines = [
        f"**{appliance_name}** — classic load balancer `{vserver}` deployed.",
        "",
        f"- Frontend VIP: `{vip}:{frontend_port}`",
        f"- Backends: {backend_text}",
    ]
    if ssl_cert:
        lines.append(f"- SSL certificate: `{ssl_cert}`")
    if verify_data:
        lines.append(f"- vServer state: **{state or 'UNKNOWN'}** ({server_count} backend(s) bound)")
    if not healthy:
        lines.extend(
            [
                "",
                "Deployment finished but the vserver is not fully healthy yet. "
                "Check `netscaler_list_service_status` before routing production traffic.",
            ]
        )
    return "\n".join(lines)


async def try_auto_deploy_classic_lb(
    db: AsyncIOMotorDatabase,
    *,
    user_message: str,
    appliance_name: str,
    enabled_tool_names: set[str],
) -> tuple[list[ToolCallTrace], str | None]:
    """Apply classic LB vserver + service group config in one batched CLI call."""
    if not appliance_name:
        return [], None
    if not detect_classic_lb_form_submission(user_message):
        return [], None

    fields = parse_classic_lb_form_fields(user_message)
    return await _deploy_classic_lb(
        db,
        appliance_name=appliance_name,
        fields=fields,
        enabled_tool_names=enabled_tool_names,
    )


async def try_auto_deploy_http_lb(
    db: AsyncIOMotorDatabase,
    *,
    user_message: str,
    appliance_name: str,
    enabled_tool_names: set[str],
) -> tuple[list[ToolCallTrace], str | None]:
    """Apply calibration HTTP LB form via classic server + serviceGroup + vserver CLI."""
    if not appliance_name:
        return [], None
    if not detect_http_lb_form_submission(user_message):
        return [], None
    if "netscaler_run_cli_commands" not in enabled_tool_names:
        return [], (
            "**HTTP Load Balancer form received** — enable `netscaler_run_cli_commands` "
            "in MCP settings and retry."
        )

    from app.services.copilot_service import execute_copilot_tool

    fields = parse_configuration_form_fields(user_message)
    _, vserver, _ = _http_lb_resource_names(str(fields["name"]))
    vip = str(fields["virtual_ip"]).strip()
    traces: list[ToolCallTrace] = []
    existing_vips = await _existing_vip_addresses(
        db,
        appliance_name=appliance_name,
        enabled_tool_names=enabled_tool_names,
        traces=traces,
    )
    cleanup = await _cleanup_commands_for_existing_lb(
        db,
        appliance_name=appliance_name,
        fields={"vserver_name": vserver, "vip": vip},
        enabled_tool_names=enabled_tool_names,
        traces=traces,
    )
    commands = cleanup + build_http_lb_commands(fields, skip_vip_add=vip in existing_vips)
    arguments = {
        "appliance_name": appliance_name,
        "commands": commands,
        "purpose": "Deploy HTTP load balancer from calibration form",
    }
    try:
        result = await execute_copilot_tool(
            db,
            "netscaler_run_cli_commands",
            arguments,
            default_appliance_name=appliance_name,
        )
    except Exception as exc:
        result = json.dumps({"success": False, "message": str(exc)}, indent=2)

    traces.append(ToolCallTrace(name="netscaler_run_cli_commands", arguments=arguments, result=result))
    data = _parse_tool_result(result) or {}
    if data.get("blocked"):
        return traces, data.get("message") or "HTTP load balancer deploy was blocked."

    if data.get("success") is False or data.get("commandFailed"):
        message = str(data.get("message") or data.get("error") or "HTTP load balancer deploy failed.")
        return traces, f"**HTTP load balancer deploy failed** — {message}"

    verify_data: dict[str, Any] | None = None
    if "netscaler_list_virtual_servers" in enabled_tool_names:
        verify_args = {"appliance_name": appliance_name}
        try:
            verify_result = await execute_copilot_tool(
                db,
                "netscaler_list_virtual_servers",
                verify_args,
                default_appliance_name=appliance_name,
            )
        except Exception:
            verify_result = ""
        if verify_result:
            traces.append(
                ToolCallTrace(
                    name="netscaler_list_virtual_servers",
                    arguments=verify_args,
                    result=verify_result,
                )
            )
            verify_data = _parse_tool_result(verify_result) or {}

    endpoints = parse_backend_server_endpoints(fields.get("servers", ""))
    backend_text = ", ".join(f"`{ip}:{port}`" for ip, port in endpoints)
    state, server_count = _vserver_state_from_list(verify_data or {}, vserver)
    lines = [
        f"**{appliance_name}** — HTTP load balancer `{vserver}` deployed via classic CLI.",
        "",
        f"- Frontend VIP: `{vip}:{fields.get('port', '80')}` ({fields.get('protocol', 'HTTP')})",
        f"- Backends: {backend_text}",
    ]
    if verify_data:
        lines.append(f"- vServer state: **{state or 'UNKNOWN'}** ({server_count} backend(s) bound)")
    return traces, "\n".join(lines)
