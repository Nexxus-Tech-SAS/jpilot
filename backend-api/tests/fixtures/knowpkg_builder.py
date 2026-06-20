"""Build minimal signed .knowpkg fixtures for tests."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Matches backend-api/app/resources/keys/nexxus_calibration_signing.pub
TEST_PRIVATE_KEY_B64 = "DEBRA8ccxypqok9e4cA+8rNyjfkFHc7rrMh0D/1zBgI="


def _sign_manifest(manifest_bytes: bytes, *, sign: bool = True) -> str:
    if not sign:
        return ""
    private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(TEST_PRIVATE_KEY_B64))
    signature = private_key.sign(manifest_bytes)
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel_path, content in files.items():
            archive.writestr(rel_path, content)
    return buffer.getvalue()


def build_knowpkg_bytes(
    *,
    pack_id: str = "nexxus-global",
    version: str = "1.0.0",
    sign: bool = True,
    include_blueprint: bool = True,
) -> tuple[bytes, str, str]:
    manifest = {
        "type": "knowledge-pack",
        "id": pack_id,
        "version": version,
        "publishedAt": "2026-06-19T12:00:00Z",
        "publisher": "nexxus",
        "contentHash": "",
        "personas": [
            {"id": "operator", "version": "1.0.0", "path": "personas/operator"},
        ],
    }

    static_files: dict[str, str] = {
        "knowpkg/catalog/vendors.json": json.dumps(
            {
                "vendors": [
                    {
                        "vendorId": "cloud-software-group",
                        "deviceId": "netscaler-adc",
                        "jpilotVendorId": "netscaler",
                    }
                ]
            },
            indent=2,
        ),
        "knowpkg/personas/operator/behavior.md": "Operator persona from knowledge pack.",
        "knowpkg/personas/operator/permissions.json": json.dumps(
            {"readOnly": False, "configurationChanges": True},
            indent=2,
        ),
        "knowpkg/indexes/assignment-index.json": json.dumps(
            {"assignmentIds": ["operator-netscaler-core"]},
            indent=2,
        ),
        "knowpkg/assignments/operator-netscaler-core.json": json.dumps(
            {
                "assignmentId": "operator-netscaler-core",
                "personaId": "operator",
                "priority": 100,
                "scope": {
                    "vendorId": "cloud-software-group",
                    "deviceId": "netscaler-adc",
                    "domainIds": ["lb"],
                    "skillIds": [],
                    "matchMode": "domain_or_explicit",
                },
                "resolvedBlueprintIds": ["nexxus-test-lb"],
            },
            indent=2,
        ),
    }

    if include_blueprint:
        static_files["knowpkg/blueprints/nexxus-test-lb/manifest.json"] = json.dumps(
            {
                "id": "nexxus-test-lb",
                "version": "0.1.0",
                "label": "Test LB",
                "vendor": "netscaler",
                "roles": ["operator"],
                "triggers": {"intents": ["lb", "load balancer"], "commands": []},
                "memoryModules": [],
            },
            indent=2,
        )
        static_files["knowpkg/blueprints/nexxus-test-lb/prompts/operator.md"] = "Follow the test LB playbook."

    encoded_static = {
        rel: content.encode("utf-8") if isinstance(content, str) else content
        for rel, content in static_files.items()
    }

    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
    package_bytes = _zip_bytes({"knowpkg/manifest.json": manifest_bytes, **encoded_static})
    content_hash = f"sha256:{hashlib.sha256(package_bytes).hexdigest()}"
    signature = _sign_manifest(manifest_bytes, sign=sign)
    return package_bytes, content_hash, signature


def write_knowpkg_fixture(path: Path, **kwargs) -> tuple[bytes, str, str]:
    package_bytes, content_hash, signature = build_knowpkg_bytes(**kwargs)
    path.write_bytes(package_bytes)
    return package_bytes, content_hash, signature
