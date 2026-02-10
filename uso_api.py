import numpy as np
import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError


def extractor(ticker_obj: yf.Ticker, hora: bool = False):
    if hora:
        empresa = ticker_obj.history(interval="1h", period="max")
        empresa.reset_index(inplace=True)
        empresa["Date"] = empresa["Datetime"]
    else:
        empresa = ticker_obj.history(period="max")
        empresa.reset_index(inplace=True)
    return empresa


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


def extrae_yf(ticker: str, hora: bool = False):
    ticker_obj = yf.Ticker(ticker)
    empresa = None
    try:
        empresa = extractor(ticker_obj, hora)
    except YFRateLimitError:
        print(f"Error rate limit al obtener datos de {ticker}.")
        from curl_cffi import requests

        session = requests.Session(impersonate="chrome")
        ticker_obj = yf.Ticker(ticker, session=session)
        empresa = extractor(ticker_obj, hora)
        session.close()
    except Exception as e:
        print(f"Otro error al obtener datos de {ticker}: {e}")

    if empresa is not None:
        empresa = optimize_dtypes(empresa)
        empresa.to_parquet(
            f"{'datos_horarios' if hora else 'datos_diarios'}/{ticker}{'_h' if hora else ''}.parquet"
        )

    return empresa


if __name__ == "__main__":
    ticker = "COPA.L"
    hora = False
    empresa = extrae_yf(ticker, hora=hora)
    print(empresa)
    if empresa is not None:
        empresa.to_parquet(f"data/Historicos/{ticker}{'_h' if hora else ''}.parquet")
