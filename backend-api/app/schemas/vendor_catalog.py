from pydantic import BaseModel, Field


class VendorCatalogProductItem(BaseModel):
    id: str
    label: str
    description: str
    vendorGroupId: str
    vendorValue: str | None = None
    status: str
    statusLabel: str
    toggleable: bool
    platformEnabled: bool
    applianceCount: int = 0


class VendorCatalogGroupItem(BaseModel):
    id: str
    label: str
    toggleable: bool
    platformEnabled: bool
    supportedCount: int
    enabledCount: int
    products: list[VendorCatalogProductItem]


class VendorCatalogResponse(BaseModel):
    groups: list[VendorCatalogGroupItem]


class VendorCatalogProductUpdate(BaseModel):
    productId: str
    enabled: bool


class VendorCatalogGroupUpdate(BaseModel):
    vendorGroupId: str
    enabled: bool


class VendorCatalogUpdate(BaseModel):
    products: list[VendorCatalogProductUpdate] = Field(default_factory=list)
    groups: list[VendorCatalogGroupUpdate] = Field(default_factory=list)
