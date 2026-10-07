# dashboard/mock_data.py
"""
для выработки СЭС.

Пока нет реальных данных о генерации (Kaggle-датасет ещё не подключён),
генерируем правдоподобную кривую выработки на основе:
- времени суток (колоколообразная кривая, пик в полдень)
- сезона (летом больше, зимой меньше)
- широты Самары (~52°)
- случайных облачных "провалов"
"""
import numpy as np
import pandas as pd
from datetime import date


# Параметры "виртуальной" электростанции
PANEL_ROWS = 4
PANEL_COLS = 4
N_PANELS = PANEL_ROWS * PANEL_COLS
PANEL_PEAK_KW = 0.5           # пиковая мощность одной панели, кВт
STATION_PEAK_KW = PANEL_PEAK_KW * N_PANELS   # 8 кВт


def _solar_factor(hour: float, day_of_year: int) -> float:
    """
    Безразмерный множитель [0..1], имитирующий высоту солнца.
    Учитывает время суток и сезон для широты ~52°.
    """
    # Сезонная поправка: летом день длиннее, зимой короче
    seasonal = 0.5 + 0.5 * np.sin(2 * np.pi * (day_of_year - 80) / 365.25)

    # Солнце встаёт/садится — аппроксимация через синус
    # Зимой световой день ~7ч (9..16), летом ~17ч (4..21)
    sunrise = 9 - 4 * seasonal
    sunset = 16 + 5 * seasonal
    if hour < sunrise or hour > sunset:
        return 0.0

    # Нормализованное время между восходом и закатом
    t = (hour - sunrise) / (sunset - sunrise)
    # Колоколообразная кривая: sin(pi * t)
    return float(np.sin(np.pi * t))


def generate_daily_generation(target_date: date, cloud_frac: float = 0.3) -> pd.DataFrame:
    """
    Генерирует 3-часовые данные выработки за сутки.

    :param target_date: дата
    :param cloud_frac: доля облачности [0..1] — снижает выработку
    :return: DataFrame с колонками datetime_local, hour, generation_kw (общая),
             и generation_kw_per_panel — список массивов по панелям.
    """
    rng = np.random.default_rng(seed=hash(target_date) % (2**32))

    hours = [0, 3, 6, 9, 12, 15, 18, 21]
    doy = target_date.timetuple().tm_yday

    rows = []
    for h in hours:
        base = _solar_factor(h, doy)
        # Облачность случайно колеблется в течение дня
        cloud_noise = rng.uniform(-0.15, 0.15)
        effective_cloud = np.clip(cloud_frac + cloud_noise, 0, 1)

        # Потери от облачности: до 70%
        cloud_loss = 1 - 0.7 * effective_cloud

        # Каждая панель немного отличается (эффективность, тень, пыль)
        per_panel = []
        for i in range(N_PANELS):
            panel_eff = 0.85 + 0.15 * rng.random()  # 85–100% эффективности
            kw = base * cloud_loss * PANEL_PEAK_KW * panel_eff
            # Небольшой шум
            kw *= rng.uniform(0.95, 1.05)
            per_panel.append(max(kw, 0.0))

        total_kw = sum(per_panel)
        rows.append({
            "datetime_local": pd.Timestamp(target_date) + pd.Timedelta(hours=h),
            "hour": h,
            "generation_kw": total_kw,
            "panel_values": per_panel,   # список по панелям
        })

    return pd.DataFrame(rows)


def generate_station_totals(target_date: date) -> dict:
    """
    Возвращает агрегаты для отображения в UI:
    - total_kwh — суммарная выработка за день, кВт·ч
    - peak_kw — пиковая мощность, кВт
    - per_panel_kwh — список выработок по каждой панели, кВт·ч
    """
    df = generate_daily_generation(target_date)
    # 3-часовой шаг → умножаем на 3, чтобы получить кВт·ч
    total_kwh = float(df["generation_kw"].sum() * 3)
    peak_kw = float(df["generation_kw"].max())

    per_panel_kwh = np.zeros(N_PANELS)
    for _, row in df.iterrows():
        for i, v in enumerate(row["panel_values"]):
            per_panel_kwh[i] += v * 3

    return {
        "total_kwh": total_kwh,
        "peak_kw": peak_kw,
        "per_panel_kwh": per_panel_kwh.tolist(),
        "df": df,
    }