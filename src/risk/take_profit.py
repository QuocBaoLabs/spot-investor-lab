from __future__ import annotations


def take_profits(entry: float, stop_loss: float, side: str) -> tuple[float, float, float, float]:
    risk = abs(entry - stop_loss)
    if side == "LONG":
        return entry + risk * 2, entry + risk * 3, entry + risk * 4, 2.0
    return entry - risk * 2, entry - risk * 3, entry - risk * 4, 2.0
