"""Tests for the Phase 3 loop-breakers (conservative, stop-and-ask, admin-configurable)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.copilot_orchestration import (  # noqa: E402
    OrchestrationRuntime,
    OrchestrationSettings,
    check_loop_breakers,
    orchestration_settings_from_document,
    tool_result_is_failure,
)

_FAIL = '{"success": false, "errorMessage": "boom"}'


def _runtime(settings: OrchestrationSettings | None = None) -> OrchestrationRuntime:
    return OrchestrationRuntime(settings or OrchestrationSettings())


def test_tool_result_is_failure_detection():
    assert tool_result_is_failure('{"success": false}') is True
    assert tool_result_is_failure('{"success": true}') is False
    assert tool_result_is_failure('{"commandFailed": true}') is True
    assert tool_result_is_failure('{"exitStatus": 1}') is True
    assert tool_result_is_failure('{"exitStatus": 0}') is False
    assert tool_result_is_failure('{"results": [{"success": true}, {"success": false}]}') is True
    assert tool_result_is_failure("10.0.0.1\n10.0.0.2") is False  # plain read output
    assert tool_result_is_failure("[1, 2, 3]") is False  # non-dict json


def test_repeated_identical_failed_call_breaks_at_limit():
    rt = _runtime()
    args = {"commands": ["add lb vserver x"]}
    # First identical failure: not yet at the limit of 2.
    assert check_loop_breakers(rt, name="netscaler_run_cli_commands", arguments=args, result=_FAIL) is None
    # Second identical failure → break.
    brk = check_loop_breakers(rt, name="netscaler_run_cli_commands", arguments=args, result=_FAIL)
    assert brk is not None
    assert brk.reason == "repeated_failed_call"
    assert "paused" in brk.message.lower()


def test_per_tool_failure_breaks_at_three_distinct_args():
    rt = _runtime()
    # Three failures of the same tool with DIFFERENT args → (a) never trips, (b) trips at 3.
    assert check_loop_breakers(rt, name="netscaler_nextgen_request", arguments={"path": "/a"}, result=_FAIL) is None
    assert check_loop_breakers(rt, name="netscaler_nextgen_request", arguments={"path": "/b"}, result=_FAIL) is None
    brk = check_loop_breakers(rt, name="netscaler_nextgen_request", arguments={"path": "/c"}, result=_FAIL)
    assert brk is not None
    assert brk.reason == "per_tool_failure"


def test_no_progress_breaks_only_past_floor():
    ok = '{"success": true, "data": "same"}'  # successful but identical every time

    # Below the floor: never breaks, even on a long run of duplicate reads.
    below = _runtime()
    below.tool_rounds = 3
    for _ in range(12):
        assert check_loop_breakers(below, name="netscaler_list_ip_addresses", arguments={"a": 1}, result=ok) is None

    # Past the floor: a window of no-new-result steps trips the stall breaker.
    rt = _runtime()
    rt.tool_rounds = 20
    last = None
    for _ in range(7):
        last = check_loop_breakers(rt, name="netscaler_list_ip_addresses", arguments={"a": 1}, result=ok)
    assert last is not None
    assert last.reason == "no_progress"


def test_happy_multistep_path_never_false_trips():
    rt = _runtime()
    rt.tool_rounds = 25  # well past the floor
    for i in range(15):
        # Distinct successful results each round = progress; no failures.
        result = f'{{"success": true, "n": {i}}}'
        assert check_loop_breakers(rt, name="netscaler_list_virtual_servers", arguments={"i": i}, result=result) is None


def test_thresholds_are_admin_configurable():
    settings = orchestration_settings_from_document(
        {
            "repeatedFailedCallLimit": 5,
            "perToolFailureLimit": 9,
            "noProgressWindow": 50,
            "noProgressFloor": 100,
        }
    )
    assert settings.repeated_failed_call_limit == 5
    assert settings.per_tool_failure_limit == 9
    assert settings.no_progress_window == 50
    assert settings.no_progress_floor == 100

    rt = _runtime(settings)
    args = {"a": 1}
    # With the limit raised to 5, four identical failures must NOT break.
    for _ in range(4):
        assert check_loop_breakers(rt, name="t", arguments=args, result=_FAIL) is None
    brk = check_loop_breakers(rt, name="t", arguments=args, result=_FAIL)  # fifth
    assert brk is not None
    assert brk.reason == "repeated_failed_call"


def test_settings_from_document_reads_loop_breaker_keys():
    s = orchestration_settings_from_document(
        {
            "loopBreakersEnabled": False,
            "repeatedFailedCallLimit": 4,
            "perToolFailureLimit": 6,
            "noProgressWindow": 9,
            "noProgressFloor": 15,
        }
    )
    assert s.loop_breakers_enabled is False
    assert s.repeated_failed_call_limit == 4
    assert s.per_tool_failure_limit == 6
    assert s.no_progress_window == 9
    assert s.no_progress_floor == 15
    # Defaults when the keys are absent.
    assert orchestration_settings_from_document({}).loop_breakers_enabled is True


def test_disabled_toggle_skips_all_breakers():
    rt = _runtime(OrchestrationSettings(loop_breakers_enabled=False))
    # A flood of identical failures never breaks when the feature is off.
    for _ in range(10):
        assert check_loop_breakers(rt, name="netscaler_run_cli_commands", arguments={"c": 1}, result=_FAIL) is None


def test_platform_settings_schema_exposes_loop_breakers():
    from app.services.copilot_platform_service import (
        CopilotPlatformSettingsResponse,
        CopilotPlatformSettingsUpdate,
    )

    resp = CopilotPlatformSettingsResponse()
    assert resp.loopBreakersEnabled is True
    assert (resp.repeatedFailedCallLimit, resp.perToolFailureLimit) == (2, 3)
    assert (resp.noProgressWindow, resp.noProgressFloor) == (5, 8)

    upd = CopilotPlatformSettingsUpdate(loopBreakersEnabled=False, noProgressFloor=20)
    assert upd.loopBreakersEnabled is False
    assert upd.noProgressFloor == 20


@pytest.mark.asyncio
async def test_update_platform_settings_clamps_and_persists_loop_breakers():
    from app.services.copilot_platform_service import (
        CopilotPlatformSettingsUpdate,
        default_document,
        update_platform_settings,
    )

    doc = default_document()
    coll = MagicMock()
    coll.find_one = AsyncMock(return_value=doc)
    coll.insert_one = AsyncMock()

    async def _fake_update(_filter, update, upsert=False):
        doc.update(update["$set"])
        return MagicMock()

    coll.update_one = AsyncMock(side_effect=_fake_update)
    db = MagicMock()
    db.copilotPlatformSettings = coll

    payload = CopilotPlatformSettingsUpdate(
        loopBreakersEnabled=False,
        repeatedFailedCallLimit=999,  # clamps to 10
        noProgressFloor=1,            # clamps to 2
    )
    resp = await update_platform_settings(db, payload)
    assert resp.loopBreakersEnabled is False
    assert resp.repeatedFailedCallLimit == 10
    assert resp.noProgressFloor == 2
