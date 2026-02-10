from pathlib import Path
import plotly.graph_objects as go
import streamlit as st

from data_utils import DATA_DIRS, filter_by_date, list_csv_files, load_prices


@st.cache_data(show_spinner=False)
def cached_load_prices(path: Path):
    return load_prices(path)


def render():
    st.subheader("Graficos unicos")
    st.sidebar.header("Opciones - Graficos unicos")

    frequency = st.sidebar.radio("Frecuencia", list(DATA_DIRS.keys()), key="freq_unico")
    folder = DATA_DIRS[frequency]
    files = list_csv_files(folder)

    if not files:
        st.info(f"No hay ficheros csv en {folder}")
        return

    selected = st.sidebar.selectbox(
        "Archivo", files, format_func=lambda p: p.stem, index=0, key="file_unico"
    )

    try:
        df, date_col = cached_load_prices(selected)
    except Exception as exc:  # pragma: no cover - feedback en UI
        st.error(str(exc))
        return

    min_date = df[date_col].min().date()
    max_date = df[date_col].max().date()

    range_default = (min_date, max_date)
    selected_range = st.sidebar.date_input(
        "Rango de fechas",
        value=range_default,
        min_value=min_date,
        max_value=max_date,
        key="range_unico",
    )

    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date = end_date = selected_range

    if start_date is None or end_date is None:
        st.warning("Elige un rango de fechas valido.")
        return

    filtered = filter_by_date(df, date_col, start_date, end_date)

    if filtered.empty:
        st.warning("No hay datos en el rango seleccionado.")
        return

    # Opciones de soportes y resistencias
    sr_enabled = st.sidebar.checkbox(
        "Trazar soportes/resistencias", value=True, key="sr_toggle_unico"
    )
    max_lookback = len(filtered)
    lookback = st.sidebar.number_input(
        "Lookback (ultimas N velas)",
        min_value=10,
        max_value=max_lookback,
        value=min(200, max_lookback),
        step=10,
        key="sr_lookback_unico",
    )
    num_levels = st.sidebar.slider(
        "Niveles por lado", min_value=1, max_value=10, value=5, key="sr_levels_unico"
    )

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=filtered[date_col],
                open=filtered["Open"],
                high=filtered["High"],
                low=filtered["Low"],
                close=filtered["Close"],
                name=selected.name,
            )
        ]
    )

    fig.update_layout(
        title=f"{selected.name} - {frequency}",
        xaxis_title="Fecha",
        yaxis_title="Precio",
        xaxis_rangeslider_visible=False,
        height=600,
    )

    if sr_enabled and lookback > 0:
        window = filtered.tail(int(lookback))
        # Seleccion simple: máximos y mínimos recientes sin duplicar valores
        resistencias = []
        for val in window["High"].nlargest(num_levels * 2):
            if all(abs(val - r) > 1e-9 for r in resistencias):
                resistencias.append(val)
            if len(resistencias) >= num_levels:
                break

        soportes = []
        for val in window["Low"].nsmallest(num_levels * 2):
            if all(abs(val - s) > 1e-9 for s in soportes):
                soportes.append(val)
            if len(soportes) >= num_levels:
                break

        for r in resistencias:
            fig.add_hline(
                y=r, line_dash="dot", line_color="orange", annotation_text=f"R {r:.2f}"
            )
        for s in soportes:
            fig.add_hline(
                y=s, line_dash="dot", line_color="green", annotation_text=f"S {s:.2f}"
            )

    st.plotly_chart(fig, width="stretch")

    with st.expander("Ver datos filtrados"):
        st.dataframe(filtered.reset_index(drop=True))
