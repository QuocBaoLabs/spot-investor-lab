from __future__ import annotations

import pandas as pd


def calculate_metrics(trades: list[dict], initial_balance: float) -> dict:
    if not trades:
        return {
            "trades": 0,
            "winrate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_percent": 0.0,
            "average_rr": 0.0,
            "net_pnl": 0.0,
            "ending_balance": initial_balance,
        }

    df = pd.DataFrame(trades)
    wins = df[df["pnl"] > 0]
    losses = df[df["pnl"] < 0]
    gross_profit = wins["pnl"].sum()
    gross_loss = abs(losses["pnl"].sum())
    equity = initial_balance + df["pnl"].cumsum()
    peak = equity.cummax()
    drawdown = (equity - peak) / peak * 100

    return {
        "trades": int(len(df)),
        "winrate": round(len(wins) / len(df) * 100, 2),
        "profit_factor": round(float(gross_profit / gross_loss), 2) if gross_loss > 0 else float("inf"),
        "max_drawdown_percent": round(abs(float(drawdown.min())), 2),
        "average_rr": round(float(df["rr"].mean()), 2),
        "net_pnl": round(float(df["pnl"].sum()), 2),
        "ending_balance": round(float(initial_balance + df["pnl"].sum()), 2),
    }
