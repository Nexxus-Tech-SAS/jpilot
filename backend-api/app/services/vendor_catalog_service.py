"""Platform-level vendor/product enablement stored in MongoDB."""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.appliance import utc_now
from app.schemas.vendor_catalog import (
    VendorCatalogGroupItem,
    VendorCatalogProductItem,
    VendorCatalogResponse,
    VendorCatalogUpdate,
)
from app.services.appliance_catalog import (
    VENDOR_GROUPS,
    get_product,
    get_products_for_group,
    is_product_supported,
    is_product_toggleable,
    product_availability_status,
    resolve_appliance_product,
)

SETTINGS_ID = "default"

_STATUS_LABELS = {
    "supported": "Available",
    "beta": "Beta",
    "coming_soon": "Coming soon",
}


def _status_label(status: str) -> str:
    return _STATUS_LABELS.get(status, status.replace("_", " ").title())


async def ensure_vendor_catalog_settings(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    existing = await db.vendorCatalogSettings.find_one({"_id": SETTINGS_ID})
    if existing is None:
        doc = {"_id": SETTINGS_ID, "products": {}, "updatedAt": utc_now()}
        await db.vendorCatalogSettings.insert_one(doc)
        return doc
    return existing


def _stored_product_flags(doc: dict[str, Any]) -> dict[str, bool]:
    raw = doc.get("products") or {}
    parsed: dict[str, bool] = {}
    for product_id, value in raw.items():
        if isinstance(value, dict):
            parsed[str(product_id)] = bool(value.get("enabled", True))
        else:
            parsed[str(product_id)] = bool(value)
    return parsed


async def get_product_platform_enabled(db: AsyncIOMotorDatabase, product_id: str) -> bool:
    product = get_product(product_id)
    if not is_product_toggleable(product):
        return False
    doc = await ensure_vendor_catalog_settings(db)
    stored = _stored_product_flags(doc)
    return stored.get(product_id, True)


async def is_appliance_platform_enabled(db: AsyncIOMotorDatabase, doc: dict[str, Any]) -> bool:
    product = resolve_appliance_product(doc)
    if product is None:
        return True
    product_id = str(product.get("id") or "")
    if not product_id:
        return True
    if not is_product_toggleable(product):
        return False
    return await get_product_platform_enabled(db, product_id)


def _appliance_query_for_product(product: dict[str, Any]) -> dict[str, Any]:
    clauses: list[dict[str, Any]] = [{"productId": product["id"]}]
    vendor_value = product.get("value")
    if vendor_value:
        clauses.append(
            {
                "vendor": vendor_value,
                "$or": [
                    {"productId": {"$exists": False}},
                    {"productId": None},
                    {"productId": ""},
                ],
            }
        )
    return {"$or": clauses}


async def _count_appliances_for_product(db: AsyncIOMotorDatabase, product: dict[str, Any]) -> int:
    return await db.appliances.count_documents(_appliance_query_for_product(product))


async def _set_appliances_enabled_for_product(
    db: AsyncIOMotorDatabase,
    product: dict[str, Any],
    *,
    enabled: bool,
) -> int:
    result = await db.appliances.update_many(
        _appliance_query_for_product(product),
        {"$set": {"enabled": enabled, "updatedAt": utc_now()}},
    )
    return int(result.modified_count)


async def set_product_platform_enabled(
    db: AsyncIOMotorDatabase,
    product_id: str,
    enabled: bool,
) -> None:
    product = get_product(product_id)
    if not is_product_toggleable(product):
        raise ValueError(f"Product '{product_id}' cannot be enabled or disabled")

    doc = await ensure_vendor_catalog_settings(db)
    products = dict(doc.get("products") or {})
    products[product_id] = {"enabled": enabled}
    await db.vendorCatalogSettings.update_one(
        {"_id": SETTINGS_ID},
        {"$set": {"products": products, "updatedAt": utc_now()}},
        upsert=True,
    )

    if not enabled:
        await _set_appliances_enabled_for_product(db, product, enabled=False)


async def set_vendor_group_platform_enabled(
    db: AsyncIOMotorDatabase,
    group_id: str,
    enabled: bool,
) -> None:
    products = [item for item in get_products_for_group(group_id) if is_product_toggleable(item)]
    if not products:
        raise ValueError(f"Vendor group '{group_id}' has no configurable products")

    doc = await ensure_vendor_catalog_settings(db)
    stored = dict(doc.get("products") or {})
    for product in products:
        stored[product["id"]] = {"enabled": enabled}
        if not enabled:
            await _set_appliances_enabled_for_product(db, product, enabled=False)

    await db.vendorCatalogSettings.update_one(
        {"_id": SETTINGS_ID},
        {"$set": {"products": stored, "updatedAt": utc_now()}},
        upsert=True,
    )


async def get_vendor_catalog(db: AsyncIOMotorDatabase) -> VendorCatalogResponse:
    doc = await ensure_vendor_catalog_settings(db)
    stored = _stored_product_flags(doc)
    groups: list[VendorCatalogGroupItem] = []

    for group in VENDOR_GROUPS:
        product_items: list[VendorCatalogProductItem] = []
        toggleable_products = []
        enabled_toggleable = 0

        for product in get_products_for_group(group["id"]):
            status = product_availability_status(product)
            toggleable = is_product_toggleable(product)
            platform_enabled = stored.get(product["id"], True) if toggleable else False
            if toggleable:
                toggleable_products.append(product)
                if platform_enabled:
                    enabled_toggleable += 1
            product_items.append(
                VendorCatalogProductItem(
                    id=product["id"],
                    label=product["label"],
                    description=product.get("description", ""),
                    vendorGroupId=group["id"],
                    vendorValue=product.get("value"),
                    status=status,
                    statusLabel=_status_label(status),
                    toggleable=toggleable,
                    platformEnabled=platform_enabled,
                    applianceCount=await _count_appliances_for_product(db, product),
                )
            )

        group_toggleable = len(toggleable_products) > 0
        group_enabled = group_toggleable and enabled_toggleable == len(toggleable_products)
        groups.append(
            VendorCatalogGroupItem(
                id=group["id"],
                label=group["label"],
                toggleable=group_toggleable,
                platformEnabled=group_enabled,
                supportedCount=len(toggleable_products),
                enabledCount=enabled_toggleable,
                products=product_items,
            )
        )

    return VendorCatalogResponse(groups=groups)


async def update_vendor_catalog(db: AsyncIOMotorDatabase, payload: VendorCatalogUpdate) -> VendorCatalogResponse:
    for item in payload.products:
        await set_product_platform_enabled(db, item.productId, item.enabled)
    for item in payload.groups:
        await set_vendor_group_platform_enabled(db, item.vendorGroupId, item.enabled)
    return await get_vendor_catalog(db)


async def serialize_appliance_with_platform(db: AsyncIOMotorDatabase, doc: dict[str, Any]) -> dict[str, Any]:
    from app.models.appliance import is_copilot_eligible_appliance, serialize_appliance

    base = serialize_appliance(doc)
    platform_enabled = await is_appliance_platform_enabled(db, doc)
    base["platformEnabled"] = platform_enabled
    base["chatAvailable"] = bool(
        base["enabled"] and platform_enabled and base["copilotEligible"]
    )
    return base


def appliance_can_be_enabled(doc: dict[str, Any], *, platform_enabled: bool) -> bool:
    if not platform_enabled:
        return False
    from app.models.appliance import is_copilot_eligible_appliance

    if not is_copilot_eligible_appliance(doc):
        return False
    product = resolve_appliance_product(doc)
    if product and not is_product_supported(product):
        return False
    return True
