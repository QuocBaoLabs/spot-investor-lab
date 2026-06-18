from __future__ import annotations

from src.models import BrainDecision


def decision_to_order(decision: BrainDecision) -> dict | None:
    if decision.decision not in {"LONG", "SHORT"}:
        return None
    return {
        "symbol": decision.symbol,
        "side": "buy" if decision.decision == "LONG" else "sell",
        "entry": decision.entry,
        "stop_loss": decision.stop_loss,
        "take_profit": decision.take_profit_1,
        "confidence": decision.confidence_score,
    }
