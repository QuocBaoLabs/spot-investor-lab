from __future__ import annotations

import pandas as pd


def detect_liquidity(df: pd.DataFrame, tolerance: float = 0.0015) -> dict:
    recent = df.tail(80)
    highs = recent["high"]
    lows = recent["low"]
    equal_highs = highs.rolling(5).max().diff().abs().lt(highs * tolerance).sum() > 2
    equal_lows = lows.rolling(5).min().diff().abs().lt(lows * tolerance).sum() > 2
    prev_high = highs.iloc[:-1].max()
    prev_low = lows.iloc[:-1].min()
    last = recent.iloc[-1]
    sweep_high = bool(last["high"] > prev_high and last["close"] < prev_high)
    sweep_low = bool(last["low"] < prev_low and last["close"] > prev_low)
    return {
        "equal_highs": bool(equal_highs),
        "equal_lows": bool(equal_lows),
        "sweep_high": sweep_high,
        "sweep_low": sweep_low,
        "liquidity_sweep": sweep_high or sweep_low,
    }
