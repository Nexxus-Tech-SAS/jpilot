from app.services.update_service import (
    _normalize_version,
    _pick_latest_semver_tag,
    _read_installed_version,
    cancel_update_request,
    is_newer_version,
    reconcile_stale_update_lock,
)


def test_normalize_version_strips_v_prefix():
    assert _normalize_version("v0.06") == "0.06"
    assert _normalize_version("0.06") == "0.06"


def test_is_newer_version_compares_numeric_segments():
    assert is_newer_version("0.07", "0.06")
    assert not is_newer_version("0.06", "0.06")
    assert not is_newer_version("0.05", "0.06")


def test_pick_latest_semver_tag():
    tags = [{"name": "v0.05"}, {"name": "v0.06"}, {"name": "bad-tag"}]
    assert _pick_latest_semver_tag(tags) == "v0.06"


def test_read_installed_version_picks_highest(tmp_path, monkeypatch):
    low = tmp_path / "low"
    high = tmp_path / "high"
    low.write_text("0.103\n", encoding="utf-8")
    high.write_text("0.106\n", encoding="utf-8")
    monkeypatch.setattr(
        "app.services.update_service._version_paths",
        (low, high),
    )
    assert _read_installed_version() == "0.106"


def test_reconcile_clears_stale_requested(tmp_path, monkeypatch):
    update_dir = tmp_path / "update"
    update_dir.mkdir()
    monkeypatch.setenv("JPILOT_UPDATE_DIR", str(update_dir))
    status = update_dir / "status.json"
    request = update_dir / "request.json"
    status.write_text('{"state": "requested", "targetTag": "v0.83"}', encoding="utf-8")
    request.write_text('{"targetTag": "v0.83"}', encoding="utf-8")
    # mtime older than stale threshold
    old = 1_000_000_000
    import os

    os.utime(status, (old, old))
    assert reconcile_stale_update_lock() is True
    assert not status.is_file()
    assert not request.is_file()


def test_cancel_update_request_clears_sentinels(tmp_path, monkeypatch):
    update_dir = tmp_path / "update"
    update_dir.mkdir()
    monkeypatch.setenv("JPILOT_UPDATE_DIR", str(update_dir))
    (update_dir / "request.json").write_text("{}", encoding="utf-8")
    (update_dir / "status.json").write_text('{"state": "requested"}', encoding="utf-8")
    result = cancel_update_request()
    assert result.state == "idle"
    assert not (update_dir / "request.json").is_file()
    assert not (update_dir / "status.json").is_file()
