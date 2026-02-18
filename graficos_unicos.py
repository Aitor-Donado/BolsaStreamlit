from pathlib import Path
import plotly.graph_objects as go
import streamlit as st
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from data_utils import (
    DATA_DIRS,
    filter_by_date,
    list_parquet_files,
    load_prices,
    get_sectors,
    get_tickers_by_sector,
)
from data_updater import actualizar_datos_parquet


@st.cache_data(show_spinner=False)
def cached_load_prices(path: Path):
    return load_prices(path)


def detect_support_resistance_pivots(high_prices, low_prices, order=5):
    """
    Detecta pivots (máximos y mínimos locales) para identificar soportes y resistencias.
    """
    # Encontrar máximos locales
    max_idx = argrelextrema(high_prices.values, np.greater, order=order)[0]
    resistances = high_prices.iloc[max_idx]

    # Encontrar mínimos locales
    min_idx = argrelextrema(low_prices.values, np.less, order=order)[0]
    supports = low_prices.iloc[min_idx]

    return supports, resistances


def cluster_levels(levels, threshold_percent=0.02):
    """
    Agrupa niveles de precio que estén cercanos entre sí.
    threshold_percent: porcentaje del precio para considerar agrupación (ej: 2%)
    """
    if len(levels) == 0:
        return []

    # Ordenar niveles
    sorted_levels = sorted(levels)
    clusters = []
    current_cluster = [sorted_levels[0]]

    for level in sorted_levels[1:]:
        # Calcular diferencia porcentual con el último nivel del cluster actual
        last_in_cluster = current_cluster[-1]
        diff_percent = abs(level - last_in_cluster) / last_in_cluster * 100

        if diff_percent <= threshold_percent:
            current_cluster.append(level)
        else:
            # Calcular el nivel representativo del cluster (promedio o mediana)
            clusters.append(np.mean(current_cluster))
            current_cluster = [level]

    if current_cluster:
        clusters.append(np.mean(current_cluster))

    return clusters


def find_swing_levels(df, lookback, num_levels=5, pivot_order=5, merge_threshold=1.0):
    """
    Encuentra niveles de soporte y resistencia usando múltiples métodos.
    """
    window = df.tail(int(lookback))

    # Método 1: Pivots locales
    supports_pivot, resistances_pivot = detect_support_resistance_pivots(
        window["High"], window["Low"], order=pivot_order
    )

    # Método 2: Máximos y mínimos recientes
    resistances_extreme = window["High"].nlargest(num_levels * 3).values
    supports_extreme = window["Low"].nsmallest(num_levels * 3).values

    # Combinar todos los niveles
    all_resistances = list(resistances_pivot.values) + list(resistances_extreme)
    all_supports = list(supports_pivot.values) + list(supports_extreme)

    # Eliminar duplicados y agrupar niveles cercanos
    unique_resistances = list(set(all_resistances))
    unique_supports = list(set(all_supports))

    # Agrupar niveles cercanos
    resistances_clustered = cluster_levels(
        unique_resistances, threshold_percent=merge_threshold
    )
    supports_clustered = cluster_levels(
        unique_supports, threshold_percent=merge_threshold
    )

    # Ordenar y seleccionar los niveles más importantes
    resistances_clustered.sort(reverse=True)
    supports_clustered.sort()

    return resistances_clustered[:num_levels], supports_clustered[:num_levels]


def render():
    st.subheader("Gráficos únicos")
    st.sidebar.header("Opciones - Gráficos únicos")

    frequency = st.sidebar.radio("Frecuencia", list(DATA_DIRS.keys()), key="freq_unico")
    folder = DATA_DIRS[frequency]
    # files = list_parquet_files(folder)

    sectors = ["Todos"] + get_sectors()
    selected_sector = st.sidebar.selectbox(
        "Sector", sectors, index=0, key="sector_unico"
    )

    tickers_filtered = get_tickers_by_sector(selected_sector)

    if not tickers_filtered:
        st.info(f"No hay tickers validados para el sector {selected_sector}")
        return

    selected_ticker = st.sidebar.selectbox(
        "Ticker", tickers_filtered, index=0, key="ticker_unico"
    )
    selected = folder / f"{selected_ticker}.parquet"

    if not selected.exists():
        st.warning(
            f"No existe archivo para {selected_ticker}. Descarga los datos primero."
        )
        return

    # Botón para actualizar datos
    if st.sidebar.button("🔄 Actualizar datos", key="update_data_unico"):
        with st.spinner(f"Actualizando datos de {selected.name}..."):
            success = actualizar_datos_parquet(selected)
            if success:
                st.success(f"✅ Datos de {selected.name} actualizados correctamente")
                # Limpiar caché para recargar datos frescos
                cached_load_prices.clear()
                # Recargar datos
                try:
                    df, date_col = cached_load_prices(selected)
                    min_date = df[date_col].min().date()
                    max_date = df[date_col].max().date()
                except Exception as exc:
                    st.error(f"Error al recargar datos: {exc}")
                    return
            else:
                st.error(f"❌ No se pudieron actualizar los datos de {selected.name}")
                st.info(
                    "Verifique que el ticker sea válido y que haya conexión a internet"
                )

    try:
        df, date_col = cached_load_prices(selected)
    except Exception as exc:
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
        st.warning("Elige un rango de fechas válido.")
        return

    filtered = filter_by_date(df, date_col, start_date, end_date)

    if filtered.empty:
        st.warning("No hay datos en el rango seleccionado.")
        return

    # Opciones avanzadas de soportes y resistencias
    sr_enabled = st.sidebar.checkbox(
        "Trazar soportes/resistencias", value=True, key="sr_toggle_unico"
    )

    if sr_enabled:
        st.sidebar.subheader("Configuración S/R")

        max_lookback = len(filtered)
        lookback = st.sidebar.number_input(
            "Lookback (últimas N velas)",
            min_value=10,
            max_value=max_lookback,
            value=min(200, max_lookback),
            step=10,
            key="sr_lookback_unico",
            help="Número de velas hacia atrás para calcular S/R",
        )

        num_levels = st.sidebar.slider(
            "Niveles máximos por lado",
            min_value=1,
            max_value=20,
            value=5,
            key="sr_levels_unico",
        )

        # Método de detección
        detection_method = st.sidebar.selectbox(
            "Método de detección",
            ["Pivots Locales", "Máximos/Mínimos", "Combinado"],
            index=2,
            help="Pivots: usa máximos/minimos locales. Máximos/Mínimos: precios extremos. Combinado: ambos métodos.",
        )

        # Parámetros avanzados
        with st.sidebar.expander("Parámetros avanzados"):
            pivot_order = st.slider(
                "Orden de pivots",
                min_value=1,
                max_value=20,
                value=5,
                help="Número de velas a cada lado para considerar un pivot",
            )

            merge_threshold = st.slider(
                "Umbral de agrupación (%)",
                min_value=0.1,
                max_value=5.0,
                value=1.0,
                step=0.1,
                help="Porcentaje de diferencia para agrupar niveles cercanos",
            )

            min_touches = st.slider(
                "Mínimo de toques",
                min_value=1,
                max_value=5,
                value=2,
                help="Número mínimo de toques para considerar un nivel válido",
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
        # Calcular soportes y resistencias según el método seleccionado
        if detection_method == "Pivots Locales":
            supports, resistances = detect_support_resistance_pivots(
                filtered.tail(int(lookback))["High"],
                filtered.tail(int(lookback))["Low"],
                order=pivot_order,
            )
            resistances = cluster_levels(list(resistances.values), merge_threshold)[
                :num_levels
            ]
            supports = cluster_levels(list(supports.values), merge_threshold)[
                :num_levels
            ]

        elif detection_method == "Máximos/Mínimos":
            window = filtered.tail(int(lookback))
            resistances = window["High"].nlargest(num_levels * 3).values
            supports = window["Low"].nsmallest(num_levels * 3).values

            # Agrupar niveles cercanos
            resistances = cluster_levels(resistances, merge_threshold)[:num_levels]
            supports = cluster_levels(supports, merge_threshold)[:num_levels]

        else:  # Combinado
            resistances, supports = find_swing_levels(
                filtered, lookback, num_levels, pivot_order, merge_threshold
            )

        # Dibujar resistencias
        for i, r in enumerate(resistances):
            fig.add_hline(
                y=r,
                line_dash="dot",
                line_color="orange",
                line_width=1.5 if i == 0 else 1.0,
                annotation_text=f"R {i + 1}: {r:.2f}",
                annotation_position="top right",
                annotation_font_size=10,
            )

        # Dibujar soportes
        for i, s in enumerate(supports):
            fig.add_hline(
                y=s,
                line_dash="dot",
                line_color="green",
                line_width=1.5 if i == 0 else 1.0,
                annotation_text=f"S {i + 1}: {s:.2f}",
                annotation_position="bottom right",
                annotation_font_size=10,
            )

        # Mostrar información sobre los niveles encontrados
        with st.expander("Detalles de niveles S/R"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Resistencias:**")
                for i, r in enumerate(resistances):
                    st.write(f"R{i + 1}: {r:.2f}")

            with col2:
                st.write("**Soportes:**")
                for i, s in enumerate(supports):
                    st.write(f"S{i + 1}: {s:.2f}")

    st.plotly_chart(fig, width="stretch")

    with st.expander("Ver datos filtrados"):
        st.dataframe(filtered.reset_index(drop=True))


if __name__ == "__main__":
    render()
