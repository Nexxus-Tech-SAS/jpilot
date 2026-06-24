import re
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.services.encryption_service import decrypt_value, encrypt_value
from app.services.copilot_orchestration import (
    DEFAULT_NO_PROGRESS_FLOOR,
    DEFAULT_NO_PROGRESS_WINDOW,
    DEFAULT_PER_TOOL_FAILURE_LIMIT,
    DEFAULT_REPEATED_FAILED_CALL_LIMIT,
)
from app.services.orchestration_presets import (
    DEFAULT_ORCHESTRATION_MODE,
    ORCHESTRATION_PRESETS,
    infer_orchestration_mode,
)

SETTINGS_ID = "default"

from app.services.vendor_doc_domains import (
    LOCKED_DOMAINS,
    all_locked_domain_groups,
    get_allowed_domains_for_vendor,
)

_DOMAIN_RE = re.compile(r"^[a-z0-9.-]+\.[a-z]{2,}$")


class CopilotPlatformSettingsUpdate(BaseModel):
    allowWebSearch: bool | None = None
    braveSearchApiKey: str | None = None
    extraDomains: list[str] | None = None
    maxToolIterations: int | None = None
    maxToolContinuationPhases: int | None = None
    longTaskToolThreshold: int | None = None
    promptBeforeLongTasks: bool | None = None
    orchestrationMode: str | None = None
    # Loop-breakers (stuck detection) — orthogonal to the orchestration preset.
    loopBreakersEnabled: bool | None = None
    repeatedFailedCallLimit: int | None = None
    perToolFailureLimit: int | None = None
    noProgressWindow: int | None = None
    noProgressFloor: int | None = None


class CopilotPlatformSettingsResponse(BaseModel):
    allowWebSearch: bool = False
    hasBraveSearchApiKey: bool = False
    lockedDomains: list[str] = []
    vendorLockedDomains: dict[str, list[str]] = {}
    extraDomains: list[str] = []
    maxToolIterations: int = 20
    maxToolContinuationPhases: int = 3
    longTaskToolThreshold: int = 8
    promptBeforeLongTasks: bool = True
    orchestrationMode: str = DEFAULT_ORCHESTRATION_MODE
    loopBreakersEnabled: bool = True
    repeatedFailedCallLimit: int = DEFAULT_REPEATED_FAILED_CALL_LIMIT
    perToolFailureLimit: int = DEFAULT_PER_TOOL_FAILURE_LIMIT
    noProgressWindow: int = DEFAULT_NO_PROGRESS_WINDOW
    noProgressFloor: int = DEFAULT_NO_PROGRESS_FLOOR


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def default_document() -> dict:
    return {
        "_id": SETTINGS_ID,
        "allowWebSearch": False,
        "encryptedBraveSearchApiKey": encrypt_value(""),
        "extraDomains": [],
        "orchestrationMode": DEFAULT_ORCHESTRATION_MODE,
        **ORCHESTRATION_PRESETS[DEFAULT_ORCHESTRATION_MODE],
        "updatedAt": utc_now(),
    }


def _sanitize_domains(domains: list[str]) -> list[str]:
    """Normalize user-supplied domains; drop invalid, duplicate, and locked ones."""
    cleaned: list[str] = []
    for raw in domains or []:
        d = (raw or "").strip().lower()
        d = re.sub(r"^https?://", "", d)
        d = d.split("/")[0].strip().strip(".")
        if not d or not _DOMAIN_RE.match(d):
            continue
        if d in LOCKED_DOMAINS or d in cleaned:
            continue
        cleaned.append(d)
    return cleaned


async def ensure_default_settings(db: AsyncIOMotorDatabase) -> None:
    existing = await db.copilotPlatformSettings.find_one({"_id": SETTINGS_ID})
    if existing is None:
        await db.copilotPlatformSettings.insert_one(default_document())


async def get_platform_settings(db: AsyncIOMotorDatabase) -> CopilotPlatformSettingsResponse:
    await ensure_default_settings(db)
    document = await db.copilotPlatformSettings.find_one({"_id": SETTINGS_ID}) or {}
    api_key = decrypt_value(document.get("encryptedBraveSearchApiKey", ""))
    return CopilotPlatformSettingsResponse(
        allowWebSearch=document.get("allowWebSearch", False),
        hasBraveSearchApiKey=bool(api_key.strip()),
        lockedDomains=list(LOCKED_DOMAINS),
        vendorLockedDomains=all_locked_domain_groups(),
        extraDomains=list(document.get("extraDomains", [])),
        maxToolIterations=int(document.get("maxToolIterations", 20)),
        maxToolContinuationPhases=int(document.get("maxToolContinuationPhases", 3)),
        longTaskToolThreshold=int(document.get("longTaskToolThreshold", 8)),
        promptBeforeLongTasks=bool(document.get("promptBeforeLongTasks", True)),
        orchestrationMode=infer_orchestration_mode(document),
        loopBreakersEnabled=bool(document.get("loopBreakersEnabled", True)),
        repeatedFailedCallLimit=int(
            document.get("repeatedFailedCallLimit", DEFAULT_REPEATED_FAILED_CALL_LIMIT)
        ),
        perToolFailureLimit=int(document.get("perToolFailureLimit", DEFAULT_PER_TOOL_FAILURE_LIMIT)),
        noProgressWindow=int(document.get("noProgressWindow", DEFAULT_NO_PROGRESS_WINDOW)),
        noProgressFloor=int(document.get("noProgressFloor", DEFAULT_NO_PROGRESS_FLOOR)),
    )


async def get_brave_api_key(db: AsyncIOMotorDatabase) -> str:
    await ensure_default_settings(db)
    document = await db.copilotPlatformSettings.find_one({"_id": SETTINGS_ID}) or {}
    return decrypt_value(document.get("encryptedBraveSearchApiKey", "")).strip()


async def get_allowed_domains(db: AsyncIOMotorDatabase, vendor: str | None = "netscaler") -> list[str]:
    return await get_allowed_domains_for_vendor(db, vendor)


async def is_web_search_enabled(db: AsyncIOMotorDatabase) -> bool:
    settings = await get_platform_settings(db)
    return settings.allowWebSearch and settings.hasBraveSearchApiKey


async def get_web_search_runtime(db: AsyncIOMotorDatabase) -> dict:
    """Everything the chat needs to run a domain-restricted web search, or disabled."""
    settings = await get_platform_settings(db)
    if not (settings.allowWebSearch and settings.hasBraveSearchApiKey):
        return {"enabled": False}
    api_key = await get_brave_api_key(db)
    if not api_key:
        return {"enabled": False}
    return {
        "enabled": True,
        "apiKey": api_key,
        "allowedDomains": await get_allowed_domains(db),
    }


async def update_platform_settings(
    db: AsyncIOMotorDatabase,
    payload: CopilotPlatformSettingsUpdate,
) -> CopilotPlatformSettingsResponse:
    await ensure_default_settings(db)
    update_data: dict = {
        "updatedAt": utc_now(),
    }

    if payload.allowWebSearch is not None:
        update_data["allowWebSearch"] = payload.allowWebSearch

    if payload.braveSearchApiKey is not None and payload.braveSearchApiKey.strip():
        update_data["encryptedBraveSearchApiKey"] = encrypt_value(payload.braveSearchApiKey.strip())

    if payload.extraDomains is not None:
        update_data["extraDomains"] = _sanitize_domains(payload.extraDomains)

    if payload.orchestrationMode is not None:
        mode = payload.orchestrationMode.strip().lower()
        if mode in ORCHESTRATION_PRESETS:
            update_data["orchestrationMode"] = mode
            update_data.update(ORCHESTRATION_PRESETS[mode])
        elif mode == "custom":
            update_data["orchestrationMode"] = "custom"

    apply_custom_orchestration = payload.orchestrationMode in (None, "custom")
    if apply_custom_orchestration and payload.maxToolIterations is not None:
        update_data["maxToolIterations"] = max(5, min(int(payload.maxToolIterations), 60))
    if apply_custom_orchestration and payload.maxToolContinuationPhases is not None:
        update_data["maxToolContinuationPhases"] = max(0, min(int(payload.maxToolContinuationPhases), 8))
    if apply_custom_orchestration and payload.longTaskToolThreshold is not None:
        update_data["longTaskToolThreshold"] = max(3, min(int(payload.longTaskToolThreshold), 40))
    if apply_custom_orchestration and payload.promptBeforeLongTasks is not None:
        update_data["promptBeforeLongTasks"] = bool(payload.promptBeforeLongTasks)

    # Loop-breakers (stuck detection) — independent of the orchestration preset.
    if payload.loopBreakersEnabled is not None:
        update_data["loopBreakersEnabled"] = bool(payload.loopBreakersEnabled)
    if payload.repeatedFailedCallLimit is not None:
        update_data["repeatedFailedCallLimit"] = max(1, min(int(payload.repeatedFailedCallLimit), 10))
    if payload.perToolFailureLimit is not None:
        update_data["perToolFailureLimit"] = max(1, min(int(payload.perToolFailureLimit), 15))
    if payload.noProgressWindow is not None:
        update_data["noProgressWindow"] = max(2, min(int(payload.noProgressWindow), 30))
    if payload.noProgressFloor is not None:
        update_data["noProgressFloor"] = max(2, min(int(payload.noProgressFloor), 60))

    await db.copilotPlatformSettings.update_one({"_id": SETTINGS_ID}, {"$set": update_data}, upsert=True)
    return await get_platform_settings(db)
