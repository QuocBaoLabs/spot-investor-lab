from __future__ import annotations

import pandas as pd


def long_stop_loss(df: pd.DataFrame, atr_buffer: float = 0.5) -> float:
    swing_low = df["low"].tail(20).min()
    atr = df["atr"].iloc[-1] if "atr" in df else 0
    return float(swing_low - atr * atr_buffer)


def short_stop_loss(df: pd.DataFrame, atr_buffer: float = 0.5) -> float:
    swing_high = df["high"].tail(20).max()
    atr = df["atr"].iloc[-1] if "atr" in df else 0
    return float(swing_high + atr * atr_buffer)
