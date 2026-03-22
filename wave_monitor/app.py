import random
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.config import BEACHES, BEACH_INFO, DB_PATH
from src.db import (
    get_conn,
    init_db,
    insert_measurement,
    read_latest_for_all_beaches,
    read_measurements,
)
from src.demo import demo_timeseries, wave_class_from_index

st.set_page_config(page_title="Мониторинг морского волнения", layout="centered")

st.markdown(
    """
    <style>
    .block-container {
        max-width: 980px;
        padding-top: 1.2rem;
        padding-bottom: 1.5rem;
    }
    div[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }
    [data-testid="stHeaderActionElements"] {
        display: none;
    }
    div[data-testid="stMetric"] {
        padding: 0.2rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def class_to_status(wave_class: int | None) -> str:
    if wave_class is None:
        return "Нет данных"
    if wave_class <= 2:
        return "Спокойно"
    if wave_class == 3:
        return "Умеренно"
    return "Опасно"


def build_beach_status_table(conn):
    latest = read_latest_for_all_beaches(conn, BEACHES)
    table_rows = []
    for beach_name in BEACHES:
        row = latest.get(beach_name)
        if row is None:
            table_rows.append(
                {
                    "Пляж": beach_name,
                    "Класс": "—",
                    "Состояние": class_to_status(None),
                }
            )
            continue

        _, _, wave_class = row
        wave_class = int(wave_class)
        table_rows.append(
            {
                "Пляж": beach_name,
                "Класс": wave_class,
                "Состояние": class_to_status(wave_class),
            }
        )
    return pd.DataFrame(table_rows)


conn = get_conn(DB_PATH)
init_db(conn)

if "live_on" not in st.session_state:
    st.session_state.live_on = False

st.title("Мониторинг морского волнения")

top1, top2 = st.columns([1.5, 1.5])
with top1:
    beach = st.selectbox("Пляж", BEACHES, key="beach_select_top")
with top2:
    mode = st.radio(
        "Режим данных",
        ["Демо-данные", "Реальные данные (заглушка)"],
        index=0,
        horizontal=True,
        key="mode_top",
    )

with st.expander("Описание пляжа", expanded=False):
    st.write(BEACH_INFO.get(beach, "Описание пока не задано."))

if mode == "Реальные данные (заглушка)":
    st.caption("Режим реальных данных пока не подключён.")

st.subheader("Состояние пляжей", anchor=False)
st.dataframe(build_beach_status_table(conn), hide_index=True, use_container_width=True)

with st.sidebar:
    st.caption("Параметры отображения")

    st.session_state.live_on = st.toggle(
        "Автообновление данных",
        value=st.session_state.live_on,
    )
    st.caption("Включено" if st.session_state.live_on else "Выключено")

    refresh_ms = st.slider("Период обновления, сек", 1, 10, 2) * 1000
    tail_n = st.slider("Строк в таблице", 10, 200, 30)
    limit = st.slider("Точек на графике", 30, 500, 180)

    st.divider()
    st.caption("Демо-данные")
    col_a, col_b = st.columns(2)
    with col_a:
        add_one = st.button("Добавить 1")
    with col_b:
        add_batch = st.button("Добавить 60 мин")

if st.session_state.live_on:
    st_autorefresh(interval=refresh_ms, key="live_refresh")

action_message = None
if mode == "Демо-данные":
    if add_one:
        last_rows = read_measurements(conn, beach, limit=1)
        prev = last_rows[-1][1] if last_rows else None
        wave_index = prev if prev is not None else random.uniform(0.3, 2.0)
        wave_index = max(0.1, min(4.5, wave_index + random.uniform(-0.12, 0.12)))
        wave_class = wave_class_from_index(wave_index)
        insert_measurement(conn, datetime.now(), beach, wave_index, wave_class)
        action_message = "Добавлено 1 измерение."

    if add_batch:
        pts = demo_timeseries(minutes=60)
        for ts, wave_index, wave_class in pts:
            insert_measurement(conn, ts, beach, wave_index, wave_class)
        action_message = "Добавлены данные за 60 минут."

if action_message:
    st.caption(action_message)

rows = read_measurements(conn, beach, limit=max(limit, tail_n))
if not rows:
    st.caption("Для выбранного пляжа пока нет данных.")
    st.stop()

df = pd.DataFrame(rows, columns=["ts", "wave_index", "wave_class"])
df["ts"] = pd.to_datetime(df["ts"])
df = df.sort_values("ts")

last = df.iloc[-1]
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.caption("Пляж")
    st.write(beach)
with m2:
    st.caption("Wave Index")
    st.write(f"{last['wave_index']:.2f}")
with m3:
    st.caption("Wave Class")
    st.write(int(last["wave_class"]))
with m4:
    st.caption("Состояние")
    st.write(class_to_status(int(last["wave_class"])))

st.subheader("Изменение волнения во времени", anchor=False)

plot_df = df.tail(limit)
fig, ax = plt.subplots(figsize=(5.8, 2.8))
ax.plot(plot_df["ts"], plot_df["wave_index"], color="#787878", linewidth=1.5)
ax.set_xlabel("Время")
ax.set_ylabel("Wave Index")
ax.grid(True, alpha=0.25)

locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
formatter = mdates.ConciseDateFormatter(locator)
formatter.formats = ["%Y", "%b %Y", "%d %b", "%d %b", "%H:%M", "%H:%M"]
formatter.zero_formats = ["", "%Y", "%b %Y", "%d %b", "%d %b", "%H:%M"]
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(formatter)
ax.tick_params(axis="x", labelrotation=0, labelsize=9)
fig.tight_layout()

plot_left, plot_center, plot_right = st.columns([0.4, 1.6, 0.4])
with plot_center:
    st.pyplot(fig, clear_figure=True, use_container_width=True)

st.subheader("Последние измерения", anchor=False)
feed = df.tail(tail_n).copy()
feed["ts"] = feed["ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
st.dataframe(feed, hide_index=True, use_container_width=True, height=320)
