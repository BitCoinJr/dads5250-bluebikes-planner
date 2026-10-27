# Submission preparation handoff

**Features frozen. Submission incomplete.** Working root: `C:\dev\university\dads5250-bluebikes-planner`. Baseline implementation: `8293573de2d1987c1ce24dca9b1267196466b3be`. This preparation pass adds review/recording materials and wording clarifications, not model features.

## Contact is separate from contribution

The user reports sending GitHub invitations and review requests to teammates' university emails. **Reply deadline: 28 October 2026, 10:00 AM EDT = 14:00 UTC = 23:00 JST.** Exact send time, delivery, acceptance and replies were not independently checked. An invitation, request, acceptance, silence or elapsed deadline is not proof of review/contribution. Keep the member evidence table in [REVIEW_CHECKLIST.md](REVIEW_CHECKLIST.md) pending until a dated artifact/comment/change is supplied.

User-supplied submission deadline: **28 October 2026 23:59 EDT = 29 October 2026 12:59 JST**. This is later than the team reply cutoff. The older Canvas date is reported outdated; no live Canvas check is claimed. TA confirmation remains not received; work is not TA-approved.

## What is being compared

| Label | Meaning | Does not establish |
|---|---|---|
| Real trips / station points | Observed customer trips; existing August 2026 station locations and docks | Actual crew deployment, operator moves, historical station configuration, lost trips |
| Initial crews | Course starting headcount, assumed existing FT, held constant for a comparator | An independently audited Bluebikes staffing roster |
| Baseline: no event increment | Optimized frozen forecast plan, corresponding to the proposal in the ordinary backtest | The operator's current territory/resource allocation |
| Reviewed event scenario | Same planner plus reviewed city/month facts and an assumed increment | Verified event effect or causal forecast improvement |
| Geography | Station-coordinate context with modeled integer crews at city means; shared pool separately | Depots, event venues, routes or dedicated crews in each pooled city |

The Marathon's Boston endpoint mapping is a convention for a multi-city route. No event marker is inferred. **+3,000 handling actions** is an uncalibrated retrospective user assumption; OpenAI extracts facts, not this coefficient. Recurring events may already be in seasonal demand. Supplemental audience tests are excluded from staffing.

Course capacity stays **120 bikes/shift × 6 shifts/week × days/7**. Base conversion: 1 handling action/course-bike unit; factor 2 assumes pairing pickup and delivery. Cost and uncovered work use the declared conversion and same horizon. Shortage means **estimated uncovered rebalancing work**, not measured lost trips. $5.70 is per affected rider encounter; converting actions to encounters is another assumption.

## Verified numeric reference

Boston / **April 2026** focused scenario: demand **36,721.19→39,721.19 handling actions**, FT **12→13**, seasonal **0→0**, monthly crew cash **$72,000→$78,000**, hiring decision **March 2026**. April capacity: 120×6×30/7 = **3,085.71 course-bike units/crew**. This is a city-month comparison.

The following are **whole-system** comparisons; each row's cost and shortage cover the same period. Source: [scenario_period_comparison.csv](../results/scenario_period_comparison.csv).

| Period / shortage basis | Plan | Crew cash in period | Uncovered handling actions |
|---|---|---:|---:|
| Jan–Dec forecast | Initial course crews held fixed | $1,008,000 | 365,295.14 |
| Jan–Dec forecast | Optimized no-event baseline | $1,837,200 | 10,006.65 |
| Jan–Dec forecast | Focused Marathon +3,000 | $1,844,400 | 10,006.65 |
| Jan–Dec forecast | Full-calendar +3,000/event | $1,852,200 | 11,037.72 |
| Jan–Sep observed-trip proxy | Initial course crews held fixed | $756,000 | 326,680.86 |
| Jan–Sep observed-trip proxy | Optimized no-event baseline | $1,342,800 | 48,126.86 |
| Jan–Sep observed-trip proxy | Focused Marathon +3,000 | $1,339,800 | 45,740.43 |
| Jan–Sep observed-trip proxy | Full-calendar +3,000/event | $1,355,400 | 39,363.29 |

Current base/focused/calendar mandatory 2027 seasonal tails are $0, separate from 2026 cash. Contract changes outside April explain the focused all-city annual cash difference **+$7,200** and Jan–Sep difference **−$3,000**. Neither is the **+$6,000 Boston-April** delta. Do not substitute full-calendar numbers for the single-Marathon demo. Retrospective service comparisons do not demonstrate forecast improvement.

## Verification reused and narrowed

[Geographic verification](verification-geography.json) records the latest full computational run: **102 tests; submission 17/17 and demo 9/9 executed code cells with outputs/no errors; 13 HTTP checks; desktop/narrow browser checks; actual kernel launch/stop**. Historical reports retain their original hashes/timestamps.

The earlier preparation pass preserved all code cells/outputs and changed only explanations. The later human-adjudication integration updates review-only cells/outputs and adds current notes; numerical results, raw API artifacts, inputs, scores and model logic remain preserved. The [preparation audit](verification-submission-prep.json) records fresh hash/AST checks, relevant UI/presentation tests, package checks and review-status inspection. No raw acquisition, reprocessing, new OpenAI call or full Notebook recomputation is needed for prose-only changes. Do not represent earlier execution as newly performed. Two edited Python modules change UI wording / the script generator only; prior run metadata remains the prior execution record.

Existing package pins were inspected; fresh clean-machine installation and independent reproduction remain pending. A modified calculation, prompt, input, dependency or code cell would require relevant tests and Notebook execution again.

## Submission checklist and evidence

| Status | Requirement | Completion evidence |
|---|---|---|
| SATOSHI ADJUDICATION RECORDED | [Short review form](HUMAN_REVIEW.md); scores preserved separately | Seven cases recorded with method, rationale and compiled date; three HOCR annotations applied separately, one participant/date failure; other members pending |
| READY FOR REHEARSAL | [Script](DEMO_SCRIPT.md), [run sheet](RECORDING_RUNSHEET.md), [draft subtitles](recording_overlays.srt) | Actual total ≤180s and map 10–15s in [blank log](rehearsal_log.csv); NOT MEASURED |
| VERIFIED AUTOMATED EVIDENCE | Executed Notebooks, source/results and pinned requirements | Existing full verification + differential audit; independent clean reproduction pending |
| PENDING | TA confirmation and deadline verification | Actual reply/official course record, date and reference |
| PENDING | Teammate acceptance, response and contributions across deliverables | Actual access and dated review/change evidence per member; invitation alone does not qualify |
| PENDING | Video recording, upload, readable captions/map | Final file/URL, measured duration, playback check at submitted size |
| PENDING | Grader private-repo and video access | Correct permitted viewer verifies both; owner success is insufficient |
| PENDING | Final required submission files/link | Verified video URL in materials; preserve outputs and inspect revised artifact |
| PENDING | Manual Canvas submission | Submission receipt, timestamp and required files/URL confirmed |

### Repository and video access

Keep the repository **private**. Obtain exact grader/teaching-team GitHub accounts through the normal course process; verify intended recipients and accepted access. Teammate university-email invitations do not establish grader access. A collaborator gains access after accepting an invitation: [GitHub's official documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository). No access or visibility change was made in this pass.

A permitted non-owner viewer should open the exact final commit and rendered Notebook, download the `.ipynb` if needed, and see saved outputs without a local API key. A private-repo URL alone grants no access. Use the course-permitted video destination, verify processing/audio/captions, and test playback as the grader or an equivalent permitted viewer. A localhost app link is not a video or grader-accessible deployment. Do not make the repo public as a shortcut.

### Files and launch

Preserve/submit course-required items manually; this is not a claim that Canvas requires the entire repository.

- [Executed submission Notebook](../notebooks/bluebikes_submission.ipynb), [demo Notebook](../notebooks/bluebikes_demo.ipynb), [README](../README.md), `bluebikes/`, scripts and [requirements.txt](../requirements.txt).
- Committed `data/processed/monthly.csv`, small station/diagnostic metadata, `fixtures/`, `prompts/`, saved real API/evaluation records, `results/` and shared diagram assets. Ignored raw trips and station-hour caches are unnecessary for cached replay.
- Follow README setup, then `scripts/run_app.py --port 7876`. Use `scripts/build_notebook.py --execute` / `scripts/build_demo_notebook.py --execute` when a rerun is needed. Notebook launcher stays `LAUNCH_LOCAL_APP = False`; stop an opted-in app with `app.close()`, standalone with Ctrl+C.
- New API extraction only: set `OPENAI_API_KEY` locally in ignored `C:\dev\university\dads5250-bluebikes-planner\.env`; optional `OPENAI_MODEL` is configurable. Never put secrets in `.env.example`, Notebook, recording or logs. Saved mode needs no key. Live errors are explicit, without silent saved-result substitution.
- Before final handoff, inspect Git diff/status for secrets, missing files and unsent changes. Associate Notebook/video with the final reviewed commit. The preparation and human-review integration are authorized for a normal commit/non-force push after verification; use the reported final commit for handoff.

No public settings, external contact, invitations, recording/upload or Canvas action was performed. If teammates have not replied by the cutoff, record that accurately and follow course policy; never fabricate approval/contribution. Remaining work is other-member review/contributions, unresolved course/operational limits, timed rehearsal, recording, access checks and manual submission—not features.

## Current human adjudication

Satoshi Nakamura adjudicated seven saved event cases and conditionally accepted eight disclosed model topics. Three original cases are accepted with conventions; three HOCR cases have separate annotations; the participant/date case fails. Raw outputs and frozen scores are unchanged. See [HUMAN_REVIEW.md](HUMAN_REVIEW.md), [MODEL_REVIEW.md](MODEL_REVIEW.md), and [integration verification](verification-human-review.json). The decision record date is 2026-10-27 JST; no per-case time is invented. Earlier preparation verification remains historical. The 8 approved topics are not a blanket approval of every earlier unchecked audit item.
