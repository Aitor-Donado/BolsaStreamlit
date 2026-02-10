import numpy as np
import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError
from pathlib import Path


def extrae_datos_yf(ticker: str, hora: bool = False):
    """
    Extrae datos de yfinance con manejo de errores y fallback a curl_cffi.

    Args:
        ticker: Símbolo del ticker (ej: "IBE.MC")
        hora: Si True, obtiene datos horarios, si False, datos diarios

    Returns:
        pd.DataFrame con datos históricos o None si falla
    """

    def extractor(ticker_obj: yf.Ticker, hora: bool = False):
        if hora:
            empresa = ticker_obj.history(interval="1h", period="max")
            empresa.reset_index(inplace=True)
            empresa["Date"] = empresa["Datetime"]
        else:
            empresa = ticker_obj.history(period="max")
            empresa.reset_index(inplace=True)
        return empresa

    try:
        ticker_obj = yf.Ticker(ticker)
        empresa = extractor(ticker_obj, hora)
        if empresa.empty:
            return None
        return empresa
    except YFRateLimitError:
        try:
            from curl_cffi import requests

            session = requests.Session(impersonate="chrome")
            ticker_obj = yf.Ticker(ticker, session=session)
            empresa = extractor(ticker_obj, hora)
            session.close()
            if empresa.empty:
                return None
            return empresa
        except ImportError:
            print("curl_cffi no disponible para fallback.")
            return None
        except Exception as e:
            print(f"Error en fallback curl_cffi para {ticker}: {e}")
            return None
    except Exception as e:
        print(f"Error al obtener datos de {ticker}: {e}")
        return None


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimiza los tipos de datos para reducir el espacio y mejorar el rendimiento.
    """
    # Reducir precisión de columnas float a float32
    float_columns = ["Close", "High", "Low", "Open", "Dividends", "Stock Splits"]
    for col in float_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].astype(np.float32)

    # Reducir precisión de columnas int a int32
    int_columns = ["Volume"]
    for col in int_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].astype(np.int32)

    return df


def actualizar_datos_parquet(path_parquet: Path) -> bool:
    """
    Actualiza un archivo Parquet con datos frescos de yfinance.

    Args:
        path_parquet: Ruta al archivo Parquet a actualizar

    Returns:
        bool: True si se actualizó correctamente, False si no
    """
    if not path_parquet.exists():
        return False

    # Determinar ticker y tipo de datos desde el nombre del archivo
    filename = path_parquet.stem

    # Casos especiales: archivos horarios que terminan en "_h"
    if filename.endswith("_h"):
        ticker = filename[:-2]  # Quitar "_h"
        hora = True
    else:
        ticker = filename
        hora = False

    # Extraer datos frescos
    datos_nuevos = extrae_datos_yf(ticker, hora)

    if datos_nuevos is None or datos_nuevos.empty:
        return False

    # Verificar columnas requeridas
    columnas_requeridas = ["Open", "High", "Low", "Close"]
    fecha_col = "Date" if "Date" in datos_nuevos.columns else "Datetime"

    if not all(col in datos_nuevos.columns for col in columnas_requeridas):
        return False

    if fecha_col not in datos_nuevos.columns:
        return False

    try:
        # Optimizar tipos de datos antes de guardar
        datos_nuevos = optimize_dtypes(datos_nuevos)
        # Guardar sobrescribiendo el archivo
        datos_nuevos.to_parquet(path_parquet, index=False)
        return True
    except Exception as e:
        print(f"Error al guardar Parquet {path_parquet}: {e}")
        return False
