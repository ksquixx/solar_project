# src/config.py
from pathlib import Path

# --- Основные настройки ---
STATION_ID = 35135  # ID метеостанции Новокуйбышевск
BASE_URL = "https://www.pogodaiklimat.ru/weather.php"

# --- Пути к данным ---
# Определяем корень проекта (папка, где лежит src)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Создаем папки, если их нет
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- Параметры для парсинга ---
START_YEAR = 2024
START_MONTH = 1
# Мы будем парсить по месяцам, поэтому конечные день/месяц/год определим в цикле