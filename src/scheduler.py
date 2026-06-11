"""Планировщик: обновляет данные и шлёт отчёты/алерты в Telegram.

Запуск постоянного процесса (по расписанию):
    python -m src.scheduler

Разовая отправка вручную (для проверки):
    python -m src.scheduler --now daily    # ежедневный дайджест
    python -m src.scheduler --now weekly   # недельный отчёт
    python -m src.scheduler --now alert     # проверить свежую аномалию
"""
from __future__ import annotations

import argparse

from apscheduler.schedulers.blocking import BlockingScheduler

import config
from src.collect import collect
from src.reports import anomaly_alert, daily_digest, weekly_digest
from src.storage import Storage
from src.telegram_bot import send_message

# --- Расписание (можно менять) ---
DAILY_HOUR = 9        # ежедневный дайджест в 09:00
WEEKLY_DAY = "mon"    # недельный отчёт по понедельникам
ALERT_EVERY_HOURS = 3  # как часто проверять свежие аномалии


def _send(text: str | None) -> None:
    if text:
        send_message(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, text)


def _load() -> "Storage":
    return Storage(config.DB_PATH)


def job_daily() -> None:
    """Обновить данные и отправить дневной дайджест + проверить аномалии."""
    collect()  # подтянуть свежие данные из Метрики
    daily = _load().load("daily")
    _send(daily_digest(daily))
    _send(anomaly_alert(daily, only_last_days=2))


def job_weekly() -> None:
    daily = _load().load("daily")
    _send(weekly_digest(daily))


def job_alert() -> None:
    """Частая проверка: обновить данные и алертить только при аномалии."""
    collect()
    daily = _load().load("daily")
    _send(anomaly_alert(daily, only_last_days=1))


def run_scheduler() -> None:
    sched = BlockingScheduler(timezone="Europe/Moscow")
    sched.add_job(job_daily, "cron", hour=DAILY_HOUR, minute=0, id="daily")
    sched.add_job(
        job_weekly, "cron", day_of_week=WEEKLY_DAY, hour=DAILY_HOUR, minute=5,
        id="weekly",
    )
    sched.add_job(job_alert, "interval", hours=ALERT_EVERY_HOURS, id="alert")
    print("Планировщик запущен. Расписание:")
    print(f"  • Дневной дайджест — ежедневно в {DAILY_HOUR:02d}:00")
    print(f"  • Недельный отчёт — {WEEKLY_DAY} в {DAILY_HOUR:02d}:05")
    print(f"  • Проверка аномалий — каждые {ALERT_EVERY_HOURS} ч")
    print("Ctrl+C для остановки.")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nОстановлено.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--now", choices=["daily", "weekly", "alert"],
        help="разово выполнить задачу и выйти",
    )
    args = parser.parse_args()

    if args.now == "daily":
        job_daily()
    elif args.now == "weekly":
        job_weekly()
    elif args.now == "alert":
        job_alert()
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
