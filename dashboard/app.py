"""Streamlit-дашборд по данным Яндекс.Метрики.

Запуск:
    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# делаем корень проекта импортируемым
sys.path.append(str(Path(__file__).resolve().parent.parent))

import config
from src.anomaly import AnomalyConfig, detect_from_frame
from src.storage import Storage

st.set_page_config(page_title="Метрика · Дашборд", layout="wide")
st.title("📊 Дашборд Яндекс.Метрики")

storage = Storage(config.DB_PATH)
daily = storage.load("daily")

if daily.empty:
    st.warning(
        "Данных пока нет. Запусти выгрузку командой:  `python -m src.collect`"
    )
    st.stop()

daily["ym:s:date"] = pd.to_datetime(daily["ym:s:date"])

# --- Боковая панель: выбор метрики ---
metric_labels = {
    "ym:s:visits": "Визиты",
    "ym:s:users": "Посетители",
    "ym:s:pageviews": "Просмотры",
    "ym:s:bounceRate": "Отказы, %",
    "ym:s:pageDepth": "Глубина просмотра",
    "ym:s:avgVisitDurationSeconds": "Ср. длительность визита, сек",
}
available = [m for m in metric_labels if m in daily.columns]
metric = st.sidebar.selectbox(
    "Метрика",
    options=available,
    format_func=lambda m: metric_labels.get(m, m),
)

# --- Детектор аномалий ---
show_anomalies = st.sidebar.checkbox("Показывать аномалии", value=True)
z_threshold = st.sidebar.slider(
    "Чувствительность (порог z-score)", 2.0, 6.0, 3.5, 0.5,
    help="Меньше порог — больше срабатываний",
)
anomalies = detect_from_frame(
    daily, metric, config=AnomalyConfig(z_threshold=z_threshold)
)
flagged = anomalies[anomalies["is_anomaly"]]

# --- Сводные показатели ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Сумма за период", f"{daily[metric].sum():,.0f}")
col2.metric("Среднее за день", f"{daily[metric].mean():,.1f}")
col3.metric("Максимум", f"{daily[metric].max():,.1f}")
col4.metric("Аномалий найдено", len(flagged))

# --- График динамики ---
fig = px.line(
    daily,
    x="ym:s:date",
    y=metric,
    markers=True,
    labels={"ym:s:date": "Дата", metric: metric_labels.get(metric, metric)},
    title=f"Динамика: {metric_labels.get(metric, metric)}",
)
if show_anomalies and not flagged.empty:
    fig.add_scatter(
        x=flagged["date"],
        y=flagged["value"],
        mode="markers",
        marker=dict(color="red", size=11, symbol="circle-open", line=dict(width=2)),
        name="Аномалия",
    )
st.plotly_chart(fig, use_container_width=True)

# --- Таблица аномалий ---
if show_anomalies and not flagged.empty:
    st.subheader("⚠️ Обнаруженные аномалии")
    table = flagged.copy()
    table["Дата"] = table["date"].dt.date
    table["Тип"] = table["direction"].map({"spike": "▲ всплеск", "drop": "▼ провал"})
    table["Факт"] = table["value"].round(0)
    table["Ожидалось"] = table["expected"].round(0)
    table["Отклонение"] = (table["value"] / table["expected"] - 1).map("{:+.0%}".format)
    st.dataframe(
        table[["Дата", "Тип", "Факт", "Ожидалось", "Отклонение"]],
        use_container_width=True, hide_index=True,
    )

# --- Источники трафика ---
sources = storage.load("traffic_sources")
if not sources.empty:
    st.subheader("Источники трафика")
    fig2 = px.bar(
        sources.head(10),
        x="ym:s:visits",
        y="ym:s:lastTrafficSource",
        orientation="h",
        labels={"ym:s:visits": "Визиты", "ym:s:lastTrafficSource": "Источник"},
    )
    fig2.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig2, use_container_width=True)

# --- Рекламные кампании / площадки ---
campaigns = storage.load("ad_campaigns")
if not campaigns.empty:
    st.subheader("🎯 Рекламные кампании")

    camp = campaigns.copy()
    camp["Кампания"] = camp["ym:s:UTMCampaign"].fillna("(не задано)")
    # короткая подпись для графика, чтобы длинные UTM влезали
    camp["short"] = camp["Кампания"].str.slice(0, 40) + camp["Кампания"].str.len().gt(40).map({True: "…", False: ""})

    rank_metric = st.radio(
        "Ранжировать по",
        options=["ym:s:visits", "ym:s:users"],
        format_func=lambda m: {"ym:s:visits": "Визиты", "ym:s:users": "Посетители"}[m],
        horizontal=True,
    )
    top_n = st.slider("Сколько кампаний показать", 5, 30, 10)
    top = camp.sort_values(rank_metric, ascending=False).head(top_n)

    fig3 = px.bar(
        top,
        x=rank_metric,
        y="short",
        orientation="h",
        color="ym:s:bounceRate",
        color_continuous_scale="RdYlGn_r",  # зелёный = мало отказов, красный = много
        labels={
            rank_metric: {"ym:s:visits": "Визиты", "ym:s:users": "Посетители"}[rank_metric],
            "short": "Кампания",
            "ym:s:bounceRate": "Отказы, %",
        },
        height=max(350, top_n * 28),
    )
    fig3.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig3, use_container_width=True)

    # Полная таблица с округлением
    tbl = camp.sort_values(rank_metric, ascending=False).head(top_n).copy()
    tbl["Визиты"] = tbl["ym:s:visits"].round(0).astype(int)
    tbl["Посетители"] = tbl["ym:s:users"].round(0).astype(int)
    tbl["Отказы, %"] = tbl["ym:s:bounceRate"].round(1)
    tbl["Глубина"] = tbl["ym:s:pageDepth"].round(2)
    st.dataframe(
        tbl[["Кампания", "Визиты", "Посетители", "Отказы, %", "Глубина"]],
        use_container_width=True, hide_index=True,
    )

# --- Площадки показа РСЯ (из UTM Content) ---
placements = storage.load("ad_placements")
if not placements.empty:
    st.subheader("📍 Площадки показа РСЯ")
    st.caption("Сайты и приложения рекламной сети Яндекса, где показывалась реклама "
               "(источник — токен src из UTM Content)")

    top_p = st.slider("Сколько площадок показать", 5, 40, 15, key="placements_n")
    pl = placements.sort_values("visits", ascending=False).head(top_p)

    figp = px.bar(
        pl,
        x="visits",
        y="placement",
        orientation="h",
        color="bounce_rate",
        color_continuous_scale="RdYlGn_r",
        labels={"visits": "Визиты", "placement": "Площадка", "bounce_rate": "Отказы, %"},
        height=max(350, top_p * 26),
    )
    figp.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(figp, use_container_width=True)

    tblp = pl.copy()
    tblp["Площадка"] = tblp["placement"]
    tblp["Визиты"] = tblp["visits"].round(0).astype(int)
    tblp["Посетители"] = tblp["users"].round(0).astype(int)
    tblp["Отказы, %"] = tblp["bounce_rate"]
    st.dataframe(
        tblp[["Площадка", "Визиты", "Посетители", "Отказы, %"]],
        use_container_width=True, hide_index=True,
    )
