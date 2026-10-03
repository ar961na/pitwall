from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import HTTPException

from pitwall.data.openf1 import Session, load_session


def get_session(session_key: int) -> Session:
    try:
        return load_session(session_key)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # network / upstream data problems
        raise HTTPException(502, f"Could not load session {session_key}: {e}") from e


def columns(df: pd.DataFrame, decimals: int = 4) -> dict[str, list]:
    """Column-oriented JSON (compact for long series), NaN -> null."""
    out = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_float_dtype(s):
            s = s.round(decimals)
        out[col] = [None if (isinstance(v, float) and np.isnan(v)) else v for v in s.tolist()]
    return out


def records(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")
