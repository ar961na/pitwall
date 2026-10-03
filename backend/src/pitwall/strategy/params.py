"""Race and tyre parameters that drive the simulator (also the API schema).

The DEFAULTS below are illustrative round numbers chosen by us so the simulator runs without
data — they are NOT measured. `strategy/calibrate.py` replaces tyre and pit-loss values with
ones fitted to a real race (OpenF1 [D1] laps + MultiViewer [D3] pit loss).
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field


class CompoundParams(BaseModel):
    offset_s: float = Field(description="Pace vs the reference compound on fresh tyres (s/lap)")
    deg_s_per_lap: float = Field(description="Linear degradation (s lost per lap of tyre age)")
    cliff_age: int = Field(description="Tyre age where the cliff starts")
    cliff_s_per_lap2: float = Field(0.02, description="Quadratic penalty after the cliff")

    def tyre_penalty(self, age: np.ndarray) -> np.ndarray:
        over = np.maximum(age - self.cliff_age, 0)
        return self.offset_s + self.deg_s_per_lap * age + self.cliff_s_per_lap2 * over**2


DEFAULT_COMPOUNDS: dict[str, CompoundParams] = {
    "SOFT": CompoundParams(offset_s=-0.6, deg_s_per_lap=0.09, cliff_age=16, cliff_s_per_lap2=0.03),
    "MEDIUM": CompoundParams(
        offset_s=0.0, deg_s_per_lap=0.055, cliff_age=26, cliff_s_per_lap2=0.02
    ),
    "HARD": CompoundParams(
        offset_s=0.45, deg_s_per_lap=0.035, cliff_age=38, cliff_s_per_lap2=0.015
    ),
}


class RaceParams(BaseModel):
    total_laps: int = Field(57, ge=10, le=90)
    base_lap_time_s: float = Field(92.0, description="Reference compound, fresh tyre, lap 1 fuel")
    lap_coef_s: float = Field(-0.06, description="Lap-time change per race lap (fuel burn + track)")
    pit_loss_s: float = Field(22.0, description="Time lost driving through the pit lane + stop")
    sc_prob_per_lap: float = Field(0.015, ge=0, le=0.3, description="Chance a safety car starts")
    sc_min_laps: int = 3
    sc_max_laps: int = 5
    sc_lap_factor: float = Field(1.35, description="SC lap time = base * factor")
    sc_pit_loss_factor: float = Field(0.45, description="Pitting under SC costs this fraction")
    lap_noise_s: float = Field(0.25, ge=0, description="Std of random lap-to-lap variation")
    compounds: dict[str, CompoundParams] = Field(default_factory=lambda: dict(DEFAULT_COMPOUNDS))
