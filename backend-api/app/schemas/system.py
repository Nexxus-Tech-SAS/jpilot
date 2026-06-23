from __future__ import annotations

from pydantic import BaseModel, Field


class VersionResponse(BaseModel):
    version: str
    display_version: str


class UpdateInstructions(BaseModel):
    summary: str
    steps: list[str] = Field(default_factory=list)
    commands_linux_mac: list[str] = Field(default_factory=list)
    commands_windows: list[str] = Field(default_factory=list)


class LicenseFingerprintResponse(BaseModel):
    nsagent_encryption_key: str
    nginx_hostname: str
    date: str
    fingerprint: str


class UpdateCheckResponse(BaseModel):
    current_version: str
    display_version: str
    latest_version: str | None = None
    latest_display_version: str | None = None
    update_available: bool = False
    release_url: str | None = None
    release_name: str | None = None
    release_notes: str | None = None
    checked_at: str
    check_error: str | None = None
    update_instructions: UpdateInstructions


class UpdateStatusResponse(BaseModel):
    """Current state of the host-side update agent."""

    state: str = "idle"  # idle | requested | running | success | failed
    target_tag: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    progress: list[str] = Field(default_factory=list)
    error: str | None = None


class TriggerUpdateResponse(BaseModel):
    """Returned immediately after a trigger request is accepted."""

    accepted: bool
    message: str
    status: UpdateStatusResponse


class UpdateAgentResponse(BaseModel):
    """Whether the host-side update watcher was armed via auto-updater.sh."""

    armed: bool = False
    marker_path: str | None = None
