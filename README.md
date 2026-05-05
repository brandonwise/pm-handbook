# pm-handbook

No fluff. Just practical PM execution assets that hold up in real teams.

This repo is built for technical PMs who want reusable systems instead of blank-page anxiety.

## What's inside

### Templates
- `templates/prd-template.md`
- `templates/kpi-tree-template.md`
- `templates/ai-eval-scorecard-template.md`
- `templates/tradeoff-memo-template.md`
- `templates/launch-readiness-template.md`
- `templates/stakeholder-update-template.md`
- `templates/postmortem-template.md`
- `templates/prioritization-scorecard-template.md`

### Playbooks
- `playbooks/weekly-operating-rhythm.md`
- `playbooks/ai-pm-discovery-workflow.md`
- `playbooks/ai-eval-rollout-workflow.md`
- `playbooks/decision-quality-checklist.md`

### Case studies
- `case-studies/examples/` includes sanitized examples
- `tools/new_case_study.py` generates new case studies from a repeatable structure

### Prioritization workflows
- `templates/prioritization-scorecard-template.md` gives a lightweight scoring rubric
- `tools/prioritize_features.py` ranks candidate features from CSV into a decision-ready markdown backlog

### AI eval workflows
- `templates/ai-eval-scorecard-template.md` helps PMs define scenarios, thresholds, and launch guardrails
- `tools/generate_eval_scorecard.py` turns a simple CSV into a decision-ready eval scorecard for AI products

## Why this exists

Most PM docs fail for one of two reasons:

1. They are too vague to guide execution
2. They are too heavy to keep updated

This handbook aims for the middle: crisp enough to drive action, light enough to maintain weekly.

## Quick start

```bash
python tools/new_case_study.py \
  --title "Agent Reliability Rollout" \
  --problem "Support escalations were rising due to inconsistent AI responses" \
  --outcome "Escalations dropped by 31% in six weeks"

python tools/prioritize_features.py \
  --input path/to/features.csv \
  --output templates/generated/prioritized-backlog.md

# Optional hard constraints to avoid low-confidence roadmap noise
python tools/prioritize_features.py \
  --input path/to/features.csv \
  --min-confidence 3.0 \
  --min-strategic-fit 3.0

python tools/generate_eval_scorecard.py \
  --input path/to/evals.csv \
  --product-name "Support copilot" \
  --output templates/generated/ai-eval-scorecard.md
```

The prioritizer now supports hard constraints (`--min-confidence`, `--min-strategic-fit`) and writes an
"Excluded by hard constraints" section in the markdown output so tradeoffs stay visible.

The eval scorecard generator gives PMs a lightweight way to review offline, shadow, and launch-stage AI quality
in one place with an explicit ship/hold rule.

## Usage pattern

1. Start with a template
2. Publish a weekly update
3. Capture real outcomes
4. Archive lessons into a case study

## License

MIT
