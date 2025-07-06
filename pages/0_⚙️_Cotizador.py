# pages/0_⚙️_Cotizador.py
import streamlit as st
import pandas as pd
from state import QuoteState
from utils import *

st.title("🔩 Cotizador Profesional Ferreinox")

workbook = connect_to_gsheets()
if not workbook:
    st.error("La aplicación no puede continuar sin conexión a la base de datos.")
    st.stop()

if 'state' not in st.session_state:
    st.session_state.state = QuoteState()
state = st.session_state.state

if st.session_state.get('load_quote'):
    numero_a_cargar = st.session_state.pop('load_quote')
    state.cargar_desde_gheets(numero_a_cargar, workbook)
    st.rerun()

if state.numero_propuesta and "TEMP" not in state.numero_propuesta:
    st.info(f"✍️ **Modo Edición:** Estás modificando la cotización **{state.numero_propuesta}**.")
else:
    st.info("✨ **Modo Creación:** Estás creando una cotización nueva.")

df_productos, df_clientes = cargar_datos_maestros(workbook)

with st.sidebar:
    st.title("⚙️ Controles")
    def actualizar_vendedor():
        state.set_vendedor(st.session_state.vendedor_input)
    st.text_input(
        "Vendedor/Asesor:", value=state.vendedor,
        placeholder="Tu nombre", on_change=actualizar_vendedor, key="vendedor_input"
    )
    st.divider()
    st.button("🗑️ Iniciar Cotización Nueva", use_container_width=True, on_click=state.reiniciar_cotizacion)

st.header("1. Cliente")
with st.container(border=True):
    if df_clientes.empty:
        st.warning("No hay clientes en la base de datos.")
    else:
        lista_clientes = [""] + sorted(df_clientes[CLIENTE_NOMBRE_COL].dropna().astype(str).unique().tolist())
        current_client_name = state.cliente_actual.get(CLIENTE_NOMBRE_COL, "")
        try:
            idx = lista_clientes.index(current_client_name) if current_client_name else 0
        except ValueError:
            idx = 0
        cliente_sel_nombre = st.selectbox("Buscar o seleccionar cliente:", options=lista_clientes, index=idx)
        if cliente_sel_nombre and cliente_sel_nombre != current_client_name:
            cliente_dict = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0].to_dict()
            state.set_cliente(cliente_dict)
            st.rerun()
    if state.cliente_actual:
        st.success(f"Cliente en cotización: **{state.cliente_actual.get(CLIENTE_NOMBRE_COL, '')}**")

st.header("2. Productos")
with st.container(border=True):
    if df_productos.empty:
        st.warning("No hay productos en la base de datos para seleccionar.")
    else:
        producto_sel_str = st.selectbox("Buscar producto:", options=[""] + df_productos['Busqueda'].tolist(), index=0, placeholder="Escribe para buscar...")
        if producto_sel_str:
            info_producto = df_productos[df_productos['Busqueda'] == producto_sel_str].iloc[0]
            st.markdown(f"**Producto Seleccionado:** {info_producto[NOMBRE_PRODUCTO_COL]}")
            c1, c2 = st.columns([1, 2])
            c1.metric("Stock Disponible", f"{info_producto.get(STOCK_COL, 0)} uds.")
            cantidad = c2.number_input("Cantidad:", min_value=1, value=1, step=1)
            opciones_precio = {f"{l.replace(',', '')}": info_producto.get(l, 0)
                                for l in PRECIOS_COLS if pd.notna(info_producto.get(l)) and str(info_producto.get(l, 0)).replace('.','',1).isdigit()}
            if opciones_precio:
                precio_sel_str = st.radio("Listas de Precio:", options=opciones_precio.keys(), horizontal=True)
                if st.button("➕ Agregar a la Cotización", use_container_width=True, type="primary"):
                    state.agregar_item(info_producto.to_dict(), cantidad, opciones_precio[precio_sel_str])
                    st.rerun()
            else:
                st.warning("Este producto no tiene precios definidos.")

st.header("3. Resumen y Generación")
with st.container(border=True):
    if not state.cotizacion_items:
        st.info("Añada productos para ver el resumen.")
    else:
        df_items = pd.DataFrame(state.cotizacion_items)
        columnas_visibles = ['Referencia', 'Producto', 'Cantidad', 'Precio Unitario', 'Descuento (%)', 'Total']
        df_display = df_items[columnas_visibles]

        edited_df = st.data_editor(
            df_display,
            column_config={
                "Referencia": st.column_config.TextColumn(disabled=True),
                "Producto": st.column_config.TextColumn(label="Descripción del Producto", required=True),
                "Cantidad": st.column_config.NumberColumn(label="Cant.", required=True, min_value=1),
                "Precio Unitario": st.column_config.NumberColumn(label="Vlr. Unitario", format="$%.2f", required=True),
                "Descuento (%)": st.column_config.NumberColumn(label="Desc. %", min_value=0, max_value=100, step=1, format="%.1f%%", required=True),
                "Total": st.column_config.NumberColumn(format="$%.2f", disabled=True),
            },
            use_container_width=True, hide_index=True, num_rows="dynamic", key="data_editor_items")

        if not edited_df.equals(df_display):
            state.actualizar_items_desde_vista(edited_df)
            st.rerun()
            
        st.subheader("Resumen Financiero")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Subtotal Bruto", f"${state.subtotal_bruto:,.2f}")
        m2.metric("Descuento Total", f"-${state.descuento_total:,.2f}")
        m3.metric(f"IVA ({TASA_IVA:.0%})", f"${state.iva_valor:,.2f}")
        m4.metric("TOTAL GENERAL", f"${state.total_general:,.2f}")
        
        state.observaciones = st.text_area("Observaciones y Términos:", value=state.observaciones, height=100, on_change=state.persist_to_session)
        
        st.divider()
        st.subheader("Acciones Finales")
        col_accion1, col_accion2 = st.columns([2, 1])
        idx_status = ESTADOS_COTIZACION.index(state.status) if state.status in ESTADOS_COTIZACION else 0
        state.status = col_accion1.selectbox("Establecer Estado:", options=ESTADOS_COTIZACION, index=idx_status)
        
        col_accion2.write(""); col_accion2.write("")
        col_accion2.button("💾 Guardar en la Nube", use_container_width=True, type="primary", on_click=handle_save, args=(workbook, state))

        if state.cliente_actual:
            pdf_bytes = generar_pdf_profesional(state, workbook)
            nombre_archivo_pdf = f"Propuesta_{state.numero_propuesta.replace('TEMP-', 'BORRADOR-')}.pdf"
            
            st.divider()
            st.subheader("Documento y Envío por Correo")
            col_pdf, col_email = st.columns(2)
            
            col_pdf.download_button(
                label="📄 Descargar PDF", data=pdf_bytes,
                file_name=nombre_archivo_pdf, mime="application/pdf", use_container_width=True,
                disabled=(pdf_bytes is None)
            )
            with col_email:
                email_cliente = st.text_input("Enviar a:", value=state.cliente_actual.get(CLIENTE_EMAIL_COL, ""))
                if st.button("📧 Enviar por Email", use_container_width=True, disabled=(pdf_bytes is None)):
                    if email_cliente:
                        with st.spinner("Enviando correo..."):
                            exito, mensaje = enviar_email_seguro(email_cliente, state, pdf_bytes, nombre_archivo_pdf)
                            if exito: st.success(mensaje)
                            else: st.error(mensaje)
                    else:
                        st.warning("Por favor, ingrese un correo electrónico de destino.")
            
            # --- SECCIÓN DE WHATSAPP COMPLETAMENTE NUEVA ---
            st.divider()
            st.subheader("Compartir por WhatsApp (con enlace al PDF)")
            
            # Campo de teléfono editable
            telefono_cliente = st.text_input(
                "Teléfono del Cliente (para WhatsApp):", 
                value=state.cliente_actual.get("Teléfono", "")
            )

            if st.button("🚀 Generar Enlace de WhatsApp", use_container_width=True, type="primary", disabled=(not telefono_cliente)):
                if pdf_bytes:
                    with st.spinner("Guardando PDF en Drive y generando enlace..."):
                        # 1. Guardar en Drive
                        exito_drive, resultado_drive = guardar_pdf_en_drive(workbook, pdf_bytes, nombre_archivo_pdf)
                        
                        if exito_drive:
                            file_id = resultado_drive
                            # 2. Construir el link público
                            link_pdf_publico = f"https://drive.google.com/file/d/{file_id}/view"
                            
                            # 3. Mostrar mensajes de éxito y guardar el link para el botón
                            st.info(f"✅ PDF guardado en Google Drive. [Abrir PDF]({link_pdf_publico})")
                            st.success("✅ ¡Acción realizada con éxito! El botón de WhatsApp está listo.")
                            st.session_state['whatsapp_link_html'] = generar_boton_whatsapp(state, telefono_cliente, link_pdf_publico)
                        else:
                            # Mostrar el mensaje de error que retorna la función
                            error_msg = resultado_drive
                            st.error(error_msg)
                            st.session_state['whatsapp_link_html'] = None
                else:
                    st.error("No se pudo generar el PDF para subirlo.")

            # Mostrar el botón de WhatsApp si fue generado exitosamente en el paso anterior
            if 'whatsapp_link_html' in st.session_state and st.session_state['whatsapp_link_html']:
                st.markdown(st.session_state['whatsapp_link_html'], unsafe_allow_html=True)
                st.caption("Haz clic en el botón para abrir WhatsApp con el mensaje y el enlace al PDF listos para enviar.")
