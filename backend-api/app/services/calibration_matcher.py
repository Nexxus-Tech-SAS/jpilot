from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CALIBRATIONS_DIR = Path("data/calibrations")


def _load_manifest(path: Path) -> dict[str, Any] | None:
    manifest_file = path / "manifest.json"
    if not manifest_file.is_file():
        return None
    try:
        return json.loads(manifest_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _message_matches_triggers(message: str, triggers: dict[str, Any]) -> bool:
    lowered = (message or "").lower()
    intents = triggers.get("intents") or []
    for intent in intents:
        if str(intent).lower() in lowered:
            return True
    commands = triggers.get("commands") or []
    for command in commands:
        if str(command).lower() in lowered:
            return True
    return False


def load_skill_prompt_fragment(skill_dir: Path, role: str) -> str | None:
    manifest = _load_manifest(skill_dir)
    if not manifest:
        return None

    includes = manifest.get("promptIncludes") or []
    role_file = f"prompts/{role}.md"
    if role_file.lstrip("prompts/") not in {p.replace("prompts/", "") for p in includes} and includes:
        if role_file not in includes:
            pass

    prompt_path = skill_dir / "prompts" / f"{role}.md"
    if prompt_path.is_file():
        return prompt_path.read_text(encoding="utf-8").strip()

    if includes:
        first = includes[0]
        alt = skill_dir / first
        if alt.is_file():
            return alt.read_text(encoding="utf-8").strip()
    return None


def load_skill_memory_excerpt(skill_dir: Path, role: str, *, max_chars: int = 4000) -> str:
    manifest = _load_manifest(skill_dir)
    if not manifest:
        return ""

    chunks: list[str] = []
    for module in manifest.get("memoryModules") or []:
        role_tags = module.get("roleTags") or []
        if role_tags and role not in role_tags:
            continue
        rel = module.get("filename") or module.get("path")
        if not rel:
            continue
        file_path = skill_dir / rel
        if file_path.is_file():
            chunks.append(file_path.read_text(encoding="utf-8").strip())

    combined = "\n\n".join(chunks).strip()
    if len(combined) <= max_chars:
        return combined
    return combined[: max_chars - 3].rstrip() + "..."


def _installed_for_chat(
    installed: list[dict[str, Any]],
    *,
    role: str,
    vendor: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in installed:
        skill_vendor = str(row.get("vendor") or "")
        if skill_vendor and skill_vendor != vendor:
            continue
        skill_dir = Path(row.get("path") or "")
        manifest = _load_manifest(skill_dir) if skill_dir.is_dir() else None
        if not manifest:
            continue
        roles = manifest.get("roles") or []
        if roles and role not in roles:
            continue
        rows.append({**row, "manifest": manifest, "skillDir": str(skill_dir)})
    return rows


def _skills_from_memory_search(
    *,
    user_message: str,
    role: str,
    vendor: str,
    installed: list[dict[str, Any]],
    limit: int = 2,
) -> list[dict[str, Any]]:
    from app.services.calibration_memory_service import search_stack_calibration_memory

    try:
        result = search_stack_calibration_memory(
            user_message,
            vendor=vendor,
            role=role,
            limit=limit,
        )
    except ValueError:
        return []

    by_id = {row.get("skillId"): row for row in installed if row.get("skillId")}
    matched: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in result.get("matches") or []:
        skill_id = str(item.get("skillId") or "")
        if not skill_id or skill_id in seen:
            continue
        row = by_id.get(skill_id)
        if not row:
            continue
        seen.add(skill_id)
        skill_dir = Path(row.get("path") or "")
        manifest = _load_manifest(skill_dir) if skill_dir.is_dir() else None
        if not manifest:
            continue
        matched.append({**row, "manifest": manifest, "skillDir": str(skill_dir), "memoryHits": [item]})
    return matched


def match_installed_skills(
    *,
    user_message: str,
    role: str,
    vendor: str,
    installed: list[dict[str, Any]],
    limit: int = 2,
) -> list[dict[str, Any]]:
    matches: list[tuple[int, dict[str, Any]]] = []
    for row in _installed_for_chat(installed, role=role, vendor=vendor):
        manifest = row.get("manifest") or {}
        triggers = manifest.get("triggers") or {}
        score = 0
        if _message_matches_triggers(user_message, triggers):
            score += 100
        score += int(manifest.get("priority") or 0)
        if score > 0:
            matches.append((score, row))

    matches.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in matches[:limit]]


@dataclass(frozen=True)
class BlueprintTurnContext:
    relevant: bool
    injection_block: str | None
    matched_skill_ids: tuple[str, ...]
    stack_calibration_reviewed: bool


BLUEPRINT_FIRST_NUDGE = (
    "## Blueprint-first\n"
    "This turn matches installed stack calibration blueprint(s). Use their playbook "
    "commands/paths/inputs directly. Do NOT call search_netscaler_cli_reference, "
    "search_netscaler_nextgen_api, or memory search when the blueprint already supplies "
    "what to run — reserve discovery searches only for steps the blueprint does not cover."
)


def _merge_skill_rows(*groups: list[dict[str, Any]], limit: int = 2) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for row in group:
            skill_id = str(row.get("skillId") or "")
            if not skill_id or skill_id in seen:
                continue
            seen.add(skill_id)
            merged.append(row)
            if len(merged) >= limit:
                return merged
    return merged


def _format_memory_hits(hits: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for hit in hits:
        label = hit.get("moduleId") or hit.get("skillId") or "memory"
        excerpt = str(hit.get("excerpt") or "").strip()
        if excerpt:
            lines.append(f"**{label}**\n{excerpt}")
    return "\n\n".join(lines).strip()


def has_installed_skills_for_chat(
    *,
    role: str,
    vendor: str,
    installed: list[dict[str, Any]] | None = None,
) -> bool:
    if installed is None:
        from app.services.calibration_sync_service import list_installed_skills

        installed = list_installed_skills()
    return bool(_installed_for_chat(installed, role=role, vendor=vendor))


def build_skill_injection_block(
    *,
    user_message: str,
    role: str,
    vendor: str,
    installed: list[dict[str, Any]],
) -> str | None:
    ctx = resolve_blueprint_turn_context(
        user_message=user_message,
        role=role,
        vendor=vendor,
        installed=installed,
    )
    return ctx.injection_block


def resolve_blueprint_turn_context(
    *,
    user_message: str,
    role: str,
    vendor: str,
    installed: list[dict[str, Any]],
    limit: int = 2,
) -> BlueprintTurnContext:
    scoped = _installed_for_chat(installed, role=role, vendor=vendor)
    if not scoped:
        return BlueprintTurnContext(
            relevant=False,
            injection_block=None,
            matched_skill_ids=(),
            stack_calibration_reviewed=True,
        )

    trigger_matched = match_installed_skills(
        user_message=user_message,
        role=role,
        vendor=vendor,
        installed=installed,
        limit=limit,
    )
    memory_matched = _skills_from_memory_search(
        user_message=user_message,
        role=role,
        vendor=vendor,
        installed=scoped,
        limit=limit,
    )
    matched = _merge_skill_rows(trigger_matched, memory_matched, limit=limit)
    if not matched:
        return BlueprintTurnContext(
            relevant=False,
            injection_block=None,
            matched_skill_ids=(),
            stack_calibration_reviewed=True,
        )

    sections: list[str] = ["## Matched calibration skills"]
    for row in matched:
        skill_dir = Path(row["skillDir"])
        manifest = row.get("manifest") or {}
        label = manifest.get("label") or row.get("skillId")
        sections.append(f"### {label} (`{manifest.get('id')}`)")

        prompt = load_skill_prompt_fragment(skill_dir, role)
        if prompt:
            sections.append(prompt)

        from app.services.knowledge_pack_runtime import _format_skill_intake

        intake_block = _format_skill_intake(manifest)
        if intake_block:
            sections.append(intake_block)

        memory_hits = row.get("memoryHits") or []
        if memory_hits:
            formatted = _format_memory_hits(memory_hits)
            if formatted:
                sections.append(formatted)
        else:
            memory = load_skill_memory_excerpt(skill_dir, role)
            if memory:
                sections.append(memory)

    skill_ids = tuple(str(row.get("skillId") or "") for row in matched if row.get("skillId"))
    return BlueprintTurnContext(
        relevant=True,
        injection_block="\n\n".join(sections).strip(),
        matched_skill_ids=skill_ids,
        stack_calibration_reviewed=False,
    )


# ---------------------------------------------------------------------------
# Relaxed-candidate helper for blueprint suggestion cards.
# Called when the strict match returned relevant=False.  Returns ONE candidate
# (the highest-scored installed skill for this role/vendor) when its score meets
# a minimum floor — so only plausible matches surface a suggestion card.
# ---------------------------------------------------------------------------

_RELAXED_CONFIDENCE_FLOOR = 1  # priority > 0 OR any manifest label hit counts


def find_relaxed_blueprint_candidate(
    *,
    user_message: str,
    role: str,
    vendor: str,
    installed: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the single best installed skill for role/vendor as a suggestion candidate.

    Uses a lenient scoring path: trigger score 0 is accepted when the skill has a
    positive priority (priority score alone meets the floor).  Requires at least one
    installed skill to exist for the role/vendor (caller should gate on
    ``has_installed_skills_for_chat`` first).

    Returns None when no candidate meets the floor.
    """
    scoped = _installed_for_chat(installed, role=role, vendor=vendor)
    if not scoped:
        return None

    best_score = -1
    best_row: dict[str, Any] | None = None

    for row in scoped:
        manifest = row.get("manifest") or {}
        triggers = manifest.get("triggers") or {}
        score = 0
        if _message_matches_triggers(user_message, triggers):
            score += 100
        score += int(manifest.get("priority") or 0)
        # Also do a lightweight memory search hit boost — if a memory search finds this
        # skill it gets +50 on top of existing score.
        # (Avoid the full async search here; use synchronous trigger-only path.)
        if score > best_score:
            best_score = score
            best_row = row

    if best_row is None or best_score < _RELAXED_CONFIDENCE_FLOOR:
        return None

    manifest = best_row.get("manifest") or {}
    return {
        "skillId": str(best_row.get("skillId") or ""),
        "label": str(manifest.get("label") or best_row.get("skillId") or ""),
        "summary": str(manifest.get("description") or manifest.get("summary") or ""),
        "confidence": min(best_score, 100),
    }
