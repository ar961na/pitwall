"""Tyre degradation models.

Baseline (implemented): one linear model per race, fitted by least squares on green-flag laps

    lap_time = driver_offset[d] + compound_offset[c] + deg_per_lap[c] * tyre_life + lap_coef * lap

* driver_offset soaks up car/driver pace, so the tyre terms are estimated *within* drivers.
* lap_coef lumps fuel burn-off and track evolution together (both make cars faster per lap).
  They are nearly collinear within one race, so one race cannot separate them.
* Degradation is linear; `detect_cliff` finds where single stints steepen.

References (docs/REFERENCES.md): lap-time decomposition into base + tyre + fuel terms follows
Heilmeier et al. (2018) [M5]; driver dummies are a fixed-effects OLS [M6]; cliff detection is
breakpoint regression [M7] with the testing caveat of Davies (1987) [M8].
"""

from dataclasses import asdict, dataclass
from typing import Self

import numpy as np
import pandas as pd
from scipy import stats

from pitwall.data.laps import SLICK_COMPOUNDS


@dataclass
class LinearDegradationModel:
    reference_compound: str
    driver_offset: dict[str, float]
    compound_offset: dict[str, float]
    deg_per_lap: dict[str, float]
    lap_coef: float
    rmse: float
    n_laps: int

    @classmethod
    def fit(cls, laps: pd.DataFrame) -> Self:
        """`laps` needs driver, compound, tyre_life, lap, lap_time_s (use `green_flag_laps`)."""
        drivers = sorted(laps["driver"].unique())
        compounds = [c for c in SLICK_COMPOUNDS if c in set(laps["compound"])]
        if not compounds:
            raise ValueError("No slick-tyre laps to fit")
        ref = "MEDIUM" if "MEDIUM" in compounds else compounds[0]
        others = [c for c in compounds if c != ref]

        is_c = {c: (laps["compound"] == c).to_numpy(float) for c in compounds}
        age = laps["tyre_life"].to_numpy(float)
        columns = (
            [(laps["driver"] == d).to_numpy(float) for d in drivers]
            + [is_c[c] for c in others]
            + [is_c[c] * age for c in compounds]
            + [laps["lap"].to_numpy(float)]
        )
        X = np.column_stack(columns)
        y = laps["lap_time_s"].to_numpy(float)
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)

        nd, no = len(drivers), len(others)
        resid = y - X @ coef
        return cls(
            reference_compound=ref,
            driver_offset=dict(zip(drivers, coef[:nd].tolist(), strict=True)),
            compound_offset={
                ref: 0.0,
                **dict(zip(others, coef[nd : nd + no].tolist(), strict=True)),
            },
            deg_per_lap=dict(zip(compounds, coef[nd + no : -1].tolist(), strict=True)),
            lap_coef=float(coef[-1]),
            rmse=float(np.sqrt(np.mean(resid**2))),
            n_laps=len(y),
        )

    def predict(self, laps: pd.DataFrame) -> np.ndarray:
        mean_driver = float(np.mean(list(self.driver_offset.values())))
        driver = laps["driver"].map(self.driver_offset).fillna(mean_driver)
        offset = laps["compound"].map(self.compound_offset).fillna(0.0)
        deg = laps["compound"].map(self.deg_per_lap).fillna(0.0)
        return (driver + offset + deg * laps["tyre_life"] + self.lap_coef * laps["lap"]).to_numpy()

    def to_dict(self) -> dict:
        return asdict(self)


# Significance level for accepting a breakpoint. Strict on purpose: the breakpoint is chosen by
# grid search, which inflates the plain F-test's false-positive rate (Davies 1987 [M8]).
CLIFF_P_VALUE = 0.001


def detect_cliff(tyre_life: np.ndarray, lap_time_s: np.ndarray, min_laps: int = 5) -> int | None:
    """Tyre age where one stint's degradation steepens ("the cliff"), or None.

    Fits lap_time = a + b*age + c*max(age - k, 0) for every breakpoint k with at least
    `min_laps` laps on each side [M7], keeps the best k with c > 0, and accepts it only if it
    beats a single straight line in an F-test at CLIFF_P_VALUE.
    """
    x, y = np.asarray(tyre_life, float), np.asarray(lap_time_s, float)
    n = len(x)
    if n < 2 * min_laps + 1:
        return None
    line = np.column_stack([np.ones(n), x])
    sse_line = float(np.sum((y - line @ np.linalg.lstsq(line, y, rcond=None)[0]) ** 2))

    best_k, best_sse = None, np.inf
    for k in np.sort(x)[min_laps:-min_laps]:
        hinge = np.column_stack([line, np.maximum(x - k, 0.0)])
        coef = np.linalg.lstsq(hinge, y, rcond=None)[0]
        sse = float(np.sum((y - hinge @ coef) ** 2))
        if coef[2] > 0 and sse < best_sse:
            best_k, best_sse = k, sse
    if best_k is None or best_sse <= 0:
        return None
    f_stat = (sse_line - best_sse) / (best_sse / (n - 3))
    return int(best_k) if stats.f.sf(f_stat, 1, n - 3) < CLIFF_P_VALUE else None


def cliff_ages(laps: pd.DataFrame, model: LinearDegradationModel, min_stints: int = 3) -> dict:
    """Median detected cliff age per compound over all driver stints of a race.

    Lap times are first corrected for driver pace and the fuel/track trend. A compound gets an
    entry only if at least `min_stints` stints show a cliff; a single noisy stint proves little.

    Assumption: a cliff is a late-stint effect, so breakpoints in the first half of a stint are
    ignored. On real races those were early-stint artefacts (e.g. Zandvoort 2025 mediums at
    lap 8 of 22: traffic and tyre warm-up), not tyres falling off.
    """
    corrected = (
        laps["lap_time_s"] - laps["driver"].map(model.driver_offset) - model.lap_coef * laps["lap"]
    )
    found: dict[str, list[int]] = {}
    for (_, _, compound), stint in laps.assign(corrected=corrected).groupby(
        ["driver", "stint", "compound"]
    ):
        stint = stint.sort_values("tyre_life")
        age = detect_cliff(stint["tyre_life"].to_numpy(), stint["corrected"].to_numpy())
        if age is not None and age >= stint["tyre_life"].median():
            found.setdefault(str(compound), []).append(age)
    return {c: int(np.median(a)) for c, a in found.items() if len(a) >= min_stints}
