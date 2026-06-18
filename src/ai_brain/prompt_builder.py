from __future__ import annotations

import json


def build_prompt(context: dict) -> str:
    return (
        "Analyze this market context and return LONG, SHORT, or NO_TRADE. "
        "Prioritize capital preservation and reject conflicting signals.\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )
