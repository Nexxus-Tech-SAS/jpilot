from __future__ import annotations

import io
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.services.license_service import (
    ensure_license_synced_for_studio,
    get_installation_fingerprint,
    get_license_context_for_studio,
    license_document_id,
    license_tier_rank,
    normalize_license_type,
)

CALIBRATIONS_DIR = Path("data/calibrations")
COLLECTION = "stack_calibrations"


class CalibrationSyncError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class CalibrationSyncResult:
    installed: int
    updated: int
    removed: int
    skills: list[dict[str, Any]]
    knowledge_pack: dict[str, Any] | None = None
    knowledge_pack_updated: bool = False
    knowledge_pack_skipped: bool = False
    stack_profile: dict[str, Any] | None = None
    legacy_skills: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class CalibrationCatalogResult:
    catalog_url: str
    license_type: str
    client_id: str | None
    entitlements: list[str]
    skills: list[dict[str, Any]]
    installed_blueprints: list[dict[str, Any]]
    local_license_type: str | None = None
    license_entitlement_mismatch: bool = False
    studio_auth_missing: bool = False
    has_license_code: bool = False
    app_fingerprint: str | None = None


def _calibrations_root() -> Path:
    return CALIBRATIONS_DIR


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", (value or "").strip())
    return cleaned or "unknown"


async def ensure_calibration_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index([("skillId", 1), ("version", 1)], unique=True)
    await db[COLLECTION].create_index([("enabled", 1)])


def _skill_row_from_manifest(
    manifest: dict[str, Any],
    *,
    skill_dir_name: str,
    version_fallback: str,
    path: str,
    source: str,
) -> dict[str, Any]:
    skill_id = str(manifest.get("id") or skill_dir_name)
    return {
        "skillId": skill_id,
        "version": str(manifest.get("version") or version_fallback or ""),
        "label": str(manifest.get("label") or skill_dir_name),
        "vendor": manifest.get("vendor"),
        "path": path,
        "source": source,
        "roles": list(manifest.get("roles") or []),
        "description": str(manifest.get("description") or ""),
        "domains": list(manifest.get("domains") or []),
    }


def list_installed_skills(*, include_legacy_only: bool = False) -> list[dict[str, Any]]:
    from app.services.knowledge_pack_service import get_active_pack_dir, list_pack_embedded_skills

    rows: list[dict[str, Any]] = []
    pack_dir = get_active_pack_dir()
    pack_skill_ids: set[str] = set()
    if pack_dir and not include_legacy_only:
        for row in list_pack_embedded_skills(pack_dir):
            skill_id = str(row.get("skillId") or "")
            if skill_id:
                pack_skill_ids.add(skill_id)
            rows.append(row)

    root = _calibrations_root()
    if not root.is_dir():
        return rows
    for skill_dir in sorted(root.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name == "knowledge-packs":
            continue
        for version_dir in sorted(skill_dir.iterdir()):
            manifest_file = version_dir / "manifest.json"
            skill_file = version_dir / "skill.json"
            manifest_path = manifest_file if manifest_file.is_file() else skill_file
            if not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            skill_id = str(manifest.get("id") or skill_dir.name)
            if skill_id in pack_skill_ids:
                continue
            rows.append(
                _skill_row_from_manifest(
                    manifest,
                    skill_dir_name=skill_dir.name,
                    version_fallback=version_dir.name,
                    path=str(version_dir),
                    source="legacy",
                )
            )
    return rows


def installed_versions_map() -> dict[str, str]:
    return {
        row["skillId"]: row["version"]
        for row in list_installed_skills()
        if row.get("skillId") and row.get("version")
    }


async def _studio_request_body(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    fingerprint = await get_installation_fingerprint(db)
    app_fingerprint = fingerprint.get("fingerprint") or license_document_id()
    license_context = await get_license_context_for_studio(db)
    body: dict[str, Any] = {
        "appFingerprint": app_fingerprint,
        "appName": settings.jpilot_app_name,
        "installedVersions": installed_versions_map(),
    }
    license_code = license_context.get("licenseCode")
    if license_code:
        body["licenseCode"] = license_code
    from app.services.knowledge_pack_service import get_installed_knowledge_pack_sync_state

    installed_pack = get_installed_knowledge_pack_sync_state()
    if installed_pack:
        body["installedKnowledgePack"] = installed_pack
    return body


def _sync_entitled_by_id(sync_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(skill.get("id") or ""): skill
        for skill in (sync_payload.get("skills") or [])
        if skill.get("id")
    }


def _merge_studio_identity(
    catalog_payload: dict[str, Any],
    sync_payload: dict[str, Any],
) -> tuple[str, str | None, list[str]]:
    license_type = normalize_license_type(str(catalog_payload.get("licenseType") or "free"))
    sync_license_type = normalize_license_type(str(sync_payload.get("licenseType") or ""))
    if sync_license_type and license_tier_rank(sync_license_type) > license_tier_rank(license_type):
        license_type = sync_license_type

    client_id = catalog_payload.get("clientId") or sync_payload.get("clientId")
    if client_id is not None:
        client_id = str(client_id).strip() or None

    entitlements = list(catalog_payload.get("entitlements") or [])
    if not entitlements:
        entitlements = list(sync_payload.get("entitlements") or [])
    return license_type, client_id, entitlements


def _enrich_catalog_skills_with_sync_entitlements(
    catalog_skills: list[dict[str, Any]],
    sync_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge entitled bundles from POST /calibrations/sync into catalog rows.

    scstudio catalog ``installable`` can be false while sync still returns entitled
    skills for this fingerprint — use sync as the download source of truth.
    """
    entitled = _sync_entitled_by_id(sync_payload)
    enriched: list[dict[str, Any]] = []
    for raw in catalog_skills:
        skill = dict(raw)
        skill_id = str(skill.get("id") or "")
        sync_skill = entitled.get(skill_id)
        if sync_skill:
            sync_version = str(sync_skill.get("version") or "")
            sync_bundle = str(sync_skill.get("bundleUrl") or "")
            skill["entitledViaSync"] = True
            skill["entitledVersion"] = sync_version or None
            if sync_bundle:
                skill["syncBundleUrl"] = sync_bundle
            skill["installable"] = True
            skill["ineligibleReason"] = None
        else:
            skill["entitledViaSync"] = False
        enriched.append(skill)
    return enriched


async def _post_studio_sync_manifest(body: dict[str, Any]) -> dict[str, Any]:
    base = settings.nexxus_calibration_base_url.rstrip("/")
    sync_url = f"{base}/calibrations/sync"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(sync_url, json=body)
        except httpx.RequestError as exc:
            raise CalibrationSyncError(f"Could not reach Calibration Studio: {exc}") from exc

    if response.status_code >= 400:
        raise CalibrationSyncError(
            f"Calibration sync failed ({response.status_code}): {(response.text or '')[:300]}",
            status_code=response.status_code,
        )

    return response.json() if response.content else {}


async def _fetch_studio_sync_manifest(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    body = await _studio_request_body(db)
    return await _post_studio_sync_manifest(body)


def _build_installed_blueprints(
    catalog_skills: list[dict[str, Any]],
    installed_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    catalog_by_id = {str(skill.get("id") or ""): skill for skill in catalog_skills if skill.get("id")}
    installed_by_id = {str(row.get("skillId") or ""): row for row in installed_rows if row.get("skillId")}
    blueprint_ids = sorted(set(catalog_by_id) | set(installed_by_id) - {""})

    rows: list[dict[str, Any]] = []
    for skill_id in blueprint_ids:
        catalog_skill = catalog_by_id.get(skill_id) or {}
        installed_row = installed_by_id.get(skill_id) or {}
        installed_version = installed_row.get("version")
        catalog_version = catalog_skill.get("version")
        rows.append(
            {
                "skillId": skill_id,
                "label": installed_row.get("label") or catalog_skill.get("label") or skill_id,
                "vendor": installed_row.get("vendor") or catalog_skill.get("vendor"),
                "installedVersion": installed_version,
                "catalogVersion": catalog_version,
                "installed": bool(installed_version),
                "updateAvailable": bool(
                    installed_version
                    and catalog_version
                    and installed_version != catalog_version
                ),
            }
        )
    return rows


async def fetch_calibration_catalog(
    db: AsyncIOMotorDatabase,
    *,
    vendor: str | None = None,
) -> CalibrationCatalogResult:
    if not settings.calibration_sync_enabled:
        raise CalibrationSyncError("Calibration sync is disabled on this installation.")

    await ensure_license_synced_for_studio(db)

    body = await _studio_request_body(db)
    if vendor:
        body["vendor"] = vendor.strip().lower()

    base = settings.nexxus_calibration_base_url.rstrip("/")
    catalog_url = f"{base}/calibrations/catalog"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(catalog_url, json=body)
        except httpx.RequestError as exc:
            raise CalibrationSyncError(f"Could not reach Calibration Studio: {exc}") from exc

    if response.status_code >= 400:
        raise CalibrationSyncError(
            f"Calibration catalog failed ({response.status_code}): {(response.text or '')[:300]}",
            status_code=response.status_code,
        )

    payload = response.json() if response.content else {}
    catalog_skills = payload.get("skills") or []
    try:
        sync_payload = await _fetch_studio_sync_manifest(db)
    except CalibrationSyncError:
        sync_payload = {}
    catalog_skills = _enrich_catalog_skills_with_sync_entitlements(catalog_skills, sync_payload)
    installed_rows = list_installed_skills()
    license_context = await get_license_context_for_studio(db)
    local_license_type = license_context.get("localLicenseType")
    studio_license_type, client_id, entitlements = _merge_studio_identity(payload, sync_payload)
    license_entitlement_mismatch = bool(
        local_license_type
        and license_tier_rank(local_license_type) > license_tier_rank(studio_license_type)
    )
    studio_auth_missing = bool(
        license_entitlement_mismatch and not license_context.get("hasLicenseCode")
    )
    fingerprint = await get_installation_fingerprint(db)

    return CalibrationCatalogResult(
        catalog_url=str(payload.get("catalogUrl") or catalog_url),
        license_type=studio_license_type,
        client_id=client_id,
        entitlements=entitlements,
        skills=catalog_skills,
        installed_blueprints=_build_installed_blueprints(catalog_skills, installed_rows),
        local_license_type=str(local_license_type) if local_license_type else None,
        license_entitlement_mismatch=license_entitlement_mismatch,
        studio_auth_missing=studio_auth_missing,
        has_license_code=bool(license_context.get("hasLicenseCode")),
        app_fingerprint=str(fingerprint.get("fingerprint") or license_document_id()).strip() or None,
    )


@dataclass(frozen=True)
class CalibrationInstallResult:
    skill_id: str
    version: str
    label: str
    vendor: str | None
    path: str
    updated: bool


@dataclass(frozen=True)
class CalibrationUninstallResult:
    skill_id: str
    label: str
    removed_versions: list[str]


def _resolve_bundle_url(base: str, bundle_url: str) -> str:
    cleaned = (bundle_url or "").strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    path = cleaned if cleaned.startswith("/") else f"/{cleaned}"
    return f"{base.rstrip('/')}{path}"


def _manifest_from_skill_dir(skill_dir: Path) -> dict[str, Any]:
    manifest_file = skill_dir / "manifest.json"
    skill_file = skill_dir / "skill.json"
    if manifest_file.is_file():
        try:
            return json.loads(manifest_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    if skill_file.is_file():
        try:
            manifest = json.loads(skill_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest
    return {}


def _extract_calpkg_bytes(skill_id: str, version: str, package_bytes: bytes) -> Path:
    target = _calibrations_root() / _safe_segment(skill_id) / _safe_segment(version)
    target.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            rel = Path(name)
            if ".." in rel.parts:
                continue
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.read(name))

    return target


async def _download_and_install_skill(
    db: AsyncIOMotorDatabase,
    *,
    base: str,
    skill_id: str,
    version: str,
    bundle_url: str,
    label: str | None = None,
    installed_versions: dict[str, str] | None = None,
) -> bool:
    fetch_url = _resolve_bundle_url(base, bundle_url)
    async with httpx.AsyncClient(timeout=60.0) as client:
        bundle_response = await client.get(fetch_url)
    if bundle_response.status_code >= 400:
        raise CalibrationSyncError(
            f"Could not download bundle for {skill_id} ({bundle_response.status_code}).",
            status_code=bundle_response.status_code,
        )

    content_type = (bundle_response.headers.get("content-type") or "").lower()
    if "json" in content_type:
        bundle = bundle_response.json()
        skill_dir = _write_skill_bundle(skill_id, version, bundle)
        manifest = bundle.get("manifest") or {}
    else:
        skill_dir = _extract_calpkg_bytes(skill_id, version, bundle_response.content)
        manifest = _manifest_from_skill_dir(skill_dir)

    await _upsert_calibration_index(
        db,
        skill_id=skill_id,
        version=version,
        vendor=manifest.get("vendor"),
        label=label or manifest.get("label"),
    )
    prior = (installed_versions or {}).get(skill_id)
    return prior == version


def _catalog_skill(catalog: CalibrationCatalogResult, skill_id: str) -> dict[str, Any] | None:
    for skill in catalog.skills:
        if str(skill.get("id") or "") == skill_id:
            return skill
    return None


async def install_calibration_skill(
    db: AsyncIOMotorDatabase,
    skill_id: str,
) -> CalibrationInstallResult:
    if not settings.calibration_sync_enabled:
        raise CalibrationSyncError("Calibration sync is disabled on this installation.")

    cleaned_id = (skill_id or "").strip()
    if not cleaned_id:
        raise CalibrationSyncError("skillId is required.", status_code=400)

    catalog = await fetch_calibration_catalog(db)
    skill = _catalog_skill(catalog, cleaned_id)
    if skill is None:
        raise CalibrationSyncError(
            f"Skill '{cleaned_id}' is not in the official blueprint catalog.",
            status_code=404,
        )
    if not skill.get("installable"):
        sync_payload = await _fetch_studio_sync_manifest(db)
        sync_skill = _sync_entitled_by_id(sync_payload).get(cleaned_id)
        if sync_skill is None:
            reason = str(skill.get("ineligibleReason") or "Not entitled under your current license.")
            raise CalibrationSyncError(reason, status_code=403)
        skill = {
            **skill,
            "installable": True,
            "entitledViaSync": True,
            "entitledVersion": str(sync_skill.get("version") or ""),
            "syncBundleUrl": str(sync_skill.get("bundleUrl") or ""),
            "ineligibleReason": None,
        }

    version = str(skill.get("entitledVersion") or skill.get("version") or "")
    bundle_url = str(skill.get("syncBundleUrl") or skill.get("bundleUrl") or "")
    if not version or not bundle_url:
        raise CalibrationSyncError(
            f"Skill '{cleaned_id}' has no downloadable bundle.",
            status_code=502,
        )

    base = settings.nexxus_calibration_base_url.rstrip("/")
    unchanged = await _download_and_install_skill(
        db,
        base=base,
        skill_id=cleaned_id,
        version=version,
        bundle_url=bundle_url,
        label=str(skill.get("label") or cleaned_id),
        installed_versions=installed_versions_map(),
    )
    skill_dir = _calibrations_root() / _safe_segment(cleaned_id) / _safe_segment(version)
    manifest = _manifest_from_skill_dir(skill_dir)
    return CalibrationInstallResult(
        skill_id=cleaned_id,
        version=version,
        label=str(skill.get("label") or manifest.get("label") or cleaned_id),
        vendor=manifest.get("vendor") or skill.get("vendor"),
        path=str(skill_dir),
        updated=not unchanged,
    )


async def uninstall_calibration_skill(
    db: AsyncIOMotorDatabase,
    skill_id: str,
    *,
    version: str | None = None,
) -> CalibrationUninstallResult:
    cleaned_id = (skill_id or "").strip()
    if not cleaned_id:
        raise CalibrationSyncError("skillId is required.", status_code=400)

    cleaned_version = (version or "").strip() or None
    installed = list_installed_skills()
    matching = [row for row in installed if str(row.get("skillId") or "") == cleaned_id]
    if not matching:
        raise CalibrationSyncError(
            f"Skill '{cleaned_id}' is not installed locally.",
            status_code=404,
        )

    if cleaned_version:
        matching = [row for row in matching if str(row.get("version") or "") == cleaned_version]
        if not matching:
            raise CalibrationSyncError(
                f"Skill '{cleaned_id}' version '{cleaned_version}' is not installed locally.",
                status_code=404,
            )

    removed_versions: list[str] = []
    label = str(matching[0].get("label") or cleaned_id)
    for row in matching:
        version_value = str(row.get("version") or "")
        skill_path = Path(row.get("path") or "")
        if skill_path.is_dir():
            shutil.rmtree(skill_path)
            parent = skill_path.parent
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        await db[COLLECTION].delete_one({"skillId": cleaned_id, "version": version_value})
        if version_value:
            removed_versions.append(version_value)

    return CalibrationUninstallResult(
        skill_id=cleaned_id,
        label=label,
        removed_versions=sorted(removed_versions),
    )


def _write_skill_bundle(skill_id: str, version: str, bundle: dict[str, Any]) -> Path:
    target = _calibrations_root() / _safe_segment(skill_id) / _safe_segment(version)
    target.mkdir(parents=True, exist_ok=True)

    manifest = bundle.get("manifest") or {}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    for rel_path, content in (bundle.get("files") or {}).items():
        file_path = target / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(str(content), encoding="utf-8")

    return target


async def _upsert_calibration_index(
    db: AsyncIOMotorDatabase,
    *,
    skill_id: str,
    version: str,
    vendor: str | None,
    label: str | None,
) -> None:
    now = datetime.now(timezone.utc)
    await db[COLLECTION].update_one(
        {"skillId": skill_id, "version": version},
        {
            "$set": {
                "skillId": skill_id,
                "version": version,
                "vendor": vendor,
                "label": label,
                "enabled": True,
                "path": str(_calibrations_root() / _safe_segment(skill_id) / _safe_segment(version)),
                "updatedAt": now,
            },
            "$setOnInsert": {"installedAt": now},
        },
        upsert=True,
    )


async def sync_calibrations_from_studio(db: AsyncIOMotorDatabase) -> CalibrationSyncResult:
    if not settings.calibration_sync_enabled:
        raise CalibrationSyncError("Calibration sync is disabled on this installation.")

    await ensure_license_synced_for_studio(db)

    body = await _studio_request_body(db)
    installed_versions = body["installedVersions"]

    base = settings.nexxus_calibration_base_url.rstrip("/")
    payload = await _post_studio_sync_manifest(body)
    skills = payload.get("skills") or []
    removed = payload.get("removed") or []
    stack_profile = payload.get("stackProfile") or None
    knowledge_pack_meta = payload.get("knowledgePack") or None

    knowledge_pack_updated = False
    knowledge_pack_skipped = False
    knowledge_pack_summary: dict[str, Any] | None = None

    if knowledge_pack_meta:
        from app.services.knowledge_pack_service import KnowledgePackError, process_knowledge_pack_from_sync

        try:
            pack_outcome = await process_knowledge_pack_from_sync(
                db,
                knowledge_pack=knowledge_pack_meta,
                base_url=base,
                stack_profile=stack_profile,
            )
            knowledge_pack_updated = pack_outcome.updated
            knowledge_pack_skipped = pack_outcome.skipped
            if pack_outcome.pack_id:
                knowledge_pack_summary = {
                    "id": pack_outcome.pack_id,
                    "version": pack_outcome.version,
                    "contentHash": pack_outcome.content_hash,
                }
        except KnowledgePackError as exc:
            raise CalibrationSyncError(str(exc), status_code=exc.status_code) from exc

    updated = 0
    installed = 0
    for skill in skills:
        skill_id = str(skill.get("id") or "")
        version = str(skill.get("version") or "")
        bundle_url = str(skill.get("bundleUrl") or "")
        if not skill_id or not version or not bundle_url:
            continue

        try:
            unchanged = await _download_and_install_skill(
                db,
                base=base,
                skill_id=skill_id,
                version=version,
                bundle_url=bundle_url,
                label=str(skill.get("label") or skill_id),
                installed_versions=installed_versions,
            )
        except CalibrationSyncError:
            continue

        if unchanged:
            installed += 1
        else:
            updated += 1

    legacy_skills = skills if not knowledge_pack_meta else skills

    return CalibrationSyncResult(
        installed=installed,
        updated=updated,
        removed=len(removed),
        skills=skills,
        knowledge_pack=knowledge_pack_summary or knowledge_pack_meta,
        knowledge_pack_updated=knowledge_pack_updated,
        knowledge_pack_skipped=knowledge_pack_skipped,
        stack_profile=stack_profile,
        legacy_skills=legacy_skills,
    )
