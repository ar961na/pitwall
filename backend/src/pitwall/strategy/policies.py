"""Reactive strategies — TASK 4 (docs/tasks/04-reactive-strategy.md).

`simulate()` replays a *fixed* plan: the car pits on lap 20 whether or not a safety car came
out on lap 17. Real strategists react. Here you write a policy that does too, then measure
how much reacting is worth.

References: common random numbers [M18]; for the RL stretch see Sutton & Barto [M20] and the
neural "virtual strategy engineer" of Heilmeier et al. (2020) [M19]. docs/REFERENCES.md.
"""

from __future__ import annotations

from pitwall.strategy.params import RaceParams
from pitwall.strategy.simulator import RaceScenarios, SimResult, Strategy


def simulate_reactive(
    plan: Strategy,
    params: RaceParams,
    scenarios: RaceScenarios,
    window: int = 6,
) -> SimResult:
    """Follow `plan`, but if a safety car is out within `window` laps BEFORE a planned stop,
    pit now (cheap stop) and shift the remaining stints accordingly.

    Must use the same `scenarios` as `simulate` so the comparison is fair.
    """
    raise NotImplementedError("TASK 4 — see docs/tasks/04-reactive-strategy.md")
