from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.calibration_sync_service import list_installed_skills


def _score_excerpt(text: str, query: str) -> int:
    lowered_text = text.lower()
    tokens = [token for token in re.split(r"\W+", query.lower()) if len(token) >= 3]
    if not tokens:
        return 0
    return sum(2 if token in lowered_text else 0 for token in tokens)


def search_stack_calibration_memory(
    query: str,
    *,
    skill_id: str | None = None,
    vendor: str | None = None,
    role: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        raise ValueError("query is required")

    installed = list_installed_skills()
    if skill_id:
        installed = [row for row in installed if row.get("skillId") == skill_id]
    if vendor:
        installed = [row for row in installed if (row.get("vendor") or "").lower() == vendor.lower()]

    matches: list[dict[str, Any]] = []
    for row in installed:
        skill_dir = Path(row.get("path") or "")
        if not skill_dir.is_dir():
            continue

        manifest_file = skill_dir / "manifest.json"
        manifest: dict[str, Any] = {}
        if manifest_file.is_file():
            try:
                import json

                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                manifest = {}

        roles = manifest.get("roles") or []
        if role and roles and role not in roles:
            continue

        for module in manifest.get("memoryModules") or []:
            role_tags = module.get("roleTags") or []
            if role and role_tags and role not in role_tags:
                continue
            rel = module.get("filename") or module.get("path")
            if not rel:
                continue
            file_path = skill_dir / rel
            if not file_path.is_file():
                continue
            content = file_path.read_text(encoding="utf-8")
            score = _score_excerpt(content, cleaned_query)
            if score <= 0:
                continue
            excerpt = content.strip()
            if len(excerpt) > 1200:
                excerpt = excerpt[:1197].rstrip() + "..."
            matches.append(
                {
                    "skillId": row.get("skillId"),
                    "version": row.get("version"),
                    "label": manifest.get("label") or row.get("label") or row.get("skillId"),
                    "vendor": row.get("vendor") or manifest.get("vendor"),
                    "moduleId": module.get("id") or rel,
                    "score": score,
                    "excerpt": excerpt,
                }
            )

    matches.sort(key=lambda item: item["score"], reverse=True)
    trimmed = matches[:limit]
    return {
        "query": cleaned_query,
        "installedSkillCount": len(installed),
        "matchCount": len(trimmed),
        "matches": trimmed,
    }
