import requests
import json
import time
import os
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ.get(“TELEGRAM_BOT_TOKEN”, “”)
TELEGRAM_CHAT_ID = os.environ.get(“TELEGRAM_CHAT_ID”, “”)

BITGET_API_KEY = os.environ.get(“BITGET_API_KEY”, “”)
BITGET_SECRET_KEY = os.environ.get(“BITGET_SECRET_KEY”, “”)
BITGET_PASSPHRASE = os.environ.get(“BITGET_PASSPHRASE”, “”)

UP_ALERT_PERCENT = 3
DOWN_ALERT_PERCENT = -3
NEAR_HIGH_PERCENT = 1
NEAR_LOW_PERCENT = 1

SIMULATE_TRADE = True
SIMULATE_AMOUNT_USDT = 90
STOP_LOSS_PERCENT = -3.0
TAKE_PROFIT_PERCENT = 5.0

SYMBOLS = [“BTCUSDT”, “ETHUSDT”, “PREOPAIUSDT”]

sim_positions = {}

def send_telegram(message):
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
print(“Telegram not configured”)
return
url = “https://api.telegram.org/bot” + TELEGRAM_BOT_TOKEN + “/sendMessage”
payload = {
“chat_id”: TELEGRAM_CHAT_ID,
“text”: message,
“parse_mode”: “HTML”
}
try:
resp = requests.post(url, json=payload, timeout=10)
if resp.status_code == 200:
print(“Telegram sent”)
else:
print(“Telegram failed: “ + resp.text)
except Exception as e:
print(“Telegram error: “ + str(e))

def get_ticker(symbol):
url = “https://api.bitget.com/api/v2/spot/market/tickers?symbol=” + symbol
try:
resp = requests.get(url, timeout=10)
data = resp.json()
if data.get(“code”) == “00000” and data.get(“data”):
return data[“data”][0]
except Exception as e:
print(“Ticker error “ + symbol + “: “ + str(e))
return None

def get_candles(symbol, granularity=“15min”, limit=20):
url = “https://api.bitget.com/api/v2/spot/market/candles?symbol=” + symbol + “&granularity=” + granularity + “&limit=” + str(limit)
try:
resp = requests.get(url, timeout=10)
data = resp.json()
if data.get(“code”) == “00000”:
return data.get(“data”, [])
except Exception as e:
print(“Candle error “ + symbol + “: “ + str(e))
return []

def analyze_candles(candles):
if not candles or len(candles) < 3:
return “資料不足”, 0, 0
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
trend = “偏多”
elif bear >= 3:
trend = “偏空”
else:
trend = “盤整”
return trend, support, resistance

def simulate_trade(symbol, price, trend, support, resistance):
now = datetime.now().strftime(”%Y-%m-%d %H:%M:%S”)
msg_lines = []

```
if symbol in sim_positions:
    pos = sim_positions[symbol]
    entry = pos["entry"]
    qty = pos["qty"]
    pnl_pct = (price - entry) / entry * 100
    pnl_usdt = (price - entry) * qty

    print("[" + symbol + "] 持倉中 買入價:" + str(entry) + " 現價:" + str(price) + " 損益:" + str(round(pnl_pct, 2)) + "%")

    if pnl_pct <= STOP_LOSS_PERCENT:
        msg_lines.append("🔴 <b>[模擬] " + symbol + " 止損出場</b>")
        msg_lines.append("買入價：" + str(round(entry, 4)) + " USDT")
        msg_lines.append("出場價：" + str(round(price, 4)) + " USDT")
        msg_lines.append("損益：" + str(round(pnl_pct, 2)) + "% (約 " + str(round(pnl_usdt, 2)) + " USDT)")
        msg_lines.append("時間：" + now)
        del sim_positions[symbol]
    elif pnl_pct >= TAKE_PROFIT_PERCENT:
        msg_lines.append("🟢 <b>[模擬] " + symbol + " 停利出場</b>")
        msg_lines.append("買入價：" + str(round(entry, 4)) + " USDT")
        msg_lines.append("出場價：" + str(round(price, 4)) + " USDT")
        msg_lines.append("損益：" + str(round(pnl_pct, 2)) + "% (約 " + str(round(pnl_usdt, 2)) + " USDT)")
        msg_lines.append("時間：" + now)
        del sim_positions[symbol]
    else:
        msg_lines.append("📊 <b>[模擬] " + symbol + " 持倉中</b>")
        msg_lines.append("買入價：" + str(round(entry, 4)) + " USDT")
        msg_lines.append("現價：" + str(round(price, 4)) + " USDT")
        msg_lines.append("損益：" + str(round(pnl_pct, 2)) + "% (約 " + str(round(pnl_usdt, 2)) + " USDT)")
        msg_lines.append("止損價：" + str(round(entry * (1 + STOP_LOSS_PERCENT / 100), 4)) + " | 停利價：" + str(round(entry * (1 + TAKE_PROFIT_PERCENT / 100), 4)))
else:
    if trend == "偏多":
        qty = SIMULATE_AMOUNT_USDT / price
        sim_positions[symbol] = {"entry": price, "qty": qty}
        sl_price = price * (1 + STOP_LOSS_PERCENT / 100)
        tp_price = price * (1 + TAKE_PROFIT_PERCENT / 100)
        msg_lines.append("🟡 <b>[模擬] " + symbol + " 買入訊號</b>")
        msg_lines.append("模擬買入價：" + str(round(price, 4)) + " USDT")
        msg_lines.append("模擬金額：" + str(SIMULATE_AMOUNT_USDT) + " USDT (約 " + str(SIMULATE_AMOUNT_USDT * 30) + " 台幣)")
        msg_lines.append("模擬數量：" + str(round(qty, 6)))
        msg_lines.append("止損價：" + str(round(sl_price, 4)) + " (-" + str(abs(STOP_LOSS_PERCENT)) + "%)")
        msg_lines.append("停利價：" + str(round(tp_price, 4)) + " (+" + str(TAKE_PROFIT_PERCENT) + "%)")
        msg_lines.append("時間：" + now)
    else:
        msg_lines.append("⚪ <b>[模擬] " + symbol + "</b> 無進場訊號 (" + trend + ")")

return "\n".join(msg_lines)
```

def analyze_symbol(symbol):
print(”\n========== “ + symbol + “ ==========”)

```
ticker = get_ticker(symbol)
if not ticker:
    print(symbol + " 無法取得資料")
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

if trend_15m == "偏多" and trend_1h == "偏多":
    overall = "偏多"
elif trend_15m == "偏空" and trend_1h == "偏空":
    overall = "偏空"
else:
    overall = "中性"

print("現價：" + str(price))
print("24h 漲跌：" + str(round(change_pct, 2)) + "%")
print("15m 趨勢：" + trend_15m + " | 1H 趨勢：" + trend_1h)
print("綜合判斷：" + overall)
print("模式：模擬交易")

should_notify = (
    change_pct >= UP_ALERT_PERCENT or
    change_pct <= DOWN_ALERT_PERCENT or
    near_high <= NEAR_HIGH_PERCENT or
    near_low <= NEAR_LOW_PERCENT or
    overall == "偏多"
)

if overall == "偏多":
    direction = "📈 偏多"
elif overall == "偏空":
    direction = "📉 偏空"
else:
    direction = "➡️ 中性"

report = "📌 <b>" + symbol + " 分析報告</b>\n"
report += "現價：" + str(round(price, 4)) + " USDT\n"
report += "24h 漲跌：" + str(round(change_pct, 2)) + "%\n"
report += "24h 高點：" + str(round(high_24h, 4)) + " | 低點：" + str(round(low_24h, 4)) + "\n"
report += "\n📊 K棒分析\n"
report += "15m 趨勢：" + trend_15m + " | 1H 趨勢：" + trend_1h + "\n"
report += "短線支撐：" + str(round(support_15m, 4)) + "\n"
report += "短線壓力：" + str(round(resistance_15m, 4)) + "\n"
report += "\n🎯 綜合判斷：" + direction

sim_report = ""
if SIMULATE_TRADE:
    sim_report = simulate_trade(symbol, price, overall, support_15m, resistance_15m)
    print("\n[模擬下單]\n" + sim_report)

full_message = report
if sim_report:
    full_message += "\n\n" + sim_report

return should_notify, full_message
```

def main():
print(”===== Crypto Alert 啟動 =====”)
print(“模式：模擬交易”)
print(“監控：” + str(SYMBOLS))
print(“模擬金額：” + str(SIMULATE_AMOUNT_USDT) + “ USDT | 止損：” + str(STOP_LOSS_PERCENT) + “% | 停利：” + str(TAKE_PROFIT_PERCENT) + “%”)

```
for symbol in SYMBOLS:
    try:
        should_notify, message = analyze_symbol(symbol)
        if should_notify and message:
            send_telegram(message)
            time.sleep(1)
    except Exception as e:
        print(symbol + " 錯誤：" + str(e))

print("\n===== 分析完成 =====")
```

if **name** == “**main**”:
main()
