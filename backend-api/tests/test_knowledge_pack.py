import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.calibration_sync_service import sync_calibrations_from_studio
from app.services.knowledge_pack_runtime import resolve_knowledge_pack_turn_context
from app.services.knowledge_pack_service import (
    KNOWLEDGE_PACKS_DIR,
    get_active_pack_dir,
    get_installed_knowledge_pack_sync_state,
    install_knowledge_pack_bytes,
    rollback_knowledge_pack,
)
from app.services.knowledge_pack_verify import (
    KnowledgePackVerifyError,
    compute_content_hash,
    verify_knowledge_pack_bytes,
)
from tests.fixtures.knowpkg_builder import build_knowpkg_bytes


def test_compute_content_hash_stable():
    package_bytes, content_hash, _ = build_knowpkg_bytes()
    assert compute_content_hash(package_bytes) == content_hash


def test_verify_knowpkg_with_signature():
    package_bytes, content_hash, signature = build_knowpkg_bytes(sign=True)
    manifest = verify_knowledge_pack_bytes(
        package_bytes,
        package_signature=signature,
        expected_content_hash=content_hash,
    )
    assert manifest["id"] == "nexxus-global"
    assert manifest["version"] == "1.0.0"


def test_verify_knowpkg_without_signature_transition_mode():
    package_bytes, content_hash, _ = build_knowpkg_bytes(sign=False)
    manifest = verify_knowledge_pack_bytes(
        package_bytes,
        package_signature=None,
        expected_content_hash=content_hash,
    )
    assert manifest["type"] == "knowledge-pack"


def test_verify_rejects_bad_hash():
    package_bytes, _, signature = build_knowpkg_bytes(sign=True)
    with pytest.raises(KnowledgePackVerifyError):
        verify_knowledge_pack_bytes(
            package_bytes,
            package_signature=signature,
            expected_content_hash="sha256:deadbeef",
        )


@pytest.mark.asyncio
async def test_install_and_sync_state(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.knowledge_pack_service.KNOWLEDGE_PACKS_DIR", tmp_path / "knowledge-packs")
    package_bytes, content_hash, signature = build_knowpkg_bytes()

    collection = MagicMock()
    collection.find_one = AsyncMock(return_value={})
    collection.update_one = AsyncMock()
    db = MagicMock()
    db.__getitem__.return_value = collection

    result = await install_knowledge_pack_bytes(
        db,
        package_bytes,
        package_signature=signature,
        expected_content_hash=content_hash,
    )
    assert result["packId"] == "nexxus-global"
    assert get_active_pack_dir() is not None

    sync_state = get_installed_knowledge_pack_sync_state()
    assert sync_state["id"] == "nexxus-global"
    assert sync_state["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_rollback_requires_previous(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.knowledge_pack_service.KNOWLEDGE_PACKS_DIR", tmp_path / "knowledge-packs")
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value={})
    collection.update_one = AsyncMock()
    db = MagicMock()
    db.__getitem__.return_value = collection

    package_v1, hash_v1, sig_v1 = build_knowpkg_bytes(version="1.0.0")
    await install_knowledge_pack_bytes(db, package_v1, package_signature=sig_v1, expected_content_hash=hash_v1)

    package_v2, hash_v2, sig_v2 = build_knowpkg_bytes(version="2.0.0")
    collection.find_one = AsyncMock(
        return_value={
            "activePackId": "nexxus-global",
            "currentVersion": "1.0.0",
            "previousVersion": None,
            "pinnedVersion": None,
        }
    )
    await install_knowledge_pack_bytes(db, package_v2, package_signature=sig_v2, expected_content_hash=hash_v2)

    collection.find_one = AsyncMock(
        return_value={
            "activePackId": "nexxus-global",
            "currentVersion": "2.0.0",
            "previousVersion": "1.0.0",
            "pinnedVersion": None,
        }
    )
    rolled = await rollback_knowledge_pack(db)
    assert rolled["version"] == "1.0.0"


def test_runtime_assembly_from_local_pack(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.knowledge_pack_service.KNOWLEDGE_PACKS_DIR", tmp_path / "knowledge-packs")
    package_bytes, content_hash, signature = build_knowpkg_bytes()
    from app.services.knowledge_pack_service import _install_verified_pack_bytes
    from app.services.knowledge_pack_verify import verify_knowledge_pack_bytes

    manifest = verify_knowledge_pack_bytes(
        package_bytes,
        package_signature=signature,
        expected_content_hash=content_hash,
    )
    pack_root = _install_verified_pack_bytes(package_bytes, manifest)
    # Activate symlink for get_active_pack_dir
    from app.services.knowledge_pack_service import _current_link, _set_symlink

    _set_symlink(_current_link(manifest["id"]), pack_root)

    ctx, _policy = resolve_knowledge_pack_turn_context(
        user_message="configure lb for storefront",
        role="operator",
        vendor="netscaler",
    )
    assert ctx.injection_block
    assert "Operator persona from knowledge pack" in ctx.injection_block
    assert "nexxus-test-lb" in "".join(ctx.matched_skill_ids)


@pytest.mark.asyncio
async def test_sync_skips_knowledge_pack_when_hash_matches(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.knowledge_pack_service.KNOWLEDGE_PACKS_DIR", tmp_path / "knowledge-packs")
    monkeypatch.setattr("app.services.calibration_sync_service.CALIBRATIONS_DIR", tmp_path / "calibrations")

    package_bytes, content_hash, signature = build_knowpkg_bytes()
    db = AsyncMock()
    collection = AsyncMock()
    db.__getitem__ = lambda self, name: collection
    collection.update_one = AsyncMock()
    collection.find_one = AsyncMock(return_value={})
    await install_knowledge_pack_bytes(
        db,
        package_bytes,
        package_signature=signature,
        expected_content_hash=content_hash,
    )

    sync_payload = {
        "skills": [{"id": "legacy-skill", "version": "1.0.0", "bundleUrl": ""}],
        "removed": [],
        "knowledgePack": {
            "id": "nexxus-global",
            "version": "1.0.0",
            "contentHash": content_hash,
        },
        "stackProfile": {"knowledgePackVersion": "1.0.0"},
    }

    with patch(
        "app.services.calibration_sync_service.ensure_license_synced_for_studio",
        new=AsyncMock(),
    ), patch(
        "app.services.calibration_sync_service._studio_request_body",
        new=AsyncMock(return_value={"installedVersions": {}}),
    ), patch(
        "app.services.calibration_sync_service._post_studio_sync_manifest",
        new=AsyncMock(return_value=sync_payload),
    ), patch(
        "app.services.knowledge_pack_service.process_knowledge_pack_from_sync",
        new=AsyncMock(),
    ) as pack_sync:
        from app.services.knowledge_pack_service import KnowledgePackSyncOutcome

        pack_sync.return_value = KnowledgePackSyncOutcome(
            updated=False,
            skipped=True,
            pack_id="nexxus-global",
            version="1.0.0",
            content_hash=content_hash,
        )
        result = await sync_calibrations_from_studio(db)
        assert result.knowledge_pack_skipped is True
        assert result.knowledge_pack_updated is False


def test_list_installed_skills_unions_pack_and_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.knowledge_pack_service.KNOWLEDGE_PACKS_DIR", tmp_path / "knowledge-packs")
    monkeypatch.setattr("app.services.calibration_sync_service.CALIBRATIONS_DIR", tmp_path / "calibrations")

    from app.services.knowledge_pack_service import _install_verified_pack_bytes
    from app.services.knowledge_pack_verify import verify_knowledge_pack_bytes
    from app.services.calibration_sync_service import list_installed_skills

    package_bytes, content_hash, signature = build_knowpkg_bytes()
    manifest = verify_knowledge_pack_bytes(
        package_bytes,
        package_signature=signature,
        expected_content_hash=content_hash,
    )
    pack_root = _install_verified_pack_bytes(package_bytes, manifest)
    from app.services.knowledge_pack_service import _current_link, _set_symlink

    _set_symlink(_current_link(manifest["id"]), pack_root)

    legacy_root = tmp_path / "calibrations" / "legacy-skill" / "1.0.0"
    legacy_root.mkdir(parents=True)
    (legacy_root / "manifest.json").write_text(
        json.dumps({"id": "legacy-skill", "version": "1.0.0", "vendor": "netscaler"}),
        encoding="utf-8",
    )

    rows = list_installed_skills()
    ids = {row["skillId"] for row in rows}
    assert "nexxus-test-lb" in ids
    assert "legacy-skill" in ids

    legacy_only = list_installed_skills(include_legacy_only=True)
    assert all(row.get("source") == "legacy" for row in legacy_only)
