from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TradingConfig:
    symbol: str = "BTCUSDT"
    risk_percent: float = 0.5
    min_rr: float = 2.0
    max_daily_loss_percent: float = 2.0
    max_weekly_loss_percent: float = 5.0
    max_open_positions: int = 1
    max_leverage: float = 3.0
    live_trading_enabled: bool = False


@dataclass
class AccountState:
    balance: float = 1000.0
    equity: float = 1000.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    consecutive_losses: int = 0
    open_positions: int = 0


@dataclass
class TradeSetup:
    symbol: str
    side: str
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    rr_ratio: float
    confidence_score: int
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrainDecision:
    symbol: str
    timeframes_checked: list[str]
    market_bias: str
    smc_analysis: dict[str, Any]
    wyckoff_analysis: dict[str, Any]
    indicator_confirmation: dict[str, Any]
    risk_check: dict[str, Any]
    decision: str
    entry: float | None
    stop_loss: float | None
    take_profit_1: float | None
    take_profit_2: float | None
    take_profit_3: float | None
    confidence_score: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframes_checked": self.timeframes_checked,
            "market_bias": self.market_bias,
            "smc_analysis": self.smc_analysis,
            "wyckoff_analysis": self.wyckoff_analysis,
            "indicator_confirmation": self.indicator_confirmation,
            "risk_check": self.risk_check,
            "decision": self.decision,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "take_profit_1": self.take_profit_1,
            "take_profit_2": self.take_profit_2,
            "take_profit_3": self.take_profit_3,
            "confidence_score": self.confidence_score,
            "reason": self.reason,
        }
