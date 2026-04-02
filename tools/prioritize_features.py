from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional

REQUIRED_COLUMNS = {"feature", "reach", "impact", "confidence", "effort", "strategic_fit"}


def _to_float(row: Dict[str, str], key: str) -> float:
    value = row.get(key, "").strip()
    if value == "":
        raise ValueError(f"Missing value for '{key}' in feature '{row.get('feature', '<unknown>')}'")
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value for '{key}': {value}") from exc


def score_feature(row: Dict[str, str]) -> float:
    """Score one feature using weighted value divided by effort.

    Inputs are expected to be 1-5 scale values.
    """

    reach = _to_float(row, "reach")
    impact = _to_float(row, "impact")
    confidence = _to_float(row, "confidence")
    strategic_fit = _to_float(row, "strategic_fit")
    effort = _to_float(row, "effort")

    weighted_value = (reach * 0.30) + (impact * 0.35) + (confidence * 0.20) + (strategic_fit * 0.15)
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


def rank_features(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    ranked: List[Dict[str, str]] = []
    for row in rows:
        copy = dict(row)
        copy["score"] = f"{score_feature(row):.3f}"
        ranked.append(copy)

    ranked.sort(key=lambda item: float(item["score"]), reverse=True)
    return ranked


def render_markdown(ranked: List[Dict[str, str]], top: Optional[int] = None) -> str:
    limited = ranked[:top] if top else ranked
    lines = [
        "# Prioritized Feature Backlog",
        "",
        "Scoring formula: ((Reach×0.30)+(Impact×0.35)+(Confidence×0.20)+(Strategic Fit×0.15)) ÷ Effort",
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


def create_prioritized_backlog(input_csv: Path, output_file: Path, top: Optional[int] = None) -> Path:
    rows = load_features(input_csv)
    ranked = rank_features(rows)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(render_markdown(ranked, top=top), encoding="utf-8")
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
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_path = create_prioritized_backlog(
        input_csv=Path(args.input),
        output_file=Path(args.output),
        top=args.top,
    )
    print(f"Created: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
