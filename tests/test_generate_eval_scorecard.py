from pathlib import Path

import pytest

from tools.generate_eval_scorecard import (
    DEFAULT_DECISION_RULE,
    assess_decision,
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


def test_load_eval_rows_rejects_invalid_status(tmp_path: Path):
    csv_file = tmp_path / "invalid-status.csv"
    csv_file.write_text(
        "\n".join(
            [
                "scenario,stage,metric,threshold,owner,status",
                "Billing dispute,offline,Task success,>=0.90,PM,maybe",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid status"):
        load_eval_rows(csv_file)


def test_summarize_stages_uses_canonical_order_and_status_counts():
    rows = [
        {
            "scenario": "Go live",
            "stage": "launch",
            "metric": "Fallback rate",
            "threshold": "<2%",
            "owner": "Ops",
            "status": "blocked",
        },
        {
            "scenario": "Refund edge case",
            "stage": "offline",
            "metric": "Task success",
            "threshold": ">=0.90",
            "owner": "PM",
            "severity": "critical",
            "status": "pass",
        },
        {
            "scenario": "Shadow compare",
            "stage": "shadow",
            "metric": "Delta",
            "threshold": "<5 pts",
            "owner": "Eng",
            "status": "not-run",
        },
    ]

    summary = summarize_stages(rows)
    assert [item["stage"] for item in summary] == ["Offline", "Shadow", "Launch"]
    assert summary[0]["critical"] == "1"
    assert summary[0]["passed"] == "1"
    assert summary[1]["pending"] == "1"
    assert summary[2]["blocked"] == "1"


def test_assess_decision_returns_ready_for_passing_launch_pack():
    rows = [
        {
            "scenario": "Billing dispute with incomplete history",
            "stage": "offline",
            "metric": "Task success",
            "threshold": ">=0.90",
            "actual": "0.94",
            "owner": "PM + Eng",
            "severity": "critical",
            "status": "pass",
            "failure_mode": "Wrong refund answer",
        },
        {
            "scenario": "Escalation handoff under load",
            "stage": "launch",
            "metric": "Escalation latency",
            "threshold": "<2 min",
            "actual": "88 sec",
            "owner": "Support Ops",
            "severity": "high",
            "status": "pass",
            "rollback_trigger": ">3 min for 2 days",
        },
    ]

    decision = assess_decision(rows)
    assert decision["status"] == "READY"
    assert decision["blockers"] == []
    assert decision["warnings"] == []


def test_assess_decision_distinguishes_hold_from_pending():
    pending_rows = [
        {
            "scenario": "Billing dispute with incomplete history",
            "stage": "offline",
            "metric": "Task success",
            "threshold": ">=0.90",
            "owner": "PM + Eng",
            "severity": "critical",
            "status": "not-run",
        },
        {
            "scenario": "Escalation handoff under load",
            "stage": "launch",
            "metric": "Escalation latency",
            "threshold": "<2 min",
            "owner": "Support Ops",
            "severity": "high",
            "status": "pass",
            "rollback_trigger": ">3 min for 2 days",
        },
    ]
    hold_rows = [
        {
            "scenario": "Low-confidence policy answer",
            "stage": "launch",
            "metric": "Unsafe answer rate",
            "threshold": "<1%",
            "actual": "1.8%",
            "owner": "PM + Support Ops",
            "severity": "critical",
            "status": "fail",
            "rollback_trigger": ">1% for 1 day",
        }
    ]

    pending = assess_decision(pending_rows)
    hold = assess_decision(hold_rows)

    assert pending["status"] == "PENDING"
    assert hold["status"] == "HOLD"
    assert any("Low-confidence policy answer" in item for item in hold["blockers"])


def test_render_markdown_includes_launch_recommendation_and_execution_columns():
    rows = [
        {
            "scenario": "Billing dispute with incomplete history",
            "stage": "offline",
            "metric": "Task success",
            "threshold": ">=0.90",
            "actual": "0.94",
            "owner": "PM + Eng",
            "severity": "critical",
            "status": "pass",
            "failure_mode": "Wrong refund answer",
            "notes": "Use real support transcripts",
        },
        {
            "scenario": "Live escalation handoff",
            "stage": "launch",
            "metric": "Escalation latency",
            "threshold": "<2 min",
            "actual": "88 sec",
            "owner": "Support Ops",
            "status": "pass",
            "rollback_trigger": ">3 min for 2 days",
        },
    ]

    text = render_markdown(rows, product_name="Support copilot", decision_rule=DEFAULT_DECISION_RULE)

    assert "# AI Eval Scorecard" in text
    assert "- Product: Support copilot" in text
    assert "- Status: **READY**" in text
    assert "| Stage | Scenarios | Critical | Pass | Fail | Blocked | Pending | Owners |" in text
    assert "| Scenario | Metric | Threshold | Actual | Status | Severity | Owner | Failure Mode | Rollback Trigger | Notes |" in text
    assert "Wrong refund answer" in text
    assert ">3 min for 2 days" in text
    assert DEFAULT_DECISION_RULE in text


def test_create_eval_scorecard_end_to_end(tmp_path: Path):
    input_csv = tmp_path / "evals.csv"
    output_md = tmp_path / "ai-eval-scorecard.md"

    input_csv.write_text(
        "\n".join(
            [
                "scenario,stage,metric,threshold,actual,owner,severity,status,failure_mode,rollback_trigger,notes",
                "Billing dispute with incomplete history,offline,Task success,>=0.90,0.92,PM + Eng,critical,pass,Wrong refund answer,,Use real support transcripts",
                "Escalation handoff,launch,Escalation latency,<2 min,95 sec,Support Ops,high,pass,Escalation loop,>3 min for 2 days,Monitor during beta",
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
    assert "## Launch recommendation" in content
    assert "- Status: **READY**" in content
    assert "Support copilot" in content
    assert "Billing dispute with incomplete history" in content
