# src/data_explorer.py
"""
Разведочный анализ данных (EDA) для собранных метеоданных.

Задачи:
1. Показать общую информацию о датасете (типы, пропуски).
2. Для каждого столбца вывести уникальные значения (или топ-N для
   высококардинальных).
3. Отдельно проанализировать категориальные столбцы, которые
   понадобятся для кодирования в ML.
4. Сохранить отчёт в reports/eda_report.txt.
"""
import pandas as pd
from pathlib import Path
import sys

from src import config


# Столбцы, которые заведомо категориальные
CATEGORICAL_COLS = ["wind_dir", "visibility", "phenomena", "cloudiness", "comfort"]

# Столбцы, которые заведомо числовые (после парсера)
NUMERIC_COLS = ["wind_speed_ms", "T", "Td", "f", "Te", "Tes",
                "P", "Po", "Tmin", "Tmax", "R", "R24", "S"]


def load_raw_data() -> pd.DataFrame:
    """Загружает самый свежий raw-файл из data/raw/."""
    raw_files = sorted(config.RAW_DATA_DIR.glob("weather_*.csv"))
    if not raw_files:
        raise FileNotFoundError(
            f"Не найдено ни одного файла в {config.RAW_DATA_DIR}. "
            "Сначала запустите src/data_parser.py"
        )
    latest = raw_files[-1]
    print(f"Загружаем файл: {latest}")
    df = pd.read_csv(latest, parse_dates=["datetime_utc", "datetime_local"])
    return df


def describe_columns(df: pd.DataFrame, out) -> None:
    """Общая информация о датасете: типы, пропуски, диапазон дат."""
    print("=" * 70, file=out)
    print("ОБЩАЯ ИНФОРМАЦИЯ", file=out)
    print("=" * 70, file=out)
    print(f"Размер: {df.shape[0]} строк, {df.shape[1]} столбцов", file=out)
    print(f"Период: с {df['datetime_local'].min()} "
          f"по {df['datetime_local'].max()}", file=out)
    print(file=out)

    print("Типы данных и пропуски:", file=out)
    info = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "non_null": df.notna().sum(),
        "null": df.isna().sum(),
        "null_pct": (df.isna().sum() / len(df) * 100).round(2),
    })
    print(info.to_string(), file=out)
    print(file=out)


def analyze_numeric(df: pd.DataFrame, out) -> None:
    """Статистика по числовым столбцам."""
    print("=" * 70, file=out)
    print("ЧИСЛОВЫЕ СТОЛБЦЫ (describe)", file=out)
    print("=" * 70, file=out)

    existing = [c for c in NUMERIC_COLS if c in df.columns]
    print(df[existing].describe().T.to_string(), file=out)
    print(file=out)


def analyze_categorical(df: pd.DataFrame, out, top_n: int = 30) -> None:
    """Уникальные значения для категориальных столбцов."""
    print("=" * 70, file=out)
    print("КАТЕГОРИАЛЬНЫЕ СТОЛБЦЫ (уникальные значения)", file=out)
    print("=" * 70, file=out)

    existing = [c for c in CATEGORICAL_COLS if c in df.columns]
    for col in existing:
        uniq = df[col].dropna().unique()
        n_uniq = len(uniq)
        print(f"\n--- {col} ---", file=out)
        print(f"Уникальных значений: {n_uniq}", file=out)

        # Частоты
        vc = df[col].value_counts(dropna=False)
        if n_uniq <= top_n:
            print("Все значения с частотами:", file=out)
            print(vc.to_string(), file=out)
        else:
            print(f"Топ-{top_n} по частоте (из {n_uniq}):", file=out)
            print(vc.head(top_n).to_string(), file=out)
    print(file=out)


def analyze_datetime(df: pd.DataFrame, out) -> None:
    """Проверка временного ряда: пропущенные слоты."""
    print("=" * 70, file=out)
    print("ВРЕМЕННОЙ РЯД", file=out)
    print("=" * 70, file=out)

    dt = df["datetime_local"].dropna().sort_values()
    if dt.empty:
        print("Нет валидных datetime!", file=out)
        return

    diffs = dt.diff().dropna().value_counts()
    print("Распределение интервалов между записями:", file=out)
    print(diffs.to_string(), file=out)
    print(file=out)

    # Ожидаемый шаг для этой станции — 3 часа (8 раз в сутки)
    expected = pd.Timedelta(hours=3)
    missing = diffs.index[(diffs.index != expected) & (diffs.index > pd.Timedelta(0))]
    if len(missing) > 0:
        print(f"ВНИМАНИЕ: есть нестандартные интервалы: {list(missing)}", file=out)
        print("Это может означать пропуски в данных.", file=out)
    else:
        print("Пропусков не обнаружено (шаг ровно 3 часа).", file=out)
    print(file=out)


def suggest_encoding(df: pd.DataFrame, out) -> None:
    """Подсказки по кодированию для ML."""
    print("=" * 70, file=out)
    print("РЕКОМЕНДАЦИИ ПО КОДИРОВАНИЮ ДЛЯ ML", file=out)
    print("=" * 70, file=out)

    for col in CATEGORICAL_COLS:
        if col not in df.columns:
            continue
        uniq = df[col].dropna().unique()
        n_uniq = len(uniq)

        if col == "wind_dir":
            print(f"{col}: {n_uniq} значений → ЦИКЛИЧЕСКОЕ кодирование "
                  f"(sin/cos по азимуту)", file=out)
        elif col == "comfort":
            print(f"{col}: {n_uniq} значений → ORDINAL (порядковый) или "
                  f"ONE-HOT, значений мало", file=out)
        elif col == "cloudiness":
            print(f"{col}: строки вида '10/8' → разбить на 2 числа: "
                  f"cloud_total, cloud_low", file=out)
        elif col == "phenomena":
            print(f"{col}: {n_uniq} уникальных → бинарные флаги "
                  f"(есть_дождь, есть_снег, есть_туман) или ONE-HOT", file=out)
        else:
            print(f"{col}: {n_uniq} значений → ONE-HOT", file=out)

    print(file=out)
    print("Числовые столбцы (T, P, R и т.д.): оставить как есть, "
          "предварительно масштабировав (StandardScaler/MinMaxScaler).", file=out)


def main():
    # Куда писать отчёт
    config.PROJECT_ROOT.joinpath("reports").mkdir(exist_ok=True)
    report_path = config.PROJECT_ROOT / "reports" / "eda_report.txt"

    df = load_raw_data()

    with open(report_path, "w", encoding="utf-8") as out:
        describe_columns(df, out)
        analyze_numeric(df, out)
        analyze_categorical(df, out)
        analyze_datetime(df, out)
        suggest_encoding(df, out)

    print(f"\nОтчёт сохранён: {report_path}")

    # Дополнительно — короткая сводка в консоль
    print("\n--- КРАТКАЯ СВОДКА ---")
    print(f"Строк: {len(df)}")
    print(f"Категориальные столбцы: {CATEGORICAL_COLS}")
    print("\nУникальные значения wind_dir:", df['wind_dir'].dropna().unique())
    print("Уникальные значения comfort:", df['comfort'].dropna().unique())
    print("Уникальные значения cloudiness:",
          df['cloudiness'].dropna().unique()[:20])


if __name__ == "__main__":
    main()