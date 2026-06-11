"""Прогон детектора аномалий по выгруженным данным.

Запуск:
    python -m src.check_anomalies                 # по визитам
    python -m src.check_anomalies ym:s:users      # по другой метрике
"""
from __future__ import annotations

import sys

import config
from src.anomaly import AnomalyConfig, detect_from_frame
from src.storage import Storage

METRIC_LABELS = {
    "ym:s:visits": "Визиты",
    "ym:s:users": "Посетители",
    "ym:s:pageviews": "Просмотры",
    "ym:s:bounceRate": "Отказы, %",
}


def main(metric: str = "ym:s:visits") -> None:
    storage = Storage(config.DB_PATH)
    daily = storage.load("daily")
    if daily.empty:
        print("Нет данных. Сначала запусти: python -m src.collect")
        return

    label = METRIC_LABELS.get(metric, metric)
    result = detect_from_frame(daily, metric, config=AnomalyConfig())
    anomalies = result[result["is_anomaly"]].copy()

    print(f"Метрика: {label}")
    print(f"Проанализировано дней: {len(result)}")
    print(f"Найдено аномалий: {len(anomalies)}\n")

    if anomalies.empty:
        print("Аномалий не обнаружено.")
        return

    arrow = {"spike": "▲ всплеск", "drop": "▼ провал"}
    for _, r in anomalies.iterrows():
        date = r["date"].date()
        fact = r["value"]
        exp = r["expected"]
        dev = (fact / exp - 1) * 100 if exp else float("nan")
        print(
            f"{date}  {arrow[r['direction']]:12}  "
            f"факт={fact:>10,.0f}  ожидалось≈{exp:>10,.0f}  "
            f"({dev:+.0f}%)  z={r['zscore']:+.1f}"
        )


if __name__ == "__main__":
    metric = sys.argv[1] if len(sys.argv) > 1 else "ym:s:visits"
    main(metric)
