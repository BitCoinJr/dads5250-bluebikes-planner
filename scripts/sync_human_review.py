"""Rebuild only human review CSVs/notes; no API calls or numerical analysis."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bluebikes.human_review import sync_review_csvs, annotation_lines, METHOD, REVIEWER

def short(record):
    audience = record["expected_crowd_size"]
    return (f"{record['start_date'] or 'unknown'} to {record['end_date'] or 'unknown'}; "
            f"{record['city'] or 'unknown city'}; {record['location']}; spectators "
            + (f"{audience:,}" if audience is not None else "unknown/null"))

def cell(text):
    return str(text).replace("|", "\\|").replace("\n", "<br>")

def sync(root=ROOT):
    review = sync_review_csvs(root)
    record = review["record"]
    header = (
        f"**7 cases adjudicated by {REVIEWER}; not all passed.** Method: **{METHOD}**. "
        "Record compiled **2026-10-27 JST**. Exact per-decision times were not recorded and remain blank. "
        "Review concerns saved input/extraction faithfulness, not independent full-website verification.\n\n"
        "The [user-confirmed decision record](human_review_decisions.json) is preserved byte-for-byte. "
        "Source IDs, frozen request hashes and all seven output SHA256 values match the saved actual API artifacts. "
        "Raw output, inputs, AI draft references, prompt, schema and original **19/20 (95%)** / separate **11/15** scores are unchanged. "
        "No new all-pass or human-gold accuracy score is claimed. "
        "Adjudicated means a decision was recorded; it does not mean a flawed model response was rewritten.\n"
    )
    lines = ["# Human event adjudication and separate annotations", "", header,
             "## Seven saved actual outputs", "",
             "| Source / excerpt | Frozen AI reference | Original actual LLM output | Human case judgment | Separate human annotation |",
             "|---|---|---|---|---|"]
    for source_id,entry in review["events"].items():
        doc=entry["document"]; decision=entry["decision"]
        ref=doc.get("human_gold",doc.get("reference"))
        values=[f"[{source_id}]({doc['source_url']})<br>{doc['source_text']}",
                short(ref),short(entry["output"]),decision["human_judgment"],
                " ".join(annotation_lines(entry,record))]
        lines.append("| "+" | ".join(cell(v) for v in values)+" |")
    lines += ["", "Reviewer and method apply to every row. Field-level original judgments: "
              "[20-field CSV](../results/event_original_four_human_review.csv); additional judgments: "
              "[three-case CSV](../results/event_extraction_additional_review.csv). Both include reviewer, rationale, "
              "method, compiled date, case outcome and exact output hash; adjudication time is blank.",
              "", "## What was remediated", "",
              "- Three original cases accepted with stated conventions; Cambridge's expanded address is source-supported, while the frozen string mismatch stays in the original score.",
              "- Original HOCR and both supplemental HOCR outputs now have separate grounded/qualified annotations in this document, the CSVs, Notebooks and matching app displays. Raw response errors and omitted qualifiers remain visible as original evidence.",
              "- The participant-only Marathon fails start/end date and spectator grounding. Its separate annotation specifies null for all three fields; the raw April 21 / 30,000 output remains unchanged. It is evaluation-only, never a new planning input.",
              "- HOCR sources refer to one event. Do not sum/average their estimates without justification, duplicate demand, infer a single venue, or divide the audience among cities without evidence.",
              "- App annotations require matching source title/URL/excerpt and output hash. They do not auto-confirm editable values or bypass Apply. Live/edited outputs have no inherited adjudication unless the evidence is identical.",
              "", "## Model review scope", "",
              "The **eight** recorded topics are conditionally accepted in [MODEL_REVIEW.md](MODEL_REVIEW.md). "
              "This is disclosed-assumption acceptance, not empirical validation, TA approval or all-member review. "
              "Unrecorded topics remain outside the approval; do not infer agreement from the earlier blank checklist.",
              "", "Regenerate these human materials with §python scripts/sync_human_review.py§. "
              "The immutable decision record is the source. Existing analysis review exporters retain human fields or reject changed evidence; "
              "they do not reset judgments to PENDING. Historical run summaries/evaluation flags describe the pre-adjudication run, not today's review status."]
    (root/"docs/HUMAN_REVIEW.md").write_text("\n".join(lines).replace("§",chr(96))+"\n",encoding="utf-8",newline="\n")
    names={
        "crew_unit_review":"Handling/course-bike conversion",
        "daily_inventory_reset_review":"Daily half-full reset",
        "hiring_and_contract_review":"Hiring, notices and contract horizon",
        "shared_pool_review":"Nine-city shared capacity pool",
        "shortage_loss_conversion_review":"Shortage-to-encounter loss conversion",
        "event_uplift_review":"+3,000 event assumption",
        "forecast_backtest_review":"Forecast / held-out backtest separation",
        "demand_and_ebike_sensitivity_review":"Fixed-staffing demand / e-bike stress",
    }
    model=["# Eight conditionally accepted model assumptions","",
           f"Reviewer: **{REVIEWER}**. Method: **{METHOD}**. Record compiled **2026-10-27 JST**; exact individual times unknown. "
           "Every approval below is conditional on disclosure. It is not empirical validation, TA approval, general model approval or all-member review. "
           "Source: [unchanged user decision record](human_review_decisions.json).",""]
    for i,(key,item) in enumerate(review["assumptions"].items(),1):
        model.extend([f"## {i}. {names[key]}","",f"**{item['human_judgment']}**",""])
        model.extend("- "+text for text in item["confirmed"])
        model.append("")
    model.extend(["## Existing shared versus dedicated comparison","",
                  "Same-period costs and observed-trip-derived shortages; these are existing conditional models, not observed deployment. "
                  "The shared scenario has a course-permission uncertainty, no verified travel-time or simultaneous-service feasibility.",
                  "", "| Period / demand basis | Shared no-event proposal | Dedicated-city alternative |",
                  "|---|---:|---:|",
                  "| Jan–Dec forecast: crew cash | $1,837,200 | $1,732,200 |",
                  "| Jan–Dec forecast: uncovered handling actions | 10,006.65 | 59,985.96 |",
                  "| Jan–Sep observed proxy: crew cash | $1,342,800 | $1,273,800 |",
                  "| Jan–Sep observed proxy: uncovered handling actions | 48,126.86 | 84,997.86 |",
                  "", "Source: [preserved summary](../results/summary.json), proposed/dedicated_city_scenario/backtest fields. "
                  "The original initial-crew comparator is separate. Neither table establishes actual Bluebikes resource deployment.",
                  "", "## Outside the recorded approval", "",
                  "- January fixed staffing is confirmed, but a separate blanket acceptance of all initial-employment assumptions is not recorded.",
                  "- Exact-name station joining, DST/hourly ordering, missing trip boundaries, virtual-depot feasibility and all raw-data audit checks have not received separate blanket human sign-off here.",
                  "- No measured capacity/productivity, rider-loss conversion, event effect, station-hour service or route feasibility is established.",
                  "- **120 nominal bikes/shift** stays the course capacity. **108 equivalent bikes/shift = 120×0.9** applies only to the assumed e-bike productivity stress. Demand/e-bike stresses hold staffing and cash fixed; the separate unit-conversion experiment replans.",
                  "- TA topic registration is confirmed and the narrated video exists; neither validates these assumptions. See [current submission status](SUBMISSION_PREP.md) for remaining member, access, listening and Canvas actions."])
    (root/"docs/MODEL_REVIEW.md").write_text("\n".join(model)+"\n",encoding="utf-8",newline="\n")
    supplementary=["# Supplemental event adjudication","",header,
                   "The two HOCR outputs need the displayed separate annotations; the participant-only output fails semantic grounding. "
                   "These are decisions, not rewritten model responses. Full input/reference/output comparison and exact annotations: "
                   "[HUMAN_REVIEW.md](HUMAN_REVIEW.md). The [review CSV](../results/event_extraction_additional_review.csv) "
                   "stores all three case verdicts and rationale. Supplemental examples remain evaluation-only and do not enter demand planning.",
                   "", "More than 300,000 is a strict lower bound and a recurring audience statement, not measured 2026 attendance. "
                   "Approximately 325,000 denotes an expected approximate unique audience. Do not sum or average these correlated same-event figures, "
                   "add competitors/volunteers, or allocate audiences among cities without evidence. Unsupported multi-municipality explanation in the BU excerpt is separately rejected.",
                   "", "The participant-only source supplies no event day and no spectator count. Start/end dates and audience must be unknown/null in a corrected interpretation; the original response remains available unchanged."]
    (root/"docs/human_review_additional.md").write_text("\n".join(supplementary)+"\n",encoding="utf-8",newline="\n")
    return review

if __name__=="__main__":
    result=sync()
    print(f"Integrated {len(result['events'])} event decisions and {len(result['assumptions'])} conditional assumptions; no model/API run.")
