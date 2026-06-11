# Дашборд Яндекс.Метрики

Проект подтягивает данные из Яндекс.Метрики, визуализирует их в дашборде,
ищет аномалии и шлёт отчёты в Telegram.

## Статус по этапам
- [x] Этап 1 — сбор данных из Метрики в SQLite
- [x] Этап 2 — дашборд на Streamlit (базовая версия)
- [x] Этап 3 — детектор аномалий (STL + робастный z-score)
- [x] Этап 4 — Telegram-бот (отчёты + алерты)

## Установка

```bash
cd ~/metrika-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка доступа

```bash
cp .env.example .env
```

Заполни в `.env`:
- `METRIKA_COUNTER_ID` — ID счётчика (уже проставлен: 97189312)
- `METRIKA_OAUTH_TOKEN` — OAuth-токен Яндекса (см. ниже)

### Как получить OAuth-токен
1. Создай приложение: https://oauth.yandex.ru/client/new
2. Доступы → «Яндекс.Метрика» → «Получение статистики, чтение параметров».
3. Получи токен по инструкции: https://yandex.ru/dev/id/doc/dg/oauth/concepts/about.html

## Использование

```bash
# выгрузить данные (по умолчанию — за 30 дней)
python -m src.collect

# или за конкретный период
python -m src.collect 2024-01-01 2024-01-31

# проверить аномалии в консоли
python -m src.check_anomalies            # по визитам
python -m src.check_anomalies ym:s:users # по другой метрике

# запустить дашборд (с подсветкой аномалий)
streamlit run dashboard/app.py
```

## Telegram-отчёты

```bash
# разовая отправка (для проверки)
python -m src.scheduler --now daily    # дайджест за вчера
python -m src.scheduler --now weekly   # недельный отчёт
python -m src.scheduler --now alert    # проверить свежую аномалию

# постоянный процесс по расписанию
python -m src.scheduler
```

Расписание задаётся в начале `src/scheduler.py`:
- дневной дайджест — ежедневно в 09:00 (МСК)
- недельный отчёт — понедельник 09:05
- проверка аномалий — каждые 3 часа

## Структура
```
metrika-dashboard/
├── config.py              # настройки из .env
├── src/
│   ├── metrika_client.py  # клиент Reporting API
│   ├── storage.py         # сохранение в SQLite
│   └── collect.py         # скрипт выгрузки
├── dashboard/
│   └── app.py             # Streamlit-дашборд
└── data/                  # локальная БД (в git не попадает)
```
