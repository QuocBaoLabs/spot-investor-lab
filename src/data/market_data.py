from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def load_ohlcv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = set(OHLCV_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    return df[OHLCV_COLUMNS].reset_index(drop=True)


def generate_sample_ohlcv(rows: int = 1200, start_price: float = 65000.0) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2025-01-01", periods=rows, freq="15min", tz="UTC")
    drift = np.sin(np.linspace(0, 18, rows)) * 0.001
    noise = rng.normal(0, 0.0025, rows)
    returns = drift + noise
    close = start_price * np.cumprod(1 + returns)
    open_ = np.r_[start_price, close[:-1]]
    spread = close * rng.uniform(0.001, 0.006, rows)
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volume = rng.integers(800, 4000, rows).astype(float)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


def resample_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rule_map = {"M15": "15min", "H1": "1h", "H4": "4h", "D1": "1D"}
    rule = rule_map.get(timeframe, timeframe)
    indexed = df.set_index("timestamp")
    out = indexed.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna().reset_index()


def load_multitimeframe_data(base_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "M15": base_df.copy(),
        "H1": resample_ohlcv(base_df, "H1"),
        "H4": resample_ohlcv(base_df, "H4"),
        "D1": resample_ohlcv(base_df, "D1"),
    }
