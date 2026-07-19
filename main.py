import os
import time
import logging
from datetime import datetime

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
# AYARLAR (Token ve kanal bilgisi ORTAM DEĞİŞKENİ olarak Railway'de girilecek,
# kod içine YAZILMAYACAK — güvenlik için)
# --------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")  # örn: @btcfiyattakip
INTERVAL_SECONDS = 180  # 3 dakika

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price"


def get_btc_price():
    """CoinGecko API'den güncel BTC fiyatını çeker."""
    try:
        params = {
            "ids": "bitcoin",
            "vs_currencies": "usd,try",
            "include_24hr_change": "true",
        }
        response = requests.get(PRICE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()["bitcoin"]
        return {
            "usd": data["usd"],
            "try": data["try"],
            "change_24h": data.get("usd_24h_change", 0.0),
        }
    except Exception as e:
        logger.error(f"Fiyat alınamadı: {e}")
        return None


def format_message(price_data):
    """Telegram'a gönderilecek mesajı hazırlar."""
    change = price_data["change_24h"]
    trend_emoji = "🟢📈" if change >= 0 else "🔴📉"
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    message = (
        f"{trend_emoji} <b>BTC/USD Fiyat Güncellemesi</b>\n\n"
        f"💵 <b>USD:</b> ${price_data['usd']:,.2f}\n"
        f"🇹🇷 <b>TRY:</b> ₺{price_data['try']:,.2f}\n"
        f"📊 <b>24s Değişim:</b> {change:+.2f}%\n\n"
        f"🕐 {now}"
    )
    return message


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

    logger.info("BTC Fiyat Botu başlatıldı. Her %s saniyede bir çalışacak.", INTERVAL_SECONDS)

    while True:
        price_data = get_btc_price()
        if price_data:
            message = format_message(price_data)
            send_to_channel(message)
        else:
            logger.warning("Bu döngüde fiyat alınamadığı için mesaj gönderilmedi.")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
