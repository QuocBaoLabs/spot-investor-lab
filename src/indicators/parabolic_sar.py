from __future__ import annotations

import pandas as pd


def parabolic_sar(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    if len(df) == 0:
        return pd.Series(dtype=float)

    sar = [low[0]]
    uptrend = True
    ep = high[0]
    af = step

    for i in range(1, len(df)):
        prev_sar = sar[-1]
        next_sar = prev_sar + af * (ep - prev_sar)
        if uptrend:
            next_sar = min(next_sar, low[i - 1], low[i])
            if low[i] < next_sar:
                uptrend = False
                next_sar = ep
                ep = low[i]
                af = step
            elif high[i] > ep:
                ep = high[i]
                af = min(af + step, max_step)
        else:
            next_sar = max(next_sar, high[i - 1], high[i])
            if high[i] > next_sar:
                uptrend = True
                next_sar = ep
                ep = high[i]
                af = step
            elif low[i] < ep:
                ep = low[i]
                af = min(af + step, max_step)
        sar.append(next_sar)

    return pd.Series(sar, index=df.index)
