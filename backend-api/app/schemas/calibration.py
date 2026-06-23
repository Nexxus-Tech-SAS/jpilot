from pydantic import BaseModel, Field


class CalibrationSkillSummary(BaseModel):
    skillId: str
    version: str
    label: str = ""
    vendor: str | None = None
    path: str = ""
    source: str = ""
    roles: list[str] = Field(default_factory=list)
    description: str = ""
    domains: list[str] = Field(default_factory=list)


class KnowledgePackSummary(BaseModel):
    id: str = ""
    version: str = ""
    contentHash: str | None = None
    packageSignature: str | None = None
    bundleUrl: str | None = None
    manifestUrl: str | None = None


class SyncItem(BaseModel):
    """Type-tagged entitled item returned by POST /calibrations/sync (frozen contract)."""

    type: str = "skill"  # "skill" | "persona" | "knowledge_pack"
    id: str
    version: str = ""
    packageSignature: str = ""
    bundleUrl: str = ""


class CalibrationSyncResponse(BaseModel):
    installed: int
    updated: int
    removed: int
    skills: list[dict] = Field(default_factory=list)
    entitledItems: list[SyncItem] = Field(default_factory=list)
    personasInstalled: int = 0
    message: str = ""
    knowledgePack: KnowledgePackSummary | None = None
    knowledgePackUpdated: bool = False
    knowledgePackSkipped: bool = False
    stackProfile: dict | None = None
    legacySkills: list[dict] = Field(default_factory=list)


class CalibrationCatalogSkill(BaseModel):
    id: str
    version: str
    label: str = ""
    vendor: str = ""
    domains: list[str] = Field(default_factory=list)
    description: str = ""
    minTier: str = "free"
    globalFreeSkill: bool = False
    installable: bool = False
    ineligibleReason: str | None = None
    bundleUrl: str = ""
    entitledVersion: str | None = None
    entitledViaSync: bool = False
    syncBundleUrl: str = ""


class CatalogItem(BaseModel):
    """Type-tagged catalog entry from POST /calibrations/catalog ``items[]`` (frozen contract).

    Skills, personas and knowledge packs all flow through this shape. License gating
    (``installable`` + ``ineligibleReason``) is computed by scstudio uniformly via
    ``minTier`` + entitlements; jpilot mirrors the result and re-enriches via sync.
    """

    type: str = "skill"  # "skill" | "persona" | "knowledge_pack"
    id: str
    version: str = ""
    label: str = ""
    vendor: str = ""
    domains: list[str] = Field(default_factory=list)
    description: str = ""
    minTier: str = "free"
    globalFree: bool = False
    installable: bool = False
    ineligibleReason: str | None = None
    bundleUrl: str = ""
    meta: dict = Field(default_factory=dict)
    # Sync-enrichment mirror (download source of truth, keyed by (type, id)).
    entitledVersion: str | None = None
    entitledViaSync: bool = False
    syncBundleUrl: str = ""


class CalibrationInstalledBlueprint(BaseModel):
    skillId: str
    label: str = ""
    vendor: str | None = None
    installedVersion: str | None = None
    catalogVersion: str | None = None
    installed: bool = False
    updateAvailable: bool = False


class CalibrationInstallResponse(BaseModel):
    skillId: str
    version: str
    label: str = ""
    vendor: str | None = None
    path: str = ""
    updated: bool = False
    message: str = ""


class CalibrationUninstallResponse(BaseModel):
    skillId: str
    label: str = ""
    removedVersions: list[str] = Field(default_factory=list)
    message: str = ""


class CalibrationCatalogResponse(BaseModel):
    catalogUrl: str = ""
    licenseType: str = "free"
    localLicenseType: str | None = None
    licenseEntitlementMismatch: bool = False
    studioAuthMissing: bool = False
    hasLicenseCode: bool = False
    appFingerprint: str | None = None
    clientId: str | None = None
    entitlements: list[str] = Field(default_factory=list)
    skills: list[CalibrationCatalogSkill] = Field(default_factory=list)
    items: list[CatalogItem] = Field(default_factory=list)
    installedBlueprints: list[CalibrationInstalledBlueprint] = Field(default_factory=list)


class KnowledgePackStatusResponse(BaseModel):
    active: bool = False
    packId: str | None = None
    version: str | None = None
    previousVersion: str | None = None
    pinnedVersion: str | None = None
    contentHash: str | None = None
    publishedAt: str | None = None
    blueprintCount: int = 0
    lastSyncAt: str | None = None
    syncScheduleHours: int = 6
    syncScheduleEnabled: bool = True
    path: str = ""
    legacySkillCount: int = 0
    message: str = ""


class KnowledgePackImportResponse(BaseModel):
    packId: str
    version: str
    contentHash: str | None = None
    blueprintCount: int = 0
    path: str = ""
    message: str = ""


class KnowledgePackRollbackResponse(BaseModel):
    packId: str
    version: str
    previousVersion: str | None = None
    blueprintCount: int = 0
    message: str = ""


class KnowledgePackPinRequest(BaseModel):
    version: str | None = None


class KnowledgePackPinResponse(BaseModel):
    packId: str
    pinnedVersion: str | None = None
    currentVersion: str | None = None
    message: str = ""


class KnowledgePackScheduleRequest(BaseModel):
    enabled: bool | None = None
    hours: int | None = None


class KnowledgePackScheduleResponse(BaseModel):
    syncScheduleEnabled: bool = True
    syncScheduleHours: int = 6
    message: str = ""
