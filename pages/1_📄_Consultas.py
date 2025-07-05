# pages/1_📄_Consultas.py
import streamlit as st
import pandas as pd
from utils import *
from state import QuoteState # Importar la clase QuoteState

st.set_page_config(page_title="Consulta de Propuestas", page_icon="📄", layout="wide")
st.title("📄 Consulta y Gestión de Propuestas")

workbook = connect_to_gsheets()
if not workbook:
    st.error("No se puede conectar a la base de datos para consultar propuestas.")
    st.stop()

# --- Mostrar tabla de propuestas ---
df_propuestas = listar_propuestas_df(workbook)

if df_propuestas.empty:
    st.warning("No se encontraron propuestas guardadas o no se pudieron cargar.")
else:
    st.info("Aquí puedes ver, filtrar y gestionar todas las propuestas comerciales guardadas.")
    # Aquí puedes agregar filtros si lo deseas, por ejemplo:
    # st.dataframe(df_propuestas) # Descomenta para ver la tabla completa
    
    st.header("⚙️ Acciones sobre una Propuesta")
    propuestas_para_seleccionar = [""] + df_propuestas['N° Propuesta'].tolist()
    prop_seleccionada = st.selectbox(
        "Seleccione una propuesta para ver acciones:", 
        options=propuestas_para_seleccionar
    )

    if prop_seleccionada:
        st.success(f"Propuesta seleccionada: **{prop_seleccionada}**")
        col_cargar, col_pdf, col_mail = st.columns(3)

        # --- Acción 1: Cargar para Editar ---
        # page_link es la forma moderna y correcta de crear estos enlaces
        col_cargar.page_link(
            "Cotizador_Ferreinox.py",
            label="✏️ Cargar para Editar",
            icon="✏️",
            # Pasamos el número de propuesta como un parámetro en la URL
            help=f"Abre la propuesta {prop_seleccionada} en el cotizador principal.",
            use_container_width=True
        )

        # --- Acciones 2 y 3: Descargar PDF y Enviar Email ---
        # Lógica corregida: Cargamos los datos en un objeto de estado temporal REAL.
        # Esto nos da acceso a todos los cálculos y datos formateados.
        
        # Usamos un objeto temporal para no interferir con el estado de la página principal
        temp_state = QuoteState()
        # El modo 'silent=True' evita que se muestren toasts o se modifiquen los query_params
        cargado_ok = temp_state.cargar_desde_gheets(prop_seleccionada, workbook, silent=True)
        
        if cargado_ok:
            # --- Acción 2: Descargar PDF ---
            pdf_bytes = generar_pdf_profesional(temp_state, workbook)
            col_pdf.download_button(
                label="📄 Descargar PDF",
                data=pdf_bytes,
                file_name=f"Propuesta_{prop_seleccionada}.pdf",
                mime="application/pdf",
                help=f"Genera y descarga un nuevo PDF para la propuesta {prop_seleccionada}.",
                use_container_width=True
            )

            # --- Acción 3: Enviar por Email ---
            email_cliente = temp_state.cliente_actual.get('Email', '')
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
