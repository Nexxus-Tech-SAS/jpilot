# JPilot chat feedback watch

Live watcher on the backend container logs (`nexxus-workspace-jpilot-backend-api-1`).
JPilot does not persist chat transcripts server-side, so the logs are the feedback feed:
every `tool_call`, guard firing, gate block, stuck/loop-breaker, and error surfaces here.

The watcher streams matching lines as notifications while other work proceeds. Issues are
triaged and logged below (newest first). Signatures watched: guard firings, "Deployment may
be incomplete", stuck/loop-breaker, iteration limit, fabricated_execution, unverified read,
tracebacks/exceptions, HTTP 500.

## Triaged findings

| When (UTC) | Signature | Context | Verdict | Action |
|---|---|---|---|---|
| session start | Traceback: `ValueError: name is required` / `query is required` (copilot_service.py:2096/1794) | Model called a tool with missing/wrong params (e.g. `question` instead of `query`); loop catches it, model retries & recovers | Recovered, but logged as ERROR+traceback (misleading noise). Low-pri: catch tool-arg ValueErrors → clean tool-error result instead of traceback | note for cleanup |
| session start | Operator LB create via raw `run_cli_command` with invalid `-purpose lb` arg ("No such argument") | Model hand-built `add lb vserver … -purpose …` instead of using `netscaler_create_lb`; got gated → searched → built buggy CLI | Reinforces O6: operator LB still escapes to raw CLI. Fix in O6. | folding into O6 |
| session start | fabricated_execution_guard fired (toolCalls=0) | Model claimed a config change but ran no tool | Likely guard working as intended (catching an unbacked success claim); watch for false-positive recurrence | watching |
