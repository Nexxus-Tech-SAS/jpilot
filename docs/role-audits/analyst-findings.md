# ANALYST Role — Root-Cause Findings & Recommendations

Audit date: 2026-06-24. Scope: why `netscaler_get_logs` and `netscaler_search_config`
(read-only SSH reads) get false "no tool ran" / "unverified read" / "configuration change"
banners even though the SSH command succeeded (`success:true`, `exitStatus 0`). NITRO/Next-Gen
reads are clean.

**READ-ONLY audit — no code was changed.** All recommendations preserve the analyst's
read-only posture (see SAFETY section).

---

## TL;DR — minimal-change summary

The false banners are produced by **two post-response guards** in
`copilot_orchestrator.py`, both of which fail to recognize the two SSH-backed read tools
as successful reads:

1. **`guard_unverified_read`** ("⚠️ Unverified read") fires because
   `trace_executed_successfully()` returns **`False`** for `netscaler_get_logs` /
   `netscaler_search_config` — those tool names are in **none** of the recognized sets, so
   the guard concludes "every tool failed."
2. **`guard_fabricated_execution`** ("⚠️ No changes were applied") fires because the
   model echoes running-config / log lines that start with `add`/`bind`/`set lb…`, which
   match `_CLI_LISTING_PATTERN`, and `_had_successful_action()` is `False` for a pure read.

**The single highest-leverage fix:** add `netscaler_get_logs` and
`netscaler_search_config` to the `READ_ONLY_OPERATOR_TOOLS` frozenset in
`copilot_orchestration.py` (line 28). That set is the source of truth consulted by
`trace_executed_successfully` (kills banner #2's "Unverified read") and by
`trace_is_state_changing` (so the reads are correctly classed read-only). Combined with a
guard scoping fix for banner #1 (don't fire `guard_fabricated_execution` when the only tools
that ran were read-only and succeeded), both false banners disappear with no new write
capability.

---

## Root cause 1 — "⚠️ Unverified read" banner [workflow-code] — P1

**Files:**
- `app/services/copilot_orchestrator.py:643` (`guard_unverified_read`)
- `app/services/copilot_orchestration.py:105` (`trace_executed_successfully`)
- `app/services/copilot_orchestration.py:28` (`READ_ONLY_OPERATOR_TOOLS`)

`guard_unverified_read` prepends `UNVERIFIED_READ_BANNER` when **no** trace executed
successfully and the answer text matches `_STATUS_ANSWER_PATTERN` (`down|bound to|service
group|…`). For a config search of `lb`, the answer contains lines like `bind lb vserver …`
and `service group`, so the content pattern matches:

```python
# copilot_orchestrator.py:651-661
if any(trace_executed_successfully(trace) for trace in tool_traces):
    return content
if not _STATUS_ANSWER_PATTERN.search(content):
    return content
... return f"{UNVERIFIED_READ_BANNER}\n\n---\n\n{content}"
```

The decisive bug is upstream in `trace_executed_successfully`:

```python
# copilot_orchestration.py:108-110
if trace.name not in WRITE_EXEC_TOOL_NAMES and trace.name not in READ_ONLY_OPERATOR_TOOLS:
    if trace.name not in {"netscaler_run_cli_command", "netscaler_run_cli_commands"}:
        return False        # <-- get_logs / search_config land here → "failed"
```

`netscaler_get_logs` and `netscaler_search_config` are **not** in `WRITE_EXEC_TOOL_NAMES`
(orchestration.py:66), **not** in `READ_ONLY_OPERATOR_TOOLS` (orchestration.py:28), and
**not** in the CLI-command set — so the function returns `False` regardless of the actual
`success:true` payload. `guard_unverified_read` then sees "all tools failed" and fires.

This is exactly why **NITRO/Next-Gen reads are clean**: `netscaler_list_service_status`,
`netscaler_list_virtual_servers`, etc. **are** in `READ_ONLY_OPERATOR_TOOLS`, so
`trace_executed_successfully` actually inspects their payload and returns `True`.

### Recommended change (P1)
Add the two SSH read tools to `READ_ONLY_OPERATOR_TOOLS`:

```python
# copilot_orchestration.py:28  (before)
READ_ONLY_OPERATOR_TOOLS = frozenset({
    "netscaler_get_system_info",
    ...
    "jpilot_check_doc_connectivity",
})

# after — add:
    "netscaler_get_logs",
    "netscaler_search_config",
```

Effect: `trace_executed_successfully` now parses their JSON and returns `True` when
`success` is not `False` → `guard_unverified_read` short-circuits at line 653.
Because these tools are read-only, adding them here also makes `trace_is_state_changing`
(orchestration.py:91-95) correctly return `False` for them — no write semantics introduced.

---

## Root cause 2 — "⚠️ No changes were applied" banner [workflow-code] — P1

**Files:**
- `app/services/copilot_orchestrator.py:624` (`guard_fabricated_execution`)
- `app/services/copilot_orchestrator.py:191` (`_CLI_LISTING_PATTERN`)
- `app/services/copilot_orchestrator.py:562` (`_had_successful_action` → `had_successful_state_change`)

```python
# copilot_orchestrator.py:633-639
if _claims_config_change(content) and not _had_successful_action(tool_traces):
    ... return f"{UNEXECUTED_ACTION_BANNER}\n\n---\n\n{content}"
```

`_claims_config_change` returns `True` whenever the answer text matches
`_CLI_LISTING_PATTERN`:

```python
# copilot_orchestrator.py:191-194
_CLI_LISTING_PATTERN = re.compile(
    r"(?m)^\s*(add|bind|set|enable|disable|rm|clear|save)\s+(lb|service|servicegroup|ns|vlan|route)\b",
    re.IGNORECASE,
)
```

A `netscaler_search_config keyword=lb` result is a verbatim dump of running-config lines —
`add lb vserver …`, `bind lb vserver …`, `set lb monitor …` — every one of which matches
this pattern at line-start. So the guard mistakes the **echoed config it just read** for a
**claimed config change**. `netscaler_get_logs` can hit the same pattern when a log line
begins with one of those verbs (explains the non-deterministic 2/3 on Request 5).

`_had_successful_action` only counts **state-changing** successes
(`had_successful_state_change`, orchestration.py:125) — a pure read is never "a successful
action," so the second half of the `and` is always `True` for these reads.

### Recommended change (P1)
Exempt the guard when the only NetScaler tools that ran this turn were read-only tools
that succeeded — the model is quoting data, not claiming a write. Add an early return at the
top of `guard_fabricated_execution`:

```python
def guard_fabricated_execution(content, tool_traces, role=None):
    if normalize_role(role) == JPilotRole.ARCHITECT:
        return content

    # NEW: a successful read that merely echoes config/log lines is not a fabricated write.
    read_traces = [t for t in tool_traces if not trace_is_state_changing(t)]
    if (
        tool_traces
        and not any(trace_is_state_changing(t) for t in tool_traces)
        and any(trace_executed_successfully(t) for t in read_traces)
    ):
        return content

    if _claims_config_change(content) and not _had_successful_action(tool_traces):
        ...
```

This depends on Root cause 1's fix (so `trace_executed_successfully` recognizes the SSH
reads). With both in place, the guard no longer fires on read-only turns but still fires when
a genuine write tool was expected and absent.

**Alternative / complementary (P2):** tighten `_CLI_LISTING_PATTERN` /
`guard_fabricated_execution` so quoted material inside fenced code blocks or
`search_config` output is not treated as a prose claim. Lower priority because the
read-only scoping above already removes the false positive for analyst.

---

## Root cause 3 — `_should_force_tool_execution` could re-prompt on read phrasing [model-behavior / workflow-code] — P2

**File:** `app/services/copilot_orchestrator.py:460-493`, `266-270`

Not triggered by the 7 tested requests, but a latent risk for multi-turn. The
`FORCE_TOOL_EXECUTION_MESSAGE` retry loop is gated by `_user_requests_config_change`:

```python
# copilot_orchestrator.py:266-270
def _user_requests_config_change(user_message: str) -> bool:
    has_verb = any(verb in lowered for verb in CONFIG_CHANGE_VERBS)
    has_noun = any(noun in lowered for noun in CONFIG_CHANGE_NOUNS)
    return has_verb and has_noun
```

`CONFIG_CHANGE_NOUNS` includes `"lb "`, `"service"`, `"route"`, `"policy"`, and
`CONFIG_CHANGE_VERBS` includes `"set up"`, `"add"`, etc. A read request such as
"add up the **service** counts" or "**set up** a view of the **lb** vservers" would match
both and, if the model then narrated CLI verbs, push it onto the force-execution path. For
the analyst (read-only) this manifests as friction/extra round-trips, never an actual write
(writes are blocked at `filter_tools_for_role`).

### Recommended change (P2)
Short-circuit the force-execution path for the analyst role, which has no write tools to
force anyway:

```python
# copilot_orchestrator.py, top of _should_force_tool_execution (after the ARCHITECT guard)
if normalize_role(role) == JPilotRole.ANALYST:
    return False
```

Tag: the trigger is `[workflow-code]` (heuristic phrase match); the resulting extra prose is
`[model-behavior]`. Safe because the analyst cannot execute the writes the message would ask
for — forcing is pointless and only adds latency.

---

## Items checked and cleared (no change needed)

- **Memory gate** (`copilot_memory_gate.py`): `nextgen_memory_review_required` covers only
  `NEXTGEN_API_TOOLS`; `cli_memory_review_required` covers only SSH/CLI **write** tools.
  Neither `netscaler_get_logs` nor `netscaler_search_config` is gated → no search-first
  round-trip, no confirmation. [no friction]
- **Calibration gate** (`copilot_calibration_gate.py`): `blueprint_action_review_required`
  does not list the two SSH read tools, so they are never blocked for a blueprint review.
  (Note: they are also not in `BLUEPRINT_GATE_EXEMPT_TOOLS`, but since they fail the
  review-required check they pass anyway. Optionally add them to the exempt set for clarity —
  P3, cosmetic.)
- **Analyst system prompt** (`copilot_roles.py:172-184`, `build_system_prompt`): contains no
  "ask/confirm before reading" instruction and does not mislabel SSH reads. The confirm/dry-run
  language lives only in the **operator** branch (lines 186-219). [clean]
- **Tool router** (`copilot_tool_router.py:98-102`, `ROLE_BASE_PACKS["analyst"]` +
  `logs`/`config_search` packs at 83-84, 406/420): analyst correctly receives the read tools;
  dedicated-config-pack matching demotes search tools but does not gate reads. [clean]

---

## SAFETY assessment

All three recommended edits **only remove false-positive banners / unnecessary gating on
read paths**; none grants the analyst any write capability:

- Adding `netscaler_get_logs` / `netscaler_search_config` to `READ_ONLY_OPERATOR_TOOLS`
  classifies them as reads. Since both tools are read-only by nature (log tail / config grep
  over SSH), this is factually correct. It makes `trace_is_state_changing` return `False`
  for them — which is the truth — and does **not** add them to `WRITE_EXEC_TOOL_NAMES` or to
  any role's allowed-write set. Writes remain controlled by `filter_tools_for_role` /
  `_ANALYST_BLOCKED` / the manifest, which are untouched.
- The `guard_fabricated_execution` exemption is conditioned on *all* tools being non-state-
  changing AND at least one read succeeding; a turn containing any state-changing tool still
  flows into the existing fabrication check unchanged. **Risk to watch:** if a future tool is
  mis-classified as read-only in `READ_ONLY_OPERATOR_TOOLS`, this exemption would suppress the
  fabrication banner for it too — so keep that set strictly read-only.
- The analyst short-circuit in `_should_force_tool_execution` only suppresses a retry nudge
  for a role that already cannot perform writes; operator/architect behavior is unchanged.

---

## Priority recap

| # | Finding | Tag | Priority | Fix location |
|---|---------|-----|----------|--------------|
| 1 | "Unverified read" banner on SSH reads | workflow-code | **P1** | `copilot_orchestration.py:28` (add 2 tools to `READ_ONLY_OPERATOR_TOOLS`) |
| 2 | "No changes were applied" banner on echoed config/logs | workflow-code | **P1** | `copilot_orchestrator.py:624` (read-only exemption in `guard_fabricated_execution`) + depends on #1 |
| 3 | Force-execution retry could prompt on read phrasing (multi-turn) | workflow-code / model-behavior | P2 | `copilot_orchestrator.py:460` (analyst short-circuit) |
| — | Calibration gate exempt-list clarity for the 2 SSH reads | workflow-code | P3 | `copilot_calibration_gate.py:21` (cosmetic) |

**Minimal change to kill both observed banners:** apply **#1** (one frozenset edit) and the
read-only early-return in **#2**.
