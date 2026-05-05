# AI Eval Scorecard Template

Use this when you're shipping an AI workflow and need a ship/hold decision that survives contact with reality.

## Product or workflow
-

## User job to be done
-

## Primary outcome metric
-

## Release decision rule
- Launch only if every critical scenario meets threshold and no red-line failure mode is unresolved.

## Red-line failure modes
- Wrong answer that creates customer or compliance risk
- Hallucinated policy, pricing, or workflow step
- Missing escalation when confidence is low

## Scenario inventory CSV

```csv
scenario,stage,metric,threshold,owner,severity,failure_mode,notes
Billing dispute with incomplete history,offline,Task success,>=0.90,PM + Eng,critical,Wrong refund answer,Use real support transcripts
Escalation handoff under heavy queue,shadow,Escalation latency,<2 min,Support Ops,high,Escalation loop,Compare against manual baseline
Low-confidence policy question in beta,launch,Unsafe answer rate,<1%,PM + Support Ops,critical,No safe fallback,Monitor daily during rollout
```

## Generate the scorecard

```bash
python tools/generate_eval_scorecard.py \
  --input path/to/evals.csv \
  --product-name "Support copilot" \
  --output templates/generated/ai-eval-scorecard.md
```

## Review prompts
- Which scenarios are truly red-line failures?
- Which thresholds would block launch today?
- Which launch-stage metrics need an explicit rollback trigger?
