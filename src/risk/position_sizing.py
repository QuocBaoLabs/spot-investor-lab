from __future__ import annotations


def calculate_position_size(balance: float, risk_percent: float, entry: float, stop_loss: float) -> float:
    risk_amount = balance * risk_percent / 100
    stop_distance = abs(entry - stop_loss)
    if stop_distance <= 0:
        return 0.0
    return risk_amount / stop_distance
