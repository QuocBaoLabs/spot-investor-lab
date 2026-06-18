from __future__ import annotations

import pandas as pd

from src.wyckoff.spring_upthrust import detect_spring_upthrust


def detect_phase(df: pd.DataFrame) -> dict:
    recent = df.tail(100)
    range_pct = (recent["high"].max() - recent["low"].min()) / recent["close"].iloc[-1]
    slope = recent["close"].tail(20).mean() - recent["close"].head(20).mean()
    spring_upthrust = detect_spring_upthrust(df)

    if spring_upthrust["spring"]:
        phase = "accumulation"
    elif spring_upthrust["upthrust"]:
        phase = "distribution"
    elif range_pct < 0.08 and slope > 0:
        phase = "re-accumulation"
    elif range_pct < 0.08 and slope < 0:
        phase = "re-distribution"
    else:
        phase = "unclear"

    return {"phase": phase, **spring_upthrust}
