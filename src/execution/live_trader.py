from __future__ import annotations

from src.data.exchange_client import LiveExchangeClient
from src.execution.order_manager import decision_to_order
from src.models import BrainDecision, TradingConfig


class LiveTrader:
    def __init__(self, config: TradingConfig) -> None:
        self.config = config
        self.client = LiveExchangeClient(enabled=config.live_trading_enabled)

    def submit(self, decision: BrainDecision) -> dict:
        if not self.config.live_trading_enabled:
            return {"status": "blocked", "reason": "Live trading is disabled by default"}
        order = decision_to_order(decision)
        if order is None:
            return {"status": "no_trade", "reason": decision.reason}
        return self.client.create_order(order)
