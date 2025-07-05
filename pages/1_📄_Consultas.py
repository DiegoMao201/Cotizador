# pages/1_📄_Consultas.py
import streamlit as st
import pandas as pd
from utils import *

st.set_page_config(page_title="Consulta de Propuestas", page_icon="📄", layout="wide")
st.title("📄 Consulta y Gestión de Propuestas")

df_propuestas = listar_propuestas_df()

if df_propuestas.empty:
    st.warning("No se encontraron propuestas guardadas o no se pudieron cargar.")
else:
    st.header("🔍 Filtros de Búsqueda")
    # Filtros (sin cambios)...
    
    st.divider()
    st.header("📊 Resultados")
    st.dataframe(...) # Dataframe (sin cambios)...

    st.header("⚙️ Acciones")
    propuestas_para_seleccionar = df_filtrado['N° Propuesta'].tolist()
    
    if propuestas_para_seleccionar:
        prop_seleccionada = st.selectbox("Seleccione una propuesta para ver acciones:", options=[""] + propuestas_para_seleccionar)

        if prop_seleccionada:
            st.info(f"Ha seleccionado la propuesta **{prop_seleccionada}**.")
            
            # ### CAMBIO: Solución a TypeError y adición de botones ###
            col_cargar, col_pdf, col_mail = st.columns(3)
            with col_cargar:
                st.page_link(
                    "Cotizador_Ferreinox.py",
                    label="✏️ Cargar para Editar",
                    icon="✏️",
                    # Se asegura que el parámetro sea un string
                    query_params={"load_quote": str(prop_seleccionada)}
                )
            with col_pdf:
                # ### CAMBIO: Botón para descargar PDF directamente ###
                data_propuesta = get_full_proposal_data(prop_seleccionada)
                if data_propuesta:
                    # Lógica para generar PDF...
                    st.download_button(
                        label="📄 Descargar PDF",
                        data=bytes(), # Reemplazar con los bytes del PDF
                        file_name=f"Propuesta_{prop_seleccionada}.pdf",
                        mime="application/pdf"
                    )
            with col_mail:
                 # Lógica para botón de email...
                 pass
    else:
        st.info("Ninguna propuesta coincide con los filtros seleccionados.")
