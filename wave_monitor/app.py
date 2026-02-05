import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime

from src.config import BEACHES, DB_PATH
from src.db import get_conn, init_db, insert_measurement, read_measurements
from src.demo import demo_timeseries, wave_class_from_index

st.set_page_config(page_title="Мониторинг морского волнения (Крым) — прототип", layout="wide")

# --- Инициализация БД ---
conn = get_conn(DB_PATH)
init_db(conn)

st.title("Автоматизированная система мониторинга морского волнения (Крым)")
st.caption("Прототип для ВКР: Streamlit + SQLite + демо-данные (вместо микрофона на старте)")

# --- Панель управления ---
with st.sidebar:
    st.header("Параметры")
    beach = st.selectbox("Выберите пляж", BEACHES)

    st.subheader("Источник данных")
    mode = st.radio("Режим", ["Демо-данные"], index=0)

    st.subheader("Добавление данных")
    colA, colB = st.columns(2)
    with colA:
        add_one = st.button("Добавить 1 измерение")
    with colB:
        add_batch = st.button("Сгенерировать 60 минут")

    limit = st.slider("Сколько точек показывать на графике", 30, 500, 180)

# --- Логика добавления демо-данных в БД ---
if add_one:
    # Берем последнюю точку для пляжа (если есть), чтобы “продолжать” ряд
    rows = read_measurements(conn, beach, limit=1)
    prev = rows[-1][1] if rows else None

    # Генерируем новую точку
    import random
    wave_index = prev if prev is not None else random.uniform(0.3, 2.0)
    wave_index = max(0.1, min(4.5, wave_index + random.uniform(-0.25, 0.25)))
    wave_class = wave_class_from_index(wave_index)

    insert_measurement(conn, datetime.now(), beach, wave_index, wave_class)
    st.success("Добавлено 1 измерение в базу данных.")

if add_batch:
    pts = demo_timeseries(minutes=60)
    for ts, wave_index, wave_class in pts:
        insert_measurement(conn, ts, beach, wave_index, wave_class)
    st.success("Добавлены демо-данные за 60 минут.")

# --- Чтение данных из БД и отображение ---
rows = read_measurements(conn, beach, limit=limit)

if not rows:
    st.info("Пока нет данных. Нажмите в боковой панели: «Сгенерировать 60 минут» или «Добавить 1 измерение».")
    st.stop()

df = pd.DataFrame(rows, columns=["ts", "wave_index", "wave_class"])
df["ts"] = pd.to_datetime(df["ts"])

# --- Верхние метрики ---
last = df.iloc[-1]
col1, col2, col3 = st.columns(3)
col1.metric("Пляж", beach)
col2.metric("Индекс волнения", f"{last['wave_index']:.2f}")
col3.metric("Класс волнения", int(last["wave_class"]))

# --- График ---
st.subheader("Изменение волнения во времени")

fig, ax = plt.subplots()
ax.plot(df["ts"], df["wave_index"])
ax.set_xlabel("Время")
ax.set_ylabel("Индекс волнения (условн.)")
ax.grid(True)

st.pyplot(fig, clear_figure=True)

# --- Таблица (полезно для защиты) ---
with st.expander("Показать последние записи (таблица)"):
    st.dataframe(df.tail(30), use_container_width=True)
