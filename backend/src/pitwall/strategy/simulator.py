"""Lap-by-lap race simulator with Monte Carlo safety cars, plus a two-stage strategy search.

Model of one car's race time:

    lap_time[i] = base + lap_coef * i + tyre_penalty(compound, age) + noise      (green lap)
    lap_time[i] = base * sc_lap_factor                                           (SC lap)
    total       = sum(lap_time) + sum(pit_loss at each stop; cheaper if under SC)

All strategies are evaluated on the *same* random draws (common random numbers), so the
differences between them come from the strategy, not from luck in the sampling. That's
what makes "P(best)" meaningful and the ranking stable with only a few thousand sims.

References (docs/REFERENCES.md): Monte Carlo race simulation after Heilmeier et al. (2020) [M17]
and its open implementation https://github.com/TUMFTM/race-simulation (we re-implemented a
much simpler single-car version; no code copied); common random numbers [M18].
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product

import numpy as np

from pitwall.strategy.params import RaceParams


@dataclass(frozen=True)
class Stint:
    compound: str
    laps: int


@dataclass(frozen=True)
class Strategy:
    stints: tuple[Stint, ...]

    @property
    def n_stops(self) -> int:
        return len(self.stints) - 1

    @property
    def pit_laps(self) -> list[int]:
        """Race lap numbers (1-based) at the end of which the car pits."""
        return np.cumsum([s.laps for s in self.stints])[:-1].tolist()

    @property
    def label(self) -> str:
        return " → ".join(f"{s.compound[0]}{s.laps}" for s in self.stints)

    def validate(self, params: RaceParams) -> None:
        if sum(s.laps for s in self.stints) != params.total_laps:
            raise ValueError(f"{self.label}: stints must add up to {params.total_laps} laps")
        if len({s.compound for s in self.stints}) < 2:
            raise ValueError(f"{self.label}: dry races require two different compounds")
        unknown = {s.compound for s in self.stints} - set(params.compounds)
        if unknown:
            raise ValueError(f"Unknown compounds {unknown}")


@dataclass
class SimResult:
    strategy: Strategy
    totals: np.ndarray  # (n_sims,) race time in seconds

    @property
    def mean(self) -> float:
        return float(self.totals.mean())

    def summary(self) -> dict:
        p10, p50, p90 = np.percentile(self.totals, [10, 50, 90])
        return {
            "label": self.strategy.label,
            "stints": [{"compound": s.compound, "laps": s.laps} for s in self.strategy.stints],
            "pit_laps": self.strategy.pit_laps,
            "n_stops": self.strategy.n_stops,
            "mean_s": self.mean,
            "std_s": float(self.totals.std()),
            "p10_s": float(p10),
            "p50_s": float(p50),
            "p90_s": float(p90),
        }


def clean_lap_times(strategy: Strategy, params: RaceParams) -> np.ndarray:
    """Deterministic green-flag lap times, shape (total_laps,)."""
    laps = params.base_lap_time_s + params.lap_coef_s * np.arange(params.total_laps, dtype=float)
    start = 0
    for stint in strategy.stints:
        age = np.arange(1, stint.laps + 1, dtype=float)
        laps[start : start + stint.laps] += params.compounds[stint.compound].tyre_penalty(age)
        start += stint.laps
    return laps


def sample_safety_cars(params: RaceParams, n_sims: int, rng: np.random.Generator) -> np.ndarray:
    """Boolean (n_sims, total_laps): is the safety car out on this lap?"""
    n_laps = params.total_laps
    starts = rng.random((n_sims, n_laps)) < params.sc_prob_per_lap
    starts[:, 0] = False  # no SC deployed before the race has started
    durations = rng.integers(params.sc_min_laps, params.sc_max_laps + 1, size=(n_sims, n_laps))
    sc = np.zeros((n_sims, n_laps), dtype=bool)
    remaining = np.zeros(n_sims, dtype=int)
    for lap in range(n_laps):
        new = (remaining == 0) & starts[:, lap]
        remaining[new] = durations[new, lap]
        sc[:, lap] = remaining > 0
        remaining = np.maximum(remaining - 1, 0)
    return sc


@dataclass
class RaceScenarios:
    """Random draws shared by every strategy (common random numbers)."""

    safety_car: np.ndarray  # (n_sims, n_laps) bool
    noise: np.ndarray  # (n_sims, n_laps) float

    @classmethod
    def sample(cls, params: RaceParams, n_sims: int, seed: int = 0) -> RaceScenarios:
        rng = np.random.default_rng(seed)
        sc = sample_safety_cars(params, n_sims, rng)
        noise = rng.normal(0.0, params.lap_noise_s, size=sc.shape)
        return cls(safety_car=sc, noise=noise)


def simulate(strategy: Strategy, params: RaceParams, scenarios: RaceScenarios) -> SimResult:
    sc = scenarios.safety_car
    laps = np.where(
        sc,
        params.base_lap_time_s * params.sc_lap_factor,
        clean_lap_times(strategy, params) + scenarios.noise,
    )
    pit_idx = np.asarray(strategy.pit_laps, dtype=int) - 1  # in-lap index
    pit_cost = np.where(
        sc[:, pit_idx], params.pit_loss_s * params.sc_pit_loss_factor, params.pit_loss_s
    )
    return SimResult(strategy, laps.sum(axis=1) + pit_cost.sum(axis=1))


def enumerate_strategies(
    params: RaceParams, max_stops: int = 2, min_stint: int = 8, step: int = 1
) -> list[Strategy]:
    """Every legal strategy with 1..max_stops stops, pit laps on a `step`-lap grid."""
    n_laps, compounds = params.total_laps, list(params.compounds)
    out: list[Strategy] = []
    for n_stops in range(1, max_stops + 1):
        pit_grid = range(min_stint, n_laps - min_stint + 1, step)
        for pits in combinations(pit_grid, n_stops):
            lengths = np.diff([0, *pits, n_laps])
            if lengths.min() < min_stint:
                continue
            for combo in product(compounds, repeat=n_stops + 1):
                if len(set(combo)) < 2:
                    continue
                out.append(
                    Strategy(tuple(Stint(c, int(n)) for c, n in zip(combo, lengths, strict=True)))
                )
    return out


def expected_time_no_sc(strategy: Strategy, params: RaceParams) -> float:
    return float(clean_lap_times(strategy, params).sum() + strategy.n_stops * params.pit_loss_s)


def optimize(
    params: RaceParams,
    max_stops: int = 2,
    min_stint: int = 8,
    shortlist: int = 20,
    n_sims: int = 2000,
    seed: int = 0,
) -> list[dict]:
    """Two-stage search.

    1. Score every legal strategy deterministically (no SC, no noise) — cheap.
    2. Monte-Carlo the shortlist (best overall + best few per stop count) on shared scenarios,
       rank by mean race time, and report P(best) = share of scenarios where it was fastest.
    """
    candidates = enumerate_strategies(params, max_stops=max_stops, min_stint=min_stint)
    scored = sorted(candidates, key=lambda s: expected_time_no_sc(s, params))
    picked = list(
        dict.fromkeys(
            scored[:shortlist]
            + [
                s
                for k in range(1, max_stops + 1)
                for s in [x for x in scored if x.n_stops == k][:3]
            ]
        )
    )

    scenarios = RaceScenarios.sample(params, n_sims, seed)
    results = [simulate(s, params, scenarios) for s in picked]
    totals = np.stack([r.totals for r in results])  # (n_strategies, n_sims)
    p_best = np.bincount(totals.argmin(axis=0), minlength=len(results)) / n_sims

    rows = []
    for r, p in zip(results, p_best, strict=True):
        row = r.summary()
        row["p_best"] = float(p)
        row["expected_no_sc_s"] = expected_time_no_sc(r.strategy, params)
        rows.append(row)
    rows.sort(key=lambda row: row["mean_s"])
    best = rows[0]["mean_s"]
    for row in rows:
        row["gap_s"] = row["mean_s"] - best
    return rows
