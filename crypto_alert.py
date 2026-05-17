import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

COIN_ID = "bitcoin"
VS_CURRENCY = "usd"


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()


def get_bitcoin_price():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": COIN_ID,
        "vs_currencies": VS_CURRENCY,
        "include_24hr_change": "true"
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    price = data[COIN_ID][VS_CURRENCY]
    change_24h = data[COIN_ID][f"{VS_CURRENCY}_24h_change"]

    return price, change_24h


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    price, change_24h = get_bitcoin_price()

    message = (
        "📊 BTC 價格提醒\n\n"
        f"目前價格：${price:,.2f}\n"
        f"24 小時漲跌：{change_24h:.2f}%\n\n"
        "提醒：這不是投資建議，請自行控管風險。"
    )

    if change_24h <= -3:
        send_telegram_message("🚨 BTC 24 小時跌超過 3%\n\n" + message)
    elif change_24h >= 3:
        send_telegram_message("🚀 BTC 24 小時漲超過 3%\n\n" + message)
    else:
        print(message)
        print("沒有達到通知條件。")


if __name__ == "__main__":
    main()