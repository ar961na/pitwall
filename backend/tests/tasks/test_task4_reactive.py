"""TASK 4 acceptance tests. Run:  pytest -m task tests/tasks/test_task4_reactive.py"""

import numpy as np
import pytest

from pitwall.strategy.params import RaceParams
from pitwall.strategy.policies import simulate_reactive
from pitwall.strategy.simulator import RaceScenarios, Stint, Strategy, simulate

pytestmark = pytest.mark.task

PLAN = Strategy((Stint("MEDIUM", 25), Stint("HARD", 32)))


def test_identical_without_safety_cars():
    p = RaceParams(sc_prob_per_lap=0.0)
    sc = RaceScenarios.sample(p, 300)
    assert np.allclose(simulate_reactive(PLAN, p, sc).totals, simulate(PLAN, p, sc).totals)


def test_reacting_helps_on_average_when_safety_cars_are_common():
    p = RaceParams(sc_prob_per_lap=0.04)
    sc = RaceScenarios.sample(p, 3000, seed=3)
    fixed, reactive = simulate(PLAN, p, sc), simulate_reactive(PLAN, p, sc)
    assert reactive.mean < fixed.mean - 1.0


def test_pits_on_sc_lap_inside_window():
    p = RaceParams(sc_prob_per_lap=0.0, lap_noise_s=0.0)
    sc = RaceScenarios.sample(p, 1)
    sc.safety_car[0, 19:23] = True  # SC laps 20-23; the plan says pit at the end of lap 25 (green)
    res = simulate_reactive(PLAN, p, sc, window=6)
    # pitting on lap 20 under SC costs pit_loss * sc_pit_loss_factor instead of the full pit_loss,
    # which outweighs running the hard tyre 5 laps longer
    assert res.totals[0] < simulate(PLAN, p, sc).totals[0]
