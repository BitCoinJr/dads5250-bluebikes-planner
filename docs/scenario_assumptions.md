# Review scenario assumptions

The new scenario module makes no API calls and fits no forecast. It receives the frozen forecast produced only from 2024–2025, recorded event records, and separate January–September 2026 observed inventory proxies. Actual demand is used only after plans are fixed.

The focused demo uses the actual extracted Boston Marathon event dated 20 April 2026, if supplied. Its source URL and literal evidence stay attached to the eligible April Boston input. A declared extra 3,000 handling actions changes that city-month, then the same planner reruns with hiring delays and contract constraints. Full-calendar stress uses the existing coefficient for every eligible extracted event. Missing dates/cities, absent forecast city-months and duplicate inputs are exposed in the event ledger; no municipality is inferred from an unsupported landmark. A named city can still have recorded ambiguity requiring review. Payroll effects can extend outside an event's month.

The +3,000 coefficient is uncalibrated and retrospective. It is not extracted crowd size, a fitted effect, demonstrated forecast improvement or observed lost ridership. Human label and semantic review remain separate from schema checks.

The course states **120 bikes per shift**. This stays fixed in every new unit scenario. Only the declared conversion changes:

| Interpretation | Handling actions per course bike | Example: pick up then deliver one bike | January capacity of one crew |
|---|---:|---|---|
| Factor one | 1 | Two handling actions become two course-bike units | 3,188.57 course units = 3,188.57 handling actions |
| Factor two | 2 | Two handling actions become one completed relocation/course-bike unit | 3,188.57 course units = 6,377.14 handling actions |

Both cases use 120 × 6 × 31/7 course-bike units in January. Factor two divides forecast handling demand by two **before replanning**; it does not set `bikes_per_shift=240`. Result shortages convert back to handling actions by multiplying by the same factor. This is a conditional accounting convention, not empirical evidence about van productivity or a resolution of the course wording.

The assumed rider-loss penalty per uncovered **handling action** stays fixed. If that assumption is r affected encounters/action, the factor-two MILP uses 2r encounters per course-bike unit. Thus converting units does not accidentally halve the penalty and confound the comparison. The $5.70 is still per affected encounter; r remains an assumption, not observed customer impact.

Period comparisons keep payroll and service on the same horizon:

- January–December 2026 crew cash cost is compared with annual forecast-proxy shortage. Mandatory 2027 seasonal tail is a separate column.
- January–September 2026 crew cash cost is compared with shortage on the actual-derived proxy for those nine months, using the frozen plan. Annual cost is never compared with only nine months of service.
- Dedicated cities use integer crews. Other municipalities have shared capacity allocations; repeated staffing-group integer counts must not be summed across member cities.

The new factor-two result is a newly optimized plan on the converted forecast. The earlier frozen-plan capacity sensitivity changes service/capacity only and cannot show a new crew/cost recommendation.

## Recorded conditional review

Satoshi Nakamura explicitly adjudicated the eight topics in [MODEL_REVIEW.md](MODEL_REVIEW.md), using AI-assisted review in chat. Record compiled 2026-10-27 JST; exact decision times not recorded. This accepts disclosed assumptions, not empirical validity, TA approval or all-member review. Nominal course capacity is 120 bikes/shift; only the fixed-staffing e-bike stress assumes 90% effective capacity, equivalent to 108 bikes/shift. Forecast/backtest and sensitivity scope are recorded separately; unlisted audit topics remain unapproved.
