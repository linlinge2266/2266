import requests
import json
import time
import hmac
import hashlib
import os
from datetime import datetime

# ========== Telegram 設定 ==========

TELEGRAM_BOT_TOKEN = os.environ.get(“TELEGRAM_BOT_TOKEN”, “”)
TELEGRAM_CHAT_ID = os.environ.get(“TELEGRAM_CHAT_ID”, “”)

# ========== Bitget API 設定（模擬模式不需要真實下單）==========

BITGET_API_KEY = os.environ.get(“BITGET_API_KEY”, “”)
BITGET_SECRET_KEY = os.environ.get(“BITGET_SECRET_KEY”, “”)
BITGET_PASSPHRASE = os.environ.get(“BITGET_PASSPHRASE”, “”)

# ========== 通知條件 ==========

UP_ALERT_PERCENT = 3
DOWN_ALERT_PERCENT = -3
NEAR_HIGH_PERCENT = 1
NEAR_LOW_PERCENT = 1

# ========== 模擬下單設定 ==========

SIMULATE_TRADE = True          # True = 模擬模式，不真實下單
SIMULATE_AMOUNT_USDT = 90      # 每次模擬買入金額（約 3000 台幣）
STOP_LOSS_PERCENT = -3.0       # 止損 -3%
TAKE_PROFIT_PERCENT = 5.0      # 停利 +5%

# ========== 監控交易對 ==========

SYMBOLS = [“BTCUSDT”, “ETHUSDT”, “PREOPAIUSDT”]

# ========== 模擬倉位記錄（當次執行）==========

sim_positions = {}

def send_telegram(message):
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
print(“Telegram 未設定，跳過通知”)
return
url = f”https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage”
payload = {
“chat_id”: TELEGRAM_CHAT_ID,
“text”: message,
“parse_mode”: “HTML”
}
try:
resp = requests.post(url, json=payload, timeout=10)
if resp.status_code == 200:
print(“Telegram 通知已發送”)
else:
print(f”Telegram 發送失敗：{resp.text}”)
except Exception as e:
print(f”Telegram 錯誤：{e}”)

def get_ticker(symbol):
url = f”https://api.bitget.com/api/v2/spot/market/tickers?symbol={symbol}”
try:
resp = requests.get(url, timeout=10)
data = resp.json()
if data.get(“code”) == “00000” and data.get(“data”):
return data[“data”][0]
except Exception as e:
print(f”取得 {symbol} ticker 失敗：{e}”)
return None

def get_candles(symbol, granularity=“15min”, limit=20):
url = f”https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}”
try:
resp = requests.get(url, timeout=10)
data = resp.json()
if data.get(“code”) == “00000”:
return data.get(“data”, [])
except Exception as e:
print(f”取得 {symbol} K線失敗：{e}”)
return []

def analyze_candles(candles):
if not candles or len(candles) < 3:
return “資料不足”, 0, 0

```
bull = 0
bear = 0
for c in candles[-5:]:
    open_p = float(c[1])
    close_p = float(c[4])
    if close_p > open_p:
        bull += 1
    elif close_p < open_p:
        bear += 1

lows = [float(c[3]) for c in candles]
highs = [float(c[2]) for c in candles]
support = min(lows[-5:])
resistance = max(highs[-5:])

if bull >= 3:
    trend = "偏多"
elif bear >= 3:
    trend = "偏空"
else:
    trend = "盤整"

return trend, support, resistance
```

def simulate_trade(symbol, price, trend, support, resistance):
now = datetime.now().strftime(”%Y-%m-%d %H:%M:%S”)
msg_lines = []

```
# 檢查是否已有模擬倉位
if symbol in sim_positions:
    pos = sim_positions[symbol]
    entry = pos["entry"]
    qty = pos["qty"]
    pnl_pct = (price - entry) / entry * 100
    pnl_usdt = (price - entry) * qty

    print(f"[{symbol}] 持有模擬倉位 | 買入價:{entry:.4f} | 現價:{price:.4f} | 損益:{pnl_pct:.2f}%")

    if pnl_pct <= STOP_LOSS_PERCENT:
        msg_lines.append(f"🔴 <b>[模擬] {symbol} 止損出場</b>")
        msg_lines.append(f"買入價：{entry:.4f} USDT")
        msg_lines.append(f"出場價：{price:.4f} USDT")
        msg_lines.append(f"損益：{pnl_pct:.2f}%（約 {pnl_usdt:.2f} USDT）")
        msg_lines.append(f"時間：{now}")
        del sim_positions[symbol]
    elif pnl_pct >= TAKE_PROFIT_PERCENT:
        msg_lines.append(f"🟢 <b>[模擬] {symbol} 停利出場</b>")
        msg_lines.append(f"買入價：{entry:.4f} USDT")
        msg_lines.append(f"出場價：{price:.4f} USDT")
        msg_lines.append(f"損益：{pnl_pct:.2f}%（約 {pnl_usdt:.2f} USDT）")
        msg_lines.append(f"時間：{now}")
        del sim_positions[symbol]
    else:
        msg_lines.append(f"📊 <b>[模擬] {symbol} 持倉中</b>")
        msg_lines.append(f"買入價：{entry:.4f} USDT")
        msg_lines.append(f"現價：{price:.4f} USDT")
        msg_lines.append(f"目前損益：{pnl_pct:.2f}%（約 {pnl_usdt:.2f} USDT）")
        msg_lines.append(f"止損價：{entry * (1 + STOP_LOSS_PERCENT/100):.4f} | 停利價：{entry * (1 + TAKE_PROFIT_PERCENT/100):.4f}")

else:
    # 沒有倉位，判斷是否進場
    if trend == "偏多":
        qty = SIMULATE_AMOUNT_USDT / price
        sim_positions[symbol] = {"entry": price, "qty": qty}
        sl_price = price * (1 + STOP_LOSS_PERCENT / 100)
        tp_price = price * (1 + TAKE_PROFIT_PERCENT / 100)

        msg_lines.append(f"🟡 <b>[模擬] {symbol} 買入訊號</b>")
        msg_lines.append(f"模擬買入價：{price:.4f} USDT")
        msg_lines.append(f"模擬金額：{SIMULATE_AMOUNT_USDT} USDT（約 {SIMULATE_AMOUNT_USDT * 30:.0f} 台幣）")
        msg_lines.append(f"模擬數量：{qty:.6f}")
        msg_lines.append(f"止損價：{sl_price:.4f}（-{abs(STOP_LOSS_PERCENT)}%）")
        msg_lines.append(f"停利價：{tp_price:.4f}（+{TAKE_PROFIT_PERCENT}%）")
        msg_lines.append(f"時間：{now}")
    else:
        msg_lines.append(f"⚪ <b>[模擬] {symbol}</b> 無進場訊號（{trend}）")

return "\n".join(msg_lines)
```

def analyze_symbol(symbol):
print(f”\n========== {symbol} ==========”)

```
ticker = get_ticker(symbol)
if not ticker:
    print(f"{symbol} 無法取得資料")
    return False, ""

price = float(ticker.get("lastPr", 0))
change_pct = float(ticker.get("change24h", 0)) * 100
high_24h = float(ticker.get("high24h", 0))
low_24h = float(ticker.get("low24h", 0))
volume = float(ticker.get("baseVolume", 0))

near_high = ((high_24h - price) / high_24h * 100) if high_24h > 0 else 999
near_low = ((price - low_24h) / low_24h * 100) if low_24h > 0 else 999

candles_15m = get_candles(symbol, "15min", 20)
candles_1h = get_candles(symbol, "1H", 20)

trend_15m, support_15m, resistance_15m = analyze_candles(candles_15m)
trend_1h, support_1h, resistance_1h = analyze_candles(candles_1h)

# 綜合判斷
if trend_15m == "偏多" and trend_1h == "偏多":
    overall = "偏多"
elif trend_15m == "偏空" and trend_1h == "偏空":
    overall = "偏空"
else:
    overall = "中性"

print(f"現價：{price}")
print(f"24h 漲跌：{change_pct:.2f}%")
print(f"24h 高點：{high_24h} | 低點：{low_24h}")
print(f"15m K棒趨勢：{trend_15m} | 1H K棒趨勢：{trend_1h}")
print(f"短線支撐：{support_15m:.4f} | 短線壓力：{resistance_15m:.4f}")
print(f"綜合判斷：{overall}")
print(f"距24h高點：{near_high:.2f}% | 距24h低點：{near_low:.2f}%")

# 判斷是否觸發通知條件
should_notify = (
    change_pct >= UP_ALERT_PERCENT or
    change_pct <= DOWN_ALERT_PERCENT or
    near_high <= NEAR_HIGH_PERCENT or
    near_low <= NEAR_LOW_PERCENT or
    overall == "偏多"
)

# 組合分析訊息
direction = "📈 偏多" if overall == "偏多" else ("📉 偏空" if overall == "偏空" else "➡️ 中性")

report = f"""
```

📌 <b>{symbol} 分析報告</b>
現價：{price:.4f} USDT
24h 漲跌：{change_pct:.2f}%
24h 高點：{high_24h:.4f} | 低點：{low_24h:.4f}
成交量：{volume:.2f}

📊 K棒分析
15m 趨勢：{trend_15m} | 1H 趨勢：{trend_1h}
短線支撐：{support_15m:.4f}
短線壓力：{resistance_15m:.4f}

🎯 綜合判斷：{direction}
距24h高點：{near_high:.2f}% | 距24h低點：{near_low:.2f}%
“””.strip()

```
# 模擬下單分析
sim_report = ""
if SIMULATE_TRADE:
    sim_report = simulate_trade(symbol, price, overall, support_15m, resistance_15m)
    print(f"\n[模擬下單]\n{sim_report}")

full_message = report
if sim_report:
    full_message += "\n\n" + sim_report

return should_notify, full_message
```

def main():
print(”===== Crypto Alert 啟動 =====”)
print(f”模式：{‘🟡 模擬交易’ if SIMULATE_TRADE else ‘🔴 真實交易’}”)
print(f”監控：{SYMBOLS}”)
print(f”模擬金額：{SIMULATE_AMOUNT_USDT} USDT | 止損：{STOP_LOSS_PERCENT}% | 停利：{TAKE_PROFIT_PERCENT}%”)

```
for symbol in SYMBOLS:
    try:
        should_notify, message = analyze_symbol(symbol)
        if should_notify and message:
            send_telegram(message)
            time.sleep(1)
    except Exception as e:
        print(f"{symbol} 分析錯誤：{e}")

print("\n===== 分析完成 =====")
```

if **name** == “**main**”:
main()
