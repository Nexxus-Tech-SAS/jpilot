"""Static appliance product catalog — keep in sync with frontend/src/config/applianceVendors.js."""

from __future__ import annotations

from typing import Any

NETSCALER_VENDOR = "netscaler"

VENDOR_GROUPS: list[dict[str, str]] = [
    {"id": "citrix", "label": "Citrix"},
    {"id": "cisco", "label": "Cisco"},
    {"id": "f5", "label": "F5"},
    {"id": "juniper", "label": "Juniper"},
    {"id": "palo_alto", "label": "Palo Alto Networks"},
    {"id": "fortinet", "label": "Fortinet"},
    {"id": "checkpoint", "label": "Check Point"},
    {"id": "a10", "label": "A10 Networks"},
    {"id": "radware", "label": "Radware"},
    {"id": "haproxy", "label": "HAProxy / Kemp"},
    {"id": "other", "label": "Other"},
]

PRODUCTS: list[dict[str, Any]] = [
    {
        "id": "netscaler-mpx",
        "vendorGroupId": "citrix",
        "value": NETSCALER_VENDOR,
        "label": "NetScaler MPX",
        "description": "Physical ADC — full JPilot chat, Next-Gen API, SSH CLI, Citrix Gateway, diagnostics, and SSL tools.",
        "status": "supported",
    },
    {
        "id": "netscaler-vpx",
        "vendorGroupId": "citrix",
        "value": NETSCALER_VENDOR,
        "label": "NetScaler VPX",
        "description": "Virtual ADC — full JPilot chat, Next-Gen API, SSH CLI, Citrix Gateway, diagnostics, and SSL tools.",
        "status": "supported",
    },
    {
        "id": "netscaler-sdx",
        "vendorGroupId": "citrix",
        "value": "sdx",
        "label": "NetScaler SDX",
        "description": "JPilot Operator/Analyst over SSH for SVM platform and VPX lifecycle.",
        "status": "supported",
        "beta": True,
    },
    {
        "id": "cisco-switches",
        "vendorGroupId": "cisco",
        "value": "cisco",
        "label": "Cisco IOS/XE Switches",
        "description": "JPilot Operator/Analyst over SSH (show/configure).",
        "status": "supported",
        "beta": True,
    },
    {
        "id": "cisco-asa",
        "vendorGroupId": "cisco",
        "value": None,
        "label": "Cisco ASA",
        "description": "Adaptive Security Appliance firewalls.",
        "status": "coming_soon",
    },
    {
        "id": "cisco-ftd",
        "vendorGroupId": "cisco",
        "value": None,
        "label": "Cisco FTD",
        "description": "Firepower Threat Defense platforms.",
        "status": "coming_soon",
    },
    {
        "id": "cisco-aci",
        "vendorGroupId": "cisco",
        "value": None,
        "label": "Cisco ACI",
        "description": "Application Centric Infrastructure.",
        "status": "coming_soon",
    },
    {
        "id": "f5-bigip",
        "vendorGroupId": "f5",
        "value": "f5",
        "label": "F5 BIG-IP",
        "description": "JPilot Operator/Analyst over SSH (TMSH show/configure) and Architect from official F5 docs.",
        "status": "supported",
        "beta": True,
    },
    {
        "id": "juniper-junos",
        "vendorGroupId": "juniper",
        "value": "juniper",
        "label": "Junos (SRX / EX / QFX)",
        "description": "Junos devices and SRX series.",
        "status": "coming_soon",
    },
    {
        "id": "palo-panos",
        "vendorGroupId": "palo_alto",
        "value": "palo_alto",
        "label": "PAN-OS / Panorama",
        "description": "Palo Alto Networks firewalls and Panorama.",
        "status": "coming_soon",
    },
    {
        "id": "fortinet-fortigate",
        "vendorGroupId": "fortinet",
        "value": "fortinet",
        "label": "FortiGate / FortiADC",
        "description": "Fortinet security and ADC platforms.",
        "status": "coming_soon",
    },
    {
        "id": "checkpoint-gw",
        "vendorGroupId": "checkpoint",
        "value": "checkpoint",
        "label": "Check Point Gateway",
        "description": "Security gateways and management.",
        "status": "coming_soon",
    },
    {
        "id": "a10-thunder",
        "vendorGroupId": "a10",
        "value": "a10",
        "label": "A10 Thunder ADC",
        "description": "Thunder ADC load balancers.",
        "status": "coming_soon",
    },
    {
        "id": "radware-alteon",
        "vendorGroupId": "radware",
        "value": "radware",
        "label": "Radware Alteon / AppWall",
        "description": "Alteon and AppWall ADC platforms.",
        "status": "coming_soon",
    },
    {
        "id": "haproxy-kemp",
        "vendorGroupId": "haproxy",
        "value": "haproxy",
        "label": "HAProxy / Kemp",
        "description": "Software and hardware load balancers.",
        "status": "coming_soon",
    },
    {
        "id": "other-generic",
        "vendorGroupId": "other",
        "value": "other",
        "label": "Other platform",
        "description": "Any vendor with SSH CLI and/or REST API access.",
        "status": "coming_soon",
    },
]

_PRODUCT_BY_ID = {item["id"]: item for item in PRODUCTS}


def get_vendor_group_label(group_id: str) -> str:
    for group in VENDOR_GROUPS:
        if group["id"] == group_id:
            return group["label"]
    return group_id


def get_product(product_id: str | None) -> dict[str, Any] | None:
    if not product_id:
        return None
    return _PRODUCT_BY_ID.get(product_id)


def get_products_for_group(group_id: str) -> list[dict[str, Any]]:
    return [item for item in PRODUCTS if item["vendorGroupId"] == group_id]


def product_availability_status(product: dict[str, Any]) -> str:
    if product.get("status") != "supported":
        return "coming_soon"
    return "beta" if product.get("beta") else "supported"


def is_product_supported(product: dict[str, Any] | None) -> bool:
    return bool(product and product.get("status") == "supported" and product.get("value"))


def is_product_toggleable(product: dict[str, Any] | None) -> bool:
    return is_product_supported(product)


def resolve_appliance_product(doc: dict[str, Any]) -> dict[str, Any] | None:
    product_id = (doc.get("productId") or "").strip()
    if product_id:
        return get_product(product_id)
    vendor = (doc.get("vendor") or NETSCALER_VENDOR).strip().lower()
    if not vendor or vendor == NETSCALER_VENDOR:
        return {
            "id": "netscaler-adc",
            "label": "NetScaler ADC",
            "value": NETSCALER_VENDOR,
            "vendorGroupId": "citrix",
            "status": "supported",
        }
    for product in PRODUCTS:
        if product.get("value") == vendor:
            return product
    return None
