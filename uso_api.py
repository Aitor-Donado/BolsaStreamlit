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

def extrae_yf(ticker: str, hora: bool = False):
    ticker_obj = yf.Ticker(ticker)
    try:
        empresa = extractor(ticker_obj, hora)
        return empresa
    except YFRateLimitError:
        print(f"Error rate limit al obtener datos de {ticker}.")
        from curl_cffi import requests
        session = requests.Session(impersonate="chrome")
        ticker_obj = yf.Ticker(ticker, session=session)
        empresa = extractor(ticker_obj, hora)
        session.close()
        return empresa
    except Exception as e:
        print(f"Otro error al obtener datos de {ticker}: {e}")
        return None
    finally:
        empresa.to_csv(f"{'datos_horarios' if hora else 'datos_diarios'}/{ticker}{'_h' if hora else ''}.csv")


if __name__ == "__main__":
    ticker = "COPA.L"
    hora = False
    empresa = extrae_yf(ticker, hora=hora)
    print(empresa)
    empresa.to_csv(f"data/Historicos/{ticker}{'_h' if hora else ''}.csv")