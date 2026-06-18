# AI Trading Bot

Bot demo cho crypto, ưu tiên BTC/USDT. Dự án này tập trung vào an toàn: backtest, paper trading, risk engine và AI reasoning dạng rule-based trước. Live trading mặc định bị khóa.

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy nhanh

Backtest bằng dữ liệu demo tự sinh:

```bash
python -m src.main --mode backtest --symbol BTCUSDT
```

Phân tích chart và trả JSON quyết định:

```bash
python -m src.main --mode analysis --symbol BTCUSDT
```

Paper trading demo:

```bash
python -m src.main --mode paper --symbol BTCUSDT
```

Dashboard so sánh đầu tư spot:

```bash
streamlit run src/dashboard/app.py
```

Dashboard dùng Binance Spot public API để:

- Chọn tối đa 50 cặp spot USDT.
- So sánh lãi/lỗ 7D, 30D, Quý, 180D, 1 năm, 2 năm và từ khi niêm yết trên Binance.
- Chấm điểm rủi ro, điểm đầu tư, xu hướng MA200, drawdown từ ATH, max drawdown và biến động 30D.
- So sánh sức mạnh tương đối với BTC.
- Đánh giá phản ứng quanh các mốc lớn như BTC halving, COVID crash, LUNA/UST, FTX và downtrend lớn.
- Xếp hạng coin đáng nghiên cứu đầu tư spot nhất.

## Nguyên tắc an toàn

- Không all-in.
- Không martingale.
- Không DCA vô kiểm soát.
- Risk mỗi lệnh mặc định 0.5%, bị chặn nếu vượt 1% khi chưa cấu hình rõ.
- Max daily loss 2%, max weekly loss 5%.
- Thua 3 lệnh liên tiếp thì kill switch chuyển sang quan sát.
- Live trading không hoạt động nếu `LIVE_TRADING_ENABLED=false`.

## Cấu trúc

```text
src/
  data/          dữ liệu, exchange client demo
  indicators/    EMA, MACD, RSI, ATR, SAR
  structure/     swing, BOS, CHoCH, market structure
  smc/           order block, FVG, liquidity, premium/discount
  wyckoff/       phase, spring/upthrust, volume
  ai_brain/      reasoning engine và JSON decision
  risk/          risk manager, sizing, SL/TP, kill switch
  execution/     paper/live trader
  backtest/      engine và metrics
  dashboard/     Streamlit dashboard
```

## Lưu ý

Đây là framework kỹ thuật để test và mở rộng, không phải lời khuyên tài chính. Các module SMC/Wyckoff ban đầu là heuristic có thể kiểm chứng, không phải mô hình AI tự học.
