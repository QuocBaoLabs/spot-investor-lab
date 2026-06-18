from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.execution.order_manager import decision_to_order
from src.models import BrainDecision


class PaperTrader:
    def __init__(self, log_path: str | Path = "paper_trades.jsonl") -> None:
        self.log_path = Path(log_path)

    def submit(self, decision: BrainDecision) -> dict:
        order = decision_to_order(decision)
        if order is None:
            event = {"time": self._now(), "status": "no_trade", "reason": decision.reason}
        else:
            event = {"time": self._now(), "status": "paper_order_created", "order": order, "reason": decision.reason}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
