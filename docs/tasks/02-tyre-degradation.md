# Task 2: Fuel correction and cliff detection

**File:** `backend/src/pitwall/models/tyre_deg.py` → `detect_cliff()`, plus a notebook study
**Check:** `pytest -m task tests/tasks/test_task2_cliff.py`
**Feeds:** `strategy/calibrate.py`, which currently takes cliffs from defaults.

## Goal

The baseline `LinearDegradationModel` says "SOFT loses 0.057 s/lap", forever. Real tyres hold up
and then fall off a **cliff**. Find where.

## Part A: look at the data first (notebook)

```python
from pitwall.data import openf1
from pitwall.data.laps import race_laps, green_flag_laps
from pitwall.models.tyre_deg import LinearDegradationModel

s = openf1.load_session(openf1.find_session(2025, "zandvoort"))
g = green_flag_laps(race_laps(s))
m = LinearDegradationModel.fit(g)
m.compound_offset   # HARD faster than MEDIUM?! why?
```

Look at that: at Zandvoort 2025 the baseline says HARD is 0.18 s/lap *faster* than MEDIUM on fresh
tyres. Before reading on, write down two hypotheses for why.

<details><summary>Discussion</summary>

`lap_coef` mixes **fuel burn** with **track evolution** (rubber goes down). A commonly quoted
rule of thumb is a few hundredths of a second per kg of fuel. Find a source you trust, cite it
in your notebook, and check it against the data.

Most teams run HARD at the end of the race, on low fuel and a rubbered-in track. If the lap term
doesn't capture those effects perfectly (they aren't linear!), the leftover gets absorbed by the
compound offset. That's confounding. Ways out: a fixed physical fuel correction
(`lap_time - k_fuel * fuel_kg`, with `k_fuel` from your cited source), interactions, or pooling
many races (Task 3).
</details>

Try: fix the fuel effect physically (start fuel → ~0 kg at the flag, linear burn), refit, and
compare the offsets. **Cite the start-fuel number:** the FIA Formula 1 Technical Regulations set
the race-fuel limit, and the 2026 power-unit rules changed how fuel/energy is limited. Look up
the regulation for the season you analyse (https://www.fia.com/regulation/category/110) and
reference the article in your notebook, the way `docs/REFERENCES.md` does.

## Part B: `detect_cliff(tyre_life, lap_time_s, min_laps=5)`

Return the tyre age where degradation stops being linear, or `None`.

## Concept refresher

- **Piecewise-linear ("hinge") regression:** `t = a + b·age + c·max(age − k, 0)`. For a fixed
  breakpoint `k` it's ordinary least squares, so you can grid-search `k`.
- **Model selection:** a hinge always fits at least as well as a line, because it has one more
  parameter. You need a test that asks whether the improvement is bigger than chance: an
  F-test on nested models, or compare AIC/BIC.
- **Multiple comparisons:** searching over many `k` values and keeping the best inflates false
  positives. Use a strict threshold.

<details><summary>Hint 1</summary>

`X0 = [1, age]`, `X1 = [1, age, max(age-k, 0)]`; `np.linalg.lstsq` both and compare SSEs.
Only consider `k` with ≥ `min_laps` points on each side, and only accept `c > 0` (a cliff makes
cars *slower*).
</details>

<details><summary>Hint 2</summary>

F = ((SSE0 − SSE1) / 1) / (SSE1 / (n − 3)); p = `scipy.stats.f.sf(F, 1, n - 3)`. A threshold of
around p < 0.001 keeps the false-positive test happy.
</details>

## Stretch

1. The test lets your estimate be up to 3 laps late, because smooth cliffs bias hinge fits late.
   Fit `c·max(age − k, 0)^p` with `scipy.optimize.curve_fit` and see whether the bias disappears.
2. Run `detect_cliff` over every stint of a season and plot the cliff-age distribution per
   compound. Feed the median into `params_from_degradation` (replace the defaults).
3. **Pit loss from data:** OpenF1 `pit` has `lane_duration`, and MultiViewer has `pitLoss`.
   Estimate pit loss yourself as (in-lap + out-lap) − 2 × the median green lap. Do they agree?

## Interview questions

- How do you separate fuel effect from tyre degradation from track evolution?
- Why is a hinge model with a grid-searched breakpoint not a standard OLS for inference?

## References

Tags point to [docs/REFERENCES.md](../REFERENCES.md).

- [D1] OpenF1 laps/stints/pit; [D3] MultiViewer `pitLoss`
- [M5] Heilmeier et al. 2018 (lap-time model with tyre + fuel terms), [M6] fixed-effects OLS, [M7] Muggeo 2003 (breakpoint regression), [M8] Davies 1987 (testing a breakpoint)
