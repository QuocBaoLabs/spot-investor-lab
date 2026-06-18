from __future__ import annotations

from src.models import AccountState, TradingConfig


def kill_switch_reason(account: AccountState, config: TradingConfig) -> str | None:
    if account.daily_pnl <= -account.balance * config.max_daily_loss_percent / 100:
        return "Max daily loss reached"
    if account.weekly_pnl <= -account.balance * config.max_weekly_loss_percent / 100:
        return "Max weekly loss reached"
    if account.consecutive_losses >= 3:
        return "Three consecutive losses"
    if account.open_positions >= config.max_open_positions:
        return "Max open positions reached"
    return None
