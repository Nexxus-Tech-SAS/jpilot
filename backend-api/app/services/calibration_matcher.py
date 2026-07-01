from __future__ import annotations

import json
import re
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


# Generic tokens that don't disambiguate WHICH NetScaler blueprint applies — excluded
# from intent-relevance scoring so a blueprint only matches on its distinctive terms.
_TRIGGER_STOPWORDS = frozenset(
    {
        "configure", "create", "setup", "deploy", "enable", "disable", "update",
        "modify", "change", "implement", "http", "https", "netscaler", "citrix",
        "adc", "this", "that", "your", "with", "from", "into", "onto", "want",
        "need", "please", "using", "use", "via", "run", "show", "list", "make",
        "server", "servers", "vserver", "vservers", "service", "other", "traffic",
        "request", "requests", "response", "responses",
    }
)


def _terms(text: str) -> set[str]:
    """Distinctive lowercase tokens (>=4 chars, minus generic stopwords)."""
    return {
        tok
        for tok in re.split(r"\W+", (text or "").lower())
        if len(tok) >= 4 and tok not in _TRIGGER_STOPWORDS
    }


def _trigger_terms(manifest: dict[str, Any]) -> set[str]:
    """Distinctive terms drawn from a skill's trigger intents/commands only.

    Deliberately excludes label/domains — those carry generic words like "load
    balancer" that would cross-match unrelated blueprints (e.g. the Security
    Headers skill's label contains 'Load Balancer')."""
    triggers = manifest.get("triggers") or {}
    parts: list[str] = [str(i) for i in (triggers.get("intents") or [])]
    parts += [str(c).replace("-", " ") for c in (triggers.get("commands") or [])]
    terms: set[str] = set()
    for part in parts:
        terms |= _terms(part)
    return terms


# A blueprint is "relevant" for the turn only when the message shares at least this
# many distinctive intent terms with the skill (or an exact trigger-phrase match).
_RELEVANCE_MIN_TERMS = 2


def _trigger_relevance(message: str, manifest: dict[str, Any]) -> int:
    return len(_terms(message) & _trigger_terms(manifest))


# ---------------------------------------------------------------------------
# Provisioning-intent gate.
#
# Some blueprints provision a NEW object (e.g. "Configure HTTP Load Balancer"
# stands up a new LB vserver). Their only distinctive trigger terms are the domain
# NOUNS ("load", "balancer"), so a bare mention of "load balancer" as an incidental
# binding target — or even a *declined* one ("no load balancer for now") — clears the
# >=2-term relevance bar and the blueprint hijacks the turn. Worse, the phrase appears
# verbatim inside another blueprint's NAME ("...on Load Balancer"), so invoking the
# Security Headers blueprint drags the LB one in on the shared nouns.
#
# Fix: a provisioning blueprint is relevant only when the message expresses genuine
# provisioning intent (a create/configure/deploy verb) AND does not negate the object.
# This does NOT weaken the legitimate "configure a new HTTP load balancer" case.
# ---------------------------------------------------------------------------

# Verbs that signal the user wants to stand something up (not merely reference it).
_PROVISION_VERBS = frozenset(
    {
        "configure", "create", "setup", "set up", "deploy", "add", "provision",
        "build", "stand up", "spin up", "new",
    }
)

# Leading verbs that mark a blueprint's intents as provisioning intents.
_PROVISION_INTENT_LEADERS = frozenset(
    {"configure", "create", "setup", "deploy", "add", "provision", "build"}
)


def _is_provisioning_blueprint(manifest: dict[str, Any]) -> bool:
    """True when every trigger intent is verb-led with a provisioning verb.

    Detected from the manifest's own intents (no per-skill flag needed): e.g. the LB
    blueprint's intents are all "configure http load balancer" / "create new http load
    balancer" / "deploy http lb". Read-only or apply-to-existing blueprints (Security
    Headers: "apply security headers to lb vserver", "enable ...") are NOT flagged,
    so this gate only ever tightens genuine provisioning blueprints."""
    intents = (manifest.get("triggers") or {}).get("intents") or []
    if not intents:
        return False
    for intent in intents:
        first = str(intent).strip().lower().split(" ", 1)[0]
        if first not in _PROVISION_INTENT_LEADERS:
            return False
    return True


def _message_has_provisioning_intent(message: str) -> bool:
    lowered = (message or "").lower()
    return any(verb in lowered for verb in _PROVISION_VERBS)


# "no load balancer", "without a load balancer", "don't create a load balancer", etc.
_NEGATION_TOKENS = ("no ", "not ", "without", "don't", "dont", "skip", "decline", "aren't")


def _message_negates_terms(message: str, terms: set[str]) -> bool:
    """True when a distinctive term appears in a negated clause of the message.

    Guards against "no load balancer for now, just create the policies" selecting the
    LB provisioning blueprint off the incidental noun."""
    lowered = (message or "").lower()
    for term in terms:
        idx = lowered.find(term)
        while idx != -1:
            window = lowered[max(0, idx - 24): idx]
            if any(neg in window for neg in _NEGATION_TOKENS):
                return True
            idx = lowered.find(term, idx + 1)
    return False


def _passes_provisioning_gate(message: str, manifest: dict[str, Any], *, intent_hit: bool) -> bool:
    """For a provisioning blueprint matched only on term overlap (no exact intent
    phrase), require real provisioning intent and no negation of its domain nouns.

    Returns True for non-provisioning blueprints (gate is a no-op) and whenever an
    exact trigger-phrase already matched (the user spelled out the intent)."""
    if intent_hit or not _is_provisioning_blueprint(manifest):
        return True
    if not _message_has_provisioning_intent(message):
        return False
    if _message_negates_terms(message, _trigger_terms(manifest)):
        return False
    return True


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
        intent_hit = _message_matches_triggers(user_message, triggers)
        overlap = _trigger_relevance(user_message, manifest)
        # Require a genuine intent signal: an exact trigger-phrase match OR enough
        # distinctive intent-term overlap. This is what gates blueprint injection on
        # request intent instead of incidental word overlap with the memory body.
        if not (intent_hit or overlap >= _RELEVANCE_MIN_TERMS):
            continue
        # Provisioning blueprints (e.g. "Configure HTTP Load Balancer") must not be
        # selected on an incidental/declined mention of their domain nouns. When the
        # match rests only on term overlap, require real provisioning intent and no
        # negation of those nouns — otherwise "bind headers to the load balancer",
        # "no load balancer for now", or another blueprint's "...on Load Balancer"
        # name would hijack the turn.
        if not _passes_provisioning_gate(user_message, manifest, intent_hit=intent_hit):
            continue
        score = (100 if intent_hit else 0) + 10 * overlap + int(manifest.get("priority") or 0)
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

    # Intent-gated: a blueprint is injected only when the message genuinely matches
    # its trigger intent (exact phrase or >=2 distinctive intent terms). Memory-body
    # keyword overlap is NOT used to decide relevance — it over-matched unrelated
    # requests (e.g. injecting the Security Headers blueprint on "list all IPs").
    matched = match_installed_skills(
        user_message=user_message,
        role=role,
        vendor=vendor,
        installed=installed,
        limit=limit,
    )
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
