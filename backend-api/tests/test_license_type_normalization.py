import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.license_service import (  # noqa: E402
    license_tier_rank,
    normalize_license_type,
    resolve_license_type_from_document,
)


def test_normalize_license_type_accepts_hyphen_and_underscore():
    assert normalize_license_type("enterprise-pro") == "enterprise_pro"
    assert normalize_license_type("enterprise_pro") == "enterprise_pro"


def test_license_tier_rank_orders_enterprise_pro_above_enterprise():
    assert license_tier_rank("enterprise_pro") > license_tier_rank("enterprise")
    assert license_tier_rank("enterprise") > license_tier_rank("free")


def test_resolve_license_type_from_cached_license():
    document = {
        "licenseType": None,
        "cachedLicense": {"licenseType": "enterprise-pro"},
    }
    assert resolve_license_type_from_document(document) == "enterprise_pro"
