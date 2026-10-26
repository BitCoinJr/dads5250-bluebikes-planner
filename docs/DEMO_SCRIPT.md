# Three-minute demo script (English)

AI-generated draft; all three members must review and contribute. Numbers below are generated from `results/summary.json`, not manually typed claims. Recording and upload are **not done**. Speak only the paragraphs, not the headings or stage directions; rehearse timing to three minutes.

## 0:00-0:30 Problem and data

Bluebikes needs bikes where riders start and spare docks where they finish. Our prototype turns public trips into monthly staffing for 13 municipalities. We trained on 2024 and 2025, holding out January through September 2026. Current station capacities approximate historical docks; unmatched stations remain excluded and audited.

Show `results/figures/demand_forecast.png`.

## 0:30-1:05 Event input and GenAI

Here is an official event announcement. Our prompt asks OpenAI for dates, location, city, crowd size and evidence in JSON. Structured output and local validation preserve null when crowd size is absent. We replay recorded real API extractions, with source and prompt provenance checked. Exact agreement with draft labels is 19 of 20 fields; human review remains pending. Extracted facts remain separate from assumed demand effects.

Show Notebook event input, prompt and validated JSON.

## 1:05-1:45 Plan change

Stations start each day half full. Hourly flows estimate boundary corrections; resetting also counts as work. These are proxy handling tasks, not measured rebalancing or lost trips. The planner enforces hiring delays, severance, seasonal minimum contracts and the eight-crew cap, including mandatory 2027 costs. Compare the base table with our event stress scenario: three thousand assumed tasks per eligible event. That coefficient is uncalibrated, and later-published sources make this a retrospective scenario. Default uplift is zero to avoid double counting seasonality.

Show `results/figures/crew_plan.png` and the event plan delta table.

## 1:45-2:25 Validation and limitations

Held-out forecast WAPE is 9.7%. September has missing return-boundary departures, so January-August is also reported. Initial crews leave 326,681 proxy tasks uncovered; our frozen plan leaves 48,127. Annual crew cost plus committed seasonal tail is $1,837,200. Assumed customer losses stay separate. We stress demand by twenty percent and test an assumed e-bike capacity penalty. Event-scenario WAPE is 8.9%, reported whether better or worse.

Show backtest and sensitivity figures.

## 2:25-3:00 Architecture and strength

The notebook connects small Python modules for data, inventory, forecasting, extraction and optimization. Figures and this script share the same results. Our strength is traceability with hand-checkable tests. Capacity units and shared-city crews require review; dedicated-city results are also available. Before submission we still need TA confirmation, all-member review, and the recorded, uploaded demo.

Show `docs/architecture.md`. Do not describe the submission as complete until the video link and required reviews exist.
