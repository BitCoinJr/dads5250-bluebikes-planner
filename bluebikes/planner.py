"""Transparent monthly crew allocation, using forecasts only.

The MILP minimizes employment cash costs plus an explicitly assumed shortage
penalty. Rebalancing-proxy bikes are not observed affected customers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import calendar
from numbers import Integral
from typing import Mapping

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


CORE_CITIES = ("Boston", "Cambridge", "Somerville", "Brookline")
OTHER_POOL = "Other cities (shared)"


@dataclass(frozen=True)
class PlannerConfig:
    bikes_per_shift: float = 120.0
    shifts_per_week: float = 6.0
    ft_monthly_cost: float = 54000 / 12 + 1500
    severance_cost: float = 54000 * 0.25
    seasonal_monthly_cost: float = 7800.0
    seasonal_min_months: int = 3
    seasonal_system_cap: int = 8
    affected_users_per_proxy_bike: float = 1.0
    expected_loss_per_affected_user: float = 5.70
    pool_other_cities: bool = True
    initial_ft: Mapping[str, int] = field(default_factory=lambda: {
        "Boston": 6, "Cambridge": 4, "Somerville": 1, "Brookline": 1,
        OTHER_POOL: 2,
    })
    # In dedicated mode, set this to specify where the two initial shared crews go.
    dedicated_other_initial: Mapping[str, int] | None = None
    solver_time_limit_seconds: float = 45.0
    mip_relative_gap: float = 0.001

    @property
    def shortage_penalty(self) -> float:
        return self.affected_users_per_proxy_bike * self.expected_loss_per_affected_user


def capacity_per_crew(year: int, month: int, config: PlannerConfig | None = None) -> float:
    """Calendar-days prorating: 120 bikes * 6 shifts/week * days/7."""
    cfg = config or PlannerConfig()
    return cfg.bikes_per_shift * cfg.shifts_per_week * calendar.monthrange(int(year), int(month))[1] / 7


def _prepare(demand: pd.DataFrame, cfg: PlannerConfig):
    cols = {"year", "month", "city", "demand_bikes"}
    if not cols.issubset(demand.columns):
        raise ValueError(f"Demand requires columns {sorted(cols)}")
    data = demand[list(cols)].copy()
    if data.empty or data.isna().any().any():
        raise ValueError("Demand must be nonempty and have no null values")
    data["year"] = data.year.astype(int)
    data["month"] = data.month.astype(int)
    if set(data.year) != {2026} or set(data.month) != set(range(1, 13)):
        raise ValueError("Planning requires all twelve months of 2026")
    if (data.demand_bikes < 0).any() or not np.isfinite(data.demand_bikes).all():
        raise ValueError("Demand must be nonnegative and finite")
    if data.duplicated(["city", "year", "month"]).any():
        raise ValueError("Duplicate city/month demand rows")
    if data.groupby("city").size().ne(12).any():
        raise ValueError("Every city must have all twelve forecast months")
    if cfg.seasonal_min_months < 1 or cfg.seasonal_system_cap < 0 or cfg.shortage_penalty < 0:
        raise ValueError("Invalid planning configuration")
    if any(isinstance(n, bool) or not isinstance(n, Integral) or n < 0 for n in cfg.initial_ft.values()):
        raise ValueError("Initial full-time crews must be nonnegative integers")
    if cfg.pool_other_cities:
        data["city"] = data.city.where(data.city.isin(CORE_CITIES), OTHER_POOL)
        initial = dict(cfg.initial_ft)
    else:
        initial = {c: n for c, n in cfg.initial_ft.items() if c != OTHER_POOL}
        other = sorted(set(data.city) - set(CORE_CITIES))
        if cfg.dedicated_other_initial is not None:
            allocation = cfg.dedicated_other_initial
            if set(allocation) - set(other):
                raise ValueError("Dedicated other allocation keys must be observed non-core cities")
            if any(isinstance(n, bool) or not isinstance(n, Integral) or n < 0 for n in allocation.values()):
                raise ValueError("Dedicated other allocation crews must be nonnegative integers")
            if sum(cfg.dedicated_other_initial.values()) != cfg.initial_ft.get(OTHER_POOL, 0):
                raise ValueError("Dedicated other allocation must preserve the initial two crews")
            initial.update(cfg.dedicated_other_initial)
        elif other:
            ranking = data[data.city.isin(other)].groupby("city").demand_bikes.sum().sort_values(ascending=False)
            # Deterministic forecast-only allocation; no actual backtest outcomes.
            for index in range(cfg.initial_ft.get(OTHER_POOL, 0)):
                city = ranking.index[index % len(ranking)]
                initial[city] = initial.get(city, 0) + 1
    data = data.groupby(["year", "month", "city"], as_index=False).demand_bikes.sum()
    groups = sorted(set(data.city) | set(initial))
    grid = pd.MultiIndex.from_product([groups, range(1, 13)], names=["city", "month"])
    data = data.set_index(["city", "month"]).reindex(grid)
    # Absent initial cities still retain payroll but have zero supplied forecast.
    data["year"] = 2026
    data["demand_bikes"] = data.demand_bikes.fillna(0.0)
    return data.reset_index(), groups, initial


def _decorate(plan: pd.DataFrame, cfg: PlannerConfig) -> tuple[pd.DataFrame, dict]:
    p = plan.sort_values(["city", "month"]).reset_index(drop=True).copy()
    p["capacity_per_crew"] = [capacity_per_crew(y, m, cfg) for y, m in zip(p.year, p.month)]
    p["capacity_bikes"] = (p.full_time + p.seasonal) * p.capacity_per_crew
    p["unmet_bikes"] = (p.demand_bikes - p.capacity_bikes).clip(lower=0)
    p["served_bikes"] = np.minimum(p.demand_bikes, p.capacity_bikes)
    p["full_time_cost"] = p.full_time * cfg.ft_monthly_cost
    p["seasonal_cost"] = p.seasonal * cfg.seasonal_monthly_cost
    p["severance_cost"] = p.fires_effective * cfg.severance_cost
    p["crew_cost"] = p.full_time_cost + p.seasonal_cost + p.severance_cost
    p["assumed_affected_users"] = p.unmet_bikes * cfg.affected_users_per_proxy_bike
    p["assumed_service_loss"] = p.assumed_affected_users * cfg.expected_loss_per_affected_user
    # A start in month m obliges max(0, m + minimum - 1 - 12) months in 2027.
    p["terminal_seasonal_months"] = p.seasonal_starts * (p.month + cfg.seasonal_min_months - 13).clip(lower=0)
    p["terminal_seasonal_cost"] = p.terminal_seasonal_months * cfg.seasonal_monthly_cost
    for current, decision in [("hires_effective", "hires_decision"), ("fires_effective", "fires_notice"), ("seasonal_starts", "seasonal_start_decision"), ("seasonal_ends", "seasonal_end_decision")]:
        p[decision] = p.groupby("city")[current].shift(-1).fillna(0).astype(int)
    summary = {
        "crew_cost_2026": float(p.crew_cost.sum()),
        "terminal_seasonal_committed_cost_2027": float(p.terminal_seasonal_cost.sum()),
        "total_committed_crew_cost": float(p.crew_cost.sum() + p.terminal_seasonal_cost.sum()),
        "unmet_proxy_bikes": float(p.unmet_bikes.sum()),
        "assumed_affected_users_per_proxy_bike": cfg.affected_users_per_proxy_bike,
        "assumed_service_loss": float(p.assumed_service_loss.sum()),
        "objective_with_assumed_loss": float(p.crew_cost.sum() + p.terminal_seasonal_cost.sum() + p.assumed_service_loss.sum()),
        "max_simultaneous_seasonal": int(p.groupby("month").seasonal.sum().max()),
        "december_full_time": int(p.loc[p.month == 12, "full_time"].sum()),
        "january_2027_continuing_ft_monthly_run_rate": float(p.loc[p.month == 12, "full_time"].sum() * cfg.ft_monthly_cost),
        "other_city_policy": "shared capacity pool (explicit city-rule exception)" if cfg.pool_other_cities else "dedicated cities",
        "cost_horizon_note": "2026 salary accrual plus mandatory seasonal tail; continuing full-time employment beyond 2026 is not a finite lifetime liability. No year-end firing assumed.",
    }
    return p, summary


def plan_crews(demand: pd.DataFrame, config: PlannerConfig | None = None) -> tuple[pd.DataFrame, dict]:
    """Solve a monthly mixed-integer staffing model; Jan staffing is fixed.

    Effective hires/fires/seasonal starts from February correspond to decisions
    made in the previous month. Seasonal ends use the same conservative notice.
    Return the feasible incumbent and report the actual solver status/gap.
    """
    cfg = config or PlannerConfig()
    data, groups, initial = _prepare(demand, cfg)
    # Per group/month: FT, hire, fire, active seasonal, seasonal start/end, unmet.
    n_g, months, width = len(groups), 12, 7
    n = n_g * months * width
    idx = lambda g, t, k: (g * months + t) * width + k
    F, H, L, A, S, E, U = range(width)
    objective = np.zeros(n)
    lower = np.zeros(n)
    upper = np.full(n, np.inf)
    integer = np.ones(n)
    constraints: list[tuple[dict[int, float], float, float]] = []
    demand_array = data.demand_bikes.to_numpy().reshape(n_g, months)
    max_needed = max(1, int(np.ceil(demand_array.max() / min(capacity_per_crew(2026, m, cfg) for m in range(1, 13)))))
    crew_bound = max_needed + sum(initial.values()) + cfg.seasonal_system_cap
    for g, city in enumerate(groups):
        for t in range(months):
            for kind in (F, H, L, A, S, E):
                upper[idx(g, t, kind)] = crew_bound
            integer[idx(g, t, U)] = 0
            objective[idx(g, t, F)] = cfg.ft_monthly_cost
            objective[idx(g, t, L)] = cfg.severance_cost
            objective[idx(g, t, A)] = cfg.seasonal_monthly_cost
            objective[idx(g, t, S)] = cfg.seasonal_monthly_cost * max(0, t + cfg.seasonal_min_months - 12)
            objective[idx(g, t, U)] = cfg.shortage_penalty
            cap = capacity_per_crew(2026, t + 1, cfg)
            constraints.append(({idx(g, t, F): cap, idx(g, t, A): cap, idx(g, t, U): 1.0}, demand_array[g, t], np.inf))
            if t == 0:
                lower[idx(g, t, F)] = upper[idx(g, t, F)] = initial.get(city, 0)
                for kind in (H, L, A, S, E):
                    upper[idx(g, t, kind)] = 0
            else:
                constraints.append(({idx(g, t, F): 1, idx(g, t - 1, F): -1, idx(g, t, H): -1, idx(g, t, L): 1}, 0, 0))
                constraints.append(({idx(g, t, L): 1, idx(g, t - 1, F): -1}, -np.inf, 0))
                constraints.append(({idx(g, t, A): 1, idx(g, t - 1, A): -1, idx(g, t, S): -1, idx(g, t, E): 1}, 0, 0))
                constraints.append(({idx(g, t, E): 1, idx(g, t - 1, A): -1}, -np.inf, 0))
            # Cumulative ends cannot exceed starts whose full minimum was served.
            min_contract = {idx(g, q, E): 1 for q in range(t + 1)}
            min_contract.update({idx(g, q, S): -1 for q in range(max(0, t - cfg.seasonal_min_months + 1))})
            constraints.append((min_contract, -np.inf, 0))
    for t in range(months):
        constraints.append(({idx(g, t, A): 1 for g in range(n_g)}, -np.inf, cfg.seasonal_system_cap))
    matrix = lil_matrix((len(constraints), n))
    lows, highs = [], []
    for row, (coefficients, lo, hi) in enumerate(constraints):
        for col, value in coefficients.items():
            matrix[row, col] = value
        lows.append(lo)
        highs.append(hi)
    result = milp(objective, integrality=integer, bounds=Bounds(lower, upper),
                  constraints=LinearConstraint(matrix.tocsr(), lows, highs),
                  options={"time_limit": cfg.solver_time_limit_seconds, "mip_rel_gap": cfg.mip_relative_gap})
    if result.x is None:
        raise RuntimeError(f"No feasible staffing solution: {result.message}")
    # Independently verify the feasible incumbent before decorating/reporting.
    residual = matrix.tocsr() @ result.x
    if np.any(residual < np.array(lows) - 1e-4) or np.any(residual > np.array(highs) + 1e-4):
        raise RuntimeError("Solver incumbent violates constraints")
    p = data.copy()
    solved = result.x.reshape(n_g * months, width)
    for name, kind in [("full_time", F), ("hires_effective", H), ("fires_effective", L), ("seasonal", A), ("seasonal_starts", S), ("seasonal_ends", E)]:
        p[name] = np.rint(solved[:, kind]).astype(int)
    p, summary = _decorate(p, cfg)
    summary.update({"method": "mixed-integer linear programming", "solver_status": int(result.status), "solver_message": result.message,
                    "solver_mip_gap": float(getattr(result, "mip_gap", np.nan)),
                    "optimality_note": "Solver tolerance/gap applies to the assumed model only; staffing is not validated as a real operational optimum."})
    return p, summary


def baseline_plan(demand: pd.DataFrame, config: PlannerConfig | None = None) -> tuple[pd.DataFrame, dict]:
    cfg = config or PlannerConfig()
    p, _, initial = _prepare(demand, cfg)
    p["full_time"] = p.city.map(initial).fillna(0).astype(int)
    for column in ["hires_effective", "fires_effective", "seasonal", "seasonal_starts", "seasonal_ends"]:
        p[column] = 0
    p, summary = _decorate(p, cfg)
    summary["method"] = "Maintain initial full-time crews"
    return p, summary


def evaluate_plan(plan: pd.DataFrame, actual: pd.DataFrame, config: PlannerConfig | None = None) -> pd.DataFrame:
    """Score a frozen forecast plan against available actual months, without refit."""
    cfg = config or PlannerConfig()
    a = actual[["year", "month", "city", "demand_bikes"]].copy()
    if a.duplicated(["year", "month", "city"]).any():
        raise ValueError("Duplicate actual city/month")
    if (a.demand_bikes < 0).any() or a.demand_bikes.isna().any():
        raise ValueError("Invalid actual proxy demand")
    if cfg.pool_other_cities:
        a["city"] = a.city.where(a.city.isin(CORE_CITIES), OTHER_POOL)
    a = a.groupby(["year", "month", "city"], as_index=False).demand_bikes.sum().rename(columns={"demand_bikes": "actual_demand_bikes"})
    p = plan.merge(a, on=["year", "month", "city"], how="inner", validate="one_to_one")
    # Re-evaluate productivity assumptions without changing frozen staffing.
    p["capacity_per_crew"] = [capacity_per_crew(y, m, cfg) for y, m in zip(p.year, p.month)]
    p["capacity_bikes"] = (p.full_time + p.seasonal) * p.capacity_per_crew
    p["actual_unmet_bikes"] = (p.actual_demand_bikes - p.capacity_bikes).clip(lower=0)
    p["actual_served_bikes"] = np.minimum(p.actual_demand_bikes, p.capacity_bikes)
    p["assumed_actual_service_loss"] = p.actual_unmet_bikes * cfg.shortage_penalty
    return p


def allocate_city_capacity(plan: pd.DataFrame, demand: pd.DataFrame, config: PlannerConfig | None = None) -> pd.DataFrame:
    """Export all-city capacity shares; pooled fractional shares are not crews.

    Integer staffing belongs to staffing_group only. A forecast-proportional
    allocation is a monthly planning convention, not a route schedule.
    """
    cfg = config or PlannerConfig()
    d = demand[["year", "month", "city", "demand_bikes"]].copy()
    d["staffing_group"] = d.city.where(d.city.isin(CORE_CITIES), OTHER_POOL) if cfg.pool_other_cities else d.city
    total = d.groupby(["year", "month", "staffing_group"]).demand_bikes.transform("sum")
    count = d.groupby(["year", "month", "staffing_group"]).city.transform("count")
    d["capacity_share"] = np.where(total > 0, d.demand_bikes / total, 1 / count)
    columns = ["year", "month", "city", "full_time", "seasonal", "capacity_bikes", "crew_cost"]
    counts = plan[columns].rename(columns={"city": "staffing_group", "full_time": "group_full_time_crews", "seasonal": "group_seasonal_crews", "capacity_bikes": "group_capacity_bikes", "crew_cost": "group_crew_cost"})
    out = d.merge(counts, on=["year", "month", "staffing_group"], how="left", validate="many_to_one")
    out["full_time_capacity_share"] = out.group_full_time_crews * out.capacity_share
    out["seasonal_capacity_share"] = out.group_seasonal_crews * out.capacity_share
    out["allocated_capacity_bikes"] = out.group_capacity_bikes * out.capacity_share
    out["allocated_crew_cost"] = out.group_crew_cost * out.capacity_share
    out["assignment_type"] = np.where(out.staffing_group == OTHER_POOL, "shared pool; fractional capacity allocation, not dedicated crews", "dedicated city crews")
    return out.sort_values(["city", "month"]).reset_index(drop=True)
