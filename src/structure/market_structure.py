from __future__ import annotations

import pandas as pd

from src.structure.swing_detector import add_swing_points


def classify_structure(df: pd.DataFrame) -> str:
    enriched = add_swing_points(df)
    highs = enriched[enriched["swing_high"]]["high"].tail(2).to_list()
    lows = enriched[enriched["swing_low"]]["low"].tail(2).to_list()
    if len(highs) >= 2 and len(lows) >= 2:
        if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
            return "uptrend"
        if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
            return "downtrend"
    if "ema200" in df and df["close"].iloc[-1] > df["ema200"].iloc[-1]:
        return "bullish_range"
    if "ema200" in df and df["close"].iloc[-1] < df["ema200"].iloc[-1]:
        return "bearish_range"
    return "range"
