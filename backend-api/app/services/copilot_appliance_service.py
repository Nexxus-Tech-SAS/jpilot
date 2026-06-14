from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.appliance import is_copilot_eligible_appliance
from app.services.vendor_catalog_service import is_appliance_platform_enabled, serialize_appliance_with_platform
from app.services.copilot_service import resolve_appliance_credentials
from app.services.mcp_client import call_mcp_tool, test_appliance_via_mcp
from app.services.vendor_registry import get_vendor_manifest

NEXTGEN_LOGIN_PATH = "/mgmt/api/nextgen/v1/login"


async def list_copilot_appliances(db: AsyncIOMotorDatabase) -> list[dict]:
    appliances = await db.appliances.find({}).sort("name", 1).to_list(length=None)
    return [await serialize_appliance_with_platform(db, doc) for doc in appliances]


async def connect_appliance(db: AsyncIOMotorDatabase, appliance_name: str) -> dict:
    appliance = await db.appliances.find_one({"name": appliance_name})
    if appliance is None:
        raise ValueError(f"Appliance '{appliance_name}' not found in inventory")

    vendor = str(appliance.get("vendor") or "netscaler").strip().lower()
    if not is_copilot_eligible_appliance(appliance):
        raise ValueError(
            f"Appliance '{appliance_name}' (vendor '{vendor}') is not supported for JPilot chat yet."
        )

    if not await is_appliance_platform_enabled(db, appliance):
        raise ValueError(
            f"Appliance '{appliance_name}' is disabled at the platform level for its vendor product."
        )

    if not appliance.get("enabled", True):
        raise ValueError(f"Appliance '{appliance_name}' is disabled in inventory")

    host, username, password = await resolve_appliance_credentials(db, appliance_name)
    manifest = get_vendor_manifest(vendor)

    if manifest and manifest.connect_mode == "ssh":
        raw = await call_mcp_tool(
            manifest.connect_test_tool,
            {"host": host, "username": username, "password": password},
            db=db,
        )
        import json

        payload = json.loads(raw) if raw.strip().startswith("{") else {"success": False, "message": raw}
        if not payload.get("success"):
            raise ValueError(payload.get("message") or "SSH connection failed")
        return {
            "success": True,
            "applianceName": appliance_name,
            "environment": appliance.get("environment", ""),
            "message": payload.get("message", "Connected"),
            "api": "SSH",
            "authenticatedUser": username,
        }

    result = await test_appliance_via_mcp(host, username, password, db=db)
    if not result.get("success"):
        raise ValueError(result.get("message") or "Next-Gen API login failed")

    return {
        "success": True,
        "applianceName": appliance_name,
        "environment": appliance.get("environment", ""),
        "message": result.get("message", "Connected"),
        "api": "NetScaler Next-Gen API",
        "apiPath": "/mgmt/api/nextgen/v1",
        "loginEndpoint": NEXTGEN_LOGIN_PATH,
        "authenticatedUser": username,
    }
