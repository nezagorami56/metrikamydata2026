"""Извлечение рекламных площадок из UTM Content.

Яндекс.Директ записывает площадку показа в UTM Content макросом {source}.
Формат UTM Content — пары «ключ|значение», разделённые «|»:
    pid|...|cid|703126717|...|dt|mobile|...|src|com.imo.android.imoim|srct|context|...

Нас интересует:
    src  — площадка показа (приложение/сайт РСЯ)
    srct — тип источника (context / search)
    dt   — тип устройства (mobile / tablet / desktop)
"""
from __future__ import annotations

import pandas as pd

_UNKNOWN = "(не определено)"


def parse_utm_content(content: str) -> dict[str, str]:
    """Разбирает строку UTM Content в словарь ключ→значение."""
    if not content or not isinstance(content, str):
        return {}
    parts = content.split("|")
    result: dict[str, str] = {}
    # идём парами: parts[0]=ключ, parts[1]=значение, parts[2]=ключ, ...
    for i in range(0, len(parts) - 1, 2):
        key = parts[i]
        if key:
            result[key] = parts[i + 1]
    return result


def extract_placement(content: str) -> str:
    """Возвращает название площадки (токен src) или '(не определено)'."""
    return parse_utm_content(content).get("src") or _UNKNOWN


def aggregate_placements(
    df: pd.DataFrame,
    content_col: str = "ym:s:UTMContent",
) -> pd.DataFrame:
    """Группирует выгрузку по площадке (src из UTM Content).

    Ожидает колонки: content_col, ym:s:visits, ym:s:users, ym:s:bounceRate.
    Возвращает DataFrame с колонками:
        placement, visits, users, bounce_rate (взвешенный по визитам)
    """
    if df.empty:
        return pd.DataFrame(columns=["placement", "visits", "users", "bounce_rate"])

    work = df.copy()
    work["placement"] = work[content_col].map(extract_placement)
    # для взвешенного среднего отказов: сумма (отказы% × визиты)
    work["_bounce_weighted"] = work["ym:s:bounceRate"] * work["ym:s:visits"]

    grouped = work.groupby("placement", as_index=False).agg(
        visits=("ym:s:visits", "sum"),
        users=("ym:s:users", "sum"),
        _bounce_weighted=("_bounce_weighted", "sum"),
    )
    grouped["bounce_rate"] = (
        grouped["_bounce_weighted"] / grouped["visits"].replace(0, pd.NA)
    ).round(2)
    grouped = grouped.drop(columns=["_bounce_weighted"])
    return grouped.sort_values("visits", ascending=False).reset_index(drop=True)
