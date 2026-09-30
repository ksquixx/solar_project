# src/data_parser.py
"""
Парсер исторических данных о погоде с сайта pogodaiklimat
для метеостанции Новокуйбышевск
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
from pathlib import Path

from src import config


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

WIND_DIRS = {
    "wind_n": "С", "wind_ne": "СВ", "wind_e": "В", "wind_se": "ЮВ",
    "wind_s": "Ю", "wind_sw": "ЮЗ", "wind_w": "З", "wind_nw": "СЗ",
    "wind_": "штиль",
}


def parse_month(session: requests.Session, year: int, month: int) -> pd.DataFrame | None:
    """Парсит один месяц целиком."""
    params = {
        "id": config.STATION_ID,
        "bday": 1,
        "fday": 31,
        "amonth": month,
        "ayear": year,
        "bot": 2,   # "человек" — обход проверки на бота
    }
    try:
        r = session.get(config.BASE_URL, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
    except requests.RequestException as e:
        print(f"  [ERROR] {month:02d}.{year}: {e}")
        return None

    soup = BeautifulSoup(r.text, "lxml")

    # --- 1. Левая колонка: время и дата ---
    left = soup.find("div", class_="archive-table-left-column")
    if not left:
        print(f"  [WARN] нет левой колонки за {month:02d}.{year}")
        return None

    timestamps = []
    for tr in left.find_all("tr"):
        tds = tr.find_all("td", class_="black")
        if len(tds) == 2:
            hour = tds[0].get_text(strip=True)
            day_month = tds[1].get_text(strip=True)  # "16.09"
            try:
                day, mon = day_month.split(".")
                timestamps.append((year, int(mon), int(day), int(hour)))
            except ValueError:
                timestamps.append(None)

    # --- 2. Основная таблица с данными ---
    wrap = soup.find("div", class_="archive-table-wrap")
    if not wrap:
        print(f"  [WARN] нет таблицы за {month:02d}.{year}")
        return None

    table = wrap.find("table")
    rows = table.find_all("tr", attrs={"height": "30"})

    records = []
    for i, tr in enumerate(rows):
        tds = tr.find_all("td")
        if len(tds) < 17:
            continue

        # Ветер: направление + скорость
        wind_dir = ""
        wind_speed = ""
        for td in tds[:2]:
            cls = " ".join(td.get("class", []))
            if cls.startswith("wind_"):
                wind_dir = WIND_DIRS.get(cls, td.get_text(strip=True))
            elif cls.startswith("ff_"):
                wind_speed = td.get_text(strip=True)

        def txt(idx):
            return tds[idx].get_text(strip=True) if idx < len(tds) else ""

        rec = {
            "wind_dir": wind_dir,
            "wind_speed_ms": wind_speed,
            "visibility": txt(2),
            "phenomena": txt(3),
            "cloudiness": txt(4),
            "T": txt(5),
            "Td": txt(6),
            "f": txt(7),
            "Te": txt(8),
            "Tes": txt(9),
            "comfort": txt(10),
            "P": txt(11),
            "Po": txt(12),
            "Tmin": txt(13),
            "Tmax": txt(14),
            "R": txt(15),
            "R24": txt(16),
            "S": txt(17) if len(tds) > 17 else "",
        }

        if i < len(timestamps) and timestamps[i]:
            y, m, d, h = timestamps[i]
            rec["datetime_utc"] = datetime(y, m, d, h)
        else:
            rec["datetime_utc"] = None

        records.append(rec)

    return pd.DataFrame(records)


def parse_years(years, months=range(1, 13), delay: float = 1.5) -> pd.DataFrame:
    """
    Парсит данные за указанные годы и месяцы.

    :param years: список годов, например [2024, 2025]
    :param months: диапазон месяцев (1-12)
    :param delay: пауза между запросами (сек), чтобы не забанили
    :return: DataFrame с почасовыми данными
    """
    session = requests.Session()

    all_data = []
    for year in years:
        for month in months:
            print(f"Парсинг {month:02d}.{year}...")
            df = parse_month(session, year, month)
            if df is not None and not df.empty:
                df["year"] = year
                df["month"] = month
                all_data.append(df)
            time.sleep(delay)

    if not all_data:
        print("Данные не собраны.")
        return pd.DataFrame()

    result = pd.concat(all_data, ignore_index=True)

    # Чистим числовые поля
    num_cols = ["wind_speed_ms", "T", "Td", "f", "Te", "Tes", "P", "Po",
                "Tmin", "Tmax", "R", "R24", "S"]
    for c in num_cols:
        result[c] = (result[c]
                     .astype(str)
                     .str.replace("+", "", regex=False)
                     .str.replace(",", ".", regex=False)
                     .replace({"н/о": None, "": None, "nan": None}))
        result[c] = pd.to_numeric(result[c], errors="coerce")

    # Локальное время = UTC + 4 (Самара)
    result["datetime_local"] = result["datetime_utc"] + pd.Timedelta(hours=4)

    return result


def collect_and_save(start_year: int = 2024, end_year: int | None = None) -> Path:
    """
    Собирает данные с start_year по текущий момент (или end_year)
    и сохраняет в data/raw/.
    """
    if end_year is None:
        end_year = datetime.now().year

    years = list(range(start_year, end_year + 1))
    df = parse_years(years=years)

    if df.empty:
        raise RuntimeError("Не удалось собрать данные о погоде.")

    output_path = config.RAW_DATA_DIR / f"weather_{config.STATION_ID}_{start_year}_{end_year}_raw.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"\nГотово! Строк: {len(df)}")
    print(f"Сохранено в: {output_path}")
    return output_path


if __name__ == "__main__":
    # Т.к. нам нужны данные с 1.01.2024 — собираем 2024 и 2025
    collect_and_save(start_year=2024)