# JPilot chat feedback watch

Live watcher on the backend container logs (`nexxus-workspace-jpilot-backend-api-1`).
JPilot does not persist chat transcripts server-side, so the logs are the feedback feed:
every `tool_call`, guard firing, gate block, stuck/loop-breaker, and error surfaces here.

The watcher streams matching lines as notifications while other work proceeds. Issues are
triaged and logged below (newest first). Signatures watched: guard firings, "Deployment may
be incomplete", stuck/loop-breaker, iteration limit, fabricated_execution, unverified read,
tracebacks/exceptions, HTTP 500.

## Watch session 2026-06-25 (continued, watermark 06:25)

- cycle 1 (06:42 UTC): quiet. Post-06:25 logs show only 2 clean operator read turns (`netscaler_list_virtual_servers`, toolCalls=1, 200 OK, no guards/errors). The `netscaler_delete_lb failed` traceback (06:19:32) and `netscaler_run_cli_commands BLOCKED` (06:20:05) both PREDATE the watermark — already triaged (delete_lb = row 1). MongoDB `AutoReconnect`/`ConnectionResetError` at 06:02:03 is an infra blip, pre-watermark, not chat feedback. No new issues.
- cycle 2 (06:47 UTC): quiet. No chat/tool activity in the interval; only health checks.
- STOP EARLY after 2 consecutive quiet cycles (per run policy). Watermark advanced to 06:47. No fixes, no flags, nothing still-open. VERSION unchanged at 0.105.

## Triaged findings

| When (UTC) | Signature | Context | Verdict | Action |
|---|---|---|---|---|
| 2026-06-25 06:19 | Traceback `ValueError: name is required` (copilot_service.py:2158) from `netscaler_delete_lb` | Model called `netscaler_delete_lb` with `vs_name` instead of `name` (`{"vs_name":"o6_lb1_vs","confirmed":true}`); `confirm`/`confirmed` bypassed the destructive gate → reached `execute_copilot_tool` → raised. Model recovered (re-called with `name`). The traceback fired at 06:19:32, just after a transient `--reload` at 06:18:15 during an active human edit window (server procs 320–426 over 06:16–06:18) — i.e. an intermediate pre-commit state. The committed v0.104 catch in `_execute_tool_with_memory_gate` handles this correctly; no traceback on current code (logs clean since the 06:25:11 reload). | NOT a regression — v0.104 fix is correct & present. Added a regression **test** so it can't silently break. Live-verified: read turn clean, no tracebacks. | FIXED-as-test v0.105 (`test_copilot_tool_arg_errors.py`, 3/3) |
| session start | Traceback: `ValueError: name is required` / `query is required` (copilot_service.py:2096/1794) | Model called a tool with missing/wrong params (e.g. `question` instead of `query`); loop catches it, model retries & recovers | Recovered, but logged as ERROR+traceback (misleading noise). Low-pri: catch tool-arg ValueErrors → clean tool-error result instead of traceback | note for cleanup |
| session start | Operator LB create via raw `run_cli_command` with invalid `-purpose lb` arg ("No such argument") | Model hand-built `add lb vserver … -purpose …` instead of using `netscaler_create_lb`; got gated → searched → built buggy CLI | FIXED in O6 part 1 (v0.101): backstop blocks+redirects raw `add lb vserver`; router strips raw CLI on LB turns | done |
| recurring (3×) | Traceback `ValueError: name is required` / `query is required` from execute_copilot_tool | Model calls a tool with a missing required arg → previously raised as ValueError + ERROR traceback | FIXED v0.104: _execute_tool_with_memory_gate catches tool-arg ValueErrors → logs WARNING + returns a clean `{success:false,error,hint}` result the model retries from. No more tracebacks for arg errors | done |
| session start | fabricated_execution_guard fired (toolCalls=0) | Model claimed a config change but ran no tool | Likely guard working as intended (catching an unbacked success claim); watch for false-positive recurrence | watching |
