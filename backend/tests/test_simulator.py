import numpy as np
import pytest

from pitwall.strategy.params import CompoundParams, RaceParams
from pitwall.strategy.simulator import (
    RaceScenarios,
    Stint,
    Strategy,
    clean_lap_times,
    enumerate_strategies,
    expected_time_no_sc,
    optimize,
    simulate,
)


def flat_params(**kw) -> RaceParams:
    """No degradation, no noise, no SC, so totals are easy to check by hand."""
    zero = CompoundParams(offset_s=0, deg_s_per_lap=0, cliff_age=99, cliff_s_per_lap2=0)
    base = dict(
        total_laps=20,
        base_lap_time_s=90,
        lap_coef_s=0,
        sc_prob_per_lap=0,
        lap_noise_s=0,
        compounds={"SOFT": zero, "HARD": zero},
    )
    return RaceParams(**{**base, **kw})


def strat(*stints) -> Strategy:
    return Strategy(tuple(Stint(c, n) for c, n in stints))


def test_validate():
    p = flat_params()
    strat(("SOFT", 10), ("HARD", 10)).validate(p)
    with pytest.raises(ValueError, match="add up"):
        strat(("SOFT", 10), ("HARD", 9)).validate(p)
    with pytest.raises(ValueError, match="two different"):
        strat(("SOFT", 10), ("SOFT", 10)).validate(p)


def test_pit_laps_and_label():
    s = strat(("SOFT", 12), ("HARD", 20), ("SOFT", 8))
    assert s.pit_laps == [12, 32]
    assert s.n_stops == 2
    assert s.label == "S12 → H20 → S8"


def test_clean_lap_times_tyre_age_resets_after_stop():
    soft = CompoundParams(offset_s=0, deg_s_per_lap=0.1, cliff_age=99)
    p = flat_params(compounds={"SOFT": soft, "HARD": soft})
    laps = clean_lap_times(strat(("SOFT", 10), ("HARD", 10)), p)
    assert np.isclose(laps[0], 90.1) and np.isclose(laps[9], 91.0)
    assert np.isclose(laps[10], 90.1)  # fresh tyre


def test_deterministic_sim_equals_expected_time():
    p = flat_params(pit_loss_s=20)
    s = strat(("SOFT", 10), ("HARD", 10))
    res = simulate(s, p, RaceScenarios.sample(p, n_sims=50))
    assert np.allclose(res.totals, expected_time_no_sc(s, p))
    assert np.isclose(res.mean, 20 * 90 + 20)


def test_pitting_under_safety_car_is_cheaper():
    p = flat_params(pit_loss_s=20, sc_pit_loss_factor=0.5)
    s = strat(("SOFT", 10), ("HARD", 10))
    sc = np.zeros((1, 20), dtype=bool)
    sc[0, 9] = True  # SC on the in-lap (lap 10)
    res = simulate(s, p, RaceScenarios(safety_car=sc, noise=np.zeros((1, 20))))
    assert np.isclose(res.totals[0], 19 * 90 + 90 * p.sc_lap_factor + 10)


def test_safety_car_durations_respected():
    p = flat_params(total_laps=60, sc_prob_per_lap=0.05, sc_min_laps=3, sc_max_laps=5)
    sc = RaceScenarios.sample(p, n_sims=500, seed=1).safety_car
    assert not sc[:, 0].any()
    for row in sc[:100]:
        edges = np.flatnonzero(np.diff(np.r_[0, row.astype(int), 0]))
        starts, ends = edges[::2], edges[1::2]
        for start, end in zip(starts, ends, strict=True):
            if end < len(row):  # an SC can be cut short by the chequered flag
                assert end - start >= 3


def test_common_random_numbers():
    p = RaceParams()
    a = RaceScenarios.sample(p, 100, seed=7)
    b = RaceScenarios.sample(p, 100, seed=7)
    assert (a.safety_car == b.safety_car).all() and np.allclose(a.noise, b.noise)


def test_enumerate_strategies_all_legal():
    p = RaceParams(total_laps=40)
    strats = enumerate_strategies(p, max_stops=2, min_stint=8)
    assert len(strats) > 100
    for s in strats:
        s.validate(p)
        assert min(st.laps for st in s.stints) >= 8


def test_optimizer_prefers_fewer_stops_when_pitting_is_expensive():
    p = RaceParams(pit_loss_s=60, sc_prob_per_lap=0)
    best = optimize(p, n_sims=200)[0]
    assert best["n_stops"] == 1


def test_optimizer_prefers_more_stops_when_pitting_is_free():
    p = RaceParams(pit_loss_s=0.5, sc_prob_per_lap=0)
    best = optimize(p, n_sims=200)[0]
    assert best["n_stops"] == 2
    assert 0.99 <= sum(r["p_best"] for r in optimize(p, n_sims=200)) <= 1.01
