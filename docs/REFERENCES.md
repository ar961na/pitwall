# References

Every external data source and every method used in pitwall, with where it's used in the code.
Code comments cite these by tag, e.g. `[D1]` or `[M4]`. Tags are stable, so append new entries
rather than renumbering.

## Data sources

pitwall is an unofficial, non-commercial project and is not associated with Formula 1. F1,
FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD CHAMPIONSHIP, GRAND PRIX and related marks are trade
marks of Formula One Licensing B.V.

| Tag | Source | What we take | Access / limits | Licence | Used in |
|-----|--------|--------------|-----------------|---------|---------|
| **D1** | **OpenF1 API**: https://openf1.org · docs https://openf1.org/docs · code https://github.com/br-g/openf1 | `sessions`, `meetings`, `drivers`, `laps` (lap & sector times), `stints` (compound, tyre age), `pit` (lane duration), `race_control` (SC/VSC/red flag messages), `session_result`, `car_data` (speed, throttle, brake, gear, RPM, DRS at ≈3.7 Hz), `location` (x, y, z) | Historical data 2023→ without auth. Community tier: **3 req/s and 30 req/min** (https://openf1.org/#sponsorship). We throttle to one request per 2.1 s and cache every response on disk. | Data/code: **CC BY-NC-SA 4.0** (see the repo's `LICENSE`) | `data/openf1.py`, `data/laps.py`, `api/routes/*` |
| **D2** | **Jolpica F1 API** (Ergast-compatible successor to Ergast): https://github.com/jolpica/jolpica-f1 · base URL `https://api.jolpi.ca/ergast/f1/` | Season results (`/{year}/results.json`) and qualifying (`/{year}/qualifying.json`), 1950→ | Unauthenticated: **4 req/s burst, 500 req/h sustained** ([rate_limits.md](https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md)) | Data: **CC BY-NC-SA 4.0**, non-commercial ([TERMS.md](https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md)); code Apache-2.0 | `predict/history.py` |
| **D3** | **MultiViewer circuit API** (undocumented): `https://api.multiviewer.app/api/v1/circuits/{circuit_key}/{year}` · https://multiviewer.app | Corner numbers + XY positions, track outline, typical pit loss (`pitLoss.normal/sc/vsc`) | Same endpoint FastF1 uses for `Session.get_circuit_info()` ([fastf1/mvapi/api.py](https://github.com/theOehrly/Fast-F1/blob/master/fastf1/mvapi/api.py)). The data is hand-made, *"not highly accurate but sufficient for visualization"* ([FastF1 docs](https://docs.fastf1.dev/core.html)). New circuits can be missing (404). | Unspecified; used as FastF1 does, cached, with credit | `data/openf1.py::circuit_info`, `telemetry/corners.py`, `api/routes/strategy.py` |
| **D4** | **Ergast Developer API** (original, deprecated after 2024): http://ergast.com/mrd/ | Not called directly. D2 serves the same schema. | — | — | background |
| **D5** | **FastF1**: https://github.com/theOehrly/Fast-F1 · https://docs.fastf1.dev (MIT) | **Not used at runtime.** On 2026-10-03 F1's live-timing archive (`livetiming.formula1.com/static/…`, which FastF1 reads) answered our network with HTTP 403 from CloudFront, so pitwall reads D1 directly. Our distance integration and corner lookup follow FastF1's approach (see M2, M3). | — | MIT | design reference |

**What this means for the repo:** raw data is **never committed** (`data/` is git-ignored and
rebuilt from the cache). The GitHub Pages demo publishes a small **derived** snapshot
(`static-api/`, built in CI by `pitwall.static_demo`), shared under CC BY-NC-SA 4.0 with a
`README.txt` crediting the sources, as the licence's attribution and share-alike terms require. Derived artefacts we publish, such as predictions and charts, credit
OpenF1 and Jolpica under CC BY-NC-SA 4.0. The web UI shows the data credit in its footer.

## Methods

### Telemetry & signal processing

| Tag | Method | Reference | Used in |
|-----|--------|-----------|---------|
| **M1** | Resampling time-series onto a common distance grid (linear interpolation) | NumPy `np.interp` docs: https://numpy.org/doc/stable/reference/generated/numpy.interp.html | `telemetry/compare.py::resample_on_distance` |
| **M2** | Distance by integrating speed over time (trapezoidal rule); integration error grows with length, so we use single laps only and rescale both laps to a common length | FastF1 `Telemetry.integrate_distance` / `add_distance`: https://docs.fastf1.dev/core.html · trapezoidal rule, e.g. Burden & Faires, *Numerical Analysis*, ch. 4 | `data/openf1.py::Session.lap_telemetry`, `telemetry/compare.py::compare_laps` |
| **M3** | Corner apex → lap distance by nearest-neighbour match of XY positions | Same idea as FastF1 `CircuitInfo.add_marker_distance` (https://docs.fastf1.dev/circuit_info.html) | `telemetry/corners.py::locate_corners` |
| **M4** | Corner detection from speed minima (Task 1 stretch) | `scipy.signal.find_peaks`: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html | Task 1 |

### Tyre & pace modelling

| Tag | Method | Reference | Used in |
|-----|--------|-----------|---------|
| **M5** | Lap-time model = base + tyre degradation + fuel-mass effect (+ driver offset); linear and non-linear degradation forms | Heilmeier, Graf & Lienkamp (2018). *A Race Simulation for Strategy Decisions in Circuit Motorsports.* IEEE ITSC 2018. doi:[10.1109/ITSC.2018.8570012](https://doi.org/10.1109/ITSC.2018.8570012) | `models/tyre_deg.py`, `strategy/params.py` |
| **M6** | Ordinary least squares with fixed effects (driver dummies) | Wooldridge, J. M. (2010). *Econometric Analysis of Cross Section and Panel Data*, 2nd ed., MIT Press, ch. 10 | `models/tyre_deg.py::LinearDegradationModel` |
| **M7** | Breakpoint ("hinge"/segmented) regression for the tyre cliff | Muggeo, V. M. R. (2003). *Estimating regression models with unknown break-points.* Statistics in Medicine 22(19):3055–3071. doi:[10.1002/sim.1545](https://doi.org/10.1002/sim.1545) | Task 2 `detect_cliff` |
| **M8** | Testing for a breakpoint when it's only defined under the alternative (why a plain F-test after grid search is optimistic) | Davies, R. B. (1987). *Hypothesis testing when a nuisance parameter is present only under the alternative.* Biometrika 74(1):33–43. doi:[10.1093/biomet/74.1.33](https://doi.org/10.1093/biomet/74.1.33) | Task 2 |
| **M9** | Gradient-boosted decision trees | Ke, G. et al. (2017). *LightGBM: A Highly Efficient Gradient Boosting Decision Tree.* NeurIPS 30. https://papers.nips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html | Tasks 3, 5 |
| **M10** | Quantile regression / pinball loss for prediction intervals | Koenker, R. & Bassett, G. (1978). *Regression Quantiles.* Econometrica 46(1):33–50. doi:[10.2307/1913643](https://doi.org/10.2307/1913643) | Task 3 |
| **M11** | Huber loss (robust to outlier laps) | Huber, P. J. (1964). *Robust Estimation of a Location Parameter.* Ann. Math. Statist. 35(1):73–101. doi:[10.1214/aoms/1177703732](https://doi.org/10.1214/aoms/1177703732) | Tasks 3, 6 |
| **M12** | Mixed-effects models (stretch) | Bates, D. et al. (2015). *Fitting Linear Mixed-Effects Models Using lme4.* J. Stat. Softw. 67(1). doi:[10.18637/jss.v067.i01](https://doi.org/10.18637/jss.v067.i01) | Task 3 stretch |

### Validation

| Tag | Method | Reference | Used in |
|-----|--------|-----------|---------|
| **M13** | Time-ordered (expanding-window) cross-validation, grouped by race | Bergmeir, C. & Benítez, J. M. (2012). *On the use of cross-validation for time series predictor evaluation.* Information Sciences 191:192–213. doi:[10.1016/j.ins.2011.12.028](https://doi.org/10.1016/j.ins.2011.12.028) · Hyndman & Athanasopoulos, *Forecasting: Principles and Practice*, 3rd ed., §5.10: https://otexts.com/fpp3/tscv.html | Tasks 3, 5, 6 |
| **M14** | Data leakage (why features use `.shift(1)` and the perturbation test) | Kaufman, S., Rosset, S. & Perlich, C. (2012). *Leakage in Data Mining: Formulation, Detection, and Avoidance.* ACM TKDD 6(4). doi:[10.1145/2382577.2382579](https://doi.org/10.1145/2382577.2382579) | Task 5 tests |
| **M15** | Brier score for probabilistic forecasts | Brier, G. W. (1950). *Verification of forecasts expressed in terms of probability.* Monthly Weather Review 78(1):1–3. doi:[10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2) | Task 5 |
| **M16** | Probability calibration / reliability diagrams | Niculescu-Mizil, A. & Caruana, R. (2005). *Predicting Good Probabilities with Supervised Learning.* ICML. doi:[10.1145/1102351.1102430](https://doi.org/10.1145/1102351.1102430) | Task 5 |

### Strategy simulation

| Tag | Method | Reference | Used in |
|-----|--------|-----------|---------|
| **M17** | Lap-by-lap race simulation with Monte Carlo for safety cars, lap-time variability and pit stops | Heilmeier, Graf, Betz & Lienkamp (2020). *Application of Monte Carlo Methods to Consider Probabilistic Effects in a Race Simulation for Circuit Motorsport.* Applied Sciences 10(12):4229. doi:[10.3390/app10124229](https://doi.org/10.3390/app10124229) · reference implementation (LGPL-3.0): https://github.com/TUMFTM/race-simulation | `strategy/simulator.py` |
| **M18** | Common random numbers (variance reduction when comparing alternatives) | Law, A. M. (2015). *Simulation Modeling and Analysis*, 5th ed., McGraw-Hill, ch. 11 · Glasserman, P. (2003). *Monte Carlo Methods in Financial Engineering*, Springer, §4.2 | `strategy/simulator.py::RaceScenarios`, `optimize` |
| **M19** | Neural networks for pit-stop decisions (Task 4 stretch background) | Heilmeier, Thomaser, Graf & Betz (2020). *Virtual Strategy Engineer: Using Artificial Neural Networks for Making Race Strategy Decisions in Circuit Motorsport.* Applied Sciences 10(21):7805. doi:[10.3390/app10217805](https://doi.org/10.3390/app10217805) | Task 4 stretch |
| **M20** | Q-learning / MDPs for the reactive-policy stretch | Sutton, R. S. & Barto, A. G. (2018). *Reinforcement Learning: An Introduction*, 2nd ed., MIT Press. http://incompleteideas.net/book/the-book-2nd.html · Watkins, C. & Dayan, P. (1992). *Q-learning.* Machine Learning 8:279–292. doi:[10.1007/BF00992698](https://doi.org/10.1007/BF00992698) | Task 4 stretch |

### Ranking & deep learning

| Tag | Method | Reference | Used in |
|-----|--------|-----------|---------|
| **M21** | LambdaRank / LambdaMART (LightGBM `lambdarank`) | Burges, C. J. C. (2010). *From RankNet to LambdaRank to LambdaMART: An Overview.* Microsoft Research Tech. Report MSR-TR-2010-82 | Task 5 |
| **M22** | Listwise ranking loss (ListNet) and the Plackett–Luce model | Cao, Z. et al. (2007). *Learning to Rank: From Pairwise Approach to Listwise Approach.* ICML. doi:[10.1145/1273496.1273513](https://doi.org/10.1145/1273496.1273513) · Plackett, R. L. (1975). *The Analysis of Permutations.* JRSS C 24(2):193–202 | Task 5 stretch |
| **M23** | Permutation-invariant set models | Zaheer, M. et al. (2017). *Deep Sets.* NeurIPS · Lee, J. et al. (2019). *Set Transformer.* ICML | Task 5 stretch |
| **M24** | LSTM / GRU sequence models | Hochreiter, S. & Schmidhuber, J. (1997). *Long Short-Term Memory.* Neural Computation 9(8):1735–1780 · Cho, K. et al. (2014). *Learning Phrase Representations using RNN Encoder–Decoder.* EMNLP | Task 6 |
| **M25** | Transformer encoder | Vaswani, A. et al. (2017). *Attention Is All You Need.* NeurIPS | Tasks 5, 6 |
| **M26** | AdamW optimiser | Loshchilov, I. & Hutter, F. (2019). *Decoupled Weight Decay Regularization.* ICLR | Task 6 |

## Software

FastAPI (https://fastapi.tiangolo.com), pydantic (https://docs.pydantic.dev), pandas
(https://pandas.pydata.org), NumPy, SciPy, scikit-learn, LightGBM
(https://lightgbm.readthedocs.io), PyTorch with the MPS backend
(https://pytorch.org/docs/stable/notes/mps.html), MLflow (https://mlflow.org), httpx,
React (https://react.dev), Vite (https://vite.dev), Recharts (https://recharts.org), Vitest,
micromamba / conda-forge, Docker.
