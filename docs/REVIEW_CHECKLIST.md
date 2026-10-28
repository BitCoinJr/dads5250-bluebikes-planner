# First-review checklist and remaining submission work

Status: reviewable implementation in progress; **submission incomplete**. Check items only after inspecting evidence. Initial implementation and drafting are AI-assisted. Vinay’s README/UI contribution is now evidenced by PR #1; remaining contribution claims require their own evidence.

Start with the [short human review form](HUMAN_REVIEW.md), [submission handoff](SUBMISSION_PREP.md), and [recording run sheet](RECORDING_RUNSHEET.md). Existing automated evidence is retained. Satoshi's bounded seven-case and eight-topic decisions are recorded below; other unchecked items remain outside that approval.

## Administrative facts

- [x] Communication status recorded from the user's report: GitHub invitations and review requests sent to teammates' university emails; reply deadline **28 October 2026 10:00 AM EDT / 23:00 JST**. This is not verified delivery, acceptance, reply, review or contribution.
- [x] Vinay’s repository access and reply are evidenced by PR #1 on 2026-10-28. This does not establish Aditi’s access or all-member approval.
- [ ] Verify remaining member access/contribution evidence without treating silence or the deadline as approval.

- [ ] Record TA confirmation if received. Until then retain **not received / not TA-approved**. The user explicitly directed building despite the reported TA instruction to wait.
- [ ] Verify the user-supplied final deadline: **28 October 2026 23:59 ET / 29 October 2026 12:59 JST**. The older Canvas 25 October display is reported outdated, not independently verified here.
- [ ] Confirm the remote remains private: `gh repo view BitCoinJr/dads5250-bluebikes-planner --json url,isPrivate`.
- [ ] Obtain exact teaching-team GitHub usernames, grant only the required access manually, and verify the private repository and Notebook open for them.
- [ ] Keep synchronized course references unchanged; inspect the reference hash manifest and ensure no credentials or raw bulk data are staged.

## Reproducibility and real-data audit

- [ ] Run the README setup in a clean environment. Record Python version, dependency installation result, command, timestamp and exit code.
- [ ] Run the full test suite. Inspect hand-count cases for inventory conservation/reset, endpoint attribution, crew capacity, hiring delay, notice/severance, seasonal minimum duration, monthly cap and year-end obligations. Synthetic tests must remain labelled as tests.
- [ ] Confirm January 2024 Boston/Cambridge pilot evidence predates broad expansion; note that the full run supplies its missing December 2023 arrival boundary.
- [ ] Inspect `data/metadata/diagnostics.json`: all 33 requested months really processed, no silent missing-period substitution, 2024–2025 training and January–September 2026 backtest coverage.
- [ ] Distinguish 34 downloaded archives, including December 2023, from complete underlying trip coverage. Confirm partition-change evidence and deduplication of 222 cross-archive duplicate-ID pairs (141 at May/June 2024, 81 at April/May 2026).
- [ ] Explain the unquantified March-start/April-end 2026 gap and September-start/October-end right censoring. January–August metrics remove only the final boundary issue, not the internal gap. Do not fabricate replacement trips.
- [ ] Inspect the August 2026 station snapshot, retrieval-check timestamp, 13 Municipality values and dock counts. Review the retrospective-snapshot and exact-name-join limitations.
- [ ] Review per-month file extensions, archive members, actual source columns, valid counts, missing IDs/names, duplicate handling, timestamp validity and start/end join rates. Explain any weak or changing coverage.
- [ ] Check cross-month returns use end timestamps, IDs remain strings, and DST repeated local hours are netted together. No fabricated UTC offsets or missing observations.
- [ ] Verify `results/summary.json`, tables, figures and demo-script numbers refer to the same completed run. Do not fill pending results with invented figures.
- [x] Historical evidence before app integration: 64 tests passed; submission 14/14 and demo 6/6 code cells executed with outputs and zero errors; seven original-artifact hashes matched. See [baseline verification](verification-demo-revision.json). The subsequent pre-polish app revision passed 85 tests, submission 15/15 and demo 7/7 code cells, 9/9 HTTP checks and a real-kernel launch/stop check: [Gradio verification](verification-gradio.json).
- [x] Historical UI-polish checks at commit `22d4e3d`, preserved on branch `preserve/ui-polish-22d4e3d`: 93 tests; submission 16/16 and demo 8/8 code cells with outputs and zero errors; 10/10 local HTTP workflow checks; desktop/narrow browser checks for confirmation/apply and invalidation; a 3-cell real-kernel launch/stop check with the port released and zero API calls. See [UI polish verification](verification-ui-polish.json).
- [x] Current automated verification complete: **102 tests**, submission **17/17** and demo **9/9** code cells with outputs and zero errors, **13/13 HTTP checks**, desktop/narrow browser checks, and a **3-cell real-kernel launch/stop** check with HTTP 200 and port release. All made zero new real API calls. See [verification-geography.json](verification-geography.json), [HTTP evidence](verification-geography-http.json) and [kernel evidence](verification-geography-notebook.json).
- [x] Preservation verified: 100 pre-existing data/prompt/fixture/result files byte-identical to `22d4e3d`, nine model modules unchanged, planning-service AST unchanged after excluding its new display payload, and unchanged dependencies, earlier reports and shared Mermaid/SVG/PNG assets. See [verification-geography.json](verification-geography.json).
- [ ] Independently reproduce the full submission Notebook and compact `notebooks/bluebikes_demo.ipynb` from the top. Inspect every code cell for execution count, outputs and errors; open both in another viewer. A new demo link alone is not execution evidence.

## Model and planning decisions

The [eight-topic record](MODEL_REVIEW.md) establishes conditional interpretation acceptance only. The unchecked audit actions below include implementation/empirical checks outside that record; they are not blanket-approved.

- [ ] Confirm no 2026 demand enters model selection, growth estimation or base-plan calibration. Inspect the 2025 validation table.
- [ ] Explain the daily half-full reset, hourly netting, virtual external depot, counted reset work and daily supply/collection conservation. Label demand as a proxy, never observed moves or lost trips.
- [ ] Keep **120 bikes/shift** fixed. Hand-count pickup plus delivery as two handling actions using [the synthetic walkthrough](handling_unit_walkthrough.md), including the unbalanced depot case; inspect factor-one/factor-two conversion before a new optimization in `results/unit_interpretation_comparison.csv`. Compare peak crew counts, crew cash cost and shortage on the same period. Distinguish the older frozen-crew sensitivity, and keep the assumed penalty per uncovered handling action fixed.
- [ ] Confirm January's 14 initial crews are existing full-time employees. Review next-month decision timing, $6,000 monthly full-time cost, $13,500 severance and $7,800 seasonal monthly cost.
- [ ] Verify minimum three-month seasonal contracts and the system-wide eight-crew cap, including mandatory 2027 tails for late starts. Review the disclosed full-time horizon bias and continuing crew cash cost run rate.
- [ ] Resolve whether the other-city shared pool is permitted. Inspect both default shared capacity allocations and dedicated-city integer plans. Do not present fractional capacity shares as dedicated crews or route-feasible staffing.
- [ ] Compare January-September crew cash cost and observed-proxy shortage together: initial crews **$756,000 / 326,680.86 actions**, frozen proposal **$1,342,800 / 48,126.86 actions**. Verify the current CSVs. Keep annual forecast comparisons and mandatory 2027 seasonal obligations separate; never pair annual crew cash cost with nine-month shortage.
- [ ] Inspect demand −20%/+20%, assumed affected-user ratios 0/0.5/1/2 and e-bike productivity scenarios. Keep $5.70 per encounter separate from proxy units and label monetary losses as assumption-based.
- [ ] Inspect solver status/gap. Claim optimality only as supported for the specified monthly model, not actual field operations.

## Optional local Gradio app

- [ ] Independent reviewer: install the current requirements, then open `python scripts/run_app.py --port 7876` at `127.0.0.1`, with public sharing and analytics disabled. The default remains 7860; 7876 avoids older reviews on 7860 and 7872. Use an explicitly free port for another collision. The implementation's CLI/Notebook launch checks are already recorded below; confirm usability independently.
- [x] Historical 10-check HTTP rerun passed with zero real API calls and temporary port released: [verification-ui-polish.json](verification-ui-polish.json). Inspect the separate geographic verification for the current revision; independent human review below remains pending.
- [x] Both Notebooks executed with `LAUNCH_LOCAL_APP = False`: submission 17/17 and demo 9/9 code cells with outputs and zero errors, including geographic outputs. No app server or new model call was started by the disabled launcher. See [verification-geography.json](verification-geography.json). Independent reproduction remains a review item above.
- [x] Local HTTP and real-kernel launch/stop checks complete; HTTP 200, `app.close()`, zero real API calls and released temporary ports recorded in [HTTP evidence](verification-geography-http.json) and [kernel evidence](verification-geography-notebook.json). Reproduce the kernel check with `python scripts/verify_app_notebook.py --port 7878 --output docs/verification-geography-notebook.json`. The 7876 review server was stopped; older 7860/7872 reviews were left untouched.
- [ ] Inspect saved-real initialization. Opening the app must not call the model. New extraction occurs only after the explicit live button, with provenance distinct from recorded original/supplemental evidence; a missing key must remain an explicit blocked state.
- [ ] Compare source text/URL with the date, city, venue and crowd/unknown cards; inspect raw structured JSON and ambiguity notes as needed. Verify the locally cached Mermaid image matches its single editable `.mmd` source, with no runtime CDN dependency.
- [ ] Review source text/URL, JSON and ambiguity fields, explain corrections in notes, select **Confirm reviewed values (this session only)**, then explicitly **Apply to plan**. Trace its city/month increment to demand and crew decisions. Confirm edits stay in the session and preserve all frozen raw API/evaluation/reference artifacts; session review is not a completed human-gold evaluation.
- [ ] Change source, extraction/review JSON or an assumption after applying. Verify the previous applied plan is invalidated and requires another apply, rather than silently displaying stale scenario results.
- [ ] Verify dynamic KPI cards and plots match the applied scenario and selected period tab. Keep January–December forecast/cost separate from January–September observed-proxy/cost; inspect hiring decisions alongside the next month's active crews.
- [ ] Inspect the [geographic comparison](geographic_comparison.md): 613 cached station coordinates, four integer core-city crew bubbles, and a separately reported integer pool for the nine other municipalities. Verify both panels share the selected month, coordinate extent and fixed bubble-area scale. Do not show fractional pool shares as crews or invent a pool base, event marker, depot or route.
- [ ] Check the all-city city/group demand view retains forecast-proxy handling-action units and is not a station demand allocation. Changing the displayed geographic month must only select cached results, with no optimization, LLM, geocoding, tile/download or new dependency. Inspect the [geographic capture](screenshots/geography/desktop-april.jpg) and current verification; coordinate centroids are not depots, and the station snapshot remains retrospective.
- [ ] After applying, change the source, reviewed fields or scenario assumption and verify the geographic view clears alongside the earlier KPI/charts/tables. Preserve all original and supplemental raw API, evaluation, reference and human-review artifacts.
- [x] Implementation browser checks passed at **1366×900** and **390×844**: April Boston FT **12 → 13**, proxy demand **36,721 → 39,721**, separate shared pool **2 FT**; September selection changed only the geographic month while the event KPI remained April. Increment changes cleared all three plots and the KPI. See the [capture](screenshots/geography/desktop-april.jpg) and [verification-geography.json](verification-geography.json). The unchecked inspection items request independent human review, not unfinished automated checks.
- [ ] Review the 1366 px desktop and 390 px narrow layouts. Wide plots/tables should scroll internally without widening the page. Inspect captures of [flow](screenshots/ui-polish/desktop-flow.jpg), [extraction](screenshots/ui-polish/desktop-extraction.jpg), [decisions](screenshots/ui-polish/desktop-decisions.jpg), [capacity](screenshots/ui-polish/desktop-capacity.jpg), [narrow decisions](screenshots/ui-polish/narrow-decisions.jpg) and [narrow table](screenshots/ui-polish/narrow-table.jpg); screenshots alone do not establish functional correctness.
- [ ] Verify 120 course bikes/shift stays fixed during handling-unit conversion, +3,000 remains an uncalibrated retrospective scenario, and a hiring decision takes effect next month. Keep annual forecast/cost comparisons separate from nine-month observed-proxy/cost comparisons and the 2027 seasonal tail.
- [ ] Keep original four-call 19/20 and separate three-call 11/15 provisional results, participant/crowd and date failures, and Satoshi's bounded adjudications visible. Supplemental evaluation-only cases must not enter staffing.
- [ ] Stop the Notebook app with `app.close()` and the standalone app with Ctrl+C; verify the selected local port is released. Restore `LAUNCH_LOCAL_APP = False` before saving the submitted artifacts. No recording, upload, public app link or Canvas submission is implied.

## GenAI evidence

- [x] Satoshi adjudicated all seven saved-input/output cases using AI-assisted review, explicitly adjudicated by Satoshi in chat. Both review CSVs record judgments and separate notes. Record compiled 2026-10-27 JST; exact decision times unknown. See [HUMAN_REVIEW.md](HUMAN_REVIEW.md). This is not independent full-website verification or all-pass accuracy.
- [x] Eight model topics conditionally accepted as disclosed assumptions, including forecast/backtest and fixed-staffing demand/e-bike stress: [MODEL_REVIEW.md](MODEL_REVIEW.md). Nominal 120 differs from stressed effective 108; no empirical validation or TA permission inferred.
- [x] Real API evidence exists separately: four original calls in `results/event_extraction_live.json` and three supplemental calls in `results/event_extraction_additional_live.json`. Model, usage, timestamps, response IDs and hashes are retained; no credential value belongs in tracked artifacts.
- [ ] Inspect prompt instructions, the example, strict Structured Outputs and local schema validation. Review dates, URL/evidence grounding, crowd-size nulls and ambiguity handling manually.
- [ ] Preserve **19/20 original** and **11/15 supplemental** exact agreements separately, not as human-reviewed accuracy. Review the Cambridge address mismatch and unscored HOCR ambiguity. Inspect two positive counts from the same HOCR event, missing quantity qualifiers, 30,000 participants misread as crowd, unsupported dates and expanded location wording. Do not retune labels to hide failures.
- [ ] Confirm the no-key live path reports blocked/unverified with zero API calls. Mocked HTTP tests establish the contract only. Verify recorded mode reuses actual live outputs only after checking prompt/source/schema and output hashes, without issuing new API calls.
- [ ] Trace the saved Marathon record to April Boston: assumed **+3,000 actions**, forecast **36,721.19 to 39,721.19**, FT **12 to 13**, April crew cash cost **$72,000 to $78,000**. Inspect focused and full-calendar chain CSVs. Keep zero uplift as default and label the positive case **uncalibrated retrospective**, not demonstrated forecast improvement. Supplemental evaluation inputs never enter planning.

## Member participation across every deliverable

Each member should make and review substantive contributions to **all** deliverables required by the course. Choose tasks collaboratively; the table records evidence without assigning imaginary completed work. A review note should identify the artifact, what changed or was checked, and a commit/comment or dated record.

| Member | Code/data and tests | Notebook and results | README/assumptions and sources | Demo script, figures and recording |
|---|---|---|---|---|
| Satoshi Nakamura | Eight disclosed model topics adjudicated; no code/test authorship inferred | Forecast/backtest and proxy interpretation reviewed in chat; independent Notebook execution not established | Seven extraction decisions and model assumptions: [record](human_review_decisions.json) | Interpretation decisions support demo; rehearsal/recording contribution pending |
| Vinay Manikandan Nagarajan | English UI changes and prototype review in [PR #1](https://github.com/BitCoinJr/dads5250-bluebikes-planner/pull/1); app/clean-environment run self-reported | Builder review submitted; independent full Notebook rerun not evidenced | README rewrite and capacity/route-allocation review in PR #1 | Contribution now acknowledged in script; rehearsal/recording role pending |
| Aditi Rao | Pending evidence | Pending evidence | Pending evidence | Pending evidence |

Available work includes checking a raw month against its aggregate, independently hand-counting an inventory example, reviewing a crew lifecycle/cost example, inspecting an event annotation, reproducing the Notebook, explaining one sensitivity result, correcting README limitations, and rehearsing the complete demo. Contributions should span artifacts rather than imply exclusive ownership of only one deliverable.

## Demo and submission completion

- [ ] Review the generated [English narration](DEMO_SCRIPT.md) and matching [six-row run sheet](RECORDING_RUNSHEET.md): overview → Mermaid → saved source/extraction → Confirm/Apply and April KPI → fifteen-second geography → review/contribution/limits. Target 2:45–2:55; operation-only measurement is separate from narration estimates and an unmeasured spoken take. Synchronize draft overlays after recording. Update the existing analysis generator if narration changes.
- [ ] Show the problem, recorded real event JSON, focused demand/crew/cost chain, shared-month/shared-scale geographic overview, matched-period validation, unit interpretation and architecture. Keep the shared pool separate and centroids distinct from depots; there are no event markers. Distinguish four original live calls, three supplemental calls, zero-call replay and fixtures; disclose Satoshi's adjudications and remaining other-member/empirical review.
- [ ] Rehearse the English script and measure actual duration; target three minutes.
- [ ] Record the demo. **Not recorded by the implementation.**
- [ ] Upload the video and verify teaching-team access. **No upload is performed automatically.**
- [ ] Add the verified video URL to the Notebook and required submission materials, then rerun/inspect if content changes.
- [ ] Confirm all members' contributions and approvals without inventing participation.
- [ ] Submit to Canvas manually and retain the submission receipt. **No Canvas submission is performed automatically.**

## Highest-value improvements before the deadline

Feature additions stop with the geographic comparison. Focus next on independent review and recording preparation.

1. **Other-member review:** Satoshi's seven case judgments and eight conditional topics are recorded. Preserve separate 19/20 and 11/15 frozen scores and visible participant/date failures; do not infer other members' agreement.
2. **Model interpretation:** settle capacity counting and other-city sharing, then review their sensitivity and late-year full-time hiring before endorsing a staffing recommendation.
3. **Finish the actual submission:** obtain team review/contributions, record and upload the demo, verify grader access, and complete the manual Canvas workflow. Do not mark the project complete before these are done.
