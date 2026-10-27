# Hand calculation of bike handling and completed relocations

Every station, trip and hourly value on this page is a **synthetic hand-count example**, not observed Bluebikes data. These examples explain the existing inventory algorithm and remain separate from the forecast and backtest inputs. Run `build_unit_examples()` from `bluebikes.unit_examples` to obtain the tables used by the submission Notebook.

## Inventory rule and units

Stations A and B each have 4 docks and start the day with `floor(4 / 2) = 2` bikes. For each station-hour:

1. `unconstrained stock = opening stock + arrivals - departures`.
2. A negative stock needs `-unconstrained stock` supplied bikes. Stock above 4 needs `unconstrained stock - 4` collected bikes.
3. Clip the corrected stock to `[0, 4]`. At the end of the day, supply or collect enough bikes to reset stock to 2.

The proxy counts **one handling action for each supplied or collected bike**, including reset work. One bike picked up at B and delivered to A therefore contributes **two handling actions** when both endpoints are included. An algebraically paired pickup and delivery counts as **one completed relocation**. These invented flows establish counts, not feasible routes or actual van operations; within-hour ordering, travel time, depot stock and truck stock are not modeled.

## Example 1 Customer trips from A to B

Four customer bikes depart A and arrive at B in the same hour. Arrivals and departures are netted within each station-hour.

| Station | Opening | Departures | Arrivals | Net arrivals | Unconstrained | Supply | Collect | Corrected closing |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A |2|4|0|−4|−2|2|0|0|
| B |2|0|4|4|6|0|2|4|

The end-of-day reset adds another 2 deliveries to A and 2 collections from B.

| Station | Before reset | Reset target | Reset supply | Reset collection | Total handling actions |
|---|---:|---:|---:|---:|---:|
| A |0|2|2|0|4|
| B |4|2|0|2|4|
| Total | | |2|2|**8**|

Within-day corrections contribute 2 supplies + 2 collections = 4 actions; resets contribute another 4 actions. If the two within-day collections at B can be paired with the two deliveries to A, and likewise for the reset, this is **4 completed relocations from B to A and 8 endpoint actions**. The virtual-depot proxy does not establish that pickups can happen before deliveries.

Station conservation includes the reset:

`opening stock + arrivals + within-day supply + reset supply = final stock after reset + departures + within-day collection + reset collection`.

- A: `2 + 0 + 2 + 2 = 2 + 4 + 0 + 0 = 6`.
- B: `2 + 4 + 0 + 0 = 2 + 0 + 2 + 2 = 6`.

## Example 2 Each station has zero net flow but work remains

The first hour is identical. In the next hour, four customer bikes return from B to A.

| Hour | Station | Opening | Departures | Arrivals | Unconstrained | Supply | Collect | Closing |
|---|---|---:|---:|---:|---:|---:|---:|---:|
|08:00| A |2|4|0|−2|2|0|0|
|08:00| B |2|0|4|6|0|2|4|
|09:00| A |0|0|4|4|0|0|4|
|09:00| B |4|4|0|0|0|0|0|

Reset now collects 2 from A and supplies 2 to B. Each station had 4 departures and 4 arrivals: **daily net flow is zero at both stations**, yet the within-day corrections and reset still total **8 handling actions**. Algebraic pairing gives 2 relocations from B to A during the day and 2 from A to B for the reset, or 4 completed relocations under the pairing assumption. Monthly departure-minus-arrival totals cannot recover this work.

Conservation is A: `2 + 4 + 2 = 2 + 4 + 2 = 8`; B: `2 + 4 + 2 = 2 + 4 + 2 = 8`. The supplies and collections occur in different parts of each station's day.

## Example 3 An unbalanced city cannot simply divide by two

Suppose A has 4 departures, B is idle, and the customer arrivals occur outside this two-station example. A requires 2 supplied bikes during the hour and 2 more for the reset. The proxy counts **4 local delivery actions and no local collection actions**.

Those 4 local actions do not establish 2 completed relocations. An external depot must supply the bikes, and the depot's pickup endpoints are outside the stations counted here. The example therefore reports `assumed_paired_relocations = null`. More generally, city supply and collection totals need not balance, especially when customer trips cross city boundaries. A factor-of-two interpretation for the full plan is a declared sensitivity scenario requiring a pairing assumption, not an empirical conversion of every proxy action into a physical relocation.

## Keeping 120 bikes per shift unchanged

The course specification stays **120 bikes/shift and 6 shifts/week**. The ambiguity is what one course “bike” means.

| Interpretation | Example 1 workload in the interpreted course unit | Required crew shifts |
|---|---:|---:|
|120 handling actions/shift |8 handling actions |`8 / 120 = 0.066667`|
|120 completed paired relocations/shift |4 assumed completed relocations |`4 / 120 = 0.033333`|

For a 31-day month, one crew has `120 × 6 × 31 / 7 = 3,188.571429` course bike-units of capacity. This calendar-day conversion averages fractional workweeks; it is not an actual shift roster.

- If the course unit is a handling action, endpoint capacity is 3,188.571429 actions per crew-month.
- If the course unit is a completed relocation and both endpoints can be paired, the same 3,188.571429 completed relocations correspond to 6,377.142857 endpoint actions. The 120-bike course parameter remains unchanged; endpoint capacity is multiplied by 2 under that assumption.

Whole-crew decisions are discrete, include hiring and contract constraints, and must be reoptimized. One cannot infer that a factor-of-two capacity assumption halves crew counts or cost. See [the generated unit-interpretation plan comparison](../results/unit_interpretation_comparison.csv) for the actual rerun results; this hand calculation does not invent their staffing or cost effects.

## Reproduce the example

```python
from bluebikes.unit_examples import build_unit_examples

examples = build_unit_examples()
print(examples["provenance"])
display(examples["hourly_steps"])
display(examples["daily_reset"])
display(examples["station_conservation"])
display(examples["case_summary"])
display(examples["unit_conversion"])
display(examples["monthly_capacity"])
```

The function checks the hand-entered expected corrections against the existing `inventory_proxy`. It neither changes that algorithm nor reads or writes the observed-data files.
