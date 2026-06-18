from __future__ import annotations

import pandas as pd

from src.ai_brain.reasoning_engine import ReasoningEngine
from src.backtest.metrics import calculate_metrics
from src.data.market_data import load_multitimeframe_data
from src.models import AccountState, TradingConfig
from src.risk.position_sizing import calculate_position_size


class BacktestEngine:
    def __init__(self, config: TradingConfig, initial_balance: float = 1000.0) -> None:
        self.config = config
        self.initial_balance = initial_balance
        self.brain = ReasoningEngine(config)

    def run(self, base_df: pd.DataFrame, warmup: int = 300, step: int = 24) -> dict:
        account = AccountState(balance=self.initial_balance, equity=self.initial_balance)
        trades: list[dict] = []
        open_trade: dict | None = None

        for i in range(warmup, len(base_df), step):
            current = base_df.iloc[: i + 1].copy()
            candle = current.iloc[-1]

            if open_trade:
                closed = self._check_exit(open_trade, candle, account)
                if closed:
                    trades.append(closed)
                    account.balance += closed["pnl"]
                    account.equity = account.balance
                    account.daily_pnl += closed["pnl"]
                    account.weekly_pnl += closed["pnl"]
                    account.consecutive_losses = account.consecutive_losses + 1 if closed["pnl"] < 0 else 0
                    account.open_positions = 0
                    open_trade = None
                continue

            mtf = load_multitimeframe_data(current)
            decision = self.brain.analyze(mtf, account)
            if decision.decision in {"LONG", "SHORT"} and decision.entry and decision.stop_loss:
                size = calculate_position_size(account.balance, self.config.risk_percent, decision.entry, decision.stop_loss)
                if size <= 0:
                    continue
                open_trade = {
                    "entry_time": candle["timestamp"],
                    "side": decision.decision,
                    "entry": decision.entry,
                    "stop_loss": decision.stop_loss,
                    "take_profit": decision.take_profit_1,
                    "size": size,
                    "confidence": decision.confidence_score,
                    "reason": decision.reason,
                }
                account.open_positions = 1

        metrics = calculate_metrics(trades, self.initial_balance)
        return {"metrics": metrics, "trades": trades[-50:]}

    @staticmethod
    def _check_exit(trade: dict, candle: pd.Series, account: AccountState) -> dict | None:
        side = trade["side"]
        hit_tp = candle["high"] >= trade["take_profit"] if side == "LONG" else candle["low"] <= trade["take_profit"]
        hit_sl = candle["low"] <= trade["stop_loss"] if side == "LONG" else candle["high"] >= trade["stop_loss"]
        if not (hit_tp or hit_sl):
            return None

        # Conservative when TP and SL touch in same candle: count SL first.
        exit_price = trade["stop_loss"] if hit_sl else trade["take_profit"]
        direction = 1 if side == "LONG" else -1
        pnl = (exit_price - trade["entry"]) * trade["size"] * direction
        risk = abs(trade["entry"] - trade["stop_loss"]) * trade["size"]
        rr = pnl / risk if risk > 0 else 0
        return {
            **trade,
            "exit_time": candle["timestamp"],
            "exit": exit_price,
            "pnl": round(float(pnl), 2),
            "rr": round(float(rr), 2),
            "balance_after": round(float(account.balance + pnl), 2),
        }
