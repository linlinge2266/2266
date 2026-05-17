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
# 漲超過 3% 會通知
# 跌超過 -3% 會通知
UP_ALERT_PERCENT = 3
DOWN_ALERT_PERCENT = -3

# 多空觀察門檻
# 只是文字分析，不會自動下單
LONG_SIGNAL_PERCENT = 2
SHORT_SIGNAL_PERCENT = -2


def send_telegram_message(text):
    """
    發送 Telegram 通知
    """
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
    """
    從 Bitget 取得現貨 ticker 資料
    """
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

    # Bitget 回傳的 24 小時漲跌，有些交易對可能欄位名稱不同
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


def get_signal(change_24h):
    """
    根據 24 小時漲跌幅，給出簡單多空觀察
    注意：這不是自動交易，不會下單
    """
    if change_24h >= LONG_SIGNAL_PERCENT:
        return "偏多觀察：24 小時漲幅較強，但不代表一定要追多。"
    elif change_24h <= SHORT_SIGNAL_PERCENT:
        return "偏空觀察：24 小時跌幅較大，但不代表一定要追空。"
    else:
        return "中性觀察：目前沒有明顯多空方向。"


def format_price(price):
    """
    價格格式化
    BTC / ETH 價格大，preOPAI 價格可能需要小數
    """
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:,.4f}"
    else:
        return f"${price:,.8f}"


def main():
    alerts = []
    report_lines = []

    report_lines.append("📊 Bitget 加密貨幣監控")
    report_lines.append("")
    report_lines.append("監控幣種：BTC / ETH / preOPAI")
    report_lines.append("")

    for name, symbol in SYMBOLS.items():
        try:
            price, change_24h, high_24h, low_24h, volume_24h, quote_volume_24h = get_bitget_ticker(symbol)

            signal = get_signal(change_24h)

            coin_message = (
                f"{name} / USDT\n"
                f"交易對：{symbol}\n"
                f"目前價格：{format_price(price)}\n"
                f"24 小時漲跌：{change_24h:.2f}%\n"
                f"24 小時高點：{format_price(high_24h)}\n"
                f"24 小時低點：{format_price(low_24h)}\n"
                f"24 小時成交量：{volume_24h:,.4f} {name}\n"
                f"24 小時成交額：${quote_volume_24h:,.2f}\n"
                f"多空判斷：{signal}\n"
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

        except Exception as e:
            error_message = (
                f"{name} / {symbol}\n"
                f"抓取失敗：{e}\n"
            )
            report_lines.append(error_message)

    report_lines.append("提醒：這不是投資建議，請自行控管風險。")
    full_report = "\n".join(report_lines)

    if alerts:
        final_message = (
            "\n\n--------------------\n\n".join(alerts)
            + "\n\n提醒：這不是投資建議，請自行控管風險。"
        )
        send_telegram_message(final_message)
    else:
        print(full_report)
        print("沒有達到 Telegram 通知條件。")


if __name__ == "__main__":
    main()