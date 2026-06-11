"""Формирование текстов отчётов для Telegram.

Все функции возвращают готовую HTML-строку.
"""
from __future__ import annotations

import pandas as pd

from src.anomaly import AnomalyConfig, detect_from_frame

METRIC_LABELS = {
    "ym:s:visits": "Визиты",
    "ym:s:users": "Посетители",
    "ym:s:pageviews": "Просмотры",
    "ym:s:bounceRate": "Отказы, %",
    "ym:s:pageDepth": "Глубина",
    "ym:s:avgVisitDurationSeconds": "Ср. визит, сек",
}
# метрики, где рост — это плохо (для подбора стрелок)
_INVERSE = {"ym:s:bounceRate"}


def _fmt(metric: str, value: float) -> str:
    if metric == "ym:s:bounceRate":
        return f"{value:.1f}%"
    if metric in ("ym:s:pageDepth", "ym:s:avgVisitDurationSeconds"):
        return f"{value:.1f}"
    return f"{value:,.0f}".replace(",", " ")


def _delta(metric: str, cur: float, prev: float) -> str:
    if prev is None or pd.isna(prev) or prev == 0:
        return ""
    change = (cur / prev - 1) * 100
    good = (change < 0) if metric in _INVERSE else (change > 0)
    arrow = "🟢" if good else "🔴"
    if abs(change) < 0.5:
        arrow = "⚪️"
    return f" {arrow} {change:+.0f}% к пред. неделе"


def daily_digest(daily: pd.DataFrame, metrics: list[str] | None = None) -> str:
    """Дайджест за последний день с сравнением: тот же день неделей раньше."""
    metrics = metrics or list(METRIC_LABELS)
    df = daily.copy()
    df["ym:s:date"] = pd.to_datetime(df["ym:s:date"])
    df = df.sort_values("ym:s:date")
    if df.empty:
        return "Нет данных для отчёта."

    last = df.iloc[-1]
    last_date = last["ym:s:date"].date()
    prev_row = df[df["ym:s:date"] == last["ym:s:date"] - pd.Timedelta(days=7)]
    prev = prev_row.iloc[0] if not prev_row.empty else None

    lines = [f"📊 <b>Отчёт за {last_date:%d.%m.%Y}</b>", ""]
    for m in metrics:
        if m not in df.columns:
            continue
        label = METRIC_LABELS.get(m, m)
        val = _fmt(m, last[m])
        delta = _delta(m, last[m], prev[m] if prev is not None else None)
        lines.append(f"• {label}: <b>{val}</b>{delta}")
    return "\n".join(lines)


def weekly_digest(daily: pd.DataFrame, metrics: list[str] | None = None) -> str:
    """Недельный итог: суммы/средние за 7 дней против предыдущих 7."""
    metrics = metrics or list(METRIC_LABELS)
    df = daily.copy()
    df["ym:s:date"] = pd.to_datetime(df["ym:s:date"])
    df = df.sort_values("ym:s:date")
    if len(df) < 14:
        return "Недостаточно данных для недельного отчёта (нужно ≥14 дней)."

    cur, prev = df.iloc[-7:], df.iloc[-14:-7]
    d1, d2 = cur["ym:s:date"].min().date(), cur["ym:s:date"].max().date()

    lines = [f"🗓 <b>Недельный отчёт {d1:%d.%m} — {d2:%d.%m}</b>", ""]
    for m in metrics:
        if m not in df.columns:
            continue
        label = METRIC_LABELS.get(m, m)
        # счётные метрики суммируем, относительные — усредняем
        agg = "mean" if m in _INVERSE or m in (
            "ym:s:pageDepth", "ym:s:avgVisitDurationSeconds") else "sum"
        c, p = getattr(cur[m], agg)(), getattr(prev[m], agg)()
        lines.append(f"• {label}: <b>{_fmt(m, c)}</b>{_delta(m, c, p)}")
    return "\n".join(lines)


def anomaly_alert(
    daily: pd.DataFrame,
    metric: str = "ym:s:visits",
    z_threshold: float = 3.5,
    only_last_days: int = 1,
) -> str | None:
    """Текст алерта, если в последние `only_last_days` дней есть аномалия.

    Возвращает None, если аномалий в этом окне нет.
    """
    result = detect_from_frame(
        daily, metric, config=AnomalyConfig(z_threshold=z_threshold)
    )
    if result.empty:
        return None
    recent = result.tail(only_last_days)
    flagged = recent[recent["is_anomaly"]]
    if flagged.empty:
        return None

    label = METRIC_LABELS.get(metric, metric)
    lines = [f"⚠️ <b>Аномалия: {label}</b>", ""]
    for _, r in flagged.iterrows():
        dev = (r["value"] / r["expected"] - 1) * 100 if r["expected"] else float("nan")
        kind = "▲ всплеск" if r["direction"] == "spike" else "▼ провал"
        lines.append(
            f"{r['date']:%d.%m.%Y} — {kind}\n"
            f"факт <b>{_fmt(metric, r['value'])}</b>, "
            f"ожидалось ≈ {_fmt(metric, r['expected'])} ({dev:+.0f}%)"
        )
    return "\n".join(lines)
