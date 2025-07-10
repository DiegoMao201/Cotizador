# pages/0_⚙️_Cotizador.py
import streamlit as st
import pandas as pd
from state import QuoteState
from utils import *
import time
import re

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide", page_title="Cotizador Profesional")

# =============================================================================
# --- INYECCIÓN DE ESTILO (CSS) PARA UN LOOK PROFESIONAL ---
# =============================================================================
st.markdown("""
<style>
    /* Fuente principal y color de fondo */
    body {
        font-family: 'Inter', sans-serif;
    }

    /* Estilo de los contenedores principales */
    .st-emotion-cache-183lzff {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    /* Estilo para los encabezados de sección */
    .section-header {
        font-size: 24px;
        font-weight: 600;
        color: #003366; /* Azul corporativo */
        border-bottom: 2px solid #003366;
        padding-bottom: 10px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    
    /* Mejoras en los botones */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #003366;
        color: #003366;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #003366;
        color: white;
        border: 1px solid #003366;
    }
    
    /* Botón primario (Agregar, Guardar, etc.) */
    .stButton>button[data-testid="baseButton-primary"] {
        background-color: #ff4b4b; /* Rojo para acciones primarias */
        color: white;
        border: none;
    }
    .stButton>button[data-testid="baseButton-primary"]:hover {
        background-color: #cc0000;
    }

</style>
""", unsafe_allow_html=True)


# --- TÍTULO Y CARGA DE DATOS ---
st.title("🔩 Cotizador Profesional Ferreinox")
st.markdown("Herramienta de alta eficiencia para la creación y gestión de propuestas comerciales.")

workbook = connect_to_gsheets()
if not workbook:
    st.error("La aplicación no puede continuar sin conexión a la base de datos.")
    st.stop()

if 'state' not in st.session_state:
    st.session_state.state = QuoteState()
state = st.session_state.state

# --- ESTADOS PARA LA BÚSQUEDA ---
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'selected_product_string' not in st.session_state:
    st.session_state.selected_product_string = None


# --- Lógica para cargar cotizaciones (sin cambios) ---
if st.session_state.get('load_quote'):
    numero_a_cargar = st.session_state.pop('load_quote')
    state.cargar_desde_gheets(numero_a_cargar, workbook)
    st.rerun()

# --- BARRA LATERAL DE CONTROLES ---
with st.sidebar:
    st.title("⚙️ Controles")
    if state.numero_propuesta and "TEMP" not in state.numero_propuesta:
        st.info(f"✍️ **Modo Edición:**\nCotización **{state.numero_propuesta}**.")
    else:
        st.info("✨ **Modo Creación:**\nEstás creando una cotización nueva.")
    
    def actualizar_vendedor():
        state.set_vendedor(st.session_state.vendedor_input)
    st.text_input(
        "Vendedor/Asesor:", value=state.vendedor,
        placeholder="Tu nombre", on_change=actualizar_vendedor, key="vendedor_input"
    )
    st.divider()
    st.button("🗑️ Iniciar Cotización Nueva", use_container_width=True, on_click=state.reiniciar_cotizacion)

df_productos, df_clientes = cargar_datos_maestros(workbook)

# --- PASO 1: CLIENTE ---
st.markdown("<h2 class='section-header'>👤 1. Datos del Cliente</h2>", unsafe_allow_html=True)
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
        cliente_sel_nombre = st.selectbox("Selecciona un cliente existente:", options=lista_clientes, index=idx)
        if cliente_sel_nombre and cliente_sel_nombre != current_client_name:
            cliente_dict = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0].to_dict()
            state.set_cliente(cliente_dict)
            st.rerun()
    if state.cliente_actual:
        st.success(f"Cliente seleccionado: **{state.cliente_actual.get(CLIENTE_NOMBRE_COL, '')}**")

# --- PASO 2: TIENDA ---
st.markdown("<h2 class='section-header'>🏬 2. Tienda de Despacho</h2>", unsafe_allow_html=True)
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
            "Selecciona la tienda para consultar stock y despachar:",
            options=lista_tiendas,
            index=idx_tienda,
            placeholder="Elige una tienda..."
        )
        if tienda_seleccionada and tienda_seleccionada != state.tienda_despacho:
            state.set_tienda(tienda_seleccionada)
            st.rerun()
    if state.tienda_despacho:
        st.success(f"Tienda para despacho: **{state.tienda_despacho}**")
    else:
        st.warning("Debes seleccionar una tienda para poder agregar productos.")

# ==============================================================================
# --- PASO 3: BUSCADOR DE PRODUCTOS CON BOTÓN DE LIMPIEZA ---
# ==============================================================================
st.markdown("<h2 class='section-header'>📦 3. Agregar Productos</h2>", unsafe_allow_html=True)
with st.container(border=True):
    if df_productos.empty:
        st.warning("No hay productos en la base de datos para seleccionar.")
    else:
        # --- MEJORA: Columnas para búsqueda y botón de limpiar ---
        col_search, col_clear, col_filters = st.columns([6, 1, 5])
        with col_search:
            st.session_state.search_query = st.text_input(
                "**Buscar productos:**",
                value=st.session_state.search_query,
                placeholder="Ej: viniltex blanco galon",
                label_visibility="collapsed"
            )
        with col_clear:
            st.write("") # Espaciador para alinear el botón
            st.write("")
            if st.button("✖️", help="Limpiar búsqueda"):
                st.session_state.search_query = ""
                st.rerun()
        with col_filters:
            lista_categorias = ["Todas"]
            if 'Categoria' in df_productos.columns:
                lista_categorias += sorted(df_productos['Categoria'].dropna().unique().tolist())
            categoria_seleccionada = st.selectbox(
                "**Filtrar por categoría:**",
                options=lista_categorias,
                label_visibility="collapsed"
            )

        resultados = buscar_productos_inteligentemente(
            st.session_state.search_query, df_productos, categoria_seleccionada
        )

        producto_seleccionado = None
        if not resultados.empty:
            options_dict = {"-- Elige un producto de los resultados --": None}
            for _, row in resultados.head(50).iterrows():
                stock_col = f"Stock {state.tienda_despacho}"
                stock_disponible = row.get(stock_col, 0)
                option_string = f"{row[NOMBRE_PRODUCTO_COL]} | Ref: {row['Referencia']} | Stock: {stock_disponible}"
                options_dict[option_string] = row['Referencia']

            selected_option = st.selectbox(
                f"**Resultados de la búsqueda ({len(resultados)} encontrados):**",
                options=list(options_dict.keys()),
                index=0,
                key="results_selectbox"
            )
            
            selected_ref = options_dict[selected_option]
            if selected_ref:
                producto_seleccionado_df = resultados[resultados['Referencia'] == selected_ref]
                if not producto_seleccionado_df.empty:
                    producto_seleccionado = producto_seleccionado_df.iloc[0]

        elif st.session_state.search_query:
            st.warning("No se encontraron productos para tu búsqueda.")
        else:
            st.info("Utiliza el buscador y los filtros para encontrar productos.")
        
        st.divider()

        if producto_seleccionado is not None:
            st.markdown(f"#### Producto Seleccionado")
            opciones_precio = {
                l: producto_seleccionado.get(l, 0) for l in PRECIOS_COLS 
                if pd.notna(producto_seleccionado.get(l)) and str(producto_seleccionado.get(l, 0)).replace('.','',1).isdigit()
            }

            col_info, col_actions = st.columns([3, 2])
            with col_info:
                st.markdown(f"**{producto_seleccionado[NOMBRE_PRODUCTO_COL]}**")
                st.caption(f"Referencia: {producto_seleccionado['Referencia']}")
            
            with col_actions:
                if not opciones_precio:
                    st.error("Este producto no tiene precios definidos.")
                else:
                    precio_sel_str = st.radio(
                        "Lista de Precio:", 
                        options=opciones_precio.keys(), 
                        horizontal=True,
                        key=f"price_{producto_seleccionado['Referencia']}"
                    )
                    cantidad = st.number_input(
                        "Cantidad:", 
                        min_value=1, value=1, step=1, 
                        key=f"qty_{producto_seleccionado['Referencia']}"
                    )
                    if st.button("➕ Agregar a la Cotización", type="primary", use_container_width=True, disabled=not state.tienda_despacho):
                        state.agregar_item(producto_seleccionado.to_dict(), cantidad, opciones_precio[precio_sel_str])
                        st.toast(f"✅ Añadido: {producto_seleccionado[NOMBRE_PRODUCTO_COL]}", icon="🎉")
                        time.sleep(1)
                        st.rerun()

# ==============================================================================
# --- PASO 4: RESUMEN Y GENERACIÓN ---
# ==============================================================================
st.markdown("<h2 class='section-header'>📝 4. Resumen y Generación</h2>", unsafe_allow_html=True)
with st.container(border=True):
    if not state.cotizacion_items:
        st.info("Cuando agregues productos, aparecerán aquí para que puedas editar las cantidades, precios y descuentos.")
    else:
        st.markdown("#### Items de la Cotización")
        df_items = pd.DataFrame(state.cotizacion_items)
        columnas_visibles = ['Referencia', 'Producto', 'Cantidad', 'Precio Unitario', 'Descuento (%)', 'Total']
        df_display = df_items[columnas_visibles]

        edited_df = st.data_editor(
            df_display,
            column_config={
                "Referencia": st.column_config.TextColumn(disabled=True),
                "Producto": st.column_config.TextColumn(label="Descripción", width="large", required=True),
                "Cantidad": st.column_config.NumberColumn(label="Cant.", required=True, min_value=1),
                "Precio Unitario": st.column_config.NumberColumn(label="Vlr. Unitario", format="$%.2f", required=True),
                "Descuento (%)": st.column_config.NumberColumn(label="Desc. %", min_value=0, max_value=100, step=1, format="%.1f%%", required=True),
                "Total": st.column_config.NumberColumn(label="Total", format="$%.2f", disabled=True),
            },
            use_container_width=True, hide_index=True, num_rows="dynamic", key="data_editor_items")
        
        if not edited_df.equals(df_display):
            state.actualizar_items_desde_vista(edited_df)
            st.rerun()

        st.divider()
        st.markdown("#### Resumen Financiero")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Subtotal Bruto", f"${state.subtotal_bruto:,.2f}")
        m2.metric("Descuento Total", f"-${state.descuento_total:,.2f}")
        m3.metric(f"IVA ({TASA_IVA:.0%})", f"${state.iva_valor:,.2f}")
        m4.metric("TOTAL GENERAL", f"${state.total_general:,.2f}")

        st.divider()
        st.markdown("#### Observaciones y Estado")
        col_obs, col_status = st.columns(2)
        with col_obs:
            state.observaciones = st.text_area("Observaciones y Términos:", value=state.observaciones, height=120, on_change=state.persist_to_session)
        with col_status:
            idx_status = ESTADOS_COTIZACION.index(state.status) if state.status in ESTADOS_COTIZACION else 0
            state.status = st.selectbox("Establecer Estado de la Propuesta:", options=ESTADOS_COTIZACION, index=idx_status)

        if state.cliente_actual:
            st.divider()
            st.subheader("Acciones Finales")
            col_accion1, col_accion2 = st.columns([2, 1])
            col_accion2.button("💾 Guardar Cambios en la Nube", use_container_width=True, type="primary", on_click=handle_save, args=(workbook, state))

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

            st.divider()
            st.subheader("Compartir por WhatsApp")

            telefono_cliente = st.text_input(
                "Teléfono del Cliente:",
                value=state.cliente_actual.get("Teléfono", "")
            )
            
            if st.button("🚀 Preparar y Enviar por WhatsApp", use_container_width=True, type="primary", disabled=(not telefono_cliente or pdf_bytes is None)):
                with st.spinner("Subiendo PDF y preparando mensaje..."):
                    exito_drive, resultado_drive = guardar_pdf_en_drive(workbook, pdf_bytes, nombre_archivo_pdf)
                    if exito_drive:
                        file_id = resultado_drive
                        link_pdf_publico = f"https://drive.google.com/file/d/{file_id}/view"
                        whatsapp_html = generar_boton_whatsapp(state, telefono_cliente, link_pdf_publico)
                        st.markdown(whatsapp_html, unsafe_allow_html=True)
                    else:
                        st.error(resultado_drive)
