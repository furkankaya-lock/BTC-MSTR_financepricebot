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
# AYARLAR (Hepsi ORTAM DEĞİŞKENİ olarak Railway'de girilir, kod içine
# YAZILMAZ — güvenlik için ve kolayca değiştirebilmen için)
# --------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")  # örn: @finance_ServisAcademy

# İkinci hedef: bir grup ve o grup içindeki belirli bir oda (topic).
# İkisi de opsiyonel — boş bırakırsan bot sadece kanala mesaj atar.
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID")      # örn: -1004498727604
GROUP_THREAD_ID = os.environ.get("GROUP_THREAD_ID")  # örn: 3

INTERVAL_SECONDS = 180  # 3 dakika

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
CRYPTO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
STOCK_API_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# --------------------------------------------------------------------------
# TAKİP EDİLECEK VARLIKLAR
# Yeni bir kripto para eklemek için COINS listesine yeni bir satır eklemen
# yeterli ("id" değeri CoinGecko'daki resmi coin id'si olmalı).
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


def get_targets():
    """Mesajın gönderileceği tüm hedefleri (kanal + varsa grup/oda) döner."""
    targets = []

    if CHANNEL_USERNAME:
        targets.append({"chat_id": CHANNEL_USERNAME, "thread_id": None})

    if GROUP_CHAT_ID:
        targets.append({"chat_id": GROUP_CHAT_ID, "thread_id": GROUP_THREAD_ID or None})

    return targets


def send_message(chat_id, text, thread_id=None):
    """Belirtilen chat_id'ye (ve varsa oda/thread'e) mesaj gönderir."""
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if thread_id:
            payload["message_thread_id"] = thread_id

        response = requests.post(TELEGRAM_API_URL, data=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Mesaj başarıyla gönderildi -> chat_id={chat_id}, thread_id={thread_id}")
    except Exception as e:
        logger.error(f"Mesaj gönderilemedi (chat_id={chat_id}, thread_id={thread_id}): {e}")


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN ortam değişkeni eksik!")
        return

    targets = get_targets()
    if not targets:
        logger.error("Hiçbir hedef (CHANNEL_USERNAME veya GROUP_CHAT_ID) tanımlı değil!")
        return

    logger.info("Fiyat Botu başlatıldı. Her %s saniyede bir çalışacak. Hedef sayısı: %s", INTERVAL_SECONDS, len(targets))

    while True:
        message = build_message()
        if message:
            for target in targets:
                send_message(target["chat_id"], message, target["thread_id"])
        else:
            logger.warning("Bu döngüde hiç veri alınamadığı için mesaj gönderilmedi.")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
