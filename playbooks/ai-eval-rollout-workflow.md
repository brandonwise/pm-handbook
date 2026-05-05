# AI Eval Rollout Workflow

1. Pick the user job, not the model trick.
2. Name the red-line failures before you look at a single demo.
3. Capture 10-20 real scenarios from support tickets, user sessions, and internal edge cases.
4. Define one metric and one threshold per scenario.
5. Tag each scenario by stage: offline, shadow, or launch.
6. Generate the scorecard and review it with engineering and ops.
7. Hold the launch if any critical scenario misses threshold or lacks an owner.

## Guardrails
- No launch on vibes alone.
- No “we’ll monitor later” without a rollback trigger.
- No critical scenario without a named owner.
- No eval set made only from happy-path prompts.

## Minimum viable review
- 3 offline scenarios that represent the main user job
- 1 adversarial or abuse case for each critical flow
- 1 launch-stage guardrail metric tied to customer risk
