"""Детектор аномалий по временным рядам Метрики.

Подход:
1. STL-декомпозиция ряда на тренд + недельную сезонность + остаток.
   Так мы «снимаем» закономерные колебания (будни/выходные, общий рост/спад),
   и в остатке остаётся только то, что моделью не объясняется.
2. По остаткам считаем РОБАСТНЫЙ z-score через медиану и MAD
   (median absolute deviation). В отличие от среднего/σ, эти оценки
   не «перекашиваются» одиночными выбросами — а у нас как раз бывают
   всплески в 10+ раз.
3. День считается аномальным, если |z| превышает порог (по умолчанию 3.5).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

# 1.4826 переводит MAD в оценку стандартного отклонения для нормального распределения
_MAD_TO_STD = 1.4826


@dataclass
class AnomalyConfig:
    period: int = 7          # длина сезонного цикла (неделя)
    z_threshold: float = 3.5  # порог робастного z-score
    min_points: int = 21      # минимум точек для осмысленной декомпозиции (3 недели)


def detect(
    series: pd.Series,
    config: AnomalyConfig | None = None,
) -> pd.DataFrame:
    """Ищет аномалии во временном ряде.

    series — pandas.Series со значениями и DatetimeIndex (без пропусков дней).
    Возвращает DataFrame с колонками:
        value     — фактическое значение
        expected  — ожидаемое (тренд + сезонность)
        residual  — остаток (факт − ожидание)
        zscore    — робастный z-score остатка
        is_anomaly — флаг аномалии
        direction — 'spike' (всплеск) / 'drop' (провал) / '' (норма)
    """
    cfg = config or AnomalyConfig()
    series = series.astype(float).sort_index()

    out = pd.DataFrame(index=series.index)
    out["value"] = series.values

    if len(series) < cfg.min_points:
        # данных мало — декомпозицию не строим, помечаем как «норма»
        out["expected"] = np.nan
        out["residual"] = np.nan
        out["zscore"] = np.nan
        out["is_anomaly"] = False
        out["direction"] = ""
        return out

    stl = STL(series, period=cfg.period, robust=True).fit()
    expected = stl.trend + stl.seasonal
    residual = series - expected

    med = np.median(residual)
    mad = np.median(np.abs(residual - med))
    scale = _MAD_TO_STD * mad if mad > 0 else 1e-9
    zscore = (residual - med) / scale

    is_anomaly = np.abs(zscore) > cfg.z_threshold
    direction = np.where(is_anomaly, np.where(zscore > 0, "spike", "drop"), "")

    out["expected"] = expected.values
    out["residual"] = residual.values
    out["zscore"] = zscore.values
    out["is_anomaly"] = is_anomaly.values
    out["direction"] = direction
    return out


def detect_from_frame(
    df: pd.DataFrame,
    metric: str,
    date_col: str = "ym:s:date",
    config: AnomalyConfig | None = None,
) -> pd.DataFrame:
    """Удобная обёртка: принимает таблицу `daily` и имя метрики."""
    s = df.copy()
    s[date_col] = pd.to_datetime(s[date_col])
    s = s.set_index(date_col)[metric]
    # восстанавливаем непрерывный дневной индекс (на случай пропусков)
    s = s.asfreq("D").interpolate()
    result = detect(s, config)
    return result.reset_index().rename(columns={date_col: "date", "index": "date"})
