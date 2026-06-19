from pydantic import BaseModel, Field


class CalibrationSkillSummary(BaseModel):
    skillId: str
    version: str
    label: str = ""
    vendor: str | None = None
    path: str = ""


class CalibrationSyncResponse(BaseModel):
    installed: int
    updated: int
    removed: int
    skills: list[dict] = Field(default_factory=list)
    message: str = ""


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
    clientId: str | None = None
    entitlements: list[str] = Field(default_factory=list)
    skills: list[CalibrationCatalogSkill] = Field(default_factory=list)
    installedBlueprints: list[CalibrationInstalledBlueprint] = Field(default_factory=list)
