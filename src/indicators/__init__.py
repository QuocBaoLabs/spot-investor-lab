from __future__ import annotations

import pandas as pd

from src.indicators.atr import atr
from src.indicators.ema import ema
from src.indicators.macd import macd
from src.indicators.parabolic_sar import parabolic_sar
from src.indicators.rsi import rsi


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema50"] = ema(out["close"], 50)
    out["ema200"] = ema(out["close"], 200)
    out = pd.concat([out, macd(out["close"])], axis=1)
    out["rsi"] = rsi(out["close"])
    out["atr"] = atr(out)
    out["sar"] = parabolic_sar(out)
    out["volume_ma"] = out["volume"].rolling(20).mean()
    return out
