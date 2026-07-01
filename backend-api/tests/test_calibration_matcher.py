from app.services.calibration_matcher import build_skill_injection_block, match_installed_skills


def test_match_firmware_skill_from_message(tmp_path, monkeypatch):
    skill_dir = tmp_path / "nexxus-netscaler-firmware-ha-upgrade" / "0.1.0"
    (skill_dir / "prompts").mkdir(parents=True)
    (skill_dir / "prompts" / "architect.md").write_text("Fast path firmware upgrade", encoding="utf-8")
    (skill_dir / "manifest.json").write_text(
        """
        {
          "id": "nexxus-netscaler-firmware-ha-upgrade",
          "vendor": "netscaler",
          "roles": ["architect"],
          "priority": 80,
          "triggers": {"intents": ["firmware upgrade", "ha pair"]}
        }
        """,
        encoding="utf-8",
    )

    installed = [
        {
            "skillId": "nexxus-netscaler-firmware-ha-upgrade",
            "version": "0.1.0",
            "vendor": "netscaler",
            "path": str(skill_dir),
        }
    ]

    matched = match_installed_skills(
        user_message="Create a phased firmware upgrade plan for HA pairs",
        role="architect",
        vendor="netscaler",
        installed=installed,
    )
    assert len(matched) == 1

    block = build_skill_injection_block(
        user_message="Create a phased firmware upgrade plan for HA pairs",
        role="architect",
        vendor="netscaler",
        installed=installed,
    )
    assert block is not None
    assert "Fast path firmware upgrade" in block


def test_resolve_blueprint_turn_context_intent_gated(tmp_path, monkeypatch):
    """Blueprint injection is gated on trigger intent; a matched skill still
    surfaces its memory excerpt, and unrelated requests inject nothing."""
    skill_dir = tmp_path / "nexxus-netscaler-custom-skill" / "0.1.0"
    (skill_dir / "memory").mkdir(parents=True)
    (skill_dir / "memory" / "playbook.md").write_text(
        "Use phased maintenance window for certificate rotation on HA pairs.",
        encoding="utf-8",
    )
    (skill_dir / "manifest.json").write_text(
        """
        {
          "id": "nexxus-netscaler-custom-skill",
          "vendor": "netscaler",
          "roles": ["operator"],
          "triggers": {"intents": ["rotate certificates on an ha pair", "certificate rotation"]},
          "memoryModules": [{"id": "playbook", "filename": "memory/playbook.md", "roleTags": ["operator"]}]
        }
        """,
        encoding="utf-8",
    )

    installed = [
        {
            "skillId": "nexxus-netscaler-custom-skill",
            "version": "0.1.0",
            "vendor": "netscaler",
            "path": str(skill_dir),
        }
    ]

    from app.services.calibration_matcher import resolve_blueprint_turn_context

    # On-intent: matches and injects the skill's memory excerpt.
    ctx = resolve_blueprint_turn_context(
        user_message="How do I rotate certificates on an HA pair?",
        role="operator",
        vendor="netscaler",
        installed=installed,
    )
    assert ctx.relevant is True
    assert ctx.injection_block is not None
    assert "certificate rotation" in ctx.injection_block.lower()

    # Off-intent (NS-1 regression guard): an unrelated request must NOT inject the
    # blueprint just because of incidental word overlap with the memory body.
    off = resolve_blueprint_turn_context(
        user_message="list all IPs",
        role="operator",
        vendor="netscaler",
        installed=installed,
    )
    assert off.relevant is False
    assert off.injection_block is None
