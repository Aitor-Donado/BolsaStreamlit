# graficos_comparacion.py
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_utils import DATA_DIRS, filter_by_date, list_csv_files, load_prices


@st.cache_data(show_spinner=False)
def cached_load_prices(path: Path):
    return load_prices(path)


def render():
    st.subheader("Graficos comparacion")
    st.sidebar.header("Opciones - Comparacion")

    frequency = st.sidebar.radio("Frecuencia", list(DATA_DIRS.keys()), key="freq_comp")
    folder = DATA_DIRS[frequency]
    files = list_csv_files(folder)

    if len(files) < 2:
        st.info(f"Necesitas al menos dos ficheros csv en {folder} para comparar.")
        return

    file_one = st.sidebar.selectbox(
        "Archivo 1", files, format_func=lambda p: p.stem, index=0, key="file_comp_1"
    )
    file_two = st.sidebar.selectbox(
        "Archivo 2", files, format_func=lambda p: p.stem, index=1, key="file_comp_2"
    )

    if file_one == file_two:
        st.warning("Selecciona dos archivos distintos para comparar.")
        return

    try:
        df1, date_col1 = cached_load_prices(file_one)
        df2, date_col2 = cached_load_prices(file_two)
    except Exception as exc:  # pragma: no cover - feedback en UI
        st.error(str(exc))
        return

    min_overlap = max(df1[date_col1].min().date(), df2[date_col2].min().date())
    max_overlap = min(df1[date_col1].max().date(), df2[date_col2].max().date())
    if min_overlap > max_overlap:
        st.warning("No hay solape de fechas entre los dos archivos seleccionados.")
        return

    selected_range = st.sidebar.date_input(
        "Rango de fechas",
        value=(min_overlap, max_overlap),
        min_value=min_overlap,
        max_value=max_overlap,
        key="range_comp",
    )

    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date = end_date = selected_range

    df1_f = filter_by_date(df1, date_col1, start_date, end_date)
    df2_f = filter_by_date(df2, date_col2, start_date, end_date)

    common_dates = sorted(set(df1_f[date_col1].dt.date).intersection(set(df2_f[date_col2].dt.date)))
    df1_common = df1_f[df1_f[date_col1].dt.date.isin(common_dates)]
    df2_common = df2_f[df2_f[date_col2].dt.date.isin(common_dates)]

    if not common_dates:
        st.warning("No hay fechas u horas comunes en el rango seleccionado para el grafico principal.")
    else:
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df1_common[date_col1],
                    open=df1_common["Open"],
                    high=df1_common["High"],
                    low=df1_common["Low"],
                    close=df1_common["Close"],
                    name=file_one.name,
                ),
                go.Candlestick(
                    x=df2_common[date_col2],
                    open=df2_common["Open"],
                    high=df2_common["High"],
                    low=df2_common["Low"],
                    close=df2_common["Close"],
                    name=file_two.name,
                    increasing_line_color="royalblue",
                    decreasing_line_color="orange",
                ),
            ]
        )

        fig.update_layout(
            title=f"Comparacion: {file_one.name} vs {file_two.name} - {frequency}",
            xaxis_title="Fecha",
            yaxis_title="Precio",
            xaxis_rangeslider_visible=False,
            height=650,
        )

        st.plotly_chart(fig, width='stretch')

    # Ratio chart sobre union de fechas, rellenando con ultimo Close de cada serie
    union_index = sorted(set(df1_f[date_col1]).union(set(df2_f[date_col2])))

    def fill_missing(df, date_col):
        aligned = df.set_index(date_col).reindex(union_index).sort_index()
        close_filled = aligned["Close"].ffill()
        filled = aligned.copy()
        filled["Close"] = close_filled
        for col in ["Open", "High", "Low"]:
            filled[col] = aligned[col].combine_first(close_filled)
        return filled.dropna(subset=["Close"])

    df1_filled = fill_missing(df1_f, date_col1)
    df2_filled = fill_missing(df2_f, date_col2)

    common_idx = df1_filled.index.intersection(df2_filled.index)
    if common_idx.empty:
        st.warning("No hay datos suficientes para calcular el ratio.")
        return

    df1_ratio = df1_filled.loc[common_idx]
    df2_ratio = df2_filled.loc[common_idx]

    ratio_df = pd.DataFrame(index=common_idx)
    ratio_df["Open"] = df1_ratio["Open"] / df2_ratio["Open"]
    ratio_df["High"] = df1_ratio["High"] / df2_ratio["Low"]
    ratio_df["Low"] = df1_ratio["Low"] / df2_ratio["High"]
    ratio_df["Close"] = df1_ratio["Close"] / df2_ratio["Close"]
    ratio_df = ratio_df.replace([pd.NA, pd.NaT, float("inf"), -float("inf")], pd.NA).dropna()

    if ratio_df.empty:
        st.warning("No hay valores validos para el ratio en el rango seleccionado.")
        return

    ratio_fig = go.Figure(
        data=[
            go.Candlestick(
                x=ratio_df.index,
                open=ratio_df["Open"],
                high=ratio_df["High"],
                low=ratio_df["Low"],
                close=ratio_df["Close"],
                name="Ratio",
                increasing_line_color="green",
                decreasing_line_color="red",
            )
        ]
    )

    ratio_fig.update_layout(
        title=f"Ratio: {file_one.name} vs {file_two.name} - {frequency}",
        xaxis_title="Fecha",
        yaxis_title="Ratio",
        xaxis_rangeslider_visible=False,
        height=650,
    )

    st.plotly_chart(ratio_fig, width='stretch')

    if common_dates:
        with st.expander("Ver datos comunes"):
            st.write(f"Fechas comunes: {len(common_dates)}")
            st.dataframe(
                df1_common[[date_col1, "Open", "High", "Low", "Close"]]
                .reset_index(drop=True)
                .rename(columns={date_col1: "Fecha", "Open": f"A1 Open", "High": f"A1 High", "Low": f"A1 Low", "Close": f"A1 Close"})
            )
            st.dataframe(
                df2_common[[date_col2, "Open", "High", "Low", "Close"]]
                .reset_index(drop=True)
                .rename(columns={date_col2: "Fecha", "Open": f"A2 Open", "High": f"A2 High", "Low": f"A2 Low", "Close": f"A2 Close"})
            )

