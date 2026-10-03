"""Tyre degradation models.

Baseline (implemented): one linear model per race, fitted by least squares on green-flag laps

    lap_time = driver_offset[d] + compound_offset[c] + deg_per_lap[c] * tyre_life + lap_coef * lap

* driver_offset soaks up car/driver pace, so the tyre terms are estimated *within* drivers.
* lap_coef lumps fuel burn-off and track evolution together (both make cars faster per lap).
  They are nearly collinear within one race — separating them is part of TASK 2.
* Degradation is linear: no cliff. Detecting the cliff is TASK 2.

References (docs/REFERENCES.md): lap-time decomposition into base + tyre + fuel terms follows
Heilmeier et al. (2018) [M5]; driver dummies are a fixed-effects OLS [M6]; cliff detection is
breakpoint regression [M7] with the testing caveat of Davies (1987) [M8].
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

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
    def fit(cls, laps: pd.DataFrame) -> LinearDegradationModel:
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


def detect_cliff(tyre_life: np.ndarray, lap_time_s: np.ndarray, min_laps: int = 5) -> int | None:
    """TASK 2 — find the tyre age where degradation stops being linear ("the cliff").

    Args:
        tyre_life: tyre age per lap within ONE stint (fuel-corrected lap times work best).
        lap_time_s: lap times for those laps.
        min_laps: minimum laps on each side of a candidate breakpoint.

    Returns:
        The tyre age at which the cliff starts, or None if a single straight line explains
        the stint just as well.
    """
    raise NotImplementedError("TASK 2 — see docs/tasks/02-tyre-degradation.md")
