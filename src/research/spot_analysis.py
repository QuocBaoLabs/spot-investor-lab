from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


MILESTONES = [
    {
        "date": "2018-11-14",
        "name": "Downtrend 2018",
        "type": "Bear market",
        "desc": "Thị trường gấu kéo dài sau đỉnh 2017, giá giảm dần đều trong nhiều tháng.",
    },
    {
        "date": "2020-03-12",
        "name": "COVID crash",
        "type": "Thiên nga đen",
        "desc": "Cú sập bất ngờ vì hoảng loạn COVID-19, giá rơi rất nhanh chỉ trong 1-2 ngày.",
    },
    {
        "date": "2020-05-11",
        "name": "BTC Halving 2020",
        "type": "Halving",
        "desc": "Sự kiện giảm một nửa thưởng khối BTC, thường được kỳ vọng tích cực cho giá dài hạn.",
    },
    {
        "date": "2021-05-19",
        "name": "China/FUD crash 2021",
        "type": "Downtrend lớn",
        "desc": "Trung Quốc siết đào/giao dịch crypto, tin xấu dồn dập khiến giá giảm mạnh trong vài tuần.",
    },
    {
        "date": "2021-11-10",
        "name": "Đỉnh chu kỳ 2021",
        "type": "Market top",
        "desc": "Đỉnh giá của chu kỳ tăng 2020-2021, sau đó thị trường bắt đầu xu hướng giảm dài.",
    },
    {
        "date": "2022-05-12",
        "name": "LUNA/UST collapse",
        "type": "Thiên nga đen",
        "desc": "Stablecoin UST mất peg kéo theo LUNA sụp đổ, gây hoảng loạn lan ra toàn thị trường.",
    },
    {
        "date": "2022-11-09",
        "name": "FTX collapse",
        "type": "Thiên nga đen",
        "desc": "Sàn giao dịch FTX phá sản đột ngột, nhà đầu tư mất niềm tin và bán tháo diện rộng.",
    },
    {
        "date": "2024-04-20",
        "name": "BTC Halving 2024",
        "type": "Halving",
        "desc": "Lần giảm thưởng khối BTC gần nhất, là mốc được thị trường quan sát kỹ về cung tiền BTC mới.",
    },
]


@dataclass(frozen=True)
class SpotMetrics:
    symbol: str
    price: float
    listed_on: str
    age_days: int
    return_7d: float | None
    return_30d: float | None
    return_quarter: float | None
    return_180d: float | None
    return_1y: float | None
    return_2y: float | None
    return_since_listing: float | None
    above_ma200: bool
    distance_ma200: float | None
    drawdown_from_ath: float | None
    max_drawdown: float | None
    volatility_30d: float | None
    btc_strength_quarter: float | None
    btc_strength_1y: float | None
    btc_strength_2y: float | None
    event_stability_score: float
    risk_score: float
    investment_score: float
    decision: str
    note: str


def analyze_coin(symbol: str, df: pd.DataFrame, btc_df: pd.DataFrame) -> SpotMetrics:
    if df.empty or len(df) < 30:
        raise ValueError(f"Not enough data for {symbol}")

    frame = df.copy().sort_values("timestamp").reset_index(drop=True)
    btc = btc_df.copy().sort_values("timestamp").reset_index(drop=True)
    close = frame["close"]
    returns = close.pct_change()
    price = float(close.iloc[-1])
    age_days = int((frame["timestamp"].iloc[-1] - frame["timestamp"].iloc[0]).days)
    ma200 = close.rolling(200).mean()
    current_ma200 = ma200.iloc[-1]
    above_ma200 = bool(price >= current_ma200) if not pd.isna(current_ma200) else False
    distance_ma200 = pct(price, current_ma200) if current_ma200 and not pd.isna(current_ma200) else None
    ath = float(close.max())
    drawdown_from_ath = pct(price, ath)
    max_drawdown = calculate_max_drawdown(close)
    volatility_30d = float(returns.tail(30).std() * 100) if len(returns.dropna()) >= 30 else None

    r7 = period_return(close, 7)
    r30 = period_return(close, 30)
    rq = period_return(close, 90)
    r180 = period_return(close, 180)
    r1y = period_return(close, 365)
    r2y = period_return(close, 730)
    rlife = pct(float(close.iloc[-1]), float(close.iloc[0]))

    btc_rq = period_return(btc["close"], 90)
    btc_r1y = period_return(btc["close"], 365)
    btc_r2y = period_return(btc["close"], 730)
    strength_q = safe_sub(rq, btc_rq)
    strength_1y = safe_sub(r1y, btc_r1y)
    strength_2y = safe_sub(r2y, btc_r2y)

    event_df = milestone_reactions(symbol, frame)
    event_stability = float(event_df["score"].mean()) if not event_df.empty else 50.0
    risk = calculate_risk_score(
        above_ma200=above_ma200,
        drawdown_from_ath=drawdown_from_ath,
        max_drawdown=max_drawdown,
        volatility_30d=volatility_30d,
        strength_1y=strength_1y,
        strength_2y=strength_2y,
        event_stability=event_stability,
        age_days=age_days,
    )
    investment = calculate_investment_score(
        risk_score=risk,
        above_ma200=above_ma200,
        return_quarter=rq,
        return_1y=r1y,
        return_2y=r2y,
        strength_1y=strength_1y,
        strength_2y=strength_2y,
        event_stability=event_stability,
        age_days=age_days,
    )
    decision, note = decision_text(investment, risk, above_ma200)

    return SpotMetrics(
        symbol=symbol,
        price=price,
        listed_on=str(frame["timestamp"].iloc[0].date()),
        age_days=age_days,
        return_7d=r7,
        return_30d=r30,
        return_quarter=rq,
        return_180d=r180,
        return_1y=r1y,
        return_2y=r2y,
        return_since_listing=rlife,
        above_ma200=above_ma200,
        distance_ma200=distance_ma200,
        drawdown_from_ath=drawdown_from_ath,
        max_drawdown=max_drawdown,
        volatility_30d=volatility_30d,
        btc_strength_quarter=strength_q,
        btc_strength_1y=strength_1y,
        btc_strength_2y=strength_2y,
        event_stability_score=event_stability,
        risk_score=risk,
        investment_score=investment,
        decision=decision,
        note=note,
    )


def metrics_to_frame(metrics: list[SpotMetrics]) -> pd.DataFrame:
    rows = []
    for item in metrics:
        rows.append(
            {
                "Coin": item.symbol,
                "Giá spot": item.price,
                "Điểm đầu tư": item.investment_score,
                "Điểm rủi ro": item.risk_score,
                "Kết luận": item.decision,
                "Ghi chú": item.note,
                "Xu hướng MA200": "Trên MA200" if item.above_ma200 else "Dưới MA200",
                "Lãi/lỗ 7D %": item.return_7d,
                "Lãi/lỗ 30D %": item.return_30d,
                "Lãi/lỗ Quý %": item.return_quarter,
                "Lãi/lỗ 180D %": item.return_180d,
                "Lãi/lỗ 1Y %": item.return_1y,
                "Lãi/lỗ 2Y %": item.return_2y,
                "Từ khi niêm yết %": item.return_since_listing,
                "Sức mạnh quý vs BTC %": item.btc_strength_quarter,
                "Sức mạnh 1Y vs BTC %": item.btc_strength_1y,
                "Sức mạnh 2Y vs BTC %": item.btc_strength_2y,
                "Cách ATH %": item.drawdown_from_ath,
                "Max drawdown %": item.max_drawdown,
                "Biến động 30D %": item.volatility_30d,
                "Ổn định sự kiện": item.event_stability_score,
                "Ngày niêm yết Binance": item.listed_on,
                "Tuổi dữ liệu ngày": item.age_days,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame = frame.sort_values(["Điểm đầu tư", "Điểm rủi ro"], ascending=[False, True]).reset_index(drop=True)
    frame.insert(0, "Hạng", np.arange(1, len(frame) + 1))
    return frame


def milestone_reactions(symbol: str, df: pd.DataFrame, days_before: int = 7, days_after: int = 45) -> pd.DataFrame:
    rows = []
    frame = df.copy().sort_values("timestamp")
    for milestone in MILESTONES:
        event_date = pd.Timestamp(milestone["date"], tz="UTC")
        before = frame[frame["timestamp"] <= event_date - pd.Timedelta(days=days_before)]
        window = frame[(frame["timestamp"] >= event_date) & (frame["timestamp"] <= event_date + pd.Timedelta(days=days_after))]
        if before.empty or window.empty:
            continue
        anchor = float(before.iloc[-1]["close"])
        worst_low = float(window["low"].min())
        end_close = float(window.iloc[-1]["close"])
        worst_drop = pct(worst_low, anchor)
        recovery = pct(end_close, anchor)
        score = max(0.0, min(100.0, 100 + worst_drop * 1.15 + max(recovery, -30) * 0.25))
        rows.append(
            {
                "Coin": symbol,
                "Mốc": milestone["name"],
                "Loại": milestone["type"],
                "Ngày": milestone["date"],
                "Giải thích": milestone["desc"],
                "Sụt giảm xấu nhất %": worst_drop,
                "Hồi phục sau mốc %": recovery,
                "score": score,
            }
        )
    return pd.DataFrame(rows)


def calculate_max_drawdown(close: pd.Series) -> float:
    running_max = close.cummax()
    drawdown = close / running_max - 1
    return float(drawdown.min() * 100)


def calculate_risk_score(
    *,
    above_ma200: bool,
    drawdown_from_ath: float | None,
    max_drawdown: float | None,
    volatility_30d: float | None,
    strength_1y: float | None,
    strength_2y: float | None,
    event_stability: float,
    age_days: int,
) -> float:
    score = 15.0
    score += 0 if above_ma200 else 14
    score += penalty(abs(drawdown_from_ath or 0), [(35, 6), (55, 12), (75, 20)])
    score += penalty(abs(max_drawdown or 0), [(55, 5), (75, 12), (90, 20)])
    score += penalty(volatility_30d or 0, [(4, 6), (7, 12), (12, 20)])
    score += 8 if strength_1y is not None and strength_1y < -15 else 0
    score += 8 if strength_2y is not None and strength_2y < -25 else 0
    score += max(0, 60 - event_stability) * 0.35
    score += 10 if age_days < 365 else 5 if age_days < 730 else 0
    return round(float(min(max(score, 0), 100)), 2)


def calculate_investment_score(
    *,
    risk_score: float,
    above_ma200: bool,
    return_quarter: float | None,
    return_1y: float | None,
    return_2y: float | None,
    strength_1y: float | None,
    strength_2y: float | None,
    event_stability: float,
    age_days: int,
) -> float:
    score = 100 - risk_score
    score += 8 if above_ma200 else -6
    score += band_score(return_quarter, [(-20, -8), (0, 0), (20, 6), (60, 10)])
    score += band_score(return_1y, [(-30, -10), (0, 0), (50, 8), (150, 12)])
    score += band_score(return_2y, [(-40, -8), (0, 0), (80, 8), (250, 12)])
    score += band_score(strength_1y, [(-20, -8), (0, 0), (20, 8), (80, 12)])
    score += band_score(strength_2y, [(-30, -8), (0, 0), (40, 8), (120, 12)])
    score += (event_stability - 50) * 0.25
    score += min(age_days / 1460, 1) * 8
    return round(float(min(max(score, 0), 100)), 2)


def decision_text(investment_score: float, risk_score: float, above_ma200: bool) -> tuple[str, str]:
    if investment_score >= 75 and risk_score <= 35 and above_ma200:
        return "Đáng ưu tiên SPOT", "Điểm mạnh tốt, rủi ro tương đối thấp"
    if investment_score >= 62 and risk_score <= 50:
        return "Có thể DCA thận trọng", "Chỉ nên chia vốn, không mua một lần"
    if risk_score >= 70:
        return "Tránh mua lúc này", "Rủi ro cao hoặc drawdown/biến động xấu"
    return "Chờ thêm tín hiệu", "Chưa đủ lợi thế so với BTC/USDT"


def pct(current: float, previous: float) -> float | None:
    if previous == 0 or pd.isna(previous):
        return None
    return float((current / previous - 1) * 100)


def period_return(close: pd.Series, days: int) -> float | None:
    if len(close) <= days:
        return None
    return pct(float(close.iloc[-1]), float(close.iloc[-days - 1]))


def safe_sub(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return float(a - b)


def penalty(value: float, levels: list[tuple[float, float]]) -> float:
    result = 0.0
    for threshold, add in levels:
        if value >= threshold:
            result = add
    return result


def band_score(value: float | None, levels: list[tuple[float, float]]) -> float:
    if value is None:
        return -3.0
    result = 0.0
    for threshold, score in levels:
        if value >= threshold:
            result = score
    return result


def format_percent(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.2f}%"


def format_price(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    if value >= 100:
        return f"{value:,.2f}"
    if value >= 1:
        return f"{value:,.4f}"
    return f"{value:,.8f}"
