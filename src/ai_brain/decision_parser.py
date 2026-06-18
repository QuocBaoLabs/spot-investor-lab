from __future__ import annotations

from src.models import BrainDecision


def parse_decision(payload: dict) -> BrainDecision:
    return BrainDecision(**payload)
