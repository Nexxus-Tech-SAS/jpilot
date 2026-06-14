"""Preset agent orchestration profiles for platform settings."""

from __future__ import annotations

from typing import Any, Literal

OrchestrationMode = Literal["standard", "extended", "max", "custom"]

ORCHESTRATION_PRESET_MODES: tuple[str, ...] = ("standard", "extended", "max")

ORCHESTRATION_PRESETS: dict[str, dict[str, Any]] = {
    "standard": {
        "maxToolIterations": 20,
        "maxToolContinuationPhases": 3,
        "longTaskToolThreshold": 8,
        "promptBeforeLongTasks": True,
    },
    "extended": {
        "maxToolIterations": 30,
        "maxToolContinuationPhases": 4,
        "longTaskToolThreshold": 10,
        "promptBeforeLongTasks": True,
    },
    "max": {
        "maxToolIterations": 40,
        "maxToolContinuationPhases": 5,
        "longTaskToolThreshold": 12,
        "promptBeforeLongTasks": True,
    },
}

DEFAULT_ORCHESTRATION_MODE: OrchestrationMode = "standard"


def preset_values(mode: str) -> dict[str, Any] | None:
    return ORCHESTRATION_PRESETS.get(mode)


def infer_orchestration_mode(document: dict[str, Any] | None) -> OrchestrationMode:
    document = document or {}
    stored = str(document.get("orchestrationMode") or "").strip().lower()
    if stored in ORCHESTRATION_PRESETS:
        return stored  # type: ignore[return-value]
    if stored == "custom":
        return "custom"

    for mode, preset in ORCHESTRATION_PRESETS.items():
        if all(document.get(key, value) == value for key, value in preset.items()):
            return mode  # type: ignore[return-value]
    return "custom"
