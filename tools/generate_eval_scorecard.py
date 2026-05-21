from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple, TypedDict

REQUIRED_COLUMNS = {"scenario", "stage", "metric", "threshold", "owner"}
STAGE_ORDER: Sequence[str] = ("offline", "shadow", "launch")
VALID_STATUSES = {"pass", "fail", "blocked", "not-run"}
DEFAULT_DECISION_RULE = (
    "Launch only if every critical scenario meets threshold and no red-line failure mode is unresolved."
)


class StageSummary(TypedDict):
    stage: str
    count: int
    critical: int
    passed: int
    failed: int
    blocked: int
    pending: int
    owners: Set[str]


class DecisionSummary(TypedDict):
    status: str
    blockers: List[str]
    warnings: List[str]


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


def _normalize_status(value: str) -> str:
    return value.strip().lower()


def _status_label(value: str) -> str:
    normalized = _normalize_status(value)
    if normalized == "":
        return "Pending"
    if normalized == "not-run":
        return "Not Run"
    return normalized.title()


def _row_label(row: Dict[str, str]) -> str:
    scenario = row.get("scenario", "").strip()
    return scenario or "<unnamed scenario>"


def _dedupe(items: List[str]) -> List[str]:
    seen: Set[str] = set()
    deduped: List[str] = []
    for item in items:
        if item in seen:
            continue
        deduped.append(item)
        seen.add(item)
    return deduped


def _validate_row(row: Dict[str, str]) -> None:
    status = _normalize_status(row.get("status", ""))
    if status and status not in VALID_STATUSES:
        valid = ", ".join(sorted(VALID_STATUSES))
        raise ValueError(
            f"Scenario '{_row_label(row)}' has invalid status '{row.get('status', '')}'. "
            f"Use one of: {valid}."
        )


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

    for row in rows:
        _validate_row(row)

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
                "passed": 0,
                "failed": 0,
                "blocked": 0,
                "pending": 0,
                "owners": set(),
            }

        summary = grouped[key]
        summary["count"] += 1

        severity = row.get("severity", "").strip().lower()
        if severity == "critical":
            summary["critical"] += 1

        status = _normalize_status(row.get("status", ""))
        if status == "pass":
            summary["passed"] += 1
        elif status == "fail":
            summary["failed"] += 1
        elif status == "blocked":
            summary["blocked"] += 1
        else:
            summary["pending"] += 1

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
                "passed": str(summary["passed"]),
                "failed": str(summary["failed"]),
                "blocked": str(summary["blocked"]),
                "pending": str(summary["pending"]),
                "owners": ", ".join(sorted(summary["owners"])),
            }
        )

    return ordered


def assess_decision(rows: List[Dict[str, str]]) -> DecisionSummary:
    blockers: List[str] = []
    warnings: List[str] = []
    has_launch_stage = False
    has_critical = False
    has_any_status = False
    has_pending_status = False

    for row in rows:
        scenario = _row_label(row)
        stage_key = row.get("stage", "").strip().lower()
        severity = row.get("severity", "").strip().lower()
        status = _normalize_status(row.get("status", ""))
        owner = row.get("owner", "").strip()

        if owner == "":
            blockers.append(f'Scenario "{scenario}" is missing an owner.')

        if stage_key == "launch":
            has_launch_stage = True
            if row.get("rollback_trigger", "").strip() == "":
                blockers.append(f'Launch scenario "{scenario}" is missing a rollback trigger.')

        if status:
            has_any_status = True
        if status in {"", "not-run"}:
            has_pending_status = True

        if severity == "critical":
            has_critical = True
            if status in {"fail", "blocked"}:
                blockers.append(f'Critical scenario "{scenario}" is {status}.')
            elif status in {"", "not-run"}:
                warnings.append(
                    f'Critical scenario "{scenario}" still needs execution evidence.'
                )
        elif status in {"fail", "blocked"}:
            warnings.append(
                f'Scenario "{scenario}" is {status} but not tagged critical.'
            )

        if stage_key == "launch" and status in {"fail", "blocked"}:
            blockers.append(f'Launch scenario "{scenario}" is {status}.')

    if not has_launch_stage:
        warnings.append("No launch-stage guardrail scenario is listed.")
    if not has_critical:
        warnings.append("No critical scenario is tagged.")
    if not has_any_status:
        warnings.append(
            "No execution statuses were provided. Add actual/status columns after you run the evals."
        )
    elif has_pending_status:
        warnings.append("Some scenarios are still pending execution.")

    blockers = _dedupe(blockers)
    warnings = _dedupe(warnings)

    status = "READY"
    if blockers:
        status = "HOLD"
    elif warnings:
        status = "PENDING"

    return {
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
    }


def render_markdown(
    rows: List[Dict[str, str]],
    product_name: str = "AI product",
    decision_rule: str = DEFAULT_DECISION_RULE,
) -> str:
    decision = assess_decision(rows)
    lines = [
        "# AI Eval Scorecard",
        "",
        f"- Product: {product_name}",
        f"- Generated: {date.today().isoformat()}",
        "",
        "## Release decision rule",
        decision_rule,
        "",
        "## Launch recommendation",
        f"- Status: **{decision['status']}**",
    ]

    if decision["blockers"]:
        lines.extend(["- Blockers:"])
        lines.extend([f"  - {item}" for item in decision["blockers"]])

    if decision["warnings"]:
        lines.extend(["- Watchouts:"])
        lines.extend([f"  - {item}" for item in decision["warnings"]])

    lines.extend(
        [
            "",
            "## Stage coverage",
            "",
            "| Stage | Scenarios | Critical | Pass | Fail | Blocked | Pending | Owners |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )

    for summary in summarize_stages(rows):
        lines.append(
            (
                "| {stage} | {count} | {critical} | {passed} | {failed} | {blocked} | {pending} | {owners} |"
            ).format(
                stage=summary["stage"],
                count=summary["count"],
                critical=summary["critical"],
                passed=summary["passed"],
                failed=summary["failed"],
                blocked=summary["blocked"],
                pending=summary["pending"],
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
                "| Scenario | Metric | Threshold | Actual | Status | Severity | Owner | Failure Mode | Rollback Trigger | Notes |",
                "|---|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for row in grouped[stage_key]:
            lines.append(
                (
                    "| {scenario} | {metric} | {threshold} | {actual} | {status} | {severity} | {owner} | "
                    "{failure_mode} | {rollback_trigger} | {notes} |"
                ).format(
                    scenario=_escape_cell(row.get("scenario", "")),
                    metric=_escape_cell(row.get("metric", "")),
                    threshold=_escape_cell(row.get("threshold", "")),
                    actual=_escape_cell(row.get("actual", "")),
                    status=_escape_cell(_status_label(row.get("status", ""))),
                    severity=_escape_cell(row.get("severity", "medium") or "medium"),
                    owner=_escape_cell(row.get("owner", "")),
                    failure_mode=_escape_cell(row.get("failure_mode", "")),
                    rollback_trigger=_escape_cell(row.get("rollback_trigger", "")),
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
