# pages/1_📄_Consultas.py
import streamlit as st
import pandas as pd
from utils import *

st.set_page_config(page_title="Consulta de Propuestas", page_icon="📄", layout="wide")
st.title("📄 Consulta y Gestión de Propuestas")

workbook = connect_to_gsheets()
if not workbook:
    st.error("No se puede conectar a la base de datos para consultar propuestas."); st.stop()

df_propuestas = listar_propuestas_df(workbook)

if df_propuestas.empty:
    st.warning("No se encontraron propuestas guardadas o no se pudieron cargar.")
else:
    # Lógica de filtros y visualización del dataframe (sin cambios mayores)
    # ...
    # st.dataframe(df_filtrado)
    
    st.header("⚙️ Acciones")
    propuestas_para_seleccionar = df_propuestas['N° Propuesta'].tolist() # Simplificado
    prop_seleccionada = st.selectbox("Seleccione una propuesta para ver acciones:", options=[""] + propuestas_para_seleccionar)

    if prop_seleccionada:
        st.info(f"Ha seleccionado la propuesta **{prop_seleccionada}**.")
        col_cargar, col_pdf, col_mail = st.columns(3)

        # 1. Cargar para Editar
        col_cargar.page_link(
            "Cotizador_Ferreinox.py",
            label="✏️ Cargar para Editar",
            icon="✏️",
            query_params={"load_quote": str(prop_seleccionada)}
        )

        # 2. Descargar PDF y Enviar Email
        # Cargamos los datos solo una vez para ambas acciones
        data_propuesta = get_full_proposal_data(prop_seleccionada, workbook)
        if data_propuesta:
            # Reconstruimos un objeto QuoteState temporal para generar el PDF
            temp_state = type('QuoteState', (), {})() # Objeto vacío
            temp_state.numero_propuesta = data_propuesta['header'].get('numero_propuesta')
            temp_state.cliente_actual = {'Nombre': data_propuesta['header'].get('cliente_nombre')} # Simplificado
            temp_state.cotizacion_items = data_propuesta['items']
            temp_state.observaciones = data_propuesta['header'].get('observaciones')
            temp_state.vendedor = data_propuesta['header'].get('vendedor')
            
            # Recalculamos totales para el PDF
            df = pd.DataFrame(temp_state.cotizacion_items)
            temp_state.subtotal_bruto = (df['Cantidad'] * df['Precio Unitario']).sum()
            # ... (cálculos completos aquí si es necesario) ...
            
            pdf_bytes = generar_pdf_profesional(temp_state)
            col_pdf.download_button(
                label="📄 Descargar PDF",
                data=pdf_bytes,
                file_name=f"Propuesta_{prop_seleccionada}.pdf",
                mime="application/pdf"
            )

            email_cliente = data_propuesta['header'].get('cliente_email', '')
            if email_cliente:
                asunto = f"Copia de Propuesta Comercial - {prop_seleccionada}"
                cuerpo = f"Estimado(a),\n\nAdjunto encontrará una copia de nuestra propuesta comercial.\n\nAtentamente,\n{temp_state.vendedor}"
                mailto_link = generar_mailto_link(email_cliente, asunto, cuerpo)
                col_mail.link_button("📧 Enviar Copia", mailto_link)
