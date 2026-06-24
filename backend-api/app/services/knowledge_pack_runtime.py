"""Assemble chat context from the local Knowledge Pack (no SCStudio HTTP at runtime)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.calibration_matcher import (
    BlueprintTurnContext,
    _format_memory_hits,
    _merge_skill_rows,
    load_skill_memory_excerpt,
    load_skill_prompt_fragment,
    match_installed_skills,
)
from app.services.knowledge_pack_service import get_active_pack_dir, list_pack_embedded_skills


@dataclass(frozen=True)
class KnowledgePackToolPolicy:
    allowed_tools: frozenset[str] | None = None


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _vendor_scope_match(pack_root: Path, chat_vendor: str, scope_vendor_id: str) -> bool:
    if not scope_vendor_id:
        return True
    if scope_vendor_id.lower() == chat_vendor.lower():
        return True
    vendors_catalog = _read_json(pack_root / "catalog" / "vendors.json") or {}
    for entry in vendors_catalog.get("vendors") or []:
        if not isinstance(entry, dict):
            continue
        vendor_id = str(entry.get("vendorId") or entry.get("id") or "")
        jpilot_vendor = str(entry.get("jpilotVendorId") or entry.get("jpilotVendor") or "").lower()
        if vendor_id == scope_vendor_id and (not jpilot_vendor or jpilot_vendor == chat_vendor.lower()):
            return True
    return False


def _domain_scope_match(user_message: str, domain_ids: list[str]) -> bool:
    if not domain_ids:
        return True
    lowered = (user_message or "").lower()
    return any(str(domain).lower() in lowered for domain in domain_ids)


def _load_assignments(pack_root: Path, *, role: str, vendor: str, user_message: str) -> list[dict[str, Any]]:
    index = _read_json(pack_root / "indexes" / "assignment-index.json") or {}
    assignment_ids = index.get("assignmentIds") or index.get("assignments") or []
    if isinstance(assignment_ids, dict):
        assignment_ids = list(assignment_ids.keys())

    matched: list[dict[str, Any]] = []
    for raw_id in assignment_ids:
        assignment_id = str(raw_id)
        assignment = _read_json(pack_root / "assignments" / f"{assignment_id}.json")
        if not assignment:
            continue
        if str(assignment.get("personaId") or "") != role:
            continue
        scope = assignment.get("scope") or {}
        if not _vendor_scope_match(pack_root, vendor, str(scope.get("vendorId") or "")):
            continue
        domain_ids = list(scope.get("domainIds") or [])
        explicit_skill_ids = list(scope.get("skillIds") or [])
        match_mode = str(scope.get("matchMode") or "domain_or_explicit")
        if explicit_skill_ids:
            matched.append(assignment)
            continue
        if match_mode == "domain_or_explicit" and _domain_scope_match(user_message, domain_ids):
            matched.append(assignment)
            continue
        if not domain_ids:
            matched.append(assignment)

    matched.sort(key=lambda row: int(row.get("priority") or 0), reverse=True)
    return matched


def _resolved_blueprint_ids(assignments: list[dict[str, Any]], *, limit: int = 2) -> list[str]:
    ids: list[str] = []
    for assignment in assignments:
        for blueprint_id in assignment.get("resolvedBlueprintIds") or []:
            cleaned = str(blueprint_id).strip()
            if cleaned and cleaned not in ids:
                ids.append(cleaned)
            if len(ids) >= limit:
                return ids
    return ids


def _persona_sections(pack_root: Path, role: str) -> list[str]:
    persona_dir = pack_root / "personas" / role
    sections: list[str] = []
    behavior = _read_text(persona_dir / "behavior.md")
    if behavior:
        sections.append(f"## Persona behavior ({role})\n{behavior}")
    permissions = _read_json(persona_dir / "permissions.json")
    if permissions:
        lines = [f"## Persona permissions ({role})"]
        for key, value in permissions.items():
            lines.append(f"- {key}: {value}")
        sections.append("\n".join(lines))
    return sections


def _is_deliverable_intent(message: str) -> bool:
    lowered = (message or "").lower()
    phrases = (
        "configuration document",
        "design document",
        "change control",
        "deliverable",
        "produce a document",
        "generate a document",
        "configuration doc",
        "design doc",
        "write the document",
        "formal document",
    )
    return any(phrase in lowered for phrase in phrases)


def _score_deliverable_template(message: str, entry: dict[str, Any]) -> int:
    lowered = (message or "").lower()
    score = 0
    for phrase in entry.get("useWhen") or []:
        cleaned = str(phrase).strip().lower()
        if cleaned and cleaned in lowered:
            score += 3
    for example in entry.get("examples") or []:
        cleaned = str(example).strip().lower()
        if cleaned and cleaned in lowered:
            score += 2
    label = str(entry.get("label") or "").strip().lower()
    if label and label in lowered:
        score += 1
    template_id = str(entry.get("id") or "").strip().lower()
    if template_id and template_id in lowered:
        score += 1
    return score


def _persona_deliverable_catalog(pack_root: Path, role: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    persona_dir = pack_root / "personas" / role
    index = _read_json(persona_dir / "deliverable-templates.json")
    entries: list[dict[str, Any]] = []
    bodies: dict[str, str] = {}
    if index and isinstance(index.get("templates"), list):
        for raw in index["templates"]:
            if not isinstance(raw, dict):
                continue
            template_id = str(raw.get("id") or "").strip()
            rel_path = str(raw.get("path") or "").strip()
            if not template_id or not rel_path:
                continue
            body = _read_text(persona_dir / rel_path)
            if not body:
                continue
            entries.append(raw)
            bodies[template_id] = body
        if entries:
            return entries, bodies

    legacy = _read_text(persona_dir / "deliverable-template.md")
    if legacy:
        return (
            [{"id": "deliverable", "label": "Deliverable document", "useWhen": [], "examples": []}],
            {"deliverable": legacy},
        )
    return [], {}


def _format_deliverable_injection(message: str, entries: list[dict[str, Any]], bodies: dict[str, str]) -> str | None:
    if not entries:
        return None

    scored = [(entry, _score_deliverable_template(message, entry)) for entry in entries]
    best_entry, best_score = max(scored, key=lambda row: row[1])

    if len(entries) > 1 and best_score == 0:
        lines = [
            "## Deliverable document templates",
            "This persona has multiple document layouts. Pick the one that matches the user's request.",
        ]
        for entry in entries:
            label = str(entry.get("label") or entry.get("id") or "template")
            template_id = str(entry.get("id") or "")
            lines.append(f"### {label} (`{template_id}`)")
            for phrase in entry.get("useWhen") or []:
                lines.append(f"- Use when: {phrase}")
            for example in entry.get("examples") or []:
                lines.append(f"- Example request: {example}")
        lines.append(
            "If the request type is unclear, ask one short clarifying question before generating the document."
        )
        return "\n".join(lines)

    chosen = best_entry if best_score > 0 else entries[0]
    template_id = str(chosen.get("id") or "")
    body = bodies.get(template_id, "")
    if not body:
        return None
    label = str(chosen.get("label") or template_id)
    return (
        f"## Deliverable document template ({label})\n"
        "Fill this template using collected form values. Preserve section order, tables, and labels. "
        "Replace {{placeholders}} with user-provided values only — do not change structure.\n\n"
        + body
    )


def _format_skill_intake(manifest: dict[str, Any]) -> str:
    form_fields = manifest.get("formFields") or []
    if not form_fields:
        return ""
    lines = ["## Data to collect before producing deliverables"]
    for field in form_fields:
        if not isinstance(field, dict):
            continue
        label = str(field.get("label") or field.get("id") or "field").strip()
        required = "required" if field.get("required") else "optional"
        hint = str(field.get("hint") or "").strip()
        line = f"- {label} ({required})"
        if hint:
            line += f" — {hint}"
        lines.append(line)
    lines.append(
        "Collect missing required fields before generating a formal configuration or design document."
    )
    return "\n".join(lines)


def _overlay_sections(pack_root: Path, *, vendor: str, user_message: str) -> list[str]:
    sections: list[str] = []
    vendor_overlay = _read_json(pack_root / "overlays" / "vendors" / f"{vendor}.json")
    if vendor_overlay and vendor_overlay.get("promptDelta"):
        sections.append(str(vendor_overlay["promptDelta"]).strip())

    vendors_catalog = _read_json(pack_root / "catalog" / "vendors.json") or {}
    device_ids: list[str] = []
    for entry in vendors_catalog.get("vendors") or []:
        if not isinstance(entry, dict):
            continue
        jpilot_vendor = str(entry.get("jpilotVendorId") or entry.get("jpilotVendor") or "").lower()
        if jpilot_vendor == vendor.lower():
            device_id = str(entry.get("deviceId") or "")
            if device_id:
                device_ids.append(device_id)

    for device_id in device_ids:
        product_overlay = _read_json(pack_root / "overlays" / "products" / f"{device_id}.json")
        if product_overlay and product_overlay.get("promptDelta"):
            sections.append(str(product_overlay["promptDelta"]).strip())
        domain_dir = pack_root / "overlays" / "domains" / device_id
        if domain_dir.is_dir():
            for domain_file in sorted(domain_dir.glob("*.json")):
                domain_overlay = _read_json(domain_file)
                if not domain_overlay:
                    continue
                domain_id = domain_file.stem
                if _domain_scope_match(user_message, [domain_id]) and domain_overlay.get("promptDelta"):
                    sections.append(str(domain_overlay["promptDelta"]).strip())
    return [section for section in sections if section]


def _blueprint_rows_from_pack(
    pack_root: Path,
    blueprint_ids: list[str],
    *,
    user_message: str,
    role: str,
    vendor: str,
) -> list[dict[str, Any]]:
    embedded = list_pack_embedded_skills(pack_root)
    by_id = {str(row.get("skillId") or ""): row for row in embedded}
    rows: list[dict[str, Any]] = []

    trigger_pool = [by_id[bid] for bid in blueprint_ids if bid in by_id]
    trigger_matched = match_installed_skills(
        user_message=user_message,
        role=role,
        vendor=vendor,
        installed=trigger_pool,
        limit=len(blueprint_ids),
    )
    for bid in blueprint_ids:
        if bid in by_id and not any(row.get("skillId") == bid for row in trigger_matched):
            row = by_id[bid]
            skill_dir = Path(row["path"])
            manifest_file = skill_dir / "manifest.json"
            manifest = _read_json(manifest_file) or {}
            trigger_matched.append({**row, "manifest": manifest, "skillDir": str(skill_dir)})

    if not trigger_matched and blueprint_ids:
        for bid in blueprint_ids[:2]:
            row = by_id.get(bid)
            if not row:
                continue
            skill_dir = Path(row["path"])
            manifest = _read_json(skill_dir / "manifest.json") or _read_json(skill_dir / "skill.json") or {}
            trigger_matched.append({**row, "manifest": manifest, "skillDir": str(skill_dir)})

    return _merge_skill_rows(trigger_matched, [], limit=2)


def persona_allowed_tools(pack_root: Path, role: str) -> frozenset[str] | None:
    permissions = _read_json(pack_root / "personas" / role / "permissions.json") or {}
    allowed = permissions.get("allowedTools") or permissions.get("toolPack")
    if not allowed:
        return None
    return frozenset(str(name) for name in allowed if name)


def resolve_knowledge_pack_turn_context(
    *,
    user_message: str,
    role: str,
    vendor: str,
    pack_root: Path | None = None,
) -> tuple[BlueprintTurnContext, KnowledgePackToolPolicy]:
    pack_dir = pack_root or get_active_pack_dir()
    if not pack_dir:
        return (
            BlueprintTurnContext(
                relevant=False,
                injection_block=None,
                matched_skill_ids=(),
                stack_calibration_reviewed=True,
            ),
            KnowledgePackToolPolicy(),
        )

    sections: list[str] = []
    sections.extend(_persona_sections(pack_dir, role))
    sections.extend(_overlay_sections(pack_dir, vendor=vendor, user_message=user_message))

    if _is_deliverable_intent(user_message):
        entries, bodies = _persona_deliverable_catalog(pack_dir, role)
        deliverable_block = _format_deliverable_injection(user_message, entries, bodies)
        if deliverable_block:
            sections.append(deliverable_block)

    assignments = _load_assignments(pack_dir, role=role, vendor=vendor, user_message=user_message)
    blueprint_ids = _resolved_blueprint_ids(assignments, limit=2)
    blueprint_rows = _blueprint_rows_from_pack(
        pack_dir,
        blueprint_ids,
        user_message=user_message,
        role=role,
        vendor=vendor,
    )

    if blueprint_rows:
        sections.append("## Matched calibration skills")
        for row in blueprint_rows:
            skill_dir = Path(row["skillDir"])
            manifest = row.get("manifest") or {}
            label = manifest.get("label") or row.get("skillId")
            sections.append(f"### {label} (`{manifest.get('id') or row.get('skillId')}`)")
            prompt = load_skill_prompt_fragment(skill_dir, role)
            if prompt:
                sections.append(prompt)
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

    skill_ids = tuple(str(row.get("skillId") or "") for row in blueprint_rows if row.get("skillId"))
    injection = "\n\n".join(section for section in sections if section).strip() or None
    tool_policy = KnowledgePackToolPolicy(allowed_tools=persona_allowed_tools(pack_dir, role))

    if not injection:
        return (
            BlueprintTurnContext(
                relevant=False,
                injection_block=None,
                matched_skill_ids=skill_ids,
                stack_calibration_reviewed=True,
            ),
            tool_policy,
        )

    return (
        BlueprintTurnContext(
            relevant=bool(blueprint_rows),
            injection_block=injection,
            matched_skill_ids=skill_ids,
            stack_calibration_reviewed=not bool(blueprint_rows),
        ),
        tool_policy,
    )
