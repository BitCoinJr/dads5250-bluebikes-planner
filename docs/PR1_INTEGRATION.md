> Historical record. For current registration, deliverables and remaining actions, see [submission status](SUBMISSION_PREP.md). Earlier status statements below are preserved as recorded.

# PR #1 integration review

Client review date: 2026-10-28 JST. Reviewed Vinay's [PR #1](https://github.com/BitCoinJr/dads5250-bluebikes-planner/pull/1), original head `db79fb0`, against `a373335`. The PR contains two member-authored commits; integration retains their history. Its README conflicts with the new Executive Summary and recording preparation on main.

## Accepted and combined

- Keep the four-part Executive Summary and Bluebikes/rebalancing introduction from main. Adopt the grader-oriented README structure, cross-platform setup, course-technique table and concise results/limitations.
- Use English-only extraction, replay and Apply labels; synchronize active documentation and Notebook Markdown. Preserve the narrow-screen diagram scrolling hint.
- State the scale of the assumed event increment with its unit condition: April has `120 × 6 × 30 / 7 = 3,085.714` course-bike units per crew, equivalent to handling actions only at conversion 1. A +3,000 assumption is close to that scale, but spare capacity and full-year employment constraints still determine the result.
- Explain Boston-only allocation despite the multi-city route, with the [official 2026 B.A.A. course map](https://www.baa.org/wp-content/uploads/2026/03/2026-Course-Map.pdf). Do not import this contextual check into frozen event inputs or reference labels.
- Credit Vinay's observable README/UI edits and review suggestions. His clean-environment run and hand-checks are member-reported, not an independently audited full Notebook rerun. Aditi, all-member approval and narrator/operator agreement remain pending.
- Replace the obsolete narration sentence about all other members being unconfirmed with “Vinay reviewed documentation and usability.” Its five-word length preserves 307 written / approximately 322 expanded words. Spoken duration remains unmeasured; the prior 14.424-second automated operation run remains historical.
- Keep the long README as a labelled pre-PR snapshot in DEVELOPMENT_LOG.md with adjusted relative links.

## Changes corrected or not adopted

- **Notebook test failures:** retain `assert check.returncode == 0`. A dependency problem or any other failed test must not become a generic warning followed by apparent submission readiness. No empirical basis supports assuming every failure is an optional-package issue.
- **Review provenance/date:** retain the original method, compiled date and missing individual timestamps. A compiled date is not a verified per-case review date; raw human records and display provenance remain unchanged.
- **Data period:** the 12,893,134 retained-trip total covers 2024 through September 2026, not 2024–2025 training alone.
- **Optimization objective:** explain crew cash cost plus the assumed shortage penalty; do not call this payroll-only minimization.
- **Python compatibility:** retain the verified 3.13.2 environment; do not promise unverified Python 3.11+ compatibility for the pinned dependencies.
- **Platform metadata:** exclude .DS_Store from the final tree and ignore it going forward.

## Verification scope

Machine-readable review checks are in `verification-pr1-integration.json`. Notebook preservation is in [verification-pr1-notebook-preservation.json](verification-pr1-notebook-preservation.json): only Markdown labels/status change; code cells, execution counts and saved outputs remain unchanged. No Notebook rerun is claimed.

The model calculations, forecast/plan artifacts, event inputs/prompts, raw API evidence, human adjudications, evaluation scores and Mermaid sources are preserved against a373335. No new real API call, message to a teammate, access change, recording, upload or Canvas submission is part of this integration.
