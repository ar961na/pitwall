import numpy as np
import pandas as pd

from pitwall.models.tyre_deg import LinearDegradationModel
from pitwall.strategy.calibrate import params_from_degradation


def synthetic_race(rng, n_laps=50) -> pd.DataFrame:
    """Two-stop-ish race for 4 drivers with known ground truth."""
    truth = {
        "deg": {"SOFT": 0.09, "MEDIUM": 0.05, "HARD": 0.03},
        "offset": {"SOFT": -0.5, "MEDIUM": 0.0, "HARD": 0.4},
        "driver": {"AAA": 80.0, "BBB": 80.3, "CCC": 80.6, "DDD": 81.0},
        "lap_coef": -0.05,
    }
    plans = {
        "AAA": [("SOFT", 15), ("HARD", 35)],
        "BBB": [("MEDIUM", 25), ("HARD", 25)],
        "CCC": [("SOFT", 12), ("MEDIUM", 20), ("HARD", 18)],
        "DDD": [("HARD", 30), ("SOFT", 20)],
    }
    rows = []
    for drv, plan in plans.items():
        lap = 1
        for comp, n in plan:
            for age in range(1, n + 1):
                t = (
                    truth["driver"][drv]
                    + truth["offset"][comp]
                    + truth["deg"][comp] * age
                    + truth["lap_coef"] * lap
                    + rng.normal(0, 0.05)
                )
                rows.append((drv, comp, float(age), lap, t))
                lap += 1
    return pd.DataFrame(
        rows, columns=["driver", "compound", "tyre_life", "lap", "lap_time_s"]
    ), truth


def test_linear_model_recovers_ground_truth(rng):
    laps, truth = synthetic_race(rng)
    m = LinearDegradationModel.fit(laps)
    assert m.reference_compound == "MEDIUM"
    for c, deg in truth["deg"].items():
        assert abs(m.deg_per_lap[c] - deg) < 0.01
        assert abs(m.compound_offset[c] - truth["offset"][c]) < 0.1
    assert abs(m.lap_coef - truth["lap_coef"]) < 0.01
    assert m.rmse < 0.1
    assert np.abs(m.predict(laps) - laps["lap_time_s"]).mean() < 0.1


def test_calibration_uses_fitted_values(rng):
    laps, truth = synthetic_race(rng)
    m = LinearDegradationModel.fit(laps)
    p = params_from_degradation(m, total_laps=50, driver="AAA", pit_loss_s=21.0)
    assert p.pit_loss_s == 21.0
    assert abs(p.compounds["SOFT"].deg_s_per_lap - 0.09) < 0.01
    assert abs(p.base_lap_time_s - (80.0 - 0.05)) < 0.1
