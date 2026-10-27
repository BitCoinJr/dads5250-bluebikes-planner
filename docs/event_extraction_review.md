# Historical AI review — current human status

The original AI review below is preserved as historical context. Satoshi later adjudicated all seven saved-input cases; see [current judgments and annotations](HUMAN_REVIEW.md). Raw responses and frozen scores remain unchanged. Statements about pending human review below describe the earlier review, not current status.

# AI review of the first live event extraction

Four actual OpenAI Responses API calls completed on 27 October 2026 at approximately 08:35 JST (26 October 23:35 UTC), using requested model gpt-4.1-mini and returned snapshot gpt-4.1-mini-2025-04-14. The frozen-reference exact-match result remains **19 of 20 fields, 95%**. This document is an independent AI review of the saved responses and supplied excerpts. It is **not human review**, human-validated ground truth, or evidence of general extraction accuracy.

## Evidence and frozen evaluation

The reviewed artifact is [event_extraction_live.json](../results/event_extraction_live.json). It records four completed live calls, response IDs, execution timestamps, token usage, latency, and request/output hashes. It is separate from the zero-call [fixture artifact](../results/event_extraction_fixture.json). No credentials were read, displayed or used by this reviewer, and this review made no API calls.

The reference file, prompt and schema were inspected before the live output was available. Their SHA256 hashes were recorded in the review handoff and were unchanged on the post-run check:

| Frozen file | SHA256 |
|---|---|
| fixtures/event_documents.json | 3895EA1889A90A2BE644A75C6B13CCBD5C963E37BE3F5A0E086FA0FC8CD6ECE4 |
| prompts/event_extraction_v1.txt | 80C752920EA81817756F1BBF5DD8C3A85E947D78BD4C0E5765EA306275DC7A61 |
| prompts/event_schema.json | A5978EE3D4F79054F4F82483AA1588E4B38FFC8DE4774A74F7A69F391C93A556 |

A read-only recorded-mode run returned recorded_live_outputs_validated, four recorded API calls, zero new API calls, and the same 19/20 result. This verified that all four saved records passed the current local schema, date/chronology and URL/evidence checks and that their request/output hashes matched the current frozen inputs. These are reproducibility and structural checks, not cryptographic proof of provider authorship or proof that every natural-language assertion is true.

Scoring covers exactly five fields for each of four examples: start date, end date, location, city and expected crowd size. The reference labels are provisional agent-authored drafts awaiting actual team human review. Event name, evidence text, source URL, missing-information lists and ambiguity text are not part of the 20-field exact-match denominator; some of those receive separate structural/provenance validation.

## Record-by-record findings

| Example | Exact matches | AI assessment against the supplied excerpt |
|---|---:|---|
| Boston Marathon | 5/5 | Event date and route match the excerpt. Boston follows the frozen prompt's explicitly stated route-endpoint convention, rather than allocating demand among all route municipalities. Crowd remains null; the stated athlete count was correctly not converted to an audience estimate. |
| Boston Pops | 5/5 | Date, named venue and city are supported. No numerical audience estimate is supplied, so null is appropriate. |
| Cambridge science event | 4/5 | Dates, city and null crowd match. The location includes the city, state and ZIP from the supplied source address, whereas the draft reference stops at the street. The additional address components are supported; this is an exact-string disagreement rather than an identified factual error. |
| Head Of The Charles | 5/5 | The multi-day dates and named hospitality venues match the excerpt. No municipality is stated, and city remains null. No numerical audience estimate is present, and crowd remains null. The ambiguity prose has a separate caveat below. |

The Cambridge location disagreement was anticipated during the pre-response review. The original score has not been adjusted, the reference has not been shortened or expanded after seeing the answer, and no alternative 100% semantic score is claimed.

## Unscored semantic caveats

The Head Of The Charles ambiguity text says the event is known to span multiple locations. That broader assertion is not clearly established by the short supplied excerpt and uses knowledge-like phrasing despite the prompt's instruction to stay within the provided text. The null city result is still correct for the excerpt. Human reviewers should flag this unsupported explanatory wording separately; it is not counted as an error or success by the original 20-field metric.

The Cambridge draft reference mentions the full official page's Festival/Carnival naming ambiguity. The API input includes the short selected excerpt and title, not that descriptive full-page text. The model therefore cannot be expected to reproduce that extra-context ambiguity. Ambiguity text is outside the frozen numerical score.

The Head Of The Charles location is a pair of named hospitality venues, not an established description of the full regatta course. Exact agreement with that reference does not prove that these venues are the best operational representation of the event's location.

## Scope and remaining review

All four expected crowd labels are null. The run demonstrates that these particular excerpts did not trigger an invented audience number; it does not evaluate extraction of genuine positive crowd estimates. The excerpts were deliberately selected and shortened, dates are explicit, and only four examples were evaluated. Field results are related within each example and should not be treated as 20 independent examples. The same AI-assisted implementation process authored the prompt and provisional references. Human-reviewed labels and a larger, independently selected evaluation set remain outstanding.

The three non-null cities and dates can feed the existing declared event scenario. The unknown Head Of The Charles city remains excluded from a city-specific increment. Crowd is not converted into bike demand. The zero-uplift default and +3,000-action retrospective scenario remain assumptions; a successful API call does not validate that coefficient, establish causal event effects, remove seasonal double counting, or convert the retrospective calendar into information available in January 2026.

Before submission, actual team members should review the supplied excerpts and reference labels, adjudicate the address-format convention and unsupported ambiguity wording, and record their review without changing this frozen run's reported result. Any revised prompt, labels, normalization rule or additional examples should be versioned and evaluated separately.
