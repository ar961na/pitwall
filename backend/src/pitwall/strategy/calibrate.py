"""Bridge: fitted tyre model (from real race data) -> simulator parameters.

Tyre terms come from LinearDegradationModel fitted on OpenF1 laps [D1]; the API route adds the
circuit's typical pit loss (normal and under SC) from MultiViewer's `pitLoss` field [D3].
"""

import numpy as np

from pitwall.models.tyre_deg import LinearDegradationModel
from pitwall.strategy.params import DEFAULT_COMPOUNDS, CompoundParams, RaceParams


def params_from_degradation(
    model: LinearDegradationModel,
    total_laps: int,
    driver: str | None = None,
    cliffs: dict[str, int] | None = None,
    pace_deg: dict[str, float] | None = None,
    **overrides,
) -> RaceParams:
    """Simulator params for `driver` (or the median car) from a fitted degradation model.

    Compounds that weren't raced (or fitted to a nonsensical negative degradation) fall back
    to the defaults, shifted onto this race's pace scale. If `pace_deg` (degradation per lap from
    the multi-race pace model) is given, it replaces the default degradation in that fallback.
    Only degradation is taken from it: the pace model barely separates compounds' fresh-tyre
    pace (offsets within 0.15 s at Zandvoort 2025, Monza 2026, Interlagos 2026), so its offsets
    are not used. `cliffs` (from `cliff_ages`) replaces the default cliff age where detected.
    """
    offsets = model.driver_offset
    driver_offset = offsets[driver] if driver else float(np.median(list(offsets.values())))
    ref = model.reference_compound
    ref_default = DEFAULT_COMPOUNDS[ref].offset_s

    compounds: dict[str, CompoundParams] = {}
    source: dict[str, str] = {}
    for name, default in DEFAULT_COMPOUNDS.items():
        deg = model.deg_per_lap.get(name)
        fallback_deg = (pace_deg or {}).get(name)
        if deg is not None and deg > 0:
            update = {"offset_s": model.compound_offset[name], "deg_s_per_lap": deg}
            source[name] = "race"
        elif fallback_deg is not None and fallback_deg > 0:
            update = {"offset_s": default.offset_s - ref_default, "deg_s_per_lap": fallback_deg}
            source[name] = "pace_model"
        else:
            update = {"offset_s": default.offset_s - ref_default}
            source[name] = "default"
        compounds[name] = default.model_copy(update=update)

    for name, age in (cliffs or {}).items():
        compounds[name] = compounds[name].model_copy(update={"cliff_age": age})

    return RaceParams(
        total_laps=total_laps,
        # model uses 1-based lap numbers, the simulator 0-based lap index
        base_lap_time_s=driver_offset + model.lap_coef,
        lap_coef_s=model.lap_coef,
        compounds=compounds,
        tyre_source=source,
        **overrides,
    )
