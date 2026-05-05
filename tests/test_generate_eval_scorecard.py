from pathlib import Path

import pytest

from tools.generate_eval_scorecard import (
    DEFAULT_DECISION_RULE,
    create_eval_scorecard,
    load_eval_rows,
    render_markdown,
    summarize_stages,
)


def test_load_eval_rows_requires_expected_columns(tmp_path: Path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("scenario,stage,metric\nA,offline,Task success\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        load_eval_rows(csv_file)


def test_load_eval_rows_requires_feature_rows(tmp_path: Path):
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text(
        "scenario,stage,metric,threshold,owner,severity,failure_mode,notes\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="no evaluation rows"):
        load_eval_rows(csv_file)


def test_summarize_stages_uses_canonical_order():
    rows = [
        {"scenario": "Go live", "stage": "launch", "metric": "Fallback rate", "threshold": "<2%", "owner": "PM"},
        {
            "scenario": "Refund edge case",
            "stage": "offline",
            "metric": "Task success",
            "threshold": ">=0.90",
            "owner": "PM",
            "severity": "critical",
        },
        {"scenario": "Shadow compare", "stage": "shadow", "metric": "Delta", "threshold": "<5 pts", "owner": "Eng"},
    ]

    summary = summarize_stages(rows)
    assert [item["stage"] for item in summary] == ["Offline", "Shadow", "Launch"]
    assert summary[0]["critical"] == "1"


def test_render_markdown_includes_stage_sections_and_decision_rule():
    rows = [
        {
            "scenario": "Billing dispute with incomplete history",
            "stage": "offline",
            "metric": "Task success",
            "threshold": ">=0.90",
            "owner": "PM + Eng",
            "severity": "critical",
            "failure_mode": "Wrong refund answer",
            "notes": "Use real support transcripts",
        },
        {
            "scenario": "Live escalation handoff",
            "stage": "launch",
            "metric": "Escalation latency",
            "threshold": "<2 min",
            "owner": "Support Ops",
        },
    ]

    text = render_markdown(rows, product_name="Support copilot", decision_rule=DEFAULT_DECISION_RULE)

    assert "# AI Eval Scorecard" in text
    assert "- Product: Support copilot" in text
    assert "## Offline" in text
    assert "## Launch" in text
    assert text.index("## Offline") < text.index("## Launch")
    assert "Wrong refund answer" in text
    assert DEFAULT_DECISION_RULE in text


def test_create_eval_scorecard_end_to_end(tmp_path: Path):
    input_csv = tmp_path / "evals.csv"
    output_md = tmp_path / "ai-eval-scorecard.md"

    input_csv.write_text(
        "\n".join(
            [
                "scenario,stage,metric,threshold,owner,severity,failure_mode,notes",
                "Billing dispute with incomplete history,offline,Task success,>=0.90,PM + Eng,critical,Wrong refund answer,Use real support transcripts",
                "Escalation handoff,launch,Escalation latency,<2 min,Support Ops,high,Escalation loop,Monitor during beta",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = create_eval_scorecard(
        input_csv=input_csv,
        output_file=output_md,
        product_name="Support copilot",
    )

    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "## Stage coverage" in content
    assert "Support copilot" in content
    assert "Billing dispute with incomplete history" in content
