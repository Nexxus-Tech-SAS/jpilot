# Architect Role — Workflow Findings & Recommendations

**Date:** 2026-06-24
**Scope:** READ-ONLY code audit of the Architect chat workflow (no code changed).
**Inputs:** `docs/role-audits/architect-test.md` (4 live test turns) + source audit of
`copilot_architect_discovery.py`, `copilot_orchestrator.py`, `copilot_tool_router.py`,
`copilot_roles.py`, `copilot_form.py`, and the netscaler architect prompt fragments.

**Verdict:** Architect is **essentially fine** and behaves as designed. The only real
gaps are narrow phrase-matching in `user_wants_deliverable_now()` and the lack of an
explicit "best-effort now" escape hatch. Recommendations below are small and low-risk.

---

## 1. Confirmation the workflow matches intended design

| Intended behavior | Where enforced | Confirmed |
|---|---|---|
| Plan-only role; never requires/uses an appliance | `copilot_roles.py:55-59` (`requiresAppliance=False`), `:136-138` (`role_requires_appliance` → False for architect), `:161-171` (system prompt: "planning context only, do not run appliance tools") | YES — Tests 1–4, zero appliance calls |
| Discovery-first, **one `jpilot-form` per turn** | `architect_discovery.md:5` ("One topic per turn"), `architect_intent_routing.md` (per-branch topic lists) | YES — Tests 1, 2, 4 each produced exactly one form |
| Turn-1 asks **planning intent** when unknown | `architect_intent_routing.md` ("What are you planning?" form) | YES — Test 1 |
| **No MCP tools during discovery** | `architect_tools_enabled()` `copilot_architect_discovery.py:319-337` returns False during discovery; orchestrator gates the LLM tool list via `_llm_tools_for_turn()` `copilot_orchestrator.py:383-396` (returns `None` → no tools sent) | YES — no tools offered/called in any test |
| Stray tool calls are **blocked**, not executed | `block_architect_tool_during_discovery()` `copilot_architect_discovery.py:449-488`, wired in `_execute_chat_tool()` `copilot_orchestrator.py:415-424` | YES (by inspection) |
| Architect base pack is minimal | `ROLE_BASE_PACKS["architect"] = frozenset({"inventory"})` `copilot_tool_router.py:99`; architect branch returns an **empty** pack set during discovery `copilot_tool_router.py:207-213` | YES — router emitted ≤2 stack-calibration tools, none appliance |
| Hard role allow-list (defense in depth) | `filter_tools_for_role()` `copilot_roles.py:234-237` restricts architect to `_PLANNING_TOOLS` `:79-89`; `assert_tool_allowed_for_role()` `:252-260` raises on anything else | YES (by inspection) |
| Discovery → deliverable thresholds | `architect_discovery_ready_for_deliverable()` `copilot_architect_discovery.py:300-316`: new_functionality ≥5, new_deployment ≥7, change_control ≥4 (or fast paths ≥1/≥3), default ≥6 | YES — Test 2 stayed in discovery after 1 topic |
| Architect bypasses fabricated-execution / force-tool guards | `_should_force_tool_execution()` `copilot_orchestrator.py:466-467` returns False for architect | YES — no false banners |
| Deliverable markers | `_DELIVERABLE_MARKERS` `copilot_architect_discovery.py:41-44` (`jpilot-design-document` / `jpilot-change-control-document`) | YES (by inspection) |

**Conclusion:** All five "confirmed behaviors" from the test report are backed by explicit
code. The architect is implemented as a prompt-driven, tool-gated, discovery-first planner.

---

## 2. Real issues found

### 2.1 [workflow-code] `user_wants_deliverable_now()` phrase matching is narrow — MINOR
`copilot_architect_discovery.py:99-120` recognizes a deliverable request only via:
- `_DESIGN_NOW_RE` `:26-29` — a **whole-message** single command: `go|yes|ok|okay|continue|proceed|generate|draft|build` (optionally with a trailing period). A user who types "generate the full design plan" does **not** match this regex (it requires the verb to be essentially the entire message), and only matches `_DESIGN_NOW_PHRASES` if it contains one of the exact substrings.
- `_DESIGN_NOW_PHRASES` `:31-39` — `"generate the design"`, `"produce the design"`, `"write the design"`, `"design document"`, `"ready to generate"`, `"let's generate"`, `"lets generate"`.
- `_CHANGE_CONTROL_NOW_PHRASES` `:68-75` for change-control.

Phrasings that **fall through to more discovery** (observed in Test 2):
- "give me the full design and the config plan"
- "give me your best-effort design now"
- "skip the questions, just design it"
- "I have enough info, draft the design" (the verb "draft" is not the whole message)
- "create the design now" / "make the design"

**Impact:** low. This is *not* a correctness bug — when the phrase misses, the model
re-enters discovery (safe, conservative). But a user issuing a strong, explicit
"produce it now" instruction can be surprised by another form. It is a UX/expectation
gap, not a stuck-state.

### 2.2 [workflow-code] No explicit "best-effort now / skip remaining discovery" escape — MINOR
There is a **functional** escape today: `architect_tools_enabled()` `:335-337` returns True
whenever `user_wants_deliverable_now()` is True — *regardless of how many forms were
submitted*. So a user CAN force a deliverable at any point. The gap is purely that the
phrases that trigger it are narrow (see 2.1) and **the user is never told the magic words**.
The prompt only mentions "the user says to generate" (`architect_discovery.md:7`) and
"go / generate / continue" (`architect_intent_routing.md`, last line). There is no
user-facing affordance like "Say *generate the design* anytime to skip ahead."

### 2.3 [model-behavior, not a bug] Can a user get stuck in endless discovery?
**No hard lock exists.** Two independent break-outs:
1. **User-driven:** any matching deliverable phrase flips `architect_tools_enabled` and
   the orchestrator nudges the model to write the doc (`_design_now_nudge` `:254-284`).
2. **Threshold-driven:** once form counts cross `architect_discovery_ready_for_deliverable`
   `:300-316`, `build_discovery_form_submit_nudge` `:423-424` emits `_deliverable_ready_nudge`
   which orders the model to STOP asking and output the deliverable; `block_architect_tool_during_discovery`
   `:473-482` then blocks further search tools.

Residual risk is **model-behavior only**: if the LLM ignores the deliverable nudge and
keeps emitting forms, nothing in code force-converts a form into a document. The retry
loop (`_architect_discovery_retry_nudge` `copilot_orchestrator.py:440-457`) only fires on
*bad prose* (checklists / leaked tool markup, `_BAD_DISCOVERY_RE` `:17-22`) — a
**well-formed** `jpilot-form` is always accepted (`build_architect_discovery_nudge` `:541-543`
returns None when a form parses). So a stubborn model could, in theory, loop forever across
turns producing valid forms. In testing (sonnet-4.5) this never happened — the model complied
with the deliverable nudge. This is acceptable but worth noting; the mitigation is the
user-side escape in 2.1/2.2.

Note: within a single turn there is **no** infinite loop — all retries run inside the bounded
`for _ in range(runtime.max_tool_iterations)` loop (`copilot_orchestrator.py:1432/1638/1834`).

### 2.4 [workflow-code] Stale doc-tool name in `ARCHITECT_SEARCH_TOOL_NAMES` — TRIVIA
`ARCHITECT_SEARCH_TOOL_NAMES` `:10-15` lists `search_f5_documentation` alongside the
netscaler `search_jpilot_architect_resources`. That set is used to count/allow searches in
`block_architect_tool_during_discovery`. It is harmless (it only ever over-counts on the
wrong vendor, which can't be reached) but slightly muddled — the netscaler-specific search
allow-list mixes in an F5 tool name. Not worth changing on its own.

### 2.5 One-topic-per-turn pace — is it too slow?
**Not structurally too slow, and partially mitigated already.** "One topic per turn" is a
*prompt* instruction (`architect_discovery.md:5`), not a code constraint — nothing stops the
model from putting several related fields in one form, and the branches already encourage
**consolidation**: the change_control fast path emits "one consolidated `jpilot-form`" and the
focused path caps at "at most three" forms (`architect_intent_routing.md`, Branch C). The pace
only bites for `new_deployment` (≥7 forms) and `new_functionality` (≥5). For a power user this
is several round-trips. The escape hatch (2.1/2.2) is the right pressure valve rather than
loosening the per-turn rule (which exists to avoid prose question-dumps).

---

## 3. Recommendations (prioritized)

### R1 [workflow-code] — Broaden `user_wants_deliverable_now()` phrasing. PRIORITY 1 (small)
Add the common "produce it now" variants and make matching tolerant of leading filler.

**Before** (`copilot_architect_discovery.py:31-39`):
```python
_DESIGN_NOW_PHRASES = (
    "generate the design",
    "produce the design",
    "write the design",
    "design document",
    "ready to generate",
    "let's generate",
    "lets generate",
)
```
**After:**
```python
_DESIGN_NOW_PHRASES = (
    "generate the design",
    "produce the design",
    "write the design",
    "create the design",
    "make the design",
    "draft the design",
    "build the design",
    "full design",
    "design document",
    "best-effort design",
    "best effort design",
    "skip the questions",
    "skip discovery",
    "stop asking",
    "enough questions",
    "i have enough",
    "ready to generate",
    "let's generate",
    "lets generate",
    "just design",
)
```
Rationale: every added phrase is an unambiguous "produce it" signal. Risk of false-positive
mid-discovery is low because these are imperative; even if one fires a touch early, the
deliverable nudge tells the model to mark unknowns **TBD** — which is the intended behavior
for an explicit "give me your best shot now" request.

Optional companion: also relax `_DESIGN_NOW_RE` `:26-29` so a verb followed by an object still
counts (it currently requires the verb to be ~the whole message):
```python
# Before — verb must be essentially the entire message
_DESIGN_NOW_RE = re.compile(
    r"^\s*(go|yes|ok|okay|continue|proceed|generate|draft|build)\s*\.?\s*$",
    re.IGNORECASE,
)
# After — allow a short imperative like "generate it" / "build the doc now"
_DESIGN_NOW_RE = re.compile(
    r"^\s*(go|yes|ok|okay|continue|proceed|generate|draft|build)"
    r"(\s+(it|that|now|the\s+(design|doc|document|plan)).*)?\.?\s*$",
    re.IGNORECASE,
)
```
Keep `_CHANGE_CONTROL_NOW_PHRASES` mutually exclusive (it already returns False when
`_DESIGN_NOW_RE` matches, `:113-114`) so a generic "generate" still routes to design, not
change-control — preserve that ordering.

### R2 [workflow-code] — Surface the escape hatch to the user. PRIORITY 2 (tiny, prompt-only)
The escape already works in code; users just don't know about it. Add one line to the
discovery prompt so the model offers it.

**Edit** `app/resources/prompts/netscaler/roles/architect_discovery.md` (and the f5/cisco peers),
e.g. append to step 3:
```
3. **Submit label** — "submitLabel": "Continue" during discovery; produce the design when
   enough is known or the user says to generate. You may add a one-line hint under the form
   such as: "_Prefer a best-effort draft now? Say 'generate the design' and I'll fill gaps
   with TBD._" (show this hint at most once per conversation).
```
This converts the hidden code affordance into a discoverable UX, directly fixing the Test-2
surprise without touching the gating logic.

### R3 [workflow-code, optional] — Hard cap on discovery forms as a safety net. PRIORITY 3 (small)
To fully close the theoretical "stubborn model loops on valid forms" gap (2.3), force a
deliverable once form submissions clearly exceed the branch threshold (e.g. threshold + 2).
`architect_discovery_ready_for_deliverable()` already centralizes the thresholds; a sibling
`architect_discovery_must_deliver()` returning True at `count >= threshold + 2` could be OR'd
into `_should_force_deliverable_output()` `:371-380` so the deliverable nudge fires even if the
model produced a valid (not bad-prose) form. Low priority — never observed with sonnet-4.5,
and R1+R2 give the user a manual out.

### R4 [workflow-code, trivia] — Tidy `ARCHITECT_SEARCH_TOOL_NAMES`. PRIORITY 4
Drop `search_f5_documentation` from the netscaler-oriented set in
`copilot_architect_discovery.py:10-15`, or make the allow-list vendor-aware. Cosmetic only.

---

## 4. Tagging summary

| Item | Tag | Severity |
|---|---|---|
| Narrow `user_wants_deliverable_now` phrases (2.1) | [workflow-code] | Minor (UX) |
| No surfaced escape hatch (2.2) | [workflow-code] | Minor (UX) |
| "Stuck in discovery?" — soft only, model-dependent (2.3) | [model-behavior] | Low / acceptable |
| Mixed-vendor search name (2.4) | [workflow-code] | Trivia |
| One-topic-per-turn pace (2.5) | [workflow-code] | Acceptable as-is |

**Bottom line:** The Architect role is **working as designed and needs only minor polish.**
The core gating, tool-stripping, and discovery-first behavior are correct and defended in depth.
Ship **R1** (broaden phrases) and **R2** (surface the escape hint); treat **R3**/**R4** as
optional cleanup.
