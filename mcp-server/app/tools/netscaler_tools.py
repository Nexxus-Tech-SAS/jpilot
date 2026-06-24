import json

import httpx
import mcp.types as types

from app.services.netscaler_service import (
    add_ip_address,
    create_application,
    create_cs,
    create_lb,
    create_responder,
    create_rewrite,
    delete_cs,
    delete_lb,
    delete_responder,
    delete_rewrite,
    force_failover,
    format_tool_result,
    get_logs,
    get_system_info,
    list_applications,
    list_ip_addresses,
    list_service_status,
    list_virtual_ips,
    list_virtual_servers,
    modify_cs,
    modify_lb,
    modify_responder,
    modify_rewrite,
    nextgen_get,
    nextgen_request,
    run_cli_command,
    run_cli_commands,
    run_diagnostic,
    generate_ssl_csr,
    generate_ssl_self_signed,
    run_nsconmsg,
    run_telnet,
    search_config,
    ssh_run_command,
    test_appliance_connection,
)

NETSCALER_TOOLS = [
    types.Tool(
        name="netscaler_test_connection",
        description="Test connectivity and authentication to a NetScaler appliance via the Next-Gen API.",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP (HTTPS port 443)"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
            },
            "required": ["host", "username", "password"],
        },
    ),
    types.Tool(
        name="netscaler_get_system_info",
        description=(
            "Retrieve appliance summary via NetScaler Next-Gen API: management IP, firmware version, "
            "hostname, serial, and application count."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
            },
            "required": ["host", "username", "password"],
        },
    ),
    types.Tool(
        name="netscaler_list_applications",
        description="List NetScaler Next-Gen API applications (application-centric load balancing configs).",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
            },
            "required": ["host", "username", "password"],
        },
    ),
    types.Tool(
        name="netscaler_list_virtual_ips",
        description=(
            "List load-balancing virtual IPs from Next-Gen API applications. "
            "Not for appliance management IP — use netscaler_list_ip_addresses for all IPs."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
            },
            "required": ["host", "username", "password"],
        },
    ),
    types.Tool(
        name="netscaler_list_ip_addresses",
        description=(
            "List all IP addresses on the appliance: NSIP, SNIP, VIP, servers, and application IPs. "
            "Uses Next-Gen API (applications, config_sets) plus read-only NITRO for classic config."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
            },
            "required": ["host", "username", "password"],
        },
    ),
    types.Tool(
        name="netscaler_nextgen_get",
        description=(
            "Perform a read-only GET against a NetScaler Next-Gen API path "
            "(e.g. applications, applications/{name}). Path is relative to /mgmt/api/nextgen/v1/."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
                "path": {
                    "type": "string",
                    "description": "Next-Gen API resource path without the /mgmt/api/nextgen/v1 prefix",
                },
            },
            "required": ["host", "username", "password", "path"],
        },
    ),
    types.Tool(
        name="netscaler_list_virtual_servers",
        description=(
            "List load-balancing virtual servers from Next-Gen applications plus classic NITRO lbvserver. "
            "Use for 'show virtual servers', 'show lb vserver', or any VIP/vserver listing request."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
            },
            "required": ["host", "username", "password"],
        },
    ),
    types.Tool(
        name="netscaler_list_service_status",
        description=(
            "List backend service and service-group health from read-only NITRO stats. "
            "Use for down/unhealthy backends, service state, or 'services that are down'. "
            "Prefer this over inventing stat/show service CLI syntax."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
                "down_only": {
                    "type": "boolean",
                    "description": "When true (default), return only DOWN/out-of-service members",
                },
            },
            "required": ["host", "username", "password"],
        },
    ),
    types.Tool(
        name="netscaler_create_application",
        description=(
            "Create a NetScaler Next-Gen application (POST /applications). "
            "Defines VIP, frontend protocol/port, and backend server pool."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
                "name": {"type": "string", "description": "Application name, e.g. app_2"},
                "virtual_ip": {"type": "string", "description": "Frontend VIP address"},
                "port": {"type": "integer", "description": "Frontend port (default 80)"},
                "protocol": {
                    "type": "string",
                    "description": "Frontend protocol: HTTP, HTTPS, TCP, etc. (default HTTP)",
                },
                "servers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Backend server IP addresses",
                },
                "servers_port": {
                    "type": "integer",
                    "description": "Backend port (defaults to frontend port)",
                },
                "servers_protocol": {
                    "type": "string",
                    "description": "Backend protocol (defaults to frontend protocol)",
                },
            },
            "required": ["host", "username", "password", "name", "virtual_ip", "servers"],
        },
    ),
    types.Tool(
        name="netscaler_add_ip_address",
        description=(
            "Add a classic NetScaler IP address (NSIP, SNIP, or VIP) via NITRO — "
            "equivalent to: add ns ip <ip> <netmask> -type VIP|SNIP|NSIP. "
            "Persists running config with save ns config when save_config is true."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
                "ip_address": {"type": "string", "description": "IPv4 address to add"},
                "ip_type": {
                    "type": "string",
                    "description": "Address type: VIP, SNIP, NSIP, MIP, or GSLBsiteIP",
                    "enum": ["VIP", "SNIP", "NSIP", "MIP", "GSLBsiteIP"],
                },
                "netmask": {
                    "type": "string",
                    "description": "Subnet mask (default 255.255.255.0)",
                },
                "save_config": {
                    "type": "boolean",
                    "description": "Run save ns config after add (default true)",
                },
            },
            "required": ["host", "username", "password", "ip_address", "ip_type"],
        },
    ),
    types.Tool(
        name="netscaler_ssh_run_command",
        description=(
            "Run a read-only NetScaler CLI command via SSH (show/stat/get) or a connectivity "
            "troubleshooting command (ping, ping6, traceroute, traceroute6). ping is automatically "
            "bounded with a packet count so it cannot run indefinitely. "
            "Use after confirming the command in the ADC CLI reference."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler SSH username"},
                "password": {"type": "string", "description": "NetScaler SSH password"},
                "command": {
                    "type": "string",
                    "description": "Read-only or diagnostic command, e.g. show ns version, ping -c 4 10.0.0.5, traceroute 10.0.0.5",
                },
                "purpose": {
                    "type": "string",
                    "description": "Why this command answers the user's question",
                },
            },
            "required": ["host", "username", "password", "command", "purpose"],
        },
    ),
    types.Tool(
        name="netscaler_run_cli_command",
        description=(
            "Run ANY NetScaler classic CLI command via SSH, including configuration writes "
            "(add, set, bind, unbind, enable, disable, rm, clear, save, ...) as well as show/stat/get. "
            "Use after confirming exact syntax in the ADC CLI reference. "
            "Run 'save ns config' afterwards to persist classic config. Dropping to the BSD shell is blocked."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler SSH username"},
                "password": {"type": "string", "description": "NetScaler SSH password"},
                "command": {
                    "type": "string",
                    "description": "Any CLI command, e.g. add lb vserver web_vs HTTP 10.0.0.10 80",
                },
                "purpose": {
                    "type": "string",
                    "description": "Why this command is needed to fulfill the user's request",
                },
            },
            "required": ["host", "username", "password", "command", "purpose"],
        },
    ),
    types.Tool(
        name="netscaler_run_cli_commands",
        description=(
            "Run a sequence of NetScaler classic CLI commands via SSH in order — ideal for multi-step "
            "setup (add lb vserver, add serviceGroup, bind, save ns config). Stops on first failure. "
            "Use after confirming syntax in the ADC CLI reference."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler SSH username"},
                "password": {"type": "string", "description": "NetScaler SSH password"},
                "commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CLI commands to run in order, e.g. add lb vserver ..., bind ..., save ns config",
                },
                "purpose": {
                    "type": "string",
                    "description": "Why this command sequence fulfills the user's request",
                },
            },
            "required": ["host", "username", "password", "commands", "purpose"],
        },
    ),
    types.Tool(
        name="netscaler_run_diagnostic",
        description=(
            "Run a bounded network diagnostic from the appliance for connectivity troubleshooting: "
            "ping, ping6, traceroute, traceroute6 (ICMP/path), or tcp_port (TCP port via telnet). "
            "Use tcp_port for 'is port N open' or host:PORT reachability. Read-only and safe."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler SSH username"},
                "password": {"type": "string", "description": "NetScaler SSH password"},
                "operation": {
                    "type": "string",
                    "description": "Diagnostic to run",
                    "enum": ["ping", "ping6", "traceroute", "traceroute6", "tcp_port"],
                },
                "target": {
                    "type": "string",
                    "description": "Destination host or IP to test, e.g. 8.8.8.8 or server.example.com",
                },
                "count": {
                    "type": "integer",
                    "description": "ping only: number of echo requests (default 4, max 10)",
                },
                "max_hops": {
                    "type": "integer",
                    "description": "traceroute only: maximum hops/TTL (default 15, max 20)",
                },
                "port": {
                    "type": "integer",
                    "description": "tcp_port only: TCP port to test (1-65535)",
                },
            },
            "required": ["host", "username", "password", "operation", "target"],
        },
    ),
    types.Tool(
        name="netscaler_telnet",
        description=(
            "Test TCP port connectivity from the NetScaler appliance using telnet via "
            "`shell sh -c '/usr/bin/telnet HOST PORT </dev/null'`. NetScaler ADC has telnet "
            "but not netcat/nc or GNU timeout. Returns verdict open/refused/no_response. "
            "Ignore 'ERROR: Export failed' CLI noise when telnet shows Connected to."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler SSH username"},
                "password": {"type": "string", "description": "NetScaler SSH password"},
                "target": {"type": "string", "description": "Destination host or IP to test"},
                "port": {"type": "integer", "description": "TCP port to test (1-65535)"},
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Connect timeout in seconds (default 8, max 20)",
                },
            },
            "required": ["host", "username", "password", "target", "port"],
        },
    ),
    types.Tool(
        name="netscaler_collect_nsconmsg",
        description=(
            "Collect performance statistics and event logs using nsconmsg (read-only). "
            "Runs /netscaler/nsconmsg -K /var/nslog/<newnslog> -d <operation> from the shell — "
            "always read-only (uppercase -K, never -k). Use for performance counters, CPU/memory "
            "stats, event logs, and historical newnslog analysis."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler SSH username"},
                "password": {"type": "string", "description": "NetScaler SSH password"},
                "operation": {
                    "type": "string",
                    "description": "nsconmsg -d operation",
                    "enum": [
                        "current",
                        "stats",
                        "statswt0",
                        "event",
                        "consmsg",
                        "memstats",
                        "settime",
                        "oldconmsg",
                    ],
                },
                "logfile": {
                    "type": "string",
                    "description": "newnslog file name under /var/nslog (default newnslog, e.g. newnslog.100)",
                },
                "counter": {
                    "type": "string",
                    "description": "Optional -g pattern, e.g. cpu_use, mem_err, vsvr_tot_hits",
                },
                "vserver": {
                    "type": "string",
                    "description": "Optional -j LB vserver name (use with oldconmsg)",
                },
                "selectors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional -s selectors: ConLB=1..3, ConMEM=1..3, disptime=1, time=ddmmmyyyy",
                },
                "interval": {
                    "type": "integer",
                    "description": "Optional -T interval in seconds",
                },
            },
            "required": ["host", "username", "password", "operation"],
        },
    ),
    types.Tool(
        name="netscaler_generate_csr",
        description=(
            "Generate an SSL private key and either a CSR (OpenSSL) or a self-signed certificate "
            "(NetScaler classic CLI) under /nsconfig/ssl. Returns PEM output for copy/paste or local use."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler SSH username"},
                "password": {"type": "string", "description": "NetScaler SSH password"},
                "key_name": {"type": "string", "description": "Base name for key/CSR files (no path)"},
                "generation_mode": {
                    "type": "string",
                    "enum": ["csr", "self_signed"],
                    "description": "csr = signing request for a CA; self_signed = NetScaler ROOT_CERT",
                },
                "validity_days": {
                    "type": "integer",
                    "description": "Self-signed certificate validity in days (default 365)",
                },
                "cert_type": {
                    "type": "string",
                    "enum": ["standard", "wildcard", "san"],
                    "description": "Certificate type",
                },
                "key_type": {
                    "type": "string",
                    "enum": ["rsa", "ecdsa"],
                    "description": "Private key algorithm",
                },
                "key_size": {
                    "type": "integer",
                    "description": "RSA key size (2048, 3072, or 4096)",
                },
                "key_password": {
                    "type": "string",
                    "description": "Optional password to encrypt the private key",
                },
                "common_name": {"type": "string", "description": "Certificate common name (CN)"},
                "country": {"type": "string", "description": "Country code (C), e.g. US"},
                "state": {"type": "string", "description": "State or province (ST)"},
                "locality": {"type": "string", "description": "City or locality (L)"},
                "organization": {"type": "string", "description": "Organization (O)"},
                "organizational_unit": {"type": "string", "description": "Organizational unit (OU)"},
                "email": {"type": "string", "description": "Email address"},
                "subject_alt_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "DNS names or IPs for SAN certificates",
                },
            },
            "required": ["host", "username", "password", "key_name", "cert_type", "common_name"],
        },
    ),
    types.Tool(
        name="netscaler_nextgen_request",
        description=(
            "Perform any NetScaler Next-Gen API request (GET, POST, PUT, or DELETE) against a path "
            "relative to /mgmt/api/nextgen/v1/, with an optional JSON body. "
            "Use for creating, updating, or deleting applications, certificates, routes, config_sets, etc. "
            "Confirm the endpoint and payload against the Next-Gen API reference first."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler API username"},
                "password": {"type": "string", "description": "NetScaler API password"},
                "method": {
                    "type": "string",
                    "description": "HTTP method",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                },
                "path": {
                    "type": "string",
                    "description": "Resource path without the /mgmt/api/nextgen/v1 prefix, e.g. applications/app1",
                },
                "body": {
                    "type": "object",
                    "description": "JSON request body for POST/PUT (omit for GET/DELETE)",
                },
            },
            "required": ["host", "username", "password", "method", "path"],
        },
    ),
    # ------------------------------------------------------------------
    # Classic-CLI LB tools (objects visible via show lb vserver)
    # ------------------------------------------------------------------
    types.Tool(
        name="netscaler_create_lb",
        description=(
            "Create an LB vserver with backend servers and services using the classic NetScaler CLI. "
            "Objects are immediately visible via 'show lb vserver'. "
            "dry_run=true previews the command list without touching the appliance; "
            "set confirm=true to actually apply."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "name": {"type": "string", "description": "LB vserver name (also used as prefix for services/servers)"},
                "vip": {"type": "string", "description": "Virtual IP address for the LB vserver"},
                "port": {"type": "integer", "description": "Frontend listener port (default 80)", "default": 80},
                "service_type": {
                    "type": "string",
                    "description": "Protocol for the LB vserver, e.g. HTTP, HTTPS, TCP (default HTTP)",
                    "default": "HTTP",
                },
                "servers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of backend server IP addresses",
                },
                "server_port": {
                    "type": "integer",
                    "description": "Backend port (defaults to port if omitted)",
                },
                "server_protocol": {
                    "type": "string",
                    "description": "Backend protocol (defaults to service_type if omitted)",
                },
                "lb_method": {
                    "type": "string",
                    "description": "Load-balancing method, e.g. ROUNDROBIN, LEASTCONNECTION",
                },
                "persistence": {
                    "type": "string",
                    "description": "Persistence type, e.g. NONE, SOURCEIP, COOKIEINSERT",
                },
                "persistence_timeout": {
                    "type": "integer",
                    "description": "Persistence timeout in minutes (used with persistence)",
                },
                "ssl_certkey": {
                    "type": "string",
                    "description": "SSL certkey name to bind (for HTTPS/SSL vservers)",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "name", "vip", "servers"],
        },
    ),
    types.Tool(
        name="netscaler_modify_lb",
        description=(
            "Modify an existing LB vserver using the classic NetScaler CLI: change lb_method or "
            "persistence, enable/disable the vserver, add new backend servers, or remove services. "
            "dry_run=true previews commands; confirm=true applies them."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "name": {"type": "string", "description": "Name of the existing LB vserver"},
                "lb_method": {
                    "type": "string",
                    "description": "New load-balancing method, e.g. ROUNDROBIN, LEASTCONNECTION",
                },
                "persistence": {
                    "type": "string",
                    "description": "New persistence type, e.g. NONE, SOURCEIP, COOKIEINSERT",
                },
                "persistence_timeout": {
                    "type": "integer",
                    "description": "Persistence timeout in minutes",
                },
                "comment": {
                    "type": "string",
                    "description": "Comment/description to set on the vserver",
                },
                "state": {
                    "type": "string",
                    "enum": ["enable", "disable"],
                    "description": "Set to 'enable' or 'disable' to change vserver state",
                },
                "add_servers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of new backend IP addresses to add as services and bind",
                },
                "remove_services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of service names to unbind and remove",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "name"],
        },
    ),
    types.Tool(
        name="netscaler_delete_lb",
        description=(
            "Delete an LB vserver (and optionally its backing services and servers) using the "
            "classic NetScaler CLI. Safe deletion order: disable → unbind services → rm vserver → "
            "rm services → rm servers. dry_run=true previews; confirm=true applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "name": {"type": "string", "description": "Name of the LB vserver to delete"},
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Service names to unbind and remove (from create_lb serviceNames)",
                },
                "servers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Server names to remove (from create_lb serverNames)",
                },
                "remove_backends": {
                    "type": "boolean",
                    "description": "If true (default), rm service and rm server after removing vserver",
                    "default": True,
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "name"],
        },
    ),
    # ------------------------------------------------------------------
    # Classic-CLI CS tools (objects visible via show cs vserver)
    # ------------------------------------------------------------------
    types.Tool(
        name="netscaler_create_cs",
        description=(
            "Create a Content-Switching vserver with policies using the classic NetScaler CLI. "
            "Objects are immediately visible via 'show cs vserver'. "
            "classic CLI; visible via show cs vserver; dry_run previews, confirm applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "name": {"type": "string", "description": "CS vserver name"},
                "vip": {"type": "string", "description": "Virtual IP address for the CS vserver"},
                "service_type": {
                    "type": "string",
                    "description": "Protocol for the CS vserver, e.g. HTTP, HTTPS, TCP (default HTTP)",
                    "default": "HTTP",
                },
                "port": {
                    "type": "integer",
                    "description": "Frontend listener port (default 80)",
                    "default": 80,
                },
                "policies": {
                    "type": "array",
                    "description": "List of CS policies to create and bind",
                    "items": {
                        "type": "object",
                        "properties": {
                            "policy_name": {"type": "string", "description": "CS policy name"},
                            "rule": {
                                "type": "string",
                                "description": "Policy expression, e.g. HTTP.REQ.HOSTNAME.EQ(\"app1.example.com\")",
                            },
                            "target_lb_vserver": {
                                "type": "string",
                                "description": "Name of the LB vserver to forward matching traffic to",
                            },
                            "priority": {
                                "type": "integer",
                                "description": "Bind priority (lower = higher priority, default 100)",
                            },
                        },
                        "required": ["policy_name", "rule", "target_lb_vserver"],
                    },
                },
                "default_lb_vserver": {
                    "type": "string",
                    "description": "Default LB vserver for unmatched traffic (set cs vserver -lbvserver)",
                },
                "ssl_certkey": {
                    "type": "string",
                    "description": "SSL certkey name to bind (for HTTPS/SSL CS vservers)",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "name", "vip"],
        },
    ),
    types.Tool(
        name="netscaler_modify_cs",
        description=(
            "Modify an existing Content-Switching vserver using the classic NetScaler CLI: "
            "update a CS policy rule, rebind a policy with a new target or priority, change the "
            "default LB vserver, enable/disable the vserver, or add a new policy. "
            "classic CLI; visible via show cs vserver; dry_run previews, confirm applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "name": {"type": "string", "description": "Name of the existing CS vserver"},
                "set_policy_rule": {
                    "type": "object",
                    "description": "Update the expression of an existing CS policy",
                    "properties": {
                        "policy_name": {"type": "string", "description": "CS policy name to update"},
                        "rule": {"type": "string", "description": "New policy expression"},
                    },
                    "required": ["policy_name", "rule"],
                },
                "rebind_policy": {
                    "type": "object",
                    "description": "Unbind then re-bind a policy to change its target LB vserver or priority",
                    "properties": {
                        "policy_name": {"type": "string", "description": "CS policy name"},
                        "target_lb_vserver": {"type": "string", "description": "New target LB vserver"},
                        "priority": {"type": "integer", "description": "New bind priority"},
                    },
                    "required": ["policy_name", "target_lb_vserver"],
                },
                "default_lb_vserver": {
                    "type": "string",
                    "description": "New default LB vserver for unmatched traffic",
                },
                "state": {
                    "type": "string",
                    "enum": ["enable", "disable"],
                    "description": "Set to 'enable' or 'disable' to change CS vserver state",
                },
                "add_policy": {
                    "type": "object",
                    "description": "Add a brand-new CS policy and bind it to the vserver",
                    "properties": {
                        "policy_name": {"type": "string", "description": "New CS policy name"},
                        "rule": {"type": "string", "description": "Policy expression"},
                        "target_lb_vserver": {"type": "string", "description": "Target LB vserver"},
                        "priority": {"type": "integer", "description": "Bind priority (default 100)"},
                    },
                    "required": ["policy_name", "rule", "target_lb_vserver"],
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "name"],
        },
    ),
    types.Tool(
        name="netscaler_delete_cs",
        description=(
            "Delete a Content-Switching vserver (and optionally its CS policies) using the "
            "classic NetScaler CLI. Safe deletion order: disable → unbind policies → rm vserver → "
            "rm policies. classic CLI; visible via show cs vserver; dry_run previews, confirm applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "name": {"type": "string", "description": "Name of the CS vserver to delete"},
                "policies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CS policy names to unbind from the vserver before deletion",
                },
                "remove_policies": {
                    "type": "boolean",
                    "description": "If true (default), rm cs policy for each policy after removing vserver",
                    "default": True,
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "name"],
        },
    ),
    # ------------------------------------------------------------------
    # Classic-CLI Rewrite tools (objects visible via show rewrite policy)
    # ------------------------------------------------------------------
    types.Tool(
        name="netscaler_create_rewrite",
        description=(
            "Create a NetScaler rewrite action and policy using the classic CLI, then optionally bind "
            "to an LB or CS vserver. classic CLI; visible via show rewrite policy; "
            "dry_run previews, confirm applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "action_name": {"type": "string", "description": "Name for the rewrite action"},
                "action_type": {
                    "type": "string",
                    "enum": ["insert_http_header", "delete_http_header", "replace"],
                    "description": "Rewrite action type",
                },
                "target": {
                    "type": "string",
                    "description": (
                        "Header name (insert_http_header/delete_http_header) "
                        "or expression to replace (replace), e.g. X-Frame-Options or HTTP.REQ.HEADER(\"Host\")"
                    ),
                },
                "expression": {
                    "type": "string",
                    "description": (
                        "Value expression (required for insert_http_header and replace). "
                        "Must be a quoted NetScaler expression, e.g. '\"SAMEORIGIN\"'"
                    ),
                },
                "policy_name": {"type": "string", "description": "Name for the rewrite policy"},
                "rule": {
                    "type": "string",
                    "description": "Policy match expression, e.g. HTTP.RES.IS_VALID",
                },
                "bind_to": {
                    "type": "object",
                    "description": "Optional: bind the policy to an LB or CS vserver after creation",
                    "properties": {
                        "entity_type": {
                            "type": "string",
                            "enum": ["lb", "cs"],
                            "description": "Vserver type to bind to",
                        },
                        "vserver": {"type": "string", "description": "Vserver name"},
                        "bind_point": {
                            "type": "string",
                            "enum": ["REQUEST", "RESPONSE"],
                            "description": "Bind point: REQUEST or RESPONSE (default REQUEST)",
                        },
                        "priority": {"type": "integer", "description": "Bind priority (default 100)"},
                    },
                    "required": ["entity_type", "vserver"],
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "action_name", "action_type", "target", "policy_name", "rule"],
        },
    ),
    types.Tool(
        name="netscaler_modify_rewrite",
        description=(
            "Modify an existing NetScaler rewrite policy using the classic CLI: update the rule, "
            "unbind from a vserver, or rebind to a new vserver/priority. "
            "classic CLI; visible via show rewrite policy; dry_run previews, confirm applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "policy_name": {"type": "string", "description": "Name of the rewrite policy to modify"},
                "set_rule": {
                    "type": "string",
                    "description": "New policy match expression to set",
                },
                "rebind": {
                    "type": "object",
                    "description": "Unbind then re-bind the policy to an LB/CS vserver (changes priority or bind_point)",
                    "properties": {
                        "entity_type": {"type": "string", "enum": ["lb", "cs"]},
                        "vserver": {"type": "string"},
                        "bind_point": {"type": "string", "enum": ["REQUEST", "RESPONSE"]},
                        "priority": {"type": "integer"},
                    },
                    "required": ["entity_type", "vserver"],
                },
                "unbind": {
                    "type": "object",
                    "description": "Unbind the policy from an LB/CS vserver",
                    "properties": {
                        "entity_type": {"type": "string", "enum": ["lb", "cs"]},
                        "vserver": {"type": "string"},
                        "bind_point": {"type": "string", "enum": ["REQUEST", "RESPONSE"]},
                    },
                    "required": ["entity_type", "vserver"],
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "policy_name"],
        },
    ),
    types.Tool(
        name="netscaler_delete_rewrite",
        description=(
            "Delete a NetScaler rewrite policy (and optionally its action) using the classic CLI. "
            "Safe deletion order: unbind from each vserver → rm policy → rm action. "
            "classic CLI; visible via show rewrite policy; dry_run previews, confirm applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "policy_name": {"type": "string", "description": "Name of the rewrite policy to delete"},
                "action_name": {
                    "type": "string",
                    "description": "If provided, also remove this rewrite action after removing the policy",
                },
                "unbind_from": {
                    "type": "array",
                    "description": "Vserver bindings to remove before deleting the policy",
                    "items": {
                        "type": "object",
                        "properties": {
                            "entity_type": {"type": "string", "enum": ["lb", "cs"]},
                            "vserver": {"type": "string"},
                            "bind_point": {"type": "string", "enum": ["REQUEST", "RESPONSE"]},
                        },
                        "required": ["entity_type", "vserver"],
                    },
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "policy_name"],
        },
    ),
    # ------------------------------------------------------------------
    # Classic-CLI Responder tools (objects visible via show responder policy)
    # ------------------------------------------------------------------
    types.Tool(
        name="netscaler_create_responder",
        description=(
            "Create a NetScaler responder action and policy using the classic CLI, then optionally bind "
            "to an LB or CS vserver. Responder bindings have no REQUEST/RESPONSE -type flag. "
            "classic CLI; visible via show responder policy; dry_run previews, confirm applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "action_name": {"type": "string", "description": "Name for the responder action"},
                "action_type": {
                    "type": "string",
                    "enum": ["redirect", "respondwith", "drop", "noop"],
                    "description": "Responder action type. drop/noop take no expression.",
                },
                "expression": {
                    "type": "string",
                    "description": (
                        "Expression for redirect or respondwith (not used for drop/noop). "
                        "e.g. '\"https://\" + HTTP.REQ.HOSTNAME + HTTP.REQ.URL'"
                    ),
                },
                "policy_name": {"type": "string", "description": "Name for the responder policy"},
                "rule": {
                    "type": "string",
                    "description": "Policy match expression, e.g. HTTP.REQ.IS_VALID",
                },
                "bind_to": {
                    "type": "object",
                    "description": "Optional: bind the policy to an LB or CS vserver after creation",
                    "properties": {
                        "entity_type": {
                            "type": "string",
                            "enum": ["lb", "cs"],
                            "description": "Vserver type to bind to",
                        },
                        "vserver": {"type": "string", "description": "Vserver name"},
                        "priority": {"type": "integer", "description": "Bind priority (default 100)"},
                    },
                    "required": ["entity_type", "vserver"],
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "action_name", "action_type", "policy_name", "rule"],
        },
    ),
    types.Tool(
        name="netscaler_modify_responder",
        description=(
            "Modify an existing NetScaler responder policy using the classic CLI: update the rule, "
            "update the action expression, unbind from a vserver, or rebind to a new vserver/priority. "
            "classic CLI; visible via show responder policy; dry_run previews, confirm applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "policy_name": {"type": "string", "description": "Name of the responder policy to modify"},
                "set_rule": {
                    "type": "string",
                    "description": "New policy match expression to set",
                },
                "set_action_expression": {
                    "type": "object",
                    "description": "Update the target expression on a responder action",
                    "properties": {
                        "action_name": {"type": "string", "description": "Responder action name to modify"},
                        "expression": {"type": "string", "description": "New expression (e.g. new redirect URL)"},
                    },
                    "required": ["action_name", "expression"],
                },
                "rebind": {
                    "type": "object",
                    "description": "Unbind then re-bind the policy to change vserver or priority",
                    "properties": {
                        "entity_type": {"type": "string", "enum": ["lb", "cs"]},
                        "vserver": {"type": "string"},
                        "priority": {"type": "integer"},
                    },
                    "required": ["entity_type", "vserver"],
                },
                "unbind": {
                    "type": "object",
                    "description": "Unbind the policy from an LB/CS vserver",
                    "properties": {
                        "entity_type": {"type": "string", "enum": ["lb", "cs"]},
                        "vserver": {"type": "string"},
                    },
                    "required": ["entity_type", "vserver"],
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "policy_name"],
        },
    ),
    types.Tool(
        name="netscaler_delete_responder",
        description=(
            "Delete a NetScaler responder policy (and optionally its action) using the classic CLI. "
            "Safe deletion order: unbind from each vserver → rm policy → rm action. "
            "Responder unbind has no -type flag. "
            "classic CLI; visible via show responder policy; dry_run previews, confirm applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler CLI username"},
                "password": {"type": "string", "description": "NetScaler CLI password"},
                "policy_name": {"type": "string", "description": "Name of the responder policy to delete"},
                "action_name": {
                    "type": "string",
                    "description": "If provided, also remove this responder action after removing the policy",
                },
                "unbind_from": {
                    "type": "array",
                    "description": "Vserver bindings to remove before deleting the policy",
                    "items": {
                        "type": "object",
                        "properties": {
                            "entity_type": {"type": "string", "enum": ["lb", "cs"]},
                            "vserver": {"type": "string"},
                        },
                        "required": ["entity_type", "vserver"],
                    },
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return command list without executing (default false)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually apply changes (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password", "policy_name"],
        },
    ),
    # ------------------------------------------------------------------
    # Log and config inspection tools
    # ------------------------------------------------------------------
    types.Tool(
        name="netscaler_get_logs",
        description=(
            "Return the last N lines of a NetScaler syslog file via SSH (read-only). "
            "Allowed logfiles: ns.log (syslog), messages (BSD messages), nsvpn.log (VPN), "
            "newnslog (binary perf log — use netscaler_collect_nsconmsg for rich analysis). "
            "Useful for recent errors, authentication events, and health-check noise."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler SSH username"},
                "password": {"type": "string", "description": "NetScaler SSH password"},
                "logfile": {
                    "type": "string",
                    "description": "Log file name under /var/log (default ns.log). Allowed: ns.log, messages, nsvpn.log, newnslog",
                    "enum": ["ns.log", "messages", "nsvpn.log", "newnslog"],
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of lines to tail (default 100, max 2000)",
                },
            },
            "required": ["host", "username", "password"],
        },
    ),
    types.Tool(
        name="netscaler_search_config",
        description=(
            "Search the NetScaler running configuration for a keyword using grep (read-only). "
            "Runs 'show ns runningConfig | grep -i <keyword>' over SSH. "
            "Useful for finding all objects related to a VIP, hostname, certificate, or policy name."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler SSH username"},
                "password": {"type": "string", "description": "NetScaler SSH password"},
                "keyword": {
                    "type": "string",
                    "description": (
                        "Search term. Only letters, digits, and _ . : - / are allowed "
                        "(no spaces, pipes, or shell metacharacters)."
                    ),
                },
            },
            "required": ["host", "username", "password", "keyword"],
        },
    ),
    # ------------------------------------------------------------------
    # HA failover tool (guarded write)
    # ------------------------------------------------------------------
    types.Tool(
        name="netscaler_force_failover",
        description=(
            "Trigger a force HA failover on a NetScaler HA pair. "
            "Always runs 'show ha node' first — if the appliance is standalone (not in an HA pair) "
            "the tool returns haConfigured=false and does NOT attempt failover. "
            "On an HA-configured pair: dry_run=true or confirm=false returns a preview; "
            "set confirm=true to actually run 'force HA failover -force'. "
            "Safe to call on a standalone lab box — it will report not applicable."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "NetScaler hostname or IP"},
                "username": {"type": "string", "description": "NetScaler SSH username"},
                "password": {"type": "string", "description": "NetScaler SSH password"},
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to actually trigger failover on an HA pair (default false)",
                    "default": False,
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, preview mode only — do not trigger failover (default false)",
                    "default": False,
                },
            },
            "required": ["host", "username", "password"],
        },
    ),
]


def get_enabled_tools() -> list[types.Tool]:
    from app.services.config_service import is_tool_enabled

    return [tool for tool in NETSCALER_TOOLS if is_tool_enabled(tool.name)]


def _tool_error(message: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=format_tool_result({"success": False, "message": message}))]


async def _run_nextgen_tool(action):
    try:
        data = await action()
        return [types.TextContent(type="text", text=format_tool_result(data))]
    except httpx.ConnectError:
        return _tool_error(
            "Could not connect to the appliance — check hostname/IP, HTTPS (port 443), "
            "and that Next-Gen API is enabled (`enable ns nextgenapi`)"
        )
    except httpx.TimeoutException:
        return _tool_error("Connection timed out reaching the appliance")
    except ValueError as exc:
        message = str(exc)
        if "invalid" in message.lower() or "password" in message.lower() or "authentication" in message.lower():
            return _tool_error("Authentication failed — invalid username or password")
        return _tool_error(message)
    except Exception as exc:
        return _tool_error(str(exc))


async def call_netscaler_tool(name: str, arguments: dict) -> list[types.TextContent]:
    from app.services.config_service import is_tool_enabled

    if not is_tool_enabled(name):
        raise ValueError(f"Tool '{name}' is disabled in MCP server configuration")

    host = arguments.get("host", "")
    username = arguments.get("username", "")
    password = arguments.get("password", "")

    if name == "netscaler_test_connection":
        success, message = await test_appliance_connection(host, username, password)
        payload = {"success": success, "message": message}
        return [types.TextContent(type="text", text=format_tool_result(payload))]

    if name == "netscaler_get_system_info":
        return await _run_nextgen_tool(lambda: get_system_info(host, username, password))

    if name == "netscaler_list_applications":
        return await _run_nextgen_tool(lambda: list_applications(host, username, password))

    if name == "netscaler_list_virtual_servers":
        return await _run_nextgen_tool(lambda: list_virtual_servers(host, username, password))

    if name == "netscaler_list_service_status":
        down_only = arguments.get("down_only", True)
        return await _run_nextgen_tool(
            lambda: list_service_status(host, username, password, down_only=bool(down_only))
        )

    if name == "netscaler_create_application":
        app_name = arguments.get("name", "").strip()
        virtual_ip = arguments.get("virtual_ip", "").strip()
        port = int(arguments.get("port", 80))
        protocol = arguments.get("protocol", "HTTP").strip()
        servers = arguments.get("servers") or []
        if not app_name:
            return _tool_error("name is required")
        if not virtual_ip:
            return _tool_error("virtual_ip is required")
        if not servers:
            return _tool_error("servers is required — at least one backend IP")
        servers_port = arguments.get("servers_port")
        servers_protocol = arguments.get("servers_protocol")
        return await _run_nextgen_tool(
            lambda: create_application(
                host,
                username,
                password,
                app_name,
                virtual_ip,
                port,
                protocol,
                servers,
                servers_port=int(servers_port) if servers_port is not None else None,
                servers_protocol=str(servers_protocol).strip() if servers_protocol else None,
            )
        )

    if name == "netscaler_list_virtual_ips":
        return await _run_nextgen_tool(lambda: list_virtual_ips(host, username, password))

    if name == "netscaler_list_ip_addresses":
        return await _run_nextgen_tool(lambda: list_ip_addresses(host, username, password))

    if name == "netscaler_nextgen_get":
        path = arguments.get("path", "").strip().lstrip("/")
        if not path:
            return _tool_error("path is required")
        return await _run_nextgen_tool(lambda: nextgen_get(host, username, password, path))

    if name == "netscaler_add_ip_address":
        ip_address = arguments.get("ip_address", "").strip()
        ip_type = arguments.get("ip_type", "VIP").strip()
        netmask = arguments.get("netmask", "255.255.255.0").strip()
        save_config = arguments.get("save_config", True)
        if not ip_address:
            return _tool_error("ip_address is required")
        if not ip_type:
            return _tool_error("ip_type is required")
        return await _run_nextgen_tool(
            lambda: add_ip_address(
                host,
                username,
                password,
                ip_address,
                ip_type,
                netmask,
                save_config=bool(save_config),
            )
        )

    if name == "netscaler_ssh_run_command":
        command = arguments.get("command", "").strip()
        purpose = arguments.get("purpose", "").strip()
        if not command:
            return _tool_error("command is required")
        if not purpose:
            return _tool_error("purpose is required — confirm why this CLI command is needed")
        return await _run_nextgen_tool(
            lambda: ssh_run_command(host, username, password, command)
        )

    if name == "netscaler_run_cli_command":
        command = arguments.get("command", "").strip()
        purpose = arguments.get("purpose", "").strip()
        if not command:
            return _tool_error("command is required")
        if not purpose:
            return _tool_error("purpose is required — confirm why this CLI command is needed")
        return await _run_nextgen_tool(
            lambda: run_cli_command(host, username, password, command)
        )

    if name == "netscaler_run_cli_commands":
        commands = arguments.get("commands") or []
        purpose = arguments.get("purpose", "").strip()
        if not commands:
            return _tool_error("commands is required — provide at least one CLI command")
        if not purpose:
            return _tool_error("purpose is required — confirm why this command sequence is needed")
        return await _run_nextgen_tool(
            lambda: run_cli_commands(host, username, password, commands)
        )

    if name == "netscaler_run_diagnostic":
        operation = arguments.get("operation", "").strip()
        target = arguments.get("target", "").strip()
        if not operation:
            return _tool_error("operation is required (ping, ping6, traceroute, traceroute6, tcp_port)")
        if not target:
            return _tool_error("target host or IP is required")
        count = arguments.get("count")
        max_hops = arguments.get("max_hops")
        port = arguments.get("port")
        if operation == "tcp_port" and port is None:
            return _tool_error("port is required for tcp_port operation (1-65535)")
        return await _run_nextgen_tool(
            lambda: run_diagnostic(
                host,
                username,
                password,
                operation,
                target,
                count=int(count) if count is not None else None,
                max_hops=int(max_hops) if max_hops is not None else None,
                port=int(port) if port is not None else None,
            )
        )

    if name == "netscaler_telnet":
        target = arguments.get("target", "").strip()
        port = arguments.get("port")
        if not target:
            return _tool_error("target host or IP is required")
        if port is None:
            return _tool_error("port is required (1-65535)")
        timeout_seconds = arguments.get("timeout_seconds")
        return await _run_nextgen_tool(
            lambda: run_telnet(
                host,
                username,
                password,
                target,
                int(port),
                timeout_seconds=int(timeout_seconds) if timeout_seconds is not None else None,
            )
        )

    if name == "netscaler_collect_nsconmsg":
        operation = arguments.get("operation", "").strip()
        if not operation:
            return _tool_error("operation is required (current, stats, event, memstats, oldconmsg, ...)")
        interval = arguments.get("interval")
        return await _run_nextgen_tool(
            lambda: run_nsconmsg(
                host,
                username,
                password,
                operation,
                logfile=(arguments.get("logfile") or "newnslog"),
                counter=arguments.get("counter"),
                vserver=arguments.get("vserver"),
                selectors=arguments.get("selectors") or [],
                interval=int(interval) if interval is not None else None,
            )
        )

    if name == "netscaler_generate_csr":
        key_name = arguments.get("key_name", "").strip()
        cert_type = arguments.get("cert_type", "").strip()
        common_name = arguments.get("common_name", "").strip()
        if not key_name:
            return _tool_error("key_name is required")
        if not cert_type:
            return _tool_error("cert_type is required (standard, wildcard, or san)")
        if not common_name:
            return _tool_error("common_name is required")
        csr_params = {
            "key_name": key_name,
            "cert_type": cert_type,
            "generation_mode": arguments.get("generation_mode", "csr"),
            "validity_days": arguments.get("validity_days", 365),
            "key_type": arguments.get("key_type", "rsa"),
            "key_size": arguments.get("key_size", 2048),
            "key_password": arguments.get("key_password"),
            "common_name": common_name,
            "country": arguments.get("country", "US"),
            "state": arguments.get("state", ""),
            "locality": arguments.get("locality", ""),
            "organization": arguments.get("organization", ""),
            "organizational_unit": arguments.get("organizational_unit", ""),
            "email": arguments.get("email"),
            "subject_alt_names": arguments.get("subject_alt_names") or [],
        }
        mode = str(arguments.get("generation_mode", "csr")).strip().lower()
        if mode == "self_signed":
            return await _run_nextgen_tool(
                lambda: generate_ssl_self_signed(host, username, password, csr_params)
            )
        return await _run_nextgen_tool(
            lambda: generate_ssl_csr(host, username, password, csr_params)
        )

    if name == "netscaler_nextgen_request":
        method = arguments.get("method", "GET").strip().upper()
        path = arguments.get("path", "").strip().lstrip("/")
        body = arguments.get("body")
        if not path:
            return _tool_error("path is required")
        if body is not None and not isinstance(body, dict):
            return _tool_error("body must be a JSON object")
        return await _run_nextgen_tool(
            lambda: nextgen_request(host, username, password, method, path, body)
        )

    if name == "netscaler_create_lb":
        lb_name = arguments.get("name", "").strip()
        vip = arguments.get("vip", "").strip()
        servers = arguments.get("servers") or []
        if not lb_name:
            return _tool_error("name is required")
        if not vip:
            return _tool_error("vip is required")
        if not servers:
            return _tool_error("servers is required — at least one backend IP")
        port = arguments.get("port", 80)
        server_port = arguments.get("server_port")
        persistence_timeout = arguments.get("persistence_timeout")
        return await _run_nextgen_tool(
            lambda: create_lb(
                host,
                username,
                password,
                lb_name,
                vip,
                servers,
                service_type=str(arguments.get("service_type", "HTTP")).strip(),
                port=int(port),
                server_port=int(server_port) if server_port is not None else None,
                server_protocol=str(arguments.get("server_protocol")).strip() if arguments.get("server_protocol") else None,
                lb_method=str(arguments.get("lb_method")).strip() if arguments.get("lb_method") else None,
                persistence=str(arguments.get("persistence")).strip() if arguments.get("persistence") else None,
                persistence_timeout=int(persistence_timeout) if persistence_timeout is not None else None,
                ssl_certkey=str(arguments.get("ssl_certkey")).strip() if arguments.get("ssl_certkey") else None,
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_modify_lb":
        lb_name = arguments.get("name", "").strip()
        if not lb_name:
            return _tool_error("name is required")
        persistence_timeout = arguments.get("persistence_timeout")
        return await _run_nextgen_tool(
            lambda: modify_lb(
                host,
                username,
                password,
                lb_name,
                lb_method=str(arguments.get("lb_method")).strip() if arguments.get("lb_method") else None,
                persistence=str(arguments.get("persistence")).strip() if arguments.get("persistence") else None,
                persistence_timeout=int(persistence_timeout) if persistence_timeout is not None else None,
                comment=str(arguments.get("comment")) if arguments.get("comment") is not None else None,
                state=str(arguments.get("state")).strip().lower() if arguments.get("state") else None,
                add_servers=list(arguments.get("add_servers")) if arguments.get("add_servers") else None,
                remove_services=list(arguments.get("remove_services")) if arguments.get("remove_services") else None,
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_delete_lb":
        lb_name = arguments.get("name", "").strip()
        if not lb_name:
            return _tool_error("name is required")
        return await _run_nextgen_tool(
            lambda: delete_lb(
                host,
                username,
                password,
                lb_name,
                services=list(arguments.get("services")) if arguments.get("services") else None,
                servers=list(arguments.get("servers")) if arguments.get("servers") else None,
                remove_backends=bool(arguments.get("remove_backends", True)),
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_create_cs":
        cs_name = arguments.get("name", "").strip()
        vip = arguments.get("vip", "").strip()
        if not cs_name:
            return _tool_error("name is required")
        if not vip:
            return _tool_error("vip is required")
        port = arguments.get("port", 80)
        return await _run_nextgen_tool(
            lambda: create_cs(
                host,
                username,
                password,
                cs_name,
                vip,
                service_type=str(arguments.get("service_type", "HTTP")).strip(),
                port=int(port),
                policies=list(arguments.get("policies")) if arguments.get("policies") else None,
                default_lb_vserver=str(arguments.get("default_lb_vserver")).strip() if arguments.get("default_lb_vserver") else None,
                ssl_certkey=str(arguments.get("ssl_certkey")).strip() if arguments.get("ssl_certkey") else None,
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_modify_cs":
        cs_name = arguments.get("name", "").strip()
        if not cs_name:
            return _tool_error("name is required")
        return await _run_nextgen_tool(
            lambda: modify_cs(
                host,
                username,
                password,
                cs_name,
                set_policy_rule=dict(arguments.get("set_policy_rule")) if arguments.get("set_policy_rule") else None,
                rebind_policy=dict(arguments.get("rebind_policy")) if arguments.get("rebind_policy") else None,
                default_lb_vserver=str(arguments.get("default_lb_vserver")).strip() if arguments.get("default_lb_vserver") else None,
                state=str(arguments.get("state")).strip().lower() if arguments.get("state") else None,
                add_policy=dict(arguments.get("add_policy")) if arguments.get("add_policy") else None,
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_delete_cs":
        cs_name = arguments.get("name", "").strip()
        if not cs_name:
            return _tool_error("name is required")
        return await _run_nextgen_tool(
            lambda: delete_cs(
                host,
                username,
                password,
                cs_name,
                policies=list(arguments.get("policies")) if arguments.get("policies") else None,
                remove_policies=bool(arguments.get("remove_policies", True)),
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_create_rewrite":
        action_name = arguments.get("action_name", "").strip()
        action_type = arguments.get("action_type", "").strip()
        target = arguments.get("target", "").strip()
        policy_name = arguments.get("policy_name", "").strip()
        rule = arguments.get("rule", "").strip()
        if not action_name:
            return _tool_error("action_name is required")
        if not action_type:
            return _tool_error("action_type is required")
        if not target:
            return _tool_error("target is required")
        if not policy_name:
            return _tool_error("policy_name is required")
        if not rule:
            return _tool_error("rule is required")
        return await _run_nextgen_tool(
            lambda: create_rewrite(
                host,
                username,
                password,
                action_name,
                action_type,
                target,
                policy_name,
                rule,
                expression=str(arguments.get("expression")).strip() if arguments.get("expression") else None,
                bind_to=dict(arguments.get("bind_to")) if arguments.get("bind_to") else None,
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_modify_rewrite":
        policy_name = arguments.get("policy_name", "").strip()
        if not policy_name:
            return _tool_error("policy_name is required")
        return await _run_nextgen_tool(
            lambda: modify_rewrite(
                host,
                username,
                password,
                policy_name,
                set_rule=str(arguments.get("set_rule")) if arguments.get("set_rule") is not None else None,
                rebind=dict(arguments.get("rebind")) if arguments.get("rebind") else None,
                unbind=dict(arguments.get("unbind")) if arguments.get("unbind") else None,
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_delete_rewrite":
        policy_name = arguments.get("policy_name", "").strip()
        if not policy_name:
            return _tool_error("policy_name is required")
        return await _run_nextgen_tool(
            lambda: delete_rewrite(
                host,
                username,
                password,
                policy_name,
                action_name=str(arguments.get("action_name")).strip() if arguments.get("action_name") else None,
                unbind_from=list(arguments.get("unbind_from")) if arguments.get("unbind_from") else None,
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_create_responder":
        action_name = arguments.get("action_name", "").strip()
        action_type = arguments.get("action_type", "").strip()
        policy_name = arguments.get("policy_name", "").strip()
        rule = arguments.get("rule", "").strip()
        if not action_name:
            return _tool_error("action_name is required")
        if not action_type:
            return _tool_error("action_type is required")
        if not policy_name:
            return _tool_error("policy_name is required")
        if not rule:
            return _tool_error("rule is required")
        return await _run_nextgen_tool(
            lambda: create_responder(
                host,
                username,
                password,
                action_name,
                action_type,
                policy_name,
                rule,
                expression=str(arguments.get("expression")).strip() if arguments.get("expression") else None,
                bind_to=dict(arguments.get("bind_to")) if arguments.get("bind_to") else None,
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_modify_responder":
        policy_name = arguments.get("policy_name", "").strip()
        if not policy_name:
            return _tool_error("policy_name is required")
        return await _run_nextgen_tool(
            lambda: modify_responder(
                host,
                username,
                password,
                policy_name,
                set_rule=str(arguments.get("set_rule")) if arguments.get("set_rule") is not None else None,
                set_action_expression=dict(arguments.get("set_action_expression")) if arguments.get("set_action_expression") else None,
                rebind=dict(arguments.get("rebind")) if arguments.get("rebind") else None,
                unbind=dict(arguments.get("unbind")) if arguments.get("unbind") else None,
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_delete_responder":
        policy_name = arguments.get("policy_name", "").strip()
        if not policy_name:
            return _tool_error("policy_name is required")
        return await _run_nextgen_tool(
            lambda: delete_responder(
                host,
                username,
                password,
                policy_name,
                action_name=str(arguments.get("action_name")).strip() if arguments.get("action_name") else None,
                unbind_from=list(arguments.get("unbind_from")) if arguments.get("unbind_from") else None,
                dry_run=bool(arguments.get("dry_run", False)),
                confirm=bool(arguments.get("confirm", False)),
            )
        )

    if name == "netscaler_get_logs":
        logfile = str(arguments.get("logfile", "ns.log")).strip()
        lines = arguments.get("lines", 100)
        return await _run_nextgen_tool(
            lambda: get_logs(
                host,
                username,
                password,
                logfile=logfile,
                lines=int(lines),
            )
        )

    if name == "netscaler_search_config":
        keyword = str(arguments.get("keyword", "")).strip()
        if not keyword:
            return _tool_error("keyword is required")
        return await _run_nextgen_tool(
            lambda: search_config(host, username, password, keyword)
        )

    if name == "netscaler_force_failover":
        return await _run_nextgen_tool(
            lambda: force_failover(
                host,
                username,
                password,
                confirm=bool(arguments.get("confirm", False)),
                dry_run=bool(arguments.get("dry_run", False)),
            )
        )

    raise ValueError(f"Unknown tool: {name}")
