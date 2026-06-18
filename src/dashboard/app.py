from __future__ import annotations

import html as html_lib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.binance_spot import BinanceSpotClient
from src.indicators.macd import macd as calc_macd
from src.indicators.rsi import rsi as calc_rsi
from src.research.spot_analysis import (
    MILESTONES,
    analyze_coin,
    format_percent,
    format_price,
    metrics_to_frame,
    milestone_reactions,
)


st.set_page_config(
    page_title="Spot Investor Lab",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ----------------------------------------------------------------------------------
# Theme palette + colors dùng lại cho cả CSS và Plotly để đồng bộ "huyền ảo / vũ trụ"
# ----------------------------------------------------------------------------------
INK = "#06070f"
PANEL = "rgba(255,255,255,0.045)"
BORDER = "rgba(167,139,250,0.28)"
TEXT = "#e7e9f5"
SUBTEXT = "#94a3b8"
CYAN = "#22d3ee"
VIOLET = "#a78bfa"
GOLD = "#fbbf24"
GREEN = "#34d399"
RED = "#fb7185"

PLOTLY_FONT = dict(family="'Space Grotesk', 'Inter', sans-serif", color=TEXT, size=12)


def style_fig(fig: go.Figure, height: int = 420, title: str | None = None) -> go.Figure:
    has_title = title is not None or fig.layout.title.text is not None
    layout_kwargs = dict(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,15,35,0.35)",
        font=PLOTLY_FONT,
        margin=dict(l=12, r=12, t=55 if has_title else 30, b=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=SUBTEXT)),
        hoverlabel=dict(bgcolor="#10142a", font_color=TEXT, bordercolor=BORDER),
    )
    if title is not None:
        layout_kwargs["title"] = dict(text=title, font=dict(color=TEXT))
    elif fig.layout.title.text is not None:
        fig.update_layout(title_font=dict(color=TEXT))
    fig.update_layout(**layout_kwargs)
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.08)", zerolinecolor="rgba(148,163,184,0.12)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.08)", zerolinecolor="rgba(148,163,184,0.12)")
    return fig


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

.stApp {{
    background:
        radial-gradient(circle at 10% -10%, rgba(34, 211, 238, 0.16), transparent 38%),
        radial-gradient(circle at 90% 0%, rgba(167, 139, 250, 0.18), transparent 40%),
        radial-gradient(circle at 50% 100%, rgba(251, 191, 36, 0.07), transparent 45%),
        radial-gradient(1px 1px at 20px 30px, rgba(255,255,255,0.25) 99%, transparent),
        radial-gradient(1px 1px at 140px 90px, rgba(255,255,255,0.18) 99%, transparent),
        radial-gradient(1px 1px at 60px 160px, rgba(255,255,255,0.18) 99%, transparent),
        linear-gradient(160deg, {INK} 0%, #0b0f24 45%, #130a26 100%);
    background-attachment: fixed;
    color: {TEXT};
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(200deg, #0a0d1f 0%, #120a24 100%);
    border-right: 1px solid {BORDER};
    min-width: 320px !important;
}}
[data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] {{
    display: none !important;
}}
[data-testid="stSidebar"] * {{
    color: {TEXT};
}}
[data-testid="stSidebar"] .stRadio label, [data-testid="stSidebar"] .stSelectbox label {{
    color: {CYAN} !important;
    font-weight: 600;
}}

h1, h2, h3, h4 {{ font-family: 'Space Grotesk', sans-serif; }}

.hero {{
    position: relative;
    padding: 30px 36px;
    border-radius: 20px;
    background: linear-gradient(135deg, rgba(8,12,28,0.92) 0%, rgba(26,16,46,0.92) 55%, rgba(20,30,40,0.92) 100%);
    border: 1px solid {BORDER};
    box-shadow: 0 0 0 1px rgba(255,255,255,0.02) inset, 0 25px 60px rgba(10, 8, 30, 0.55), 0 0 40px rgba(34,211,238,0.08);
    margin-bottom: 22px;
    overflow: hidden;
}}
.hero::before {{
    content: "";
    position: absolute;
    inset: -2px;
    background: linear-gradient(120deg, {CYAN}, {VIOLET}, {GOLD}, {CYAN});
    background-size: 300% 300%;
    opacity: 0.18;
    filter: blur(30px);
    animation: drift 14s ease infinite;
    z-index: 0;
}}
@keyframes drift {{
    0% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}
.hero h1 {{
    position: relative; z-index: 1;
    margin: 0 0 10px 0;
    font-size: 36px;
    font-weight: 700;
    background: linear-gradient(90deg, #ffffff 0%, {CYAN} 45%, {VIOLET} 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 30px rgba(34,211,238,0.25);
}}
.hero p {{
    position: relative; z-index: 1;
    margin: 0;
    color: {SUBTEXT};
    font-size: 14.5px;
    line-height: 1.55;
    max-width: 820px;
}}
.hero p + p {{ margin-top: 9px; }}
.hero .hero-credit {{
    color: {VIOLET};
    font-weight: 600;
}}
.hero .badge-row {{ position: relative; z-index: 1; margin-top: 16px; display: flex; gap: 8px; flex-wrap: wrap; }}
.pill {{
    display: inline-block;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid {BORDER};
    background: rgba(255,255,255,0.04);
    color: {TEXT};
}}

.ticker-wrap {{
    overflow: hidden;
    white-space: nowrap;
    border-radius: 14px;
    border: 1px solid {BORDER};
    background: linear-gradient(90deg, rgba(8,12,28,0.96), rgba(20,12,36,0.96));
    box-shadow: 0 10px 28px rgba(5,5,20,0.4), inset 0 0 18px rgba(34,211,238,0.06);
    padding: 11px 0;
    margin-bottom: 22px;
}}
.ticker-track {{
    display: inline-block;
    white-space: nowrap;
    will-change: transform;
}}
.ticker-wrap:hover .ticker-track {{ animation-play-state: paused; }}
@keyframes ticker-scroll {{
    0% {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
}}
.ticker-item {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 0 22px;
    border-right: 1px solid rgba(255,255,255,0.08);
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13.5px;
}}
.ticker-dot {{ width: 6px; height: 6px; border-radius: 50%; background: {CYAN}; box-shadow: 0 0 8px {CYAN}; display: inline-block; }}
.ticker-symbol {{ color: {TEXT}; font-weight: 700; letter-spacing: 0.3px; }}
.ticker-price {{ color: {CYAN}; font-weight: 600; }}
.ticker-change {{ font-weight: 700; }}

.section-title {{
    display: flex; align-items: center; gap: 10px;
    font-size: 19px;
    font-weight: 700;
    margin: 28px 0 12px 0;
    color: {TEXT};
}}
.section-title .bar {{
    width: 5px; height: 20px; border-radius: 4px;
    background: linear-gradient(180deg, {CYAN}, {VIOLET});
    box-shadow: 0 0 12px rgba(34,211,238,0.6);
}}
.section-sub {{ color: {SUBTEXT}; font-size: 13px; margin: -6px 0 14px 0; }}

.kpi-card {{
    position: relative;
    padding: 16px 18px;
    border-radius: 16px;
    background: {PANEL};
    border: 1px solid {BORDER};
    backdrop-filter: blur(14px);
    box-shadow: 0 10px 30px rgba(5,5,20,0.35);
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    height: 100%;
}}
.kpi-card:hover {{
    transform: perspective(600px) translateY(-5px) rotateX(2deg);
    border-color: rgba(34,211,238,0.55);
    box-shadow: 0 18px 40px rgba(5,5,25,0.55), 0 0 24px rgba(34,211,238,0.18);
}}
.kpi-top {{ display:flex; align-items:center; gap:8px; margin-bottom: 8px; }}
.kpi-icon {{ font-size: 18px; filter: drop-shadow(0 0 6px rgba(34,211,238,0.5)); }}
.kpi-label {{ color: {SUBTEXT}; font-size: 12.5px; font-weight: 600; letter-spacing: 0.2px; }}
.kpi-value {{ font-size: 24px; font-weight: 700; color: {TEXT}; font-family: 'Space Grotesk', sans-serif; }}
.kpi-sub {{ font-size: 12px; margin-top: 4px; color: {SUBTEXT}; }}
.tone-pos {{ border-left: 3px solid {GREEN}; }}
.tone-neg {{ border-left: 3px solid {RED}; }}
.tone-gold {{ border-left: 3px solid {GOLD}; }}
.tone-cyan {{ border-left: 3px solid {CYAN}; }}
.tone-violet {{ border-left: 3px solid {VIOLET}; }}
.tone-pos .kpi-value {{ color: {GREEN}; }}
.tone-neg .kpi-value {{ color: {RED}; }}
.tone-gold .kpi-value {{ color: {GOLD}; }}
.tone-cyan .kpi-value {{ color: {CYAN}; }}
.tone-violet .kpi-value {{ color: {VIOLET}; }}

.glass-panel {{
    padding: 18px 20px;
    border-radius: 16px;
    background: {PANEL};
    border: 1px solid {BORDER};
    backdrop-filter: blur(14px);
    box-shadow: 0 10px 30px rgba(5,5,20,0.35);
}}

.small-note {{ color: {SUBTEXT}; font-size: 13px; line-height: 1.5; }}

div[data-testid="stDataFrame"] {{
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid {BORDER};
    box-shadow: 0 10px 30px rgba(5,5,20,0.35);
}}

[data-testid="stMetricValue"] {{ color: {CYAN}; }}

.anchor-target {{ scroll-margin-top: 80px; }}

.nav-block {{
    margin-bottom: 18px;
    padding: 12px 14px;
    border-radius: 14px;
    background: rgba(255,255,255,0.04);
    border: 1px solid {BORDER};
}}
.nav-title {{
    font-size: 11.5px; font-weight: 700; color: {SUBTEXT};
    margin-bottom: 8px; letter-spacing: 0.5px; text-transform: uppercase;
}}
.nav-link {{
    display: block;
    padding: 7px 10px;
    margin-bottom: 4px;
    border-radius: 8px;
    color: {TEXT} !important;
    text-decoration: none !important;
    font-size: 13.5px;
    font-weight: 600;
    transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}}
.nav-link:hover {{
    background: rgba(34,211,238,0.16);
    color: {CYAN} !important;
    transform: translateX(2px);
}}

.glow-table-wrap {{
    overflow: auto;
    border-radius: 16px;
    border: 1px solid {BORDER};
    background: {PANEL};
    backdrop-filter: blur(14px);
    box-shadow: 0 10px 30px rgba(5,5,20,0.35);
    margin-bottom: 10px;
}}
table.glow-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    white-space: nowrap;
}}
table.glow-table thead th {{
    position: sticky;
    top: 0;
    z-index: 2;
    background: linear-gradient(180deg, rgba(34,211,238,0.22), rgba(20,16,38,0.96));
    color: {TEXT};
    text-align: left;
    padding: 11px 16px;
    font-weight: 700;
    font-size: 12.5px;
    border-bottom: 1px solid {BORDER};
    backdrop-filter: blur(8px);
}}
table.glow-table tbody td {{
    padding: 9px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.045);
    color: {TEXT};
}}
table.glow-table tbody td.wrap-cell {{ white-space: normal; min-width: 220px; color: {SUBTEXT}; }}
table.glow-table tbody tr:hover {{ background: rgba(34,211,238,0.07); }}
table.glow-table tbody tr:nth-child(even) {{ background: rgba(255,255,255,0.015); }}
.badge {{
    display: inline-block;
    padding: 3px 11px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 700;
    border: 1px solid;
    white-space: nowrap;
}}
.score-cell {{ display: flex; align-items: center; gap: 8px; }}
.score-bar {{ width: 54px; height: 6px; border-radius: 4px; background: rgba(255,255,255,0.08); overflow: hidden; }}
.score-fill {{ height: 100%; border-radius: 4px; }}
.cell-muted {{ color: {SUBTEXT}; }}

.stButton button, [data-testid="stSegmentedControl"] label {{
    border-radius: 999px !important;
}}

hr {{ border-color: {BORDER}; }}

::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: #0a0d1f; }}
::-webkit-scrollbar-thumb {{ background: linear-gradient(180deg, {CYAN}, {VIOLET}); border-radius: 10px; }}
</style>
"""


st.markdown(CSS, unsafe_allow_html=True)


TIMEFRAMES: dict[str, int | str | None] = {
    "7D": 7,
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "YTD": "ytd",
    "ALL": None,
}


@st.cache_data(ttl=60 * 30, show_spinner=False)
def load_symbol_universe() -> pd.DataFrame:
    symbols = BinanceSpotClient().get_usdt_spot_symbols()
    return pd.DataFrame([item.__dict__ for item in symbols])


@st.cache_data(ttl=60 * 60, show_spinner=False)
def load_history(symbol: str, history_years: int | None) -> pd.DataFrame:
    return BinanceSpotClient().get_daily_klines(symbol, years=history_years)


def default_symbols(universe: pd.DataFrame) -> list[str]:
    preferred = [
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
        "SOLUSDT",
        "XRPUSDT",
        "ADAUSDT",
        "DOGEUSDT",
        "AVAXUSDT",
        "LINKUSDT",
        "TRXUSDT",
        "TONUSDT",
        "DOTUSDT",
    ]
    available = set(universe["symbol"].to_list())
    defaults = [symbol for symbol in preferred if symbol in available]
    if len(defaults) < 8:
        defaults += [symbol for symbol in universe["symbol"].head(12).to_list() if symbol not in defaults]
    return defaults[:12]


POS_NEG_COLS = {
    "Lãi/lỗ 7D %",
    "Lãi/lỗ 30D %",
    "Lãi/lỗ Quý %",
    "Lãi/lỗ 180D %",
    "Lãi/lỗ 1Y %",
    "Lãi/lỗ 2Y %",
    "Từ khi niêm yết %",
    "Sức mạnh quý vs BTC %",
    "Sức mạnh 1Y vs BTC %",
    "Sức mạnh 2Y vs BTC %",
    "Hồi phục sau mốc %",
}
NEUTRAL_PCT_COLS = {"Cách ATH %", "Max drawdown %", "Biến động 30D %", "Sụt giảm xấu nhất %"}
SCORE_COLS = {"Điểm đầu tư", "Điểm rủi ro", "Ổn định sự kiện"}
PRICE_COLS = {"Giá spot"}
WRAP_COLS = {"Ghi chú", "Giải thích"}
BADGE_COLORS = {
    "Đáng ưu tiên SPOT": GREEN,
    "Có thể DCA thận trọng": GOLD,
    "Chờ thêm tín hiệu": VIOLET,
    "Tránh mua lúc này": RED,
    "Trên MA200": GREEN,
    "Dưới MA200": RED,
    "Halving": CYAN,
    "Thiên nga đen": RED,
    "Bear market": GOLD,
    "Downtrend lớn": GOLD,
    "Market top": VIOLET,
}


def _score_tone(col: str, value: float) -> str:
    if col == "Điểm rủi ro":
        return GREEN if value <= 35 else GOLD if value <= 60 else RED
    return GREEN if value >= 75 else GOLD if value >= 60 else RED


def _cell_html(col: str, value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return '<span class="cell-muted">N/A</span>'
    if col in SCORE_COLS:
        width = max(0.0, min(100.0, float(value)))
        color = _score_tone(col, float(value))
        return (
            f'<div class="score-cell"><span style="color:{color};font-weight:700">{value:.1f}</span>'
            f'<div class="score-bar"><div class="score-fill" style="width:{width}%;background:{color}"></div></div></div>'
        )
    if value in BADGE_COLORS:
        color = BADGE_COLORS[value]
        return f'<span class="badge" style="border-color:{color}66;color:{color};background:{color}1f">{html_lib.escape(str(value))}</span>'
    if col in PRICE_COLS:
        return html_lib.escape(format_price(value))
    if col in POS_NEG_COLS:
        value = float(value)
        color = GREEN if value >= 0 else RED
        sign = "+" if value >= 0 else ""
        return f'<span style="color:{color};font-weight:700">{sign}{value:,.2f}%</span>'
    if col in NEUTRAL_PCT_COLS:
        return f'<span style="color:{GOLD}">{float(value):,.2f}%</span>'
    return html_lib.escape(str(value))


def render_glow_table(df: pd.DataFrame, columns: list[str], height: int = 520) -> None:
    header_html = "".join(f"<th>{html_lib.escape(col)}</th>" for col in columns)
    body_rows = []
    for _, row in df.iterrows():
        cells = []
        for col in columns:
            cls = "wrap-cell" if col in WRAP_COLS else ""
            cells.append(f'<td class="{cls}">{_cell_html(col, row[col])}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    table_html = f"""
    <div class="glow-table-wrap" style="max-height:{height}px">
        <table class="glow-table">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{''.join(body_rows)}</tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


def build_ticker_html(histories: dict[str, pd.DataFrame], symbols: list[str]) -> str:
    items = []
    for symbol in symbols:
        df = histories.get(symbol)
        if df is None or len(df) < 2:
            continue
        last = float(df["close"].iloc[-1])
        prev = float(df["close"].iloc[-2])
        change = (last / prev - 1) * 100 if prev else 0.0
        color = GREEN if change >= 0 else RED
        arrow = "▲" if change >= 0 else "▼"
        items.append(
            '<span class="ticker-item"><span class="ticker-dot"></span>'
            f'<span class="ticker-symbol">{html_lib.escape(symbol.replace("USDT", ""))}</span>'
            f'<span class="ticker-price">{html_lib.escape(format_price(last))}</span>'
            f'<span class="ticker-change" style="color:{color}">{arrow} {abs(change):.2f}%</span></span>'
        )
    if not items:
        return ""
    sequence = "".join(items)
    duration = max(20, len(items) * 2)
    return (
        '<div class="ticker-wrap"><div class="ticker-track" '
        f'style="animation: ticker-scroll {duration}s linear infinite;">{sequence}{sequence}</div></div>'
    )


BACKGROUND_MUSIC_URL = "https://www.youtube.com/watch?v=N7DdxbmjkeY"


def extract_youtube_id(url: str) -> str | None:
    match = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


def render_background_music(video_id: str) -> None:
    html = f"""
    <div style="display:flex;align-items:center;gap:10px;font-family:'Space Grotesk',sans-serif;padding:6px 2px;">
        <div id="yt-audio-container" style="position:absolute;width:1px;height:1px;opacity:0;overflow:hidden;pointer-events:none;"></div>
        <button id="bg-toggle" style="
            background:rgba(255,255,255,0.06);
            border:1px solid rgba(167,139,250,0.45);
            color:#e7e9f5;
            border-radius:999px;
            padding:6px 14px;
            font-size:12.5px;
            font-weight:600;
            cursor:pointer;
        ">🔈 Đang kết nối nhạc nền...</button>
    </div>
    <script>
        var ytPlayer = null;

        function setLabel(text) {{
            var btn = document.getElementById("bg-toggle");
            if (btn) {{ btn.innerText = text; }}
        }}

        function onYouTubeIframeAPIReady() {{
            ytPlayer = new YT.Player("yt-audio-container", {{
                height: "1", width: "1", videoId: "{video_id}",
                playerVars: {{ autoplay: 1, loop: 1, playlist: "{video_id}", controls: 0 }},
                events: {{
                    onReady: function(e) {{
                        e.target.playVideo();
                        setTimeout(function() {{
                            if (ytPlayer.getPlayerState() === 1) {{
                                setLabel("🔊 Nhạc nền: đang phát");
                            }} else {{
                                setLabel("🔈 Trình duyệt chặn auto-play — bấm để phát");
                            }}
                        }}, 900);
                    }},
                    onStateChange: function(e) {{
                        if (e.data === 1) {{ setLabel("🔊 Nhạc nền: đang phát"); }}
                        else if (e.data === 2) {{ setLabel("🔈 Nhạc nền: đã tạm dừng"); }}
                    }},
                    onError: function(e) {{
                        setLabel("⚠️ Không phát được video này (mã lỗi " + e.data + ")");
                    }}
                }}
            }});
        }}

        var tag = document.createElement("script");
        tag.src = "https://www.youtube.com/iframe_api";
        document.head.appendChild(tag);

        document.getElementById("bg-toggle").addEventListener("click", function() {{
            if (!ytPlayer || !ytPlayer.getPlayerState) {{ return; }}
            var state = ytPlayer.getPlayerState();
            if (state === 1) {{ ytPlayer.pauseVideo(); }} else {{ ytPlayer.playVideo(); }}
        }});
    </script>
    """
    st.iframe(html, height=46)


def kpi_card(icon: str, label: str, value: str, sub: str | None = None, tone: str = "cyan") -> None:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="kpi-card tone-{tone}">
            <div class="kpi-top"><span class="kpi-icon">{icon}</span><span class="kpi-label">{label}</span></div>
            <div class="kpi-value">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(icon: str, title: str, sub: str | None = None, anchor: str | None = None) -> None:
    anchor_html = f'<div id="{anchor}" class="anchor-target"></div>' if anchor else ""
    st.markdown(f'{anchor_html}<div class="section-title"><span class="bar"></span>{icon} {title}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="section-sub">{sub}</div>', unsafe_allow_html=True)


def gauge_fig(value: float, title: str, color: str, max_value: float = 100) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=round(value, 1),
            title={"text": title, "font": {"size": 13, "color": SUBTEXT}},
            number={"font": {"size": 26, "color": TEXT}},
            gauge={
                "axis": {"range": [0, max_value], "tickcolor": SUBTEXT, "tickfont": {"color": SUBTEXT, "size": 9}},
                "bar": {"color": color, "thickness": 0.32},
                "bgcolor": "rgba(255,255,255,0.03)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, max_value * 0.4], "color": "rgba(251,113,133,0.16)"},
                    {"range": [max_value * 0.4, max_value * 0.7], "color": "rgba(251,191,36,0.16)"},
                    {"range": [max_value * 0.7, max_value], "color": "rgba(52,211,153,0.16)"},
                ],
            },
        )
    )
    fig.update_layout(height=210, margin=dict(l=24, r=24, t=46, b=10), paper_bgcolor="rgba(0,0,0,0)", font=PLOTLY_FONT)
    return fig


def donut_fig(labels: list[str], values: list[int], colors: list[str], title: str) -> go.Figure:
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            marker=dict(colors=colors, line=dict(color=INK, width=2)),
            textinfo="label+percent",
            textfont=dict(color=TEXT, size=11),
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=SUBTEXT)),
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=10, r=10, t=44, b=10),
        font=PLOTLY_FONT,
    )
    return fig


def scatter3d_fig(ranking: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Scatter3d(
            x=ranking["Điểm rủi ro"],
            y=ranking["Điểm đầu tư"],
            z=ranking["Ổn định sự kiện"],
            mode="markers+text",
            text=ranking["Coin"],
            textposition="top center",
            textfont=dict(size=9, color=SUBTEXT),
            marker=dict(
                size=6,
                color=ranking["Điểm đầu tư"],
                colorscale=[[0, RED], [0.5, GOLD], [1, GREEN]],
                opacity=0.9,
                line=dict(color="rgba(167,139,250,0.6)", width=1),
                colorbar=dict(title="Điểm đầu tư", tickfont=dict(color=SUBTEXT), title_font=dict(color=SUBTEXT)),
            ),
            hovertemplate="<b>%{text}</b><br>Rủi ro: %{x:.1f}<br>Điểm đầu tư: %{y:.1f}<br>Ổn định sự kiện: %{z:.1f}<extra></extra>",
        )
    )
    axis_style = dict(
        backgroundcolor="rgba(15,15,35,0.45)",
        gridcolor="rgba(148,163,184,0.15)",
        zerolinecolor="rgba(148,163,184,0.2)",
        color=SUBTEXT,
    )
    fig.update_layout(
        scene=dict(
            xaxis=dict(title="Điểm rủi ro", **axis_style),
            yaxis=dict(title="Điểm đầu tư", **axis_style),
            zaxis=dict(title="Ổn định sự kiện", **axis_style),
        ),
        height=600,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=PLOTLY_FONT,
    )
    return fig


def with_indicators(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.sort_values("timestamp").reset_index(drop=True).copy()
    frame["ma20"] = frame["close"].rolling(20).mean()
    frame["ma50"] = frame["close"].rolling(50).mean()
    frame["ma200"] = frame["close"].rolling(200).mean()
    frame["rsi14"] = calc_rsi(frame["close"], 14)
    macd_df = calc_macd(frame["close"])
    frame = pd.concat([frame, macd_df], axis=1)
    bb_std = frame["close"].rolling(20).std()
    frame["bb_upper"] = frame["ma20"] + 2 * bb_std
    frame["bb_lower"] = frame["ma20"] - 2 * bb_std
    return frame


def slice_timeframe(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    spec = TIMEFRAMES[key]
    if spec is None:
        return frame
    if spec == "ytd":
        start = pd.Timestamp(year=datetime.now(timezone.utc).year, month=1, day=1, tz="UTC")
        view = frame[frame["timestamp"] >= start]
        return view if not view.empty else frame
    return frame.tail(int(spec) + 1)


def build_price_matrix(histories: dict[str, pd.DataFrame], symbols: list[str], timeframe_key: str) -> pd.DataFrame:
    series_map: dict[str, pd.Series] = {}
    for symbol in symbols:
        df = histories.get(symbol)
        if df is None or df.empty:
            continue
        view = slice_timeframe(df.sort_values("timestamp"), timeframe_key)
        if len(view) < 2:
            continue
        series_map[symbol] = view.set_index("timestamp")["close"]
    if not series_map:
        return pd.DataFrame()
    return pd.concat(series_map, axis=1).dropna(how="any")


def normalized_performance(matrix: pd.DataFrame) -> pd.DataFrame:
    return (matrix / matrix.iloc[0] - 1) * 100


def compare_performance_fig(norm: pd.DataFrame, portfolio: pd.Series, btc_norm: pd.Series | None) -> go.Figure:
    palette = [CYAN, VIOLET, GOLD, GREEN, RED, "#38bdf8", "#f472b6", "#c084fc", "#facc15", "#4ade80"]
    fig = go.Figure()
    for index, col in enumerate(norm.columns):
        fig.add_trace(go.Scatter(x=norm.index, y=norm[col], name=str(col), line=dict(width=1.5, color=palette[index % len(palette)])))
    fig.add_trace(
        go.Scatter(x=portfolio.index, y=portfolio, name="📐 Danh mục chia đều", line=dict(width=3.2, color="#ffffff"))
    )
    if btc_norm is not None:
        fig.add_trace(go.Scatter(x=btc_norm.index, y=btc_norm, name="BTC (tham chiếu)", line=dict(width=2, color=GOLD, dash="dash")))
    fig.add_hline(y=0, line_width=1, line_color="rgba(148,163,184,0.35)")
    return fig


def correlation_fig(matrix: pd.DataFrame) -> go.Figure:
    returns = matrix.pct_change().dropna(how="all")
    corr = returns.corr()
    fig = px.imshow(
        corr,
        color_continuous_scale=[GREEN, "#0f172a", RED],
        zmin=-1,
        zmax=1,
        aspect="auto",
        title="Tương quan lợi nhuận hằng ngày",
        text_auto=".2f",
    )
    return fig


def build_detail_chart(frame: pd.DataFrame, symbol: str, timeframe_key: str) -> go.Figure:
    view = slice_timeframe(frame, timeframe_key)
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.48, 0.15, 0.17, 0.20],
        vertical_spacing=0.03,
        subplot_titles=(f"{symbol} · {timeframe_key}", "Khối lượng", "RSI (14)", "MACD"),
    )

    fig.add_trace(
        go.Scatter(
            x=view["timestamp"],
            y=view["bb_upper"],
            name="Bollinger Upper",
            line=dict(color="rgba(167,139,250,0.45)", width=1, dash="dot"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=view["timestamp"],
            y=view["bb_lower"],
            name="Bollinger Lower",
            line=dict(color="rgba(167,139,250,0.45)", width=1, dash="dot"),
            fill="tonexty",
            fillcolor="rgba(167,139,250,0.08)",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Candlestick(
            x=view["timestamp"],
            open=view["open"],
            high=view["high"],
            low=view["low"],
            close=view["close"],
            increasing_line_color=GREEN,
            decreasing_line_color=RED,
            name="Giá",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(go.Scatter(x=view["timestamp"], y=view["ma20"], name="MA20", line=dict(color=CYAN, width=1.3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=view["timestamp"], y=view["ma50"], name="MA50", line=dict(color=VIOLET, width=1.3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=view["timestamp"], y=view["ma200"], name="MA200", line=dict(color=GOLD, width=1.3)), row=1, col=1)

    vol_colors = np.where(view["close"] >= view["open"], "rgba(52,211,153,0.55)", "rgba(251,113,133,0.55)")
    fig.add_trace(go.Bar(x=view["timestamp"], y=view["volume"], marker_color=vol_colors, name="Volume", showlegend=False), row=2, col=1)

    fig.add_trace(go.Scatter(x=view["timestamp"], y=view["rsi14"], name="RSI14", line=dict(color=CYAN, width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="rgba(251,113,133,0.5)", row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="rgba(52,211,153,0.5)", row=3, col=1)

    hist_colors = np.where(view["macd_hist"] >= 0, "rgba(52,211,153,0.6)", "rgba(251,113,133,0.6)")
    fig.add_trace(go.Bar(x=view["timestamp"], y=view["macd_hist"], marker_color=hist_colors, name="Hist", showlegend=False), row=4, col=1)
    fig.add_trace(go.Scatter(x=view["timestamp"], y=view["macd"], name="MACD", line=dict(color=CYAN, width=1.3)), row=4, col=1)
    fig.add_trace(go.Scatter(x=view["timestamp"], y=view["macd_signal"], name="Signal", line=dict(color=GOLD, width=1.3)), row=4, col=1)

    if not view.empty:
        for milestone in MILESTONES:
            date = pd.Timestamp(milestone["date"], tz="UTC")
            if view["timestamp"].min() <= date <= view["timestamp"].max():
                fig.add_vline(x=date, line_width=1, line_dash="dot", line_color="rgba(167,139,250,0.4)", row=1, col=1)

    fig.update_layout(
        height=820,
        showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,15,35,0.35)",
        font=PLOTLY_FONT,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, font=dict(color=SUBTEXT)),
        margin=dict(l=12, r=12, t=60, b=12),
        xaxis_rangeslider_visible=False,
        hoverlabel=dict(bgcolor="#10142a", font_color=TEXT, bordercolor=BORDER),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.07)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.07)")
    for annotation in fig.layout.annotations:
        annotation.font = dict(color=SUBTEXT, size=12)
    return fig


def timeframe_return(frame: pd.DataFrame, timeframe_key: str) -> tuple[float | None, float, float, float]:
    view = slice_timeframe(frame, timeframe_key)
    if view.empty or len(view) < 2:
        return None, float("nan"), float("nan"), float("nan")
    change = (view["close"].iloc[-1] / view["close"].iloc[0] - 1) * 100
    return float(change), float(view["high"].max()), float(view["low"].min()), float(view["volume"].mean())


def main() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>✨ Spot Investor Lab</h1>
            <p class="hero-credit">👤 Được phát triển bởi 💎Bảo Lion💎 · ❤️ Dự án phi lợi nhuận phục vụ cộng đồng crypto Việt Nam.</p>
            <p>📊 Spot Investor Lab giúp anh em phân tích đầu tư spot dựa trên dữ liệu công khai: so sánh hiệu suất coin
            theo các mốc 7 ngày, 1 tháng, 3 tháng, 6 tháng và 1 năm.</p>
            <p>🔎 Web hỗ trợ xem coin nào ít lỗ nhất, coin nào có tỷ suất lợi nhuận tốt nhất. Ngoài ra còn theo dõi các
            chỉ số như drawdown, MA200, volume, sức mạnh so với BTC và một số chỉ báo kỹ thuật như RSI/MACD.</p>
            <p>🛡️ Dự án không bán tín hiệu, không kêu gọi đầu tư và không đưa ra khuyến nghị tài chính.</p>
            <p>🎯 Mục tiêu là tạo một công cụ dữ liệu minh bạch để anh em có thêm góc nhìn trước khi xuống tiền spot.</p>
            <div class="badge-row">
                <span class="pill">📡 Dữ liệu Binance Spot public API</span>
                <span class="pill">🛡️ Không bán tín hiệu · không khuyến nghị tài chính</span>
                <span class="pill">🕒 Khung thời gian tự chọn 7D → ALL</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    ticker_slot = st.empty()

    music_id = extract_youtube_id(BACKGROUND_MUSIC_URL)
    if music_id:
        render_background_music(music_id)

    st.sidebar.markdown(
        """
        <div class="nav-block">
            <div class="nav-title">🧭 Điều hướng nhanh</div>
            <a class="nav-link" href="#tong-quan">📊 Tổng quan thị trường</a>
            <a class="nav-link" href="#bang-xep-hang">🗂️ Bảng xếp hạng</a>
            <a class="nav-link" href="#so-sanh-danh-muc">📐 So sánh & danh mục</a>
            <a class="nav-link" href="#khong-gian-3d">🌌 Không gian 3D</a>
            <a class="nav-link" href="#moc-su-kien">⚡ Mốc sự kiện lớn</a>
            <a class="nav-link" href="#chi-tiet-coin">🔬 Chi tiết coin</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        with st.spinner("🔄 Đang lấy danh sách coin spot từ Binance..."):
            universe = load_symbol_universe()
    except requests.RequestException as exc:
        st.error(f"Không kết nối được Binance public API: {exc}")
        st.stop()

    st.sidebar.markdown("## ⚙️ Thiết lập dữ liệu")
    history_label = st.sidebar.radio(
        "Phạm vi dữ liệu",
        ["Từ khi niêm yết Binance", "2 năm gần nhất", "4 năm gần nhất", "8 năm gần nhất"],
        index=0,
    )
    history_years = {
        "Từ khi niêm yết Binance": None,
        "2 năm gần nhất": 2,
        "4 năm gần nhất": 4,
        "8 năm gần nhất": 8,
    }[history_label]

    st.sidebar.markdown("### 🪙 Danh sách coin")
    selection_mode = st.sidebar.radio(
        "Cách chọn coin",
        ["Top 50 Binance", "Top 100 Binance", "Tùy chọn"],
        horizontal=False,
    )

    if selection_mode == "Top 50 Binance":
        selected = universe["symbol"].head(50).to_list()
        st.sidebar.success("Đang dùng Top 50 theo volume spot USDT.")
    elif selection_mode == "Top 100 Binance":
        selected = universe["symbol"].head(100).to_list()
        st.sidebar.success("Đang dùng Top 100 theo volume spot USDT.")
    else:
        search_default = default_symbols(universe)
        selected = st.sidebar.multiselect(
            "Chọn tối đa 100 cặp spot USDT",
            options=universe["symbol"].to_list(),
            default=search_default,
            max_selections=100,
        )

    st.sidebar.caption(
        "Nguồn: Binance Spot public API. Top 50/100 được xếp theo quote volume 24h của cặp spot USDT. "
        "Lần tải đầu với dữ liệu toàn lịch sử có thể mất một lúc, nhưng sẽ được cache."
    )
    st.sidebar.metric("Số coin đang so sánh", len(selected))

    st.sidebar.markdown(
        """
        <div class="nav-block">
            <div class="nav-title">💬 Góp ý / báo lỗi chức năng</div>
            <a class="nav-link" href="https://t.me/quocbao1991" target="_blank">📨 Telegram: @quocbao1991</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not selected:
        st.warning("Hãy chọn ít nhất một coin để bắt đầu so sánh.")
        return

    btc_symbol = "BTCUSDT"
    progress = st.progress(0, text="Đang tải dữ liệu Binance...")
    histories: dict[str, pd.DataFrame] = {}
    errors: list[str] = []
    symbols_to_load = list(dict.fromkeys(selected + [btc_symbol]))

    for index, symbol in enumerate(symbols_to_load, start=1):
        try:
            histories[symbol] = load_history(symbol, history_years)
        except requests.RequestException as exc:
            errors.append(f"{symbol}: {exc}")
        progress.progress(index / len(symbols_to_load), text=f"Đã tải {index}/{len(symbols_to_load)} coin")
    progress.empty()

    if errors:
        with st.expander("Coin tải lỗi"):
            st.write(errors)

    btc_df = histories.get("BTCUSDT")
    if btc_df is None or btc_df.empty:
        st.error("Không có dữ liệu BTCUSDT để làm mốc so sánh.")
        return

    metrics = []
    event_tables = []
    analyze_progress = st.progress(0, text="Đang chấm điểm rủi ro / đầu tư cho từng coin...")
    for index, symbol in enumerate(selected, start=1):
        df = histories.get(symbol)
        if df is not None and not df.empty:
            try:
                metrics.append(analyze_coin(symbol, df, btc_df))
                event_tables.append(milestone_reactions(symbol, df))
            except ValueError:
                pass
        analyze_progress.progress(index / len(selected), text=f"Đã phân tích {index}/{len(selected)} coin")
    analyze_progress.empty()

    ranking = metrics_to_frame(metrics)
    if ranking.empty:
        st.error("Không đủ dữ liệu để phân tích các coin đã chọn.")
        return

    ticker_symbols = ranking["Coin"].head(40).to_list()
    ticker_html = build_ticker_html(histories, ticker_symbols)
    if ticker_html:
        ticker_slot.markdown(ticker_html, unsafe_allow_html=True)

    best = ranking.iloc[0]
    worst_risk = ranking.loc[ranking["Điểm rủi ro"].idxmin()]
    risk_low_count = int((ranking["Điểm rủi ro"] <= 35).sum())
    above_ma_count = int((ranking["Xu hướng MA200"] == "Trên MA200").sum())
    avg_score = float(ranking["Điểm đầu tư"].mean())
    avg_risk = float(ranking["Điểm rủi ro"].mean())
    avg_7d = ranking["Lãi/lỗ 7D %"].mean()
    avg_vol30 = ranking["Biến động 30D %"].mean()
    top_gainer = ranking.loc[ranking["Lãi/lỗ 7D %"].idxmax()] if ranking["Lãi/lỗ 7D %"].notna().any() else None
    top_loser = ranking.loc[ranking["Lãi/lỗ 7D %"].idxmin()] if ranking["Lãi/lỗ 7D %"].notna().any() else None

    # ---------------- Tổng quan thị trường: nhiều chỉ số ----------------
    section_title("📊", "Tổng quan thị trường", f"Thống kê nhanh trên {len(ranking)} coin đang so sánh.", anchor="tong-quan")
    r1 = st.columns(5)
    with r1[0]:
        kpi_card("🏆", "Coin đáng chú ý nhất", str(best["Coin"]), f'Điểm đầu tư {best["Điểm đầu tư"]:.1f}/100', "gold")
    with r1[1]:
        kpi_card("🛡️", "Rủi ro thấp nhất", str(worst_risk["Coin"]), f'Điểm rủi ro {worst_risk["Điểm rủi ro"]:.1f}/100', "cyan")
    with r1[2]:
        kpi_card("📈", "Tăng mạnh nhất 7D", str(top_gainer["Coin"]) if top_gainer is not None else "N/A", format_percent(top_gainer["Lãi/lỗ 7D %"]) if top_gainer is not None else "", "pos")
    with r1[3]:
        kpi_card("📉", "Giảm mạnh nhất 7D", str(top_loser["Coin"]) if top_loser is not None else "N/A", format_percent(top_loser["Lãi/lỗ 7D %"]) if top_loser is not None else "", "neg")
    with r1[4]:
        kpi_card("🪐", "Tổng số coin", str(len(ranking)), f"{len(errors)} coin lỗi tải dữ liệu" if errors else "Tải dữ liệu thành công", "violet")

    r2 = st.columns(5)
    with r2[0]:
        kpi_card("⚖️", "Điểm đầu tư trung bình", f"{avg_score:.1f}/100", None, "gold")
    with r2[1]:
        kpi_card("🔥", "Điểm rủi ro trung bình", f"{avg_risk:.1f}/100", None, "cyan")
    with r2[2]:
        kpi_card("✅", "Coin rủi ro thấp", f"{risk_low_count}/{len(ranking)}", "Điểm rủi ro ≤ 35", "pos")
    with r2[3]:
        kpi_card("📐", "Coin trên MA200", f"{above_ma_count}/{len(ranking)}", "Xu hướng trung — dài hạn tích cực", "violet")
    with r2[4]:
        tone = "pos" if (avg_7d or 0) >= 0 else "neg"
        kpi_card("🌪️", "Biến động 30D TB", f"{avg_vol30:.2f}%", f"Lãi/lỗ 7D TB: {format_percent(avg_7d)}", tone)

    # ---------------- Gauge + donut: "đo" trực quan ----------------
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.plotly_chart(gauge_fig(avg_score, "Điểm đầu tư trung bình", CYAN), width="stretch")
    with g2:
        st.plotly_chart(gauge_fig(avg_risk, "Điểm rủi ro trung bình", GOLD), width="stretch")
    with g3:
        decision_counts = ranking["Kết luận"].value_counts()
        st.plotly_chart(
            donut_fig(
                decision_counts.index.to_list(),
                decision_counts.to_list(),
                [GREEN, GOLD, VIOLET, RED][: len(decision_counts)],
                "Phân bố kết luận",
            ),
            width="stretch",
        )
    with g4:
        ma_counts = ranking["Xu hướng MA200"].value_counts()
        st.plotly_chart(
            donut_fig(ma_counts.index.to_list(), ma_counts.to_list(), [GREEN, RED], "Trên / Dưới MA200"),
            width="stretch",
        )

    # ---------------- Bảng xếp hạng ----------------
    section_title("🗂️", "Bảng đánh giá coin đáng đầu tư spot nhất", anchor="bang-xep-hang")
    optional_columns = [c for c in ranking.columns if c not in ("Hạng", "Coin")]
    default_columns = [
        "Giá spot",
        "Điểm đầu tư",
        "Điểm rủi ro",
        "Kết luận",
        "Xu hướng MA200",
        "Lãi/lỗ 7D %",
        "Lãi/lỗ 1Y %",
        "Cách ATH %",
        "Ổn định sự kiện",
    ]
    chosen_columns = st.multiselect(
        "Chọn cột muốn hiển thị trong bảng (Hạng & Coin luôn cố định)",
        options=optional_columns,
        default=[c for c in default_columns if c in optional_columns],
    )
    display_cols = ["Hạng", "Coin"] + chosen_columns
    if chosen_columns:
        render_glow_table(ranking[display_cols], display_cols, height=560)
    else:
        st.info("Hãy chọn ít nhất một cột để hiển thị bảng.")

    left, right = st.columns([1.1, 0.9])
    with left:
        fig_score = px.bar(
            ranking.head(25),
            x="Coin",
            y="Điểm đầu tư",
            color="Điểm rủi ro",
            color_continuous_scale=[RED, GOLD, GREEN],
            title="Top coin theo điểm đầu tư spot",
        )
        st.plotly_chart(style_fig(fig_score, height=430), width="stretch")

    with right:
        scatter = px.scatter(
            ranking,
            x="Điểm rủi ro",
            y="Điểm đầu tư",
            color="Xu hướng MA200",
            hover_name="Coin",
            size="Ổn định sự kiện",
            title="Ma trận rủi ro và cơ hội",
            color_discrete_map={"Trên MA200": GREEN, "Dưới MA200": RED},
        )
        st.plotly_chart(style_fig(scatter, height=430), width="stretch")

    # ---------------- So sánh nhiều coin & mô phỏng danh mục ----------------
    section_title(
        "📐",
        "So sánh nhiều coin & mô phỏng danh mục",
        "Chọn vài coin để xem hiệu suất chuẩn hoá cùng lúc, mức tương quan rủi ro, và thử nếu chia đều vốn vào các coin này thì so với chỉ giữ BTC sẽ ra sao.",
        anchor="so-sanh-danh-muc",
    )
    compare_default = [c for c in ranking["Coin"].head(6).to_list() if c in selected]
    compare_symbols = st.multiselect(
        "Chọn coin để so sánh (tối đa 10)",
        options=ranking["Coin"].to_list(),
        default=compare_default,
        max_selections=10,
    )
    compare_timeframe = st.segmented_control(
        "Khung thời gian so sánh",
        options=list(TIMEFRAMES.keys()),
        default="3M",
        key="compare_timeframe",
    )
    compare_timeframe = compare_timeframe or "3M"

    if len(compare_symbols) < 2:
        st.info("Chọn ít nhất 2 coin để so sánh hiệu suất và tương quan.")
    else:
        matrix = build_price_matrix(histories, compare_symbols, compare_timeframe)
        if matrix.empty or len(matrix) < 3:
            st.warning(
                "Không đủ dữ liệu chung giữa các coin đã chọn trong khung thời gian này "
                "(thường do có coin mới niêm yết, chưa đủ lịch sử khớp với khung đã chọn)."
            )
        else:
            norm = normalized_performance(matrix)
            portfolio = norm.mean(axis=1)

            btc_view = slice_timeframe(histories["BTCUSDT"].sort_values("timestamp"), compare_timeframe)
            btc_norm = None
            if len(btc_view) >= 2:
                btc_close = btc_view.set_index("timestamp")["close"]
                btc_norm = (btc_close / btc_close.iloc[0] - 1) * 100

            portfolio_final = float(portfolio.iloc[-1])
            btc_final = float(btc_norm.iloc[-1]) if btc_norm is not None else None
            last_row = norm.iloc[-1]
            best_symbol, worst_symbol = last_row.idxmax(), last_row.idxmin()

            cmp1, cmp2, cmp3, cmp4 = st.columns(4)
            with cmp1:
                tone = "pos" if portfolio_final >= 0 else "neg"
                kpi_card("📐", f"Danh mục chia đều {compare_timeframe}", format_percent(portfolio_final), f"{len(compare_symbols)} coin, vốn chia đều", tone)
            with cmp2:
                if btc_final is not None:
                    tone = "pos" if btc_final >= 0 else "neg"
                    kpi_card("🟡", f"Nếu chỉ giữ BTC {compare_timeframe}", format_percent(btc_final), "Tham chiếu so sánh", tone)
                else:
                    kpi_card("🟡", "Nếu chỉ giữ BTC", "N/A", None, "violet")
            with cmp3:
                kpi_card("🚀", "Đóng góp tốt nhất", str(best_symbol), format_percent(float(last_row[best_symbol])), "pos")
            with cmp4:
                kpi_card("🥶", "Đóng góp kém nhất", str(worst_symbol), format_percent(float(last_row[worst_symbol])), "neg")

            cmp_left, cmp_right = st.columns([1.3, 0.9])
            with cmp_left:
                fig_compare = compare_performance_fig(norm, portfolio, btc_norm)
                st.plotly_chart(
                    style_fig(fig_compare, height=440, title=f"Hiệu suất chuẩn hoá · {compare_timeframe} (mốc 0% = đầu kỳ)"),
                    width="stretch",
                )
            with cmp_right:
                st.plotly_chart(style_fig(correlation_fig(matrix), height=440), width="stretch")
                st.markdown(
                    '<div class="small-note">Xanh = tương quan âm/thấp (đa dạng hoá tốt) · Đỏ = tương quan cao (các coin gần như đi cùng nhịp, rủi ro tập trung).</div>',
                    unsafe_allow_html=True,
                )

    # ---------------- Biểu đồ 3D ----------------
    section_title(
        "🌌",
        "Không gian 3D: Rủi ro × Điểm đầu tư × Ổn định sự kiện",
        "Xoay/kéo biểu đồ để xem coin nào nằm ở vùng góc trên-trái (điểm cao, rủi ro thấp, ổn định tốt) — vùng lý tưởng nhất.",
        anchor="khong-gian-3d",
    )
    st.plotly_chart(scatter3d_fig(ranking), width="stretch")

    # ---------------- Heatmap mốc sự kiện (đã tách rõ + giải thích) ----------------
    event_df = pd.concat([table for table in event_tables if not table.empty], ignore_index=True) if event_tables else pd.DataFrame()
    section_title("⚡", "Phản ứng quanh halving, downtrend lớn và thiên nga đen", anchor="moc-su-kien")
    st.markdown(
        """
        <div class="small-note">
        Cách đọc: với mỗi mốc, lấy <b>giá 7 ngày trước</b> mốc làm gốc, rồi nhìn vào <b>45 ngày sau</b> mốc đó để đo —
        (1) <b>Sụt giảm xấu nhất</b>: đáy thấp nhất rơi bao nhiêu % so với giá gốc;
        (2) <b>Hồi phục sau mốc</b>: giá ở cuối 45 ngày đó so với giá gốc còn thiếu/đã vượt bao nhiêu %.
        Ô <span style="color:#94a3b8">xám nhạt</span> nghĩa là coin <b>chưa niêm yết trên Binance</b> tại thời điểm đó, không phải sụt giảm.
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not event_df.empty:
        with st.expander("Diễn giải từng mốc sự kiện"):
            for milestone in MILESTONES:
                st.markdown(f"**{milestone['name']}** ({milestone['date']}, *{milestone['type']}*) — {milestone['desc']}")

        h1, h2 = st.columns(2)
        with h1:
            drop_data = event_df.pivot_table(index="Coin", columns="Mốc", values="Sụt giảm xấu nhất %", aggfunc="mean")
            fig_drop = px.imshow(
                drop_data,
                color_continuous_scale=[RED, GOLD, "#fef3c7", GREEN],
                aspect="auto",
                title="Sụt giảm xấu nhất quanh từng sự kiện (%)",
            )
            fig_drop.update_layout(plot_bgcolor="rgba(148,163,184,0.12)")
            st.plotly_chart(style_fig(fig_drop, height=430), width="stretch")
        with h2:
            rec_data = event_df.pivot_table(index="Coin", columns="Mốc", values="Hồi phục sau mốc %", aggfunc="mean")
            fig_rec = px.imshow(
                rec_data,
                color_continuous_scale=[RED, GOLD, "#fef3c7", GREEN],
                aspect="auto",
                title="Hồi phục sau mốc, so với giá trước biến cố (%)",
            )
            fig_rec.update_layout(plot_bgcolor="rgba(148,163,184,0.12)")
            st.plotly_chart(style_fig(fig_rec, height=430), width="stretch")

        event_display = event_df.drop(columns=["score"]).copy()
        event_display = event_display.sort_values(["Mốc", "Sụt giảm xấu nhất %"], ascending=[True, False])
        event_columns = ["Coin", "Mốc", "Loại", "Ngày", "Sụt giảm xấu nhất %", "Hồi phục sau mốc %", "Giải thích"]
        render_glow_table(event_display, event_columns, height=380)
    else:
        st.info("Các coin đã chọn chưa có đủ lịch sử để so sánh theo mốc sự kiện.")

    # ---------------- Hồ sơ chi tiết từng coin + khung thời gian tự chọn ----------------
    section_title("🔬", "Hồ sơ chi tiết từng coin", anchor="chi-tiet-coin")
    detail_symbol = st.selectbox("Chọn coin để xem chart và hồ sơ", options=ranking["Coin"].to_list())
    detail_row = ranking[ranking["Coin"] == detail_symbol].iloc[0]
    detail_df = with_indicators(histories[detail_symbol])

    timeframe_key = st.segmented_control(
        "Khung thời gian biểu đồ",
        options=list(TIMEFRAMES.keys()),
        default="3M",
    )
    timeframe_key = timeframe_key or "3M"

    change, period_high, period_low, avg_volume = timeframe_return(detail_df, timeframe_key)
    last_row = detail_df.iloc[-1]

    d1, d2, d3, d4, d5, d6 = st.columns(6)
    with d1:
        kpi_card("💰", "Giá spot", format_price(float(detail_row["Giá spot"])), None, "cyan")
    with d2:
        tone = "pos" if (change or 0) >= 0 else "neg"
        kpi_card("📅", f"Lãi/lỗ {timeframe_key}", format_percent(change), None, tone)
    with d3:
        kpi_card("🔺", f"Cao nhất {timeframe_key}", format_price(period_high), None, "gold")
    with d4:
        kpi_card("🔻", f"Thấp nhất {timeframe_key}", format_price(period_low), None, "violet")
    with d5:
        rsi_value = float(last_row["rsi14"]) if not pd.isna(last_row["rsi14"]) else None
        rsi_tone = "neg" if rsi_value and rsi_value >= 70 else "pos" if rsi_value and rsi_value <= 30 else "cyan"
        kpi_card("🧭", "RSI (14)", f"{rsi_value:.1f}" if rsi_value is not None else "N/A", "Quá mua ≥70 · Quá bán ≤30", rsi_tone)
    with d6:
        macd_tone = "pos" if last_row["macd_hist"] >= 0 else "neg"
        kpi_card("⚙️", "MACD Histogram", f"{last_row['macd_hist']:.4g}", "Dương = đà tăng đang mạnh", macd_tone)

    st.plotly_chart(build_detail_chart(detail_df, detail_symbol, timeframe_key), width="stretch")

    st.warning(
        "Dashboard này chỉ dùng để nghiên cứu đầu tư spot. Không phải lời khuyên tài chính. "
        "Không futures, không đòn bẩy, không all-in. Dữ liệu 'từ khi niêm yết' là từ khi Binance có lịch sử giao dịch spot cho cặp đó."
    )


if __name__ == "__main__":
    main()
