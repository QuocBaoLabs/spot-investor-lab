from __future__ import annotations

import os

from dotenv import load_dotenv

from src.models import TradingConfig


def load_config() -> TradingConfig:
    load_dotenv()
    return TradingConfig(
        symbol=os.getenv("SYMBOL", "BTCUSDT"),
        risk_percent=float(os.getenv("RISK_PERCENT", "0.5")),
        max_daily_loss_percent=float(os.getenv("MAX_DAILY_LOSS_PERCENT", "2")),
        max_weekly_loss_percent=float(os.getenv("MAX_WEEKLY_LOSS_PERCENT", "5")),
        max_leverage=float(os.getenv("MAX_LEVERAGE", "3")),
        live_trading_enabled=os.getenv("LIVE_TRADING_ENABLED", "false").lower() == "true",
    )
