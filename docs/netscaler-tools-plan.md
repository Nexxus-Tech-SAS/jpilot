# NetScaler MCP Tools — Capability Plan

> Working document. Goal: list the NetScaler capabilities we want JPilot to have, and
> for each one decide whether it's already covered by an existing MCP tool, partially
> covered, or needs a brand-new tool.

## Legend
- ✅ **Existing** — fully achievable now; tool named.
- ⚠️ **Partial** — possible via a generic tool, but error-prone / unstructured; a dedicated tool is recommended.
- 🆕 **New tool** — not achievable / not safe today; needs a new MCP tool.
- ❓ **Verify** — believed possible, must be confirmed live during implementation.

> Two generic escape hatches already exist: `netscaler_nextgen_request` (any Next-Gen API
> call) and `netscaler_run_cli_command(s)` (any CLI command, incl. writes). So many capabilities
> are *technically* reachable today — the verdicts below distinguish "possible via a generic
> tool" from "deserves a dedicated, safe, structured tool."

---

## Section 1 — Inspection / `show` commands
All read-only and run today via `netscaler_run_cli_command`. Some also have dedicated structured tools.

| Command | Verdict | Maps to |
|---|---|---|
| show ns version | ✅ | run_cli_command; also netscaler_get_system_info |
| show ns ip | ✅ | run_cli_command; also netscaler_list_ip_addresses |
| show interface | ✅ | run_cli_command (no dedicated tool) |
| show vlan | ✅ | run_cli_command (no dedicated tool) |
| show route | ✅ | run_cli_command (no dedicated tool) |
| show arp | ✅ | run_cli_command (no dedicated tool) |
| show ha node | ✅ | run_cli_command (no dedicated tool) |
| show ns runningConfig | ✅ | run_cli_command |
| show ns savedConfig | ✅ | run_cli_command |
| show ns feature | ✅ | run_cli_command |
| show ns mode | ✅ | run_cli_command |
| show license | ✅ | run_cli_command |
| show system user | ✅ | run_cli_command |
| show lb vserver [name] | ✅ | run_cli_command; also netscaler_list_virtual_servers |
| show cs vserver [name] | ✅ | run_cli_command (no dedicated tool) |
| show service [name] | ✅ | run_cli_command; partial via netscaler_list_service_status |
| show serviceGroup [name] | ✅ | run_cli_command (no dedicated tool) |
| show server [name] | ✅ | run_cli_command (no dedicated tool) |
| show ssl certKey | ✅ | run_cli_command (no dedicated tool) |
| show ns connectiontable | ✅ | run_cli_command |

Recommendation: keep `run_cli_command` for ad-hoc; optionally add per-object read tools later
for structured JSON output. Not required.

## Section 2 — Shell diagnostics
| Command | Verdict | Notes |
|---|---|---|
| nsconmsg -K /var/nslog/newnslog -d event | ✅ | netscaler_collect_nsconmsg(operation="event") |
| nsconmsg -K /var/nslog/newnslog -d stats | ✅ | netscaler_collect_nsconmsg(operation="stats") |
| tail -f /var/log/ns.log | 🆕 | shell `tail` is blocked (BSD-shell breakout) AND `-f` streaming is incompatible with request/response MCP. New tool: **netscaler_get_logs(logfile, lines)** returning last N lines (no follow). |
| tail -f /var/log/messages | 🆕 | Same new tool, `logfile="messages"`. |

## Section 3 — High Availability
| Command | Verdict | Notes |
|---|---|---|
| show ha node | ✅ | run_cli_command (read). Can't test now (single node). |
| force failover | ⚠️→🆕 | Technically allowed via run_cli_command (write path permits any verb), but DANGEROUS. New dedicated **netscaler_force_failover** with explicit confirmation flag + HA-state precheck. |

## Section 4 — Config filtering
| Command | Verdict | Notes |
|---|---|---|
| show ns runningConfig \| grep <kw> | ❓→⚠️ | `show` + pipe should pass the read validator (pipe/grep not blocked), and NetScaler CLI supports `\| grep`. Must verify the pipe survives over SSH. New **netscaler_search_config(keyword)** for safe, structured filtering. |
| show run \| grep <kw> | ❓→⚠️ | Same; `show run` is an alias of `show ns runningConfig`. |

## Section 5 — Objectives: LB / CS / Rewrite / Responder lifecycles
The four supplied topics:
1. Create / delete / modify a Load Balancer
2. Create / delete / modify Content Switching and CS policies
3. Create / delete / modify Rewrite actions and policies
4. Create / delete / modify Responder actions and policies

Every `add/set/bind/unbind/rm/enable/disable/save` command is a write verb that
`netscaler_run_cli_command(s)` already accepts (validate_writable allows any verb). So all four
lifecycles are ⚠️ **possible today via raw CLI** — but multi-step, order-sensitive config via raw
strings is error-prone and unguarded. We will wrap them in goal tools.

### Section 5b — Can each topic collapse into a SINGLE Next-Gen API request?
Verified against the live API (only `applications` + `config_sets` resources exist) and the
official Next-Gen guide. The Next-Gen API is **declarative / desired-state**:

| Topic | Single Next-Gen request? | How |
|---|---|---|
| 1. Load Balancer | ✅ Yes | `POST /applications/{name}` declares VIP+protocol+port+certs+servers+LB basics in one body. Already `netscaler_create_application`. Modify = re-POST (upsert) / PUT sub-resources. Delete = `DELETE /applications/{name}`. |
| 2. Content Switching | ⚠️ Yes, via config_set | NOT an `application` property. Express CS routing as a **`config_set`** in one `POST /config_sets/{name}`, or via CLI. |
| 3. Rewrite | ⚠️ Yes, via config_set | NOT an `application` property. Push action+policy+bindings as one **`config_set`**. |
| 4. Responder | ⚠️ Yes, via config_set | Same as rewrite. (`responder_html_pages` is a separate first-class resource for custom pages.) |

**Key finding:** `config_sets` (`POST /config_sets/{name}`) is the official mechanism to
*"define any NetScaler configuration"* in one declarative request — bridging NITRO's power with
the Next-Gen desired-state model. So all four topics can each be reduced to a single Next-Gen
request (Topic 1 via `applications`, Topics 2–4 via `config_sets`), with atomic apply and
desired-state delete (`DELETE /config_sets/{name}`) replacing the fragile "disable → unbind → rm".

⚠️ The exact `config_set` body schema is being confirmed live (the guide shows none). If it
can't cleanly model CS/Rewrite/Responder on this firmware (NS14.1 build 66.59), the fallback is
guarded ordered CLI via `netscaler_run_cli_commands` — same external tool contract.

### Recommended tool design (goal-based, declarative under the hood)
One tool per objective×action, each building the right `applications` or `config_set` body
internally so the model never has to discover syntax. **All write tools support dry-run/preview
and require an explicit confirm flag to commit.**
- LB: ✅ extend `netscaler_create_application`; 🆕 `netscaler_modify_lb`, `netscaler_delete_lb`.
- CS: 🆕 `netscaler_create_cs`, `netscaler_modify_cs`, `netscaler_delete_cs`.
- Rewrite: 🆕 `netscaler_create_rewrite`, `netscaler_modify_rewrite`, `netscaler_delete_rewrite`.
- Responder: 🆕 `netscaler_create_responder`, `netscaler_modify_responder`, `netscaler_delete_responder`.
- Diagnostics: 🆕 `netscaler_get_logs`, 🆕 `netscaler_search_config`, 🆕 `netscaler_force_failover`.
- Shared internal helper: `apply_config_set` / `delete_config_set` (not necessarily model-facing).
- ⚠️ Keep `run_cli_command(s)` + the search tools as LAST-RESORT fallback only.

## Section 6 — Design decisions (resolved)
1. **Declarative-first:** `applications` + `config_sets` primary; `run_cli_command(s)` fallback.
2. **config_set body contract:** confirmed live before tool bodies are finalized.
3. **Safety rails:** dry-run/preview + explicit confirm flag for all writes (create/modify/delete +
   force_failover); auto-save on commit (lab).
4. **Granularity:** typed goal tools per objective (a shared `apply_config_set` helper underneath).
5. **Search demotion:** dedicated tools are the fast path; search/reference tools are last-resort,
   and their results will point at the dedicated MCP tool to use.

---

## Appendix A — Existing MCP tools (all verified working as of this session)

### NetScaler (18)
| Tool | What it does |
|------|--------------|
| netscaler_test_connection | Auth/connectivity check via Next-Gen API |
| netscaler_get_system_info | Mgmt IP, firmware, hostname, serial, app count |
| netscaler_list_applications | Next-Gen API applications |
| netscaler_list_virtual_ips | LB virtual IPs from applications |
| netscaler_list_ip_addresses | All IPs: NSIP, SNIP, VIP, servers, app IPs |
| netscaler_list_virtual_servers | Classic lb vservers |
| netscaler_list_service_status | Service/up-down status |
| netscaler_nextgen_get | Read-only GET on any Next-Gen API path |
| netscaler_nextgen_request | Arbitrary Next-Gen API request (GET/POST/PUT/DELETE) |
| netscaler_create_application | Create application-centric LB config (VIP+servers) |
| netscaler_add_ip_address | Add classic NSIP/SNIP/VIP (NITRO) — fixed this session |
| netscaler_ssh_run_command | Run a read-only command over SSH |
| netscaler_run_cli_command | Run a single CLI command (write-capable) |
| netscaler_run_cli_commands | Run multiple CLI commands (write-capable) |
| netscaler_run_diagnostic | ping / traceroute style diagnostics |
| netscaler_telnet | TCP port reachability probe from the appliance |
| netscaler_collect_nsconmsg | Read-only nsconmsg perf/counter collection |
| netscaler_generate_csr | Generate private key + CSR on the appliance |

### Other families (SSH-based; not hardware-verified)
- Cisco (4): cisco_test_connection, cisco_ssh_run_command, cisco_run_cli_command, cisco_run_cli_commands
- F5 (4): f5_test_connection, f5_ssh_run_command, f5_run_tmsh_command, f5_run_tmsh_commands
- SDX (4): sdx_test_connection, sdx_ssh_run_command, sdx_run_cli_command, sdx_run_cli_commands
