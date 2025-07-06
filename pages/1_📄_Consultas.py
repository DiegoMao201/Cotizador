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

df_propuestas = listar_propuestas_df(workbook)

if df_propuestas.empty:
    st.warning("No se encontraron propuestas guardadas o no se pudieron cargar.")
else:
    st.header("🔍 Filtrar Propuestas")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            if PROPUESTA_CLIENTE_COL in df_propuestas.columns:
                clientes_disponibles = sorted(df_propuestas[PROPUESTA_CLIENTE_COL].dropna().astype(str).unique())
                clientes_seleccionados = st.multiselect(
                    "Filtrar por Cliente:",
                    options=clientes_disponibles,
                    placeholder="Seleccione uno o más clientes"
                )
            else:
                st.warning(f"La columna '{PROPUESTA_CLIENTE_COL}' no se encontró en la hoja '{PROPUESTAS_SHEET_NAME}'. No se puede filtrar por cliente.")
                clientes_seleccionados = []


        with col2:
            fecha_inicio = st.date_input("Desde:", value=None, format="YYYY/MM/DD")
            fecha_fin = st.date_input("Hasta:", value=None, format="YYYY/MM/DD")

    df_filtrado = df_propuestas.copy()
    if clientes_seleccionados and PROPUESTA_CLIENTE_COL in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado[PROPUESTA_CLIENTE_COL].isin(clientes_seleccionados)]
    
    if not df_filtrado.empty and 'fecha_creacion' in df_filtrado.columns:
        df_filtrado['fecha_creacion_dt'] = pd.to_datetime(df_filtrado['fecha_creacion'], errors='coerce').dt.date

        if fecha_inicio:
            df_filtrado = df_filtrado[df_filtrado['fecha_creacion_dt'] >= fecha_inicio]
        if fecha_fin:
            df_filtrado = df_filtrado[df_filtrado['fecha_creacion_dt'] <= fecha_fin]

    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    
    st.header("⚙️ Acciones sobre una Propuesta")
    
    if not df_filtrado.empty and 'numero_propuesta' in df_filtrado.columns:
        propuestas_para_seleccionar = [""] + df_filtrado['numero_propuesta'].tolist()
        prop_seleccionada = st.selectbox(
            "Seleccione una propuesta para ver acciones:", 
            options=propuestas_para_seleccionar,
            key="consulta_prop_sel" # Se añade una clave para evitar conflictos
        )

        if prop_seleccionada:
            st.success(f"Propuesta seleccionada: **{prop_seleccionada}**")
            
            temp_state = QuoteState()
            cargado_ok = temp_state.cargar_desde_gheets(prop_seleccionada, workbook, silent=True)
            
            if cargado_ok:
                st.subheader("Acciones Principales")
                col_cargar, col_pdf, col_mail = st.columns(3)

                if col_cargar.button("✏️ Cargar para Editar", use_container_width=True):
                    st.session_state['load_quote'] = prop_seleccionada
                    st.switch_page("pages/0_⚙️_Cotizador.py")
                
                pdf_bytes_consulta = generar_pdf_profesional(temp_state, workbook)
                nombre_archivo_pdf_consulta = f"Propuesta_{prop_seleccionada}.pdf"
                
                col_pdf.download_button(
                    label="📄 Descargar PDF",
                    data=pdf_bytes_consulta,
                    file_name=nombre_archivo_pdf_consulta,
                    use_container_width=True,
                    disabled=(pdf_bytes_consulta is None)
                )
                
                with col_mail:
                    if st.button("📧 Enviar Copia por Email", use_container_width=True, disabled=(pdf_bytes_consulta is None)):
                        email_cliente = temp_state.cliente_actual.get(CLIENTE_EMAIL_COL, '')
                        if email_cliente:
                            with st.spinner("Enviando correo..."):
                                exito, mensaje = enviar_email_seguro(email_cliente, temp_state, pdf_bytes_consulta, nombre_archivo_pdf_consulta, is_copy=True)
                                if exito: st.success(mensaje)
                                else: st.error(mensaje)
                        else:
                            st.warning("Cliente sin email registrado para enviar copia.")
                
                # --- SECCIÓN DE WHATSAPP NUEVA Y CORREGIDA ---
                st.divider()
                st.subheader("Compartir por WhatsApp (con enlace al PDF)")
                
                telefono_consulta = st.text_input(
                    "Teléfono del Cliente (para WhatsApp):", 
                    value=temp_state.cliente_actual.get("Teléfono", ""),
                    key="consulta_telefono"
                )

                if st.button("🚀 Generar Enlace de WhatsApp para esta Propuesta", use_container_width=True, type="primary", disabled=(not telefono_consulta)):
                    if pdf_bytes_consulta:
                        with st.spinner("Guardando PDF en Drive y generando enlace..."):
                            exito_drive, resultado_drive = guardar_pdf_en_drive(workbook, pdf_bytes_consulta, nombre_archivo_pdf_consulta)
                            
                            if exito_drive:
                                file_id = resultado_drive
                                link_pdf_publico = f"https://drive.google.com/file/d/{file_id}/view"
                                st.info(f"✅ PDF guardado en Google Drive. [Abrir PDF]({link_pdf_publico})")
                                st.success("✅ ¡Acción realizada con éxito! El botón de WhatsApp está listo.")
                                st.session_state['whatsapp_link_html_consulta'] = generar_boton_whatsapp(temp_state, telefono_consulta, link_pdf_publico)
                            else:
                                error_msg = resultado_drive
                                st.error(error_msg)
                                st.session_state['whatsapp_link_html_consulta'] = None
                    else:
                        st.error("No se pudo generar el PDF para subirlo.")

                if 'whatsapp_link_html_consulta' in st.session_state and st.session_state.get('whatsapp_link_html_consulta'):
                    st.markdown(st.session_state['whatsapp_link_html_consulta'], unsafe_allow_html=True)
            else:
                st.error(f"No se pudieron cargar los detalles completos para la propuesta {prop_seleccionada}.")
