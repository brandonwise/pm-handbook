from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import List, Optional


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


def build_case_study(title: str, problem: str, outcome: str) -> str:
    today = date.today().isoformat()
    return f"""# {title}

- Date: {today}
- Status: Draft

## Context
{problem}

## Constraints
- Limited time and engineering bandwidth
- Need clear customer impact, not activity theater
- Decisions must be explainable to leadership

## What we did
- Framed the problem as a measurable outcome
- Generated at least three options (including do-nothing)
- Chose a path with the best risk-adjusted impact
- Tracked execution weekly and adapted quickly

## Outcome
{outcome}

## Lessons learned
- Keep assumptions explicit early
- Align stakeholders before writing a giant spec
- If the metric does not move, the work is not done

## Artifacts
- PRD
- KPI tree
- Tradeoff memo
- Launch retro
"""


def create_case_study(output_dir: Path, title: str, problem: str, outcome: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(title)
    path = output_dir / f"{slug}.md"
    path.write_text(build_case_study(title, problem, outcome), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a new PM case study from a proven template.")
    parser.add_argument("--title", required=True, help="Case study title")
    parser.add_argument("--problem", required=True, help="Problem statement")
    parser.add_argument("--outcome", required=True, help="Outcome summary")
    parser.add_argument(
        "--output-dir",
        default="case-studies/examples",
        help="Directory where the markdown file should be created",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    path = create_case_study(
        output_dir=Path(args.output_dir),
        title=args.title,
        problem=args.problem,
        outcome=args.outcome,
    )

    print(f"Created: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
