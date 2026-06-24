"""Tests for chat persona install state (disk is source of truth)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.copilot_roles import (  # noqa: E402
    builtin_personas,
    list_all_personas,
    list_installed_personas,
    resolve_custom_persona,
    resolve_persona,
)


def _write_persona_bundle(root: Path, persona_id: str, version: str, *, label: str, base_role: str) -> None:
    bundle = root / persona_id / version
    bundle.mkdir(parents=True, exist_ok=True)
    manifest = {
        "personaId": persona_id,
        "version": version,
        "label": label,
        "baseRole": base_role,
        "behavior": {"systemPrompt": f"Prompt for {label}"},
    }
    (bundle / "manifest.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")


@pytest.fixture
def personas_root(tmp_path, monkeypatch):
    root = tmp_path / "personas"
    root.mkdir()
    monkeypatch.setattr("app.services.calibration_sync_service.PERSONAS_DIR", root)
    return root


@pytest.mark.asyncio
async def test_list_installed_personas_uses_disk_and_prunes_orphans(personas_root):
    _write_persona_bundle(
        personas_root,
        "architect-security-architect",
        "1.0.0",
        label="Security Architect",
        base_role="architect",
    )

    orphan_doc = {
        "personaId": "ghost-persona",
        "version": "1.0.0",
        "enabled": True,
        "label": "Ghost",
        "baseRole": "operator",
        "behavior": {},
    }
    live_doc = {
        "personaId": "architect-security-architect",
        "version": "1.0.0",
        "enabled": True,
        "label": "Security Architect",
        "baseRole": "architect",
        "behavior": {"systemPrompt": "Secure things"},
    }

    async def fake_find(query):
        if query.get("personaId") == "architect-security-architect":
            return live_doc
        return None

    collection = MagicMock()
    collection.find = MagicMock(return_value=AsyncIter([orphan_doc, live_doc]))
    collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=1))
    collection.find_one = AsyncMock(side_effect=fake_find)

    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)

    personas = await list_installed_personas(db)

    assert [item["id"] for item in personas] == ["architect-security-architect"]
    assert personas[0]["label"] == "Security Architect"
    collection.delete_many.assert_any_call({"personaId": "ghost-persona"})


@pytest.mark.asyncio
async def test_resolve_custom_persona_requires_disk_bundle(personas_root):
    _write_persona_bundle(
        personas_root,
        "architect-security-architect",
        "1.0.0",
        label="Security Architect",
        base_role="architect",
    )

    collection = MagicMock()
    collection.find_one = AsyncMock(
        return_value={
            "personaId": "architect-security-architect",
            "version": "1.0.0",
            "enabled": True,
            "label": "Security Architect",
            "baseRole": "architect",
            "behavior": {"systemPrompt": "Secure things", "objectives": ["Harden"]},
        }
    )
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)

    resolved = await resolve_custom_persona(db, "architect-security-architect")
    assert resolved is not None
    assert resolved.label == "Security Architect"

    missing = await resolve_custom_persona(db, "not-on-disk")
    assert missing is None


def test_builtin_personas_have_capability_and_kind():
    personas = builtin_personas()
    assert [p["id"] for p in personas] == ["architect", "operator", "analyst"]
    for p in personas:
        assert p["kind"] == "builtin"
        assert p["isCustomPersona"] is False
        assert p["baseRole"] == p["id"]
        assert p["capability"]
    caps = {p["id"]: p["capability"] for p in personas}
    assert caps == {
        "architect": "Plan-only",
        "operator": "Full control",
        "analyst": "Read-only",
    }


@pytest.mark.asyncio
async def test_resolve_persona_builtin_ids():
    db = MagicMock()  # built-in path never touches the db
    for role_id, capability in (
        ("architect", "Plan-only"),
        ("operator", "Full control"),
        ("analyst", "Read-only"),
    ):
        persona = await resolve_persona(db, role_id)
        assert persona.kind == "builtin"
        assert persona.baseRole == role_id
        assert persona.systemPrompt == ""
        assert persona.capability == capability


@pytest.mark.asyncio
async def test_resolve_persona_empty_defaults_to_operator():
    db = MagicMock()
    for value in (None, "", "   "):
        persona = await resolve_persona(db, value)
        assert persona.kind == "builtin"
        assert persona.baseRole == "operator"
        assert persona.capability == "Full control"


@pytest.mark.asyncio
async def test_resolve_persona_empty_uses_legacy_role_fallback():
    # Legacy client: role set, personaId absent → resolve to the matching built-in.
    db = MagicMock()
    persona = await resolve_persona(db, None, fallback_role="architect")
    assert persona.kind == "builtin"
    assert persona.baseRole == "architect"
    assert persona.capability == "Plan-only"


@pytest.mark.asyncio
async def test_resolve_persona_installed_custom(personas_root):
    _write_persona_bundle(
        personas_root,
        "security-architect",
        "1.0.0",
        label="Security Architect",
        base_role="architect",
    )
    collection = MagicMock()
    collection.find_one = AsyncMock(
        return_value={
            "personaId": "security-architect",
            "version": "1.0.0",
            "enabled": True,
            "label": "Security Architect",
            "baseRole": "architect",
            "behavior": {"systemPrompt": "Harden it"},
        }
    )
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)

    persona = await resolve_persona(db, "security-architect")
    assert persona.kind == "custom"
    assert persona.baseRole == "architect"
    assert persona.capability == "Plan-only"
    assert persona.systemPrompt == "Harden it"


@pytest.mark.asyncio
async def test_resolve_persona_orphan_falls_back_to_builtin(personas_root):
    # No bundle on disk for this id → resolve_custom_persona returns None → fallback.
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value=None)
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)

    persona = await resolve_persona(db, "ghost-persona", fallback_role="analyst")
    assert persona.kind == "builtin"
    assert persona.baseRole == "analyst"
    assert persona.capability == "Read-only"

    # No fallback role → defaults to operator.
    persona2 = await resolve_persona(db, "ghost-persona")
    assert persona2.baseRole == "operator"


@pytest.mark.asyncio
async def test_list_all_personas_includes_builtins_and_customs(personas_root):
    _write_persona_bundle(
        personas_root,
        "security-architect",
        "1.0.0",
        label="Security Architect",
        base_role="architect",
    )
    live_doc = {
        "personaId": "security-architect",
        "version": "1.0.0",
        "enabled": True,
        "label": "Security Architect",
        "baseRole": "architect",
        "behavior": {"systemPrompt": "Secure"},
    }

    collection = MagicMock()
    collection.find = MagicMock(return_value=AsyncIter([live_doc]))
    collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=0))
    collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=0))
    collection.find_one = AsyncMock(return_value=live_doc)
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)

    personas = await list_all_personas(db)
    ids = [p["id"] for p in personas]
    # Built-ins first (catalog order), then the custom persona.
    assert ids[:3] == ["architect", "operator", "analyst"]
    assert "security-architect" in ids

    builtins = {p["id"]: p for p in personas if p["kind"] == "builtin"}
    assert builtins["operator"]["capability"] == "Full control"
    assert builtins["operator"]["baseRole"] == "operator"

    custom = next(p for p in personas if p["id"] == "security-architect")
    assert custom["kind"] == "custom"
    assert custom["capability"] == "Plan-only"


class AsyncIter:
    def __init__(self, items):
        self._items = list(items)

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item
