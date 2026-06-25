"""Architect discovery guardrails — jpilot-form only, no checklist loops."""

from __future__ import annotations

import re

from app.services.copilot_form import is_form_submission, parse_input_form
from app.services.copilot_roles import JPilotRole, normalize_role

ARCHITECT_SEARCH_TOOL_NAMES = frozenset(
    {
        "search_jpilot_architect_resources",
        "search_f5_documentation",
    }
)

_BAD_DISCOVERY_RE = re.compile(
    r"(✅|❌|still missing|discovery checklist|let me ask turn|"
    r"one quick question to check off|we('re| are) making progress|almost there\. let me get|"
    r"</tool_calls?>|<\|tool|DSML\|tool)",
    re.IGNORECASE,
)

_TURN_CHECKLIST_RE = re.compile(r"turn\s*[1-5]\s*:", re.IGNORECASE)

_DESIGN_NOW_RE = re.compile(
    r"^\s*(go|yes|ok|okay|continue|proceed|generate|draft|build)\s*\.?\s*$",
    re.IGNORECASE,
)

_DESIGN_NOW_PHRASES = (
    "generate the design",
    "produce the design",
    "write the design",
    "create the design",
    "make the design",
    "draft the design",
    "build the design",
    "give me the design",
    "give me the full design",
    "full design",
    "design document",
    "best-effort design",
    "best effort design",
    "skip the questions",
    "skip discovery",
    "stop asking",
    "enough questions",
    "i have enough",
    "ready to generate",
    "let's generate",
    "lets generate",
    "just design",
)

_DELIVERABLE_MARKERS = (
    "<!-- jpilot-design-document -->",
    "<!-- jpilot-change-control-document -->",
)

_REVISION_PHRASES = (
    "fill in the tbd",
    "fill the tbd",
    "fill in tbd",
    "include the tbd",
    "include tbd",
    "ask me for the tbd",
    "ask me for tbd",
    "update the design",
    "revise the design",
    "edit the design",
    "update the document",
    "revise the document",
    "edit the document",
    "update design document",
    "revise design document",
    "something missing",
    "missing from the design",
    "fill in missing",
    "complete the tbd",
)

_CHANGE_CONTROL_NOW_PHRASES = (
    "generate the change control",
    "produce the change control",
    "write the change control",
    "change control document",
    "change control record",
    "maintenance window document",
)

_PLANNING_INTENT_FIELD_RE = re.compile(
    r"planning intent:\s*(new_deployment|new_functionality|change_control)\b",
    re.IGNORECASE,
)

_CHANGE_CONTROL_SIGNAL_RE = re.compile(
    r"(firmware\s+upgrade|maintenance\s+window|change\s+control|rollback\s+plan|"
    r"pre-?change\s+checklist|verification\s+checklist|phased\s+.+\s+plan|"
    r"upgrade\s+plan\s+for\s+ha)",
    re.IGNORECASE,
)

_RICH_CHANGE_CONTROL_SECTIONS = (
    "prerequisite",
    "risk",
    "maintenance",
    "rollback",
    "verification",
    "checklist",
)


def user_wants_design_now(user_message: str) -> bool:
    text = (user_message or "").strip()
    if not text:
        return False
    if _DESIGN_NOW_RE.match(text):
        return True
    lowered = text.lower()
    return any(phrase in lowered for phrase in _DESIGN_NOW_PHRASES)


def user_wants_change_control_now(user_message: str) -> bool:
    text = (user_message or "").strip()
    if not text:
        return False
    if _DESIGN_NOW_RE.match(text):
        return False
    lowered = text.lower()
    return any(phrase in lowered for phrase in _CHANGE_CONTROL_NOW_PHRASES)


def user_wants_deliverable_now(user_message: str) -> bool:
    return user_wants_design_now(user_message) or user_wants_change_control_now(user_message)


def conversation_has_deliverable(conversation_text: str) -> bool:
    text = conversation_text or ""
    return any(marker in text for marker in _DELIVERABLE_MARKERS)


def user_wants_deliverable_revision(user_message: str) -> bool:
    text = (user_message or "").strip()
    if not text or is_form_submission(text):
        return False
    lowered = text.lower()
    return any(phrase in lowered for phrase in _REVISION_PHRASES)


JPILOT_FORM_NOT_A_TOOL_HINT = (
    "jpilot-form is NOT an MCP tool. Never call jpilot-form, inputForm, or similar as tool_calls. "
    "Embed exactly one ```jpilot-form``` JSON fence in your assistant markdown reply instead."
)


def is_rich_change_control_request(text: str) -> bool:
    """User already asked for a structured change-control deliverable (e.g. firmware HA upgrade plan)."""
    stripped = (text or "").strip()
    if not stripped or is_form_submission(stripped):
        return False
    if not _CHANGE_CONTROL_SIGNAL_RE.search(stripped):
        return False
    lowered = stripped.lower()
    section_hits = sum(1 for term in _RICH_CHANGE_CONTROL_SECTIONS if term in lowered)
    return section_hits >= 2 or "ha pair" in lowered


def extract_planning_intent(*texts: str) -> str | None:
    """Return planning_intent from form submissions or plain-text hints."""
    combined = "\n".join(t for t in texts if t).lower()
    match = _PLANNING_INTENT_FIELD_RE.search(combined)
    if match:
        return match.group(1).lower()
    if "planning intent: new deployment" in combined or "greenfield" in combined:
        return "new_deployment"
    if "planning intent: new functionality" in combined:
        return "new_functionality"
    if "planning intent: change control" in combined or "change control / maintenance" in combined:
        return "change_control"
    for raw in texts:
        if raw and is_rich_change_control_request(raw):
            return "change_control"
    if _CHANGE_CONTROL_SIGNAL_RE.search(combined):
        return "change_control"
    return None


def _conversation_started_with_rich_change_control(conversation_text: str) -> bool:
    """True when the opening user request already specified a change-control deliverable."""
    for line in (conversation_text or "").splitlines():
        if re.match(r"planning inputs for:", line, re.IGNORECASE):
            return False
        stripped = line.strip()
        if stripped and is_rich_change_control_request(stripped):
            return True
    return False


def _change_control_intent_declared_upfront(conversation_text: str) -> bool:
    """True when the user asked for change control before any discovery form was submitted."""
    for line in (conversation_text or "").splitlines():
        if re.match(r"planning inputs for:", line, re.IGNORECASE):
            return False
        stripped = line.strip()
        if stripped and _CHANGE_CONTROL_SIGNAL_RE.search(stripped):
            return True
    return False


def _uses_bad_discovery_prose(content: str) -> bool:
    if not content or not content.strip():
        return False
    if _BAD_DISCOVERY_RE.search(content):
        return True
    if _TURN_CHECKLIST_RE.search(content) and "jpilot-form" not in content.lower():
        return True
    return False


def sanitize_architect_reply(content: str) -> str:
    """Strip leaked tool-call markup from model output."""
    if not content:
        return content
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("</") and "tool" in stripped.lower():
            continue
        if "DSML" in stripped and "tool_calls" in stripped:
            continue
        if stripped in {"</tool_calls>", "<tool_calls>"}:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _revision_form_nudge() -> str:
    return (
        "A design or change-control deliverable already exists in this conversation. "
        "The user wants to fill in **TBD** fields or revise the document. "
        f"{JPILOT_FORM_NOT_A_TOOL_HINT} "
        "Do NOT call search_* or other tools. "
        "Review the latest deliverable, identify fields still marked TBD (prioritize network/VLAN/IPs, "
        "licensing, firmware build, VIP address, and HA NSIPs), then output a short intro (≤2 sentences) "
        "and exactly one ```jpilot-form``` with up to 6 fields for those TBD values. "
        'Use submitLabel "Update design". No prose after the closing fence.'
    )


def _revision_apply_nudge(*, planning_intent: str | None) -> str:
    marker = (
        "<!-- jpilot-change-control-document -->"
        if planning_intent == "change_control"
        else "<!-- jpilot-design-document -->"
    )
    doc_label = "Change control record" if planning_intent == "change_control" else "Design document"
    return (
        "The user submitted values to update an existing deliverable. "
        f"{JPILOT_FORM_NOT_A_TOOL_HINT} "
        "Do NOT call any tools. "
        f"Re-output the COMPLETE revised {doc_label} in one markdown reply: first line {marker}, "
        "apply the new values everywhere relevant, keep remaining unknowns as TBD, "
        "preserve structure/tables, and keep **Handoff for Operator** if it was present. "
        "Do not ask more questions."
    )


# A4 — Ordered section skeleton for new_deployment deliverables
_NEW_DEPLOYMENT_SECTION_SKELETON = (
    "Structure the document with these ordered sections (omit any section not in scope for this design): "
    "1. **Summary** — one-paragraph executive summary; "
    "2. **Deployment Topology** — site/DC layout, appliance count, HA mode; "
    "3. **Network Table** — VLANs, subnets, interface assignments, VIP/NSIP/SNIP/gateway; "
    "4. **High Availability** — HA protocol, sync configuration, failover triggers, heartbeat; "
    "5. **SSL / WAF** — certificate details, cipher policy, SNI, AppFirewall profile (if in scope); "
    "6. **Authentication** — auth method, LDAP/RADIUS/SAML parameters, session policy; "
    "7. **Monitoring & ADM** — health checks, SNMP, syslog, ADM integration, alert thresholds; "
    "8. **Backups & Config Export** — backup schedule, ns.conf export, tech-support bundle; "
    "9. **Risks & Assumptions** — known gaps, TBD items, prerequisites; "
    "10. **Handoff for Operator** — numbered CLI/provisioning steps, run-book reference. "
)

_NEW_FUNCTIONALITY_SECTION_SKELETON = (
    "Structure the document with these ordered sections (omit any section not in scope): "
    "1. **Summary** — what is changing and why; "
    "2. **Current State** — relevant existing configuration; "
    "3. **Proposed Change** — tables and config snippets; "
    "4. **Impact & Risk** — blast radius, outage window, dependencies; "
    "5. **Prerequisites** — what must be true before the change; "
    "6. **Validation Steps** — post-change tests and success criteria; "
    "7. **Rollback Plan** — how to revert; "
    "8. **Handoff for Operator** — numbered steps. "
)


def _design_now_nudge(*, doc_tool: str, planning_intent: str | None, vendor_id: str) -> str:
    if planning_intent == "change_control":
        outline_hint = (
            "Call search_jpilot_architect_resources with query 'change control outline' if you need the section structure. "
            if vendor_id == "netscaler"
            else "Follow the change control outline from your Architect prompt (ITIL/ServiceNow sections). "
        )
        return (
            "The user wants the formal change control record now. Do NOT ask more discovery questions or show checklists. "
            "Use conversation history for answers already given. "
            f"{outline_hint}"
            "Output the full Change control record. First line: <!-- jpilot-change-control-document -->. "
            "Use ITIL/ServiceNow-style vendor-neutral sections plus the vendor pre-change checklist appendix for this product. "
            "Mark unknowns TBD — do not re-open completed topics. "
            "Include **Handoff for Operator** only if the user requested on-appliance execution."
        )
    if planning_intent == "new_functionality":
        return (
            "The user wants the functional change design now. Do NOT ask more discovery questions or show checklists. "
            "Use conversation history for answers already given. "
            f"Call {doc_tool} if you need official references, then output the full Functional change design. "
            "First line: <!-- jpilot-design-document -->. "
            f"{_NEW_FUNCTIONALITY_SECTION_SKELETON}"
            "Mark unknowns TBD — do not re-open completed topics."
        )
    # new_deployment (default) — A4 skeleton
    return (
        "The user wants the formal design document now. Do NOT ask more discovery questions or show checklists. "
        "Use conversation history for answers already given (including plain-text replies like VMware or one-arm). "
        f"Call {doc_tool} if you need official references, then output the full Design document. "
        "First line: <!-- jpilot-design-document -->. "
        f"{_NEW_DEPLOYMENT_SECTION_SKELETON}"
        "Mark unknowns TBD — do not re-open completed topics."
    )


def count_planning_form_submissions(text: str) -> int:
    return len(re.findall(r"planning inputs for:", text or "", re.IGNORECASE))


def count_unique_planning_form_submissions(text: str) -> int:
    titles = re.findall(
        r"planning inputs for:\s*(.+?)(?:\n|$)",
        text or "",
        re.IGNORECASE,
    )
    return len({title.strip().lower() for title in titles if title.strip()})


# ---------------------------------------------------------------------------
# A2 — coverage-based readiness: topics we need to see covered in conversation
# ---------------------------------------------------------------------------

# Each topic is a tuple of keyword patterns; any match counts the topic covered.
_COVERAGE_TOPICS_NEW_DEPLOYMENT = (
    # business goal / planning intent
    (r"business goal|planning intent|purpose|objective|use.?case|application",),
    # sites / topology / HA
    (r"site|datacenter|data center|topology|ha|high.?availab|pair|active.standby|single.?node",),
    # hosting / platform
    (r"hosting|platform|on.?prem|aws|azure|cloud|vmware|hyper.?v|bare.?metal|hardware",),
    # firmware / version
    (r"firmware|version|build|release|14\.\d|13\.\d|12\.\d",),
    # network model
    (r"network|vlan|subnet|ip.?address|cidr|routing|interface|one.?arm|inline|gateway",),
    # auth / access
    (r"auth|ldap|radius|saml|sso|kerberos|certificate|ssl offload|tls",),
    # features / services in scope
    (r"feature|service|load.?balanc|content.?switch|gslb|citrix.?gateway|storefront|aaa|waf|appfw",),
    # constraints / non-functional
    (r"constraint|sla|throughput|capacity|compliance|limit|budget|timeline|deadline",),
)

_COVERAGE_TOPICS_NEW_FUNCTIONALITY = (
    # existing environment
    (r"existing|current|live|production|platform|ha|version|site",),
    # what is being added / changed
    (r"adding|changing|new feature|new vserver|new policy|new cert|new service|delta|modify",),
    # dependencies / blast radius
    (r"depend|impact|blast.?radius|affect|rollback|risk",),
    # validation / success criteria
    (r"validat|success.?crit|test|verif|sign.?off|smoke.?test",),
)

_COVERAGE_TOPICS_CHANGE_CONTROL = (
    # change classification
    (r"classif|standard|normal|emergency|expedit",),
    # change summary / business justification
    (r"summary|justif|title|description|reason|business",),
    # affected systems
    (r"affect|ci\b|service|site|system|impact",),
    # maintenance window
    (r"window|schedule|date|time|timezone|duration",),
    # rollback
    (r"rollback|back.?out|revert|undo",),
    # validation
    (r"validat|verif|success|test|post.?change",),
)

# Hard backstop (A3): after this many form submissions, force deliverable regardless of coverage
_DISCOVERY_HARD_BACKSTOP = 9


def _count_covered_topics(
    conversation_text: str,
    topic_patterns: tuple,
) -> int:
    """Return count of topic groups that have at least one pattern matched in conversation."""
    text = (conversation_text or "").lower()
    covered = 0
    for topic_patterns_group in topic_patterns:
        for pattern in topic_patterns_group:
            if re.search(pattern, text):
                covered += 1
                break
    return covered


def architect_discovery_coverage_ready(
    conversation_text: str,
    planning_intent: str | None,
) -> tuple[bool, int, int]:
    """Return (is_ready, covered_count, required_count) based on topic coverage."""
    if planning_intent == "new_functionality":
        topics = _COVERAGE_TOPICS_NEW_FUNCTIONALITY
        required = 3  # must cover 3 of 4 topics
    elif planning_intent == "change_control":
        topics = _COVERAGE_TOPICS_CHANGE_CONTROL
        required = 4  # must cover 4 of 6 topics
    else:
        # new_deployment or unknown — use full deployment topics
        topics = _COVERAGE_TOPICS_NEW_DEPLOYMENT
        required = 5  # must cover 5 of 8 topics
    covered = _count_covered_topics(conversation_text, topics)
    return covered >= required, covered, len(topics)


def architect_discovery_ready_for_deliverable(
    conversation_text: str,
    planning_intent: str | None,
) -> bool:
    """
    Coverage-based readiness (A2): ready when required TOPICS are present in conversation.
    Fast-paths for change-control are preserved.
    Hard backstop (A3): always ready after _DISCOVERY_HARD_BACKSTOP form submissions.
    """
    count = count_planning_form_submissions(conversation_text)

    # A3 hard backstop — escape from endless discovery regardless of intent
    if count >= _DISCOVERY_HARD_BACKSTOP:
        return True

    # Change-control fast paths (unchanged logic — these are quick by design)
    if planning_intent == "change_control":
        if _conversation_started_with_rich_change_control(conversation_text):
            return count >= 1
        if _change_control_intent_declared_upfront(conversation_text):
            return count_unique_planning_form_submissions(conversation_text) >= 3

    # A2 — coverage-based check
    ready, _covered, _total = architect_discovery_coverage_ready(conversation_text, planning_intent)
    return ready


def architect_tools_enabled(
    role: str | None,
    user_message: str,
    *,
    conversation_text: str = "",
) -> bool:
    """Architect uses jpilot-form in markdown during discovery — disable MCP tools to avoid retry loops."""
    if normalize_role(role) != JPilotRole.ARCHITECT:
        return True
    if conversation_has_deliverable(conversation_text):
        return False
    planning_intent = extract_planning_intent(conversation_text, user_message)
    if architect_discovery_ready_for_deliverable(conversation_text, planning_intent):
        if planning_intent == "change_control":
            return True
        return False
    if user_wants_deliverable_now(user_message):
        return True
    return False


def _deliverable_ready_nudge(*, planning_intent: str | None, vendor_id: str = "netscaler") -> str:
    if planning_intent == "change_control":
        marker = "<!-- jpilot-change-control-document -->"
        label = "Change control record"
        outline_hint = (
            "Call search_jpilot_architect_resources once with query 'change control outline' if you need section structure, "
            if vendor_id == "netscaler"
            else "Follow the change control outline from your Architect prompt, "
        )
        tool_hint = f"{outline_hint}then write the document. "
        handoff_hint = "Include **Handoff for Operator** only if the user requested on-appliance execution."
        section_skeleton = ""
    elif planning_intent == "new_functionality":
        marker = "<!-- jpilot-design-document -->"
        label = "Functional change design"
        tool_hint = "Do NOT call any tools — use conversation history only. "
        handoff_hint = ""
        section_skeleton = _NEW_FUNCTIONALITY_SECTION_SKELETON
    else:
        # new_deployment (default) — A4 ordered skeleton
        marker = "<!-- jpilot-design-document -->"
        label = "Design document"
        tool_hint = "Do NOT call any tools — use conversation history only. "
        handoff_hint = ""
        section_skeleton = _NEW_DEPLOYMENT_SECTION_SKELETON

    return (
        f"Discovery is sufficient for this request. {JPILOT_FORM_NOT_A_TOOL_HINT} "
        f"{tool_hint}"
        f"Do NOT output another ```jpilot-form``` or ask more discovery questions. "
        f"Output the complete {label} in one markdown reply. "
        f"First line: {marker}. "
        f"{section_skeleton}"
        f"Include configuration tables and phased implementation steps. "
        f"Mark unknowns **TBD**. {handoff_hint}"
    )


def _should_force_deliverable_output(
    content: str,
    *,
    conversation_text: str,
    user_message: str,
) -> bool:
    if conversation_has_deliverable(conversation_text) or conversation_has_deliverable(content or ""):
        return False
    planning_intent = extract_planning_intent(conversation_text, user_message)
    return architect_discovery_ready_for_deliverable(conversation_text, planning_intent)


def _rich_change_control_initial_nudge() -> str:
    return (
        "The user requested a change-control deliverable (e.g. firmware HA upgrade plan) and already "
        "described the document sections they need. Treat planning_intent as **change_control** — "
        "do NOT show the 'What are you planning?' form. "
        f"{JPILOT_FORM_NOT_A_TOOL_HINT} "
        "Do NOT call any MCP tools. Acknowledge in one sentence, then output exactly ONE ```jpilot-form``` "
        "with ≤6 fields covering only what is still unknown: change classification, current & target "
        "firmware version/build, HA pair count, primary/secondary hostnames or IPs per pair, planned "
        "maintenance window (date, start, end, timezone). Re-use values the user already gave in chat. "
        'Use submitLabel "Continue". No prose after the closing fence.'
    )


def build_architect_session_nudge(
    user_message: str,
    *,
    conversation_text: str = "",
) -> str | None:
    """Proactive system nudge for Architect turns (form submits and rich opening requests)."""
    if conversation_has_deliverable(conversation_text):
        return None
    if count_planning_form_submissions(conversation_text) == 0 and is_rich_change_control_request(user_message):
        return _rich_change_control_initial_nudge()
    return build_discovery_form_submit_nudge(user_message, conversation_text=conversation_text)


def build_discovery_form_submit_nudge(
    user_message: str,
    *,
    conversation_text: str = "",
) -> str | None:
    """Proactive nudge after a planning form submit — next jpilot-form, no search tools."""
    if not is_form_submission(user_message):
        return None
    if conversation_has_deliverable(conversation_text):
        return None
    if user_wants_deliverable_now(user_message):
        return None
    planning_intent = extract_planning_intent(conversation_text, user_message)
    if architect_discovery_ready_for_deliverable(conversation_text, planning_intent):
        return _deliverable_ready_nudge(planning_intent=planning_intent)

    intent_hint = ""
    if planning_intent == "change_control":
        intent_hint = (
            " Next topics: change classification, window, rollback, validation — per change-control branch. "
            "Skip any topic already answered in chat or prior forms — never re-ask change summary or scope."
        )
    elif planning_intent == "new_functionality":
        intent_hint = " Next topics: delta/impact, dependencies, validation — not full greenfield topology."
    elif planning_intent == "new_deployment":
        intent_hint = (
            " Next topics still needed may include: authentication, Citrix Gateway/StoreFront integration, "
            "SSL/certificates, ADM/monitoring, backups, constraints — skip any already captured in chat."
        )
    return (
        "The user submitted a planning discovery form. "
        f"{JPILOT_FORM_NOT_A_TOOL_HINT} "
        "Do NOT call search_jpilot_architect_resources, search_* documentation tools, or any other tools. "
        "Acknowledge their answers in 1–2 sentences, then output exactly one ```jpilot-form``` that groups "
        "several RELATED independent unknown topics together (e.g. Topology + HA + hosting + firmware can be "
        "one form with up to 8 fields; auth + features + constraints is another logical group). "
        "Do NOT split tightly related fields across multiple turns — combine them. "
        f"Skip any topic already answered in chat or prior forms.{intent_hint} "
        'Use submitLabel "Continue". No prose after the closing fence.'
    )


def block_architect_tool_during_discovery(
    tool_name: str,
    *,
    role: str | None,
    user_message: str,
    tool_traces: list | None = None,
    conversation_text: str = "",
) -> str | None:
    """Block all MCP tools during Architect discovery; allow limited search when generating deliverable."""
    if normalize_role(role) != JPilotRole.ARCHITECT:
        return None

    traces = tool_traces or []
    search_count = sum(1 for trace in traces if trace.name in ARCHITECT_SEARCH_TOOL_NAMES)

    if user_wants_deliverable_now(user_message):
        if tool_name in ARCHITECT_SEARCH_TOOL_NAMES and search_count >= 3:
            return (
                "BLOCKED: You already searched architect resources enough times. "
                "Write the full deliverable now using conversation history and prior search results. "
                "Do NOT call more search tools."
            )
        return None

    if architect_discovery_ready_for_deliverable(
        conversation_text,
        extract_planning_intent(conversation_text, user_message),
    ):
        if tool_name in ARCHITECT_SEARCH_TOOL_NAMES and search_count < 1:
            return None
        return (
            f"BLOCKED: Discovery is complete — do not call `{tool_name}` or any other tool. "
            "Write the full deliverable in markdown now (see system instructions)."
        )

    return (
        f"BLOCKED: Architect discovery uses ```jpilot-form``` in chat only — do not call `{tool_name}` "
        "or any MCP tool. Acknowledge the user's form answers, then output the next ```jpilot-form``` "
        'or the final deliverable if enough is known (submitLabel "Continue").'
    )


def block_architect_search_during_discovery(
    tool_name: str,
    *,
    role: str | None,
    user_message: str,
    tool_traces: list | None = None,
    conversation_text: str = "",
) -> str | None:
    """Backward-compatible alias — blocks all architect tools during discovery."""
    return block_architect_tool_during_discovery(
        tool_name,
        role=role,
        user_message=user_message,
        tool_traces=tool_traces,
        conversation_text=conversation_text,
    )


def build_architect_discovery_nudge(
    content: str,
    user_message: str,
    vendor: str | None = None,
    *,
    conversation_text: str = "",
) -> str | None:
    """System retry when Architect discovery violates jpilot-form workflow."""
    vendor_id = (vendor or "netscaler").strip().lower()
    doc_tool = "search_f5_documentation" if vendor_id == "f5" else "search_jpilot_architect_resources"
    if vendor_id == "cisco":
        doc_tool = "search_cisco_cli_reference (syntax appendix only)"

    planning_intent = extract_planning_intent(conversation_text, user_message)
    has_deliverable = conversation_has_deliverable(conversation_text)

    if has_deliverable and is_form_submission(user_message):
        return _revision_apply_nudge(planning_intent=planning_intent)

    if has_deliverable and user_wants_deliverable_revision(user_message):
        return _revision_form_nudge()

    if _should_force_deliverable_output(
        content,
        conversation_text=conversation_text,
        user_message=user_message,
    ):
        return _deliverable_ready_nudge(
            planning_intent=planning_intent,
            vendor_id=vendor_id,
        )

    _, form = parse_input_form(content or "")
    if form is not None:
        return None

    form_submit_nudge = build_discovery_form_submit_nudge(
        user_message,
        conversation_text=conversation_text,
    )
    if form_submit_nudge is not None:
        return form_submit_nudge

    if user_wants_deliverable_now(user_message) and not has_deliverable:
        return _design_now_nudge(
            doc_tool=doc_tool,
            planning_intent=planning_intent,
            vendor_id=vendor_id,
        )

    if not _uses_bad_discovery_prose(content):
        return None

    intent_hint = ""
    if planning_intent == "change_control":
        intent_hint = " User intent is change_control — discovery forms should cover change record topics only."
    elif planning_intent == "new_functionality":
        intent_hint = " User intent is new_functionality — focus on delta/impact forms, not greenfield topology."
    elif planning_intent is None:
        intent_hint = " If planning intent is not yet captured, output the 'What are you planning?' jpilot-form first."

    return (
        "Your last reply violated Architect discovery rules. Do NOT use checklists (✅/❌), "
        'Still missing, Turn N labels, or prose question lists. Do NOT emit tool_calls or XML markup. '
        "Acknowledge any answers the user already gave in chat (1 sentence max), then output exactly one "
        "```jpilot-form``` JSON block that GROUPS related unknown topics together (e.g. topology + HA + hosting "
        "in one form; auth + features + constraints in another) — or the final deliverable if enough "
        f"is known.{intent_hint} No prose after the form fence."
    )


def architect_discovery_should_retry(
    content: str,
    user_message: str,
    role: str | None,
    vendor: str | None = None,
    *,
    conversation_text: str = "",
) -> str | None:
    if normalize_role(role) != JPilotRole.ARCHITECT:
        return None
    cleaned = sanitize_architect_reply(content)
    return build_architect_discovery_nudge(
        cleaned,
        user_message,
        vendor,
        conversation_text=conversation_text,
    )


DISCOVERY_WORKBOOK_TITLE = "# Discovery workbook"


def is_discovery_workbook(design_document_context: str) -> bool:
    text = (design_document_context or "").strip()
    if not text or conversation_has_deliverable(text):
        return False
    return text.startswith(DISCOVERY_WORKBOOK_TITLE)


def append_discovery_workbook_context(
    user_message: str,
    design_document_context: str,
) -> str:
    """Inject accumulated discovery notes from the Document Editor."""
    doc = (design_document_context or "").strip()
    if not doc:
        return user_message
    prefix = (user_message or "").strip()
    nudge = (
        "The user is continuing Architect discovery. The Document Editor contains an accumulated "
        "discovery workbook (below). Treat it as the source of truth for answers already captured. "
        "Do not re-ask topics already covered unless the user contradicts the workbook. "
        "After acknowledging new input, output the next ```jpilot-form``` or the formal deliverable "
        "when discovery is sufficient."
    )
    block = f"\n\n--- Discovery workbook ---\n{doc}\n--- end ---\n\n{nudge}"
    return f"{prefix}{block}" if prefix else block.strip()


def append_design_document_revision_context(
    user_message: str,
    design_document_context: str,
    *,
    include_revision: bool = False,
) -> str:
    """Inject the panel document so Architect revises the user's current draft."""
    doc = (design_document_context or "").strip()
    if not doc:
        return user_message
    prefix = (user_message or "").strip()
    lead = (
        "The user clicked Include my edits in the JPilot design panel. "
        if include_revision
        else "The user is revising the design document shown in the JPilot design panel. "
    )
    nudge = (
        f"{lead}"
        "Apply their request to the FULL document below (they may have edited markdown in the panel). "
        "Keep the correct deliverable HTML comment marker on the first line. "
        "Output the complete revised document — not a partial diff."
    )
    block = f"\n\n--- Current design document ---\n{doc}\n--- end ---\n\n{nudge}"
    return f"{prefix}{block}" if prefix else block.strip()


def append_architect_panel_context(
    user_message: str,
    design_document_context: str,
    *,
    include_revision: bool = False,
) -> str:
    """Route panel context to discovery workbook or deliverable revision prompts."""
    doc = (design_document_context or "").strip()
    if not doc:
        return user_message
    if include_revision or conversation_has_deliverable(doc):
        return append_design_document_revision_context(
            user_message,
            design_document_context,
            include_revision=include_revision,
        )
    if is_discovery_workbook(doc):
        return append_discovery_workbook_context(user_message, design_document_context)
    return append_design_document_revision_context(
        user_message,
        design_document_context,
        include_revision=False,
    )
