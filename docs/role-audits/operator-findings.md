# Operator Role — Root-Cause Findings & Recommendations

**Date:** 2026-06-24
**Scope:** NetScaler Operator chat (LB creation flow).
**Source test:** `docs/role-audits/operator-test.md`
**Audit type:** READ-ONLY code audit. No code changed.

Symptoms reproduced in the test:
1. Operator defaults to raw `netscaler_run_cli_command` for config → GATE-BLOCKED (requires `search_netscaler_cli_reference` first) → after a few blocked calls a "stuck/paused" banner fires.
2. Info gathered across **multiple** `inputForm`s (persistence/monitor asked in a second form).
3. The dedicated `netscaler_create_lb` (ungated, `dry_run`→`confirm`) only fires when the user names it explicitly.

---

## 1. Root Causes (file:line + quoted code)

### RC-1 — Raw CLI write tool is offered to the Operator for LB intents, and its own description recommends it for LB creation `[workflow-code]` + `[model-behavior]`

The dedicated config packs route tightly, **but they force-add the `read` pack, and `read` contains the gated raw CLI write tool.**

`backend-api/app/services/copilot_tool_router.py:22-32`
```python
"read": frozenset(
    {
        "netscaler_list_applications",
        ...
        "netscaler_nextgen_get",
        "netscaler_run_cli_command",   # <-- gated raw CLI WRITE tool lives in the "read" pack
    }
),
```

`copilot_tool_router.py:433-440` (LB intent → `read` is force-added, dragging raw CLI back in):
```python
if _dedicated_config_packs:
    packs.update(_dedicated_config_packs)
    # Always include read so the model can verify with show commands
    packs.add("read")                 # <-- re-introduces netscaler_run_cli_command
    packs.discard("cli_search")
    packs.discard("nextgen_search")
```

So even on a clean `lb_config` intent the model is *offered* both `netscaler_create_lb` **and** `netscaler_run_cli_command`. It then picks the raw CLI tool because **the raw tool's own description actively advertises LB creation**:

`backend-api/app/services/copilot_service.py:253-262`
```python
"name": "netscaler_run_cli_command",
"description": (
    "Run ANY NetScaler classic CLI command via SSH — including configuration writes "
    "(add, set, bind, unbind, enable, disable, rm, clear, save, ...) plus show/stat/get. "
    ...
),
...
"command": { ... "description": "CLI command, e.g. add lb vserver web_vs HTTP 10.0.0.10 80" },
```
The example literally is the LB-create command. The dedicated-tool preference lives only in the system prompt and in the *search-tool* descriptions (`copilot_service.py:1267`) — **not on this write tool**, so at the point of selection the model sees a tool that says "use me to add lb vserver."

### RC-2 — The base Operator prompt contradicts the dedicated-tool suffix and never mentions `netscaler_create_lb` `[model-behavior]`

`build_system_prompt` appends a strong "use the dedicated tools" suffix (`copilot_roles.py:192-219`), **but the loaded base prompt routes LB writes to raw CLI** and does not name a single dedicated tool:

`backend-api/app/resources/prompts/netscaler/roles/operator.md:16` (tool list — no `create_lb`):
```
netscaler_run_diagnostic, netscaler_run_cli_command, netscaler_run_cli_commands.
```
`operator.md:21` and `:60`:
```
d. Classic config writes: ... then netscaler_run_cli_commands or netscaler_run_cli_command.
...
- Classic writes: search CLI, then netscaler_run_cli_commands
```
`operator.md:19, 28` explicitly tell the model to deploy LBs with "classic batched CLI". The base prompt and the suffix fight each other; the base prompt is longer, more specific, and contains the concrete routing table, so the model follows it (→ raw CLI). **No line in `operator.md` mentions `netscaler_create_lb` / `modify_lb` / `delete_lb`.**

### RC-3 — An un-satisfiable gate-block counts as a "failure" and trips the stuck detector `[workflow-code]`

A gate-block is `{"success": False, "blocked": True}`. The loop-breaker treats that as a failure:

`backend-api/app/services/copilot_orchestration.py:272-289`
```python
def tool_result_is_failure(result: str) -> bool:
    ...
    if data.get("success") is False or data.get("commandFailed"):
        return True            # <-- a memory-gate block is success:False → counts as failure
```

`copilot_orchestration.py:23-24, 376-392`
```python
DEFAULT_REPEATED_FAILED_CALL_LIMIT = 2  # same (tool,args) failing → stop
DEFAULT_PER_TOOL_FAILURE_LIMIT = 3      # one tool failing N times in a turn → stop
...
if identical_fails >= settings.repeated_failed_call_limit:   # trips at 2 identical blocks
    return LoopBreak("repeated_failed_call", ...)
...
if runtime.tool_failure_counts.get(name, 0) >= settings.per_tool_failure_limit:  # trips at 3
    return LoopBreak("per_tool_failure", ...)
```
A gate-block is a *deterministic policy refusal the model can satisfy* (call the search first) or *route around* (call the dedicated tool) — it is not the appliance failing. Counting it toward "stuck" both (a) produces the misleading "I appear to be stuck" banner and (b) terminates the turn before the model gets enough rounds to recover.

### RC-4 — A gate-block produces no corrective retry hint, so the model has nothing pulling it off raw CLI `[workflow-code]`

After each tool result the orchestrator builds a retry hint (`copilot_orchestrator.py:1529`). The CLI memory-gate block is plain JSON that does **not** start with `BLOCKED:` and matches no branch in `build_tool_retry_hint`:

`backend-api/app/services/copilot_memory_gate.py:291-302` (the block payload) vs.
`backend-api/app/services/copilot_retry.py:35-36`
```python
if isinstance(result, str) and result.startswith("BLOCKED:"):
    return result.removeprefix("BLOCKED:").strip()
```
The gate message only says "call `search_netscaler_cli_reference` first" — it never says "or use `netscaler_create_lb`, which needs no search." So the model's only nudge is *toward more raw CLI*, and it loops on the same blocked tool.

### RC-5 — Multi-form info gathering: the model emits its own form; the consolidated fallback form is bypassed `[model-behavior]` (mild `[workflow-code]`)

There is a well-designed single consolidated form (`copilot_form.py:575-655`, `default_lb_vserver_form`, 9 fields incl. `monitor`), and `attach_default_lb_form_if_missing` (`:658-691`) injects it — **but only when the model did not already emit a form**:
```python
if form is not None:
    return content, normalize_lb_form_fields(form)   # <-- model's own (possibly partial) form wins
```
In the test the model emitted its own 8-field form omitting `persistenceType`/`monitor_type`, so the consolidated fallback never applied, and a second form appeared in turn 2. Nothing in the prompt enforces "ask for persistence + monitor in the **first** form," and the model's form is accepted as-is.

---

## 2. Recommendations (prioritized, with before/after)

> **SAFETY (applies to every item below):** KEEP the write confirmation. `netscaler_create_lb` must still run `dry_run=true` → user approval → `confirm=true`, and the "CONFIRM BEFORE ANY CHANGE" rule stays. None of these changes auto-apply config. The goal is fewer round-trips and removing the gated-trap, **not** removing approval.

### P1-A — Drop raw CLI write tools from Operator config-intent packs `[workflow-code]`

Make the dedicated tools the **only** offered write path when a dedicated config intent is detected, so the model literally cannot fall into the gated raw-CLI trap. Add a read-only show tool for verification instead of the full raw CLI tool.

`copilot_tool_router.py` — split a read-only verification pack out of `read`:

*Before* (`:22-32`, `:433-440`):
```python
"read": frozenset({ ..., "netscaler_run_cli_command" }),
...
if _dedicated_config_packs:
    packs.update(_dedicated_config_packs)
    packs.add("read")          # drags in raw CLI write tool
```
*After* (sketch):
```python
# raw CLI stays only in an explicit "raw_cli" pack, never auto-added for config intents
"read_safe": frozenset({           # no write tools
    "netscaler_list_virtual_servers", "netscaler_list_service_status",
    "netscaler_list_ip_addresses", "netscaler_nextgen_get",
}),
...
if _dedicated_config_packs:
    packs.update(_dedicated_config_packs)
    packs.add("read_safe")     # verification reads only — no netscaler_run_cli_command
    packs.discard("read")
    packs.discard("cli_search")
    packs.discard("nextgen_search")
```
Also guard the **form-submission** branch (`:444-454`) and the `cli_write_signal` branch (`:502-503`) the same way: when a dedicated config pack matched this turn, do **not** re-add `cli_write` / raw `read`. (Today `is_form_submission` unconditionally re-adds `cli_write` + `read` for non-architects at `:454`, which re-opens the trap on the confirm turn.)

> Net effect: for "create a load balancer," the model is offered `netscaler_create_lb/modify_lb/delete_lb` + read-only verification tools — and nothing else writable. It cannot pick raw CLI, so the gate is never hit. Citrix-known-syntax raw CLI is still available for genuinely un-covered requests (no dedicated tool matched → `read`/`cli_write` packs route normally).

### P1-B — Stop counting un-satisfiable gate-blocks as "stuck" `[workflow-code]`

Even with P1-A, a stray raw-CLI attempt shouldn't terminate the turn with a "stuck" banner — a gate-block is a recoverable policy redirect, not an appliance failure.

`copilot_orchestration.py` — exclude memory-gate blocks from the failure signal:

*Before* (`:272-281`):
```python
def tool_result_is_failure(result: str) -> bool:
    ...
    if data.get("success") is False or data.get("commandFailed"):
        return True
```
*After* (sketch):
```python
def tool_result_is_failure(result: str) -> bool:
    ...
    # A memory-review gate block is a recoverable redirect, not a failure:
    # the model can satisfy the gate or route to a dedicated tool. Don't count it.
    if data.get("blocked") and not data.get("commandFailed"):
        return False
    if data.get("needsConfirmation"):   # waiting on the user is not "stuck" either
        return False
    if data.get("success") is False or data.get("commandFailed"):
        return True
```
This also fixes the misleading banner: a destructive-confirmation block (`needsConfirmation`) and a memory gate no longer read as the appliance failing.

### P1-C — Add `netscaler_create_lb` to the base Operator prompt and resolve the contradiction `[model-behavior]`

`app/resources/prompts/netscaler/roles/operator.md` — replace the raw-CLI-first LB guidance with dedicated-tool-first.

*Before* (`:19`, `:21`, `:28`, `:60`): "JPilot deploys with classic batched CLI" / "Classic writes: search CLI, then netscaler_run_cli_commands".
*After* (sketch — new rule + routing line):
```
9b. **Load balancer create/modify/delete:** ALWAYS use netscaler_create_lb / netscaler_modify_lb /
    netscaler_delete_lb. These encode correct syntax — do NOT search the CLI reference and do NOT
    use netscaler_run_cli_command(s) for LB work. Call with dry_run=true to preview the exact
    commands, present that preview as your plan, and on the user's approval call again with
    confirm=true. Same pattern for cs/rewrite/responder via their dedicated tools.

Tool routing:
- Create/modify/delete LB: netscaler_create_lb / modify_lb / delete_lb (dry_run → confirm; no CLI search)
- Raw netscaler_run_cli_command(s): LAST RESORT, only when no dedicated tool covers the request.
```
Add `netscaler_create_lb/modify_lb/delete_lb` to the tool list at `:11-16`. This removes the head-on contradiction with the `copilot_roles.py:192-219` suffix.

### P1-D — Rewrite the raw CLI write-tool description to de-advertise LB creation `[model-behavior]`

`copilot_service.py:253-262` — change the description and the example so the tool no longer presents itself as the LB-creation path.

*Before:*
```
"Run ANY NetScaler classic CLI command via SSH — including configuration writes
 (add, set, bind, ...) plus show/stat/get. ..."
...
"command": { "description": "CLI command, e.g. add lb vserver web_vs HTTP 10.0.0.10 80" }
```
*After (sketch):*
```
"LAST RESORT raw CLI. For load balancers, content switching, rewrite, responder, logs, config
 search and failover, use the dedicated tools (netscaler_create_lb/modify_lb/delete_lb, ...).
 Only use this for classic CLI that no dedicated tool covers. Requires search_netscaler_cli_reference
 first. ..."
...
"command": { "description": "Read-only or uncovered classic CLI, e.g. show ns runningConfig -withDefaults" }
```
This is the description the model reads at selection time; today it is the single strongest pull toward the trap.

### P2-A — Consolidate LB info-gathering into ONE form `[model-behavior]` + `[workflow-code]`

Two complementary fixes:

1. **Prompt (P2):** In `operator.md` rule 13/14 region, state explicitly: *"When creating a load balancer and values are missing, emit exactly ONE `jpilot-form` that includes every field needed to call `netscaler_create_lb`: name, VIP, front-end port, service_type, backend server(s), backend port, lb_method, persistence, monitor. Never split these across multiple forms."*

2. **Code (P2, optional hardening):** In `copilot_form.py`, when the model's own LB form is missing the known LB fields, *merge in* the defaults instead of accepting the partial form. `attach_default_lb_form_if_missing` (`:670-671`) currently returns the model's form untouched; a `normalize_lb_form_fields`-style pass could append any of the 9 canonical fields (`persistence`, `monitor`, ...) that are absent, guaranteeing a single complete form. This makes "ask once" structural, not prompt-dependent.

### P2-B — Give a corrective retry hint when raw CLI is gate-blocked on a dedicated-tool intent `[workflow-code]`

So that any residual raw-CLI attempt self-corrects in the *same* turn instead of looping.

`copilot_retry.py` (add a branch) or `copilot_memory_gate.block_result_for_missing_cli_memory` (add a `BLOCKED:`-prefixed hint). Sketch in `build_tool_retry_hint`:
```python
if tool_name in {"netscaler_run_cli_command", "netscaler_run_cli_commands"} \
        and _is_gate_block(result) and user_requests_lb_vserver_create(user_message):
    return ("This is a load-balancer request. Do NOT use raw CLI. Call netscaler_create_lb "
            "with dry_run=true to preview, then confirm=true to apply. It needs no CLI search.")
```
This directly counters RC-4: the only nudge today points back at more raw CLI.

### P2-C — Relax limits for the confirm→execute turn `[workflow-code]`

`netscaler_create_lb` runs ~7 commands internally and emits HTTP-profile *warnings* (exit=1) that are non-fatal. Ensure such warning exits aren't misread as failures by the loop-breaker (`tool_result_is_failure` checks `exitStatus not in (0, None)` at `copilot_orchestration.py:282` — verify dedicated-tool results don't surface a top-level non-zero `exitStatus`). The dedicated-tool path is single-call so iteration limits (40) are not a concern; the risk is purely the warning-as-failure misclassification. No limit increase is needed if P1-B lands and dedicated-tool warnings are normalized to `success: true`.

---

## 3. Safety Review

- **All write confirmation is preserved.** Every recommendation keeps `dry_run` → user approval → `confirm` for `netscaler_create_lb`, and keeps "CONFIRM BEFORE ANY CHANGE" (`operator.md:24`) and the destructive-confirmation gate (`copilot_memory_gate.py:185-260`) intact.
- **P1-B risk:** not counting `blocked`/`needsConfirmation` as failures must not *also* suppress genuine repeated appliance failures. The sketch only excludes `blocked && not commandFailed` and `needsConfirmation`; a real failed CLI write (`commandFailed: true` / `success:false` without `blocked`) still trips the breaker. Low risk.
- **P1-A risk:** dropping raw CLI from config-intent packs could block a legitimate "uncovered" classic write that happens to co-occur with an LB keyword. Mitigation: only strip raw CLI when a dedicated pack actually matched *and* keep the existing `should_use_full_tool_set` fallback (`copilot_tool_router.py:537-549`) for multi-step/comma-heavy requests, which still exposes the full set. The memory gate remains as the backstop if raw CLI is ever offered.
- **P1-D risk:** softening the raw-CLI description must not hide it from genuine raw-CLI tasks (analyst troubleshooting, uncovered writes). It stays fully functional; only its *self-advertising for LB* is removed.

---

## 4. Minimal-Change Summary (highest impact, 3 edits)

1. **`copilot_tool_router.py` — remove `netscaler_run_cli_command` from the auto-added path for dedicated config intents** (split a write-free `read_safe` pack; stop the `read`/`cli_write` re-add on `lb_config` and on form-submission). *Eliminates the gated-trap entirely — the model can't pick raw CLI for an LB.* `[workflow-code]`
2. **`copilot_orchestration.py:272` — make `tool_result_is_failure` ignore `blocked`/`needsConfirmation`.** *Stops gate-blocks and confirmation-waits from firing the false "stuck" banner and killing the turn.* `[workflow-code]`
3. **`operator.md` + `copilot_service.py:253` — add `netscaler_create_lb` to the base prompt's LB routing and de-advertise LB creation in the raw-CLI tool description.** *Resolves the prompt contradiction and the selection-time pull so the model calls `create_lb` (dry_run→confirm) on its own.* `[model-behavior]`

Items 1+2 are pure workflow-code and are sufficient on their own to prevent the stuck/blocked loop even if model behavior is unchanged (raw CLI simply isn't offered). Item 3 makes the model *prefer* `create_lb` proactively. P2-A (one-form) further cuts a round-trip.
