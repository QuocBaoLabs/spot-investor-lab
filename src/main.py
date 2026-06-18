from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ai_brain.reasoning_engine import ReasoningEngine
from src.backtest.backtest_engine import BacktestEngine
from src.config import load_config
from src.data.market_data import generate_sample_ohlcv, load_multitimeframe_data, load_ohlcv
from src.execution.live_trader import LiveTrader
from src.execution.paper_trader import PaperTrader
from src.models import AccountState


def load_data(path: str | None):
    if path:
        return load_ohlcv(Path(path))
    return generate_sample_ohlcv()


def run_analysis(args) -> None:
    config = load_config()
    config.symbol = args.symbol
    df = load_data(args.data)
    mtf = load_multitimeframe_data(df)
    decision = ReasoningEngine(config).analyze(mtf, AccountState())
    print(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))


def run_backtest(args) -> None:
    config = load_config()
    config.symbol = args.symbol
    df = load_data(args.data)
    result = BacktestEngine(config, initial_balance=args.balance).run(df)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def run_paper(args) -> None:
    config = load_config()
    config.symbol = args.symbol
    df = load_data(args.data)
    decision = ReasoningEngine(config).analyze(load_multitimeframe_data(df), AccountState())
    event = PaperTrader().submit(decision)
    print(json.dumps({"decision": decision.to_dict(), "paper_event": event}, ensure_ascii=False, indent=2))


def run_live(args) -> None:
    config = load_config()
    config.symbol = args.symbol
    df = load_data(args.data)
    decision = ReasoningEngine(config).analyze(load_multitimeframe_data(df), AccountState())
    event = LiveTrader(config).submit(decision)
    print(json.dumps({"decision": decision.to_dict(), "live_event": event}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Trading Bot")
    parser.add_argument("--mode", choices=["analysis", "backtest", "paper", "live"], default="analysis")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--data", default=None, help="CSV OHLCV file path")
    parser.add_argument("--balance", type=float, default=1000.0)
    args = parser.parse_args()

    if args.mode == "analysis":
        run_analysis(args)
    elif args.mode == "backtest":
        run_backtest(args)
    elif args.mode == "paper":
        run_paper(args)
    elif args.mode == "live":
        run_live(args)


if __name__ == "__main__":
    main()
