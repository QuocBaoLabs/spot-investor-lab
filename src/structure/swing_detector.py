from __future__ import annotations

import pandas as pd


def add_swing_points(df: pd.DataFrame, lookback: int = 3) -> pd.DataFrame:
    out = df.copy()
    out["swing_high"] = False
    out["swing_low"] = False
    for i in range(lookback, len(out) - lookback):
        window = out.iloc[i - lookback : i + lookback + 1]
        out.loc[out.index[i], "swing_high"] = out.iloc[i]["high"] == window["high"].max()
        out.loc[out.index[i], "swing_low"] = out.iloc[i]["low"] == window["low"].min()
    return out


def last_swing_high(df: pd.DataFrame) -> float | None:
    swings = df[df.get("swing_high", False)]
    return None if swings.empty else float(swings.iloc[-1]["high"])


def last_swing_low(df: pd.DataFrame) -> float | None:
    swings = df[df.get("swing_low", False)]
    return None if swings.empty else float(swings.iloc[-1]["low"])
