# Three-minute screen demonstration

AI-assisted English narration for the current local app. **Recording and a spoken end-to-end rehearsal are not complete.** Target final video: **2:45–2:55**, including clicks and waits; three minutes is the limit. Timecodes below are provisional pacing guides, not measured delivery. Read only the six narration paragraphs between the markers. Follow the matching [recording run sheet](RECORDING_RUNSHEET.md); [overlay timecodes](recording_overlays.srt) must be synchronized after recording.

The app uses a **saved response from a real OpenAI API call**, not a new call, fixture or mock. No fabricated loading sequence. Launch a fresh local server on an unused port (recommended 7881), as explained in the run sheet. Begin with the original Marathon, 3,000 handling actions and conversion 1, **not confirmed and not applied**.

## 0:00–0:22 A · Bluebikes and the decision

<!-- NARRATION_START -->
Bluebikes is Greater Boston’s bike-share system. Rebalancing moves bikes from surplus stations to stations running short. We plan monthly full-time and seasonal crews for 2026, including hiring dates and contract starts. A crew means a driver and van. Baseline means modeled staffing, not actual deployment.
<!-- NARRATION_END -->

## 0:22–0:48 B · AI and analytics

<!-- NARRATION_START -->
Python uses 2024–2025 trips to estimate workload and plan crews. January–September 2026 trips are held out for backtesting. API calls obtain OpenAI responses. Prompt engineering defines which event facts to extract. Structured output gives validated fields for human review; unknowns should stay unknown. People supply demand assumptions; Python calculates the plan.
<!-- NARRATION_END -->

## 0:48–1:23 C · Saved Marathon facts

<!-- NARRATION_START -->
This demo uses a saved response from a real OpenAI API call. There is no new call now. Here is the original Marathon excerpt beside its extraction. April twentieth is stated. Boston is the route endpoint, not the whole event area. Thirty thousand refers to athletes. Spectators remain unknown. Evidence and human annotations stay visible.
<!-- NARRATION_END -->

## 1:23–2:05 D · Confirm, Apply and the decision

<!-- NARRATION_START -->
I confirm the reviewed facts, then explicitly apply 3,000 added handling actions. This is an uncalibrated retrospective scenario, not OpenAI’s demand prediction or a measured event effect. Boston’s April full-time crews change from 12 to 13. Monthly crew cash cost rises from $72,000 to $78,000. The hiring decision is in March. This is April’s cost, not an annual total. Our base conversion assumes one handling action per course bike; 120 bikes per shift stays fixed.
<!-- NARRATION_END -->

## 2:05–2:20 E · Geographic comparison

<!-- NARRATION_START -->
Both geographic panels show April. Dots mark stations; bubbles compare modeled city crews, not bases or routes. Nine other cities share one pool, shown separately.
<!-- NARRATION_END -->

## 2:20–2:55 F · Evaluation, contribution and close

<!-- NARRATION_START -->
Review found unsupported dates and participants mistaken for spectators. The three supplemental cases are evaluation only and cannot enter plans. Our strongest feature preserves failures while connecting text to staffing and hiring decisions. Satoshi reviewed seven cases and conditionally accepted eight disclosed assumptions. Vinay reviewed documentation and usability. Uncovered proxy work is not measured lost trips.
<!-- NARRATION_END -->

## Timing and pronunciation (not spoken)

The six paragraphs contain **307 whitespace-delimited words**. Expanding numeric years, ranges, costs and quantities as below gives **322 spoken-word equivalents**; abbreviations such as API still count as one token, so this is an estimate, not an audio measurement.

- Read 2024–2025 as “twenty twenty-four and twenty twenty-five”; January–September as “January through September”; 2026 as “twenty twenty-six”.
- Read 3,000 as “three thousand”; $72,000/$78,000 as “seventy-two/seventy-eight thousand dollars”; 120 as “one hundred twenty”; 12/13 as “twelve/thirteen”.
- At **120 expanded words/minute**, narration is about **161 seconds**. Allow **10–14 seconds of pauses not already covered by speech**: about **171–175 seconds**. At 110 words/minute plus ten seconds, about **186 seconds**, which exceeds the limit.
- The operator can scroll/click while the narrator speaks. Do not add the entire operation-only run duration to speech time; do not subtract it either and call the result measured. The actual combined take must be timed.
- Operation-only measurements, narration estimates and unmeasured spoken rehearsal are recorded separately in [the run sheet](RECORDING_RUNSHEET.md). The first two do not prove a sub-three-minute video.

If the full take overruns, cut these exact optional sentences, then measure again: “There is no new call now.” (6 words); “Evidence and human annotations stay visible.” (6); “This is April’s cost, not an annual total.” (8). Keep the saved-real-response disclosure, human gate, +3,000 assumption, April cost label, March hiring, shared pool and review failures. Do not solve an overrun by reading faster than clearly understandable.

## Evidence and contribution boundaries (not spoken)

The original **19/20** and supplemental **11/15** are frozen agreement counts against reference labels, not general human-reviewed accuracy. They need not be spoken in this short video. Preserve unsupported-date and participant/spectator failures; all three supplemental cases remain excluded from plans even after editing and session confirmation.

Satoshi's seven event adjudications and conditional acceptance of eight disclosed model topics are supported by [the human record](human_review_decisions.json). Do not infer code authorship, empirical validation, TA approval or other members' work. Vinay's README/UI review is evidenced by PR #1; Aditi's contribution and narrator/operator assignments remain pending. Membership and invitations alone are not contribution.

The map uses station coordinates and city means, not actual crew bases, routes or geocoded event locations. Keep both April panels at the same extent/scale and the nine-city shared pool visible. Do not open annual-cost tabs during the April cash-cost explanation.

Numerical narration is generated from the saved focused result by the existing `bluebikes.analysis._demo` function. Regeneration must preserve this script. The Mermaid editing source remains `docs/diagrams/bluebikes_flow.mmd`. No new API request, full computation, recording, upload, external contact or submission is part of this preparation.
