"""Хранилище выгруженных данных в SQLite."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


class Storage:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, df: pd.DataFrame, table: str, if_exists: str = "replace") -> None:
        """Сохраняет DataFrame в таблицу.

        if_exists: 'replace' — перезаписать, 'append' — дописать.
        """
        if df.empty:
            return
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql(table, conn, if_exists=if_exists, index=False)

    def load(self, table: str) -> pd.DataFrame:
        """Читает таблицу целиком. Пустой DataFrame, если таблицы нет."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                return pd.read_sql(f"SELECT * FROM {table}", conn)
            except pd.errors.DatabaseError:
                return pd.DataFrame()

    def query(self, sql: str) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(sql, conn)
