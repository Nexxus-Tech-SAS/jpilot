"""Tests for the Operator confirm-before-mutate gate helpers (Phase 1).

These cover the pure helpers behind the backend auto-path gate: affirmation detection,
prior-turn recovery, and the plan formatters. The orchestrator wires these so that a
first-contact deploy/remove returns a plan (no writes) and a short "yes" — which recovers
the original request from history — executes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.copilot_deploy import (  # noqa: E402
    detect_natural_language_lb_request,
    format_classic_lb_plan,
    parse_natural_language_lb_request,
)
from app.services.copilot_form import (  # noqa: E402
    is_affirmation,
    is_form_submission,
    last_user_message,
)
from app.services.copilot_remove import (  # noqa: E402
    detect_lb_removal_request,
    format_lb_removal_plan,
    parse_lb_removal_targets,
)

_DEPLOY_SPEC = (
    "Create a load balancer for demo1. Front end ip 192.168.20.224 SSL "
    "(use the wildcard certificate). Backend servers 192.168.20.234 ports 8060 and 8070. "
    "TCP monitor, no persistence."
)
_REMOVE_SPEC = "remove iis_lb_app and exchange_vs and all services and services groups link to it"


def test_is_affirmation_true_for_short_confirmations():
    for msg in ["yes", "Yes", "yes please", "Yes, proceed", "proceed", "confirm",
                "go ahead", "do it", "sí", "procede", "ok", "Okay!"]:
        assert is_affirmation(msg) is True, msg


def test_is_affirmation_false_for_requests_and_noise():
    for msg in [_DEPLOY_SPEC, _REMOVE_SPEC, "show me the IPs", "", "   ",
                "no", "yes but change the VIP to 10.0.0.9 and add a backend"]:
        assert is_affirmation(msg) is False, msg


def test_is_affirmation_false_for_form_submission():
    assert is_affirmation("Configuration inputs for: demo1") is False
    assert is_form_submission("Configuration inputs for: demo1") is True


def test_last_user_message_returns_most_recent_user_turn():
    history = [
        {"role": "user", "content": _DEPLOY_SPEC},
        {"role": "assistant", "content": "Plan — classic load balancer ..."},
    ]
    assert last_user_message(history) == _DEPLOY_SPEC
    assert last_user_message([]) == ""
    assert last_user_message(None) == ""


def test_deploy_gate_roundtrip():
    fields = parse_natural_language_lb_request(_DEPLOY_SPEC)
    # First contact: a complete spec is detected but is NOT an affirmation → present plan.
    assert detect_natural_language_lb_request(_DEPLOY_SPEC, fields) is True
    assert is_affirmation(_DEPLOY_SPEC) is False

    plan = format_classic_lb_plan("ns01", fields)
    assert "demo1" in plan
    assert "192.168.20.224" in plan
    assert "Reply **yes**" in plan

    # Confirmation turn: "yes" recovers the spec from history and re-detects it for execution.
    history = [{"role": "user", "content": _DEPLOY_SPEC}]
    assert is_affirmation("yes") is True
    recovered = last_user_message(history)
    assert detect_natural_language_lb_request(recovered) is True


def test_remove_gate_roundtrip():
    assert detect_lb_removal_request(_REMOVE_SPEC) is True
    assert is_affirmation(_REMOVE_SPEC) is False

    targets = parse_lb_removal_targets(_REMOVE_SPEC)
    assert "iis_lb_app" in targets and "exchange_vs" in targets

    plan = format_lb_removal_plan("ns01", targets)
    assert "iis_lb_app" in plan
    assert "Reply **yes**" in plan

    # Confirmation recovers the original removal request from history.
    history = [{"role": "user", "content": _REMOVE_SPEC}]
    assert is_affirmation("yes, proceed") is True
    assert detect_lb_removal_request(last_user_message(history)) is True
