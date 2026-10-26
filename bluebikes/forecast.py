"""Two transparent seasonal baselines; all model selection ends in 2025.

Validation: 2024 + Jan-Jun 2025 -> Jul-Dec 2025. Production refit uses
only 2024-2025. Never accepts 2026 rows as model training observations.
"""
from __future__ import annotations

import calendar
import numpy as np
import pandas as pd


def _days(year, month):
    return calendar.monthrange(int(year), int(month))[1]


def error_metrics(actual, predicted):
    a = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    if len(a) == 0:
        return {"n": 0, "mae_bikes": None, "wape": None, "bias_bikes": None}
    return {"n": len(a), "mae_bikes": float(np.abs(a-p).mean()),
            "wape": float(np.abs(a-p).sum()/a.sum()) if a.sum() else None,
            "bias_bikes": float((p-a).sum())}


def _rates(data):
    result = data.copy()
    result["days"] = [_days(y,m) for y,m in zip(result.year,result.month)]
    result["daily"] = result.demand_bikes / result.days
    return result


def _growth(train, months):
    part = train[train.month.isin(months)]
    totals = part.groupby(["city","year"]).agg(demand=("demand_bikes","sum"),days=("days","sum"))
    totals["daily"] = totals.demand/totals.days
    table = totals.daily.unstack("year")
    # Zero historical demand cannot support a relative growth estimate.
    return (table[2025]/table[2024].replace(0,np.nan)).fillna(1).clip(.8,1.2).to_dict()


def forecast_2026(monthly):
    required = {"year","month","city","demand_bikes"}
    if not required.issubset(monthly.columns):
        raise ValueError(f"Missing columns: {required-set(monthly.columns)}")
    train = _rates(monthly[monthly.year.isin([2024,2025])])
    if train.duplicated(["year","month","city"]).any():
        raise ValueError("Duplicate city-months")
    cities = sorted(train.city.unique())
    expected = pd.MultiIndex.from_product([[2024,2025],range(1,13),cities],names=["year","month","city"])
    missing = expected.difference(pd.MultiIndex.from_frame(train[["year","month","city"]]))
    if len(missing):
        raise ValueError(f"Training city-month coverage incomplete ({len(missing)}). No silent filling.")
    if not np.isfinite(train.demand_bikes).all() or (train.demand_bikes<0).any():
        raise ValueError("Demand must be finite and nonnegative")
    growth_validation = _growth(train, range(1,7))
    holdout = train[(train.year==2025)&(train.month>=7)][["city","month","demand_bikes","days"]]
    ref = train[train.year==2024][["city","month","daily"]]
    val = holdout.merge(ref,on=["city","month"],validate="one_to_one")
    val["seasonal_naive"] = val.daily*val.days
    val["capped_growth"] = val.seasonal_naive*val.city.map(growth_validation)
    metrics = []
    for model in ["seasonal_naive","capped_growth"]:
        metrics.append({"model":model,**error_metrics(val.demand_bikes,val[model])})
    scores = pd.DataFrame(metrics)
    # Stable order breaks ties in favor of the simpler seasonal naive.
    selected = scores.sort_values("wape",kind="stable").iloc[0].model
    growth_final = _growth(train,range(1,13))
    out = train[train.year==2025][["city","month","daily"]].copy()
    out["year"] = 2026
    out["days"] = out.month.map(lambda m:_days(2026,m))
    out["growth_factor"] = out.city.map(growth_final) if selected=="capped_growth" else 1.0
    out["demand_bikes"] = out.daily*out.days*out.growth_factor
    out["model"] = selected
    return out.drop(columns="daily").sort_values(["city","month"]).reset_index(drop=True),scores,val


def backtest_predictions(forecast, actual):
    observed = actual[(actual.year==2026)&actual.month.between(1,9)]
    result = forecast.merge(observed[["year","month","city","demand_bikes"]],
                            on=["year","month","city"],how="inner",suffixes=("_forecast","_actual"),validate="one_to_one")
    result["error_bikes"] = result.demand_bikes_forecast-result.demand_bikes_actual
    return result,error_metrics(result.demand_bikes_actual,result.demand_bikes_forecast)
