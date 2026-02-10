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


def actualizar_datos_csv(path_csv: Path) -> bool:
    """
    Actualiza un archivo CSV con datos frescos de yfinance.

    Args:
        path_csv: Ruta al archivo CSV a actualizar

    Returns:
        bool: True si se actualizó correctamente, False si no
    """
    if not path_csv.exists():
        return False

    # Determinar ticker y tipo de datos desde el nombre del archivo
    filename = path_csv.stem

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
        # Guardar sobrescribiendo el archivo
        datos_nuevos.to_csv(path_csv, index=False)
        return True
    except Exception as e:
        print(f"Error al guardar CSV {path_csv}: {e}")
        return False
