# First-review checklist and remaining submission work

Status: reviewable implementation in progress; **submission incomplete**. Check items only after inspecting evidence. Initial implementation and drafting are AI-assisted. Names below are group membership, not attributed contributions.

## Administrative facts

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
- [ ] Execute `scripts/build_notebook.py --execute` from the top; inspect every code cell for execution count, outputs and errors. Open the final `.ipynb` in another viewer.

## Model and planning decisions

- [ ] Confirm no 2026 demand enters model selection, growth estimation or base-plan calibration. Inspect the 2025 validation table.
- [ ] Explain the daily half-full reset, hourly netting, virtual external depot, counted reset work and daily supply/collection conservation. Label demand as a proxy, never observed moves or lost trips.
- [ ] Resolve the capacity unit: does 120 bikes mean 120 handling actions or 120 completed pickup-and-delivery relocations? Inspect the factor-two scenario before endorsing staffing numbers.
- [ ] Confirm January's 14 initial crews are existing full-time employees. Review next-month decision timing, $6,000 monthly full-time cost, $13,500 severance and $7,800 seasonal monthly cost.
- [ ] Verify minimum three-month seasonal contracts and the system-wide eight-crew cap, including mandatory 2027 tails for late starts. Review the disclosed full-time horizon bias and continuing payroll run rate.
- [ ] Resolve whether the other-city shared pool is permitted. Inspect both default shared capacity allocations and dedicated-city integer plans. Do not present fractional capacity shares as dedicated crews or route-feasible staffing.
- [ ] Compare frozen proposed and initial-crew plans on actual-derived January–September 2026 proxy demand. Inspect WAPE, bias, shortage and crew cash cost separately.
- [ ] Inspect demand −20%/+20%, assumed affected-user ratios 0/0.5/1/2 and e-bike productivity scenarios. Keep $5.70 per encounter separate from proxy units and label monetary losses as assumption-based.
- [ ] Inspect solver status/gap. Claim optimality only as supported for the specified monthly model, not actual field operations.

## GenAI evidence

- [ ] Have humans inspect and correct all four initial event answer keys; record reviewer and disagreements. Existing labels were authored by the implementation agent and are not genuine human-reviewed gold yet.
- [x] Configure `OPENAI_API_KEY` locally without committing or displaying it. Four actual OpenAI Responses API calls completed; credential-free model, usage, timestamps, response IDs and request/output hashes are recorded in `results/event_extraction_live.json`.
- [ ] Inspect prompt instructions, the example, strict Structured Outputs and local schema validation. Review dates, URL/evidence grounding, crowd-size nulls and ambiguity handling manually.
- [ ] Evaluate live extracted fields against the human-reviewed answer keys. Report the actual score and errors; never score expected fixtures against themselves as LLM accuracy.
- [ ] Confirm the no-key live path reports blocked/unverified with zero API calls. Mocked HTTP tests establish the contract only. Verify recorded mode reuses actual live outputs only after checking prompt/source/schema and output hashes, without issuing new API calls.
- [ ] Inspect event-to-plan changes for the declared +3,000-action scenario and zero-uplift default. The effect is assumed and uncalibrated, recurring effects may be double-counted, and the source calendar is retrospective rather than January-available information.

## Member participation across every deliverable

Each member should make and review substantive contributions to **all** deliverables required by the course. Choose tasks collaboratively; the table records evidence without assigning imaginary completed work. A review note should identify the artifact, what changed or was checked, and a commit/comment or dated record.

| Member | Code/data and tests | Notebook and results | README/assumptions and sources | Demo script, figures and recording |
|---|---|---|---|---|
| Satoshi Nakamura | Pending evidence | Pending evidence | Pending evidence | Pending evidence |
| Vinay Manikandan Nagarajan | Pending evidence | Pending evidence | Pending evidence | Pending evidence |
| Aditi Rao | Pending evidence | Pending evidence | Pending evidence | Pending evidence |

Available work includes checking a raw month against its aggregate, independently hand-counting an inventory example, reviewing a crew lifecycle/cost example, inspecting an event annotation, reproducing the Notebook, explaining one sensitivity result, correcting README limitations, and rehearsing the complete demo. Contributions should span artifacts rather than imply exclusive ownership of only one deliverable.

## Demo and submission completion

- [ ] Review generated `docs/DEMO_SCRIPT.md` against `results/summary.json`; correct interpretations in the generator before regenerating.
- [ ] Show the problem, an event excerpt and structured JSON, the resulting plan change, held-out validation, and architecture/strengths. Disclose fixtures and incomplete live API evidence if still applicable.
- [ ] Rehearse the English script and measure actual duration; target three minutes.
- [ ] Record the demo. **Not recorded by the implementation.**
- [ ] Upload the video and verify teaching-team access. **No upload is performed automatically.**
- [ ] Add the verified video URL to the Notebook and required submission materials, then rerun/inspect if content changes.
- [ ] Confirm all members' contributions and approvals without inventing participation.
- [ ] Submit to Canvas manually and retain the submission receipt. **No Canvas submission is performed automatically.**

## Highest-value improvements before the deadline

1. **Human evaluation of real extraction:** review the four saved API outputs and the frozen provisional labels; retain the measured 19/20 exact agreement and inspect the unscored HOCR ambiguity caveat. Live API execution is complete; human-reviewed reference answers remain pending.
2. **Model interpretation:** settle capacity counting and other-city sharing, then review their sensitivity and late-year full-time hiring before endorsing a staffing recommendation.
3. **Finish the actual submission:** obtain team review/contributions, record and upload the demo, verify grader access, and complete the manual Canvas workflow. Do not mark the project complete before these are done.
