from __future__ import annotations

import io
import json
import logging
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

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

logger = logging.getLogger(__name__)

CALIBRATIONS_DIR = Path("data/calibrations")
PERSONAS_DIR = Path("data/calibrations/personas")
COLLECTION = "stack_calibrations"
PERSONA_COLLECTION = "stack_personas"


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
    entitled_items: list[dict[str, Any]] | None = None
    personas_installed: int = 0


@dataclass(frozen=True)
class CalibrationCatalogResult:
    catalog_url: str
    license_type: str
    client_id: str | None
    entitlements: list[str]
    skills: list[dict[str, Any]]
    installed_blueprints: list[dict[str, Any]]
    items: list[dict[str, Any]] | None = None
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


SKILL_TYPE = "skill"
PERSONA_TYPE = "persona"
KNOWLEDGE_PACK_TYPE = "knowledge_pack"


def _normalize_type(value: Any) -> str:
    cleaned = str(value or "").strip().lower().replace("-", "_")
    return cleaned or SKILL_TYPE


def _catalog_item_globally_free(raw: dict[str, Any]) -> bool:
    """Contract uses ``globalFree``; legacy skills mirror used ``globalFreeSkill``."""
    return bool(raw.get("globalFree") or raw.get("globalFreeSkill"))


def _normalize_catalog_item(raw: dict[str, Any], *, default_type: str = SKILL_TYPE) -> dict[str, Any]:
    """Coerce a contract ``CatalogItem`` (or a legacy skill row) into the unified shape.

    Carries both contract field names and the legacy ``globalFreeSkill`` alias so the
    existing skills marketplace UI keeps working unchanged.
    """
    item = dict(raw)
    item["type"] = _normalize_type(raw.get("type") or default_type)
    item["id"] = str(raw.get("id") or "")
    item["version"] = str(raw.get("version") or "")
    global_free = _catalog_item_globally_free(raw)
    item["globalFree"] = global_free
    item["globalFreeSkill"] = global_free
    item["meta"] = dict(raw.get("meta") or {})
    item.setdefault("domains", list(raw.get("domains") or []))
    return item


def _sync_entitled_items(sync_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Prefer the contract ``entitledItems[]``; fall back to the legacy ``skills[]``.

    Legacy ``skills[]`` entries are untyped — treat each as a ``skill``.
    """
    raw_items = sync_payload.get("entitledItems")
    if raw_items:
        return [
            {**item, "type": _normalize_type(item.get("type"))}
            for item in raw_items
            if item.get("id")
        ]
    return [
        {**skill, "type": SKILL_TYPE}
        for skill in (sync_payload.get("skills") or [])
        if skill.get("id")
    ]


def _sync_entitled_by_key(sync_payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Key entitled sync items by ``(type, id)`` so a persona and a skill sharing an id don't collide."""
    return {
        (_normalize_type(item.get("type")), str(item.get("id") or "")): item
        for item in _sync_entitled_items(sync_payload)
        if item.get("id")
    }


def _sync_entitled_by_id(sync_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Skills-only view keyed by id (back-compat for the skill install path)."""
    return {
        key[1]: item
        for key, item in _sync_entitled_by_key(sync_payload).items()
        if key[0] == SKILL_TYPE
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
    items for this fingerprint — use sync as the download source of truth. Items are
    matched by ``(type, id)`` so a persona and a skill sharing an id don't collide;
    untyped rows (legacy catalog + legacy sync ``skills[]``) default to ``skill`` on
    both sides, preserving the original behavior.
    """
    entitled = _sync_entitled_by_key(sync_payload)
    enriched: list[dict[str, Any]] = []
    for raw in catalog_skills:
        item = dict(raw)
        item_type = _normalize_type(item.get("type"))
        item_id = str(item.get("id") or "")
        sync_item = entitled.get((item_type, item_id))
        if sync_item:
            sync_version = str(sync_item.get("version") or "")
            sync_bundle = str(sync_item.get("bundleUrl") or "")
            item["entitledViaSync"] = True
            item["entitledVersion"] = sync_version or None
            if sync_bundle:
                item["syncBundleUrl"] = sync_bundle
            item["installable"] = True
            item["ineligibleReason"] = None
        else:
            item["entitledViaSync"] = False
        enriched.append(item)
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


def _unified_catalog_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the unified catalog item list (all three types).

    Prefer the contract ``items[]`` (skills + personas + knowledge packs). If an older
    scstudio returns only the legacy ``skills[]`` (no ``items[]``), fall back to it and
    tag each entry as a ``skill`` so the rest of the pipeline is type-uniform.
    """
    raw_items = payload.get("items")
    if raw_items:
        return [_normalize_catalog_item(raw) for raw in raw_items if raw.get("id")]
    return [
        _normalize_catalog_item(raw, default_type=SKILL_TYPE)
        for raw in (payload.get("skills") or [])
        if raw.get("id")
    ]


def _skills_only(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if _normalize_type(item.get("type")) == SKILL_TYPE]


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
    # Prefer the contract items[] (all three types); fall back to legacy skills[].
    catalog_items = _unified_catalog_items(payload)
    try:
        sync_payload = await _fetch_studio_sync_manifest(db)
    except CalibrationSyncError:
        sync_payload = {}
    # Enrichment + gating apply uniformly across all types, keyed by (type, id).
    catalog_items = _enrich_catalog_skills_with_sync_entitlements(catalog_items, sync_payload)
    _mark_installed_non_skill_items(catalog_items)
    catalog_skills = _skills_only(catalog_items)
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
        items=catalog_items,
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
    base = base.rstrip("/")
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        # Bundles are always served by the configured Calibration host. Rebase the
        # absolute URL's path onto `base` so downloads use the same reachable host
        # as catalog/sync — the public hostname scstudio embeds may not be routable
        # from this backend (e.g. inside Docker the public domain isn't reachable,
        # only the internal service name is).
        split = urlsplit(cleaned)
        path = split.path or "/"
        if split.query:
            path = f"{path}?{split.query}"
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}"
    path = cleaned if cleaned.startswith("/") else f"/{cleaned}"
    return f"{base}{path}"


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
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            bundle_response = await client.get(fetch_url)
    except httpx.RequestError as exc:
        logger.exception("Bundle download failed for %s from %s", skill_id, fetch_url)
        raise CalibrationSyncError(
            f"Could not reach the bundle host for {skill_id} at {fetch_url}: {exc}",
            status_code=502,
        ) from exc
    if bundle_response.status_code >= 400:
        raise CalibrationSyncError(
            f"Could not download bundle for {skill_id} ({bundle_response.status_code}).",
            status_code=bundle_response.status_code,
        )

    content_type = (bundle_response.headers.get("content-type") or "").lower()
    try:
        if "json" in content_type:
            bundle = bundle_response.json()
            skill_dir = _write_skill_bundle(skill_id, version, bundle)
            manifest = bundle.get("manifest") or {}
        else:
            skill_dir = _extract_calpkg_bytes(skill_id, version, bundle_response.content)
            manifest = _manifest_from_skill_dir(skill_dir)
    except (json.JSONDecodeError, zipfile.BadZipFile, ValueError) as exc:
        logger.exception("Bundle for %s from %s is not a valid package", skill_id, fetch_url)
        raise CalibrationSyncError(
            f"Bundle for {skill_id} from {fetch_url} is not a valid package: {exc}",
            status_code=502,
        ) from exc
    except OSError as exc:
        logger.exception("Could not write bundle for %s to disk", skill_id)
        raise CalibrationSyncError(
            f"Could not write the bundle for {skill_id} to disk: {exc}",
            status_code=500,
        ) from exc

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


def _personas_root() -> Path:
    return PERSONAS_DIR


def list_installed_personas() -> dict[str, str]:
    """Map personaId -> installed version (latest on disk) for personas under PERSONAS_DIR."""
    root = _personas_root()
    installed: dict[str, str] = {}
    if not root.is_dir():
        return installed
    for persona_dir in sorted(root.iterdir()):
        if not persona_dir.is_dir():
            continue
        versions = [
            v.name
            for v in persona_dir.iterdir()
            if v.is_dir() and (v / "manifest.json").is_file()
        ]
        if versions:
            installed[persona_dir.name] = max(versions)
    return installed


def _mark_installed_non_skill_items(items: list[dict[str, Any]]) -> None:
    """Set install state on persona/knowledge_pack catalog items (skills use installedBlueprints)."""
    from app.services.knowledge_pack_service import get_installed_knowledge_pack_sync_state

    installed_personas = list_installed_personas()
    installed_pack = get_installed_knowledge_pack_sync_state() or {}
    for item in items:
        item_type = _normalize_type(item.get("type"))
        if item_type == PERSONA_TYPE:
            installed_version = installed_personas.get(str(item.get("id") or ""))
        elif item_type == KNOWLEDGE_PACK_TYPE:
            installed_version = (
                str(installed_pack.get("version") or "")
                if str(installed_pack.get("id") or "") == str(item.get("id") or "")
                else None
            )
        else:
            continue
        catalog_version = str(item.get("version") or "")
        item["installed"] = bool(installed_version)
        item["installedVersion"] = installed_version or None
        item["updateAvailable"] = bool(
            installed_version and catalog_version and installed_version != catalog_version
        )


def _catalog_item(
    catalog: CalibrationCatalogResult,
    item_id: str,
    *,
    item_type: str = SKILL_TYPE,
) -> dict[str, Any] | None:
    wanted_type = _normalize_type(item_type)
    for item in catalog.items or []:
        if str(item.get("id") or "") == item_id and _normalize_type(item.get("type")) == wanted_type:
            return item
    return None


def _extract_persona_skill_refs(item: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Collect referenced skills from the catalog ``meta.skillRefs`` and/or the persona manifest."""
    refs: list[dict[str, str]] = []
    seen: set[str] = set()
    sources = [
        (item.get("meta") or {}).get("skillRefs") or [],
        manifest.get("skillRefs") or [],
    ]
    for source in sources:
        for ref in source:
            if not isinstance(ref, dict):
                continue
            ref_id = str(ref.get("id") or "").strip()
            if not ref_id or ref_id in seen:
                continue
            seen.add(ref_id)
            refs.append({"id": ref_id, "version": str(ref.get("version") or "").strip()})
    return refs


@dataclass(frozen=True)
class CalibrationPersonaInstallResult:
    persona_id: str
    version: str
    label: str
    vendor: str | None
    path: str
    updated: bool
    installed_skill_refs: list[str]
    skipped_skill_refs: list[str]


async def _upsert_persona_index(
    db: AsyncIOMotorDatabase,
    *,
    persona_id: str,
    version: str,
    vendor: str | None,
    label: str | None,
    skill_refs: list[dict[str, str]],
    path: str,
    base_role: str | None = None,
    behavior: dict[str, Any] | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    set_fields: dict[str, Any] = {
        "personaId": persona_id,
        "version": version,
        "vendor": vendor,
        "label": label,
        "skillRefs": skill_refs,
        "enabled": True,
        "path": path,
        "updatedAt": now,
    }
    if base_role is not None:
        set_fields["baseRole"] = base_role
    if behavior is not None:
        set_fields["behavior"] = behavior
    await db[PERSONA_COLLECTION].update_one(
        {"personaId": persona_id, "version": version},
        {
            "$set": set_fields,
            "$setOnInsert": {"installedAt": now},
        },
        upsert=True,
    )


async def install_calibration_persona(
    db: AsyncIOMotorDatabase,
    persona_id: str,
) -> CalibrationPersonaInstallResult:
    """Install a persona bundle: register its manifest, then ensure entitled skillRefs are present.

    A persona bundle is a ``.calpkg``-style zip (manifest.json + prompts/ + roles/).
    Installing registers the manifest and downloads each referenced skill that is entitled,
    reusing the skill install path. Un-entitled skill refs are skipped (not fatal).
    """
    if not settings.calibration_sync_enabled:
        raise CalibrationSyncError("Calibration sync is disabled on this installation.")

    cleaned_id = (persona_id or "").strip()
    if not cleaned_id:
        raise CalibrationSyncError("personaId is required.", status_code=400)

    catalog = await fetch_calibration_catalog(db)
    item = _catalog_item(catalog, cleaned_id, item_type=PERSONA_TYPE)
    if item is None:
        raise CalibrationSyncError(
            f"Persona '{cleaned_id}' is not in the official blueprint catalog.",
            status_code=404,
        )
    if not item.get("installable"):
        sync_item = _sync_entitled_by_key(
            await _fetch_studio_sync_manifest(db)
        ).get((PERSONA_TYPE, cleaned_id))
        if sync_item is None:
            reason = str(item.get("ineligibleReason") or "Not entitled under your current license.")
            raise CalibrationSyncError(reason, status_code=403)
        item = {
            **item,
            "installable": True,
            "entitledViaSync": True,
            "entitledVersion": str(sync_item.get("version") or ""),
            "syncBundleUrl": str(sync_item.get("bundleUrl") or ""),
            "ineligibleReason": None,
        }

    version = str(item.get("entitledVersion") or item.get("version") or "")
    bundle_url = str(item.get("syncBundleUrl") or item.get("bundleUrl") or "")
    if not version or not bundle_url:
        raise CalibrationSyncError(
            f"Persona '{cleaned_id}' has no downloadable bundle.",
            status_code=502,
        )

    base = settings.nexxus_calibration_base_url.rstrip("/")
    target = _personas_root() / _safe_segment(cleaned_id) / _safe_segment(version)
    already_present = target.is_dir() and (target / "manifest.json").is_file()

    fetch_url = _resolve_bundle_url(base, bundle_url)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            bundle_response = await client.get(fetch_url)
    except httpx.RequestError as exc:
        logger.exception("Persona bundle download failed for %s from %s", cleaned_id, fetch_url)
        raise CalibrationSyncError(
            f"Could not reach the bundle host for persona {cleaned_id} at {fetch_url}: {exc}",
            status_code=502,
        ) from exc
    if bundle_response.status_code >= 400:
        raise CalibrationSyncError(
            f"Could not download bundle for persona {cleaned_id} ({bundle_response.status_code}).",
            status_code=bundle_response.status_code,
        )

    try:
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(bundle_response.content)) as archive:
            for name in archive.namelist():
                if name.endswith("/"):
                    continue
                rel = Path(name)
                if ".." in rel.parts:
                    continue
                dest = target / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(name))
    except (zipfile.BadZipFile, ValueError) as exc:
        logger.exception("Persona bundle for %s is not a valid package", cleaned_id)
        raise CalibrationSyncError(
            f"Bundle for persona {cleaned_id} from {fetch_url} is not a valid package: {exc}",
            status_code=502,
        ) from exc
    except OSError as exc:
        logger.exception("Could not write persona bundle for %s to disk", cleaned_id)
        raise CalibrationSyncError(
            f"Could not write the persona bundle for {cleaned_id} to disk: {exc}",
            status_code=500,
        ) from exc

    manifest = _manifest_from_skill_dir(target)
    skill_refs = _extract_persona_skill_refs(item, manifest)

    installed_refs: list[str] = []
    skipped_refs: list[str] = []
    installed_versions = installed_versions_map()
    for ref in skill_refs:
        ref_id = ref["id"]
        if ref_id in installed_versions and (
            not ref["version"] or installed_versions[ref_id] == ref["version"]
        ):
            installed_refs.append(ref_id)
            continue
        try:
            await install_calibration_skill(db, ref_id)
            installed_refs.append(ref_id)
        except CalibrationSyncError:
            # A referenced skill the user is not entitled to is skipped, not fatal.
            logger.info("Persona %s skill ref %s not installed (not entitled).", cleaned_id, ref_id)
            skipped_refs.append(ref_id)

    # Extract baseRole and behavior from the persona manifest (frozen contract fields).
    base_role: str | None = manifest.get("baseRole") or None
    behavior_raw = manifest.get("behavior")
    behavior: dict[str, Any] | None = None
    if isinstance(behavior_raw, dict):
        behavior = {
            "systemPrompt": str(behavior_raw.get("systemPrompt") or ""),
            "objectives": list(behavior_raw.get("objectives") or []),
            "expertiseLevel": behavior_raw.get("expertiseLevel"),
            "reasoningStyle": behavior_raw.get("reasoningStyle"),
            "communicationStyle": behavior_raw.get("communicationStyle"),
        }

    await _upsert_persona_index(
        db,
        persona_id=cleaned_id,
        version=version,
        vendor=manifest.get("vendor") or item.get("vendor"),
        label=str(item.get("label") or manifest.get("label") or cleaned_id),
        skill_refs=skill_refs,
        path=str(target),
        base_role=base_role,
        behavior=behavior,
    )

    return CalibrationPersonaInstallResult(
        persona_id=cleaned_id,
        version=version,
        label=str(item.get("label") or manifest.get("label") or cleaned_id),
        vendor=manifest.get("vendor") or item.get("vendor"),
        path=str(target),
        updated=not already_present,
        installed_skill_refs=installed_refs,
        skipped_skill_refs=skipped_refs,
    )


async def install_calibration_knowledge_pack(
    db: AsyncIOMotorDatabase,
    pack_id: str,
) -> dict[str, Any]:
    """Install a knowledge_pack catalog item by routing through the existing pack install path."""
    from app.services.knowledge_pack_service import (
        KnowledgePackError,
        process_knowledge_pack_from_sync,
    )

    cleaned_id = (pack_id or "").strip()
    if not cleaned_id:
        raise CalibrationSyncError("packId is required.", status_code=400)

    catalog = await fetch_calibration_catalog(db)
    item = _catalog_item(catalog, cleaned_id, item_type=KNOWLEDGE_PACK_TYPE)
    if item is None:
        raise CalibrationSyncError(
            f"Knowledge pack '{cleaned_id}' is not in the official blueprint catalog.",
            status_code=404,
        )
    if not item.get("installable"):
        reason = str(item.get("ineligibleReason") or "Not entitled under your current license.")
        raise CalibrationSyncError(reason, status_code=403)

    version = str(item.get("entitledVersion") or item.get("version") or "")
    bundle_url = str(item.get("syncBundleUrl") or item.get("bundleUrl") or "")
    content_hash = str((item.get("meta") or {}).get("contentHash") or "")
    base = settings.nexxus_calibration_base_url.rstrip("/")
    try:
        outcome = await process_knowledge_pack_from_sync(
            db,
            knowledge_pack={
                "id": cleaned_id,
                "version": version,
                "contentHash": content_hash,
                "bundleUrl": bundle_url,
            },
            base_url=base,
        )
    except KnowledgePackError as exc:
        raise CalibrationSyncError(str(exc), status_code=exc.status_code) from exc

    return {
        "packId": outcome.pack_id or cleaned_id,
        "version": outcome.version or version,
        "updated": outcome.updated,
        "skipped": outcome.skipped,
    }


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


async def uninstall_calibration_persona(
    db: AsyncIOMotorDatabase,
    persona_id: str,
    *,
    version: str | None = None,
) -> CalibrationUninstallResult:
    cleaned_id = (persona_id or "").strip()
    if not cleaned_id:
        raise CalibrationSyncError("personaId is required.", status_code=400)
    cleaned_version = (version or "").strip() or None

    persona_dir = _personas_root() / _safe_segment(cleaned_id)
    version_dirs = []
    if persona_dir.is_dir():
        version_dirs = [
            d for d in persona_dir.iterdir()
            if d.is_dir() and (d / "manifest.json").is_file()
        ]
    if cleaned_version:
        version_dirs = [d for d in version_dirs if d.name == cleaned_version]

    index_query: dict[str, Any] = {"personaId": cleaned_id}
    if cleaned_version:
        index_query["version"] = cleaned_version
    index_doc = await db[PERSONA_COLLECTION].find_one(index_query)

    if not version_dirs and not index_doc:
        detail = (
            f"Persona '{cleaned_id}' version '{cleaned_version}' is not installed locally."
            if cleaned_version
            else f"Persona '{cleaned_id}' is not installed locally."
        )
        raise CalibrationSyncError(detail, status_code=404)

    label = str((index_doc or {}).get("label") or cleaned_id)
    removed_versions: list[str] = []
    for d in version_dirs:
        shutil.rmtree(d)
        removed_versions.append(d.name)
    if persona_dir.is_dir() and not any(persona_dir.iterdir()):
        persona_dir.rmdir()

    await db[PERSONA_COLLECTION].delete_many(index_query)

    return CalibrationUninstallResult(
        skill_id=cleaned_id,
        label=label,
        removed_versions=sorted(removed_versions),
    )


async def uninstall_calibration_knowledge_pack(
    db: AsyncIOMotorDatabase,
    pack_id: str,
) -> CalibrationUninstallResult:
    from app.services.knowledge_pack_service import remove_installed_pack

    cleaned_id = (pack_id or "").strip()
    if not cleaned_id:
        raise CalibrationSyncError("packId is required.", status_code=400)

    removed_version = remove_installed_pack(cleaned_id)
    if removed_version is None:
        raise CalibrationSyncError(
            f"Knowledge pack '{cleaned_id}' is not installed locally.",
            status_code=404,
        )
    return CalibrationUninstallResult(
        skill_id=cleaned_id,
        label=cleaned_id,
        removed_versions=[removed_version] if removed_version else [],
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

    # Prefer the contract entitledItems[] (typed: skill | persona | knowledge_pack);
    # fall back to the legacy skills[] (untyped → skill) for back-compat.
    entitled_items = _sync_entitled_items(payload)
    skill_items = [item for item in entitled_items if _normalize_type(item.get("type")) == SKILL_TYPE]
    persona_items = [item for item in entitled_items if _normalize_type(item.get("type")) == PERSONA_TYPE]
    pack_items = [
        item for item in entitled_items if _normalize_type(item.get("type")) == KNOWLEDGE_PACK_TYPE
    ]

    updated = 0
    installed = 0
    for skill in skill_items:
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

    personas_installed = 0
    for persona in persona_items:
        persona_id = str(persona.get("id") or "")
        if not persona_id:
            continue
        try:
            await install_calibration_persona(db, persona_id)
            personas_installed += 1
        except CalibrationSyncError:
            logger.info("Persona %s skipped during bulk sync (not entitled or no bundle).", persona_id)
            continue

    # Knowledge packs listed in entitledItems[] route through the existing pack install path.
    for pack in pack_items:
        pack_id = str(pack.get("id") or "")
        bundle_url = str(pack.get("bundleUrl") or "")
        if not pack_id or not bundle_url:
            continue
        from app.services.knowledge_pack_service import (
            KnowledgePackError,
            process_knowledge_pack_from_sync,
        )

        try:
            pack_outcome = await process_knowledge_pack_from_sync(
                db,
                knowledge_pack={
                    "id": pack_id,
                    "version": str(pack.get("version") or ""),
                    "packageSignature": str(pack.get("packageSignature") or ""),
                    "bundleUrl": bundle_url,
                },
                base_url=base,
            )
            if pack_outcome.updated:
                knowledge_pack_updated = True
            if pack_outcome.pack_id and not knowledge_pack_summary:
                knowledge_pack_summary = {
                    "id": pack_outcome.pack_id,
                    "version": pack_outcome.version,
                    "contentHash": pack_outcome.content_hash,
                }
        except KnowledgePackError:
            logger.info("Knowledge pack %s skipped during bulk sync.", pack_id)
            continue

    legacy_skills = skills

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
        entitled_items=entitled_items,
        personas_installed=personas_installed,
    )
