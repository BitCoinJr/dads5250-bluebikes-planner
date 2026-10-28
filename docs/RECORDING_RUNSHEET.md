# Recording run sheet — preparation, not a recording

**Target final video: 2:45–2:55. Spoken end-to-end timing: NOT MEASURED. Video: NOT RECORDED / NOT UPLOADED.** The six rows below match the narration in [DEMO_SCRIPT.md](DEMO_SCRIPT.md) word for word. The [overlay timings](recording_overlays.srt) are provisional; synchronize them to actual recorded speech/actions afterwards.

## Preflight — presenter and operator

1. From `C:\dev\university\dads5250-bluebikes-planner`, inspect `git status --short` and `git log -1 --oneline`. Preserve any other person's work. Confirm the commit includes this recording-preparation revision.
2. Use a **fresh unused port**, recommended **7881**. Check `Get-NetTCPConnection -State Listen -LocalPort 7881 -ErrorAction SilentlyContinue`. If occupied, choose another port; do not kill an unknown process. Start `.\.venv\Scripts\python.exe scripts/run_app.py --port 7881` and open `http://127.0.0.1:7881`. Keep the URL visible during preflight so an older 7860/7879 review is not mistaken for this server. Verify the opening **“Bluebikes is Greater Boston’s bike-share system.”**, then four cards and Mermaid. Stop only your server with Ctrl+C.
3. Prefer **1920×1080 capture** at readable zoom; also inspect 1366×900. Use one browser window; manually hide unrelated tabs and notifications before capture. Do not change sharing/security settings. Check both map labels at actual playback size, not only on a large monitor.
4. Choose **[original] Media Resources and Schedule of Events for the 130th Boston Marathon**. Re-select it before each take to clear confirmation/results. Use the saved real response, **3,000 added handling actions**, and **1 handling action/course bike**. Verify conversion inside **Capacity and handling-unit assumptions**, then close it. Begin with Apply **disabled**, no session-confirmed values and no dynamic KPI/plots. The fixed summary example remains independently labelled.
5. Do **not** press **Extract with OpenAI**. Replay needs no key or external network. Do not show .env, environment settings, credentials, account details or personal notifications. Real saved API evidence, fixtures and mocked tests are distinct.
6. Inspect source/output/annotations before confirming on camera: April 20, Boston endpoint convention, unknown spectators and retained ambiguity. Session confirmation does not amend evaluation files. No correction is needed for this original Marathon take.
7. Prepare scroll positions without applying. After Apply within the take, geography should default to **April 2026**; verify it before the geographic segment. Keep both panels and the shared pool visible. Avoid annual-detail tabs.
8. Narrator/operator assignments are **unconfirmed** until the people agree. No teammate contribution is inferred. Perform a genuinely spoken timed run before recording.

## One-to-one narration and operation

| Time (provisional) | Read this English | Screen / scroll position | Buttons / input | Verify before proceeding | Operator caution |
|---|---|---|---|---|---|
| 0:00–0:22 · A | Bluebikes is Greater Boston’s bike-share system. Rebalancing moves bikes from surplus stations to stations running short. We plan monthly full-time and seasonal crews for 2026, including hiring dates and contract starts. A crew means a driver and van. Baseline means modeled staffing, not actual deployment. | Top: title, definition and four Executive Summary cards. Keep the fixed example label visible. | No click. Start the full-take stopwatch with the first spoken word; Apply initially disabled. | Definition present; original Marathon selected; no active result; Apply disabled. | Fixed summary illustration is not an applied result. One crew = driver + van; not 13 individually staffed cities. |
| 0:22–0:48 · B | Python uses 2024–2025 trips to estimate workload and plan crews. January–September 2026 trips are held out for backtesting. API calls obtain OpenAI responses. Prompt engineering defines which event facts to extract. Structured output gives validated fields for human review; unknowns should stay unknown. People supply demand assumptions; Python calculates the plan. | Scroll to Mermaid. Keep OpenAI, human gate, Python and held-out evaluation visible together. | No click. Follow the arrows with the pointer. | 2024–2025 training and Jan–Sep 2026 evaluation separate; no evaluation-to-training arrow. | API = response acquisition; prompt = extraction rules; structured output = validated fields. No unused framework claims. |
| 0:48–1:23 · C | This demo uses a saved response from a real OpenAI API call. There is no new call now. Here is the original Marathon excerpt beside its extraction. April twentieth is stated. Boston is the route endpoint, not the whole event area. Thirty thousand refers to athletes. Spectators remain unknown. Evidence and human annotations stay visible. | Original excerpt beside extraction cards: saved-real label, date/city/spectator fields and separate human annotation. | No API click. Keep original Marathon and spectators blank. Read April 20, 2026 and Boston endpoint. | Saved real OpenAI response; April 20; Boston route endpoint; spectators Not stated; human annotation separate. | 30,000 athletes are not spectators. Boston is only an endpoint convention for a multi-city route. Replay is not a fresh model run. |
| 1:23–2:05 · D | I confirm the reviewed facts, then explicitly apply 3,000 added handling actions. This is an uncalibrated retrospective scenario, not OpenAI’s demand prediction or a measured event effect. Boston’s April full-time crews change from 12 to 13. Monthly crew cash cost rises from $72,000 to $78,000. The hiring decision is in March. This is April’s cost, not an annual total. Our base conversion assumes one handling action per course bike; 120 bikes per shift stays fixed. | Review fields → Confirm → scenario controls → Apply. Align Boston / April KPI with March hiring; briefly show the crew chart. | Click Confirm reviewed values (this session only). Check increment 3000 and conversion 1, then click Apply to plan. Do not edit source/facts. | Confirm enables Apply. After Apply: April FT 12→13, cash $72,000→$78,000; March 2026 hiring; prior hires 3→4. | While Python runs, read This is an uncalibrated retrospective scenario. No immediate April hiring or annual +$6,000 claim. |
| 2:05–2:20 · E | Both geographic panels show April. Dots mark stations; bubbles compare modeled city crews, not bases or routes. Nine other cities share one pool, shown separately. | Geographic crew comparison: both panels, April selector and shared-pool text. | Verify Map month (both panels) = April 2026. Select April only if necessary; this does not replan. | Both plans April with common scales. Boston FT 12 vs 13; other-city pool 2 FT / 0 seasonal in both. | Allow 10–15 seconds. Centroids are not bases; no routes/event markers. Capacity shares are not city crew counts. |
| 2:20–2:55 · F | Review found unsupported dates and participants mistaken for spectators. The three supplemental cases are evaluation only and cannot enter plans. Our strongest feature preserves failures while connecting text to staffing and hiring decisions. Satoshi reviewed seven cases and conditionally accepted eight disclosed assumptions. Vinay reviewed documentation and usability. Uncovered proxy work is not measured lost trips. | Hold the same geographic/result view. Do not switch events or open evaluation tables. | No clicks. End after the last sentence and a brief still frame. | Claims match the human record; no claim that spoken rehearsal, general accuracy or submission is complete. | Do not attribute work to unconfirmed teammates or imply TA approval. Stop within the measured limit. |

## Framing, waiting and overlays

Read the uncalibrated-scenario sentence during the short Python wait after Apply. Do not narrate expected numbers until the actual KPI is visible. If calculation outlasts the sentence, pause honestly and retry the take after resolving the delay. Never fake a fresh API animation.

Show the geographic view at capture width, keeping both headings, axes, Boston labels and shared-pool text. Inspect the browser at 1920×1080/1366×900, but **compressed-video legibility remains unverified** until recording. If labels are too small, use the existing [full-resolution April figure](../results/figures/geographic_crew_comparison.png) for the 15-second segment and explicitly call it a saved figure from the same calculation. That extra transition must be timed again.

[recording_overlays.srt](recording_overlays.srt) contains emphasis captions, not a complete transcript. Timecodes are **DRAFT / UNSYNCHRONIZED**, based on the planned intervals; retime them after recording. Use unused margins, without covering evidence, March hiring, map axes or the pool.

Emphasize **Boston: +1 full-time crew / +$6,000 monthly crew cash in April**, with hiring decision **March**, alongside **Uncalibrated +3,000 handling actions**. The [focused chain](../results/focused_event_chain.csv) and actual KPI are authoritative. This is not all-city annual cash, customer loss or observed deployment.

## Timing — three separate claims

1. **Operation-only actual: 14.424 seconds**, measured at 2026-10-28 00:40:08.574–00:40:22.998 UTC. This was automated browser navigation/clicks and readiness checks at a373335, without spoken narration; it is historical operation-only evidence for the pre-PR wording. See [operation evidence](verification-recording-prep.json) for timestamps, elapsed time and scope. This is a workflow rehearsal, not a completed video or spoken run.
2. **Narration estimate:** 307 written words; approximately 322 after expanding numeric notation. At 120 expanded words/minute, about 161 seconds; plus 10–14 seconds of non-overlapping pauses gives 171–175 seconds. At 110 words/minute plus ten seconds, about 186 seconds. Simultaneous operation/speech can differ; shorten and remeasure if needed.
3. **Spoken end-to-end actual:** **NOT MEASURED**. [rehearsal_log.csv](rehearsal_log.csv) remains reserved for real spoken takes. Do not insert operation-only timing as a presenter rehearsal.

Time a real spoken run from first word to final frame, including clicks/waits/transitions. A helper can use this local timer in a separate terminal before capture:

```powershell
Read-Host 'Press Enter when ready for a spoken end-to-end rehearsal'
$demoStartedAt = [DateTimeOffset]::Now
$demoTimer = [System.Diagnostics.Stopwatch]::StartNew()
Read-Host 'After the last spoken word and final frame, press Enter'
$demoTimer.Stop()
[pscustomobject]@{
    StartedAt = $demoStartedAt.ToString('o')
    ElapsedSeconds = [Math]::Round($demoTimer.Elapsed.TotalSeconds, 2)
    Within180Seconds = ($demoTimer.Elapsed.TotalSeconds -le 180)
}
```

Returning to the terminal adds overhead; document this. Record presenter/operator, script/commit, timezone, total and geographic segment in the rehearsal log. Keep final-player legibility pending until recording. Use the exact optional cuts in DEMO_SCRIPT.md if over time, then measure again.

## Human decisions before recording

- Confirm narrator/operator, pronunciation and a measured complete take. Pacing is a target, not proof.
- Reconfirm original Marathon facts and the scenario on camera; prior adjudication does not replace the session gate.
- Satoshi's seven event decisions and eight conditional assumption decisions are recorded. Vinay's README/UI contribution is evidenced by PR #1. Aditi's contribution and all-member approval remain pending; do not invent roles.
- Preserve 19/20 and 11/15 as separate frozen-reference agreements, not general human-reviewed accuracy. Supplemental cases stay evaluation-only even if edited.
- TA confirmation, recording/upload, grader private-repo/video access and Canvas receipt remain pending. No external contact, publication or submission is part of this preparation.
