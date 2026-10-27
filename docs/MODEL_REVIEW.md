# Eight conditionally accepted model assumptions

Reviewer: **Satoshi Nakamura**. Method: **AI-assisted review, explicitly adjudicated by Satoshi in chat**. Record compiled **2026-10-27 JST**; exact individual times unknown. Every approval below is conditional on disclosure. It is not empirical validation, TA approval, general model approval or all-member review. Source: [unchanged user decision record](human_review_decisions.json).

## 1. Handling/course-bike conversion

**ACCEPT_AS_DISCLOSED_MODEL_ASSUMPTION_NOT_EMPIRICAL_CONVERSION**

- Keep course capacity fixed at 120 bikes per shift and six shifts per week.
- Baseline interprets one course bike as one handling action; explicitly disclose this interpretation.
- Two actions per course bike is a sensitivity assumption requiring paired collection and delivery, not a universally valid conversion.
- Do not describe either conversion as empirically established.
- Monthly capacity uses averaged fractional weeks and is not a shift roster or station-hour service guarantee.

## 2. Daily half-full reset

**ACCEPT_AS_DISCLOSED_SIMPLIFICATION**

- Use daily half-full reset as a simplification because actual starting inventories are unknown.
- Include reset handling work in the demand proxy and explicitly disclose it.
- Do not call the proxy actual required relocations or minimum work.
- Do not claim half-full inventories are optimal or reflect actual Bluebikes operations.
- Reset may cause unnecessary moves, while half-full targets may also be insufficient for directional demand; no universal bias direction is established.

## 3. Hiring, notices and contract horizon

**ACCEPT_WITH_DISCLOSED_TIMING_AND_HORIZON_LIMITATIONS**

- Hiring decisions precede effective staffing by one month; January staffing is fixed.
- Full-time monthly cost is 6000 USD, with prior-month release notice and 13500 USD severance per released crew.
- Seasonal monthly cost is 7800 USD, next-month start, minimum three months, and system-wide simultaneous cap of eight crews.
- Include mandatory seasonal commitments beyond 2026 in optimization and report separately from 2026 cash costs.
- Historical decision-month labels in retrospective event scenarios do not prove information was available then.
- Disclose full-time horizon bias; future ongoing salary is not fully priced beyond the planning horizon.
- Seasonal end-decision notice is a conservative implementation convention, distinct from the minimum contract condition.

## 4. Nine-city shared capacity pool

**CONDITIONALLY_ACCEPT_AS_SHARED_CAPACITY_SCENARIO**

- The nine non-core municipalities form one shared capacity scenario; integer crew counts belong to the pool, not each city.
- Fractional city values represent forecast-proportional capacity and cost allocation, not staff assignments, shifts or crew locations.
- Travel time, concurrent service feasibility, and actual deployment locations are not verified.
- Show a dedicated-city comparison alongside the shared scenario.
- Course permission for cross-city sharing remains unconfirmed; this human review does not establish TA approval.

## 5. Shortage-to-encounter loss conversion

**ACCEPT_AS_DISCLOSED_DECISION_ASSUMPTION_WITH_SENSITIVITY**

- One affected rider encounter per uncovered handling action is a modeling assumption, not an empirically validated relationship.
- Affected encounters are not unique riders or observed lost trips.
- Report crew cash costs, uncovered handling actions and assumption-based monetary loss separately.
- Include sensitivity to the encounter conversion rate.
- Do not present reduction in assumed loss as demonstrated revenue improvement.

## 6. +3,000 event assumption

**ACCEPT_AS_UNCALIBRATED_RETROSPECTIVE_SCENARIO**

- Keep the plus-3000 handling-action scenario separate from the zero-increment baseline forecast.
- Do not describe 3000 as an LLM output, crowd-derived estimate, or empirically established event effect.
- Disclose potential double-counting of recurring events already present in historical seasonality.
- Disclose retrospective information availability; no prospective forecast improvement is established.
- Crew and cost changes are conditional calculation results; an event-month cost change is not the full-plan cost change.

## 7. Forecast / held-out backtest separation

**ACCEPT_WITH_PROXY_AND_RETROSPECTIVE_DATA_LIMITATIONS**

- Select the forecast method on July-December 2025 validation, then use 2024-2025 to produce the 2026 forecast and staffing plan.
- Evaluate frozen plans on January-September 2026; do not confuse actual-demand-driven reoptimization with this backtest.
- Evaluation targets observed-trip-derived workload proxies, not observed rebalancing or demonstrated service improvement.
- Disclose retrospective station metadata, month-boundary coverage gaps and event information availability.

## 8. Fixed-staffing demand / e-bike stress

**ACCEPT_AS_FIXED_STAFFING_STRESS_TESTS**

- Demand stress multiplies the already computed observed-trip-derived workload proxy by 0.8, 1.0 or 1.2; it does not resimulate trips or station inventories.
- Keep staffing, hiring, contracts and crew cash costs fixed in these demand and e-bike stress tests.
- The e-bike case assumes effective capacity falls to 90 percent; it is not estimated from e-bike share or an empirically established causal effect.
- Distinguish nominal course capacity of 120 bikes per shift from stressed effective capacity of 108 equivalent bikes per shift.
- Do not describe these tests as reoptimized staffing plans; the separate unit-conversion comparison is a different experiment.

## Existing shared versus dedicated comparison

Same-period costs and observed-trip-derived shortages; these are existing conditional models, not observed deployment. The shared scenario has a course-permission uncertainty, no verified travel-time or simultaneous-service feasibility.

| Period / demand basis | Shared no-event proposal | Dedicated-city alternative |
|---|---:|---:|
| Jan–Dec forecast: crew cash | $1,837,200 | $1,732,200 |
| Jan–Dec forecast: uncovered handling actions | 10,006.65 | 59,985.96 |
| Jan–Sep observed proxy: crew cash | $1,342,800 | $1,273,800 |
| Jan–Sep observed proxy: uncovered handling actions | 48,126.86 | 84,997.86 |

Source: [preserved summary](../results/summary.json), proposed/dedicated_city_scenario/backtest fields. The original initial-crew comparator is separate. Neither table establishes actual Bluebikes resource deployment.

## Outside the recorded approval

- January fixed staffing is confirmed, but a separate blanket acceptance of all initial-employment assumptions is not recorded.
- Exact-name station joining, DST/hourly ordering, missing trip boundaries, virtual-depot feasibility and all raw-data audit checks have not received separate blanket human sign-off here.
- No measured capacity/productivity, rider-loss conversion, event effect, station-hour service or route feasibility is established.
- **120 nominal bikes/shift** stays the course capacity. **108 equivalent bikes/shift = 120×0.9** applies only to the assumed e-bike productivity stress. Demand/e-bike stresses hold staffing and cash fixed; the separate unit-conversion experiment replans.
- TA approval, other members' reviews/contributions, actual rehearsal/recording/upload, grader access and Canvas submission remain incomplete.
