from __future__ import annotations

from src.models import AccountState, TradeSetup, TradingConfig
from src.risk.kill_switch import kill_switch_reason
from src.risk.position_sizing import calculate_position_size


class RiskManager:
    def __init__(self, config: TradingConfig) -> None:
        self.config = config

    def validate(self, setup: TradeSetup | None, account: AccountState) -> dict:
        reason = kill_switch_reason(account, self.config)
        if reason:
            return self._reject(reason)
        if setup is None:
            return self._reject("No valid setup")
        if self.config.risk_percent > 1.0:
            return self._reject("Risk percent exceeds 1% safety limit")
        if setup.rr_ratio < self.config.min_rr:
            return self._reject("RR below minimum")
        if setup.stop_loss <= 0:
            return self._reject("Invalid stop loss")

        size = calculate_position_size(account.balance, self.config.risk_percent, setup.entry, setup.stop_loss)
        notional = size * setup.entry
        leverage = notional / account.equity if account.equity else 999
        if leverage > self.config.max_leverage:
            return self._reject("Position requires leverage above max")

        return {
            "approved": True,
            "risk_percent": self.config.risk_percent,
            "rr_ratio": setup.rr_ratio,
            "stop_loss_valid": True,
            "position_size_valid": size > 0,
            "daily_loss_limit_ok": True,
            "position_size": size,
            "estimated_leverage": leverage,
            "reason": "Risk checks passed",
        }

    @staticmethod
    def _reject(reason: str) -> dict:
        return {
            "approved": False,
            "risk_percent": None,
            "rr_ratio": None,
            "stop_loss_valid": False,
            "position_size_valid": False,
            "daily_loss_limit_ok": False,
            "position_size": 0,
            "estimated_leverage": 0,
            "reason": reason,
        }
