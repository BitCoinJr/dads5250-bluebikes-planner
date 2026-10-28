# Documentation guide

## Start here

- [Current submission checklist](SUBMISSION_PREP.md): confirmed TA registration, deliverables and remaining actions.
- [Final video, script, subtitles and rebuilding sources](../deliverables/demo/README.md).
- [Final human review checklist](REVIEW_CHECKLIST.md).

## Technical explanations and evidence

- [Architecture and Mermaid](architecture.md)
- [Planner assumptions](planner_assumptions.md) and [scenario assumptions](scenario_assumptions.md)
- [Human adjudication](HUMAN_REVIEW.md) and [conditional model review](MODEL_REVIEW.md)
- [Event sources](event_sources.md), [supplemental sources](event_sources_additional.md), [geographic comparison](geographic_comparison.md)

## Historical implementation records

`DEVELOPMENT_LOG.md`, `DECISIONS.md`, `PR1_INTEGRATION.md`, migration notes, `EVALUATION_GATE_REVIEW.md`, and dated `verification-*.json` preserve the state and checks at their recorded revision. Earlier “pending”, “not recorded”, private-access, port or test-count statements are historical; use the current submission checklist for readiness. Historical records are retained to make changes traceable, not presented as current tasks. The previous working checklists and recording drafts are also preserved in Git history at c9583c8.

The frozen `results/summary.json` contains status flags from its original numerical run. It is retained as evidence, not a live submission tracker. Current Notebook status panels read SUBMISSION_PREP.md.
