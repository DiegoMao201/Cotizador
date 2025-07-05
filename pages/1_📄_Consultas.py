# pages/1_📄_Consultas.py
import streamlit as st
import pandas as pd
from utils import *
from state import QuoteState
from datetime import datetime, date

st.set_page_config(page_title="Consulta de Propuestas", page_icon="📄", layout="wide")
st.title("📄 Consulta y Gestión de Propuestas")

workbook = connect_to_gsheets()
if not workbook:
    st.error("No se puede conectar a la base de datos para consultar propuestas.")
    st.stop()

# --- Cargar y mostrar tabla de propuestas ---
df_propuestas = listar_propuestas_df(workbook)

if df_propuestas.empty:
    st.warning("No se encontraron propuestas guardadas o no se pudieron cargar.")
else:
    # --- SECCIÓN DE FILTROS ---
    st.header("🔍 Filtrar Propuestas")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            clientes_disponibles = sorted(df_propuestas['Cliente'].dropna().unique())
            clientes_seleccionados = st.multiselect(
                "Filtrar por Cliente:",
                options=clientes_disponibles,
                placeholder="Seleccione uno o más clientes"
            )

        with col2:
            fecha_inicio = st.date_input("Desde:", value=None, format="YYYY/MM/DD")
            fecha_fin = st.date_input("Hasta:", value=None, format="YYYY/MM/DD")

    # Aplicar filtros
    df_filtrado = df_propuestas.copy()
    if clientes_seleccionados:
        df_filtrado = df_filtrado[df_filtrado['Cliente'].isin(clientes_seleccionados)]
    
    if fecha_inicio:
        # Asegurarse de que la columna Fecha sea de tipo datetime para comparar
        df_filtrado['Fecha'] = pd.to_datetime(df_filtrado['Fecha']).dt.date
        df_filtrado = df_filtrado[df_filtrado['Fecha'] >= fecha_inicio]
    if fecha_fin:
        df_filtrado['Fecha'] = pd.to_datetime(df_filtrado['Fecha']).dt.date
        df_filtrado = df_filtrado[df_filtrado['Fecha'] <= fecha_fin]

    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    
    st.header("⚙️ Acciones sobre una Propuesta")
    
    propuestas_para_seleccionar = [""] + df_filtrado['N° Propuesta'].tolist()
    prop_seleccionada = st.selectbox(
        "Seleccione una propuesta para ver acciones:", 
        options=propuestas_para_seleccionar
    )

    if prop_seleccionada:
        st.success(f"Propuesta seleccionada: **{prop_seleccionada}**")
        col_cargar, col_pdf, col_mail = st.columns(3)

        # --- Acción 1: Cargar para Editar (SOLUCIÓN ROBUSTA) ---
        link_cargar = f'<a href="/?load_quote={prop_seleccionada}" target="_self" style="display:inline-block;padding:0.5em 1em;background-color:#0068c9;color:white;border-radius:0.5em;text-decoration:none;">✏️ Cargar para Editar</a>'
        col_cargar.markdown(link_cargar, unsafe_allow_html=True)
        
        # --- Acciones 2 y 3: Descargar PDF y Enviar Email ---
        temp_state = QuoteState()
        cargado_ok = temp_state.cargar_desde_gheets(prop_seleccionada, workbook, silent=True)
        
        if cargado_ok:
            pdf_bytes = generar_pdf_profesional(temp_state, workbook)
            col_pdf.download_button(
                label="📄 Descargar PDF",
                data=pdf_bytes,
                file_name=f"Propuesta_{prop_seleccionada}.pdf",
                mime="application/pdf",
                help=f"Genera y descarga un nuevo PDF para la propuesta {prop_seleccionada}.",
                use_container_width=True
            )
            email_cliente = temp_state.cliente_actual.get(CLIENTE_EMAIL_COL, '')
            if email_cliente:
                asunto = f"Copia de Propuesta Comercial - {prop_seleccionada}"
                cuerpo = f"Estimado(a) {temp_state.cliente_actual.get('Nombre', 'Cliente')},\n\nAdjunto encontrará una copia de nuestra propuesta comercial.\n\nAtentamente,\n{temp_state.vendedor}"
                mailto_link = generar_mailto_link(email_cliente, asunto, cuerpo)
                col_mail.link_button(
                    "📧 Enviar Copia", 
                    mailto_link, 
                    help=f"Abre tu cliente de correo para enviar el PDF a {email_cliente}.",
                    use_container_width=True
                )
            else:
                col_mail.warning("Cliente sin email registrado.")
        else:
            st.error(f"No se pudieron cargar los detalles completos para la propuesta {prop_seleccionada}.")
