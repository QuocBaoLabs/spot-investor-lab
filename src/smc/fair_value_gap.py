from __future__ import annotations

import pandas as pd


def detect_fvg(df: pd.DataFrame) -> dict:
    if len(df) < 3:
        return {"fvg_detected": False, "direction": "none"}
    a = df.iloc[-3]
    c = df.iloc[-1]
    bullish = c["low"] > a["high"]
    bearish = c["high"] < a["low"]
    return {
        "fvg_detected": bool(bullish or bearish),
        "direction": "bullish" if bullish else "bearish" if bearish else "none",
    }
