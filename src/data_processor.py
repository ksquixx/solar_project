# src/data_processor.py
"""
Обработка и агрегация сырых метеоданных.

Вход:  data/raw/weather_35135_YYYY_YYYY_raw.csv (почасовые, 3-часовой шаг)
Выход: data/processed/weather_35135_daily.csv (ежедневные агрегаты)

Что делает:
1. Удаляет бесполезные столбцы (пустые или полностью 'н/о').
2. Кодирует wind_dir (sin/cos + флаг штиля).
3. Кодирует comfort в порядковую шкалу.
4. Агрегирует 3-часовые данные в дневные (по local time!).
5. Сохраняет результат в data/processed/.
"""
import numpy as np
import pandas as pd

from src import config


# Столбцы, которые выкидываем полностью (пустые или только 'н/о')
DROP_COLS = [
    "visibility",   # только 'н/о'
    "phenomena",    # 100% NaN
    "cloudiness",   # только 'н/о'
    "R24",          # 100% NaN
    "S",            # 100% NaN
    "R",            # 97% NaN — осадки возьмём из Open-Meteo
    "Tmin",         # 85% NaN — восстановим из T
    "Tmax",         # 88% NaN — восстановим из T
]

# Азимуты направлений ветра (в градусах, 0=С, по часовой)
WIND_AZIMUTH = {
    "С":  0.0,
    "СВ": 45.0,
    "В":  90.0,
    "ЮВ": 135.0,
    "Ю":  180.0,
    "ЮЗ": 225.0,
    "З":  270.0,
    "СЗ": 315.0,
}

# Порядковая шкала комфорта (от самого холодного к самому жаркому)
COMFORT_ORDER = {
    "опасность обморожения": -3,
    "очень холодно":         -2,
    "холодно":               -2,
    "прохладно":             -1,
    "по сезону":              0,
    "комфорт":                0,
    "тепло":                  1,
    "душно":                  2,
    "жарко":                  2,
    "очень душно":            3,
    "очень жарко":            3,
}


def load_raw_data() -> pd.DataFrame:
    """Загружает последний raw-файл."""
    raw_files = sorted(config.RAW_DATA_DIR.glob("weather_*.csv"))
    if not raw_files:
        raise FileNotFoundError(
            f"Нет файлов в {config.RAW_DATA_DIR}. Запустите src/data_parser.py"
        )
    latest = raw_files[-1]
    print(f"Загружаем: {latest}")
    return pd.read_csv(latest, parse_dates=["datetime_utc", "datetime_local"])


def drop_useless_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Удаляет бесполезные столбцы."""
    to_drop = [c for c in DROP_COLS if c in df.columns]
    print(f"Удаляем столбцы: {to_drop}")
    return df.drop(columns=to_drop)


def encode_wind_dir(df: pd.DataFrame) -> pd.DataFrame:
    """
    Кодирует направление ветра:
    - wind_azimuth — угол в градусах (NaN для штиля)
    - wind_dir_sin, wind_dir_cos — циклическое кодирование
    - is_calm — флаг штиля
    """
    df = df.copy()

    df["is_calm"] = (df["wind_dir"] == "штиль").astype(int)
    df["wind_azimuth"] = df["wind_dir"].map(WIND_AZIMUTH)

    # Для штиля направление не определено -> NaN в sin/cos
    rad = np.deg2rad(df["wind_azimuth"])
    df["wind_dir_sin"] = np.sin(rad)
    df["wind_dir_cos"] = np.cos(rad)

    # Для штиля sin/cos бессмысленны -> 0
    mask_calm = df["is_calm"] == 1
    df.loc[mask_calm, ["wind_dir_sin", "wind_dir_cos"]] = 0.0

    return df.drop(columns=["wind_dir", "wind_azimuth"])


def encode_comfort(df: pd.DataFrame) -> pd.DataFrame:
    """Кодирует comfort в порядковую шкалу."""
    df = df.copy()
    # Нормализуем пробелы (в данных есть "очень  холодно" с двумя пробелами)
    normalized = df["comfort"].str.replace(r"\s+", " ", regex=True).str.strip()
    df["comfort_ordinal"] = normalized.map(COMFORT_ORDER)
    return df.drop(columns=["comfort"])


def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """
    Агрегирует 3-часовые данные в дневные.

    Важно: группируем по ЛОКАЛЬНОЙ дате (datetime_local), а не по UTC.
    """
    df = df.copy()
    df["date"] = df["datetime_local"].dt.normalize()

    # Считаем число наблюдений в каждом дне (макс = 8 для 3-часового шага)
    n_obs = df.groupby("date").size().rename("n_obs")

    # Основные агрегаты
    daily = df.groupby("date").agg(
        T_mean=("T", "mean"),
        T_max=("T", "max"),
        T_min=("T", "min"),
        T_std=("T", "std"),

        Td_mean=("Td", "mean"),
        f_mean=("f", "mean"),

        Te_mean=("Te", "mean"),
        Tes_mean=("Tes", "mean"),

        P_mean=("P", "mean"),
        P_min=("P", "min"),
        P_max=("P", "max"),

        wind_speed_mean=("wind_speed_ms", "mean"),
        wind_speed_max=("wind_speed_ms", "max"),

        wind_dir_sin_mean=("wind_dir_sin", "mean"),
        wind_dir_cos_mean=("wind_dir_cos", "mean"),

        is_calm_frac=("is_calm", "mean"),
        comfort_mean=("comfort_ordinal", "mean"),
    )

    # T_range — суточная амплитуда
    daily["T_range"] = daily["T_max"] - daily["T_min"]

    # P_change — тренд давления (важный признак для прогноза погоды)
    # Разница между последним и первым значением давления за сутки
    p_change = (
        df.sort_values("datetime_local")
          .groupby("date")["P"]
          .agg(lambda s: s.iloc[-1] - s.iloc[0])
          .rename("P_change")
    )
    daily = daily.join(p_change)

    # n_obs и флаг надёжности
    daily = daily.join(n_obs)
    daily["is_reliable"] = (daily["n_obs"] >= 6).astype(int)

    # Добавляем календарные признаки (пригодятся для ML)
    daily = daily.reset_index()
    daily["year"] = daily["date"].dt.year
    daily["month"] = daily["date"].dt.month
    daily["day_of_year"] = daily["date"].dt.dayofyear
    daily["day_of_week"] = daily["date"].dt.dayofweek

    # Циклические признаки для дня года и месяца
    daily["doy_sin"] = np.sin(2 * np.pi * daily["day_of_year"] / 365.25)
    daily["doy_cos"] = np.cos(2 * np.pi * daily["day_of_year"] / 365.25)

    return daily


def main():
    df = load_raw_data()

    print(f"Исходный размер: {df.shape}")
    df = drop_useless_columns(df)
    df = encode_wind_dir(df)
    df = encode_comfort(df)
    print(f"После кодирования: {df.shape}")

    daily = aggregate_daily(df)
    print(f"После агрегации по дням: {daily.shape}")

    # Статистика по надёжности
    n_unreliable = (daily["is_reliable"] == 0).sum()
    print(f"Ненадёжных дней (< 6 наблюдений): {n_unreliable} из {len(daily)}")

    # Сохраняем
    output_path = config.PROCESSED_DATA_DIR / "weather_35135_daily.csv"
    daily.to_csv(output_path, index=False, encoding="utf-8")
    print(f"\nСохранено: {output_path}")

    # Показываем пример
    print("\nПервые 5 строк:")
    print(daily.head().to_string())
    print("\nПропуски в дневных данных:")
    print(daily.isna().sum()[daily.isna().sum() > 0])


if __name__ == "__main__":
    main()