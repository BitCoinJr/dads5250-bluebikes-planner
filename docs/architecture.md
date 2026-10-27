# Architecture and demo storyboard

AI-assisted implementation and review notes; human validation remains pending.

```mermaid
flowchart LR
  A[Official monthly trip files] --> B[Chunked station-hour counts]
  S[Current Municipality and dock snapshot] --> B
  B --> C[Daily half-full inventory handling proxy]
  C --> D[Frozen forecast trained on 2024-2025]
  E[Original four official event excerpts] --> F[Four real OpenAI structured extraction calls]
  F --> G[Saved outputs and schema checks]
  G --> H[Extracted dates and city plus declared increment]
  D --> H
  H --> I[Monthly crew MILP]
  D --> U[Explicit conversion with 120 course bikes per shift]
  U --> I
  I --> J[Annual forecast comparison and separate 2027 tail]
  I --> K[Jan-Sep crew cash cost and observed-proxy shortfall]
  C --> K
  J --> L[Full submission and compact demo Notebooks]
  K --> L
  P[Three supplemental real extraction calls] --> Q[Separate provisional evaluation and human review]
```

The supplemental evaluation has no path to demand or staffing. Its two positive crowd excerpts concern the same HOCR event, and its participant-only case exposes crowd/date grounding failures. Preserve 11/15 provisional agreement separately from the original four-call 19/20 result. Crowd qualifiers and unscored ambiguity text require review; schema validity does not establish semantic truth. All human review remains pending.

Recorded mode validates saved request/source/schema and output hashes, then replays real outputs with **zero new API calls**. Fixture mode is a separately labelled agent-authored contract test; it is not live execution evidence.

The focused demo follows the saved Marathon input: **20 April 2026, Boston, assumed +3,000 handling actions, April forecast 36,721.19 to 39,721.19, FT 12 to 13, April crew cash cost $72,000 to $78,000**. Source URL and ambiguities remain visible. The increment is uncalibrated and retrospective; it does not demonstrate forecast improvement. No 2026 actual enters forecasting or coefficient selection.

The unit comparison fixes **120 bikes/shift**. Pickup plus delivery is two handling actions. Factor two converts those to one course-bike unit before replanning and converts shortage back to handling actions. The assumed penalty per handling action stays fixed. Pairing is conditional: unbalanced city/depot handling cannot automatically be halved; inspect the [synthetic walkthrough](handling_unit_walkthrough.md). This new optimization can change crew/cost recommendations; the old frozen-plan capacity sensitivity cannot. See [scenario assumptions](scenario_assumptions.md) and the [unit comparison](../results/unit_interpretation_comparison.csv).

Figures, period tables and the script share saved computation results. January-December crew cash cost is matched to annual forecast-proxy shortage; January-September crew cash cost is matched to nine-month observed-proxy shortage. Mandatory 2027 seasonal obligations are separate. The shared other-city pool is an explicit city-rule exception, not proof of feasible routes.

Use the compact [demo Notebook](../notebooks/bluebikes_demo.ipynb) for the walkthrough and the [submission Notebook](../notebooks/bluebikes_submission.ipynb) for the full audit. Inspect both artifacts' generated cells before recording; a link is not execution evidence.

Storyboard: ordinary same-period backtest (0:00-0:30), real event text to the conditional crew decision (0:30-1:15), handling units and replanning (1:15-2:00), visible extraction failures (2:00-2:40), architecture and remaining work (2:40-3:00). [DEMO_SCRIPT.md](DEMO_SCRIPT.md) uses the same results. Rehearse to three minutes, record, upload an accessible link, verify teaching-team access and add the URL. **Video is not recorded or uploaded.** TA confirmation, all-member contributions/review and manual Canvas submission remain outstanding.
