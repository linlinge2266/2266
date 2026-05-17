import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH"
}

VS_CURRENCY = "usd"
ALERT_PERCENT = 3


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()


def get_crypto_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(COINS.keys()),
        "vs_currencies": VS_CURRENCY,
        "include_24hr_change": "true"
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    data = get_crypto_prices()
    messages = []

    for coin_id, symbol in COINS.items():
        price = data[coin_id][VS_CURRENCY]
        change_24h = data[coin_id][f"{VS_CURRENCY}_24h_change"]

        message = (
            f"📊 {symbol} 價格提醒\n\n"
            f"目前價格：${price:,.2f}\n"
            f"24 小時漲跌：{change_24h:.2f}%\n"
        )

        if change_24h <= -ALERT_PERCENT:
            messages.append(f"🚨 {symbol} 24 小時跌超過 {ALERT_PERCENT}%\n\n" + message)
        elif change_24h >= ALERT_PERCENT:
            messages.append(f"🚀 {symbol} 24 小時漲超過 {ALERT_PERCENT}%\n\n" + message)
        else:
            print(message)
            print("沒有達到通知條件。")

    if messages:
        final_message = "\n--------------------\n".join(messages)
        final_message += "\n\n提醒：這不是投資建議，請自行控管風險。"
        send_telegram_message(final_message)
    else:
        print("BTC 和 ETH 都沒有達到通知條件。")


if __name__ == "__main__":
    main()