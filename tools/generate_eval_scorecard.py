from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple, TypedDict

REQUIRED_COLUMNS = {"scenario", "stage", "metric", "threshold", "owner"}
STAGE_ORDER: Sequence[str] = ("offline", "shadow", "launch")
DEFAULT_DECISION_RULE = (
    "Launch only if every critical scenario meets threshold and no red-line failure mode is unresolved."
)


class StageSummary(TypedDict):
    stage: str
    count: int
    critical: int
    owners: Set[str]


def _clean_row(row: Dict[str, str]) -> Dict[str, str]:
    return {str(key).strip(): (value or "").strip() for key, value in row.items()}


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _stage_sort_key(stage: str) -> Tuple[int, str]:
    normalized = stage.strip().lower()
    if normalized in STAGE_ORDER:
        return (STAGE_ORDER.index(normalized), normalized)
    return (len(STAGE_ORDER), normalized)


def _stage_label(stage: str) -> str:
    normalized = stage.strip().lower()
    if normalized == "":
        return "Unspecified"
    return normalized.replace("-", " ").title()


def load_eval_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Input CSV must include a header row.")

        columns = {name.strip() for name in reader.fieldnames if name}
        missing = REQUIRED_COLUMNS - columns
        if missing:
            missing_columns = ", ".join(sorted(missing))
            raise ValueError(f"Input CSV is missing required columns: {missing_columns}")

        rows = [_clean_row(dict(row)) for row in reader]

    if not rows:
        raise ValueError("Input CSV has no evaluation rows.")

    return rows


def summarize_stages(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    grouped: Dict[str, StageSummary] = {}

    for row in rows:
        stage = row.get("stage", "")
        key = stage.strip().lower()
        if key not in grouped:
            grouped[key] = {
                "stage": _stage_label(stage),
                "count": 0,
                "critical": 0,
                "owners": set(),
            }

        summary = grouped[key]
        summary["count"] += 1

        severity = row.get("severity", "").strip().lower()
        if severity == "critical":
            summary["critical"] += 1

        owner = row.get("owner", "")
        if owner:
            summary["owners"].add(owner)

    ordered: List[Dict[str, str]] = []
    for key in sorted(grouped.keys(), key=_stage_sort_key):
        summary = grouped[key]
        ordered.append(
            {
                "stage": summary["stage"],
                "count": str(summary["count"]),
                "critical": str(summary["critical"]),
                "owners": ", ".join(sorted(summary["owners"])),
            }
        )

    return ordered


def render_markdown(
    rows: List[Dict[str, str]],
    product_name: str = "AI product",
    decision_rule: str = DEFAULT_DECISION_RULE,
) -> str:
    lines = [
        "# AI Eval Scorecard",
        "",
        f"- Product: {product_name}",
        f"- Generated: {date.today().isoformat()}",
        "",
        "## Release decision rule",
        decision_rule,
        "",
        "## Stage coverage",
        "",
        "| Stage | Scenarios | Critical Scenarios | Owners |",
        "|---|---:|---:|---|",
    ]

    for summary in summarize_stages(rows):
        lines.append(
            "| {stage} | {count} | {critical} | {owners} |".format(
                stage=summary["stage"],
                count=summary["count"],
                critical=summary["critical"],
                owners=_escape_cell(summary["owners"]),
            )
        )

    grouped: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        key = row.get("stage", "").strip().lower()
        grouped.setdefault(key, []).append(row)

    for stage_key in sorted(grouped.keys(), key=_stage_sort_key):
        lines.extend(
            [
                "",
                f"## {_stage_label(stage_key)}",
                "",
                "| Scenario | Metric | Threshold | Severity | Owner | Failure Mode | Notes |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for row in grouped[stage_key]:
            lines.append(
                "| {scenario} | {metric} | {threshold} | {severity} | {owner} | {failure_mode} | {notes} |".format(
                    scenario=_escape_cell(row.get("scenario", "")),
                    metric=_escape_cell(row.get("metric", "")),
                    threshold=_escape_cell(row.get("threshold", "")),
                    severity=_escape_cell(row.get("severity", "medium") or "medium"),
                    owner=_escape_cell(row.get("owner", "")),
                    failure_mode=_escape_cell(row.get("failure_mode", "")),
                    notes=_escape_cell(row.get("notes", "")),
                )
            )

    lines.extend(
        [
            "",
            "## Review checklist",
            "",
            "- [ ] Thresholds map to user-visible quality, not vanity metrics",
            "- [ ] At least one abuse or red-team scenario exists for each critical flow",
            "- [ ] Launch-stage monitoring owner is named",
            "- [ ] Rollback trigger is explicit before rollout starts",
        ]
    )

    return "\n".join(lines) + "\n"


def create_eval_scorecard(
    input_csv: Path,
    output_file: Path,
    product_name: str = "AI product",
    decision_rule: str = DEFAULT_DECISION_RULE,
) -> Path:
    rows = load_eval_rows(input_csv)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        render_markdown(rows, product_name=product_name, decision_rule=decision_rule),
        encoding="utf-8",
    )
    return output_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an AI eval scorecard from a CSV of scenarios, metrics, and thresholds."
    )
    parser.add_argument("--input", required=True, help="Input CSV file with evaluation rows")
    parser.add_argument(
        "--output",
        default="templates/generated/ai-eval-scorecard.md",
        help="Output markdown file path",
    )
    parser.add_argument(
        "--product-name",
        default="AI product",
        help="Name of the product, workflow, or bet being reviewed",
    )
    parser.add_argument(
        "--decision-rule",
        default=DEFAULT_DECISION_RULE,
        help="Explicit ship/hold rule printed at the top of the scorecard",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_path = create_eval_scorecard(
        input_csv=Path(args.input),
        output_file=Path(args.output),
        product_name=args.product_name,
        decision_rule=args.decision_rule,
    )
    print(f"Created: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
