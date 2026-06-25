# O6 — Reconcile legacy NL/form LB auto-deploy with `netscaler_create_lb` (single LB executor)

**Date:** 2026-06-25
**Operator finding:** R3 — "ONE executor for LB provisioning."
**Type:** READ-ONLY design pass. No code changed.
**Prereq read:** `docs/role-audits/operator-findings.md` (RC-1..RC-5, P1-A..P2-C). This plan extends those
findings: the operator-findings doc fixed the *dedicated-tool selection trap*; it did **not** touch
`copilot_deploy.py`, which is the second, divergent LB write path this plan reconciles.

---

## 0. Live evidence recap

Backend log showed the model emitting raw CLI for an LB create:

```
add lb vserver my_jp_lb HTTP 192.168.66.44 80 -purpose lb -lbMethod LEASTCONNECTION \
    -persistenceType COOKIEINSERT -cltTimeout 180
→ ERROR: No such argument [-purpose]
```

The string `-purpose` exists **nowhere** in the JPilot/MCP codebase (verified by grep over
`copilot_deploy.py` and `mcp-server/app/services/netscaler_service.py`). Neither
`build_classic_lb_commands` nor `create_lb` ever emit `-purpose`. **This command was hand-built by
the LLM** via `netscaler_run_cli_command` — i.e. neither the auto-deploy path **nor** the dedicated
tool ran. It is a pure raw-CLI escape.

---

## 1. Current-state map — TWO LB write paths

There are two completely independent code paths that can write an LB, with **divergent CLI syntax**.

### Path A — Legacy auto-deploy (`copilot_deploy.py`) — WRITES via `run_cli_commands`

Dispatched from `copilot_orchestrator.py` **before** the LLM loop. Three entry points, all of which
ultimately call `_deploy_classic_lb` / build hand-rolled CLI and execute it through the **raw batch
tool** `netscaler_run_cli_commands`:

| Function | File:line | Writes? | Via |
|---|---|---|---|
| `try_auto_deploy_http_lb` | `copilot_deploy.py:902-997` | **WRITE** | `run_cli_commands` (`:946`), cmds from `build_http_lb_commands` (`:177-206`) |
| `try_auto_create_application` | `copilot_deploy.py:247-313` | **WRITE** | `netscaler_create_application` (Next-Gen API, not CLI — `:292`) |
| `try_auto_deploy_classic_lb` | `copilot_deploy.py:880-899` → `_deploy_classic_lb` | **WRITE** | `run_cli_commands` (`:746`), cmds from `build_classic_lb_commands` (`:457-489`) |
| `try_auto_deploy_lb_from_message` (NL free-text) | `copilot_deploy.py:793-811` → `_deploy_classic_lb` | **WRITE** | same `_deploy_classic_lb` |
| `parse_*` / `format_*_plan` / `build_*_commands` | `:88-206`, `:349-489`, `:523-601`, `:814-877` | parse/plan only | — |

Parse/plan-only (no writes): `parse_configuration_form_fields`, `parse_classic_lb_form_fields`,
`parse_natural_language_lb_request`, `detect_*`, `format_classic_lb_plan` (`:853-877`),
`format_classic_lb_response` (`:814-850`), `build_classic_lb_commands`, `build_http_lb_commands`.

**Idempotency / cleanup / verify machinery that MUST be preserved** (this is the battle-tested part):
- `_existing_vip_addresses` (`:604-635`) — lists VIPs so the build can pass `skip_vip_add=True`
  (de-dups `add ns ip … -type VIP`) when the VIP already exists.
- `_cleanup_commands_for_existing_lb` (`:638-710`) — if the vserver already exists, prepends
  `build_classic_vserver_removal_commands` (unbind/rm of the old vserver+service groups) so a
  re-deploy is clean. Calls `netscaler_list_virtual_servers` + `netscaler_list_service_status`.
- Verify-after: `_deploy_classic_lb` (`:764-790`) and `try_auto_deploy_http_lb` (`:964-984`) call
  `netscaler_list_virtual_servers` post-write and fold state/serverCount into the response
  (`format_classic_lb_response`, `_vserver_state_from_list` `:492-498`).
- `skip_vip_add` de-dup threaded through `build_classic_lb_commands(fields, skip_vip_add=…)`
  (`:743`) and `build_http_lb_commands(…)` (`:939`).

**CLI syntax produced by Path A** (`build_classic_lb_commands`, `:473-489`):
```
add ns ip {vip} 255.255.255.255 -type VIP        # unless skip_vip_add
add serviceGroup {sg} {backend_protocol}
bind serviceGroup {sg} {backend_ip} {port}       # per backend port
bind serviceGroup {sg} -monitorName {monitor}
add lb vserver {vserver} {proto} {vip} {fe_port} -lbMethod {m} -persistenceType {p}
bind lb vserver {vserver} {sg}
bind ssl vserver {vserver} -certkeyName {cert}    # SSL only
save ns config
```
Uses **serviceGroup** model and inlines `-lbMethod`/`-persistenceType` on the `add lb vserver` line.

### Path B — Dedicated tool `netscaler_create_lb` — WRITES via `apply_cli_config`

- Tool schema: `copilot_service.py:494-552` (params: `appliance_name, name, vip, servers`,
  optional `port, service_type, server_port, server_protocol, lb_method, persistence,
  persistence_timeout, ssl_certkey, dry_run, confirm`; required: `appliance_name, name, vip, servers`).
- copilot dispatch: `copilot_service.py:2091-2123` (maps args → MCP, threads `dry_run`/`confirm`).
- MCP impl: `mcp-server/app/services/netscaler_service.py:create_lb` (`:2122-2189`).
- Confirm contract: `apply_cli_config` (`:2072-2115`) — `dry_run OR not confirm` ⇒ preview
  (`{success, dryRun:true, commands}`); `confirm and not dry_run` ⇒ execute (stop_on_error=False,
  warning-tolerant ERROR re-check), then `save ns config`.

**CLI syntax produced by Path B** (`create_lb`, `:2154-2182`):
```
enable ns feature LB
add server {name}_srv{i} {ip}                     # per backend
add service {name}_svc{i} {srv} {proto} {port}    # per backend  ← service model, NOT serviceGroup
add lb vserver {name} {service_type} {vip} {port} ← NO inline -lbMethod/-persistence
bind lb vserver {name} {svc}                      # per service
set lb vserver {name} -lbMethod {m}               ← separate set, correct syntax
set lb vserver {name} -persistenceType {p} [-timeout {t}]
bind ssl vserver {name} -certkeyName {cert}       # SSL only
```
Uses **individual service** model and **separate `set lb vserver`** for method/persistence.

### Where they diverge (the core problem)
| Aspect | Path A (deploy) | Path B (create_lb) |
|---|---|---|
| Backend model | `serviceGroup` + `bind serviceGroup` | individual `add service` + `bind lb vserver` |
| lb_method/persistence | inline on `add lb vserver` | separate `set lb vserver` |
| VIP object | explicit `add ns ip … -type VIP` (+ skip de-dup) | none (relies on vserver create) |
| Monitor | `bind serviceGroup -monitorName` | not supported |
| Cleanup of existing | yes (`_cleanup_commands_for_existing_lb`) | none |
| VIP de-dup | yes (`skip_vip_add`) | none |
| Verify-after | yes | none (single call) |
| dry_run→confirm | implemented as plan-then-affirm in orchestrator | native tool param |
| Reached by | form submission + NL free-text (regex-gated) | LLM tool-call, or R1 confirm-recovery |

Two executors, two syntaxes, two idempotency stories. R3 asks for **one**.

---

## 2. Root-cause of the raw-CLI escape in the log

The model freelanced `add lb vserver … -purpose …` because **for that turn, neither LB path was in
force and `netscaler_run_cli_command` was on the menu.** Precise condition (any one suffices):

**RC-A — NL parse miss → Path A silently declines → fall-through to LLM.**
`try_auto_deploy_lb_from_message` only fires when `detect_natural_language_lb_request`
(`copilot_deploy.py:587-601`) is true, which requires **all** of `vserver_name` **and** `vip`
**and** `backend_ip` **and** `backend_ports` to be regex-extracted from one sentence
(`:594-597`). The extractors are brittle:
- `vserver_name`: needs `"... for <word>"` (`:531-538`).
- `backend_ip`: needs literal `"backend[s] <ip>"` (`:540-545`).
- `backend_ports`: needs `"port N"`/`"ports N and M"` text (`_parse_backend_ports_from_text` `:508-520`).
If the operator phrases it as "create an HTTP load balancer my_jp_lb on VIP 192.168.66.44:80 with
backends X,Y" (no "for", no "backend <ip>", no "port N"), `detect_*` returns **False**, the orchestrator
block at `copilot_orchestrator.py:1414-1426` is skipped, **no plan is shown**, and control falls
through to the LLM loop at `:1528`. The model then has `netscaler_run_cli_command` available and
builds the command by hand — inventing `-purpose`.

**RC-B — On the LLM-loop turn, raw `run_cli_command` is offered.** Even though the LB-intent message
*does* set `lb_config` and the router strips raw `read`/`cli_write` for dedicated intents
(`copilot_tool_router.py:447-457`, `:541-544`), there are two ways `netscaler_run_cli_command`
re-enters:
  1. **Confirm-turn full-tool-set:** a short "yes/apply/confirm" turn has no `lb_config` keyword, so
     `precise_intent` is False (`copilot_tool_router.py:623-639`) and `should_use_full_tool_set`
     returns True (`:579-596`) → `route_copilot_tools` returns the **entire** role tool set
     (`:640-641`), re-exposing `netscaler_run_cli_command`. (R1 marker recovery at
     `copilot_orchestrator.py:1361-1412` mitigates *if* a dry_run marker was embedded last turn — but
     a marker only exists if Path B actually ran a dry_run, which it didn't here.)
  2. **Multi-step/comma-heavy first turn:** if the LB sentence trips `should_use_full_tool_set`
     (≥3 commas, "and also", "then ") **and** no dedicated pack flips `precise_intent`, the full set
     is returned. (For LB this is usually saved by `lb_config` ∈ precise_intent — but only if the LB
     keyword matched; phrasings like "set up a vserver on 1.2.3.4 …" without "lb"/"load balanc" fail
     `:356-371` and get no `lb_config`.)

**RC-C — No backstop converts a raw `add lb vserver` into the dedicated tool.** `add` is **not** in
`DESTRUCTIVE_CLI_VERBS` (`copilot_memory_gate.py:58-73`), so `destructive_confirmation_required`
(`:251`) does **not** catch a freelance `add lb vserver`. The only gate is the CLI-memory-search gate
(must call `search_netscaler_cli_reference` first); the model can satisfy that and then still run the
buggy `add lb vserver … -purpose …`. Nothing redirects it to `create_lb`.

**Net root cause:** a brittle NL detector (RC-A) drops LB intents into the LLM loop, where raw CLI is
still reachable (RC-B) with no redirect backstop (RC-C). The two LB executors plus this gap = the
escape.

---

## 3. Chosen reconciliation (lower-risk): keep Path-A PARSE/PLAN/CLEANUP, route the WRITE through `create_lb`

**Make `netscaler_create_lb` (→ MCP `create_lb` → `apply_cli_config`) the SINGLE write executor.**
Keep everything in `copilot_deploy.py` that is *parsing*, *planning*, *cleanup discovery*, and
*verify* — discard only the **`run_cli_commands` write of `build_classic_lb_commands` output**.

### 3.1 Add a spec-mapper: parsed fields → `create_lb` arg dict
New pure function in `copilot_deploy.py`:
```python
def classic_lb_fields_to_create_lb_args(appliance_name, fields) -> dict:
    f = finalize_classic_lb_fields(fields)
    args = {
        "appliance_name": appliance_name,
        "name": f["vserver_name"],
        "vip": f["vip"],
        "servers": [f["backend_ip"]],          # expand if multiple backends parsed
        "service_type": f["vserver_protocol"],  # HTTP/SSL/SSL_TCP/TCP
        "port": int(f.get("frontend_port") or 443),
    }
    ports = f.get("backend_ports") or []
    if ports: args["server_port"] = int(ports[0])
    if f.get("backend_protocol"): args["server_protocol"] = f["backend_protocol"]
    if f.get("lb_method"):  args["lb_method"]  = f["lb_method"]
    if f.get("persistence"): args["persistence"] = f["persistence"]
    if f.get("ssl_cert"):   args["ssl_certkey"] = f["ssl_cert"]
    return args
```
A parallel `http_lb_fields_to_create_lb_args` maps `parse_configuration_form_fields` output the same way.

> Note one feature gap: `create_lb` has **no monitor binding** and no serviceGroup model. Two options
> (pick per risk appetite, see §5):
> (a) **Extend `create_lb`** (MCP) with optional `monitor` + multi-port-per-backend so it is a true
>     superset of `build_classic_lb_commands`. Preferred for full parity. Effort M.
> (b) Keep `create_lb` as-is and accept that monitor binding is dropped from the auto-path (the
>     model/operator can add it via `modify_lb` after). Lower effort, slight behavior change.

### 3.2 Rewrite `_deploy_classic_lb` to call the dedicated tool, preserving cleanup/verify
`_deploy_classic_lb` (`copilot_deploy.py:713-790`) keeps `_existing_vip_addresses` +
`_cleanup_commands_for_existing_lb` discovery, but instead of building+running classic CLI:
1. If `cleanup` commands exist (vserver already present), run them via the **existing dedicated
   removal path** (prefer `netscaler_delete_lb` if it covers the case; else run the cleanup CLI batch
   exactly as today — cleanup is unbind/rm which IS gated destructive and is already battle-tested).
2. Call `execute_copilot_tool(db, "netscaler_create_lb", classic_lb_fields_to_create_lb_args(...))`
   instead of `run_cli_commands` with `build_classic_lb_commands`.
3. Keep the post-write `netscaler_list_virtual_servers` verify + `format_classic_lb_response`.

This means `build_classic_lb_commands` / `build_http_lb_commands` become **dead for the write path**
(can stay for `format_*_plan` previews or be deleted in a later cleanup).

### 3.3 Preserve dry_run → approve → confirm
The orchestrator already implements plan-then-affirm for the NL path
(`copilot_orchestrator.py:1414-1443`: first contact returns `format_classic_lb_plan` and writes
nothing; a "yes" confirms via `last_user_message` recovery). Keep that gate. For the **write turn**,
call `netscaler_create_lb` with `confirm=true` (and `dry_run` omitted) directly from
`_deploy_classic_lb`, since the orchestrator already established user approval. (The native
`dry_run→confirm` round-trip is redundant *inside* the auto-path because the auto-path already owns
the plan/confirm handshake — we pass `confirm=true` once approved.)

> Alternative (even lower code churn): in the orchestrator confirm branch, instead of calling
> `try_auto_deploy_lb_from_message`, build the `create_lb` arg spec from the recovered `effective_msg`
> and route it through the **R1 dry_run-marker mechanism** (`_DEDICATED_DRY_RUN_TOOLS` already
> includes `netscaler_create_lb`, `copilot_orchestrator.py:816-831`). i.e. on first contact emit a
> `create_lb dry_run=true` preview (which auto-embeds the plan marker via `_embed_dry_run_plan_marker`
> `:834-862`), and let the existing R1 confirm-recovery (`:1361-1412`) fire `confirm=true`. This
> unifies the NL path with the dedicated-tool confirm machinery and deletes the bespoke
> `format_classic_lb_plan` + `last_user_message` handshake. Effort M, but collapses two confirm
> systems into one — recommended as the **target** once §3.2 lands.

---

## 4. Closing the raw-CLI escape (so the model can't hand-build `add lb vserver`)

Three layers; ship 4.1 + 4.2 minimum.

**4.1 — Never offer `netscaler_run_cli_command(s)` on an LB-intent or LB-confirm turn (RC-B fix).**
In `copilot_tool_router.py`:
- Track whether the **prior** turn matched a dedicated config pack (carry an `lb_config`/dedicated
  flag through history or via the R1 plan marker presence) and treat the confirm turn as
  `precise_intent` too, so `should_use_full_tool_set` does **not** dump the full set on "yes". Concretely:
  in `route_copilot_tools` (`:640`), if `_extract_prior_dedicated_plan(history)` is non-None **or** the
  message is an affirmation, keep the narrow dedicated+`read_safe` packs instead of returning
  `enabled_tools`.
- Add a final hard strip: after all pack logic, if any LB/dedicated intent is in play (this turn or
  recovered), `selected_names.discard("netscaler_run_cli_command"); .discard("netscaler_run_cli_commands")`.

**4.2 — Redirect a freelance raw `add lb vserver` to `create_lb` (RC-C backstop).**
In the memory gate or retry layer, intercept a `run_cli_command(s)` whose command(s) contain
`add lb vserver` / `add serviceGroup` / `add service … bind lb vserver` and **block with a corrective
hint** (mirrors P2-B at `operator-findings.md:236-247`):
```python
# copilot_memory_gate or copilot_retry
if tool in {"netscaler_run_cli_command","netscaler_run_cli_commands"} \
   and re.search(r"\badd\s+lb\s+vserver\b", joined_commands, re.I):
    return BLOCKED: "Do NOT hand-build LB CLI. Call netscaler_create_lb (dry_run=true to preview,
                     confirm=true to apply). It encodes correct syntax (no -purpose, separate
                     set lb vserver -lbMethod/-persistenceType)."
```
This is the safety net for any phrasing that slips past 4.1.

**4.3 — Prompt (already partly done).** `copilot_service.py:255,292` already de-advertise raw CLI for
LB ("LAST RESORT … use netscaler_create_lb"). Confirm `operator.md` LB routing names `create_lb`
(operator-findings P1-C). No new work if P1-C landed; otherwise apply it.

**4.4 — Widen NL detection so Path A actually fires (RC-A fix), reducing fall-through.** Loosen
`detect_natural_language_lb_request` / `parse_natural_language_lb_request` (`copilot_deploy.py:523-601`)
so common phrasings ("HTTP load balancer NAME on VIP:PORT with backends a,b") are caught — OR, when an
LB **intent** is detected (`_LB_CREATE_RE` + "load balanc"/"lb") but fields are incomplete, emit the
consolidated `default_lb_vserver_form` (operator-findings P2-A) instead of dropping to the LLM. This
keeps every LB intent inside the single-executor funnel.

---

## 5. Risks & regressions

- **Battle-tested Path A behavior change (highest risk).** `build_classic_lb_commands` uses
  serviceGroup + monitor + explicit VIP add; `create_lb` uses individual services, no monitor, no VIP
  object. Switching the executor changes the resulting config object shape. *Mitigation:* §3.1 option
  (a) — extend `create_lb` to a true superset (monitor, multi-port) before flipping the write; keep
  `format_classic_lb_response` verify so a bad deploy is visible. Stage behind the existing live test.
- **Monitor binding loss** if §3.1(b) chosen — auto-deployed LBs would lack the health monitor until a
  follow-up `modify_lb`. Acceptable only if monitor is rarely set via auto-path; otherwise do (a).
- **Cleanup path still uses raw CLI** (unbind/rm). That's fine — it is destructive-gated and tested;
  reconciling *removal* onto `delete_lb` is a separate, later item, out of R3 scope.
- **4.1 over-strip:** removing `run_cli_command` on confirm turns must not block a legitimate uncovered
  classic write that co-occurs with an LB keyword. *Mitigation:* only strip when a dedicated LB pack
  matched (this/prior turn); `should_use_full_tool_set` still exposes raw CLI for genuinely multi-step
  non-LB requests.
- **R1 marker collision:** if §3.3 alternative is adopted, ensure only ONE confirm system is active
  (don't double-fire both `format_classic_lb_plan` handshake and the R1 marker).
- **HTTP-profile warning exits** from the ~7-command `create_lb` batch must read as success — already
  handled by `apply_cli_config`'s warning-tolerant ERROR re-check (`netscaler_service.py:2099-2109`);
  verify the top-level result has no non-zero `exitStatus` that `tool_result_is_failure`
  (`copilot_orchestration.py:282`) would misread (operator-findings P2-C).

### Live test plan (use 192.168.100.x for cleanup safety)
1. **NL create, happy path:** Operator chat, appliance set, "Create an HTTP load balancer `o6_lb1` on
   VIP 192.168.100.50:80 with backends 192.168.100.61 and 192.168.100.62 on port 8080, round robin."
   Expect: a single **plan** (no write), no `add lb vserver` raw CLI in traces.
2. **Confirm:** reply "yes". Expect: exactly one `netscaler_create_lb confirm=true` trace; verify
   `show lb vserver o6_lb1` UP, backends bound; no `-purpose`, no `run_cli_command`.
3. **Phrasing that previously escaped:** "set up lb `o6_lb2` 192.168.100.51:443 ssl, backend
   192.168.100.63:443, cookie persistence" — confirm it routes to `create_lb` (or a consolidated form),
   never raw `add lb vserver`.
4. **Confirm-turn tool menu:** on the "yes" turn, log `enabled_tool_names` (orchestrator `:1252`) and
   assert `netscaler_run_cli_command(s)` absent.
5. **Backstop:** force a raw attempt (e.g. via a prompt that says "use run_cli_command to add lb
   vserver…") and assert the 4.2 block fires with the redirect hint.
6. **Idempotent re-deploy:** repeat step 1-2 for the same `o6_lb1`; assert cleanup ran (old vserver
   removed) and VIP not double-added.
7. **Cleanup:** `netscaler_delete_lb` (or removal path) for `o6_lb1`/`o6_lb2`; confirm gone via
   `show lb vserver`.

---

## 6. File-by-file change list (effort S/M/L) + sequencing

| # | File | Change | Effort |
|---|---|---|---|
| 1 | `copilot_tool_router.py` | 4.1 — keep narrow packs on affirmation/prior-dedicated turns; final hard-strip of `netscaler_run_cli_command(s)` when LB/dedicated intent in play | **M** |
| 2 | `copilot_memory_gate.py` (or `copilot_retry.py`) | 4.2 — block+redirect raw `add lb vserver`/serviceGroup to `create_lb` | **S** |
| 3 | `mcp-server/.../netscaler_service.py` `create_lb` | 3.1(a) — add optional `monitor` + multi-port-per-backend so it's a superset of `build_classic_lb_commands` | **M** |
| 4 | `copilot_service.py` | thread new `create_lb` params (`monitor`, …) in schema (`:494-552`) + dispatch (`:2091-2123`) | **S** |
| 5 | `copilot_deploy.py` | 3.1/3.2 — add `classic_lb_fields_to_create_lb_args` + `http_lb_fields_to_create_lb_args`; rewrite `_deploy_classic_lb` and `try_auto_deploy_http_lb` write step to call `netscaler_create_lb`; keep cleanup/verify | **L** |
| 6 | `copilot_deploy.py` (NL detect) | 4.4 — loosen `parse/detect_natural_language_lb_request`, or emit consolidated form on incomplete LB intent | **M** |
| 7 | `operator.md` / prompts | 4.3 — confirm LB routing names `create_lb` (no-op if P1-C landed) | **S** |
| 8 | `copilot_deploy.py` (cleanup) | delete now-dead `build_classic_lb_commands`/`build_http_lb_commands` write usage (keep for plan preview or remove) | **S** |

**Recommended sequencing (each independently shippable + testable):**
1. **#2 + #1** first — these alone close the raw-CLI escape (model can't reach/keep raw `add lb
   vserver`) **even before** the executor is unified. Lowest risk, highest immediate value. Live test
   steps 4 & 5.
2. **#3 + #4** — make `create_lb` a true superset (monitor/multi-port) so flipping the executor loses
   no behavior.
3. **#5** — flip the auto-deploy write to `create_lb` (the core R3 single-executor change). Live test
   steps 1,2,3,6.
4. **#6** — widen NL detection so fewer intents fall through (defense in depth on top of #1/#2).
5. **#7, #8** — prompt confirm + dead-code cleanup.

> Safety invariant (all steps): the write confirmation stays. `netscaler_create_lb` keeps
> `dry_run`→approval→`confirm=true`; the orchestrator's plan-then-affirm gate
> (`copilot_orchestrator.py:1414-1443` / R1 marker `:1361-1412`) is preserved. No step auto-applies LB
> config without an explicit user "yes".
