# dashboard/app.py
"""
Главный файл дашборда.
Запуск:  streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы работал импорт `from src import config`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from datetime import date

import pandas as pd
import streamlit as st

from src import config
from dashboard import styles, components
from dashboard.mock_data import generate_daily_generation, generate_station_totals


# ---------- Настройки страницы ----------
st.set_page_config(
    page_title="Solar Microgrid Dashboard",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

styles.inject_css()


# ---------- Загрузка погодных данных ----------
@st.cache_data(show_spinner=False)
def load_weather() -> pd.DataFrame:
    path = config.PROCESSED_DATA_DIR / "weather_35135_daily.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    return df


# ---------- Session state ----------
if "selected_panel" not in st.session_state:
    st.session_state["selected_panel"] = None


# ---------- Заголовок ----------
st.title("☀️ Solar Microgrid Dashboard")
st.caption("Прогноз выработки СЭС и управление нагрузкой микросети — Новокуйбышевск")

# ---------- Выбор даты ----------
weather_df = load_weather()

col_date, col_info = st.columns([2, 5])
with col_date:
    if not weather_df.empty:
        min_date = weather_df["date"].min().date()
        max_date = weather_df["date"].max().date()
        default_date = max_date
    else:
        min_date = date(2024, 1, 1)
        max_date = date.today()
        default_date = max_date

    selected_date = st.date_input(
        "Выберите дату",
        value=default_date,
        min_value=min_date,
        max_value=max_date,
    )

with col_info:
    if not weather_df.empty:
        weather_row = weather_df[weather_df["date"].dt.date == selected_date]
        weather_row = weather_row.iloc[0] if not weather_row.empty else None
        if weather_row is not None:
            st.success(
                f"Данные о погоде загружены: "
                f"{weather_row['n_obs']:.0f} наблюдений за сутки "
                f"({'надёжные' if weather_row.get('is_reliable', 0) == 1 else 'неполные'})"
            )
        else:
            st.warning("Для выбранной даты нет данных о погоде.")
    else:
        weather_row = None
        st.warning("Погодные данные не найдены. Запустите src/data_parser.py и src/data_processor.py")


# ---------- Генерация заглушки выработки ----------
totals = generate_station_totals(selected_date)
gen_df = totals["df"]
per_panel_kwh = totals["per_panel_kwh"]


# ---------- 1. Область станции ----------
st.subheader("🔋 Электростанция — 16 панелей")
st.caption("Кликните на панель, чтобы увидеть индивидуальный итог. Повторный клик — сброс.")

components.render_station_grid(per_panel_kwh, st.session_state["selected_panel"])
st.divider()


# ---------- 2. Область итога ----------
st.subheader("📊 Итог по выработке")
components.render_summary(
    total_kwh=totals["total_kwh"],
    peak_kw=totals["peak_kw"],
    per_panel_kwh=per_panel_kwh,
    selected_panel=st.session_state["selected_panel"],
)
st.divider()


# ---------- 3. Область погоды ----------
components.render_weather(weather_row)
st.divider()


# ---------- 4. График выработки ----------
components.render_generation_chart(gen_df, st.session_state["selected_panel"])


# ---------- Подвал ----------
st.divider()
st.caption(
    "⚠️ Данные о выработке СЭС — заглушка (mock). "
    "После интеграции Kaggle SolarPower + Open-Meteo будут использоваться реальные значения."
)