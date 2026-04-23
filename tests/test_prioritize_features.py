from pathlib import Path

import pytest

from tools.prioritize_features import (
    create_prioritized_backlog,
    filter_features,
    load_features,
    parse_weights,
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


def test_rank_features_supports_custom_weights():
    rows = [
        {
            "feature": "Big Reach",
            "reach": "5",
            "impact": "3",
            "confidence": "3",
            "strategic_fit": "3",
            "effort": "3",
        },
        {
            "feature": "Big Impact",
            "reach": "2",
            "impact": "5",
            "confidence": "3",
            "strategic_fit": "3",
            "effort": "3",
        },
    ]

    reach_heavy = parse_weights("reach=0.55,impact=0.20,confidence=0.15,strategic_fit=0.10")
    impact_heavy = parse_weights("reach=0.15,impact=0.55,confidence=0.15,strategic_fit=0.15")

    ranked_by_reach = rank_features(rows, weights=reach_heavy)
    ranked_by_impact = rank_features(rows, weights=impact_heavy)

    assert ranked_by_reach[0]["feature"] == "Big Reach"
    assert ranked_by_impact[0]["feature"] == "Big Impact"


def test_filter_features_applies_hard_constraints():
    rows = [
        {
            "feature": "Solid bet",
            "reach": "4",
            "impact": "4",
            "confidence": "4",
            "strategic_fit": "4",
            "effort": "3",
        },
        {
            "feature": "Low confidence experiment",
            "reach": "5",
            "impact": "5",
            "confidence": "2",
            "strategic_fit": "4",
            "effort": "2",
        },
    ]

    included, excluded = filter_features(rows, min_confidence=3.0)

    assert [row["feature"] for row in included] == ["Solid bet"]
    assert [row["feature"] for row in excluded] == ["Low confidence experiment"]
    assert "confidence" in excluded[0]["exclusion_reason"]


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


def test_render_markdown_shows_custom_formula():
    ranked = [
        {
            "feature": "A",
            "reach": "5",
            "impact": "5",
            "confidence": "4",
            "strategic_fit": "5",
            "effort": "2",
            "score": "1.500",
        }
    ]
    weights = parse_weights("reach=0.40,impact=0.25,confidence=0.20,strategic_fit=0.15")

    text = render_markdown(ranked, weights=weights)
    assert "Scoring formula: ((Reach×0.40)+(Impact×0.25)+(Confidence×0.20)+(Strategic Fit×0.15)) ÷ Effort" in text


def test_render_markdown_includes_excluded_rows():
    ranked = [
        {
            "feature": "Shipped",
            "reach": "5",
            "impact": "5",
            "confidence": "5",
            "strategic_fit": "5",
            "effort": "2",
            "score": "2.000",
        }
    ]
    excluded = [
        {
            "feature": "Blocked",
            "confidence": "2",
            "strategic_fit": "2",
            "exclusion_reason": "confidence 2 < min 3",
        }
    ]

    text = render_markdown(ranked, excluded=excluded)
    assert "## Excluded by hard constraints" in text
    assert "| Blocked | 2 | 2 | confidence 2 < min 3 |" in text


def test_parse_weights_requires_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        parse_weights("reach=0.4,impact=0.3,confidence=0.2,strategic_fit=0.2")


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


def test_create_prioritized_backlog_with_custom_weights(tmp_path: Path):
    input_csv = tmp_path / "features.csv"
    output_md = tmp_path / "ranked.md"

    input_csv.write_text(
        "\n".join(
            [
                "feature,reach,impact,confidence,strategic_fit,effort",
                "Big reach,5,2,3,3,3",
                "Big impact,2,5,3,3,3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = create_prioritized_backlog(
        input_csv=input_csv,
        output_file=output_md,
        weights=parse_weights("reach=0.15,impact=0.55,confidence=0.15,strategic_fit=0.15"),
    )

    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "| 1 | Big impact |" in content


def test_create_prioritized_backlog_with_min_confidence(tmp_path: Path):
    input_csv = tmp_path / "features.csv"
    output_md = tmp_path / "ranked.md"

    input_csv.write_text(
        "\n".join(
            [
                "feature,reach,impact,confidence,strategic_fit,effort",
                "Core onboarding fix,4,5,4,5,2",
                "Speculative moonshot,5,5,2,3,2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = create_prioritized_backlog(
        input_csv=input_csv,
        output_file=output_md,
        min_confidence=3.0,
    )

    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "| 1 | Core onboarding fix |" in content
    assert "## Excluded by hard constraints" in content
    assert "Speculative moonshot" in content


def test_filter_features_raises_when_all_rows_excluded():
    rows = [
        {
            "feature": "Moonshot",
            "reach": "5",
            "impact": "5",
            "confidence": "2",
            "strategic_fit": "3",
            "effort": "2",
        }
    ]

    with pytest.raises(ValueError, match="All features were excluded"):
        filter_features(rows, min_confidence=4.0)
