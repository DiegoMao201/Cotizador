# pages/0_⚙️_Cotizador.py
import streamlit as st
import pandas as pd
from state import QuoteState
from utils import *

st.set_page_config(layout="wide") 

st.title("🔩 Cotizador Profesional Ferreinox")

workbook = connect_to_gsheets()
if not workbook:
    st.error("La aplicación no puede continuar sin conexión a la base de datos.")
    st.stop()

if 'state' not in st.session_state:
    st.session_state.state = QuoteState()
state = st.session_state.state

# Inicializamos el estado de la búsqueda si no existe
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

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


st.header("1.5 Tienda de Despacho")
with st.container(border=True):
    lista_tiendas = get_tiendas_from_df(df_productos)
    if not lista_tiendas:
        st.error("No se pudieron detectar las tiendas desde la base de datos.")
    else:
        try:
            idx_tienda = lista_tiendas.index(state.tienda_despacho) if state.tienda_despacho else None
        except ValueError:
            idx_tienda = None
        tienda_seleccionada = st.selectbox(
            "Seleccione la tienda desde donde se despachará la cotización:",
            options=lista_tiendas,
            index=idx_tienda,
            placeholder="Elige una tienda..."
        )
        if tienda_seleccionada and tienda_seleccionada != state.tienda_despacho:
            state.set_tienda(tienda_seleccionada)
            st.rerun()
    if state.tienda_despacho:
        st.success(f"Tienda para despacho: **{state.tienda_despacho}**")

# ==============================================================================
# SECCIÓN 2: BUSCADOR DE PRODUCTOS INTELIGENTE
# ==============================================================================
st.header("2. Buscador de Productos")
with st.container(border=True):
    if df_productos.empty:
        st.warning("No hay productos en la base de datos para seleccionar.")
    else:
        # --- FILTROS AVANZADOS ---
        col_search, col_filters = st.columns([3, 2])
        with col_search:
            st.session_state.search_query = st.text_input(
                "🔎 Buscar por una o más palabras:",
                value=st.session_state.search_query,
                placeholder="Ej: viniltex blanco galon"
            )
        with col_filters:
            lista_categorias = []
            if 'Categoria' in df_productos.columns:
                lista_categorias = df_productos['Categoria'].dropna().unique().tolist()
            categoria_seleccionada = st.selectbox(
                "Filtrar por categoría:",
                options=["Todas"] + sorted(lista_categorias),
                index=0
            )

        # --- LÓGICA DE BÚSQUEDA INTELIGENTE ---
        # Llamamos a nuestro nuevo y potente motor de búsqueda
        resultados = buscar_productos_inteligentemente(
            st.session_state.search_query,
            df_productos,
            categoria_seleccionada
        )

        # --- MOSTRAR RESULTADOS ---
        st.markdown("---")
        if len(resultados) == 0 and not st.session_state.search_query:
             st.info("Escribe en el buscador para encontrar productos por relevancia.")
        elif len(resultados) == 0 and st.session_state.search_query:
            st.warning("No se encontraron productos que coincidan con tu búsqueda.")
        else:
            st.markdown(f"**Mejores resultados: {len(resultados)}**")
            
            # Encabezados de la lista de resultados
            col1, col2, col3, col4, col5 = st.columns([4, 1, 2, 2, 2])
            with col1: st.caption("Producto")
            with col2: st.caption("Stock")
            with col3: st.caption("Precio")
            with col4: st.caption("Cantidad")
            with col5: st.caption("Acción")

            # Itera sobre los primeros 25 resultados para no saturar la pantalla
            for _, info_producto in resultados.head(25).iterrows():
                stock_col = f"Stock {state.tienda_despacho}" if state.tienda_despacho else None
                stock_disponible = info_producto.get(stock_col, 0) if stock_col else 0
                stock_display = f"🟢 {stock_disponible}" if stock_disponible > 0 else f"🔴 {stock_disponible}"
                opciones_precio = {
                    l: info_producto.get(l, 0) for l in PRECIOS_COLS 
                    if pd.notna(info_producto.get(l)) and str(info_producto.get(l, 0)).replace('.','',1).isdigit()
                }

                col1, col2, col3, col4, col5 = st.columns([4, 1, 2, 2, 2])
                with col1:
                    st.markdown(f"**{info_producto[NOMBRE_PRODUCTO_COL]}**")
                    st.caption(f"Ref: {info_producto['Referencia']}")
                with col2:
                    st.markdown(stock_display)
                
                if not opciones_precio:
                    with col3:
                        st.warning("Sin precios")
                else:
                    with col3:
                        precio_sel_str = st.radio(
                            "Listas de Precio:", 
                            options=opciones_precio.keys(), 
                            horizontal=True, 
                            key=f"price_{info_producto['Referencia']}",
                            label_visibility="collapsed"
                        )
                    with col4:
                        cantidad = st.number_input(
                            "Cant.", 
                            min_value=1, value=1, step=1, 
                            key=f"qty_{info_producto['Referencia']}",
                            label_visibility="collapsed"
                        )
                    with col5:
                        if st.button("➕ Agregar", key=f"add_{info_producto['Referencia']}", disabled=not state.tienda_despacho):
                            state.agregar_item(info_producto.to_dict(), cantidad, opciones_precio[precio_sel_str])
                            st.rerun()

            if not state.tienda_despacho:
                st.warning("⚠️ Debes seleccionar una Tienda de Despacho para poder agregar productos.")

st.header("3. Resumen y Generación")
with st.container(border=True):
    if not state.cotizacion_items:
        st.info("Añada productos para ver el resumen de la cotización.")
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
                "Precio Unitario": st.column_config.NumberColumn(label="Vlr. Unitario", format="$COP {:,.2f}", required=True),
                "Descuento (%)": st.column_config.NumberColumn(label="Desc. %", min_value=0, max_value=100, step=1, format="%.1f%%", required=True),
                "Total": st.column_config.NumberColumn(label="Total", format="$COP {:,.2f}", disabled=True),
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
        if state.cliente_actual and state.cotizacion_items:
            pdf_bytes = generar_pdf_profesional(state, workbook)
            nombre_archivo_pdf = f"Propuesta_{state.numero_propuesta.replace('TEMP-', 'BORRADOR-')}.pdf"
            st.divider()
            st.subheader("Documento y Envío")
            col_pdf, col_email, col_wpp = st.columns(3)
            col_pdf.download_button(
                label="📄 Descargar PDF", data=pdf_bytes,
                file_name=nombre_archivo_pdf, mime="application/pdf", use_container_width=True,
                disabled=(pdf_bytes is None)
            )
            if col_email.button("📧 Enviar por Email", use_container_width=True, disabled=(pdf_bytes is None)):
                email_cliente = state.cliente_actual.get(CLIENTE_EMAIL_COL, "")
                if email_cliente:
                    with st.spinner("Enviando correo..."):
                        exito, mensaje = enviar_email_seguro(email_cliente, state, pdf_bytes, nombre_archivo_pdf)
                        if exito: st.success(mensaje)
                        else: st.error(mensaje)
                else:
                    st.warning("El cliente no tiene un email registrado.")
            if col_wpp.button("💬 Enviar por WhatsApp", use_container_width=True, disabled=(pdf_bytes is None)):
                telefono_cliente = state.cliente_actual.get("Teléfono", "")
                if telefono_cliente:
                    with st.spinner("Subiendo PDF y preparando mensaje..."):
                        exito_drive, resultado_drive = guardar_pdf_en_drive(workbook, pdf_bytes, nombre_archivo_pdf)
                        if exito_drive:
                            file_id = resultado_drive
                            link_pdf_publico = f"https://drive.google.com/file/d/{file_id}/view"
                            whatsapp_html = generar_boton_whatsapp(state, telefono_cliente, link_pdf_publico)
                            st.session_state.whatsapp_link = whatsapp_html
                        else:
                            st.error(resultado_drive)
                else:
                    st.warning("El cliente no tiene un teléfono registrado.")
            if 'whatsapp_link' in st.session_state:
                st.markdown(st.session_state.pop('whatsapp_link'), unsafe_allow_html=True)
