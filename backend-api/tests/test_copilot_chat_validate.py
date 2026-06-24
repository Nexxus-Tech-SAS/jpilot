"""Tests for the persona-first resolve path in _validate_copilot_chat_request."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers.copilot import _validate_copilot_chat_request  # noqa: E402
from app.schemas.copilot import ChatRequest  # noqa: E402


@pytest.mark.asyncio
async def test_persona_id_drives_role_and_ignores_wire_role():
    db = MagicMock()  # architect needs no appliance lookup
    payload = ChatRequest(message="plan an HA pair", role="operator", personaId="architect")
    chat_role, appliance_name, persona = await _validate_copilot_chat_request(payload, db)
    assert chat_role.value == "architect"  # persona wins over the wire `role`
    assert persona.kind == "builtin"
    assert persona.baseRole == "architect"
    assert appliance_name == ""


@pytest.mark.asyncio
async def test_legacy_role_without_persona_resolves_to_builtin():
    db = MagicMock()
    payload = ChatRequest(message="plan a migration", role="architect")
    chat_role, _appliance, persona = await _validate_copilot_chat_request(payload, db)
    assert chat_role.value == "architect"
    assert persona.kind == "builtin"
    assert persona.baseRole == "architect"


@pytest.mark.asyncio
async def test_operator_without_appliance_raises_400():
    db = MagicMock()
    payload = ChatRequest(message="add a vip", personaId="operator")
    with pytest.raises(HTTPException) as exc:
        await _validate_copilot_chat_request(payload, db)
    assert exc.value.status_code == 400
