from app.services.copilot_architect_discovery import append_design_document_revision_context


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
