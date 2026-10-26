# Event extraction evidence and status

The GenAI integration calls the OpenAI Responses API with an explicit JSON
prompt, one example, and `text.format` set to a strict JSON schema. OpenAI is the
sole runtime provider, following the user's provider change. The direct
`requests` adapter needs no SDK or agent framework and sets `store: false`.
Client validation checks required keys, nullability, actual calendar dates,
chronology, supplied URL equality, and literal evidence grounding. JSON validity
does not establish semantic correctness. Credentials are read only from
`OPENAI_API_KEY` from the process environment, Git-ignored project `.env`, or
persisted Windows user environment, in that order. Only `OPENAI_API_KEY` and
`OPENAI_MODEL` are read from `.env`; shell evaluation/interpolation is not used.
The API URL is fixed at `https://api.openai.com/v1/responses`, redirects are
disabled, and errors do not include response bodies or credentials. Set
`OPENAI_MODEL` to override the default `gpt-4.1-mini`. The API schema uses a
portable supported subset; full local validation additionally checks dates,
URI format, string bounds and numeric bounds. Refused or incomplete responses
are rejected, with no fixture fallback.

Official API documentation checked on 2026-10-26:

- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [GPT-4.1 mini model](https://developers.openai.com/api/docs/models/gpt-4.1-mini)

The first configuration check found no key; this was a historical setup
state. A genuine run subsequently completed on **27 October 2026 JST**, with
**four OpenAI API calls** and `live_llm_verified: true`. All four responses passed
the local schema and provenance validator. The returned model was
**`gpt-4.1-mini-2025-04-14`**. The saved call completion timestamps are
2026-10-26 23:35:00.439 through 23:35:09.089 UTC, equivalent to
27 October 2026 08:35:00.439 through 08:35:09.089 JST. Recorded usage totals
**2,598 input tokens + 623 output tokens = 3,221 tokens**; the sum of individual
request latencies is **15.790 seconds**, not a claim about model-only latency.

The original credential-free evidence is
[`results/event_extraction_live.json`](../results/event_extraction_live.json),
including model, usage, timestamps, response IDs, request/output hashes and each
field comparison. Its score is **19/20 fields (95%) exact agreement against
provisional agent-authored labels**, not accuracy against human-reviewed gold.
The only mismatch is the Cambridge location: the draft label stops at
`Kendall/MIT Open Space, 292 Main Street`, while the live output includes the
source-supported `Cambridge, MA 02142`. Exact match counts this as a disagreement;
it is not evidence of a fabricated address. The prompt and reference labels
were retained after the responses rather than changed to improve the score.

The 19/20 metric covers only start date, end date, location, city and audience
count. It does **not** score the ambiguity text or establish that every semantic
claim is grounded. Independent AI review flagged the Head Of The Charles
ambiguity phrase `event is known to span multiple locations` as broader than the
supplied short excerpt. Human review is still pending; the raw response and the
original 19/20 score remain unchanged. See the
[extraction review](event_extraction_review.md) for this unscored concern.

The separate
[`results/event_extraction_fixture.json`](../results/event_extraction_fixture.json)
records **zero API calls** and **no extraction accuracy**. Agent-authored fixtures
are neither live LLM predictions nor human-reviewed gold. A requested new live
run without a key still returns an explicit blocked status and zero API calls.
The default analysis and Notebook use recorded mode, replaying the validated
real outputs without additional API calls; current replay metadata is in
`results/live_llm_check.json`.

## Sources and annotation

`fixtures/event_documents.json` contains four short excerpts fetched from primary
sources, source URLs, retrieval date, available publication dates, and a separate
provisional agent-authored answer key. Selected verbatim clauses are separated by ellipses;
they are not contiguous full articles. These deliberately short excerpts are
sufficient to exercise dates, named places, nullable audience counts and
missing-city handling. They are not a comprehensive event calendar. All draft
annotations were authored by the implementation agent and await actual human
team review; the requirement for a human-correct reference set is not yet met.

| Example | Source | Fact exercised | Audience estimate |
|---|---|---|---|
| Boston Marathon, 2026-04-20 | [B.A.A. announcement](https://www.baa.org/news/media-resources-schedule-of-events-for-the-130th-boston-marathon-presented-by-bank-of-america/) | Date, route endpoint, athlete versus audience distinction | null |
| Boston Pops, 2026-07-04 | [Boston Symphony Orchestra announcement](https://www.bso.org/press/boston-pops-announces-lainey-wilson-chance-the-rapper-and-trombone-shorty-as-special-guest-artists-at-2026-july-4-fireworks-spectacular-celebrating-massachusetts-and-america-250) | Date and named venue | null |
| Cambridge science event, 2026-10-04 | [City of Cambridge calendar](https://www.cambridgema.gov/citycalendar/2026/10/04/cambridgesciencefestival2026) | Street address and municipality | null |
| Head Of The Charles, 2026-10-16 through 2026-10-18 | [Organizer homepage](https://hocr.org/) | Multi-day period, city absent from excerpt | null |

For the marathon, Boston is the explicitly named route endpoint. Its other
municipalities are not allocated from the excerpt. For Head Of The Charles,
the source excerpt does not state a city: the record keeps city null and cannot
change a city plan. The full Cambridge page uses Festival in its title and
Carnival in its description; this naming ambiguity is recorded. Published
athlete counts, activity booth counts, and broadcast audience descriptions must
not become expected in-person crowd sizes.

Live evaluation uses exact match on start date, end date, location, city and
audience count: 20 fields across four examples. The report preserves each field
comparison. Location exact match penalizes equivalent wording, as the Cambridge
address mismatch demonstrates. All four curated examples have null audience
counts; they do not test extraction of a positive audience estimate, and four
examples cannot establish generalization. The first team review should inspect evidence,
dates and nullable fields, then add adversarial and positive audience-count
examples. These are provisional agent-authored reference labels, not human-
reviewed gold. The evaluator records this reference status in its output, even
after a successful live API run.

## Connection to demand and crew planning

`event_adjustments(forecast, events, extra_moves_per_event=0)` takes city-month
forecasts and adds a declared incremental scenario. An event receives one total
assumed increment, prorated by calendar days for a multi-month event. Null-city
or null-date events do not change demand, duplicate event records are ignored,
and the original forecast is retained as `base_demand_bikes`. The result includes
`event_increment_bikes` and feeds exactly the same crew planner as the base case.

The default coefficient is zero. Recurrent events may already be represented by
the seasonal model, so automatically adding an entire event effect would double
count it. A positive coefficient is an uncalibrated incremental stress scenario,
not a fact extracted by the model or an observed causal effect. No audience-to-
bike conversion is used because none of the short excerpts provides an audience
estimate. A positive scenario must be presented alongside the zero case and
cannot be called a demonstrated forecasting improvement.

These event pages were retrieved in October 2026; two announcements were
published during 2026 and other original publication dates are unknown. Thus an
event-adjusted comparison using them is a retrospective scenario, not a strict
January-2026 information-available backtest. Base forecasting and model selection
must use 2024-2025 only. Do not tune event increments against the held-out 2026
trip demand. A defensible operational extension would archive announcements as
they become available and apply the one-month crew decision lead time.

## Commands

```powershell
py -m bluebikes.events --check-config
py -m bluebikes.events --mode fixture --output results/event_extraction_fixture.json
py -m bluebikes.events --mode live --output results/event_extraction_live.json
py -m bluebikes.events --mode recorded
py -m unittest discover -s tests -p test_events.py -v
```

The live command makes API calls only when `OPENAI_API_KEY` is configured. Do not
commit that key; [.env.example](../.env.example) contains only blank/template
settings. `--check-config` reports key presence, configuration source and model,
never the key value. Successful execution automatically saves a complete live
artifact. Metadata includes model, usage, response ID, timestamp, latency and
request/output hashes; it never contains Authorization headers.

Recorded mode validates that the saved artifact came from the live OpenAI path,
contains every expected source, matches the current prompt/source/schema request
hashes and the stored output hashes, and still passes local validation. It then
reuses the recorded outputs with zero new API calls, so Notebook reruns and
grading do not need a key or repeat API spending. A missing or changed artifact
is blocked or rejected, never silently replaced with fixtures. These hashes are
reproducibility checks, not cryptographic proof of a provider response: preserve
the actual response IDs and execution evidence for review. Human-label review
remains pending even when a genuine live call succeeds.
