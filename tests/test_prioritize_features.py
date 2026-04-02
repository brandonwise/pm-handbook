from pathlib import Path

import pytest

from tools.prioritize_features import (
    create_prioritized_backlog,
    load_features,
    rank_features,
    render_markdown,
    score_feature,
)


def test_score_feature_rewards_high_value_low_effort():
    high = {
        "feature": "A",
        "reach": "5",
        "impact": "5",
        "confidence": "4",
        "strategic_fit": "5",
        "effort": "2",
    }
    low = {
        "feature": "B",
        "reach": "4",
        "impact": "3",
        "confidence": "3",
        "strategic_fit": "3",
        "effort": "5",
    }

    assert score_feature(high) > score_feature(low)


def test_load_features_requires_expected_columns(tmp_path: Path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("feature,reach,impact\nA,4,5\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        load_features(csv_file)


def test_rank_features_orders_descending_by_score():
    rows = [
        {
            "feature": "Higher",
            "reach": "5",
            "impact": "5",
            "confidence": "4",
            "strategic_fit": "5",
            "effort": "2",
        },
        {
            "feature": "Lower",
            "reach": "3",
            "impact": "3",
            "confidence": "3",
            "strategic_fit": "3",
            "effort": "4",
        },
    ]

    ranked = rank_features(rows)
    assert ranked[0]["feature"] == "Higher"
    assert float(ranked[0]["score"]) > float(ranked[1]["score"])


def test_render_markdown_honors_top_n():
    ranked = [
        {
            "feature": "A",
            "reach": "5",
            "impact": "5",
            "confidence": "4",
            "strategic_fit": "5",
            "effort": "2",
            "score": "1.500",
        },
        {
            "feature": "B",
            "reach": "4",
            "impact": "4",
            "confidence": "4",
            "strategic_fit": "4",
            "effort": "3",
            "score": "1.100",
        },
    ]

    text = render_markdown(ranked, top=1)
    assert "| 1 | A |" in text
    assert "| 2 | B |" not in text


def test_create_prioritized_backlog_end_to_end(tmp_path: Path):
    input_csv = tmp_path / "features.csv"
    output_md = tmp_path / "ranked.md"

    input_csv.write_text(
        "\n".join(
            [
                "feature,reach,impact,confidence,strategic_fit,effort",
                "Slack escalation digest,4,5,4,5,2",
                "Bulk policy editor,3,4,3,4,4",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = create_prioritized_backlog(input_csv=input_csv, output_file=output_md)

    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "# Prioritized Feature Backlog" in content
    assert "Slack escalation digest" in content
