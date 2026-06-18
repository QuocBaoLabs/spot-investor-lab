from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class MockExchangeClient:
    data: pd.DataFrame

    def fetch_ohlcv(self, symbol: str, timeframe: str = "15m", limit: int = 500) -> pd.DataFrame:
        return self.data.tail(limit).copy()

    def create_order(self, *args, **kwargs) -> dict:
        return {"status": "paper_only", "args": args, "kwargs": kwargs}


class LiveTradingDisabledError(RuntimeError):
    pass


class LiveExchangeClient:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def create_order(self, *args, **kwargs) -> dict:
        if not self.enabled:
            raise LiveTradingDisabledError("Live trading is disabled. Set LIVE_TRADING_ENABLED=true explicitly.")
        raise NotImplementedError("Connect ccxt/binance client here after manual review.")
