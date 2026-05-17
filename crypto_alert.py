import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 監控幣種：BTC / ETH / preOPAI
SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "preOPAI": "PREOPAIUSDT",
}

# Telegram 通知門檻
UP_ALERT_PERCENT = 3
DOWN_ALERT_PERCENT = -3

# 接近高點 / 低點通知門檻
NEAR_HIGH_PERCENT = 1
NEAR_LOW_PERCENT = 1

# 止損 / 停利參考百分比
STOP_LOSS_PERCENT = 2
TAKE_PROFIT_1_PERCENT = 3
TAKE_PROFIT_2_PERCENT = 5


def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }

    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()


def get_bitget_ticker(symbol):
    url = "https://api.bitget.com/api/v2/spot/market/tickers"

    params = {
        "symbol": symbol
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    result = response.json()

    if result.get("code") != "00000":
        raise ValueError(f"Bitget API error for {symbol}: {result}")

    data = result.get("data", [])

    if not data:
        raise ValueError(f"No ticker data found for {symbol}")

    ticker = data[0]

    price = float(ticker["lastPr"])

    if "change24h" in ticker:
        change_24h = float(ticker["change24h"]) * 100
    elif "changeUtc24h" in ticker:
        change_24h = float(ticker["changeUtc24h"]) * 100
    else:
        change_24h = 0.0

    high_24h = float(ticker.get("high24h", 0))
    low_24h = float(ticker.get("low24h", 0))
    volume_24h = float(ticker.get("baseVolume", 0))
    quote_volume_24h = float(ticker.get("quoteVolume", 0))

    return price, change_24h, high_24h, low_24h, volume_24h, quote_volume_24h


def get_bitget_candles(symbol, granularity="15min", limit=20):
    url = "https://api.bitget.com/api/v2/spot/market/candles"

    params = {
        "symbol": symbol,
        "granularity": granularity,
        "limit": limit
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    result = response.json()

    if result.get("code") != "00000":
        raise ValueError(f"Bitget candle API error for {symbol}: {result}")

    candles = result.get("data", [])

    if not candles:
        raise ValueError(f"No candle data found for {symbol}")

    parsed = []

    for candle in candles:
        # Bitget K線通常格式：
        # [timestamp, open, high, low, close, baseVolume, quoteVolume]
        parsed.append({
            "time": candle[0],
            "open": float(candle[1]),
            "high": float(candle[2]),
            "low": float(candle[3]),
            "close": float(candle[4]),
            "base_volume": float(candle[5]) if len(candle) > 5 else 0.0,
            "quote_volume": float(candle[6]) if len(candle) > 6 else 0.0,
        })

    return parsed


def format_price(price):
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:,.4f}"
    else:
        return f"${price:,.8f}"


def calculate_distance_from_high(price, high_24h):
    if high_24h <= 0:
        return 0.0

    return ((price - high_24h) / high_24h) * 100


def calculate_distance_from_low(price, low_24h):
    if low_24h <= 0:
        return 0.0

    return ((price - low_24h) / low_24h) * 100


def analyze_candles(candles, label):
    if len(candles) < 5:
        return {
            "summary": f"{label}：K棒數量不足，暫時無法分析。",
            "support": 0.0,
            "resistance": 0.0,
            "last_color": "未知",
            "trend": "未知"
        }

    recent = candles[-5:]
    last = candles[-1]

    red_count = 0
    green_count = 0

    for candle in recent:
        if candle["close"] > candle["open"]:
            red_count += 1
        elif candle["close"] < candle["open"]:
            green_count += 1

    if last["close"] > last["open"]:
        last_color = "紅K"
    elif last["close"] < last["open"]:
        last_color = "綠K"
    else:
        last_color = "十字K"

    support = min(candle["low"] for candle in recent)
    resistance = max(candle["high"] for candle in recent)

    first_close = recent[0]["close"]
    last_close = recent[-1]["close"]

    if last_close > first_close and red_count >= 3:
        trend = "偏多"
        summary = f"{label}：最近 5 根K棒偏多，紅K較多，短線買盤較強。"
    elif last_close < first_close and green_count >= 3:
        trend = "偏空"
        summary = f"{label}：最近 5 根K棒偏空，綠K較多，短線賣壓較重。"
    elif red_count > green_count:
        trend = "中性偏多"
        summary = f"{label}：紅K略多，短線中性偏多。"
    elif green_count > red_count:
        trend = "中性偏空"
        summary = f"{label}：綠K略多，短線中性偏空。"
    else:
        trend = "盤整"
        summary = f"{label}：紅K綠K接近，短線偏盤整。"

    return {
        "summary": summary,
        "support": support,
        "resistance": resistance,
        "last_color": last_color,
        "trend": trend
    }


def get_main_signal(change_24h, distance_high, distance_low, candle_15m, candle_1h):
    bullish_score = 0
    bearish_score = 0

    if change_24h >= 3:
        bullish_score += 1

    if change_24h <= -3:
        bearish_score += 1

    if distance_high >= -1:
        bullish_score += 1

    if distance_low <= 1:
        bearish_score += 1

    if candle_15m["trend"] in ["偏多", "中性偏多"]:
        bullish_score += 1

    if candle_15m["trend"] in ["偏空", "中性偏空"]:
        bearish_score += 1

    if candle_1h["trend"] in ["偏多", "中性偏多"]:
        bullish_score += 1

    if candle_1h["trend"] in ["偏空", "中性偏空"]:
        bearish_score += 1

    if bullish_score >= bearish_score + 2:
        return "偏多觀察：短線條件偏多，但不代表一定要追多。"
    elif bearish_score >= bullish_score + 2:
        return "偏空觀察：短線條件偏空，但不代表一定要追空。"
    elif bullish_score > bearish_score:
        return "中性偏多：略偏多，但方向還不夠強。"
    elif bearish_score > bullish_score:
        return "中性偏空：略偏空，但方向還不夠強。"
    else:
        return "中性觀察：目前多空條件接近，先觀察比較安全。"


def get_risk_note(change_24h, distance_high, distance_low):
    if change_24h >= 5:
        return "提醒：24 小時漲幅已大，不建議無腦追高，可以等回踩或突破確認。"

    if change_24h >= 3:
        return "提醒：24 小時漲幅較強，但不代表一定要追多，注意追高風險。"

    if change_24h <= -5:
        return "提醒：24 小時跌幅已大，不建議無腦追空，也不要急著抄底。"

    if change_24h <= -3:
        return "提醒：24 小時跌幅較大，但不代表一定要追空，注意反彈風險。"

    if distance_high >= -1:
        return "提醒：價格接近 24 小時高點，可能突破，也可能遇到壓力。"

    if distance_low <= 1:
        return "提醒：價格接近 24 小時低點，可能反彈，也可能繼續破底。"

    return "提醒：目前沒有明顯單邊方向，不急著追多或追空。"


def build_trade_levels(price, high_24h, low_24h, support, resistance):
    long_breakout_price = max(high_24h, resistance)
    short_breakdown_price = min(low_24h, support)

    long_stop_by_percent = price * (1 - STOP_LOSS_PERCENT / 100)
    short_stop_by_percent = price * (1 + STOP_LOSS_PERCENT / 100)

    long_tp_1 = price * (1 + TAKE_PROFIT_1_PERCENT / 100)
    long_tp_2 = price * (1 + TAKE_PROFIT_2_PERCENT / 100)

    short_tp_1 = price * (1 - TAKE_PROFIT_1_PERCENT / 100)
    short_tp_2 = price * (1 - TAKE_PROFIT_2_PERCENT / 100)

    return {
        "long_breakout_price": long_breakout_price,
        "long_stop": long_stop_by_percent,
        "long_tp_1": long_tp_1,
        "long_tp_2": long_tp_2,
        "short_breakdown_price": short_breakdown_price,
        "short_stop": short_stop_by_percent,
        "short_tp_1": short_tp_1,
        "short_tp_2": short_tp_2,
    }


def main():
    alerts = []
    report_lines = []

    report_lines.append("📊 Bitget 加密貨幣完整分析")
    report_lines.append("")
    report_lines.append("監控幣種：BTC / ETH / preOPAI")
    report_lines.append("模式：分析提醒，不自動下單")
    report_lines.append("")

    for name, symbol in SYMBOLS.items():
        try:
            price, change_24h, high_24h, low_24h, volume_24h, quote_volume_24h = get_bitget_ticker(symbol)

            candles_15m = get_bitget_candles(symbol, "15min", 20)
            candles_1h = get_bitget_candles(symbol, "1h", 20)

            candle_15m = analyze_candles(candles_15m, "15分K")
            candle_1h = analyze_candles(candles_1h, "1小時K")

            distance_high = calculate_distance_from_high(price, high_24h)
            distance_low = calculate_distance_from_low(price, low_24h)

            support = min(candle_15m["support"], candle_1h["support"])
            resistance = max(candle_15m["resistance"], candle_1h["resistance"])

            signal = get_main_signal(change_24h, distance_high, distance_low, candle_15m, candle_1h)
            risk_note = get_risk_note(change_24h, distance_high, distance_low)

            levels = build_trade_levels(price, high_24h, low_24h, support, resistance)

            coin_message = (
                f"📌 {name} / USDT\n"
                f"交易對：{symbol}\n"
                f"目前價格：{format_price(price)}\n"
                f"24 小時漲跌：{change_24h:.2f}%\n"
                f"24 小時高點：{format_price(high_24h)}\n"
                f"24 小時低點：{format_price(low_24h)}\n"
                f"距離高點：{distance_high:.2f}%\n"
                f"距離低點：+{distance_low:.2f}%\n"
                f"24 小時成交量：{volume_24h:,.4f} {name}\n"
                f"24 小時成交額：${quote_volume_24h:,.2f}\n"
                f"\n"
                f"📈 K棒分析\n"
                f"{candle_15m['summary']}\n"
                f"15分K最新：{candle_15m['last_color']}\n"
                f"{candle_1h['summary']}\n"
                f"1小時K最新：{candle_1h['last_color']}\n"
                f"短線支撐：{format_price(support)}\n"
                f"短線壓力：{format_price(resistance)}\n"
                f"\n"
                f"🟢 做多觀察\n"
                f"突破觀察價：{format_price(levels['long_breakout_price'])}\n"
                f"止損參考：{format_price(levels['long_stop'])}\n"
                f"停利參考：{format_price(levels['long_tp_1'])} / {format_price(levels['long_tp_2'])}\n"
                f"\n"
                f"🔴 做空觀察\n"
                f"跌破觀察價：{format_price(levels['short_breakdown_price'])}\n"
                f"止損參考：{format_price(levels['short_stop'])}\n"
                f"停利參考：{format_price(levels['short_tp_1'])} / {format_price(levels['short_tp_2'])}\n"
                f"\n"
                f"短線判斷：{signal}\n"
                f"{risk_note}\n"
            )

            report_lines.append(coin_message)

            if change_24h >= UP_ALERT_PERCENT:
                alerts.append(
                    f"🚀 {name} 24 小時漲超過 {UP_ALERT_PERCENT}%\n\n"
                    f"{coin_message}"
                )

            elif change_24h <= DOWN_ALERT_PERCENT:
                alerts.append(
                    f"🚨 {name} 24 小時跌超過 {abs(DOWN_ALERT_PERCENT)}%\n\n"
                    f"{coin_message}"
                )

            elif distance_high >= -NEAR_HIGH_PERCENT:
                alerts.append(
                    f"⚠️ {name} 接近 24 小時高點\n\n"
                    f"{coin_message}"
                )

            elif distance_low <= NEAR_LOW_PERCENT:
                alerts.append(
                    f"⚠️ {name} 接近 24 小時低點\n\n"
                    f"{coin_message}"
                )

        except Exception as e:
            error_message = (
                f"❌ {name} / {symbol}\n"
                f"抓取失敗：{e}\n"
            )
            report_lines.append(error_message)

    report_lines.append("提醒：這不是投資建議，請自行控管風險。")

    full_report = "\n".join(report_lines)

    print(full_report)

    if alerts:
        final_message = (
            "\n\n--------------------\n\n".join(alerts)
            + "\n\n提醒：這不是投資建議，請自行控管風險。"
        )
        send_telegram_message(final_message)
    else:
        print("")
        print("沒有達到 Telegram 通知條件。")


if __name__ == "__main__":
    main()