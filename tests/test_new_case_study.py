from pathlib import Path

from tools.new_case_study import create_case_study, slugify


def test_slugify_handles_spaces_and_symbols():
    assert slugify("AI PM: Launch Readiness!") == "ai-pm-launch-readiness"


def test_create_case_study_writes_expected_sections(tmp_path: Path):
    out = create_case_study(
        output_dir=tmp_path,
        title="Agent Reliability Rollout",
        problem="Support escalations were rising due to inconsistent AI responses.",
        outcome="Escalations dropped by 31% in six weeks.",
    )

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "## Context" in text
    assert "## Outcome" in text
    assert "Escalations dropped by 31%" in text
