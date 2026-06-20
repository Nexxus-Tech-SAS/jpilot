"""Knowledge Pack (.knowpkg) local cache, sync, import, rollback, and pin."""

from __future__ import annotations

import io
import json
import logging
import os
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
from app.services.knowledge_pack_verify import (
    KnowledgePackVerifyError,
    compute_content_hash,
    normalize_content_hash,
    verify_knowledge_pack_bytes,
)

logger = logging.getLogger(__name__)

KNOWLEDGE_PACKS_DIR = Path("data/calibrations/knowledge-packs")
STATE_COLLECTION = "knowledge_pack_state"
STATE_ID = "default"
DEFAULT_SYNC_SCHEDULE_HOURS = 6


class KnowledgePackError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class KnowledgePackSyncOutcome:
    updated: bool
    skipped: bool
    pack_id: str | None = None
    version: str | None = None
    content_hash: str | None = None


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", (value or "").strip())
    return cleaned or "unknown"


def _packs_root() -> Path:
    return KNOWLEDGE_PACKS_DIR


def _pack_dir(pack_id: str) -> Path:
    return _packs_root() / _safe_segment(pack_id)


def _version_dir(pack_id: str, version: str) -> Path:
    return _pack_dir(pack_id) / _safe_segment(version)


def _current_link(pack_id: str) -> Path:
    return _pack_dir(pack_id) / "current"


def _previous_link(pack_id: str) -> Path:
    return _pack_dir(pack_id) / "previous"


def _resolve_symlink(link: Path) -> Path | None:
    if not link.exists() and not link.is_symlink():
        return None
    try:
        target = link.resolve()
    except OSError:
        return None
    return target if target.is_dir() else None


def _set_symlink(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        link.unlink()
    os.symlink(target.name, link)


def _extract_zip_to_dir(package_bytes: bytes, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            rel = Path(name)
            if ".." in rel.parts:
                continue
            parts = list(rel.parts)
            if parts and parts[0] == "knowpkg":
                rel = Path(*parts[1:]) if len(parts) > 1 else Path()
            if not str(rel):
                continue
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.read(name))


def _read_root_manifest(pack_root: Path) -> dict[str, Any]:
    manifest_path = pack_root / "manifest.json"
    if not manifest_path.is_file():
        raise KnowledgePackError("Active knowledge pack is missing manifest.json.")
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise KnowledgePackError("Could not read knowledge pack manifest.") from exc


def _count_blueprints(pack_root: Path) -> int:
    blueprints_dir = pack_root / "blueprints"
    if not blueprints_dir.is_dir():
        return 0
    return sum(1 for child in blueprints_dir.iterdir() if child.is_dir())


async def ensure_knowledge_pack_indexes(db: AsyncIOMotorDatabase) -> None:
    """No-op: knowledge_pack_state uses a fixed ``_id`` doc; MongoDB already indexes _id."""
    return


async def _get_state_doc(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    doc = await db[STATE_COLLECTION].find_one({"_id": STATE_ID})
    return doc or {}


async def get_knowledge_pack_state(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    doc = await _get_state_doc(db)
    pack_id = str(doc.get("activePackId") or "")
    current_version = str(doc.get("currentVersion") or "")
    pack_root = get_active_pack_dir(pack_id or None)
    manifest: dict[str, Any] = {}
    blueprint_count = 0
    if pack_root:
        try:
            manifest = _read_root_manifest(pack_root)
            blueprint_count = _count_blueprints(pack_root)
        except KnowledgePackError:
            pack_root = None

    last_sync = doc.get("lastSyncAt")
    if isinstance(last_sync, datetime):
        last_sync = last_sync.isoformat()

    return {
        "active": bool(pack_root),
        "packId": pack_id or manifest.get("id"),
        "version": current_version or manifest.get("version"),
        "previousVersion": doc.get("previousVersion"),
        "pinnedVersion": doc.get("pinnedVersion"),
        "contentHash": doc.get("contentHash") or manifest.get("contentHash"),
        "publishedAt": doc.get("publishedAt") or manifest.get("publishedAt"),
        "blueprintCount": blueprint_count,
        "lastSyncAt": last_sync,
        "syncScheduleHours": int(doc.get("syncScheduleHours") or DEFAULT_SYNC_SCHEDULE_HOURS),
        "syncScheduleEnabled": bool(doc.get("syncScheduleEnabled", True)),
        "path": str(pack_root) if pack_root else "",
    }


def get_installed_knowledge_pack_sync_state() -> dict[str, str] | None:
    """Build installedKnowledgePack payload for POST /calibrations/sync."""
    if not settings.knowledge_pack_enabled:
        return None
    root = _packs_root()
    if not root.is_dir():
        return None
    for pack_parent in sorted(root.iterdir()):
        if not pack_parent.is_dir():
            continue
        current = _resolve_symlink(_current_link(pack_parent.name))
        if not current:
            continue
        try:
            manifest = _read_root_manifest(current)
        except KnowledgePackError:
            continue
        pack_id = str(manifest.get("id") or pack_parent.name)
        version = str(manifest.get("version") or current.name)
        content_hash = normalize_content_hash(str(manifest.get("contentHash") or ""))
        sidecar = current / ".content-hash"
        if not content_hash and sidecar.is_file():
            content_hash = normalize_content_hash(sidecar.read_text(encoding="utf-8").strip())
        if not content_hash:
            continue
        return {"id": pack_id, "version": version, "contentHash": content_hash}
    return None


def get_active_pack_dir(pack_id: str | None = None) -> Path | None:
    if not settings.knowledge_pack_enabled:
        return None
    root = _packs_root()
    if not root.is_dir():
        return None
    if pack_id:
        return _resolve_symlink(_current_link(pack_id))
    for pack_parent in sorted(root.iterdir()):
        if not pack_parent.is_dir():
            continue
        current = _resolve_symlink(_current_link(pack_parent.name))
        if current:
            return current
    return None


def list_pack_embedded_skills(pack_dir: Path | None = None) -> list[dict[str, Any]]:
    pack_root = pack_dir or get_active_pack_dir()
    if not pack_root:
        return []

    rows: list[dict[str, Any]] = []
    blueprints_dir = pack_root / "blueprints"
    if not blueprints_dir.is_dir():
        return rows

    for skill_dir in sorted(blueprints_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        manifest_file = skill_dir / "manifest.json"
        skill_file = skill_dir / "skill.json"
        manifest_path = manifest_file if manifest_file.is_file() else skill_file
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        rows.append(
            {
                "skillId": manifest.get("id") or skill_dir.name,
                "version": manifest.get("version") or "",
                "label": manifest.get("label") or skill_dir.name,
                "vendor": manifest.get("vendor"),
                "path": str(skill_dir),
                "source": "knowledge-pack",
                "roles": list(manifest.get("roles") or []),
                "description": str(manifest.get("description") or ""),
                "domains": list(manifest.get("domains") or []),
            }
        )
    return rows


async def _persist_state(
    db: AsyncIOMotorDatabase,
    *,
    pack_id: str,
    version: str,
    content_hash: str,
    published_at: str | None,
    blueprint_count: int,
    previous_version: str | None,
) -> None:
    now = datetime.now(timezone.utc)
    await db[STATE_COLLECTION].update_one(
        {"_id": STATE_ID},
        {
            "$set": {
                "activePackId": pack_id,
                "currentVersion": version,
                "previousVersion": previous_version,
                "contentHash": content_hash,
                "publishedAt": published_at,
                "blueprintCount": blueprint_count,
                "lastSyncAt": now,
                "updatedAt": now,
            },
            "$setOnInsert": {
                "syncScheduleHours": DEFAULT_SYNC_SCHEDULE_HOURS,
                "syncScheduleEnabled": True,
                "pinnedVersion": None,
            },
        },
        upsert=True,
    )


def _install_verified_pack_bytes(
    package_bytes: bytes,
    manifest: dict[str, Any],
) -> Path:
    pack_id = str(manifest["id"])
    version = str(manifest["version"])
    pack_parent = _pack_dir(pack_id)
    pack_parent.mkdir(parents=True, exist_ok=True)

    staging = pack_parent / f"{_safe_segment(version)}.staging"
    final_dir = _version_dir(pack_id, version)
    previous_target = _resolve_symlink(_current_link(pack_id))
    previous_version = previous_target.name if previous_target else None

    _extract_zip_to_dir(package_bytes, staging)
    if final_dir.exists():
        shutil.rmtree(final_dir)
    staging.rename(final_dir)

    if previous_target and previous_target.is_dir() and previous_target != final_dir:
        _set_symlink(_previous_link(pack_id), previous_target)
    _set_symlink(_current_link(pack_id), final_dir)

    return final_dir


async def install_knowledge_pack_bytes(
    db: AsyncIOMotorDatabase,
    package_bytes: bytes,
    *,
    package_signature: str | None = None,
    expected_content_hash: str | None = None,
) -> dict[str, Any]:
    try:
        manifest = verify_knowledge_pack_bytes(
            package_bytes,
            package_signature=package_signature,
            expected_content_hash=expected_content_hash,
        )
    except KnowledgePackVerifyError as exc:
        raise KnowledgePackError(str(exc), status_code=400) from exc

    pinned_doc = await _get_state_doc(db)
    pinned = pinned_doc.get("pinnedVersion")
    version = str(manifest["version"])
    if pinned and str(pinned) != version:
        raise KnowledgePackError(
            f"Install blocked: version {version} does not match pinned version {pinned}.",
            status_code=409,
        )

    pack_root = _install_verified_pack_bytes(package_bytes, manifest)
    content_hash = normalize_content_hash(str(manifest.get("contentHash") or "")) or compute_content_hash(
        package_bytes
    )
    (pack_root / ".content-hash").write_text(content_hash, encoding="utf-8")
    previous_version = (await _get_state_doc(db)).get("currentVersion")
    if previous_version == version:
        previous_version = (await _get_state_doc(db)).get("previousVersion")

    await _persist_state(
        db,
        pack_id=str(manifest["id"]),
        version=version,
        content_hash=content_hash,
        published_at=str(manifest.get("publishedAt") or "") or None,
        blueprint_count=_count_blueprints(pack_root),
        previous_version=str(previous_version) if previous_version else None,
    )
    return {
        "packId": manifest["id"],
        "version": version,
        "contentHash": content_hash,
        "blueprintCount": _count_blueprints(pack_root),
        "path": str(pack_root),
    }


def _resolve_bundle_url(base: str, bundle_url: str) -> str:
    cleaned = (bundle_url or "").strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    path = cleaned if cleaned.startswith("/") else f"/{cleaned}"
    return f"{base.rstrip('/')}{path}"


async def process_knowledge_pack_from_sync(
    db: AsyncIOMotorDatabase,
    *,
    knowledge_pack: dict[str, Any],
    base_url: str,
    stack_profile: dict[str, Any] | None = None,
) -> KnowledgePackSyncOutcome:
    if not settings.knowledge_pack_enabled:
        return KnowledgePackSyncOutcome(updated=False, skipped=True)
    pack_id = str(knowledge_pack.get("id") or "")
    version = str(knowledge_pack.get("version") or "")
    remote_hash = normalize_content_hash(str(knowledge_pack.get("contentHash") or ""))
    bundle_url = str(knowledge_pack.get("bundleUrl") or "").strip()
    package_signature = str(knowledge_pack.get("packageSignature") or "").strip() or None

    if not pack_id or not version:
        return KnowledgePackSyncOutcome(updated=False, skipped=True)

    local_state = get_installed_knowledge_pack_sync_state()
    if remote_hash and local_state and local_state.get("contentHash") == remote_hash:
        if stack_profile:
            await _apply_stack_profile_pin(db, stack_profile)
        return KnowledgePackSyncOutcome(
            updated=False,
            skipped=True,
            pack_id=pack_id,
            version=version,
            content_hash=remote_hash,
        )

    if not bundle_url:
        if stack_profile:
            await _apply_stack_profile_pin(db, stack_profile)
        return KnowledgePackSyncOutcome(
            updated=False,
            skipped=True,
            pack_id=pack_id,
            version=version,
            content_hash=remote_hash or None,
        )

    pinned_version = (await _get_state_doc(db)).get("pinnedVersion")
    target_version = str(pinned_version or version)
    if pinned_version and pinned_version != version:
        local_version_dir = _version_dir(pack_id, str(pinned_version))
        if local_version_dir.is_dir():
            _set_symlink(_current_link(pack_id), local_version_dir)
            return KnowledgePackSyncOutcome(
                updated=False,
                skipped=True,
                pack_id=pack_id,
                version=str(pinned_version),
                content_hash=remote_hash or None,
            )

    fetch_url = _resolve_bundle_url(base_url, bundle_url)
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.get(fetch_url)
        except httpx.RequestError as exc:
            raise KnowledgePackError(f"Could not download knowledge pack: {exc}") from exc
    if response.status_code >= 400:
        raise KnowledgePackError(
            f"Knowledge pack download failed ({response.status_code}).",
            status_code=response.status_code,
        )

    try:
        result = await install_knowledge_pack_bytes(
            db,
            response.content,
            package_signature=package_signature,
            expected_content_hash=remote_hash or None,
        )
    except KnowledgePackError:
        raise
    except Exception as exc:
        raise KnowledgePackError(f"Knowledge pack install failed: {exc}") from exc

    if stack_profile:
        await _apply_stack_profile_pin(db, stack_profile)

    return KnowledgePackSyncOutcome(
        updated=True,
        skipped=False,
        pack_id=result["packId"],
        version=result["version"],
        content_hash=result.get("contentHash"),
    )


async def _apply_stack_profile_pin(db: AsyncIOMotorDatabase, stack_profile: dict[str, Any]) -> None:
    pinned = str(stack_profile.get("knowledgePackVersion") or "").strip()
    if not pinned:
        return
    doc = await _get_state_doc(db)
    pack_id = str(doc.get("activePackId") or "")
    if not pack_id:
        return
    version_dir = _version_dir(pack_id, pinned)
    if version_dir.is_dir():
        _set_symlink(_current_link(pack_id), version_dir)
        await db[STATE_COLLECTION].update_one(
            {"_id": STATE_ID},
            {"$set": {"pinnedVersion": pinned, "currentVersion": pinned}},
        )


async def rollback_knowledge_pack(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    doc = await _get_state_doc(db)
    pack_id = str(doc.get("activePackId") or "")
    if not pack_id:
        raise KnowledgePackError("No knowledge pack is installed.", status_code=404)

    previous = _resolve_symlink(_previous_link(pack_id))
    if not previous:
        previous_version = str(doc.get("previousVersion") or "")
        if previous_version:
            candidate = _version_dir(pack_id, previous_version)
            if candidate.is_dir():
                previous = candidate
    if not previous:
        raise KnowledgePackError("No previous knowledge pack version available.", status_code=404)

    current = _resolve_symlink(_current_link(pack_id))
    current_version = current.name if current else doc.get("currentVersion")
    _set_symlink(_current_link(pack_id), previous)
    if current and current.is_dir():
        _set_symlink(_previous_link(pack_id), current)

    manifest = _read_root_manifest(previous)
    await db[STATE_COLLECTION].update_one(
        {"_id": STATE_ID},
        {
            "$set": {
                "currentVersion": previous.name,
                "previousVersion": current_version,
                "contentHash": manifest.get("contentHash"),
                "blueprintCount": _count_blueprints(previous),
                "updatedAt": datetime.now(timezone.utc),
            }
        },
    )
    return {
        "packId": pack_id,
        "version": previous.name,
        "previousVersion": current_version,
        "blueprintCount": _count_blueprints(previous),
    }


async def pin_knowledge_pack_version(db: AsyncIOMotorDatabase, version: str | None) -> dict[str, Any]:
    doc = await _get_state_doc(db)
    pack_id = str(doc.get("activePackId") or "")
    if not pack_id:
        raise KnowledgePackError("No knowledge pack is installed.", status_code=404)

    cleaned = (version or "").strip() or None
    if cleaned:
        version_dir = _version_dir(pack_id, cleaned)
        if not version_dir.is_dir():
            raise KnowledgePackError(f"Version '{cleaned}' is not available locally.", status_code=404)
        _set_symlink(_current_link(pack_id), version_dir)

    await db[STATE_COLLECTION].update_one(
        {"_id": STATE_ID},
        {
            "$set": {
                "pinnedVersion": cleaned,
                "currentVersion": cleaned or doc.get("currentVersion"),
                "updatedAt": datetime.now(timezone.utc),
            }
        },
    )
    active = get_active_pack_dir(pack_id)
    return {
        "packId": pack_id,
        "pinnedVersion": cleaned,
        "currentVersion": active.name if active else doc.get("currentVersion"),
    }


async def update_knowledge_pack_schedule(
    db: AsyncIOMotorDatabase,
    *,
    enabled: bool | None = None,
    hours: int | None = None,
) -> dict[str, Any]:
    updates: dict[str, Any] = {"updatedAt": datetime.now(timezone.utc)}
    if enabled is not None:
        updates["syncScheduleEnabled"] = enabled
    if hours is not None:
        updates["syncScheduleHours"] = max(1, int(hours))
    await db[STATE_COLLECTION].update_one({"_id": STATE_ID}, {"$set": updates}, upsert=True)
    return await get_knowledge_pack_state(db)
