# Three-minute recording script

AI-assisted English draft. Speak only the five paragraphs below; stage directions are not spoken. Rehearse to three minutes. Video is NOT recorded or uploaded. Numbers are regenerated from the notebooks' results. Open `notebooks/bluebikes_demo.ipynb`; use the submission Notebook for the full audit.

## 0:00-0:30 Problem and ordinary backtest

We plan Bluebikes crews across thirteen municipalities, training on 2024 and 2025. In the January-to-September 2026 backtest, initial crews cost $756,000, leaving 326,681 proxy actions uncovered. Our proposal costs $1,342,800, leaving 48,127. Both costs and shortages cover the same nine months. These are inventory proxies, with documented data gaps.

## 0:30-1:15 Event text to a conditional decision

This Marathon announcement produces a real OpenAI extraction: Boston, April twentieth. We assign the route to its named endpoint. Our scenario then adds three thousand handling actions to Boston in April: an uncalibrated assumption, separate from extracted facts. April demand moves from 36,721 to 39,721; full-time crews change from 12 to 13, and April city crew cost from $72,000 to $78,000. Annual contracts can change other months. This is a retrospective scenario, not demonstrated forecast improvement.

## 1:15-2:00 Handling actions versus relocated bikes

These synthetic stations need four collections and four deliveries, including resets: eight handling actions. Pairing them gives four relocation tasks, subject to depot and timing assumptions. The course's one hundred twenty bikes per shift stays fixed. Converting two actions per course bike and replanning gives a nine-month cost of $830,700, 30,640 uncovered handling actions, and peak staffing of 18 rather than 32 crews. This is unit sensitivity, not measured productivity; unbalanced depot flows cannot automatically be halved.

## 2:00-2:40 Extraction failure is visible

The original four real extractions retain nineteen-of-twenty draft-reference agreement. Three added cases score 11 of 15 separately. Two spectator-count sources describe one event; both numeric counts are extracted. The participant-only case wrongly calls thirty thousand participants an audience and invents dates. Quantity qualifiers also need review. Input, provisional labels, outputs and blank human judgments appear side by side. These added cases are evaluation only. Human review is pending.

## 2:40-3:00 Architecture and remaining work

Small Python modules connect streaming trip aggregation, inventory, structured extraction and constrained staffing. Saved real responses make the demo reproducible without new API calls. Human and team review, TA confirmation, video recording and upload, and manual Canvas submission remain.

## Stage directions and recording checklist (not spoken)

1. Checkpoint 1: show the matched nine-month baseline/proposal table.
2. Checkpoints 2-3: show the source, recorded real response, April city row and event diagram. Keep the retrospective/+3,000 assumption label visible.
3. Checkpoints 4-5: show the hand count, unchanged 120 and matched nine-month unit comparison.
4. Checkpoint 6: show participant-only failure and PENDING human judgments; do not imply these cases entered planning.
5. Collapse setup/long tables; verify screen and microphone; rehearse timing; record/upload manually; test teaching-team access; insert the video URL. Recording/upload are NOT completed here.
