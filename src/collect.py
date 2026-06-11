"""Скрипт выгрузки данных из Метрики в локальную БД.

Запуск:
    python -m src.collect                 # за последние 30 дней
    python -m src.collect 2024-01-01 2024-01-31
"""
from __future__ import annotations

import sys

import config
from src.metrika_client import MetrikaClient
from src.placements import aggregate_placements
from src.storage import Storage


def collect(date1: str = "30daysAgo", date2: str = "yesterday") -> None:
    client = MetrikaClient(config.OAUTH_TOKEN, config.COUNTER_ID)
    storage = Storage(config.DB_PATH)

    # 1) Динамика по дням — основа графиков и детектора аномалий
    print(f"Выгружаю дневную динамику за период {date1} … {date2}")
    daily = client.get_data(
        metrics=config.DEFAULT_METRICS,
        dimensions=["ym:s:date"],
        date1=date1,
        date2=date2,
        sort="ym:s:date",
    )
    storage.save(daily, "daily")
    print(f"  → строк: {len(daily)}")

    # 2) Разбивка по источникам трафика
    print("Выгружаю разбивку по источникам трафика")
    sources = client.get_data(
        metrics=["ym:s:visits", "ym:s:users", "ym:s:bounceRate"],
        dimensions=["ym:s:lastTrafficSource"],
        date1=date1,
        date2=date2,
        sort="-ym:s:visits",
    )
    storage.save(sources, "traffic_sources")
    print(f"  → строк: {len(sources)}")

    # 3) Разбивка по рекламным кампаниям (UTM Campaign)
    print("Выгружаю разбивку по рекламным кампаниям")
    campaigns = client.get_data(
        metrics=["ym:s:visits", "ym:s:users", "ym:s:bounceRate", "ym:s:pageDepth"],
        dimensions=["ym:s:UTMCampaign"],
        date1=date1,
        date2=date2,
        sort="-ym:s:visits",
        limit=100,
    )
    storage.save(campaigns, "ad_campaigns")
    print(f"  → строк: {len(campaigns)}")

    # 4) Разбивка по рекламным площадкам/каналам (рекл. система + источник + канал)
    print("Выгружаю разбивку по рекламным площадкам/каналам")
    platforms = client.get_data(
        metrics=["ym:s:visits", "ym:s:users", "ym:s:bounceRate"],
        dimensions=["ym:s:lastAdvEngine", "ym:s:UTMSource", "ym:s:UTMMedium"],
        date1=date1,
        date2=date2,
        sort="-ym:s:visits",
        limit=100,
    )
    storage.save(platforms, "ad_platforms")
    print(f"  → строк: {len(platforms)}")

    # 5) Площадки показа РСЯ — из UTM Content (токен src), с агрегацией
    print("Выгружаю площадки показа (UTM Content → src)")
    utm = client.get_data(
        metrics=["ym:s:visits", "ym:s:users", "ym:s:bounceRate"],
        dimensions=["ym:s:UTMContent"],
        date1=date1,
        date2=date2,
        sort="-ym:s:visits",
        limit=10000,
    )
    placements = aggregate_placements(utm)
    storage.save(placements, "ad_placements")
    print(f"  → строк UTM Content: {len(utm)} → площадок: {len(placements)}")

    print(f"\nГотово. База: {config.DB_PATH}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2:
        collect(args[0], args[1])
    else:
        collect()
