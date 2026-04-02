# Prioritization Scorecard Template

Use this when the roadmap gets noisy and every request sounds urgent.

## 1) Score each candidate feature (1-5 scale)

- **Reach**: How many customers/users are affected?
- **Impact**: How much measurable outcome movement do we expect?
- **Confidence**: How sure are we based on evidence, not gut feel?
- **Strategic Fit**: How aligned is this to current strategy/company goals?
- **Effort**: Relative engineering/design effort (higher = harder)

## 2) Use this CSV structure

```csv
feature,reach,impact,confidence,strategic_fit,effort
Slack escalation digest,4,5,4,5,2
Bulk policy editor,3,4,3,4,4
Customer health score export,5,3,3,3,2
```

## 3) Generate ranked backlog

```bash
python tools/prioritize_features.py \
  --input path/to/features.csv \
  --output templates/generated/prioritized-backlog.md
```

Formula used by default:

`((Reach×0.30) + (Impact×0.35) + (Confidence×0.20) + (Strategic Fit×0.15)) ÷ Effort`

## 4) Sanity checks before committing roadmap

- Top 3 items all connect to one measurable outcome
- At least one near-term (<2 sprint) delivery candidate
- At least one strategic investment candidate
- "Do nothing" option documented for major bets
