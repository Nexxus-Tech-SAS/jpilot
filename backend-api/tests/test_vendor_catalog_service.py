from app.services.appliance_catalog import get_product
from app.services.vendor_catalog_service import (
    _appliance_query_for_product,
    appliance_can_be_enabled,
)


def test_appliance_can_be_enabled_requires_platform():
    doc = {"vendor": "f5", "productId": "f5-bigip", "enabled": True}
    assert appliance_can_be_enabled(doc, platform_enabled=True) is True
    assert appliance_can_be_enabled(doc, platform_enabled=False) is False


def test_appliance_query_for_product_matches_legacy_vendor():
    product = get_product("netscaler-mpx")
    query = _appliance_query_for_product(product)
    assert {"productId": "netscaler-mpx"} in query["$or"]
    legacy_clause = next(item for item in query["$or"] if item.get("vendor") == "netscaler")
    assert legacy_clause is not None


def test_coming_soon_product_not_toggleable():
    product = get_product("cisco-asa")
    from app.services.appliance_catalog import is_product_toggleable

    assert is_product_toggleable(product) is False
