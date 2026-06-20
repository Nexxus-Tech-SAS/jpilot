from app.services.copilot_architect_discovery import (
    append_architect_panel_context,
    append_design_document_revision_context,
    append_discovery_workbook_context,
    is_discovery_workbook,
)


def test_append_design_document_revision_context():
    result = append_design_document_revision_context(
        "Update the VIP section",
        "# Design\n\nVIP: 10.0.0.1",
        include_revision=True,
    )
    assert "Update the VIP section" in result
    assert "--- Current design document ---" in result
    assert "VIP: 10.0.0.1" in result
    assert "Include my edits" in result


def test_append_design_document_revision_context_empty_doc():
    assert append_design_document_revision_context("Hello", "  ") == "Hello"


def test_is_discovery_workbook():
    assert is_discovery_workbook("# Discovery workbook\n\n## Topology\n- **Layout:** dual")
    assert not is_discovery_workbook("<!-- jpilot-design-document -->\n# Design")
    assert not is_discovery_workbook("")


def test_append_discovery_workbook_context():
    workbook = "# Discovery workbook\n\n## Deployment topology\n- **Layout:** dual_dc_gslb"
    result = append_discovery_workbook_context("Planning inputs for: Deployment topology", workbook)
    assert "Planning inputs for:" in result
    assert "--- Discovery workbook ---" in result
    assert "dual_dc_gslb" in result
    assert "source of truth" in result


def test_append_architect_panel_context_routes_discovery():
    workbook = "# Discovery workbook\n\n## Auth\n- **Method:** SAML"
    result = append_architect_panel_context("Continue", workbook)
    assert "--- Discovery workbook ---" in result
    assert "--- Current design document ---" not in result


def test_append_architect_panel_context_routes_deliverable_revision():
    doc = "<!-- jpilot-design-document -->\n# Design\n\nVIP: TBD"
    result = append_architect_panel_context("Update VIP", doc, include_revision=True)
    assert "--- Current design document ---" in result
    assert "Include my edits" in result
