# Recording run sheet — not a recording

**Status: actual rehearsal time NOT MEASURED; video NOT RECORDED / NOT UPLOADED.** Use the [English script](DEMO_SCRIPT.md); the timecodes are targets only. The script targets 2:55 + 5 seconds of buffer. Real clicks, waits and transitions count toward the three-minute limit. No member contribution is attributed in the script.

## Preflight

1. Launch from the repository root: `.\.venv\Scripts\python.exe scripts/run_app.py --port 7876`. Open `http://127.0.0.1:7876`. Leave older 7860/7872 review processes untouched; choose another free port if needed. Stop only your app with Ctrl+C.
2. Use the **original Marathon** event, saved matching real response, increment **3,000**, conversion **1 action/course bike**, April 2026 map month. This is a retrospective model scenario. Do not press **Extract with OpenAI** during this saved-mode demo.
3. Keep original output separate from editable review fields. The presenter must actually inspect dates, Boston endpoint convention, null spectators and ambiguities before **Confirm reviewed values (this session only)**, then **Apply to plan**. Do not claim that this fills the human evaluation CSVs.
4. Keep unrelated windows, email notifications and terminals containing credentials out of capture. No key is needed for replay. Opening `.env` is unnecessary.
5. Use the verified desktop layout as reference; record at 1920×1080 when available. Prepare scroll positions before the take; do not use the narrow/mobile view for the paired map.

## Planned screen order

| Target time | On-screen action | Spoken point / emphasis |
|---|---|---|
| 0:00–0:15 | Title and shared architecture | Event text → OpenAI structure → human confirmation → Python plan. Baseline is modeled staffing. |
| 0:15–0:45 | Marathon source beside extraction cards | Say **“Saved real API result”**. April 20; named Boston endpoint; 30,000 athletes are not spectators. Replay makes no new call. |
| 0:45–1:10 | Review fields → Confirm → scenario 3,000 → Apply | User assumption, separate confirmation/apply gates; do not pretend an unperformed review happened. |
| 1:10–1:55 | April KPI, March hiring decision, crew and demand/capacity plots | **+1 full-time crew / +$6,000 in April 2026**; seasonal stays 0. Explain handling units, uncovered proxy work and limits. |
| 1:55–2:08 | Same-month geographic panels; keep pool visible | Both April scales match. Boston 12→13; shared pool stays 2 FT / 0 seasonal. Centroids are not depots. |
| 2:08–2:55 | Shared architecture and evaluation explanation | API calls, prompt engineering, structured output, validation/confirmation, Python optimization. Train 2024–2025; Jan–Sep held-out evaluation. Keep 19/20 and separate 11/15 provisional results/failures. |
| 2:55–3:00 | End | Buffer only; no extra feature tour. |

The dynamic KPI and [focused chain](../results/focused_event_chain.csv) are the numeric authority. Boston April: 12→13 FT, 0→0 seasonal, $72,000→$78,000 monthly crew cash. This **+$6,000 city-month** differs from the focused scenario's **+$7,200 all-city Jan–Dec cash difference**, because other months/contracts change. It is not a customer-loss amount or actual staff deployment.

## Map legibility and subtitles

The existing [1366×900 browser capture](screenshots/geography/desktop-april.jpg) and [full-resolution saved geographic PNG](../results/figures/geographic_crew_comparison.png) were visually inspected during preparation. Both panel headings, Boston FT 12/13, +1 delta and handling-action labels are readable at original size; shrinking an entire desktop makes the labels small. This is asset inspection, not verification of a recorded/compressed video.

Show the paired plot at readable width, scroll it to the top of capture and keep the shared-pool text below. Do not zoom/crop just one panel or remove either legend/scale. If screen capture cannot preserve legibility, switch explicitly to the **saved April figure from the same run** for the 13-second segment; describe it as a saved figure and retain “shared pool: 2 FT / 0 seasonal in both plans” in speech/on-screen text. No new map data or render is needed.

Use [recording_overlays.srt](recording_overlays.srt) as **draft, unsynchronized captions**. Amounts were derived from the focused chain; timecodes are planned, not measured. Place large high-contrast text over unused margins without covering Boston labels, axes or the pool. During geography, keep **“Boston: +1 crew / +$6,000 in April”** visible with **“Uncalibrated +3,000-action scenario”**. Keep full-time and March decision details in the preceding KPI segment.

After recording, replay at the **actual submitted player size/resolution**. Have a viewer read both headings, Boston counts and pool count without pausing; if they cannot, use the existing full-resolution figure or revise framing/caption size. This check remains **PENDING** until a real video exists.

## Measure an actual rehearsal

Use a stopwatch from the first spoken word through the final frame, including interaction/wait time. Do not fill duration from word count. Record measured total and geographic segment in [rehearsal_log.csv](rehearsal_log.csv), currently header-only. Keep a take ID, presenter, script/commit revision, timestamp/timezone and any recording evidence.

For a simple local PowerShell timer (no installation/upload), run this in a separate terminal, then perform the real rehearsal in the app:

```powershell
Read-Host 'Press Enter when ready to start the actual rehearsal'
$demoStart = [DateTimeOffset]::Now
$demoTimer = [System.Diagnostics.Stopwatch]::StartNew()
Read-Host 'After the final spoken word and screen, return here and press Enter'
$demoTimer.Stop()
[pscustomobject]@{
    StartedAt = $demoStart.ToString('o')
    ElapsedSeconds = [Math]::Round($demoTimer.Elapsed.TotalSeconds, 2)
    Within180Seconds = ($demoTimer.Elapsed.TotalSeconds -le 180)
}
```

The timer includes switching to/from the terminal; it is a conservative rehearsal time. A stopwatch lap or actual recording timestamps can measure the 13-second map segment. Do not run the timer without speaking/operating and call that a rehearsal. If over 180 seconds, shorten wording/transitions while keeping saved-mode disclosure, confirmation, assumption/units, comparisons and limitations. Measure again; a planned cut is not timed.

After recording/upload and permitted-viewer access checks, add the verified video URL to submission materials and inspect them again. Satoshi's seven human judgments and eight conditional assumptions are now recorded. Leave TA confirmation, other-member contributions, actual rehearsal/recording/access and Canvas receipt pending until evidence exists. Show the separate human annotation below the unedited output; do not claim that the raw failed response has been repaired.
