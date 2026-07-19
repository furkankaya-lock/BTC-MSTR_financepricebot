import os
import time
import logging

import requests

# --------------------------------------------------------------------------
# LOG AYARLARI
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# AYARLAR (Token ve kanal bilgisi ORTAM DEĞİŞKENİ olarak Railway'de girilir,
# kod içine YAZILMAZ — güvenlik için)
# --------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")  # örn: @finance_ServisAcademy
INTERVAL_SECONDS = 180  # 3 dakika

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
CRYPTO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
STOCK_API_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# --------------------------------------------------------------------------
# TAKİP EDİLECEK VARLIKLAR
# Buraya yeni bir kripto para eklemek için COINS listesine yeni bir satır
# eklemen yeterli. "id" değeri CoinGecko'daki resmi coin id'si olmalı.
# Yeni bir hisse eklemek için STOCKS listesine sembolü eklemen yeterli.
# --------------------------------------------------------------------------
COINS = [
    {"id": "bitcoin", "symbol": "BTC", "emoji": "🟠"},
    {"id": "ethereum", "symbol": "ETH", "emoji": "🔷"},
    {"id": "solana", "symbol": "SOL", "emoji": "🟣"},
    {"id": "binancecoin", "symbol": "BNB", "emoji": "🟡"},
]

STOCKS = [
    {"symbol": "MSTR", "emoji": "📊"},
]


def get_crypto_prices():
    """CoinGecko API'den tüm kripto paraların fiyatını tek seferde çeker."""
    try:
        ids = ",".join(coin["id"] for coin in COINS)
        params = {
            "ids": ids,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        }
        response = requests.get(CRYPTO_API_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Kripto fiyatları alınamadı: {e}")
        return {}


def get_stock_price(symbol):
    """Yahoo Finance üzerinden hisse fiyatını çeker."""
    try:
        url = STOCK_API_URL.format(symbol=symbol)
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()["chart"]["result"][0]
        meta = result["meta"]
        price = meta["regularMarketPrice"]
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
        change = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0
        return {"price": price, "change": change}
    except Exception as e:
        logger.error(f"{symbol} hisse fiyatı alınamadı: {e}")
        return None


def format_line(emoji, symbol, price, change):
    trend = "🟢" if change >= 0 else "🔴"
    return f"{emoji} <b>{symbol}</b>: ${price:,.2f}  {trend} {change:+.2f}%"


def build_message():
    lines = ["💹 <b>Piyasa Fiyat Güncellemesi</b>", ""]

    crypto_data = get_crypto_prices()
    for coin in COINS:
        data = crypto_data.get(coin["id"])
        if data:
            lines.append(format_line(coin["emoji"], coin["symbol"], data["usd"], data.get("usd_24h_change", 0.0)))
        else:
            logger.warning(f"{coin['symbol']} için veri bulunamadı, atlanıyor.")

    for stock in STOCKS:
        data = get_stock_price(stock["symbol"])
        if data:
            lines.append(format_line(stock["emoji"], stock["symbol"], data["price"], data["change"]))
        else:
            logger.warning(f"{stock['symbol']} için veri bulunamadı, atlanıyor.")

    if len(lines) <= 2:
        return None

    return "\n".join(lines)


def send_to_channel(text):
    """Mesajı Telegram kanalına gönderir."""
    try:
        payload = {
            "chat_id": CHANNEL_USERNAME,
            "text": text,
            "parse_mode": "HTML",
        }
        response = requests.post(TELEGRAM_API_URL, data=payload, timeout=10)
        response.raise_for_status()
        logger.info("Mesaj başarıyla gönderildi.")
    except Exception as e:
        logger.error(f"Mesaj gönderilemedi: {e}")


def main():
    if not BOT_TOKEN or not CHANNEL_USERNAME:
        logger.error(
            "BOT_TOKEN veya CHANNEL_USERNAME ortam değişkeni eksik! "
            "Railway ayarlarından eklemeyi unutma."
        )
        return

    logger.info("Fiyat Botu başlatıldı. Her %s saniyede bir çalışacak.", INTERVAL_SECONDS)

    while True:
        message = build_message()
        if message:
            send_to_channel(message)
        else:
            logger.warning("Bu döngüde hiç veri alınamadığı için mesaj gönderilmedi.")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()