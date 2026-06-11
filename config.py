"""Конфигурация проекта: читаем настройки из .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "metrika.db"

load_dotenv(BASE_DIR / ".env")

COUNTER_ID = os.getenv("METRIKA_COUNTER_ID", "")
OAUTH_TOKEN = os.getenv("METRIKA_OAUTH_TOKEN", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Стандартный набор метрик и разбивок для выгрузки.
# Полный справочник: https://yandex.ru/dev/metrika/doc/api2/api_v1/attrandmetr/dim_all.html
DEFAULT_METRICS = [
    "ym:s:visits",          # визиты
    "ym:s:users",           # посетители
    "ym:s:pageviews",       # просмотры
    "ym:s:bounceRate",      # отказы, %
    "ym:s:pageDepth",       # глубина просмотра
    "ym:s:avgVisitDurationSeconds",  # средняя длительность визита
]
