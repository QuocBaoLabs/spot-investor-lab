from __future__ import annotations

import pandas as pd


def premium_or_discount(df: pd.DataFrame, lookback: int = 100) -> str:
    recent = df.tail(lookback)
    high = recent["high"].max()
    low = recent["low"].min()
    mid = (high + low) / 2
    close = df["close"].iloc[-1]
    if close < mid:
        return "discount"
    if close > mid:
        return "premium"
    return "equilibrium"
