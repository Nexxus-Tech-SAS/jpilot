"""Verify Knowledge Pack (.knowpkg) archives: contentHash + optional Ed25519 signature."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

logger = logging.getLogger(__name__)

SIGNING_KEY_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "keys" / "nexxus_calibration_signing.pub"
)


class KnowledgePackVerifyError(Exception):
    pass


def compute_content_hash(package_bytes: bytes) -> str:
    digest = hashlib.sha256(package_bytes).hexdigest()
    return f"sha256:{digest}"


def normalize_content_hash(value: str | None) -> str:
    cleaned = (value or "").strip().lower()
    if cleaned.startswith("sha256:"):
        return cleaned
    if cleaned:
        return f"sha256:{cleaned}"
    return ""


def load_signing_public_key() -> Ed25519PublicKey:
    if not SIGNING_KEY_PATH.is_file():
        raise KnowledgePackVerifyError(f"Signing public key not found: {SIGNING_KEY_PATH}")
    raw_b64 = SIGNING_KEY_PATH.read_text(encoding="utf-8").strip()
    try:
        raw = base64.b64decode(raw_b64)
    except Exception as exc:
        raise KnowledgePackVerifyError("Invalid signing public key encoding.") from exc
    if len(raw) != 32:
        raise KnowledgePackVerifyError("Ed25519 public key must be 32 bytes.")
    return Ed25519PublicKey.from_public_bytes(raw)


def _decode_signature(signature_b64: str) -> bytes:
    cleaned = (signature_b64 or "").strip()
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            padded = cleaned + "=" * (-len(cleaned) % 4)
            return decoder(padded)
        except Exception:
            continue
    raise KnowledgePackVerifyError("Invalid packageSignature encoding.")


def verify_ed25519_signature(manifest_bytes: bytes, signature_b64: str) -> None:
    public_key = load_signing_public_key()
    signature = _decode_signature(signature_b64)
    try:
        public_key.verify(signature, manifest_bytes)
    except InvalidSignature as exc:
        raise KnowledgePackVerifyError("Ed25519 package signature verification failed.") from exc


def _find_manifest_entry(names: list[str]) -> str | None:
    candidates = [
        name
        for name in names
        if name.endswith("manifest.json") and ".." not in name and not name.endswith("/manifest.json/")
    ]
    for preferred in ("knowpkg/manifest.json", "manifest.json"):
        if preferred in candidates:
            return preferred
    return candidates[0] if candidates else None


def read_manifest_from_zip(package_bytes: bytes) -> tuple[dict[str, Any], bytes]:
    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        entry = _find_manifest_entry(archive.namelist())
        if not entry:
            raise KnowledgePackVerifyError("manifest.json not found in knowledge pack archive.")
        manifest_bytes = archive.read(entry)
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise KnowledgePackVerifyError("manifest.json is not valid JSON.") from exc
    if not isinstance(manifest, dict):
        raise KnowledgePackVerifyError("manifest.json must be a JSON object.")
    return manifest, manifest_bytes


def verify_knowledge_pack_bytes(
    package_bytes: bytes,
    *,
    package_signature: str | None = None,
    expected_content_hash: str | None = None,
) -> dict[str, Any]:
    if not package_bytes:
        raise KnowledgePackVerifyError("Knowledge pack archive is empty.")

    manifest, manifest_bytes = read_manifest_from_zip(package_bytes)
    if manifest.get("type") and manifest.get("type") != "knowledge-pack":
        raise KnowledgePackVerifyError("manifest type must be knowledge-pack.")

    computed_hash = compute_content_hash(package_bytes)
    manifest_hash = normalize_content_hash(str(manifest.get("contentHash") or ""))
    expected_hash = normalize_content_hash(expected_content_hash) if expected_content_hash else ""

    if expected_hash and computed_hash != expected_hash:
        raise KnowledgePackVerifyError(
            f"contentHash mismatch (expected {expected_hash}, got {computed_hash})."
        )
    if not expected_hash and manifest_hash and manifest_hash != computed_hash:
        raise KnowledgePackVerifyError(
            f"manifest contentHash mismatch (manifest {manifest_hash}, archive {computed_hash})."
        )

    signature = (package_signature or "").strip()
    if signature:
        verify_ed25519_signature(manifest_bytes, signature)
    else:
        logger.warning(
            "Knowledge pack installed without packageSignature (transition mode — hash-only verify)."
        )

    pack_id = str(manifest.get("id") or "").strip()
    version = str(manifest.get("version") or "").strip()
    if not pack_id or not version:
        raise KnowledgePackVerifyError("manifest must include id and version.")

    return manifest
