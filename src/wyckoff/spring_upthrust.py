from __future__ import annotations

import pandas as pd

from src.wyckoff.volume_analysis import volume_confirmation


def detect_spring_upthrust(df: pd.DataFrame) -> dict:
    recent = df.tail(60)
    last = recent.iloc[-1]
    low_range = recent["low"].iloc[:-1].min()
    high_range = recent["high"].iloc[:-1].max()
    vol = volume_confirmation(df)
    spring = bool(last["low"] < low_range and last["close"] > low_range and vol["volume_confirmation"])
    upthrust = bool(last["high"] > high_range and last["close"] < high_range and vol["volume_confirmation"])
    return {"spring": spring, "upthrust": upthrust, **vol}
