# pages/1_📄_Consultas.py
import streamlit as st
import pandas as pd
from utils import *
from state import QuoteState
from datetime import datetime, date

# --- Configuración de la página ---
st.set_page_config(page_title="Consulta de Propuestas", page_icon="📄", layout="wide")
st.title("📄 Consulta y Gestión de Propuestas")

# --- Conexión a la base de datos ---
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

    # --- Aplicar filtros ---
    df_filtrado = df_propuestas.copy()
    if clientes_seleccionados:
        df_filtrado = df_filtrado[df_filtrado['Cliente'].isin(clientes_seleccionados)]
    
    # Asegurarse de que la columna Fecha sea de tipo datetime para comparar
    df_filtrado['Fecha'] = pd.to_datetime(df_filtrado['Fecha'], errors='coerce').dt.date

    if fecha_inicio:
        df_filtrado = df_filtrado[df_filtrado['Fecha'] >= fecha_inicio]
    if fecha_fin:
        df_filtrado = df_filtrado[df_filtrado['Fecha'] <= fecha_fin]

    # --- Mostrar DataFrame filtrado ---
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    
    # --- SECCIÓN DE ACCIONES ---
    st.header("⚙️ Acciones sobre una Propuesta")
    
    propuestas_para_seleccionar = [""] + df_filtrado['N° Propuesta'].tolist()
    prop_seleccionada = st.selectbox(
        "Seleccione una propuesta para ver acciones:", 
        options=propuestas_para_seleccionar
    )

    if prop_seleccionada:
        st.success(f"Propuesta seleccionada: **{prop_seleccionada}**")
        col_cargar, col_pdf, col_mail = st.columns(3)

        # --- SOLUCIÓN ALTERNATIVA CON st.button Y st.session_state ---
        # Al hacer clic, guardamos la propuesta a cargar y cambiamos de página.
        # Este método es más robusto que st.page_link.
        if col_cargar.button("✏️ Cargar para Editar", use_container_width=True):
            st.session_state['load_quote'] = prop_seleccionada
            st.switch_page("Cotizador_Ferreinox.py")
        
        # --- Acciones 2 y 3: Descargar PDF y Enviar Email ---
        temp_state = QuoteState()
        cargado_ok = temp_state.cargar_desde_gheets(prop_seleccionada, workbook, silent=True)
        
        if cargado_ok:
            # Generar PDF para descarga
            pdf_bytes = generar_pdf_profesional(temp_state, workbook)
            nombre_archivo_pdf = f"Propuesta_{prop_seleccionada}.pdf"
            
            col_pdf.download_button(
                label="📄 Descargar PDF",
                data=pdf_bytes,
                file_name=nombre_archivo_pdf,
                help=f"Genera y descarga un nuevo PDF para la propuesta {prop_seleccionada}.",
                use_container_width=True
            )
            
            # Botón para enviar copia por email
            with col_mail:
                if st.button("📧 Enviar Copia", use_container_width=True):
                    email_cliente = temp_state.cliente_actual.get(CLIENTE_EMAIL_COL, '')
                    if email_cliente:
                        with st.spinner("Enviando correo..."):
                            exito, mensaje = enviar_email_seguro(
                                email_cliente, 
                                temp_state, 
                                pdf_bytes, 
                                nombre_archivo_pdf, 
                                is_copy=True
                            )
                            if exito:
                                st.success(mensaje)
                            else:
                                st.error(mensaje)
                    else:
                        st.warning("Cliente sin email registrado para enviar copia.")
        else:
            st.error(f"No se pudieron cargar los detalles completos para la propuesta {prop_seleccionada}.")
