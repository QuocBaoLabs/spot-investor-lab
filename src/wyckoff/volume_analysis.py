from __future__ import annotations

import pandas as pd


def volume_confirmation(df: pd.DataFrame) -> dict:
    avg = df["volume"].rolling(20).mean().iloc[-1]
    last = df["volume"].iloc[-1]
    ratio = float(last / avg) if avg and avg == avg else 1.0
    return {"volume_ratio": ratio, "volume_confirmation": ratio >= 1.2}
