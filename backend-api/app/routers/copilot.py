import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db
from app.schemas.test import TestConnectionResponse
from app.services.brave_search_service import test_brave_search
from app.services.copilot_platform_service import (
    CopilotPlatformSettingsResponse,
    CopilotPlatformSettingsUpdate,
    get_brave_api_key,
    get_platform_settings,
    update_platform_settings,
)
from app.services.copilot_orchestrator import (
    ChatCancelledError,
    get_default_provider,
    resolve_chat_provider,
    run_copilot_chat,
)
from app.services.ai_provider_errors import (
    AiProviderError,
    build_gateway_timeout_detail,
    enrich_ai_provider_error,
    maybe_parse_ai_provider_error,
)
from app.schemas.calibration import (
    CalibrationCatalogResponse,
    CalibrationCatalogSkill,
    CalibrationInstallResponse,
    CalibrationInstalledBlueprint,
    CalibrationSkillSummary,
    CalibrationSyncResponse,
    CalibrationUninstallResponse,
    CatalogItem,
    KnowledgePackImportResponse,
    KnowledgePackPinRequest,
    KnowledgePackPinResponse,
    KnowledgePackRollbackResponse,
    KnowledgePackScheduleRequest,
    KnowledgePackScheduleResponse,
    KnowledgePackStatusResponse,
    KnowledgePackSummary,
    SyncItem,
)
from app.schemas.calibration_feedback import CalibrationFeedbackRequest, CalibrationFeedbackResponse
from app.schemas.copilot import (
    ChatRequest,
    ChatResponse,
    CopilotApplianceItem,
    CopilotConnectRequest,
    CopilotConnectResponse,
    CopilotRoleResponse,
    CopilotSettings,
    CopilotStatusResponse,
)
from app.config import settings
from app.services.calibration_sync_service import (
    CalibrationSyncError,
    fetch_calibration_catalog,
    install_calibration_knowledge_pack,
    install_calibration_persona,
    install_calibration_skill,
    list_installed_skills,
    sync_calibrations_from_studio,
    uninstall_calibration_knowledge_pack,
    uninstall_calibration_persona,
    uninstall_calibration_skill,
)
from app.services.knowledge_pack_service import (
    KnowledgePackError,
    get_knowledge_pack_state,
    install_knowledge_pack_bytes,
    pin_knowledge_pack_version,
    rollback_knowledge_pack,
    update_knowledge_pack_schedule,
)
from app.services.skill_feedback_service import CalibrationFeedbackError, submit_calibration_feedback
from app.services.copilot_roles import (
    get_role_catalog,
    list_installed_personas,
    normalize_role,
    resolve_custom_persona,
    role_requires_appliance,
)
from app.schemas.model_usage import ModelUsageDashboardResponse, UsageLimitsUpdate
from app.services.model_usage_service import get_usage_dashboard, update_usage_limits
from app.services.copilot_streaming import stream_copilot_chat_events
from app.services.copilot_appliance_service import connect_appliance, list_copilot_appliances

router = APIRouter(prefix="/copilot", tags=["copilot"])

DEFAULT_SETTINGS = CopilotSettings()


async def _validate_copilot_chat_request(
    payload: ChatRequest,
    db: AsyncIOMotorDatabase,
) -> tuple:
    if not payload.message.strip() and not payload.attachments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message or attachments are required",
        )

    # Resolve optional custom persona — if found, its baseRole drives tooling.
    custom_persona = await resolve_custom_persona(db, payload.personaId)
    effective_role_str = custom_persona.baseRole if custom_persona else payload.role

    chat_role = normalize_role(effective_role_str)
    appliance_name = (payload.applianceName or "").strip()
    if role_requires_appliance(chat_role) and not appliance_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select and connect to an appliance for Operator and Analyst roles",
        )
    if role_requires_appliance(chat_role) and appliance_name:
        from app.models.appliance import is_netscaler_appliance

        appliance = await db.appliances.find_one({"name": appliance_name})
        if appliance is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Appliance '{appliance_name}' not found in inventory",
            )
        if not is_netscaler_appliance(appliance):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operator and Analyst roles require a NetScaler appliance for now",
            )
    return chat_role, appliance_name, custom_persona


@router.get("/settings", response_model=CopilotSettings)
async def get_copilot_settings() -> CopilotSettings:
    return DEFAULT_SETTINGS


@router.get("/roles", response_model=list[CopilotRoleResponse])
async def list_copilot_roles(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[CopilotRoleResponse]:
    base_roles = [CopilotRoleResponse(**item) for item in get_role_catalog()]
    custom_personas = await list_installed_personas(db)
    persona_responses = [CopilotRoleResponse(**p) for p in custom_personas]
    return base_roles + persona_responses


@router.get("/platform-settings", response_model=CopilotPlatformSettingsResponse)
async def read_platform_settings(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CopilotPlatformSettingsResponse:
    return await get_platform_settings(db)


@router.put("/platform-settings", response_model=CopilotPlatformSettingsResponse)
async def save_platform_settings(
    payload: CopilotPlatformSettingsUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CopilotPlatformSettingsResponse:
    if payload.allowWebSearch is True and payload.braveSearchApiKey is None:
        existing = await get_platform_settings(db)
        if not existing.hasBraveSearchApiKey:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Brave Search API key is required when web search is enabled",
            )
    return await update_platform_settings(db, payload)


@router.post("/platform-settings/test", response_model=TestConnectionResponse)
async def test_platform_search(
    payload: CopilotPlatformSettingsUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TestConnectionResponse:
    api_key = (payload.braveSearchApiKey or "").strip()
    if not api_key:
        api_key = await get_brave_api_key(db)
    if not api_key:
        return TestConnectionResponse(success=False, message="Brave Search API key is not configured")
    success, message = await test_brave_search(api_key)
    if success:
        from app.services.model_usage_service import record_brave_search_usage

        await record_brave_search_usage(db, queries=1)
    return TestConnectionResponse(success=success, message=message)


@router.get("/usage-dashboard", response_model=ModelUsageDashboardResponse)
async def read_usage_dashboard(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ModelUsageDashboardResponse:
    return await get_usage_dashboard(db)


@router.put("/usage-limits", response_model=ModelUsageDashboardResponse)
async def save_usage_limits(
    payload: UsageLimitsUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ModelUsageDashboardResponse:
    await update_usage_limits(db, payload)
    return await get_usage_dashboard(db)


@router.get("/status", response_model=CopilotStatusResponse)
async def copilot_status(db: AsyncIOMotorDatabase = Depends(get_db)) -> CopilotStatusResponse:
    provider = await get_default_provider(db)
    if provider is None:
        return CopilotStatusResponse(
            ready=False,
            message="No enabled AI provider found. Configure one and set it as default.",
            settings=DEFAULT_SETTINGS,
        )

    return CopilotStatusResponse(
        ready=True,
        providerName=provider["providerName"],
        providerType=provider["providerType"],
        model=provider["model"],
        message="Copilot is ready",
        settings=DEFAULT_SETTINGS,
    )


@router.get("/appliances", response_model=list[CopilotApplianceItem])
async def copilot_appliances(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[dict]:
    return await list_copilot_appliances(db)


@router.post("/connect", response_model=CopilotConnectResponse)
async def copilot_connect(
    payload: CopilotConnectRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    appliance_name = payload.applianceName.strip()
    if not appliance_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="applianceName is required")
    try:
        return await connect_appliance(db, appliance_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Next-Gen API login failed: {exc}",
        ) from exc


@router.post("/chat", response_model=ChatResponse)
async def copilot_chat(
    payload: ChatRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ChatResponse:
    settings = payload.settings or DEFAULT_SETTINGS
    chat_role, appliance_name, custom_persona = await _validate_copilot_chat_request(payload, db)
    provider = await resolve_chat_provider(db, payload.providerId, role=chat_role.value)

    try:
        history = [item.model_dump() for item in payload.history]
        return await run_copilot_chat(
            db,
            payload.message.strip(),
            history,
            attachments=payload.attachments,
            settings=settings,
            appliance_name=appliance_name,
            provider_id=payload.providerId,
            web_search=payload.webSearch,
            role=chat_role.value,
            request=request,
            deployment_continuation=payload.deploymentContinuation,
            long_task_approved=payload.longTaskApproved,
            persona_system_prompt=custom_persona.systemPrompt if custom_persona else None,
        )
    except ChatCancelledError as exc:
        raise HTTPException(
            status_code=499,
            detail="Chat request cancelled",
        ) from exc
    except AiProviderError as exc:
        if provider and not exc.provider_name:
            exc.provider_name = provider.get("providerName", "")
        detail = await enrich_ai_provider_error(db, exc, payload.providerId)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        ) from exc
    except ValueError as exc:
        if isinstance(exc, AiProviderError):
            detail = await enrich_ai_provider_error(db, exc, payload.providerId)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=build_gateway_timeout_detail(),
        ) from exc
    except Exception as exc:
        provider_type = provider.get("providerType", "") if provider else ""
        model = provider.get("model", "") if provider else ""
        provider_name = provider.get("providerName", "") if provider else ""
        parsed = maybe_parse_ai_provider_error(
            str(exc),
            provider_type=provider_type,
            model=model,
            provider_name=provider_name,
        )
        if parsed is not None:
            detail = await enrich_ai_provider_error(db, parsed, payload.providerId)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Copilot request failed: {exc}",
        ) from exc


@router.get("/calibrations", response_model=list[CalibrationSkillSummary])
async def list_calibrations() -> list[CalibrationSkillSummary]:
    return [CalibrationSkillSummary(**row) for row in list_installed_skills()]


@router.get("/calibrations/catalog", response_model=CalibrationCatalogResponse)
async def get_calibration_catalog(
    vendor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CalibrationCatalogResponse:
    try:
        result = await fetch_calibration_catalog(db, vendor=vendor)
    except CalibrationSyncError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return CalibrationCatalogResponse(
        catalogUrl=result.catalog_url,
        licenseType=result.license_type,
        localLicenseType=result.local_license_type,
        licenseEntitlementMismatch=result.license_entitlement_mismatch,
        studioAuthMissing=result.studio_auth_missing,
        hasLicenseCode=result.has_license_code,
        appFingerprint=result.app_fingerprint,
        clientId=result.client_id,
        entitlements=result.entitlements,
        skills=[CalibrationCatalogSkill(**skill) for skill in result.skills],
        items=[CatalogItem(**item) for item in (result.items or [])],
        installedBlueprints=[CalibrationInstalledBlueprint(**row) for row in result.installed_blueprints],
    )


@router.post("/calibrations/sync", response_model=CalibrationSyncResponse)
async def sync_calibrations(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CalibrationSyncResponse:
    try:
        result = await sync_calibrations_from_studio(db)
    except CalibrationSyncError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    pack_payload = result.knowledge_pack or {}
    knowledge_pack_model = None
    if pack_payload:
        knowledge_pack_model = KnowledgePackSummary(
            id=str(pack_payload.get("id") or ""),
            version=str(pack_payload.get("version") or ""),
            contentHash=pack_payload.get("contentHash"),
            packageSignature=pack_payload.get("packageSignature"),
            bundleUrl=pack_payload.get("bundleUrl"),
            manifestUrl=pack_payload.get("manifestUrl"),
        )

    entitled_items = [
        SyncItem(
            type=str(item.get("type") or "skill"),
            id=str(item.get("id") or ""),
            version=str(item.get("version") or ""),
            packageSignature=str(item.get("packageSignature") or ""),
            bundleUrl=str(item.get("bundleUrl") or ""),
        )
        for item in (result.entitled_items or [])
        if item.get("id")
    ]

    return CalibrationSyncResponse(
        installed=result.installed,
        updated=result.updated,
        removed=result.removed,
        skills=result.skills,
        entitledItems=entitled_items,
        personasInstalled=result.personas_installed,
        knowledgePack=knowledge_pack_model,
        knowledgePackUpdated=result.knowledge_pack_updated,
        knowledgePackSkipped=result.knowledge_pack_skipped,
        stackProfile=result.stack_profile,
        legacySkills=result.legacy_skills or [],
        message=_build_sync_message(result),
    )


def _build_sync_message(result) -> str:
    parts: list[str] = []
    if result.knowledge_pack_updated:
        pack = result.knowledge_pack or {}
        parts.append(
            f"Knowledge pack {pack.get('id') or 'unknown'} ({pack.get('version') or '?'}) updated."
        )
    elif result.knowledge_pack_skipped:
        parts.append("Knowledge pack already up to date.")
    if result.updated or result.installed:
        parts.append(
            f"Synced {result.updated} updated and {result.installed} unchanged entitled skill(s) from Calibration Studio."
        )
    if getattr(result, "personas_installed", 0):
        parts.append(f"Installed {result.personas_installed} entitled persona(s).")
    if not parts:
        return "Calibration sync completed."
    return " ".join(parts)


@router.get("/knowledge-pack", response_model=KnowledgePackStatusResponse)
async def get_knowledge_pack_status(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> KnowledgePackStatusResponse:
    state = await get_knowledge_pack_state(db)
    legacy_count = len(list_installed_skills(include_legacy_only=True))
    return KnowledgePackStatusResponse(
        **state,
        legacySkillCount=legacy_count,
        message="Knowledge pack status loaded.",
    )


@router.post("/knowledge-pack/import", response_model=KnowledgePackImportResponse)
async def import_knowledge_pack(
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> KnowledgePackImportResponse:
    if not settings.calibration_sync_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Calibration sync is disabled.")
    package_bytes = await file.read()
    if not package_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty knowledge pack file.")
    try:
        result = await install_knowledge_pack_bytes(db, package_bytes)
    except KnowledgePackError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return KnowledgePackImportResponse(
        packId=result["packId"],
        version=result["version"],
        contentHash=result.get("contentHash"),
        blueprintCount=result.get("blueprintCount", 0),
        path=result.get("path", ""),
        message=f"Imported knowledge pack {result['packId']} ({result['version']}).",
    )


@router.post("/knowledge-pack/rollback", response_model=KnowledgePackRollbackResponse)
async def rollback_knowledge_pack_route(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> KnowledgePackRollbackResponse:
    try:
        result = await rollback_knowledge_pack(db)
    except KnowledgePackError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return KnowledgePackRollbackResponse(
        packId=result["packId"],
        version=result["version"],
        previousVersion=result.get("previousVersion"),
        blueprintCount=result.get("blueprintCount", 0),
        message=f"Rolled back to knowledge pack {result['packId']} ({result['version']}).",
    )


@router.put("/knowledge-pack/pin", response_model=KnowledgePackPinResponse)
async def pin_knowledge_pack_route(
    payload: KnowledgePackPinRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> KnowledgePackPinResponse:
    try:
        result = await pin_knowledge_pack_version(db, payload.version)
    except KnowledgePackError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    pinned = result.get("pinnedVersion")
    action = f"Pinned to {pinned}" if pinned else "Pin cleared"
    return KnowledgePackPinResponse(
        packId=result["packId"],
        pinnedVersion=pinned,
        currentVersion=result.get("currentVersion"),
        message=f"{action} for knowledge pack {result['packId']}.",
    )


@router.put("/knowledge-pack/schedule", response_model=KnowledgePackScheduleResponse)
async def update_knowledge_pack_schedule_route(
    payload: KnowledgePackScheduleRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> KnowledgePackScheduleResponse:
    state = await update_knowledge_pack_schedule(db, enabled=payload.enabled, hours=payload.hours)
    return KnowledgePackScheduleResponse(
        syncScheduleEnabled=bool(state.get("syncScheduleEnabled", True)),
        syncScheduleHours=int(state.get("syncScheduleHours") or 6),
        message="Knowledge pack sync schedule updated.",
    )


@router.post("/calibrations/{skill_id}/install", response_model=CalibrationInstallResponse)
async def install_calibration(
    skill_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CalibrationInstallResponse:
    try:
        result = await install_calibration_skill(db, skill_id)
    except CalibrationSyncError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    action = "updated" if result.updated else "installed"
    return CalibrationInstallResponse(
        skillId=result.skill_id,
        version=result.version,
        label=result.label,
        vendor=result.vendor,
        path=result.path,
        updated=result.updated,
        message=f"Skill {result.label} ({result.version}) {action}.",
    )


@router.post("/calibrations/personas/{persona_id}/install", response_model=CalibrationInstallResponse)
async def install_calibration_persona_route(
    persona_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CalibrationInstallResponse:
    try:
        result = await install_calibration_persona(db, persona_id)
    except CalibrationSyncError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    action = "updated" if result.updated else "installed"
    skill_note = ""
    if result.installed_skill_refs:
        skill_note = f" Included {len(result.installed_skill_refs)} referenced skill(s)."
    if result.skipped_skill_refs:
        skill_note += f" {len(result.skipped_skill_refs)} referenced skill(s) not entitled."
    return CalibrationInstallResponse(
        skillId=result.persona_id,
        version=result.version,
        label=result.label,
        vendor=result.vendor,
        path=result.path,
        updated=result.updated,
        message=f"Persona {result.label} ({result.version}) {action}.{skill_note}",
    )


@router.post("/calibrations/knowledge-packs/{pack_id}/install", response_model=CalibrationInstallResponse)
async def install_calibration_knowledge_pack_route(
    pack_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CalibrationInstallResponse:
    try:
        result = await install_calibration_knowledge_pack(db, pack_id)
    except CalibrationSyncError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    action = "skipped (already current)" if result.get("skipped") else ("updated" if result.get("updated") else "installed")
    return CalibrationInstallResponse(
        skillId=str(result.get("packId") or pack_id),
        version=str(result.get("version") or ""),
        label=str(result.get("packId") or pack_id),
        vendor=None,
        path="",
        updated=bool(result.get("updated")),
        message=f"Knowledge pack {result.get('packId') or pack_id} ({result.get('version') or '?'}) {action}.",
    )


@router.delete("/calibrations/{skill_id}", response_model=CalibrationUninstallResponse)
async def uninstall_calibration(
    skill_id: str,
    version: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CalibrationUninstallResponse:
    try:
        result = await uninstall_calibration_skill(db, skill_id, version=version)
    except CalibrationSyncError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    removed = ", ".join(result.removed_versions) if result.removed_versions else "none"
    return CalibrationUninstallResponse(
        skillId=result.skill_id,
        label=result.label,
        removedVersions=result.removed_versions,
        message=f"Removed {result.label} ({removed}) from this installation.",
    )


@router.delete("/calibrations/personas/{persona_id}", response_model=CalibrationUninstallResponse)
async def uninstall_calibration_persona_route(
    persona_id: str,
    version: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CalibrationUninstallResponse:
    try:
        result = await uninstall_calibration_persona(db, persona_id, version=version)
    except CalibrationSyncError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    removed = ", ".join(result.removed_versions) if result.removed_versions else "none"
    return CalibrationUninstallResponse(
        skillId=result.skill_id,
        label=result.label,
        removedVersions=result.removed_versions,
        message=f"Removed persona {result.label} ({removed}) from this installation.",
    )


@router.delete("/calibrations/knowledge-packs/{pack_id}", response_model=CalibrationUninstallResponse)
async def uninstall_calibration_knowledge_pack_route(
    pack_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CalibrationUninstallResponse:
    try:
        result = await uninstall_calibration_knowledge_pack(db, pack_id)
    except CalibrationSyncError as exc:
        raise HTTPException(status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    removed = ", ".join(result.removed_versions) if result.removed_versions else "none"
    return CalibrationUninstallResponse(
        skillId=result.skill_id,
        label=result.label,
        removedVersions=result.removed_versions,
        message=f"Removed knowledge pack {result.label} ({removed}) from this installation.",
    )


@router.get("/calibration-feedback/status", response_model=CalibrationFeedbackResponse)
async def calibration_feedback_status() -> CalibrationFeedbackResponse:
    if not settings.calibration_feedback_enabled:
        return CalibrationFeedbackResponse(
            status="disabled",
            message="Calibration feedback is disabled on this installation.",
        )
    return CalibrationFeedbackResponse(
        status="ready",
        message="Calibration feedback can be sent to Stack Calibration Studio.",
        calibrationUrl=settings.nexxus_calibration_base_url.rstrip("/"),
    )


@router.post("/calibration-feedback", response_model=CalibrationFeedbackResponse)
async def submit_calibration_feedback_route(
    payload: CalibrationFeedbackRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CalibrationFeedbackResponse:
    if not payload.session.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session.messages is required",
        )
    try:
        result = await submit_calibration_feedback(db, payload)
    except CalibrationFeedbackError as exc:
        code = exc.status_code or status.HTTP_502_BAD_GATEWAY
        if "disabled" in str(exc).lower():
            code = status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(status_code=code, detail=str(exc)) from exc

    return CalibrationFeedbackResponse(
        status=str(result.payload.get("status") or "accepted"),
        message=str(result.payload.get("message") or "Feedback sent to Calibration Studio."),
        feedbackId=result.feedback_id,
        calibrationUrl=result.payload.get("calibrationUrl"),
    )


@router.post("/chat/stream")
async def copilot_chat_stream(
    payload: ChatRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> StreamingResponse:
    chat_role, _appliance_name, custom_persona = await _validate_copilot_chat_request(payload, db)
    # When a custom persona is active, override the role in the payload so
    # the streaming service uses the persona's baseRole for tooling.
    if custom_persona:
        payload = payload.model_copy(update={"role": custom_persona.baseRole})
    return StreamingResponse(
        stream_copilot_chat_events(
            db=db,
            payload=payload,
            request=request,
            persona_system_prompt=custom_persona.systemPrompt if custom_persona else None,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
