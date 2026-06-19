from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests


BINANCE_BASE_URL = "https://api.binance.com"
WEIGHT_LIMIT_PER_MINUTE = 1200
WEIGHT_SLOWDOWN_THRESHOLD = 0.65
MIN_REQUEST_INTERVAL_SECONDS = 0.25


class BinanceRateLimitBannedError(RuntimeError):
    """Raised when Binance temporarily bans this IP for sending too many requests (HTTP 418)."""


class _RateLimitState:
    """Module-level (shared across every BinanceSpotClient instance) pacing/ban state.

    A fresh BinanceSpotClient() is created on every call site, so this state must live
    outside any single instance to actually throttle requests across symbols/calls.
    """

    last_request_at: float = 0.0
    banned_until: float = 0.0


_rate_limit_state = _RateLimitState()


@dataclass(frozen=True)
class BinanceSymbol:
    symbol: str
    base_asset: str
    quote_asset: str
    quote_volume: float = 0.0


class BinanceSpotClient:
    def __init__(self, base_url: str = BINANCE_BASE_URL, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_usdt_spot_symbols(self) -> list[BinanceSymbol]:
        info = self._get("/api/v3/exchangeInfo")
        tickers = {item["symbol"]: item for item in self._get("/api/v3/ticker/24hr")}
        symbols: list[BinanceSymbol] = []

        for item in info["symbols"]:
            symbol = item["symbol"]
            base = item["baseAsset"]
            quote = item["quoteAsset"]
            if item["status"] != "TRADING" or quote != "USDT":
                continue
            if not item.get("isSpotTradingAllowed", True):
                continue
            if self._looks_like_leveraged_token(base):
                continue
            quote_volume = float(tickers.get(symbol, {}).get("quoteVolume", 0) or 0)
            symbols.append(BinanceSymbol(symbol=symbol, base_asset=base, quote_asset=quote, quote_volume=quote_volume))

        return sorted(symbols, key=lambda x: x.quote_volume, reverse=True)

    def get_daily_klines(self, symbol: str, years: int | None = None) -> pd.DataFrame:
        now_ms = int(time.time() * 1000)
        start_ms = 0 if years is None else now_ms - int(years * 365.25 * 24 * 60 * 60 * 1000)
        rows: list[list[Any]] = []

        while True:
            payload = self._get(
                "/api/v3/klines",
                {
                    "symbol": symbol,
                    "interval": "1d",
                    "startTime": start_ms,
                    "limit": 1000,
                },
            )
            if not payload:
                break
            rows.extend(payload)
            next_start = int(payload[-1][0]) + 24 * 60 * 60 * 1000
            if next_start >= now_ms or len(payload) < 1000:
                break
            start_ms = next_start

        return self._klines_to_frame(rows)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self._wait_for_ban_to_lift()
        self._pace_request()

        response = requests.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)

        if response.status_code in (418, 429):
            ban_until = self._parse_ban_until(response)
            if response.status_code == 418:
                _rate_limit_state.banned_until = ban_until
                wait_seconds = max(0, round(ban_until - time.time()))
                raise BinanceRateLimitBannedError(
                    "Binance đã tạm chặn IP server này vì gửi quá nhiều request (HTTP 418). "
                    f"Thử lại sau khoảng {wait_seconds} giây."
                )
            # 429: short-lived "too many requests", just wait and retry once.
            time.sleep(min(max(ban_until - time.time(), 1.0), 30.0))
            self._pace_request()
            response = requests.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)

        response.raise_for_status()
        self._throttle_if_near_limit(response)
        return response.json()

    @staticmethod
    def _pace_request() -> None:
        now = time.time()
        wait = _rate_limit_state.last_request_at + MIN_REQUEST_INTERVAL_SECONDS - now
        if wait > 0:
            time.sleep(wait)
        _rate_limit_state.last_request_at = time.time()

    @staticmethod
    def _wait_for_ban_to_lift() -> None:
        remaining = _rate_limit_state.banned_until - time.time()
        if remaining > 0:
            wait_seconds = round(remaining)
            raise BinanceRateLimitBannedError(
                f"Binance đang tạm chặn IP server này. Còn khoảng {wait_seconds} giây nữa mới gọi lại được."
            )

    @staticmethod
    def _parse_ban_until(response: requests.Response) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return time.time() + float(retry_after)
            except ValueError:
                pass
        try:
            message = str(response.json().get("msg", ""))
        except ValueError:
            message = ""
        match = re.search(r"until\s+(\d+)", message)
        if match:
            return int(match.group(1)) / 1000
        return time.time() + 60.0

    @staticmethod
    def _throttle_if_near_limit(response: requests.Response) -> None:
        used_weight = response.headers.get("X-MBX-USED-WEIGHT-1M")
        if used_weight is None:
            return
        ratio = float(used_weight) / WEIGHT_LIMIT_PER_MINUTE
        if ratio >= WEIGHT_SLOWDOWN_THRESHOLD:
            time.sleep(min(0.5 + ratio, 3.0))

    @staticmethod
    def _klines_to_frame(rows: list[list[Any]]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "quote_volume"])
        df = pd.DataFrame(
            rows,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "trades",
                "taker_buy_base",
                "taker_buy_quote",
                "ignore",
            ],
        )
        out = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(df["open_time"], unit="ms", utc=True),
                "open": pd.to_numeric(df["open"], errors="coerce"),
                "high": pd.to_numeric(df["high"], errors="coerce"),
                "low": pd.to_numeric(df["low"], errors="coerce"),
                "close": pd.to_numeric(df["close"], errors="coerce"),
                "volume": pd.to_numeric(df["volume"], errors="coerce"),
                "quote_volume": pd.to_numeric(df["quote_volume"], errors="coerce"),
            }
        )
        return out.dropna().reset_index(drop=True)

    @staticmethod
    def _looks_like_leveraged_token(base_asset: str) -> bool:
        stable_assets = {
            "USDC",
            "FDUSD",
            "TUSD",
            "USDP",
            "DAI",
            "USD1",
            "BUSD",
            "EUR",
            "EURI",
            "AEUR",
            "TRY",
            "BRL",
        }
        if base_asset in stable_assets:
            return True
        suffixes = ("UP", "DOWN", "BULL", "BEAR", "3L", "3S", "5L", "5S")
        return base_asset.endswith(suffixes)
