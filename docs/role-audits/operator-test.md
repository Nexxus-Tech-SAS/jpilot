# Operator Role Audit — NetScaler Load Balancer

**Date:** 2026-06-24  
**Tester:** Claude Code (automated API drive)  
**Backend:** http://172.18.0.5:8000  
**Appliance:** NetScaler 192.168.20.220  
**Model/Provider:** As configured in backend (tested via `/copilot/chat` role=operator)

---

## Scenario A — Under-specified Request (test "ask info once")

### Turn 1
**Message:** "Create a load balancer on NetScaler"  
**Latency:** ~10s  

| # | Tool | Arguments (summary) | Result |
|---|------|---------------------|--------|
| — | *(none)* | — | — |

**Tool call count:** 0  
**Did it ask for info once?** YES — rendered a single structured `inputForm` titled "Configure HTTP Load Balancer" with 8 fields: app_name, VIP, front-end port, backend servers, backend port, LB method (select), persistenceType (choice), monitor_type (choice).  
**Did it call tools prematurely?** NO — no tools ran at all.  
**Did it dribble questions?** NO — all missing fields collected in one consolidated form.  
**Hit iteration limit?** NO  
**Key observation:** Uses `inputForm` widget (not plain-text questions) to gather required parameters.

---

### Turn 2
**Message:** "Name op_lb1, VIP 192.168.100.190 port 80 HTTP, one backend server 192.168.100.191 port 80, round robin."  
**Latency:** ~38s  

| # | Tool | Arguments (summary) | Result |
|---|------|---------------------|--------|
| 1 | `netscaler_telnet` | target=192.168.100.190, port=80 | FAILED (SSH connect error) |

**Tool call count:** 1  
**Did it present a plan and ask for approval?** PARTIAL — called `netscaler_telnet` unexpectedly (probe of VIP?) before presenting a second `inputForm` asking for the still-missing `persistenceType` and `monitor_type` (defaults: NONE / tcp-default).  
**Did it ask info once?** NO — the first form (turn 1) did not capture all parameters; a second form appeared in turn 2 for persistence and monitor type.  
**Hit iteration limit?** NO  
**Key observation:** `netscaler_telnet` to the VIP IP is an unexpected/unexplained probe. Model split the information gathering across two turns instead of one.

---

### Turn 3
**Message:** "Use persistence NONE and monitor tcp-default. Yes, apply it."  
**Latency:** ~6s  

| # | Tool | Arguments (summary) | Result |
|---|------|---------------------|--------|
| — | *(none)* | — | — |

**Tool call count:** 0  
**Did it present a plan?** YES — presented 5 CLI steps (add lb vserver, add service, bind, add httpProfile, save config) using raw `add lb vserver ...` syntax.  
**Did it execute?** NO — 0 tool calls. System surfaced a warning banner:  
> ⚠️ **No changes were applied to the appliance.** The reply below claims a configuration change, but no NetScaler tool ran successfully this turn — so nothing was actually sent to the appliance. This usually means the current model is not reliably emitting tool calls. Switch to a more capable model …  
**Hit iteration limit?** NO (0 tool calls, just no tools fired)  
**Key observation:** Model drafted a plan but failed to emit any tool calls. The plan used raw CLI syntax rather than the dedicated `netscaler_create_lb` tool.

---

### Turn 4
**Message:** "Yes"  
**Latency:** ~14s  

| # | Tool | Arguments (summary) | Result |
|---|------|---------------------|--------|
| 1 | `netscaler_run_cli_command` | command="add lb vserver op_lb1-lb HTTP …" | BLOCKED |
| 2 | `netscaler_run_cli_command` | command="add lb vserver op_lb1-lb HTTP …" (variant) | BLOCKED |
| 3 | `netscaler_run_cli_command` | command=compound multi-statement | BLOCKED |

**Tool call count:** 3  
**Blocked?** YES — all 3 calls blocked with:  
> Tool 'netscaler_run_cli_command' blocked: call search_netscaler_cli_reference first and read memoryExcerpts + recommendedCommands from netscaler_adc_cli_memory.md.  
**Execution gate:** `netscaler_run_cli_command` requires a prerequisite `search_netscaler_cli_reference` call; model kept retrying raw CLI without satisfying the gate.  
**Hit max tool call / stuck message?** YES — system surfaced:  
> I've paused — I appear to be stuck. After 3 tool call(s), `netscaler_run_cli_command` failed several times this turn.  
**Did it use dedicated netscaler_create_lb?** NO — fell back to raw CLI every time.  
**Key observation:** Model never tried the dedicated `netscaler_create_lb` tool. It hit the gate-block loop 3 times and stopped.

---

### Turn 5 (remediation: explicit hint to use dedicated tool)
**Message:** "Please use the netscaler_create_lb tool to create this load balancer instead of run_cli_command."  
**Latency:** ~22s  

| # | Tool | Arguments (summary) | Result |
|---|------|---------------------|--------|
| 1 | `netscaler_create_lb` | name=op_lb1, vip=192.168.100.190, port=80, HTTP, servers=["192.168.100.191"], lb_method=ROUNDROBIN, persistence=NONE, **dry_run=true** | SUCCESS (preview) |
| 2 | `netscaler_create_lb` | same params, **confirm=true** | SUCCESS — 7 commands executed on 192.168.20.220 |

**Tool call count:** 2  
**Dry-run before commit?** YES — call 1 was dry_run=true, call 2 was confirm=true.  
**Execution result:** 7/7 commands ran; 3 commands reported exit=1 but with "Warning" output (HTTP profile security warning), not hard errors. LB op_lb1 created successfully.  
**Hit iteration limit?** NO  
**Key observation:** When explicitly told to use `netscaler_create_lb`, the model used it correctly with proper dry_run → confirm pattern.

---

### Scenario A Summary
| Metric | Value |
|--------|-------|
| Total turns to completion | 5 |
| Total tool calls | 6 (0+1+0+3+2) |
| Tool calls that succeeded | 2 |
| Tool calls that were blocked/gated | 3 |
| Tool calls that failed (telnet) | 1 |
| Total latency | ~90s |
| Asked info once? | NO (2 separate forms) |
| Presented plan? | YES (turn 3) but failed to execute it |
| Hit stuck/limit message? | YES (turn 4) |
| Used dedicated netscaler_create_lb? | Only when explicitly told to (turn 5) |

---

## Scenario B — Fully-Specified Request (test directness)

### Turn 1
**Message:** "Create a load balancer named op_lb2 on NetScaler, VIP 192.168.100.192 port 80 HTTP, backend 192.168.100.193 port 80."  
**Latency:** ~5s  

| # | Tool | Arguments (summary) | Result |
|---|------|---------------------|--------|
| — | *(none)* | — | — |

**Tool call count:** 0  
**Action (plan vs immediate)?** Presented a clear plan with named objects (op_lb2, op_lb2_srv1, op_lb2_svc1) and asked "Do you want me to proceed?"  
**Did it ask for more info?** NO — used sensible defaults (ROUNDROBIN) for unspecified fields.  
**Did it use dedicated tool?** NO tool calls at all (plan stage).  
**Hit iteration limit?** NO  
**Key observation:** With full spec, model correctly moved to plan-then-confirm without asking additional questions.

---

### Turn 2
**Message:** "Yes, go ahead."  
**Latency:** ~8s  

| # | Tool | Arguments (summary) | Result |
|---|------|---------------------|--------|
| 1 | `netscaler_run_cli_command` | command="add lb vserver op_lb2 HTTP 192.168.100.192 80" | BLOCKED |
| 2 | `netscaler_run_cli_command` | command="add server op_lb2_srv1 192.168.100.193" | BLOCKED |
| 3 | `netscaler_run_cli_command` | command="add service op_lb2_svc1 op_lb2_srv1 HTTP 80" | BLOCKED |

**Tool call count:** 3  
**Blocked?** YES — all 3 with same gate message:  
> Tool 'netscaler_run_cli_command' blocked: call search_netscaler_cli_reference first …  
**Hit stuck/limit message?** YES:  
> I've paused — I appear to be stuck. After 1 tool call(s), `netscaler_run_cli_command` failed several times this turn.  
**Used dedicated tool?** NO  
**Key observation:** Same problem as Scenario A. Model defaults to raw CLI, hits gate-block, stops.

---

### Turn 3 (remediation: hint to use dedicated tool)
**Message:** "Please use the netscaler_create_lb tool to create op_lb2."  
**Latency:** ~18s  

| # | Tool | Arguments (summary) | Result |
|---|------|---------------------|--------|
| 1 | `netscaler_create_lb` | app_name=op_lb2, servers passed as JSON string (malformed) | FAILED (arg parsing error) |
| 2 | `netscaler_create_lb` | name=op_lb2, servers as JSON string (malformed) | FAILED (arg parsing error) |
| 3 | `netscaler_create_lb` | name=op_lb2, servers as JSON string (still malformed), **dry_run="true"** (string) | SUCCESS (dry_run) — but servers parsed character-by-character (treat IP as iterable) |

**Tool call count:** 3  
**Did execution succeed?** NO — dry_run showed malformed commands (each char of IP as separate server).  
**Stuck/limit?** NO, but 2/3 calls failed due to argument format issues.  
**System banner?** YES:  
> ⚠️ No changes were applied to the appliance. … no NetScaler tool ran successfully this turn.  
**Key observation:** Model struggled with the `servers` argument type — passed it as a JSON-encoded string `"[\"192.168.100.193\"]"` instead of an array, causing character-by-character parsing.

---

### Turn 4 (remediation: explicit correct args format)
**Message:** "Use netscaler_create_lb with: name=op_lb2, vip=192.168.100.192, port=80, service_type=HTTP, servers=["192.168.100.193"], server_port=80, lb_method=ROUNDROBIN, persistence=NONE, confirm=true"  
**Latency:** ~16s  

| # | Tool | Arguments (summary) | Result |
|---|------|---------------------|--------|
| 1 | `netscaler_create_lb` | name=op_lb2, vip=192.168.100.192, port=80, HTTP, servers=["192.168.100.193"], server_port=80, ROUNDROBIN, NONE, **confirm=true** | SUCCESS — 7 commands executed |

**Tool call count:** 1  
**Execution result:** 7/7 commands ran (same HTTP-profile warnings as op_lb1, non-fatal). LB op_lb2 created.  
**Hit iteration limit?** NO  
**Key observation:** When the exact correct argument schema was spelled out, the model called the tool correctly in a single shot — no dry_run step this time (went straight to confirm=true).

---

### Scenario B Summary
| Metric | Value |
|--------|-------|
| Total turns to completion | 4 |
| Total tool calls | 7 (0+3+3+1) |
| Tool calls that succeeded | 2 (1 dry, 1 live) |
| Tool calls that were blocked/gated | 3 |
| Tool calls that failed (arg errors) | 2 |
| Total latency | ~47s |
| Asked extra info? | NO (used defaults) |
| Presented plan? | YES (turn 1) |
| Hit stuck/limit message? | YES (turn 2) |
| Used dedicated netscaler_create_lb? | Only when explicitly told (turns 3-4) |

---

## SUMMARY

| Question | Finding |
|----------|---------|
| **Total tool calls (A end-to-end)** | 6 over 5 turns (~90s total latency) |
| **Total tool calls (B end-to-end)** | 7 over 4 turns (~47s total latency) |
| **Hit iteration/max-tool-call limit?** | YES — in both scenarios the "stuck" banner fired when `netscaler_run_cli_command` was blocked 3 consecutive times |
| **Asked info once vs piecemeal?** | PIECEMEAL in A (2 separate forms across turns 1 and 2); ONCE in B (no extra questions, used defaults) |
| **Dedicated netscaler_create_lb vs raw CLI?** | Model always defaulted to raw `netscaler_run_cli_command` — only used `netscaler_create_lb` when the user explicitly named the tool |
| **Gate-blocking (`netscaler_run_cli_command`)** | `search_netscaler_cli_reference` is a mandatory prerequisite that the model never called autonomously; every raw CLI attempt was blocked |
| **Unexpected behavior** | Turn A2: spurious `netscaler_telnet` probe; Turn B3: `servers` passed as JSON-encoded string causing character-by-character IP parsing |
| **Plan-then-execute pattern** | Present in both scenarios but the "execute" step consistently failed without user intervention to name the correct tool |

### Key Issues Identified

1. **Wrong tool selection (root cause of all failures):** The model defaults to `netscaler_run_cli_command` for LB creation instead of the dedicated `netscaler_create_lb`. Since `netscaler_run_cli_command` requires `search_netscaler_cli_reference` first, every direct CLI attempt is gate-blocked.

2. **No autonomous recovery:** After hitting the gate-block the model does not try `search_netscaler_cli_reference` to unlock the gate, nor does it fall back to `netscaler_create_lb`. It hits the block 3 times and declares itself stuck.

3. **Info gathering split across turns (Scenario A):** The first `inputForm` asked for 8 fields but did not include persistence or monitor type; a second form in turn 2 asked for those. This split increased round-trips unnecessarily.

4. **`servers` argument type confusion (Scenario B Turn 3):** The model serialised the array as a JSON string rather than a native array, causing the tool to iterate over individual characters of the IP string.

5. **Spurious `netscaler_telnet` call:** In A Turn 2 the model called `netscaler_telnet` to probe the VIP — this call is unrelated to the creation workflow, adds latency, and failed silently.
