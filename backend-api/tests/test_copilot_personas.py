"""Tests for chat persona install state (disk is source of truth)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.copilot_roles import list_installed_personas, resolve_custom_persona  # noqa: E402


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
