# Geographic crew comparison

The optional app compares **Baseline: no event increment** with **Reviewed event scenario** for the same selected month. It renders two Matplotlib coordinate plots from cached station metadata and the already computed plans. Changing the displayed month selects cached results; it does not call the optimizer, an LLM, a map service or a tile API. This is a geographic overview of the monthly model, not a routing or dispatch plan.

## Station source and read-only audit

Coordinates come from the official Bluebikes station list preserved as [stations_original.csv](../data/metadata/stations_original.csv), whose first line says **Last Updated: 8/21/2026**. Its [source record](../data/metadata/station_source.json) records the [download URL](https://assets.ctfassets.net/p6ae3zqfb1e3/3BswRZgQMp0f8XWBLY6T19/60da57a4630102788a127902bfda9888/-External-_Bluebikes_Station_List__updated_08.21.26_.csv), effective date **2026-08-21**, last download check **2026-10-26 11:08:48.297414 UTC**, byte count and SHA-256. The check timestamp is not a claim that station locations were refreshed for this feature.

A read-only audit of the preserved original and [normalized metadata](../data/metadata/stations.csv) found:

| Check | Result |
|---|---:|
| Original / normalized station rows | 613 / 613 |
| Finite coordinates within latitude/longitude bounds | 613 |
| Missing or invalid coordinate pairs | 0 |
| Duplicate numeric coordinate pairs | 0 |
| Duplicate normalized station-name keys | 0 |
| Municipalities / missing municipality values | 13 / 0 |
| One-to-one normalized-name matches | 613 / 613 (100%) |
| Municipality or dock-count mismatches after joining | 0 |
| Monthly-data municipalities missing from station metadata | 0 |

Latitude ranges from **42.252287 to 42.534669** and longitude from **−71.247759 to −70.870214**. Passing numeric bounds does not independently verify every station's physical location. The join uses the existing NFKC, whitespace-normalized, casefolded station-name key; no fuzzy matching or historic-ID substitution is introduced. The 100% figure describes the two metadata files, not historical trip-endpoint coverage. Existing trip join limitations remain in [data diagnostics](../data/metadata/diagnostics.json).

| Municipality | Station points | Dock count |
|---|---:|---:|
| Arlington | 11 | 123 |
| Boston | 352 | 6,547 |
| Brookline | 20 | 329 |
| Cambridge | 96 | 1,934 |
| Chelsea | 6 | 67 |
| Everett | 15 | 206 |
| Malden | 6 | 66 |
| Medford | 17 | 207 |
| Newton | 15 | 194 |
| Revere | 8 | 88 |
| Salem | 17 | 203 |
| Somerville | 40 | 712 |
| Watertown | 10 | 136 |

## Reading the plots

Small station dots provide geographic context. Crew bubbles appear only for **Boston, Cambridge, Somerville and Brookline**, the four dedicated-city planning units. Each anchor is the unweighted mean of that municipality's station coordinates. These are station-location averages, **not crew bases, depots, city boundaries or event locations**. Bubble labels give integer full-time, seasonal and total crews; scenario labels show the change from the same-month baseline.

The other nine municipalities—Arlington, Chelsea, Everett, Malden, Medford, Newton, Revere, Salem and Watertown—retain station dots and municipality labels. Their **Other cities (shared)** unit is reported separately as text, with one integer pool headcount per plan. It has no invented base coordinate or crew bubble. Do not distribute that headcount into fractional people or repeat it as dedicated staffing in each city. Forecast-proportional capacity shares elsewhere in the project are an accounting assumption, not crew locations or route feasibility.

Both panels use the same fixed extent covering all station points, the same geographic aspect treatment, and one constant **bubble-area-per-total-crew** scale across all twelve months. Compare bubble areas, not radii. The two panels always use the same selected month and counting-unit interpretation; a month change must not silently rescale one panel. Station dots do not encode demand, shortages or assigned crews. No event coordinates, inferred event markers, street network or station-level demand allocation are generated.

## Limits and evidence

The August 2026 snapshot is also applied retrospectively in the analysis; it cannot establish which stations, docks or locations existed in 2024–2025. Coordinates add context to cached model results and do not resolve hourly truck capacity, travel time, depot stock, event access or feasible movement between cities. The explicit reviewed-event increment remains an uncalibrated assumption, and a hiring decision still becomes active the following month.

Rendering uses existing local CSVs and Python plotting libraries, with no new raw-trip processing, download, geocoding, tiles or API calls. Refer to the current feature verification for executed checks; the metadata audit alone does not establish that the app interaction or rendering tests passed. Human review, TA confirmation, team contributions, recording/upload, grader access and Canvas submission remain separate pending requirements in the [review checklist](REVIEW_CHECKLIST.md).
