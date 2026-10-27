# Three-minute screen demonstration

AI-assisted English draft; rehearse timing before recording. Video is **NOT recorded or uploaded**. Speak the five paragraphs below; screen directions are not spoken. Start the revised app on `python scripts/run_app.py --port 7872` so an older review on 7860 can remain untouched. The same generated Mermaid diagram is used in the app, README, Notebooks and presentation.

## 0:00-0:20 Problem and value

This prototype turns an event headline into a conditional crew decision. Historical trips establish the baseline; OpenAI structures event facts; a reviewer checks them; and Python plans staffing. The question is when and where crews might need to change.

## 0:20-0:55 Event text and readable extraction

The Marathon announcement sits beside readable extracted facts. Saved real API result means a genuine recorded response, without a new model call. The cards show the date, Boston endpoint, venue and spectators: Not stated. Thirty thousand athletes are not spectators. The evidence excerpt and Needs review section make that distinction visible; raw JSON and model details remain available underneath.

## 0:55-1:20 Confirm facts and choose the assumption

I verify the city allocation, dates and ambiguity, then confirm. My corrections stay separate from the original response and do not mark evaluation files human reviewed. Three thousand added handling actions is my uncalibrated scenario assumption, not OpenAI's demand estimate. Only Apply sends the reviewed event to planning. Unknown cities or dates block it.

## 1:20-2:15 The staffing decision and why it changes

Boston's April full-time crews change from 12 to 13, and monthly crew cash cost from $72,000 to $78,000. The hiring decision belongs in March. The first graph separates full-time and seasonal crews, comparing baseline with scenario. The demand graph shows added demand crossing prior-plan capacity, then the replanned capacity responding. Red fill is estimated uncovered rebalancing work, not measured lost trips. Monthly capacity does not guarantee station-hour service. These are retrospective scenario results, not demonstrated forecasting improvement.

## 2:15-3:00 Architecture, evaluation and limits

The architecture uses three course techniques: API calls reach OpenAI, prompt engineering defines extraction and unknowns, and structured output supports validation and reviewed planning input. Python handles costs, capacity, hiring and seasonal constraints. Training uses 2024-2025; January-September 2026 evaluates frozen plans. Annual forecast and nine-month evaluation have separate cost tabs. Original responses retain nineteen-of-twenty provisional agreement; added cases score 11 of 15 separately. The participant-count and guessed-date failure remains visible. Human review, verified contributions, recording, access checks and submission remain pending.

## Screen directions (not spoken)

1. Show the title and canonical Mermaid flow. Identify OpenAI, reviewer and Python roles; no held-out data arrow returns to training.
2. Choose Marathon. Compare the left-hand source with right-hand readable cards, null spectators and evidence; avoid opening raw JSON unless asked. Saved mode has no fake extraction animation or new API call.
3. Confirm unchanged values or note a correction, then Apply explicitly. Show the city/event-month KPI cards and March hiring decision.
4. Show both graphs with April highlighted. Full-time/seasonal markers and baseline/scenario line styles differ. The demand graph keeps handling units consistent, distinguishes prior-plan from replanned capacity, and shades current estimated uncovered work.
5. Open detail tabs only if needed: Jan-Dec forecast totals cover all cities for twelve months, Jan-Sep held-out totals cover the same nine months as their cash costs, and monthly details cover the selected staffing group. Do not compare a city-month cash cost with all-city annual cost.
6. Optional short failure check: select the participant-only challenge, inspect its warning, clear unsupported dates/crowd and confirm; planning must stay blocked. Changing any source or reviewed fields must clear earlier decisions/charts.
7. The single diagram editing source is `docs/diagrams/bluebikes_flow.mmd`; regenerate its SVG/PNG with `node scripts/render_architecture.mjs`. The app displays the local SVG without a CDN. For presentation, use the same generated asset rather than editing a copy.
8. Keep the uncalibrated increment, 120 bikes/shift and conditional handling conversion visible where needed. Rehearse, record/upload manually and verify grader access. Only verified member contributions may be reported. Stop only the server started for this demo; leave another chat's 7860 review untouched.
