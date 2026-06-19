import io
import json
import zipfile
from unittest.mock import AsyncMock, patch

import pytest

from app.services.calibration_memory_service import search_stack_calibration_memory
from app.services.calibration_sync_service import (
    CalibrationCatalogResult,
    CalibrationSyncError,
    _build_installed_blueprints,
    _enrich_catalog_skills_with_sync_entitlements,
    _extract_calpkg_bytes,
    fetch_calibration_catalog,
    install_calibration_skill,
    installed_versions_map,
)


def test_enrich_catalog_skills_with_sync_entitlements():
    catalog = [
        {
            "id": "nexxus-netscaler-adc-security-ip-reputation-configuration",
            "version": "0.1.1",
            "installable": False,
            "ineligibleReason": "Requires enterprise_pro license (current: free)",
            "bundleUrl": "",
        }
    ]
    sync_payload = {
        "skills": [
            {
                "id": "nexxus-netscaler-adc-security-ip-reputation-configuration",
                "version": "0.1.0",
                "bundleUrl": "https://studio.example/bundles/ip-reputation/0.1.0",
            }
        ]
    }

    enriched = _enrich_catalog_skills_with_sync_entitlements(catalog, sync_payload)

    assert enriched[0]["installable"] is True
    assert enriched[0]["entitledVersion"] == "0.1.0"
    assert enriched[0]["entitledViaSync"] is True
    assert enriched[0]["version"] == "0.1.1"
    assert enriched[0]["ineligibleReason"] is None


def test_installed_versions_map_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.calibration_sync_service.CALIBRATIONS_DIR", tmp_path)
    assert installed_versions_map() == {}


def test_build_installed_blueprints_marks_update_available():
    catalog = [{"id": "skill-a", "version": "2.0.0", "label": "Skill A", "vendor": "netscaler"}]
    installed = [
        {
            "skillId": "skill-a",
            "version": "1.0.0",
            "label": "Skill A",
            "vendor": "netscaler",
            "path": "/tmp/skill-a/1.0.0",
        }
    ]
    rows = _build_installed_blueprints(catalog, installed)
    assert len(rows) == 1
    assert rows[0]["installed"] is True
    assert rows[0]["updateAvailable"] is True
    assert rows[0]["installedVersion"] == "1.0.0"
    assert rows[0]["catalogVersion"] == "2.0.0"


@pytest.mark.asyncio
async def test_studio_request_body_includes_license_code():
    with patch(
        "app.services.calibration_sync_service.get_installation_fingerprint",
        new=AsyncMock(return_value={"fingerprint": "fp-abc"}),
    ), patch(
        "app.services.calibration_sync_service.get_license_context_for_studio",
        new=AsyncMock(
            return_value={
                "localLicenseType": "enterprise_pro",
                "licenseCode": "ABCD-1234-EFGH-5678",
                "hasLicenseCode": True,
                "status": "active",
            }
        ),
    ), patch(
        "app.services.calibration_sync_service.installed_versions_map",
        return_value={"skill-a": "1.0.0"},
    ):
        from app.services.calibration_sync_service import _studio_request_body

        body = await _studio_request_body(object())

    assert body["appFingerprint"] == "fp-abc"
    assert body["licenseCode"] == "ABCD-1234-EFGH-5678"
    assert body["installedVersions"] == {"skill-a": "1.0.0"}


@pytest.mark.asyncio
async def test_fetch_calibration_catalog_flags_license_mismatch():
    catalog_payload = {
        "catalogUrl": "https://studio.example/calibrations/catalog",
        "licenseType": "free",
        "skills": [],
    }

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = json.dumps(catalog_payload).encode("utf-8")
    mock_response.json.return_value = catalog_payload

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch(
        "app.services.calibration_sync_service._studio_request_body",
        new=AsyncMock(return_value={"appFingerprint": "abc", "appName": "JPilot", "installedVersions": {}}),
    ), patch(
        "app.services.calibration_sync_service._fetch_studio_sync_manifest",
        new=AsyncMock(return_value={"skills": []}),
    ), patch(
        "app.services.calibration_sync_service.get_license_context_for_studio",
        new=AsyncMock(
            return_value={
                "localLicenseType": "enterprise_pro",
                "licenseCode": None,
                "hasLicenseCode": False,
                "status": "active",
            }
        ),
    ), patch(
        "app.services.calibration_sync_service.list_installed_skills",
        return_value=[],
    ), patch(
        "app.services.calibration_sync_service.settings.calibration_sync_enabled",
        True,
    ), patch(
        "app.services.calibration_sync_service.settings.nexxus_calibration_base_url",
        "https://studio.example",
    ), patch(
        "app.services.calibration_sync_service.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await fetch_calibration_catalog(object())

    assert result.local_license_type == "enterprise_pro"
    assert result.license_entitlement_mismatch is True
    assert result.studio_auth_missing is True


@pytest.mark.asyncio
async def test_fetch_calibration_catalog_syncs_license_first():
    catalog_payload = {"catalogUrl": "https://studio.example/calibrations/catalog", "licenseType": "free", "skills": []}
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = json.dumps(catalog_payload).encode("utf-8")
    mock_response.json.return_value = catalog_payload
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch(
        "app.services.calibration_sync_service.ensure_license_synced_for_studio",
        new=AsyncMock(),
    ) as sync_mock, patch(
        "app.services.calibration_sync_service._studio_request_body",
        new=AsyncMock(return_value={"appFingerprint": "abc", "appName": "JPilot", "installedVersions": {}}),
    ), patch(
        "app.services.calibration_sync_service.get_license_context_for_studio",
        new=AsyncMock(
            return_value={
                "localLicenseType": None,
                "licenseCode": None,
                "hasLicenseCode": False,
                "status": None,
            }
        ),
    ), patch(
        "app.services.calibration_sync_service.list_installed_skills",
        return_value=[],
    ), patch(
        "app.services.calibration_sync_service.settings.calibration_sync_enabled",
        True,
    ), patch(
        "app.services.calibration_sync_service.settings.nexxus_calibration_base_url",
        "https://studio.example",
    ), patch(
        "app.services.calibration_sync_service.httpx.AsyncClient",
        return_value=mock_client,
    ):
        await fetch_calibration_catalog(object())

    sync_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_calibration_catalog_enriches_installed_blueprints():
    catalog_payload = {
        "catalogUrl": "https://studio.example/calibrations/catalog",
        "licenseType": "free",
        "clientId": None,
        "entitlements": [],
        "skills": [
            {
                "id": "nexxus-free-skill",
                "version": "1.0.0",
                "label": "Free skill",
                "vendor": "netscaler",
                "domains": ["discovery"],
                "minTier": "free",
                "globalFreeSkill": True,
                "installable": True,
                "ineligibleReason": None,
                "bundleUrl": "https://studio.example/bundle",
            }
        ],
    }

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = json.dumps(catalog_payload).encode("utf-8")
    mock_response.json.return_value = catalog_payload

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch(
        "app.services.calibration_sync_service._studio_request_body",
        new=AsyncMock(return_value={"appFingerprint": "abc", "appName": "JPilot", "installedVersions": {}}),
    ), patch(
        "app.services.calibration_sync_service._fetch_studio_sync_manifest",
        new=AsyncMock(return_value={"skills": []}),
    ), patch(
        "app.services.calibration_sync_service.get_license_context_for_studio",
        new=AsyncMock(
            return_value={
                "localLicenseType": None,
                "licenseCode": None,
                "hasLicenseCode": False,
                "status": None,
            }
        ),
    ), patch(
        "app.services.calibration_sync_service.list_installed_skills",
        return_value=[],
    ), patch(
        "app.services.calibration_sync_service.settings.calibration_sync_enabled",
        True,
    ), patch(
        "app.services.calibration_sync_service.settings.nexxus_calibration_base_url",
        "https://studio.example",
    ), patch(
        "app.services.calibration_sync_service.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await fetch_calibration_catalog(object())

    assert result.license_type == "free"
    assert len(result.skills) == 1
    assert result.installed_blueprints == [
        {
            "skillId": "nexxus-free-skill",
            "label": "Free skill",
            "vendor": "netscaler",
            "installedVersion": None,
            "catalogVersion": "1.0.0",
            "installed": False,
            "updateAvailable": False,
        }
    ]


def test_search_stack_calibration_memory_finds_installed_skill(tmp_path, monkeypatch):
    skill_dir = tmp_path / "nexxus-netscaler-ha" / "1.0.0"
    (skill_dir / "memory").mkdir(parents=True)
    (skill_dir / "memory" / "ha-steps.md").write_text(
        "Perform graceful failover before firmware upgrade on HA pairs.",
        encoding="utf-8",
    )
    (skill_dir / "manifest.json").write_text(
        json.dumps(
            {
                "id": "nexxus-netscaler-ha",
                "label": "HA upgrade",
                "vendor": "netscaler",
                "roles": ["architect"],
                "memoryModules": [{"id": "ha-steps", "filename": "memory/ha-steps.md"}],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "app.services.calibration_memory_service.list_installed_skills",
        lambda: [
            {
                "skillId": "nexxus-netscaler-ha",
                "version": "1.0.0",
                "label": "HA upgrade",
                "vendor": "netscaler",
                "path": str(skill_dir),
            }
        ],
    )

    result = search_stack_calibration_memory(
        "firmware upgrade HA",
        vendor="netscaler",
        role="architect",
    )
    assert result["matchCount"] == 1
    assert "failover" in result["matches"][0]["excerpt"]


def test_extract_calpkg_bytes_writes_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.calibration_sync_service.CALIBRATIONS_DIR", tmp_path)
    manifest = {"id": "skill-a", "version": "1.0.0", "vendor": "netscaler", "label": "Skill A"}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("memory/playbook.md", "HA failover steps")

    target = _extract_calpkg_bytes("skill-a", "1.0.0", buffer.getvalue())
    assert (target / "manifest.json").is_file()
    assert (target / "memory" / "playbook.md").is_file()


@pytest.mark.asyncio
async def test_install_calibration_skill_rejects_not_entitled():
    catalog = CalibrationCatalogResult(
        catalog_url="https://studio.example/catalog",
        license_type="free",
        client_id=None,
        entitlements=[],
        skills=[
            {
                "id": "enterprise-only",
                "version": "1.0.0",
                "label": "Enterprise skill",
                "vendor": "netscaler",
                "installable": False,
                "ineligibleReason": "Requires enterprise license (current: free)",
                "bundleUrl": "",
            }
        ],
        installed_blueprints=[],
    )

    with patch(
        "app.services.calibration_sync_service.fetch_calibration_catalog",
        new=AsyncMock(return_value=catalog),
    ), patch(
        "app.services.calibration_sync_service.settings.calibration_sync_enabled",
        True,
    ):
        with pytest.raises(CalibrationSyncError) as exc:
            await install_calibration_skill(object(), "enterprise-only")

    assert exc.value.status_code == 403
    assert "enterprise license" in str(exc.value)


@pytest.mark.asyncio
async def test_install_calibration_skill_rejects_enterprise_pro():
    catalog = CalibrationCatalogResult(
        catalog_url="https://studio.example/catalog",
        license_type="free",
        client_id=None,
        entitlements=[],
        skills=[
            {
                "id": "nexxus-netscaler-adc-load-balancing-storefront-load-balancing",
                "version": "0.1.4",
                "label": "Citrix Storefront Load Balancing",
                "vendor": "netscaler",
                "minTier": "enterprise_pro",
                "globalFreeSkill": False,
                "installable": False,
                "ineligibleReason": "Requires enterprise_pro license (current: free)",
                "bundleUrl": "",
            }
        ],
        installed_blueprints=[],
    )

    with patch(
        "app.services.calibration_sync_service.fetch_calibration_catalog",
        new=AsyncMock(return_value=catalog),
    ), patch(
        "app.services.calibration_sync_service.settings.calibration_sync_enabled",
        True,
    ):
        with pytest.raises(CalibrationSyncError) as exc:
            await install_calibration_skill(object(), "nexxus-netscaler-adc-load-balancing-storefront-load-balancing")

    assert exc.value.status_code == 403
    assert "enterprise_pro" in str(exc.value)


def test_uninstall_calibration_skill_removes_files_and_index(tmp_path, monkeypatch):
    skill_dir = tmp_path / "nexxus-test-skill" / "0.1.0"
    skill_dir.mkdir(parents=True)
    (skill_dir / "manifest.json").write_text(
        '{"id": "nexxus-test-skill", "version": "0.1.0", "label": "Test skill"}',
        encoding="utf-8",
    )

    monkeypatch.setattr("app.services.calibration_sync_service.CALIBRATIONS_DIR", tmp_path)

    class FakeCollection:
        def __init__(self):
            self.deleted = []

        async def delete_one(self, query):
            self.deleted.append(query)
            return None

    fake_db = {"stack_calibrations": FakeCollection()}

    async def _run():
        from app.services.calibration_sync_service import uninstall_calibration_skill

        return await uninstall_calibration_skill(fake_db, "nexxus-test-skill", version="0.1.0")

    import asyncio

    result = asyncio.run(_run())

    assert result.removed_versions == ["0.1.0"]
    assert not skill_dir.exists()
    assert fake_db["stack_calibrations"].deleted == [{"skillId": "nexxus-test-skill", "version": "0.1.0"}]
