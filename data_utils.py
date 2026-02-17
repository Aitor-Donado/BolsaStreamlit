from pathlib import Path
import numpy as np
import pandas as pd

# Carpetas disponibles para los datos
DATA_DIRS = {
    "Diario": Path("datos_diarios"),
    "Horario": Path("datos_horarios"),
}


def list_parquet_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(path for path in folder.glob("*.parquet") if path.is_file())


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimiza los tipos de datos para reducir el espacio y mejorar el rendimiento.
    """
    # Reducir precisión de columnas float a float32
    float_columns = ["Close", "High", "Low", "Open", "Dividends", "Stock Splits"]
    for col in float_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(np.float32)

    # Reducir precisión de columnas int a int32
    int_columns = ["Volume"]
    for col in int_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(np.int32)

    return df


def load_prices(path: Path) -> tuple[pd.DataFrame, str]:
    df = pd.read_parquet(path)
    date_col = next((c for c in ["Datetime", "Date"] if c in df.columns), None)
    if date_col is None:
        raise ValueError(
            "No se encontro columna Date o Datetime en el archivo parquet."
        )

    parsed_dates = pd.to_datetime(df[date_col], errors="coerce", utc=True)
    try:
        parsed_dates = parsed_dates.dt.tz_convert(None)
    except TypeError:
        parsed_dates = parsed_dates.dt.tz_localize(None)
    df[date_col] = parsed_dates

    df = df.dropna(subset=[date_col, "Open", "High", "Low", "Close"])
    if df.empty:
        raise ValueError(
            "No se pudieron interpretar fechas ni datos numericos en el archivo."
        )

    df = df.sort_values(date_col)
    df = optimize_dtypes(df)
    return df, date_col


def filter_by_date(df: pd.DataFrame, date_col: str, start, end) -> pd.DataFrame:
    start_ts = pd.to_datetime(start)
    # Incluir todo el dia final
    end_ts = pd.to_datetime(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    mask = (df[date_col] >= start_ts) & (df[date_col] <= end_ts)
    return df.loc[mask]


def get_validated_tickers() -> list[str]:
    xtb_path = Path("xtb_verificado.csv")
    if not xtb_path.exists():
        return []
    df = pd.read_csv(xtb_path)
    validated = df[df["Validado"] == True]
    return sorted(validated["ticker.yf"].dropna().unique().tolist())


def get_sectors() -> list[str]:
    xtb_path = Path("xtb_verificado.csv")
    if not xtb_path.exists():
        return ["No especificado"]
    df = pd.read_csv(xtb_path)
    validated = df[df["Validado"] == True]
    sectors = validated["Sector"].fillna("No especificado").unique()
    return sorted(sectors.tolist())


def get_tickers_by_sector(sector: str | None = None) -> list[str]:
    xtb_path = Path("xtb_verificado.csv")
    if not xtb_path.exists():
        return []
    df = pd.read_csv(xtb_path)
    validated = df[df["Validado"] == True]
    if sector and sector != "Todos":
        validated = validated[validated["Sector"].fillna("No especificado") == sector]
    return sorted(validated["ticker.yf"].dropna().unique().tolist())
