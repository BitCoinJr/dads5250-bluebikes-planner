# Three-minute Gradio recording script

AI-assisted English draft. Speak the five paragraphs; directions are not spoken. Rehearse to three minutes. **Video is NOT recorded or uploaded.** All numbers come from the same saved results as the Notebooks. Launch `python scripts/run_app.py --port 7860` and open `http://127.0.0.1:7860`, or use the optional local-app cell in either executed Notebook.

## 0:00-0:25 Problem and evidence

We plan Bluebikes crews across thirteen municipalities, using 2024 and 2025 for training. Our ordinary January-to-September 2026 backtest leaves 48,127 proxy actions uncovered at a same-period crew cost of $1,342,800. This screen explores an event scenario; it is separate from that backtest. The proxy is neither measured operator work nor lost trips.

## 0:25-1:00 Real extraction and review

I select the Marathon announcement. This label says saved real API result: a genuine OpenAI response, replayed without a new call. Dates, city, location, crowd and ambiguities are visible. Crowd is unknown; thirty thousand athletes are not spectators. The separate live button calls OpenAI only when pressed. I review the Boston endpoint convention, then confirm. Confirmation is session-only and does not mark the evaluation files human reviewed.

## 1:00-1:55 Explicit plan change and timing

Only now do I press Apply to plan. Three thousand extra handling actions is an uncalibrated assumption, not LLM-estimated demand. This retrospective scenario does not demonstrate forecast improvement. Boston's April full-time crews change from 12 to 13, and April city cash cost from $72,000 to $78,000. The table shows the preceding March hire decision changing from three to four; it does not assume instant April hiring. Annual forecast and nine-month observed-proxy comparisons keep cost and shortage within their own matching periods. Contract changes can affect other months.

## 1:55-2:35 A visible failure and human correction

I select the participant-only challenge. Its actual model output wrongly treats thirty thousand participants as crowd and guesses absent dates. I clear those fields instead of inventing replacements. Missing dates or an unsupported city block planning. The original four cases retain nineteen-of-twenty provisional agreement; three supplemental cases score 11 of 15 separately. None is human-gold accuracy. Changing source input clears old extraction and plans; changing reviewed fields requires confirmation again.

## 2:35-3:00 Units, architecture and handoff

The course's one hundred twenty bikes per shift stays fixed. The conversion selector distinguishes separate pickup and delivery actions from paired relocations. Existing Python modules perform extraction and constrained planning on cached aggregates. Human and team review, TA confirmation, video recording and upload, grader access and manual submission remain.

## Screen directions (not spoken)

1. Begin with the Marathon selected. Point to source excerpt, saved-real label, null crowd and disabled Apply button. Optional: expand details or use the full submission Notebook for data audit.
2. Confirm unchanged values, or enter a note explaining a deliberate correction. Original model JSON and session-confirmed JSON remain separate. Press Apply explicitly.
3. Show system comparison and selected Boston monthly rows. April FT is 12 to 13; April cost is $72,000 to $78,000. `hire_decision_month_for_active_month` is March; prior-month hires are 3 to 4. Do not sum separate peak FT/seasonal counts from different months.
4. Show the participant-only source and original failure. Clear spectator count and both dates, add a correction note, and confirm; Apply must be blocked for missing date/city. This is a demo interaction, not a persisted human evaluation.
5. Keep +3,000/retrospective, nominal 120 and conversion assumptions visible. The hand-count audit is `docs/handling_unit_walkthrough.md`: 8 handling actions versus 4 assumed paired relocations; unbalanced depot flows cannot automatically be halved.
6. Optional reliability demonstration: edit the source excerpt; old extraction/plan clears and saved reload requires an exact match. API failure must remain a visible failure; use the separate saved button to recover. Do not make a paid live call merely to replay the demo.
7. Record/upload manually, test teaching-team access and insert the video URL. Stop CLI with Ctrl+C; stop a Notebook-owned app with `app.close()`. No public share link or deployment is created.
