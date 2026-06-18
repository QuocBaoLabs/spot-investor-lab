from __future__ import annotations

import pandas as pd

from src.structure.swing_detector import add_swing_points


def detect_bos_choch(df: pd.DataFrame) -> dict:
    enriched = add_swing_points(df)
    highs = enriched[enriched["swing_high"]]["high"].tail(2).to_list()
    lows = enriched[enriched["swing_low"]]["low"].tail(2).to_list()
    close = float(df["close"].iloc[-1])
    bos = False
    choch = False
    direction = "none"

    if highs and close > highs[-1]:
        bos = True
        direction = "bullish"
    elif lows and close < lows[-1]:
        bos = True
        direction = "bearish"

    if len(highs) >= 2 and len(lows) >= 2:
        was_down = highs[-1] < highs[-2] and lows[-1] < lows[-2]
        was_up = highs[-1] > highs[-2] and lows[-1] > lows[-2]
        choch = (was_down and direction == "bullish") or (was_up and direction == "bearish")

    return {"bos": bos, "choch": choch, "direction": direction}
