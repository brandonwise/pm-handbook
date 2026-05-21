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
scenario,stage,metric,threshold,actual,owner,severity,status,failure_mode,rollback_trigger,notes
Billing dispute with incomplete history,offline,Task success,>=0.90,0.94,PM + Eng,critical,pass,Wrong refund answer,,Use real support transcripts
Escalation handoff under heavy queue,shadow,Escalation latency,<2 min,95 sec,Support Ops,high,pass,Escalation loop,,Compare against manual baseline
Low-confidence policy question in beta,launch,Unsafe answer rate,<1%,0.4%,PM + Support Ops,critical,pass,No safe fallback,>1% for 1 day,Monitor daily during rollout
```

Leave `actual`, `status`, and `rollback_trigger` blank while you are still drafting the eval plan.
Fill them in after execution to get a real ship/hold/pending recommendation.

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
- Which scenarios still need evidence before the decision can move from pending to ready?
