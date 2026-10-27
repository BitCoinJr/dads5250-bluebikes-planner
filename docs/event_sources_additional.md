# Supplemental audience and participant validation sources

This separate evaluation adds two positive audience-number examples and one participant-only contrast. It preserves the original four-case prompt, schema, source references, real API artifact and 19/20 score. New draft references are AI-authored, frozen before additional API calls, and await actual human review. A larger count of related text examples is not a larger set of independent events.

## Primary sources

| Supplemental case | Primary source and retrieval | Why it is a useful contrast |
|---|---|---|
| additional_hocr_bu_2026 | [Boston University event preview](https://www.bu.edu/articles/2026/rowers-prepare-head-of-charles-regatta/), published 15 October 2026, retrieved 27 October 2026 | A university whose teams compete describes spectators separately from rowers. The audience statement is a recurring-event lower bound in a 2026 preview, not measured 2026 attendance. |
| additional_hocr_avive_2026 | [First-aid sponsor's announcement](https://www.avive.life/news/head-of-the-charles-regatta), published 13 October 2026, retrieved 27 October 2026 | Its expected unique-spectator estimate is separate from competitors and volunteers. The sponsor is involved in the event, but its promotional estimate is not an independently measured crowd census. |
| additional_baa_participants_only_2026 | [Official organizer spectator guidance](https://www.baa.org/races/boston-marathon/info-for-spectators/), publication date unknown, retrieved 27 October 2026 | The selected 2026 guide body gives a participant count and a starting city, without a numerical spectator count or an event calendar date. Navigation elsewhere on the live page concerns a later edition and is not used to invent missing dates. |

The exact short inputs are stored in fixtures/event_documents_additional.json as selected verbatim clauses joined by ellipses. They are not contiguous full articles. Each excerpt has at most 25 source words, excluding the inserted ellipsis separators. Source titles are descriptive labels. Both positive cases refer to the same 2026 Head Of The Charles regatta; their figures describe different source-specific claims and must not be summed, averaged, or treated as independent crowd measurements.

## Numeric meaning and evaluation protocol

The unchanged original schema has one nullable integer crowd field. It cannot directly represent a lower bound, approximation, uncertainty interval or temporal scope. The new reference annotations therefore retain the source qualifier and interpretation visibly: the BU number is a lower-bound threshold and describes the recurring audience; the sponsor number is an approximate 2026 expectation. Neither integer is an exact attendance claim. Participants and volunteers remain separate roles and never substitute for audience.

The original versioned prompt and JSON schema are reused without retuning them after seeing supplemental responses. Before the first call, the module saves hashes of the new source/reference file and all four original frozen inputs, together with the original 19/20 baseline, in results/event_extraction_additional_freeze.json. Live results are saved only to results/event_extraction_additional_live.json. The module records attempts, successfully validated calls, model snapshot, token usage, response IDs, request/output hashes and the raw structured records. No key or authorization header is saved.

The supplementary score covers the same five fields per source (15 field comparisons total). It is exact agreement with provisional AI draft references, not accuracy against human-validated gold. Additional checks explicitly report positive audience extraction, withholding a crowd number for the participant-only text, any non-audience number substituted as crowd, and whether quantity qualifiers also appear in the model's ambiguity prose. Semantic discrepancies and qualifier omissions must remain visible; references are not edited to improve a result after the call.

The raw live artifact stays separate from recorded-mode replay. Recorded mode verifies the frozen inputs and request/output provenance, then makes zero new API calls. It never silently uses a fixture when evidence is absent or stale. Existing human-entered CSV review fields are preserved on a same-output rerun, and a different output is rejected rather than overwriting prior human review work.

## Human review and scope

The generated [human review sheet](human_review_additional.md) and results/event_extraction_additional_review.csv contain the input excerpt, draft reference, actual model output and explicit pending judgment fields. Human judgment and reviewer fields begin blank. A successful API run or AI review does not complete them.

These supplemental texts do not feed the demand forecast, event uplift or crew plan. Head Of The Charles already appears in the original calendar, and the new sources must not create duplicate events or additional audience-based bike demand. The original event scenario remains an uncalibrated retrospective assumption. Supplemental extraction success would validate only this small text contract, not its operational effect.

## First separate live run

Three additional real OpenAI Responses API calls completed on 27 October 2026 JST using returned snapshot gpt-4.1-mini-2025-04-14. All three passed the unchanged structural/schema and literal-evidence validator, but that validator did not establish semantic correctness. Recorded usage was 1,941 input tokens and 437 output tokens. The original four-case artifact and 19/20 result were unchanged.

The separate result is **11/15 fields (73.33%) exact agreement with the frozen AI draft references**. Both positive crowd examples matched their draft numbers (2/2), but the participant-only example failed (0/1 null audience): it incorrectly placed the 30,000 participants in expected_crowd_size. It also filled both dates with 2026-04-21 despite no event day appearing in the input, while its own ambiguity text acknowledged the date was inferred. These are substantive grounding/role errors, not successful extraction. The fourth disagreement was a source-supported location-format expansion from the street alone to street plus city. The original score remains unadjusted.

Neither positive output repeated the numeric qualifier in its ambiguity prose. The original evidence_text and frozen companion reference annotations still retain the lower-bound/approximation words, so consumers must display those annotations and must not treat the bare integer fields as exact attendance. The BU output additionally stated that the river spans multiple municipalities, a claim not established in the provided short excerpt. Its null city is appropriate, but this explanatory claim needs separate human review.

The supplementary result therefore exposes a limitation that the first all-null crowd dataset did not reveal. Do not present the two positive matches as evidence that participants are reliably distinguished from audience, or that schema acceptance prevents guessed dates. No labels, source snippets, original prompt or schema were retuned after these responses. Actual human judgments remain blank/PENDING in the review sheet.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_event_validation.py -v
.\.venv\Scripts\python.exe -m bluebikes.event_validation --mode live
.\.venv\Scripts\python.exe -m bluebikes.event_validation --mode recorded
```

Only the explicit live command makes the authorized additional API calls. Keep OPENAI_API_KEY in the existing ignored local configuration; do not display it, copy it into documents or use credential backups.
