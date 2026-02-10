from pathlib import Path
import pandas as pd

# Carpetas disponibles para los datos
DATA_DIRS = {
    "Diario": Path("datos_diarios"),
    "Horario": Path("datos_horarios"),
}


def list_csv_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(path for path in folder.glob("*.csv") if path.is_file())


def load_prices(path: Path) -> tuple[pd.DataFrame, str]:
    df = pd.read_csv(path)
    date_col = next((c for c in ["Datetime", "Date"] if c in df.columns), None)
    if date_col is None:
        raise ValueError("No se encontro columna Date o Datetime en el csv.")

    parsed_dates = pd.to_datetime(df[date_col], errors="coerce", utc=True)
    try:
        parsed_dates = parsed_dates.dt.tz_convert(None)
    except TypeError:
        parsed_dates = parsed_dates.dt.tz_localize(None)
    df[date_col] = parsed_dates

    df = df.dropna(subset=[date_col, "Open", "High", "Low", "Close"])
    if df.empty:
        raise ValueError("No se pudieron interpretar fechas ni datos numericos en el archivo.")

    df = df.sort_values(date_col)
    return df, date_col


def filter_by_date(df: pd.DataFrame, date_col: str, start, end) -> pd.DataFrame:
    start_ts = pd.to_datetime(start)
    # Incluir todo el dia final
    end_ts = pd.to_datetime(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    mask = (df[date_col] >= start_ts) & (df[date_col] <= end_ts)
    return df.loc[mask]

