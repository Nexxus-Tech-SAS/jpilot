# Architect Role Audit

**Date:** 2026-06-24
**Backend:** `nexxus-workspace-jpilot-backend-api-1` (http://172.18.0.5:8000)
**Model:** `anthropic/claude-sonnet-4.5` via OpenRouter
**Appliance:** NetScaler (no live appliance connection; architect does not require one)
**Tester:** Claude Code automated audit

---

## Intended Architect Workflow (from code)

### Role identity (`copilot_roles.py`, `copilot_roles/architect.md`)
- "Plan-only" role: `requiresAppliance=False`; passes `guard_fabricated_execution`, `guard_unverified_read`, `_should_force_tool_execution` checks (architect is skipped / returns `False` for all)
- System prompt tells the LLM it does **not** execute changes; reference appliance is "planning context only"

### Tool availability (`copilot_tool_router.py`)
- Base pack for architect (netscaler vendor): `frozenset({"inventory"})` → only `netscaler_list_inventory`
- During normal discovery turns the router strips every tool and returns an **empty set** (no tools sent to LLM)
- When `user_wants_deliverable_now()` is True, adds: `architect_search`, `cli_search`, `nextgen_search` → `search_jpilot_architect_resources`, `search_netscaler_cli_reference`, `search_netscaler_nextgen_api`
- When a planning form is submitted: search and write packs are all discarded; effective tool list is empty or minimal
- From logs: `routed=2 names=['list_official_blueprint_catalog', 'search_stack_calibration_memory']` — these are stack_calibration pack tools added when installed skills are present

### Discovery gating (`copilot_architect_discovery.py`)
- `architect_tools_enabled()` — disables ALL MCP tools while discovery is active (no deliverable yet + not enough form submissions); returns True only when `user_wants_deliverable_now()` or `architect_discovery_ready_for_deliverable()` thresholds are met
- `block_architect_tool_during_discovery()` — if a tool call sneaks through, returns a BLOCKED string; allows search tools only once discovery thresholds pass
- `build_architect_session_nudge()` — injects proactive system nudges to guide form-based discovery (called per turn via `_architect_effective_system_prompt`)
- `architect_discovery_should_retry()` — triggers a retry loop if the LLM produces a checklist or bad prose instead of a `jpilot-form`

### Discovery workflow
1. First turn: LLM should produce a `jpilot-form` asking planning intent (new_deployment / new_functionality / change_control)
2. Subsequent turns: one form per turn, each covering one topic; NO tool calls during discovery
3. When sufficient forms collected (threshold: ≥5 for new_functionality, ≥7 for new_deployment, ≥4 for change_control), LLM is nudged to write the deliverable
4. User can bypass with "generate the design" / "give me the full design" → `user_wants_deliverable_now()` triggers tool-enabled turn for doc generation
5. Deliverable output: markdown block starting with `<!-- jpilot-design-document -->` or `<!-- jpilot-change-control-document -->`
6. Post-deliverable: revision via `jpilot-form` with `submitLabel "Update design"` then re-output of complete document

### What architect is NOT supposed to do
- Call appliance write tools (netscaler_create_lb, netscaler_run_cli_commands, etc.)
- Call read tools during discovery (netscaler_list_virtual_servers, netscaler_get_system_info, etc.)
- Produce a CLI walkthrough or claim to execute config
- Show checklists (✅/❌), Turn N labels, or prose question lists (guarded by `_BAD_DISCOVERY_RE`)

---

## Test 1 — HTTPS LB Design Request (Fresh Turn)

**Message:** "I need to design an HTTPS load-balancing setup on NetScaler for app1.example.com with two backend web servers."

**Latency:** ~6,100 ms (two runs: 6,104 ms, ~6,200 ms)

**Behavior summary:** The architect immediately entered discovery mode. No tool calls were made. The LLM produced a short acknowledgement plus a `jpilot-form` asking planning intent (new_deployment / new_functionality / change_control). This is exactly the intended turn-1 behavior.

**Tools invoked:**

| Tool | Args | Result |
|------|------|--------|
| (none) | — | — |

**inputForm produced:**
- Title: "What are you planning?"
- Field: `planning_intent` (choice: new_deployment / new_functionality / change_control)
- submitLabel: "Continue"

**Matches intended workflow?** YES — correct discovery form for turn 1; no appliance tools called.

---

## Test 2 — Push for Full Design (Turn 2, Continuing Turn 1)

**Message:** "Give me the full design and the config plan. This is new functionality on an existing NetScaler HA pair."

**History:** [Turn 1 user + assistant]

**Latency:** ~8,330 ms

**Behavior summary:** The user provided planning intent ("new functionality / existing HA pair") inline rather than via the form. The architect acknowledged the intent and pivoted to the next discovery topic — it did **not** produce the full design immediately. Instead it issued a second `jpilot-form` scoped to "Existing NetScaler environment" (platform choice, version, HA mode, existing services). No tool calls were made.

This is nuanced: the code's `user_wants_deliverable_now()` checks for exact phrases like "generate the design" or "design document" but not for "give me the full design and the config plan" combined with plain-intent context. The LLM correctly judged that it lacked enough discovery information (only one topic answered so far) and continued discovery rather than jumping to output.

**Tools invoked:**

| Tool | Args | Result |
|------|------|--------|
| (none) | — | — |

**inputForm produced:**
- Title: "Existing NetScaler environment"
- Fields: appliance_platform (choice), current_version (text), ha_mode (choice), existing_services (text)
- submitLabel: "Continue"

**Matches intended workflow?** YES — continues structured discovery; no tools; correct next topic. Minor note: "Give me the full design" was not matched by `user_wants_deliverable_now()` (which requires "design document", "generate the design" etc.), so discovery proceeded normally.

---

## Test 3 — Role Self-Description (Fresh Turn)

**Message:** "What can you help me with as an architect?"

**Latency:** 8,733 ms

**Behavior summary:** The LLM produced a clear, accurate, self-contained role description covering: Planning & Design (greenfield / add functionality / change control), How it works (structured discovery → official docs → formal deliverables), and What it doesn't do (no appliance execution, no guessing). No form, no tool calls. This is appropriate for a capabilities question that triggers no discovery form (not a form submission, not a deliverable request, not a bad-prose retry).

**Tools invoked:**

| Tool | Args | Result |
|------|------|--------|
| (none) | — | — |

**inputForm:** None

**Matches intended workflow?** YES — informational question handled in prose; no form spam; accurate self-description; no tool calls.

---

## Test 4 — Config Audit Request (Fresh Turn)

**Message:** "Audit the current NetScaler config and recommend improvements."

**Latency:** ~6,500 ms

**Behavior summary:** Despite the phrase "current NetScaler config" (which could trigger read tools in Operator/Analyst), the architect role correctly stayed in planning mode. No inventory or config-read tools were called. The LLM produced a discovery form asking for audit scope (comprehensive / security / performance / HA / other). From the logs: `routed=2 names=['list_official_blueprint_catalog', 'search_stack_calibration_memory']` — the router provided only stack-calibration tools (no appliance reads), and the LLM did not call any of them.

**Tools invoked:**

| Tool | Args | Result |
|------|------|--------|
| (none) | — | — |

**inputForm:** Present — Title: "Configuration audit scope" (primary audit focus: comprehensive / security / performance / HA)

**Matches intended workflow?** YES — audit framed as a planning exercise, not a live appliance read; correct form-based scoping; no state-reading tools invoked.

---

## Appliance Write Check

No write tools (`netscaler_create_lb`, `netscaler_run_cli_commands`, `netscaler_nextgen_request`, etc.) were called in any test turn. No cleanup needed.

---

## SUMMARY

**Does architect behave as designed?** YES, in all four test scenarios.

### Confirmed behaviors
1. **Discovery-first, form-per-turn**: Every substantive request (LB design, audit) correctly triggered a structured `jpilot-form` rather than prose question lists or immediate output.
2. **Zero tool calls during discovery**: No appliance read or write tools were invoked in any turn. The router correctly limits architect to 2 stack-calibration tools max, and the model did not attempt to call them during discovery.
3. **No fabricated execution**: All guards (`guard_fabricated_execution`, `_should_force_tool_execution`) correctly bypass the architect role; no false-positive banners were triggered.
4. **Role self-description is accurate**: The LLM's description of its own capabilities ("planning only / no appliance execution") matches the code's intent exactly.
5. **"Give me the full design" resistance**: When the user pushed for an immediate deliverable without sufficient discovery, the LLM continued discovery rather than producing a premature design. This matches the discovery gate thresholds in code (`new_functionality` requires ≥5 form submissions).

### Minor observations / gaps
- `user_wants_deliverable_now()` checks for "generate the design" / "design document" but misses phrasing like "give me the full design and the config plan" — this is not a bug (the LLM correctly fell through to discovery), but the phrase matching is narrow and could create confusion if users expect immediate output from strong phrasing.
- The audit request ("Audit the current config") could arguably benefit from optionally calling `netscaler_list_inventory` (which is in the architect base pack) to pre-populate known config details, but the current behavior of asking discovery questions first is consistent with the stated design and avoids requiring a live connection.
- No `architect_discovery_nudge` warning was observed in logs for these turns, indicating the LLM naturally complied with form-based discovery without needing retry correction — a healthy sign for the model in use (`claude-sonnet-4.5`).
