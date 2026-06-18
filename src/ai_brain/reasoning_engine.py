from __future__ import annotations

from src.indicators import add_indicators
from src.models import AccountState, BrainDecision, TradeSetup, TradingConfig
from src.risk.risk_manager import RiskManager
from src.risk.stop_loss import long_stop_loss, short_stop_loss
from src.risk.take_profit import take_profits
from src.smc.fair_value_gap import detect_fvg
from src.smc.liquidity import detect_liquidity
from src.smc.order_block import detect_order_block
from src.smc.premium_discount import premium_or_discount
from src.structure.bos_choch import detect_bos_choch
from src.structure.market_structure import classify_structure
from src.wyckoff.phase_detector import detect_phase


class ReasoningEngine:
    def __init__(self, config: TradingConfig) -> None:
        self.config = config
        self.risk = RiskManager(config)

    def analyze(self, mtf_data: dict, account: AccountState) -> BrainDecision:
        enriched = {tf: add_indicators(df).ffill().bfill().reset_index(drop=True) for tf, df in mtf_data.items()}
        d1 = enriched["D1"]
        h4 = enriched["H4"]
        h1 = enriched["H1"]
        m15 = enriched["M15"]

        if min(len(d1), len(h4), len(h1), len(m15)) < 2:
            return self._no_trade("Not enough market data", account)

        h4_bias = self._ema_bias(h4)
        d1_bias = self._ema_bias(d1)
        h1_structure = classify_structure(h1)
        bos = detect_bos_choch(h1)
        liquidity = detect_liquidity(m15)
        fvg = detect_fvg(m15)
        order_block = detect_order_block(m15)
        premium_discount = premium_or_discount(m15)
        wyckoff = detect_phase(m15)
        indicators = self._indicator_context(h4, h1, m15)

        long_score = 0
        short_score = 0
        reasons: list[str] = []

        if h4_bias == "bullish":
            long_score += 20
            reasons.append("H4 bullish bias")
        elif h4_bias == "bearish":
            short_score += 20
            reasons.append("H4 bearish bias")

        if d1_bias == h4_bias and h4_bias != "neutral":
            if h4_bias == "bullish":
                long_score += 10
            else:
                short_score += 10

        if bos["direction"] == "bullish":
            long_score += 15
        elif bos["direction"] == "bearish":
            short_score += 15

        if liquidity["sweep_low"]:
            long_score += 15
        if liquidity["sweep_high"]:
            short_score += 15

        if fvg["direction"] == "bullish" or order_block["direction"] == "bullish":
            long_score += 10
        if fvg["direction"] == "bearish" or order_block["direction"] == "bearish":
            short_score += 10

        if premium_discount == "discount":
            long_score += 10
        elif premium_discount == "premium":
            short_score += 10

        if wyckoff["spring"]:
            long_score += 15
        if wyckoff["upthrust"]:
            short_score += 15

        if indicators["macd"] == "bullish momentum":
            long_score += 8
        elif indicators["macd"] == "bearish momentum":
            short_score += 8

        if indicators["atr_condition"] == "abnormal":
            long_score -= 20
            short_score -= 20

        decision_side = "NO_TRADE"
        confidence = max(long_score, short_score)
        setup = None
        entry = float(m15["close"].iloc[-1])

        if confidence >= 70 and abs(long_score - short_score) >= 12:
            if long_score > short_score:
                stop = long_stop_loss(m15)
                tp1, tp2, tp3, rr = take_profits(entry, stop, "LONG")
                setup = TradeSetup(self.config.symbol, "LONG", entry, stop, tp1, tp2, tp3, rr, confidence, "; ".join(reasons))
            else:
                stop = short_stop_loss(m15)
                tp1, tp2, tp3, rr = take_profits(entry, stop, "SHORT")
                setup = TradeSetup(self.config.symbol, "SHORT", entry, stop, tp1, tp2, tp3, rr, confidence, "; ".join(reasons))

        risk_check = self.risk.validate(setup, account)
        if setup and risk_check["approved"]:
            decision_side = setup.side
        else:
            confidence = min(confidence, 59)

        reason = setup.reason if setup and risk_check["approved"] else risk_check["reason"]
        return BrainDecision(
            symbol=self.config.symbol,
            timeframes_checked=["D1", "H4", "H1", "M15"],
            market_bias=h4_bias if h4_bias == d1_bias else "neutral",
            smc_analysis={
                "structure": h1_structure,
                "bos": bos["bos"],
                "choch": bos["choch"],
                "liquidity_sweep": liquidity["liquidity_sweep"],
                "order_block_detected": order_block["order_block_detected"],
                "fvg_detected": fvg["fvg_detected"],
                "premium_or_discount": premium_discount,
            },
            wyckoff_analysis={
                "phase": wyckoff["phase"],
                "spring": wyckoff["spring"],
                "upthrust": wyckoff["upthrust"],
                "volume_confirmation": wyckoff["volume_confirmation"],
            },
            indicator_confirmation=indicators,
            risk_check=risk_check,
            decision=decision_side,
            entry=setup.entry if setup and risk_check["approved"] else None,
            stop_loss=setup.stop_loss if setup and risk_check["approved"] else None,
            take_profit_1=setup.take_profit_1 if setup and risk_check["approved"] else None,
            take_profit_2=setup.take_profit_2 if setup and risk_check["approved"] else None,
            take_profit_3=setup.take_profit_3 if setup and risk_check["approved"] else None,
            confidence_score=int(confidence),
            reason=reason,
        )

    def _no_trade(self, reason: str, account: AccountState) -> BrainDecision:
        risk_check = self.risk.validate(None, account)
        risk_check["reason"] = reason
        return BrainDecision(self.config.symbol, ["D1", "H4", "H1", "M15"], "neutral", {}, {}, {}, risk_check, "NO_TRADE", None, None, None, None, None, 0, reason)

    @staticmethod
    def _ema_bias(df) -> str:
        last = df.iloc[-1]
        if last["close"] > last["ema200"] and last["ema50"] > last["ema200"]:
            return "bullish"
        if last["close"] < last["ema200"] and last["ema50"] < last["ema200"]:
            return "bearish"
        return "neutral"

    @staticmethod
    def _indicator_context(h4, h1, m15) -> dict:
        macd = "bullish momentum" if m15["macd"].iloc[-1] > m15["macd_signal"].iloc[-1] else "bearish momentum"
        rsi_value = float(m15["rsi"].iloc[-1])
        rsi_state = "overbought" if rsi_value > 70 else "oversold" if rsi_value < 30 else "neutral"
        atr_ratio = float(m15["atr"].iloc[-1] / m15["close"].iloc[-1])
        return {
            "ema200_bias": "bullish" if h1["close"].iloc[-1] > h1["ema200"].iloc[-1] else "bearish",
            "macd": macd,
            "rsi": rsi_state,
            "atr_condition": "abnormal" if atr_ratio > 0.04 else "normal",
            "sar": "bullish" if m15["sar"].iloc[-1] < m15["close"].iloc[-1] else "bearish",
        }
