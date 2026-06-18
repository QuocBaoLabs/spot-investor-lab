from __future__ import annotations

import pandas as pd


def detect_order_block(df: pd.DataFrame) -> dict:
    recent = df.tail(20)
    body = (recent["close"] - recent["open"]).abs()
    avg_body = body.rolling(10).mean()
    impulse = body > avg_body * 1.6
    if not impulse.any():
        return {"order_block_detected": False, "direction": "none", "zone": None}
    idx = impulse[impulse].index[-1]
    candle = recent.loc[idx]
    direction = "bullish" if candle["close"] > candle["open"] else "bearish"
    return {
        "order_block_detected": True,
        "direction": direction,
        "zone": [float(candle["low"]), float(candle["high"])],
    }
