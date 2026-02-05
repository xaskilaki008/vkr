import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st
from datetime import datetime

from streamlit_autorefresh import st_autorefresh

from src.config import BEACHES, BEACH_INFO, DB_PATH
from src.db import (
    get_conn, init_db,
    insert_measurement, read_measurements,
    read_latest_for_all_beaches
)
from src.demo import demo_timeseries, wave_class_from_index

st.set_page_config(page_title="Мониторинг морского волнения (Крым) — прототип", layout="wide")

# --- Инициализация БД ---
conn = get_conn(DB_PATH)
init_db(conn)

# --- session_state для live-режима ---
if "live_on" not in st.session_state:
    st.session_state.live_on = False


# ====== ПЕРЕМЕСТИЛИ ВЫБОР ПЛЯЖА СЮДА (под заголовок) ======
top1, top2, top3, top4 = st.columns([2.2, 1.8, 1.2, 1.3])

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

with top3:
    if st.button("ℹ️ Информация о пляже"):
        st.info(BEACH_INFO.get(beach, "Описание пока не задано."))

with top4:
    latest_all = read_latest_for_all_beaches(conn, BEACHES)
    row = latest_all.get(beach)

    st.write("Статус")  # маленькая подпись

    if row is None:
        st.write("⚪ нет данных")
    else:
        _, _, wc = row
        wc = int(wc)
        if wc <= 2:
            st.write("🟢 спокойно")
        elif wc == 3:
            st.write("🟡 умеренно")
        else:
            st.write("🔴 опасно")

if mode == "Реальные данные (заглушка)":
    st.info("Режим реальных данных пока не подключён. Для ВКР можно оставить как перспективу развития.")

st.markdown("---")

def class_to_status(wave_class: int | None):
    if wave_class is None:
        return "⚪", "нет данных"
    if wave_class <= 2:
        return "🟢", "спокойно"
    if wave_class == 3:
        return "🟡", "умеренно"
    return "🔴", "опасно"

# ====== БОКОВАЯ ПАНЕЛЬ: управление демо-данными + live-режим ======

with st.sidebar:
    st.header("Управление")


    st.subheader("Автоподгрузка таблицы")

    toggle = st.button(
        "⏸ Остановить автоподгрузку" if st.session_state.live_on else "▶️ Запустить автоподгрузку",
        key="toggle_live"
    )

    if toggle:
        st.session_state.live_on = not st.session_state.live_on

    if st.session_state.live_on:
        st.caption("🟢 Автоподгрузка включена")
    else:
        st.caption("⚪ Автоподгрузка остановлена")



    refresh_ms = st.slider("Период обновления (сек)", 1, 10, 2) * 1000
    tail_n = st.slider("Сколько последних строк показывать", 10, 200, 30)

    st.subheader("Добавление демо-данных")
    colA, colB = st.columns(2)
    with colA:
        add_one = st.button("Добавить 1")
    with colB:
        add_batch = st.button("Сгенерировать 60 мин")

    limit = st.slider("Точек на графике", 30, 500, 180)

    st.subheader("Состояние пляжей (сейчас)")
    latest = read_latest_for_all_beaches(conn, BEACHES)

    rows = []
    for b in BEACHES:
        r = latest.get(b)
        if r is None:
            emoji, status = class_to_status(None)
            rows.append({"Статус": emoji, "Пляж": b, "Класс": "—", "Описание": status})
        else:
            _, _, wave_class = r
            wave_class = int(wave_class)
            emoji, status = class_to_status(wave_class)
            rows.append({"Статус": emoji, "Пляж": b, "Класс": wave_class, "Описание": status})

    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# ====== Автообновление страницы (только когда live включен) ======
if st.session_state.live_on:
    st_autorefresh(interval=refresh_ms, key="live_refresh")

# ====== Добавление демо-данных в БД ======
if mode == "Демо-данные":
    if add_one:
        # Последнее значение — чтобы ряд был “плавный”
        last_rows = read_measurements(conn, beach, limit=1)
        prev = last_rows[-1][1] if last_rows else None

        import random
        wave_index = prev if prev is not None else random.uniform(0.3, 2.0)
        # Ограничили скорость изменения, чтобы не было резких скачков
        wave_index = max(0.1, min(4.5, wave_index + random.uniform(-0.12, 0.12)))
        wave_class = wave_class_from_index(wave_index)

        insert_measurement(conn, datetime.now(), beach, wave_index, wave_class)
        st.success("Добавлено 1 измерение.")

    if add_batch:
        pts = demo_timeseries(minutes=60)
        for ts, wave_index, wave_class in pts:
            insert_measurement(conn, ts, beach, wave_index, wave_class)
        st.success("Добавлены демо-данные за 60 минут.")

# ====== Чтение данных выбранного пляжа ======
rows = read_measurements(conn, beach, limit=max(limit, tail_n))

if not rows:
    st.info("Пока нет данных для этого пляжа. Нажми «Сгенерировать 60 мин».")
    st.stop()

df = pd.DataFrame(rows, columns=["ts", "wave_index", "wave_class"])
df["ts"] = pd.to_datetime(df["ts"])

last = df.iloc[-1]
emoji, status_text = class_to_status(int(last["wave_class"]))

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
    st.caption("Статус")
    st.write(f"{emoji} {status_text}")


# ====== График ======
st.subheader("Изменение волнения во времени")

fig, ax = plt.subplots()
ax.plot(df["ts"].tail(limit), df["wave_index"].tail(limit))
ax.set_xlabel("Время")
ax.set_ylabel("Wave Index (условн.)")
ax.grid(True)

# Чтобы подписи времени не налезали и не “пересекались”
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
fig.autofmt_xdate()

st.pyplot(fig, clear_figure=True)

# ====== “Лента” последних измерений (как чат) ======
st.subheader("Лента измерений (последние записи)")
st.caption("При включенной автоподгрузке таблица будет обновляться и показывать последние строки.")

feed = df.tail(tail_n).copy()
feed["ts"] = feed["ts"].dt.strftime("%Y-%m-%d %H:%M:%S")

# Новые строки будут “внизу”, как в чате
st.dataframe(feed, hide_index=True, use_container_width=True, height=360)

st.markdown("---")
st.caption("Поделиться сервисом • Связаться с автором • Поддержать проект (добавим на следующем шаге)")

st.title("Автоматизированная система мониторинга морского волнения (Крым)")
st.caption("Прототип для ВКР: Streamlit + SQLite + демо-данные (на старте)")