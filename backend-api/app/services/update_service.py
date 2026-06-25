from __future__ import annotations

import datetime as dt
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.schemas.system import (
    TriggerUpdateResponse,
    UpdateCheckResponse,
    UpdateInstructions,
    UpdateStatusResponse,
    VersionResponse,
)

_VERSION_RE = re.compile(r"^\s*v?(?P<version>\d+(?:\.\d+)*)\s*$", re.IGNORECASE)
_DEFAULT_REPO = "Nexxus-Tech-SAS/jpilot"
_CACHE_TTL = dt.timedelta(hours=1)
# Even a forced ("Check for updates" button) check reuses the cached result if the
# last real check was this recent — stops the button from exhausting GitHub's
# unauthenticated 60-requests/hour rate limit (which returns HTTP 403).
_FORCE_MIN_INTERVAL = dt.timedelta(minutes=2)

_version_paths = (
    Path("/usr/share/jpilot/VERSION"),
    Path(__file__).resolve().parents[3] / "VERSION",
)

_cache: dict[str, Any] = {"checked_at": None, "payload": None}


def _read_installed_version() -> str:
    candidates: list[str] = []
    for path in _version_paths:
        try:
            if path.is_file():
                raw = path.read_text(encoding="utf-8").strip()
                if raw:
                    candidates.append(_normalize_version(raw))
        except OSError:
            continue
    if not candidates:
        return "0.0.0"
    return max(candidates, key=_version_tuple)


def _normalize_version(raw: str) -> str:
    match = _VERSION_RE.match(raw)
    if match:
        return match.group("version")
    return raw.strip().lstrip("vV")


def _display_version(version: str) -> str:
    normalized = _normalize_version(version)
    return f"v{normalized}"


def _version_tuple(version: str) -> tuple[int, ...]:
    normalized = _normalize_version(version)
    parts: list[int] = []
    for part in normalized.split("."):
        if not part.isdigit():
            raise ValueError(f"Invalid version segment: {part}")
        parts.append(int(part))
    return tuple(parts)


def is_newer_version(latest: str, current: str) -> bool:
    try:
        return _version_tuple(latest) > _version_tuple(current)
    except ValueError:
        return _normalize_version(latest) != _normalize_version(current)


def get_version_info() -> VersionResponse:
    version = _read_installed_version()
    return VersionResponse(version=version, display_version=_display_version(version))


def _build_instructions(latest_tag: str | None) -> UpdateInstructions:
    tag = latest_tag or "vX.Y"
    if not tag.startswith("v"):
        tag = f"v{tag}"

    return UpdateInstructions(
        summary=(
            "Updates are applied on the host where Docker is running. "
            "Your data in MongoDB and your .env file are kept across upgrades."
        ),
        steps=[
            "On the host machine, open a terminal in your JPilot project directory.",
            f"Check out the release: git fetch --tags origin && git checkout {tag}",
            "Run ./scripts/upgrade.sh (macOS/Linux) or .\\scripts\\upgrade.ps1 (Windows).",
            "When prompted, choose 1 for development or 2 for production.",
            "Sign in again and confirm the version under Settings → About.",
        ],
        commands_linux_mac=["./scripts/upgrade.sh"],
        commands_windows=[".\\scripts\\upgrade.ps1"],
    )


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "JPilot-Update-Check",
    }
    # Optional: set GITHUB_TOKEN (or GH_TOKEN) to raise the API rate limit from 60 to
    # 5000 requests/hour and avoid the unauthenticated 403s.
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _pick_latest_semver_tag(tags: list[dict[str, Any]]) -> str | None:
    best_tag: str | None = None
    best_tuple: tuple[int, ...] | None = None
    for item in tags:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        try:
            normalized = _normalize_version(name)
            version_tuple = _version_tuple(normalized)
        except ValueError:
            continue
        if best_tuple is None or version_tuple > best_tuple:
            best_tuple = version_tuple
            best_tag = name
    return best_tag


def _version_key(tag: str) -> tuple[int, ...]:
    """Sortable version key; unparseable tags sort lowest."""
    try:
        return _version_tuple(_normalize_version(tag))
    except ValueError:
        return (-1,)


async def _fetch_latest_version_info(repo: str) -> dict[str, Any]:
    """Resolve the newest available version, picking the higher of the latest
    published GitHub Release and the latest semver *tag*.

    Releases can lag behind tags (or never be cut), so trusting ``releases/latest``
    alone hides newer tags. We consider both and return whichever is higher.
    """
    headers = _github_headers()
    async with httpx.AsyncClient(timeout=15.0) as client:
        candidates: list[dict[str, Any]] = []

        # Latest *published* release (carries release notes), if any.
        release_response = await client.get(
            f"https://api.github.com/repos/{repo}/releases/latest",
            headers=headers,
        )
        if release_response.status_code == 200:
            release = release_response.json()
            tag = str(release.get("tag_name") or "").strip()
            if tag:
                body = release.get("body")
                candidates.append({
                    "tag": tag,
                    "release_url": release.get("html_url"),
                    "release_name": release.get("name") or tag,
                    "release_notes": str(body).strip() if body else None,
                })
        elif release_response.status_code not in (404,):
            release_response.raise_for_status()

        # Latest semver *tag* — authoritative for what is shippable / checkout-able,
        # even when no Release has been published for it.
        tags_response = await client.get(
            f"https://api.github.com/repos/{repo}/tags",
            headers=headers,
            params={"per_page": 100},
        )
        tags_response.raise_for_status()
        latest_tag = _pick_latest_semver_tag(tags_response.json())
        if latest_tag:
            display_tag = latest_tag if latest_tag.startswith(("v", "V")) else f"v{latest_tag}"
            release_notes: str | None = None
            tag_release = await client.get(
                f"https://api.github.com/repos/{repo}/releases/tags/{latest_tag}",
                headers=headers,
            )
            if tag_release.status_code == 200:
                body = tag_release.json().get("body")
                if body:
                    release_notes = str(body).strip()
            candidates.append({
                "tag": latest_tag,
                "release_url": f"https://github.com/{repo}/tree/{display_tag}",
                "release_name": display_tag,
                "release_notes": release_notes,
            })

        if not candidates:
            raise ValueError("No version tags found on GitHub.")

        # Highest version wins — a newer tag beats an older published release.
        return max(candidates, key=lambda c: _version_key(c["tag"]))


async def check_for_updates(*, force: bool = False, repo: str = _DEFAULT_REPO) -> UpdateCheckResponse:
    now = dt.datetime.now(dt.timezone.utc)
    if _cache["checked_at"] is not None and _cache["payload"] is not None:
        age = now - _cache["checked_at"]
        # Serve cache on a normal check within TTL, or on a forced check that's
        # within the throttle window (so the button can't hammer the rate limit).
        if (not force and age < _CACHE_TTL) or (force and age < _FORCE_MIN_INTERVAL):
            return _cache["payload"]

    current = _read_installed_version()
    display = _display_version(current)
    check_error: str | None = None
    latest_version: str | None = None
    release_url: str | None = None
    release_name: str | None = None
    release_notes: str | None = None
    update_available = False

    try:
        latest = await _fetch_latest_version_info(repo)
        tag = str(latest.get("tag") or "").strip()
        if tag:
            latest_version = _normalize_version(tag)
            release_url = latest.get("release_url")
            release_name = latest.get("release_name") or _display_version(latest_version)
            release_notes = latest.get("release_notes")
            update_available = is_newer_version(latest_version, current)
    except httpx.HTTPStatusError as exc:
        check_error = f"GitHub returned HTTP {exc.response.status_code}."
    except httpx.RequestError:
        check_error = "Could not reach GitHub to check for updates."
    except Exception:
        check_error = "Update check failed unexpectedly."

    payload = UpdateCheckResponse(
        current_version=current,
        display_version=display,
        latest_version=latest_version,
        latest_display_version=_display_version(latest_version) if latest_version else None,
        update_available=update_available,
        release_url=release_url,
        release_name=release_name,
        release_notes=release_notes if update_available else None,
        checked_at=now.isoformat(),
        check_error=check_error,
        update_instructions=_build_instructions(latest_version),
    )
    _cache["checked_at"] = now
    _cache["payload"] = payload
    return payload


# ---------------------------------------------------------------------------
# Self-update sentinel protocol
# ---------------------------------------------------------------------------

_UPDATE_DIR_ENV = "JPILOT_UPDATE_DIR"
_DEFAULT_UPDATE_DIR = "/var/jpilot/update"

_COMPOSE_MODE_PATH = Path(__file__).resolve().parents[3] / ".compose-mode"
_ENV_FILE_CANDIDATES = (
    Path("/app/.env"),
    Path(__file__).resolve().parents[2] / ".env",
    _COMPOSE_MODE_PATH.parent / ".env",
)


def _normalize_deploy_mode(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip().strip('"').strip("'").lower()
    if value in ("prod", "production"):
        return "prod"
    if value in ("dev", "development"):
        return "dev"
    return None


def _parse_deploy_mode_from_env_file(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("NSAGENT_DEPLOY_MODE="):
                return _normalize_deploy_mode(stripped.split("=", 1)[1])
    except OSError:
        return None
    return None


def _read_compose_mode() -> str:
    """Match ./compose.sh: NSAGENT_DEPLOY_MODE in the container env or mounted .env."""
    from_env = _normalize_deploy_mode(os.environ.get("NSAGENT_DEPLOY_MODE"))
    if from_env:
        return from_env

    for candidate in _ENV_FILE_CANDIDATES:
        parsed = _parse_deploy_mode_from_env_file(candidate)
        if parsed:
            return parsed

    try:
        if _COMPOSE_MODE_PATH.is_file():
            legacy = _normalize_deploy_mode(_COMPOSE_MODE_PATH.read_text(encoding="utf-8"))
            if legacy:
                return legacy
    except OSError:
        pass

    return "dev"


def _update_dir() -> Path:
    """Return the shared sentinel directory (create if missing)."""
    path = Path(os.environ.get(_UPDATE_DIR_ENV, _DEFAULT_UPDATE_DIR))
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(path.stat().st_mode | 0o777)
    except OSError:
        pass
    return path


def _make_sentinel_writable(path: Path) -> None:
    """Best-effort: backend may run as root in Docker while the host agent runs as the install owner."""
    try:
        path.chmod(0o666)
    except OSError:
        pass


def _clear_sentinel_files() -> None:
    for path in (_request_file(), _status_file()):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def reconcile_stale_update_lock() -> bool:
    """Drop abandoned request/status files so updates stay manual (button-only).

    Returns True when stale sentinels were cleared.
    """
    status_path = _status_file()
    request_path = _request_file()
    if not status_path.is_file() and not request_path.is_file():
        return False

    try:
        if status_path.is_file():
            raw = json.loads(status_path.read_text(encoding="utf-8"))
            state = str(raw.get("state") or "idle")
        else:
            state = "idle"
    except (OSError, json.JSONDecodeError):
        state = "idle"

    stale = state in ("requested", "running") and _lock_is_stale()
    terminal_with_request = state in ("success", "failed", "idle") and request_path.is_file()
    if stale or terminal_with_request:
        _clear_sentinel_files()
        return True
    return False


def _request_file() -> Path:
    return _update_dir() / "request.json"


def _status_file() -> Path:
    return _update_dir() / "status.json"


def is_update_agent_armed() -> bool:
    """True when auto-updater.sh has installed the host watcher (marker on shared volume)."""
    marker = _update_dir() / ".agent-armed"
    try:
        return marker.is_file()
    except OSError:
        return False


def get_update_agent_info() -> tuple[bool, str]:
    marker = _update_dir() / ".agent-armed"
    return is_update_agent_armed(), str(marker)


def read_update_status() -> UpdateStatusResponse:
    """Read status.json from the sentinel dir; return idle defaults if absent."""
    if reconcile_stale_update_lock():
        return UpdateStatusResponse(state="idle")

    status_path = _status_file()
    try:
        if status_path.is_file():
            raw = json.loads(status_path.read_text(encoding="utf-8"))
            return UpdateStatusResponse(
                state=raw.get("state", "idle"),
                target_tag=raw.get("targetTag"),
                started_at=raw.get("startedAt"),
                finished_at=raw.get("finishedAt"),
                progress=raw.get("progress", []),
                error=raw.get("error"),
            )
    except (OSError, json.JSONDecodeError):
        pass
    return UpdateStatusResponse(state="idle")


# An in-progress update whose sentinel hasn't been touched in this long is treated as
# stale (the host agent never picked it up, or died) so the single-flight lock recovers
# instead of staying "in progress" forever.
_STALE_LOCK_AFTER = dt.timedelta(minutes=20)


def _lock_is_stale() -> bool:
    """True if an in-progress update appears abandoned.

    The host agent rewrites status.json as it progresses, so a fresh mtime means a live
    update while a stale mtime (or a missing file) means nothing is processing it.
    """
    try:
        status_path = _status_file()
        if not status_path.is_file():
            return True
        mtime = dt.datetime.fromtimestamp(status_path.stat().st_mtime, dt.timezone.utc)
        return dt.datetime.now(dt.timezone.utc) - mtime > _STALE_LOCK_AFTER
    except OSError:
        return True


async def request_update() -> TriggerUpdateResponse:
    """
    Resolve the latest release tag via GitHub, write request.json and
    initialise status.json. Raises ValueError if already in-progress.
    Returns TriggerUpdateResponse (accepted=False) if already up to date.
    """
    reconcile_stale_update_lock()

    # Single-flight guard — block only if an update is genuinely in progress.
    # A stale lock (host agent never picked it up / died) is allowed to be overridden.
    current_status = read_update_status()
    if current_status.state in ("requested", "running") and not _lock_is_stale():
        raise RuntimeError(
            f"An update is already in progress (state={current_status.state})."
        )

    # Resolve the latest release tag from GitHub (force bypass cache).
    check = await check_for_updates(force=True)

    if not check.update_available:
        return TriggerUpdateResponse(
            accepted=False,
            message="Already up to date — no update was scheduled.",
            status=current_status,
        )

    target_tag = check.latest_display_version or check.latest_version
    if not target_tag:
        return TriggerUpdateResponse(
            accepted=False,
            message="Could not determine the target release tag.",
            status=current_status,
        )

    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    nonce = uuid.uuid4().hex
    mode = _read_compose_mode()

    # Write request.json — the host agent watches this file.
    request_payload = {
        "nonce": nonce,
        "requestedAt": now_iso,
        "targetTag": target_tag,
        "mode": mode,
    }
    _request_file().write_text(
        json.dumps(request_payload, indent=2), encoding="utf-8"
    )
    _make_sentinel_writable(_request_file())

    # Initialise status.json so the frontend can poll immediately.
    initial_status_payload = {
        "state": "requested",
        "targetTag": target_tag,
        "startedAt": now_iso,
        "finishedAt": None,
        "progress": ["Update requested — waiting for host agent to pick up."],
        "error": None,
    }
    _status_file().write_text(
        json.dumps(initial_status_payload, indent=2), encoding="utf-8"
    )
    _make_sentinel_writable(_status_file())

    new_status = UpdateStatusResponse(
        state="requested",
        target_tag=target_tag,
        started_at=now_iso,
        progress=["Update requested — waiting for host agent to pick up."],
    )

    return TriggerUpdateResponse(
        accepted=True,
        message=f"Update to {target_tag} has been requested. The host agent will rebuild the stack shortly.",
        status=new_status,
    )


def cancel_update_request() -> UpdateStatusResponse:
    """Admin-only: clear a stuck or abandoned update request (does not roll back)."""
    reconcile_stale_update_lock()
    _clear_sentinel_files()
    return UpdateStatusResponse(state="idle")
