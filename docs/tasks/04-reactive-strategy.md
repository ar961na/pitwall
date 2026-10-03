# Task 4: React to safety cars

**File:** `backend/src/pitwall/strategy/policies.py` → `simulate_reactive()`
**Check:** `pytest -m task tests/tasks/test_task4_reactive.py`

## Goal

`simulate()` follows a fixed plan. Real strategists **box under the safety car**, because a stop
costs ~45–65% of the usual pit loss. Write a policy: *if a safety car is out within `window`
laps before a planned stop, pit now instead, and lengthen the next stint by the same number of
laps.* Then measure what reacting is worth.

## Read first

`strategy/simulator.py` → `RaceScenarios` (shared random draws), `simulate`, `clean_lap_times`.
Note how `simulate` is fully vectorised over simulations. Your policy branches per simulation, so
a Python loop over sims is fine to start with (3000 × 57 is small).

## Concept refresher

- **Common random numbers (CRN):** evaluate fixed and reactive on the *same* `scenarios`. The
  difference per scenario then has much lower variance than comparing two independent samples.
  Compute `(fixed.totals - reactive.totals).std()` vs the std of each one alone to see it.
- **Policy vs plan:** a plan is a fixed sequence; a policy maps state → action. That's the step
  from Monte Carlo evaluation toward reinforcement learning.

<details><summary>Hint 1</summary>

Per simulation: copy the stint lengths into a list. For each planned stop `P` (1-based lap), look
for the earliest lap `L` in `[P - window, P - 1]` with `sc[i, L - 1]`. If the car isn't already
pitting under SC on lap `P`, shift: `lengths[j] -= P - L; lengths[j + 1] += P - L`.
</details>

<details><summary>Hint 2</summary>

Build a `Strategy` from the adjusted lengths and reuse `clean_lap_times`, then apply the SC lap
times and pit costs exactly like `simulate` does (copy those 6 lines, or refactor `simulate` so
both share a helper. Bonus points for the refactor, with tests still green).
</details>

## Stretch

1. Sweep `window` from 0 to 15 and plot the mean gain. Where's the optimum, and why does a large
   window hurt?
2. Expose it in the API (`reactive: bool` in `OptimizeRequest`) and show "fixed vs reactive" in
   the Strategy page.
3. **RL:** state = (lap, tyre age, compound, SC on?), action = pit/stay. Tabular Q-learning or
   policy iteration on this small MDP. Compare with your hand-written policy.
4. **Traffic:** add a time penalty when rejoining within 1.5 s of a slower car. That needs a
   multi-car simulation, which is a big step up and a good "next project" talking point.

## Interview questions

- Why does CRN reduce variance, and when does it not help?
- What's the downside of always pitting under SC? (Hint: everyone else does too: track position.)

## References

Tags point to [docs/REFERENCES.md](../REFERENCES.md).

- [M17] Monte Carlo race simulation (Heilmeier et al. 2020, TUMFTM/race-simulation), [M18] common random numbers (Law 2015 ch. 11; Glasserman 2003 §4.2), [M19] Virtual Strategy Engineer (Heilmeier et al. 2020), [M20] Sutton & Barto 2018; Watkins & Dayan 1992
