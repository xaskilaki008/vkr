import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Hello Streamlit", layout="centered")

st.title("✅ Streamlit работает")
st.write("Если ты видишь эту страницу — запуск успешный.")

name = st.text_input("Введите имя:")
beach = st.selectbox("Выберите пляж", ["Ялта", "Алушта", "Евпатория", "Севастополь"])

st.success(f"Привет, {name if name else 'гость'}! Выбран пляж: {beach}")
st.info(f"Текущее время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if st.button("Нажми меня"):
    st.balloons()