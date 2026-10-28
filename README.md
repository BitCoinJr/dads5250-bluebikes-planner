# Bluebikes Crew Planner: From Event Headlines to Crew Decisions

DADS5250 — Generative AI in Practice · Group 8

## Where should rebalancing crews work—and when?

Turn trip history and reviewed event information into monthly crew plans.

### The problem

Bluebikes is Greater Boston’s bike-share system. Rebalancing means moving bikes from stations with surplus bikes to stations running short. Trips move bikes unevenly across stations: some run short of bikes; others run short of empty docks.

### The decision

Plan full-time and seasonal crews by city or planning group for each month of **2026**, including hiring and contract starts. Four cities have dedicated crews; nine others share a pool. **One crew = a driver + van.**

### AI + analytics

- **Python:** 2024–2025 trips → an inventory-based rebalancing workload proxy → monthly crew plans.
- **OpenAI:** API calls, prompt engineering and structured output extract dates, locations and audience information when stated.
- **A person:** reviews facts and supplies an explicit demand scenario before applying it to the Python planner.
- **Backtest:** January–September 2026 trips are held out for evaluation, separately from training.

### Illustrative scenario — saved Marathon example

This fixed explanation example is independent of your event selection in the app. Values are checked against the [saved focused calculation](results/focused_event_chain.csv).

**Boston / April 2026**

- **12 → 13 full-time crews**
- **$72,000 → $78,000 monthly crew cash cost**
- **Hiring decision: March 2026**
- **Assumes +3,000 handling actions**

This is an **uncalibrated retrospective scenario**, not a measured event effect or evidence of improved forecast accuracy. Baseline means a **model plan**, not actual Bluebikes crew deployment. OpenAI extracts text; it does not predict added demand or crew counts.

## How it works

![Historical data, OpenAI event extraction, human review, Python crew planning and held-out evaluation](docs/diagrams/bluebikes_flow.svg)

The [Mermaid source](docs/diagrams/bluebikes_flow.mmd) is the single editing source for the diagram shared by the app and both Notebooks. See [architecture](docs/architecture.md) for details.

**Submission is incomplete.** Vinay's review and README/UI contribution are evidenced by [PR #1](https://github.com/BitCoinJr/dads5250-bluebikes-planner/pull/1). Aditi's contribution, all-member review, TA confirmation, a spoken rehearsal, video recording/upload, grader access and Canvas submission remain pending. Keep the repository private; a link alone does not grant grader access. See [submission preparation](docs/SUBMISSION_PREP.md) and the [review checklist](docs/REVIEW_CHECKLIST.md).

## Course techniques used

| Technique | Where and why |
|---|---|
| **API calls** | OpenAI Responses API through `requests` in [events.py](bluebikes/events.py) obtains event extractions. |
| **Prompt engineering** | The [versioned prompt](prompts/event_extraction_v1.txt) defines route conventions, unknown values and participants versus spectators. |
| **Structured output** | A [strict JSON schema](prompts/event_schema.json) constrains the response; local validation and human confirmation precede planning. Structural validation alone does not prove factual correctness. |

## Quick start

Developed and verified on **Python 3.13.2** with [pinned dependencies](requirements.txt). Other Python/platform combinations have not been independently verified in this integration. Clone with an account that has access to this private repository. No OpenAI key or raw-data download is needed for saved-response replay.

**macOS / Linux**

```bash
git clone https://github.com/BitCoinJr/dads5250-bluebikes-planner.git
cd dads5250-bluebikes-planner
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/run_app.py --port 7881
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/BitCoinJr/dads5250-bluebikes-planner.git
cd dads5250-bluebikes-planner
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/run_app.py --port 7881
```

If already in the project, use the existing environment rather than cloning or recreating it. Open [the local app](http://127.0.0.1:7881) and stop it with Ctrl+C. If this port is occupied, choose a free port and use it in both the command and URL. The app binds to `127.0.0.1`, with sharing and analytics disabled; it creates no public link. The CLI default is still 7860.

### Notebook submission

Open the executed [submission Notebook](notebooks/bluebikes_submission.ipynb) or [compact demo Notebook](notebooks/bluebikes_demo.ipynb) in VS Code/Jupyter. To regenerate and execute, use the environment's Python with `scripts/build_notebook.py --execute` and `scripts/build_demo_notebook.py --execute`. Jupyter's browser interface is optional; install `notebook` if that interface is needed. Test failures stop submission verification; resolve them rather than treating failed checks as success.

Both Notebooks keep `LAUNCH_LOCAL_APP = False` by default. Optional app launch uses the same implementation; call `app.close()` when finished and restore the flag to False before submission. Cached replay is the default; fixture tests are distinct from actual model results.

### App walkthrough

1. Select the **original Boston Marathon**; the initial view loads its saved real response. **Load saved real response** explicitly replays it again.
2. Compare the source with dates, location, unknown spectators and separate human annotations.
3. Click **Confirm reviewed values (this session only)**, retain the illustrative **+3,000 handling actions** and conversion **1**, then **Apply to plan**.
4. Inspect Boston's April KPI, March hiring decision, monthly charts and the same-month geographic comparison. Set the geographic selector to **April 2026**.

Changing source, reviewed fields or assumptions clears the prior result. Reviews stay in session and never overwrite frozen API outputs or evaluation records. **Evaluation only — excluded from staffing plans:** all three supplemental cases remain inspectable but cannot enter a plan, even after edits and confirmation; the server also enforces this restriction.

The station-coordinate view is not a route map. Four core cities have dedicated whole crews; the nine-city pool is shown separately. Centroids are not actual bases or event locations.

### Optional new extraction

Only **Extract with OpenAI** makes a new call. Configure the Git-ignored project `.env` using [.env.example](.env.example) without overwriting an existing credential file. Set `OPENAI_API_KEY` locally; the default model is `gpt-4.1-mini`. Failed live calls do not silently substitute recorded results. A new app response stays in session memory. Do not use the legacy live CLI in this evidence checkout: it can overwrite the canonical saved response even with a different output argument. Never commit or display credentials.

## Results and their scope

The pipeline retained **12,893,134 trips across January 2024–September 2026**, covering 33 requested months and 13 municipalities; this total includes the held-out period. Only **2024–2025** trains the forecast. Crew optimization balances cash cost and an assumed shortage penalty under capacity, hiring and contract constraints; it does not simply minimize payroll.

| Period and service basis | Plan | Crew cash cost | Uncovered handling-action proxy |
|---|---|---:|---:|
| Jan–Dec 2026 forecast | Initial 14 crews held fixed | $1,008,000 | 365,295.14 |
| Jan–Dec 2026 forecast | No-event optimized plan | $1,837,200 | 10,006.65 |
| Jan–Sep 2026 observed-trip proxy | Initial 14 crews held fixed | $756,000 | 326,680.86 |
| Jan–Sep 2026 observed-trip proxy | No-event optimized plan | $1,342,800 | 48,126.86 |

- **Forecast:** 9.68% WAPE over January–September 2026; January–August is 10.29%. Boundary gaps/censoring and the retrospective station snapshot limit interpretation; see [data diagnostics](data/metadata/diagnostics.json) and the [development record](docs/DEVELOPMENT_LOG.md).
- **Extraction:** original four-call agreement is **19/20**; the separate three-call challenge is **11/15**, against frozen AI-drafted references. Satoshi's seven later adjudications are separate annotations, not a replacement accuracy score. The participant/date failure remains visible. See [human review](docs/HUMAN_REVIEW.md).
- **Marathon:** the assumed Boston April increment produces the fixed example above. April's **+$6,000** differs from the **+$7,200 all-city annual** cash change. Neither demonstrates measured event impact or forecasting improvement.

## Key assumptions and limitations

- **Workload is a proxy:** stations reset to half-full daily. Boundary supply/collection and reset handling are counted. This is not observed rebalancing, lost trips or customer loss.
- **Capacity and units:** nominal capacity stays **120 course bikes/shift, 6 shifts/week**, prorated by calendar days/7. A pickup and delivery are two handling actions. The default conversion is one action per course bike; factor-two pairing is a separate conditional scenario. Full-time crews cost $6,000/month; seasonal crews cost $7,800/month. Hiring starts the following month; seasonal contracts last at least three months, with a system-wide cap of eight.
- **The event increment is assumed:** under conversion **1**, April capacity per crew is `120 × 6 × 30 / 7 ≈ 3,086` handling actions. Thus +3,000 is close to one crew-month and helps explain the +1 result. It does not guarantee exactly one extra crew: baseline spare capacity and full-year hiring/contracts also matter. At conversion **2**, the handling-action comparison changes. OpenAI does not estimate this coefficient.
- **Boston-only event allocation:** Boston is the named route endpoint convention. The [official 2026 B.A.A. course map](https://www.baa.org/wp-content/uploads/2026/03/2026-Course-Map.pdf) also includes Newton and Brookline, but this scenario assigns them no additional event demand. This route check is contextual evidence, not an addition to the frozen extraction input or evaluation labels.
- **Retrospective scenario:** event evidence was collected in October 2026; the nonzero comparison is a what-if illustration, not a forecast available in January. Recurring events may already be represented in seasonality.
- **Shared pool and geography:** other-city capacity sharing is an explicit policy assumption, not dedicated staffing or a route-feasibility guarantee. The current 613-station snapshot does not reconstruct historical station openings/capacities.
- **Evaluation limits:** reference labels were AI-drafted; human review covered the supplied excerpts and disclosed assumptions. It does not establish independent gold-standard accuracy, empirical operational validity or TA approval.

See [planner assumptions](docs/planner_assumptions.md), [scenario assumptions](docs/scenario_assumptions.md), [model review](docs/MODEL_REVIEW.md) and [event sources](docs/event_sources.md).

## Three-minute demo preparation

Use the [English script](docs/DEMO_SCRIPT.md), [one-to-one recording run sheet](docs/RECORDING_RUNSHEET.md) and [draft emphasis captions](docs/recording_overlays.srt). The current script is **307 written words**, approximately **322** with numeric expansion, targeting **2:45–2:55**. A spoken full take is **not measured**. The earlier **14.424-second operation-only** run excludes narration and viewing pauses; it does not establish video duration. Captions must be synchronized after recording. Vinay's evidenced PR contribution is now acknowledged; Aditi and narrator/operator assignments remain pending.

## Repository layout and sources

| Location | Contents |
|---|---|
| `bluebikes/` | Data, inventory proxy, forecast, planner, event extraction and app |
| `notebooks/` | Executed submission and demo Notebooks |
| `prompts/`, `fixtures/` | Versioned prompt/schema and saved source excerpts |
| `data/` | Small monthly aggregates and provenance; raw data/caches are excluded |
| `results/` | Plans, figures, saved real API responses and evaluation |
| `scripts/`, `tests/` | Reproducible commands and verification |
| `docs/` | Assumptions, reviews, architecture and recording preparation |

Official trip/station sources: [Bluebikes System Data](https://bluebikes.com/system-data) and the [trip-data bucket](https://s3.amazonaws.com/hubway-data/index.html). Object names and hashes are in `data/metadata/`. Event provenance is in [event_sources.md](docs/event_sources.md). Optional full reacquisition uses `scripts/acquire_data.py --workers 4`; it downloads large raw files and is unnecessary for cached review. Use a separate checkout/cache for intentional data or model experiments.

## Team contributions and AI use

| Member | Evidence and scope |
|---|---|
| Satoshi Nakamura | Project lead directing AI-assisted development and integration; adjudicated seven event cases and eight conditional model topics in the [recorded review](docs/human_review_decisions.json). This does not imply independent authorship of every generated line. |
| Vinay Manikandan Nagarajan | [PR #1](https://github.com/BitCoinJr/dads5250-bluebikes-planner/pull/1) demonstrates a README rewrite, English UI changes and concrete review suggestions, including the capacity and route-allocation limitations. His clean-environment/app run and hand-checks are self-reported in the PR; they are not treated as an independently reproduced full Notebook run. |
| Aditi Rao | Contribution and review evidence pending. |

Codex/ChatGPT assisted initial implementation, tests, documentation, prompt, draft references and demo preparation. Vinay reports Claude assistance for his review. The runtime GenAI feature is OpenAI structured extraction. Members remain responsible for reviewing AI-assisted work; these records do not establish all-member contribution to every deliverable or completed submission.

The [PR integration record](docs/PR1_INTEGRATION.md) explains accepted changes and safeguards retained. [DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md) preserves the longer pre-PR README as a historical snapshot; [DECISIONS.md](docs/DECISIONS.md) and current submission/review documents retain the detailed audit trail.
