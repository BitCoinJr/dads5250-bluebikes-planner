"""Pure, local presentation of an AppService result; no model or API calls."""
from __future__ import annotations

from copy import deepcopy
from html import escape
import calendar
import math

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, StrMethodFormatter
import numpy as np
import pandas as pd


def _safe(value):
    return escape("" if value is None else str(value), quote=True)


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(number):
        return "n/a"
    return format(number, ",.0f") if number.is_integer() else format(number, ",.1f")


def _human_month(value):
    text = "" if value is None else str(value)
    parts = text.split("-")
    if (len(parts) == 2 and len(parts[0]) == 4 and parts[0].isdigit()
            and len(parts[1]) == 2 and parts[1].isdigit() and 1 <= int(parts[1]) <= 12):
        return calendar.month_name[int(parts[1])] + " " + parts[0]
    return text


def _money(value):
    return "n/a" if _number(value) == "n/a" else "$" + format(float(value), ",.0f")


def _empty():
    return {"kpi_html": "", "crew_figure": None, "demand_figure": None,
            "annual_table": pd.DataFrame(), "backtest_table": pd.DataFrame(),
            "monthly_table": pd.DataFrame(), "explanation_md": ""}


def _event_keys(records):
    keys = set()
    for row in records:
        try:
            year, month = int(row["year"]), int(row["month"])
            if 1 <= month <= 12:
                keys.add((year, month))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(keys)


def _highlight(ax, months):
    for index, month in enumerate(months):
        ax.axvspan(month - .42, month + .42, color="#e2b95a", alpha=.18,
                   label="Selected event month" if index == 0 else "_event_month", zorder=0)


def _axes_style(ax, frame):
    ax.set_xticks(frame.month, [calendar.month_abbr[int(m)] for m in frame.month])
    ax.set_xlim(float(frame.month.min()) - .5, float(frame.month.max()) + .5)
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=.18)
    ax.spines[["top", "right"]].set_visible(False)


def _crew_plot(frame, group, event_months):
    fig, ax = plt.subplots(figsize=(9, 3.8), layout="constrained")
    for field, label, color, marker in [
        ("full_time", "Full-time", "#305b91", "o"),
        ("seasonal", "Seasonal", "#158474", "s"),
    ]:
        ax.plot(frame.month, frame[field + "_base"], color=color, linestyle="--",
                marker=marker, markersize=4, linewidth=1.8, label=label + " - no event increment")
        ax.plot(frame.month, frame[field + "_scenario"], color=color, linestyle="-",
                marker=marker, markersize=3, linewidth=2.1, label=label + " - event scenario")
    _highlight(ax, event_months)
    _axes_style(ax, frame)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylabel("Crews in staffing group")
    ax.set_title("Monthly staffing: " + _safe(group), loc="left", fontsize=12)
    ax.legend(fontsize=8, ncol=2, loc="best")
    plt.close(fig)
    return fig


def _demand_plot(frame, group, event_months):
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True, sharey=True, layout="constrained")
    for ax, suffix, title in zip(axes, ["base", "scenario"],
                                 ["No event increment", "Reviewed event scenario"]):
        months = frame.month.to_numpy(dtype=float)
        demand = frame["demand_handling_actions_" + suffix].to_numpy(dtype=float)
        capacity = frame["capacity_handling_actions_" + suffix].to_numpy(dtype=float)
        ax.plot(months, demand, color="#674a8b", marker="o", markersize=3,
                linewidth=1.8, label="Demand proxy")
        ax.plot(months, capacity, color="#305b91", linestyle="--", linewidth=1.8,
                label="Replanned capacity" if suffix == "scenario" else "Crew capacity")
        if suffix == "scenario":
            prior_capacity = frame["capacity_handling_actions_base"].to_numpy(dtype=float)
            ax.plot(months, prior_capacity, color="#89929b", linestyle=":", linewidth=1.5,
                    label="Prior-plan capacity", zorder=3)
        ax.fill_between(months, capacity, demand, where=demand > capacity,
                        interpolate=True, color="#c9574b", alpha=.3,
                        label="Uncovered after replanning" if suffix == "scenario" else "Uncovered handling actions")
        if suffix == "scenario" and event_months:
            selected = frame[frame.month == event_months[0]]
            if len(selected):
                first = selected.iloc[0]
                callout = ("New demand " + format(float(first["demand_handling_actions_scenario"]), ",.0f")
                           + " / Prior capacity " + format(float(first["capacity_handling_actions_base"]), ",.0f"))
                ax.annotate(callout,
                            xy=(float(first.month), float(first["demand_handling_actions_scenario"])),
                            xytext=(.99, 1.03), textcoords="axes fraction", ha="right", va="bottom",
                            fontsize=8.5, color="#4d5964", annotation_clip=False,
                            arrowprops={"arrowstyle": "->", "color": "#89929b", "lw": .9},
                            bbox={"facecolor": "white", "edgecolor": "none", "alpha": .9, "pad": 2})
        _highlight(ax, event_months)
        _axes_style(ax, frame)
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.set_title(title, loc="left", fontsize=10)
        ax.set_ylabel("Handling actions")
        ax.tick_params(labelbottom=True)
    axes[0].legend(fontsize=8, ncol=2, loc="best")
    axes[1].legend(fontsize=8, ncol=2, loc="upper left")
    axes[1].set_xlabel("Shading: all selected event months. Callout: first event month only.", fontsize=8)
    fig.suptitle("Monthly demand and capacity: " + _safe(group), x=.02, ha="left", fontsize=12)
    plt.close(fig)
    return fig


def _kpis(frame, summary, event_keys):
    city, group = _safe(summary["selected_city"]), _safe(summary["selected_group"])
    selected = frame[frame.apply(lambda row: (int(row.year), int(row.month)) in event_keys, axis=1)]
    heading = '<div class="bb-kpis"><p><strong>Selected city: ' + city + '</strong>'
    heading += ' &nbsp;|&nbsp; Staffing group: ' + group + '</p>'
    if not len(selected):
        return heading + '<p>No matching event month is available in this result.</p></div>'
    cards = []
    for row in selected.to_dict("records"):
        unchanged = all(float(row[a + "_base"]) == float(row[a + "_scenario"])
                        for a in ["full_time", "seasonal", "crew_cost"])
        month = calendar.month_name[int(row["month"])] + " " + str(int(row["year"]))
        card = '<section class="bb-event-card" style="border:1px solid #dce3e8;border-radius:10px;padding:16px;flex:1;min-width:260px">'
        card += '<h3 style="margin:0 0 10px">' + city + ' / ' + month + '</h3>'
        if summary["selected_city"] != summary["selected_group"]:
            card += '<p style="font-size:.9rem;margin:0 0 12px">Crew counts apply to shared group: ' + group + '</p>'
        card += '<div class="bb-metric-grid">'
        for label, key, formatter in [("Full-time crews", "full_time", _number),
                                       ("Seasonal crews", "seasonal", _number),
                                       ("Monthly crew cash cost", "crew_cost", _money)]:
            card += '<div class="bb-metric" style="margin:12px 0">'
            card += '<div class="bb-metric-label" style="font-size:.85rem;color:inherit;opacity:.9">' + label + '</div>'
            card += '<div class="bb-metric-value" style="font-size:1.6rem;font-weight:700;line-height:1.25">'
            card += formatter(row.get(key + "_base")) + ' &rarr; ' + formatter(row.get(key + "_scenario"))
            card += '</div></div>'
        card += '</div>'
        card += '<div style="font-size:.9em;margin-top:10px">Hiring decision month: '
        card += _safe(_human_month(row.get("hire_decision_month_for_active_month", "not available"))) + '<br>Prior-month hires: '
        card += _number(row.get("prior_month_hires_decision_base")) + ' &rarr; '
        card += _number(row.get("prior_month_hires_decision_scenario")) + '</div>'
        if unchanged:
            card += '<div style="font-size:.9em;margin-top:8px">No crew or monthly cash-cost change.</div>'
        cards.append(card + '</section>')
    return heading + '<div style="display:flex;flex-wrap:wrap;gap:12px">' + "".join(cards) + '</div></div>'


def _period_table(rows, months):
    frame = pd.DataFrame(rows)
    if frame.empty or "period_months" not in frame:
        return pd.DataFrame()
    selected = frame[frame.period_months == months]
    labels = {"initial_crews": "Initial crews", "no_event": "No event increment",
              "reviewed_event": "Reviewed event scenario"}
    result = []
    for row in selected.to_dict("records"):
        values = {
            "Plan": labels.get(row.get("scenario"), _safe(row.get("scenario"))),
            "Cash cost": _money(row.get("crew_cash_cost_in_period")),
            "Uncovered actions": _number(row.get("uncovered_handling_actions")),
            "Peak crews (FT / S / total)": " / ".join(_number(row.get(key)) for key in [
                "peak_full_time_crews_in_period", "peak_seasonal_crews_in_period", "peak_total_crews_in_period"]),
        }
        if months == 12:
            values["2027 seasonal tail (separate)"] = _money(row.get("mandatory_seasonal_tail_cost_2027_separate"))
        result.append(values)
    return pd.DataFrame(result)


def _monthly_table(frame):
    rows = []
    for row in frame.to_dict("records"):
        crews = lambda suffix: _number(row["full_time_" + suffix]) + "; " + _number(row["seasonal_" + suffix])
        rows.append({
            "Month": f"{int(row['year'])}-{int(row['month']):02d}",
            "Crews (FT; seasonal)": crews("base") + " -> " + crews("scenario"),
            "Cash cost": _money(row["crew_cost_base"]) + " -> " + _money(row["crew_cost_scenario"]),
            "Uncovered actions": _number(row.get("uncovered_handling_actions_base")) + " -> " + _number(row.get("uncovered_handling_actions_scenario")),
            "Prior hires": _safe(row.get("hire_decision_month_for_active_month", "n/a")) + ": "
                           + _number(row.get("prior_month_hires_decision_base")) + " -> "
                           + _number(row.get("prior_month_hires_decision_scenario")),
        })
    return pd.DataFrame(rows)


def render_result(result: dict | None) -> dict:
    """Return fresh Gradio-ready views; never mutate result or access data/API."""
    if not isinstance(result, dict):
        return _empty()
    data = deepcopy(result)
    summary = data.get("summary") or {}
    if not isinstance(summary, dict) or not summary.get("selected_city") or not summary.get("selected_group"):
        return _empty()
    frame = pd.DataFrame(data.get("monthly_chain", []))
    required = ["year", "month", "full_time_base", "full_time_scenario", "seasonal_base", "seasonal_scenario",
                "crew_cost_base", "crew_cost_scenario", "demand_handling_actions_base", "demand_handling_actions_scenario",
                "capacity_handling_actions_base", "capacity_handling_actions_scenario"]
    if frame.empty or any(field not in frame for field in required):
        return _empty()
    numeric = frame[required].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        return _empty()
    frame[required] = numeric
    frame = frame.sort_values(["year", "month"]).reset_index(drop=True)
    if frame.duplicated(["year", "month"]).any() or not frame.month.between(1, 12).all():
        return _empty()
    keys = _event_keys(data.get("city_month_inputs", []))
    event_months = sorted({month for year, month in keys
                           if year in set(frame.year) and month in set(frame.month)})
    conversion = summary.get("handling_actions_per_course_bike", "not available")
    increment = summary.get("increment_handling_actions_per_event")
    city, group = _safe(summary["selected_city"]), _safe(summary["selected_group"])
    scope = ("The selected city is " + city + "; crew counts and charts cover staffing group **" + group
             + "**. Period tables cover the **whole system**, not just this city. ")
    if summary["selected_city"] != summary["selected_group"]:
        scope += "This city shares the group's capacity; group crews are not dedicated city crews. "
    explanation = scope + (
        "\n\nAll before/after arrows mean **no event increment -> reviewed event scenario**. "
        "Annual forecast-proxy results and January-September observed-proxy results stay in separate tables; "
        "mandatory 2027 seasonal cost is separate from annual crew cash cost. "
        "FT and seasonal peak counts can occur in different months.\n\n"
        "Both demand charts use **handling actions**, including conversion " + _safe(conversion) + ". "
        "The course's 120 bikes/shift is fixed; conversion changes the declared handling/course-bike relationship. "
        "Shading marks all selected event calendar months, including a zero-increment case. "
        "The scenario's dotted gray line is prior-plan capacity; its dashed blue line is replanned capacity. "
        "The first-event callout compares new demand with prior capacity; all other event months remain shaded. "
        "Red fill is demand above the capacity of that panel, after replanning in the scenario panel. "
        "Monthly capacity does not guarantee station-hour service; "
        "this proxy is not lost trips or observed customer loss.\n\n"
        "The event increment is **" + _number(increment) + " handling actions per event**, a user-selected, "
        "**uncalibrated retrospective assumption**, not an OpenAI output or demonstrated forecast improvement."
    )
    return {"kpi_html": _kpis(frame, summary, keys),
            "crew_figure": _crew_plot(frame, summary["selected_group"], event_months),
            "demand_figure": _demand_plot(frame, summary["selected_group"], event_months),
            "annual_table": _period_table(data.get("period_comparison", []), 12),
            "backtest_table": _period_table(data.get("period_comparison", []), 9),
            "monthly_table": _monthly_table(frame), "explanation_md": explanation}


def executive_summary(chain):
    """Fixed saved Marathon illustration, independent of the session's event.

    Reads an already-computed chain supplied by the caller; no optimizer or API.
    The decision month is found from the prior saved row (one-month lead).
    """
    selected = chain.loc[chain.event_increment_handling_actions.gt(0)]
    example = "<p>Saved illustrative example unavailable.</p>"
    if len(selected) == 1:
        row = selected.iloc[0]
        previous = chain.loc[(chain.city == row.city) & (chain.year == row.year)
                             & (chain.month == row.month - 1)]
        if len(previous) == 1:
            decision = previous.iloc[0]
            active = _human_month(f"{int(row.year):04d}-{int(row.month):02d}")
            hire = _human_month(f"{int(decision.year):04d}-{int(decision.month):02d}")
            example = (
                f'<p class="bb-summary-example"><strong>{_safe(row.city)} / {_safe(active)}</strong></p>'
                f'<p><strong>{_number(row.full_time_base)} → {_number(row.full_time_scenario)}</strong> full-time crews<br>'
                f'<strong>{_money(row.crew_cost_base)} → {_money(row.crew_cost_scenario)}</strong><br>'
                f'monthly crew cash cost<br>Hiring decision: <strong>{_safe(hire)}</strong></p>'
                f'<p class="bb-summary-caveat">Assumes +{_number(row.event_increment_handling_actions)} handling actions. '
                'This is an uncalibrated retrospective scenario, not a measured event effect.</p>')
    return (
        '<section class="bb-summary" aria-label="Executive Summary">'
        '<h2>Where should rebalancing crews work—and when?</h2>'
        '<p class="bb-summary-lead">Turn Bluebikes trip history and event information into monthly crew plans for Greater Boston.</p>'
        '<div class="bb-summary-grid">'
        '<article><span class="bb-summary-step">01 · THE PROBLEM</span>'
        '<h3>Bikes and docks fall out of balance</h3>'
        '<p>Trips move bikes unevenly across stations. Some stations run short of bikes; others run short of empty docks.</p></article>'
        '<article><span class="bb-summary-step">02 · THE DECISION</span>'
        '<h3>Where to staff, when to hire</h3>'
        '<p>Plan full-time and seasonal crews each month of 2026, including hiring and contract starts.</p>'
        '<p>Four cities have dedicated crews; nine others share a pool. One crew = a driver + van.</p></article>'
        '<article><span class="bb-summary-step">03 · AI + ANALYTICS</span>'
        '<h3>Extract facts, then plan</h3>'
        '<ul><li><strong>Python:</strong> 2024–2025 trips → workload and crew plans.</li>'
        '<li><strong>OpenAI:</strong> dates, locations and audience information, when stated.</li>'
        '<li><strong>A person:</strong> reviews facts and supplies an explicit demand scenario.</li>'
        '<li><strong>Backtest:</strong> Jan–Sep 2026 trips kept separate.</li></ul></article>'
        '<article class="bb-summary-demo"><span class="bb-summary-step">04 · ILLUSTRATIVE SCENARIO</span>'
        '<h3>Saved Marathon example</h3>'
        '<p class="bb-summary-caveat">Fixed explanation example; independent of your event selection below.</p>'
        + example + '</article></div>'
        '<p class="bb-summary-foot">Baseline means a model plan, not actual Bluebikes crew deployment. '
        'OpenAI extracts text; it does not predict added demand or crew counts.</p></section>')
