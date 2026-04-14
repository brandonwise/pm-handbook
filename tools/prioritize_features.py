from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional

REQUIRED_COLUMNS = {"feature", "reach", "impact", "confidence", "effort", "strategic_fit"}
SCORE_DIMENSIONS = ("reach", "impact", "confidence", "strategic_fit")
DEFAULT_WEIGHTS: Dict[str, float] = {
    "reach": 0.30,
    "impact": 0.35,
    "confidence": 0.20,
    "strategic_fit": 0.15,
}


def _to_float(row: Dict[str, str], key: str) -> float:
    value = row.get(key, "").strip()
    if value == "":
        raise ValueError(f"Missing value for '{key}' in feature '{row.get('feature', '<unknown>')}'")
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value for '{key}': {value}") from exc


def _validate_weights(weights: Dict[str, float]) -> Dict[str, float]:
    keys = set(weights)
    expected = set(SCORE_DIMENSIONS)

    missing = expected - keys
    extras = keys - expected
    if missing or extras:
        details: List[str] = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if extras:
            details.append(f"unexpected: {', '.join(sorted(extras))}")
        raise ValueError(f"Weight keys must match scoring dimensions ({'; '.join(details)}).")

    for key, value in weights.items():
        if value <= 0:
            raise ValueError(f"Weight '{key}' must be > 0.")

    total = sum(weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Weights must sum to 1.0, got {total:.3f}.")

    return {dimension: weights[dimension] for dimension in SCORE_DIMENSIONS}


def parse_weights(raw: Optional[str]) -> Dict[str, float]:
    """Parse custom scoring weights from a key=value CSV string."""

    if raw is None or raw.strip() == "":
        return dict(DEFAULT_WEIGHTS)

    parsed: Dict[str, float] = {}
    for item in raw.split(","):
        token = item.strip()
        if token == "":
            continue

        if "=" not in token:
            raise ValueError(f"Invalid weight token '{token}'. Use key=value format.")

        key, value = token.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip()

        if key in parsed:
            raise ValueError(f"Duplicate weight key '{key}'.")

        try:
            parsed[key] = float(value)
        except ValueError as exc:
            raise ValueError(f"Invalid weight value for '{key}': {value}") from exc

    return _validate_weights(parsed)


def _format_formula(weights: Dict[str, float]) -> str:
    return (
        f"((Reach×{weights['reach']:.2f})"
        f"+(Impact×{weights['impact']:.2f})"
        f"+(Confidence×{weights['confidence']:.2f})"
        f"+(Strategic Fit×{weights['strategic_fit']:.2f})) ÷ Effort"
    )


def score_feature(row: Dict[str, str], weights: Optional[Dict[str, float]] = None) -> float:
    """Score one feature using weighted value divided by effort.

    Inputs are expected to be 1-5 scale values.
    """

    active_weights = _validate_weights(weights) if weights is not None else DEFAULT_WEIGHTS

    reach = _to_float(row, "reach")
    impact = _to_float(row, "impact")
    confidence = _to_float(row, "confidence")
    strategic_fit = _to_float(row, "strategic_fit")
    effort = _to_float(row, "effort")

    weighted_value = (
        (reach * active_weights["reach"])
        + (impact * active_weights["impact"])
        + (confidence * active_weights["confidence"])
        + (strategic_fit * active_weights["strategic_fit"])
    )
    return round(weighted_value / max(effort, 0.1), 3)


def load_features(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Input CSV must include a header row.")

        columns = {name.strip() for name in reader.fieldnames if name}
        missing = REQUIRED_COLUMNS - columns
        if missing:
            missing_columns = ", ".join(sorted(missing))
            raise ValueError(f"Input CSV is missing required columns: {missing_columns}")

        rows = [dict(row) for row in reader]

    if not rows:
        raise ValueError("Input CSV has no feature rows.")

    return rows


def rank_features(rows: List[Dict[str, str]], weights: Optional[Dict[str, float]] = None) -> List[Dict[str, str]]:
    active_weights = _validate_weights(weights) if weights is not None else DEFAULT_WEIGHTS

    ranked: List[Dict[str, str]] = []
    for row in rows:
        copy = dict(row)
        copy["score"] = f"{score_feature(row, weights=active_weights):.3f}"
        ranked.append(copy)

    ranked.sort(key=lambda item: float(item["score"]), reverse=True)
    return ranked


def render_markdown(
    ranked: List[Dict[str, str]],
    top: Optional[int] = None,
    weights: Optional[Dict[str, float]] = None,
) -> str:
    active_weights = _validate_weights(weights) if weights is not None else DEFAULT_WEIGHTS
    limited = ranked[:top] if top else ranked
    lines = [
        "# Prioritized Feature Backlog",
        "",
        f"Scoring formula: {_format_formula(active_weights)}",
        "",
        "| Rank | Feature | Score | Reach | Impact | Confidence | Strategic Fit | Effort |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]

    for index, row in enumerate(limited, start=1):
        lines.append(
            "| {rank} | {feature} | {score} | {reach} | {impact} | {confidence} | {strategic_fit} | {effort} |".format(
                rank=index,
                feature=row.get("feature", "").replace("|", "\\|"),
                score=row["score"],
                reach=row.get("reach", ""),
                impact=row.get("impact", ""),
                confidence=row.get("confidence", ""),
                strategic_fit=row.get("strategic_fit", ""),
                effort=row.get("effort", ""),
            )
        )

    return "\n".join(lines) + "\n"


def create_prioritized_backlog(
    input_csv: Path,
    output_file: Path,
    top: Optional[int] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Path:
    rows = load_features(input_csv)
    active_weights = _validate_weights(weights) if weights is not None else DEFAULT_WEIGHTS
    ranked = rank_features(rows, weights=active_weights)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(render_markdown(ranked, top=top, weights=active_weights), encoding="utf-8")
    return output_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prioritize feature candidates with a lightweight weighted scorecard and export markdown."
    )
    parser.add_argument("--input", required=True, help="Input CSV file with feature scoring rows")
    parser.add_argument(
        "--output",
        default="templates/generated/prioritized-backlog.md",
        help="Output markdown file path",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Only keep the top N ranked rows in the output",
    )
    parser.add_argument(
        "--weights",
        default=None,
        help=(
            "Optional custom weights as comma-separated key=value pairs "
            "for reach,impact,confidence,strategic_fit (must sum to 1.0)."
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    weights = parse_weights(args.weights)

    output_path = create_prioritized_backlog(
        input_csv=Path(args.input),
        output_file=Path(args.output),
        top=args.top,
        weights=weights,
    )
    print(f"Created: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
