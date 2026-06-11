"""Отправка сообщений в Telegram через Bot API (без сторонних фреймворков)."""
from __future__ import annotations

import requests

API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramError(RuntimeError):
    pass


def send_message(token: str, chat_id: str | int, text: str) -> dict:
    """Отправляет сообщение в чат. text поддерживает HTML-разметку."""
    if not token or not chat_id:
        raise TelegramError(
            "Не заданы TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID в .env"
        )
    resp = requests.post(
        API.format(token=token),
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    data = resp.json()
    if not data.get("ok"):
        raise TelegramError(f"Telegram вернул ошибку: {data}")
    return data
