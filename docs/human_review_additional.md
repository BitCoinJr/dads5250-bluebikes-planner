# Supplemental event extraction human review

**PENDING: no actual human judgment has been entered or claimed.** The input excerpts and AI draft references were frozen before the separate API run. The original four-case 19/20 baseline is unchanged.

Use [the review CSV](../results/event_extraction_additional_review.csv) to enter human_judgment, human_reviewer and human_review_notes. Leave the original AI reference and model output intact. Qualifiers are part of the fact: a lower bound or approximate figure must not become an exact attendance claim.

| Case | Input excerpt | Draft reference (five scored fields) | LLM output (five scored fields) | Human judgment |
|---|---|---|---|---|
| additional_hocr_bu_2026 | October 15, 2026 ... October 16, 17, and 18 ... for one weekend each October, more than 300,000 spectators ... Charles River ... over 12,000 rowers | {"start_date": "2026-10-16", "end_date": "2026-10-18", "location": "Charles River", "city": null, "expected_crowd_size": 300000} | {"start_date": "2026-10-16", "end_date": "2026-10-18", "location": "Charles River", "city": null, "expected_crowd_size": 300000} | PENDING |
| additional_hocr_avive_2026 | October 16-18, 2026 ... Charles River between Boston and Cambridge ... approximately 325,000 unique spectators, 11,500 competitors, and 2,400 volunteers. | {"start_date": "2026-10-16", "end_date": "2026-10-18", "location": "Charles River between Boston and Cambridge", "city": null, "expected_crowd_size": 325000} | {"start_date": "2026-10-16", "end_date": "2026-10-18", "location": "Charles River between Boston and Cambridge", "city": null, "expected_crowd_size": 325000} | PENDING |
| additional_baa_participants_only_2026 | The 2026 Boston Marathon Spectator Guide ... Main Street and see 30,000 participants depart historic Hopkinton! | {"start_date": null, "end_date": null, "location": "Main Street", "city": "Hopkinton", "expected_crowd_size": null} | {"start_date": "2026-04-21", "end_date": "2026-04-21", "location": "Main Street, Hopkinton", "city": "Hopkinton", "expected_crowd_size": 30000} | PENDING |

Two positive sources describe the same Head Of The Charles event; they are correlated and their audience estimates are source-specific. The participant-only case must keep audience null. This is a supplemental text test, not new forecasting demand or an allocation of audience to a city.

Automatic checks found 11/15 exact field agreement, two positive audience-number matches, and a participant-only failure: the model used 30,000 participants as crowd and inferred two event-date fields absent from the excerpt. The location disagreement is a street-plus-city formatting expansion. Both positive outputs omit the numeric qualifier in their ambiguity prose; the source/reference annotations retain the lower-bound/approximation and must accompany the bare number. These are automatic/AI review notes, not filled human judgments. The review CSV has a separate automated_quality_notes column; its human judgment, reviewer and notes fields remain blank/PENDING.

Review dates and venue/city evidence, spectator-versus-participant roles, quantity qualifiers and any unsupported ambiguity prose. Automatic exact-match agreement is not human evaluation. Additional source details: [event_sources_additional.md](event_sources_additional.md).
