# Architecture and demo storyboard

AI-assisted implementation and review notes; human validation remains pending.

![Bluebikes flow with explicit Python, OpenAI, human-review and user-assumption roles](diagrams/bluebikes_flow.svg)

Edit only [bluebikes_flow.mmd](diagrams/bluebikes_flow.mmd) for diagram content. The [SVG](diagrams/bluebikes_flow.svg) and [PNG](diagrams/bluebikes_flow.png) are generated from that source, then reused by the README, both Notebooks and the local app. There is no separately maintained Mermaid graph in this document. Text labels identify each role in addition to color.

Python builds the station-hour inventory proxy, selects a model on **2024–2025**, freezes the 2026 monthly forecast, and solves the crew constraints. GenAI has three visible roles: an **OpenAI API call**, **prompt engineering** for extraction, and **structured JSON output**. Python validates that output; a human confirms the facts and ambiguities. An explicit user demand assumption and **Apply** action connect those reviewed facts to staffing. The event coefficient is not extracted from text. **January–September 2026 trips enter only the held-out evaluation**; no backtest arrow returns to forecast training or model selection.

## Regenerate the shared diagram

The [renderer](../scripts/render_architecture.mjs) uses **Mermaid CLI 12.0.0**, pinned in a local ignored `build/mermaid-cli` cache. The [official CLI documentation](https://github.com/mermaid-js/mermaid-cli#install-locally) describes local installation and SVG/PNG/PDF exports. Node 22.13 or later and a local Chrome/Chromium/Edge executable are needed only when regenerating the images, not when running the app or viewing a Notebook.

```powershell
$env:PUPPETEER_SKIP_DOWNLOAD = 'true'
npm.cmd install --prefix build/mermaid-cli --cache build/mermaid-npm-cache --no-audit --no-fund --save-exact @mermaid-js/mermaid-cli@12.0.0
node scripts/render_architecture.mjs
```

The renderer reuses an installed browser; set `MERMAID_BROWSER_EXECUTABLE` if it is elsewhere. It generates both images and records source/output hashes in ignored `build/architecture-render.json`. The SVG contains plain text and embedded styles without scripts or external assets. App and Notebook display the cached image without a Mermaid CDN or runtime Node dependency. New UI/diagram verification is tracked in [verification-ui-polish.json](verification-ui-polish.json).

The supplemental evaluation has no path to demand or staffing. Its two positive crowd excerpts concern the same HOCR event, and its participant-only case exposes crowd/date grounding failures. Preserve 11/15 provisional agreement separately from the original four-call 19/20 result. Crowd qualifiers and unscored ambiguity text require review; schema validity does not establish semantic truth. All human review remains pending.

Recorded mode validates saved request/source/schema and output hashes, then replays real outputs with **zero new API calls**. Fixture mode is a separately labelled agent-authored contract test; it is not live execution evidence.

The optional Gradio app uses the same planning and extraction modules. Its initial state displays saved real evidence and results. **実APIで抽出 / Extract with OpenAI** makes a distinct new call into session memory; it does not replace the four-call or supplemental frozen evidence. Source, reviewed event and assumption edits invalidate an applied scenario. Review editable fields and notes, **Confirm reviewed values (this session only)**, then explicitly **Apply to plan**. This neither writes human judgments into the frozen evaluation files nor establishes reviewed gold labels. The original 19/20 and supplemental 11/15 scores and exposed failures remain separate and visible.

`create_app(root=None)` builds the app; `launch_local(root=None, port=7860, inline=False, prevent_thread_lock=False)` binds it to **127.0.0.1**, with `share=False` and analytics disabled. The default remains 7860. For this polished revision's review, use `scripts/run_app.py --port 7872` and open `http://127.0.0.1:7872` to avoid an older process on 7860. The CLI and Notebook use the same app. Both Notebooks default to `LAUNCH_LOCAL_APP = False`, so ordinary execution starts no server. For review in a Notebook, set `LOCAL_APP_PORT = 7872` before opting in; stop with `app.close()`. The CLI stops with Ctrl+C. Earlier integration evidence remains in [verification-gradio.json](verification-gradio.json); the new review belongs in [verification-ui-polish.json](verification-ui-polish.json).

The focused demo follows the saved Marathon input: **20 April 2026, Boston, assumed +3,000 handling actions, April forecast 36,721.19 to 39,721.19, FT 12 to 13, April crew cash cost $72,000 to $78,000**. Source URL and ambiguities remain visible. The increment is uncalibrated and retrospective; it does not demonstrate forecast improvement. No 2026 actual enters forecasting or coefficient selection.

In the app, a hiring decision belongs to the preceding decision month and changes active crews the following month. Display that lead explicitly; applying a new event does not make a crew immediately available. The same retrospective increment, fixed 120 course bikes/shift, counting-unit conversion and same-period cost/service limits apply to both the UI and Notebook.

The unit comparison fixes **120 bikes/shift**. Pickup plus delivery is two handling actions. Factor two converts those to one course-bike unit before replanning and converts shortage back to handling actions. The assumed penalty per handling action stays fixed. Pairing is conditional: unbalanced city/depot handling cannot automatically be halved; inspect the [synthetic walkthrough](handling_unit_walkthrough.md). This new optimization can change crew/cost recommendations; the old frozen-plan capacity sensitivity cannot. See [scenario assumptions](scenario_assumptions.md) and the [unit comparison](../results/unit_interpretation_comparison.csv).

Figures, period tables and the script share saved computation results. January-December crew cash cost is matched to annual forecast-proxy shortage; January-September crew cash cost is matched to nine-month observed-proxy shortage. Mandatory 2027 seasonal obligations are separate. The shared other-city pool is an explicit city-rule exception, not proof of feasible routes.

Use the compact [demo Notebook](../notebooks/bluebikes_demo.ipynb) for the walkthrough and the [submission Notebook](../notebooks/bluebikes_submission.ipynb) for the full audit. Inspect both artifacts' generated cells before recording; a link is not execution evidence.

Gradio recording storyboard: problem/value (0:00-0:20), source and readable extraction (0:20-0:55), confirmation and explicit scenario (0:55-1:20), KPI/crew/capacity and prior hiring decision (1:20-2:15), architecture/evaluation/limits (2:15-3:00). [DEMO_SCRIPT.md](DEMO_SCRIPT.md) is regenerated from the same saved numeric results. Rehearsal, video recording/upload, TA confirmation, all-member review and manual Canvas submission remain incomplete.
