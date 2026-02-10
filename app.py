import streamlit as st

import graficos_comparacion
import graficos_unicos


st.set_page_config(page_title="Visor de velas", layout="wide")
st.title("Bolsa - Visualizaciones")
st.caption("Navega entre las pestañas para ver un solo grafico o comparar dos series.")

tab_unico, tab_comp = st.tabs(["Graficos unicos", "Graficos comparacion"])

with tab_unico:
    graficos_unicos.render()

with tab_comp:
    graficos_comparacion.render()
