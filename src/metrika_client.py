"""Клиент Reporting API Яндекс.Метрики.

Документация API:
https://yandex.ru/dev/metrika/doc/api2/api_v1/data.html
"""
from __future__ import annotations

import time
from typing import Iterable

import pandas as pd
import requests

API_URL = "https://api-metrika.yandex.net/stat/v1/data"


class MetrikaError(RuntimeError):
    """Ошибка обращения к API Метрики."""


class MetrikaClient:
    def __init__(self, oauth_token: str, counter_id: str | int):
        if not oauth_token:
            raise MetrikaError(
                "Не задан OAuth-токен. Заполни METRIKA_OAUTH_TOKEN в .env"
            )
        self.counter_id = str(counter_id)
        self._session = requests.Session()
        self._session.headers.update(
            {"Authorization": f"OAuth {oauth_token}"}
        )

    def get_data(
        self,
        metrics: Iterable[str],
        date1: str,
        date2: str,
        dimensions: Iterable[str] | None = None,
        filters: str | None = None,
        limit: int = 10000,
        sort: str | None = None,
    ) -> pd.DataFrame:
        """Запрашивает отчёт и возвращает «плоский» DataFrame.

        date1 / date2 — границы периода в формате YYYY-MM-DD
        (либо относительные значения вроде 'today', '7daysAgo').
        """
        metrics = list(metrics)
        dimensions = list(dimensions or [])

        params = {
            "ids": self.counter_id,
            "metrics": ",".join(metrics),
            "date1": date1,
            "date2": date2,
            "limit": limit,
            "accuracy": "full",
        }
        if dimensions:
            params["dimensions"] = ",".join(dimensions)
        if filters:
            params["filters"] = filters
        if sort:
            params["sort"] = sort

        payload = self._request(params)
        return self._to_dataframe(payload, dimensions, metrics)

    def _request(self, params: dict, retries: int = 3) -> dict:
        for attempt in range(1, retries + 1):
            resp = self._session.get(API_URL, params=params, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            # 429 — превышен лимит запросов, ждём и повторяем
            if resp.status_code == 429 and attempt < retries:
                time.sleep(2 * attempt)
                continue
            raise MetrikaError(
                f"API вернул {resp.status_code}: {resp.text[:500]}"
            )
        raise MetrikaError("Исчерпаны попытки запроса к API")

    @staticmethod
    def _to_dataframe(
        payload: dict, dimensions: list[str], metrics: list[str]
    ) -> pd.DataFrame:
        rows = []
        for item in payload.get("data", []):
            row: dict = {}
            for dim_name, dim_val in zip(dimensions, item["dimensions"]):
                # у разбивок берём человекочитаемое имя, fallback на id
                row[dim_name] = dim_val.get("name") or dim_val.get("id")
            for metric_name, metric_val in zip(metrics, item["metrics"]):
                row[metric_name] = metric_val
            rows.append(row)
        return pd.DataFrame(rows)
