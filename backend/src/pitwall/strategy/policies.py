"""Reactive strategies.

`simulate()` replays a *fixed* plan: the car pits on lap 20 whether or not a safety car came
out on lap 17. Real strategists react. `simulate_reactive` is a simple policy that does, so the
value of reacting can be measured.

References: common random numbers [M18]; for the RL stretch see Sutton & Barto [M20] and the
neural "virtual strategy engineer" of Heilmeier et al. (2020) [M19]. docs/REFERENCES.md.
"""

import numpy as np

from pitwall.strategy.params import RaceParams
from pitwall.strategy.simulator import RaceScenarios, SimResult, Strategy


def simulate_reactive(
    plan: Strategy,
    params: RaceParams,
    scenarios: RaceScenarios,
    window: int = 6,
) -> SimResult:
    """Follow `plan`, but pit early when a safety car is out shortly before a planned stop.

    If a safety car is out on any of the `window` laps before a planned stop (and not on the
    stop lap itself, where the plan already gets the cheap stop), the car pits on the first
    such lap and the next stint grows by the laps saved. Uses the same `scenarios` as
    `simulate`, so the two can be compared scenario by scenario [M18].
    """
    sc = scenarios.safety_car
    n_sims, n_laps = sc.shape
    lap_no = np.arange(1, n_laps + 1)

    pits = np.empty((n_sims, plan.n_stops), dtype=int)
    prev_pit = np.zeros(n_sims, dtype=int)
    for j, planned in enumerate(plan.pit_laps):
        candidates = np.arange(max(planned - window, 1), planned)
        usable = sc[:, candidates - 1] & (candidates[None, :] > prev_pit[:, None])
        react = usable.any(axis=1) & ~sc[:, planned - 1]
        pits[:, j] = np.where(react, candidates[usable.argmax(axis=1)], planned)
        prev_pit = pits[:, j]

    # tyre age and stint index per (sim, lap) from each sim's actual pit laps
    done = pits[:, None, :] < lap_no[None, :, None]
    stint_idx = done.sum(axis=2)
    last_pit = np.where(done, pits[:, None, :], 0).max(axis=2)
    age = (lap_no[None, :] - last_pit).astype(float)

    clean = params.base_lap_time_s + params.lap_coef_s * np.arange(n_laps, dtype=float)
    laps = np.broadcast_to(clean, (n_sims, n_laps)).copy()
    for j, stint in enumerate(plan.stints):
        mask = stint_idx == j
        laps[mask] += params.compounds[stint.compound].tyre_penalty(age[mask])

    laps = np.where(sc, params.base_lap_time_s * params.sc_lap_factor, laps + scenarios.noise)
    under_sc = np.take_along_axis(sc, pits - 1, axis=1)
    pit_cost = np.where(under_sc, params.pit_loss_s * params.sc_pit_loss_factor, params.pit_loss_s)
    return SimResult(plan, laps.sum(axis=1) + pit_cost.sum(axis=1))
