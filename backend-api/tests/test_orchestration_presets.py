from app.services.orchestration_presets import infer_orchestration_mode


def test_infer_orchestration_mode_defaults_to_standard():
    assert infer_orchestration_mode({}) == "standard"


def test_infer_orchestration_mode_reads_stored_mode():
    assert infer_orchestration_mode({"orchestrationMode": "extended"}) == "extended"


def test_infer_orchestration_mode_detects_matching_preset_values():
    assert infer_orchestration_mode(
        {
            "maxToolIterations": 40,
            "maxToolContinuationPhases": 5,
            "longTaskToolThreshold": 12,
            "promptBeforeLongTasks": True,
        }
    ) == "max"


def test_infer_orchestration_mode_marks_non_preset_as_custom():
    assert infer_orchestration_mode(
        {
            "maxToolIterations": 25,
            "maxToolContinuationPhases": 3,
            "longTaskToolThreshold": 8,
            "promptBeforeLongTasks": True,
        }
    ) == "custom"
