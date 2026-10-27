# Three-minute screen demonstration

AI-assisted English draft; rehearse timing before recording. Video is **NOT recorded or uploaded**. Speak the six paragraphs below; screen directions are not spoken. The timecodes below are a planned 2:55 with five seconds of buffer, not measured duration. Use the [recording run sheet](RECORDING_RUNSHEET.md) and its stopwatch log to measure actual delivery, clicks and waits. The [draft captions](recording_overlays.srt) require synchronization after rehearsal. Start the revised app on `python scripts/run_app.py --port 7876` so an older review on 7860 can remain untouched. The same generated Mermaid diagram is used in the app, README, Notebooks and presentation.

## 0:00-0:15 Problem and value

This prototype turns event announcements into conditional crew decisions. OpenAI structures event text; people confirm it; Python replans crews. The baseline is a model plan, not observed staffing.

## 0:15-0:45 Event text and readable extraction

Here is the Marathon source beside readable extraction cards. Saved real API result replays an actual response without another model call. The cards show dates, Boston endpoint and venue, but spectators are Not stated. Thirty thousand athletes are not spectators. Source evidence and Needs review expose uncertainties; raw JSON remains available.

## 0:45-1:10 Confirm facts and choose the assumption

I check dates, city allocation and ambiguities, then confirm. Session edits do not rewrite raw outputs or recorded human judgments. Three thousand added handling actions is my uncalibrated assumption. Only Apply runs planning. Unknown dates or cities block it. This is a retrospective scenario.

## 1:10-1:55 The staffing decision and why it changes

Boston's April full-time crews rise from 12 to 13; monthly cash cost changes from $72,000 to $78,000. Hiring belongs in March. The crew graph separates full-time and seasonal staffing. The demand graph compares added demand, prior capacity and replanned capacity. Red fill means uncovered proxy work, not lost trips. Monthly capacity cannot guarantee station-hour service. Both graphs use handling actions. One action per course bike is our base convention; 120 bikes per shift stays fixed. Contract changes can affect other months.

## 1:55-2:08 Geographic comparison

Offline geographic panels share one month and scale. Bubbles show whole core-city crews; the pool stays separate. Centroids are not depots; event markers are absent.

## 2:08-2:55 Architecture, evaluation and limits

API calls obtain responses; prompt engineering defines extraction; structured output supports validation and review. Python optimizes crews. Training uses twenty twenty-four and twenty twenty-five; January through September twenty twenty-six is held out. Satoshi adjudicated seven saved cases and conditionally accepted eight assumptions. HOCR annotations are separate; participant and date failures remain. Frozen scores stay nineteen of twenty and eleven of fifteen against AI draft references. This establishes neither measured event effects, TA approval nor all-member review.

## 2:55-3:00 Buffer

No additional spoken content; leave room for interface transitions.

## Screen directions (not spoken)

1. Show the title and canonical Mermaid flow. Identify OpenAI, reviewer and Python roles; no held-out data arrow returns to training.
2. Choose Marathon. Compare the left-hand source with right-hand readable cards, null spectators and evidence; avoid opening raw JSON unless asked. Saved mode has no fake extraction animation or new API call.
3. Confirm unchanged values or note a correction, then Apply explicitly. Show the city/event-month KPI cards and March hiring decision. Overlay Boston: +1 full-time crew / +$6,000 in April 2026. This is monthly crew cash cost, not annual or customer loss.
4. Show both graphs with April highlighted. Full-time/seasonal markers and baseline/scenario line styles differ. The demand graph keeps handling units consistent, distinguishes prior-plan from replanned capacity, and shades current estimated uncovered work.
5. Spend thirteen seconds on the geographic comparison (use the 1080p framing and legibility check in RECORDING_RUNSHEET.md): use the same selected month and shared bubble scale for no-event versus reviewed-event panels. The coordinate view works offline. Bubbles represent whole crews in the four core cities, not fractional city allocations; show the other-city shared pool separately. Station-coordinate centroids are geographic reference points, not depots or routes. Do not add event markers or imply event locations were geocoded.
6. Open detail tabs only if needed: Jan-Dec forecast totals cover all cities for twelve months, Jan-Sep held-out totals cover the same nine months as their cash costs, and monthly details cover the selected staffing group. Do not compare a city-month cash cost with all-city annual cost.
7. Optional failure check for review, outside the timed script: select the participant-only challenge, inspect its warning, clear unsupported dates/crowd and confirm; planning must stay blocked. Changing any source or reviewed fields must clear earlier decisions/charts.
8. The single diagram editing source is `docs/diagrams/bluebikes_flow.mmd`; regenerate its SVG/PNG with `node scripts/render_architecture.mjs`. The app displays the local SVG without a CDN. For presentation, use the same generated asset rather than editing a copy.
9. Keep the uncalibrated increment, 120 bikes/shift and conditional handling conversion visible where needed. Rehearse, record/upload manually and verify grader access. Only verified member contributions may be reported. Stop only the server started for this demo; leave another chat's 7860 review untouched.
