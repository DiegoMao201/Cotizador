# Cotizador_Ferreinox.py
import streamlit as st
import pandas as pd
from state import QuoteState
from utils import *

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cotizador Profesional", page_icon="🔩", layout="wide")

# --- CARGA DE DATOS Y ESTADO ---
workbook = connect_to_gsheets()
if not workbook:
    st.error("La aplicación no puede continuar sin conexión a la base de datos.")
    st.stop()

# --- GESTOR DE ESTADO ---
if 'state' not in st.session_state:
    st.session_state.state = QuoteState()
state = st.session_state.state

df_productos, df_clientes = cargar_datos_maestros(workbook)

if "load_quote" in st.query_params and st.query_params["load_quote"]:
    numero_a_cargar = st.query_params["load_quote"]
    state.cargar_desde_gheets(numero_a_cargar, workbook)
    st.query_params.clear()

# --- INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Profesional Ferreinox")

# --- SIDEBAR ---
with st.sidebar:
    if LOGO_FILE_PATH.exists():
        st.image(str(LOGO_FILE_PATH), use_container_width=True)
    st.title("⚙️ Controles")
    
    def actualizar_vendedor():
        state.set_vendedor(st.session_state.vendedor_input)

    st.text_input(
        "Vendedor/Asesor:",
        value=state.vendedor,
        placeholder="Tu nombre",
        on_change=actualizar_vendedor,
        key="vendedor_input"
    )
    st.divider()
    st.button("🗑️ Iniciar Cotización Nueva", use_container_width=True, on_click=state.reiniciar_cotizacion)

# --- 1. SELECCIÓN DE CLIENTE ---
st.header("1. Cliente")
with st.container(border=True):
    if df_clientes.empty:
        st.warning("No hay clientes en la base de datos.")
    else:
        lista_clientes = [""] + sorted(df_clientes[CLIENTE_NOMBRE_COL].unique().tolist())
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
    
    with st.expander("➕ Registrar Cliente Nuevo"):
        st.info("Formulario para registrar un nuevo cliente (funcionalidad pendiente).")

# --- 2. SELECCIÓN DE PRODUCTOS ---
st.header("2. Productos")
with st.container(border=True):
    producto_sel_str = st.selectbox("Buscar producto:", options=[""] + df_productos['Busqueda'].tolist(), index=0, placeholder="Escribe para buscar...")
    if producto_sel_str:
        info_producto = df_productos[df_productos['Busqueda'] == producto_sel_str].iloc[0]
        st.markdown(f"**Producto Seleccionado:** {info_producto[NOMBRE_PRODUCTO_COL]}")
        
        c1, c2 = st.columns([1, 2])
        c1.metric("Stock Disponible", f"{info_producto.get(STOCK_COL, 0)} uds.")
        cantidad = c2.number_input("Cantidad:", min_value=1, value=1, step=1)
        
        # CORRECCIÓN: Formato de precios para mostrar decimales
        opciones_precio = {f"{l} - ${info_producto.get(l, 0):,.2f}": info_producto.get(l, 0)
                           for l in PRECIOS_COLS if pd.notna(info_producto.get(l)) and info_producto.get(l) > 0}
        
        if opciones_precio:
            precio_sel_str = st.radio("Listas de Precio:", options=opciones_precio.keys(), horizontal=True)
            if st.button("➕ Agregar a la Cotización", use_container_width=True, type="primary"):
                state.agregar_item(info_producto.to_dict(), cantidad, opciones_precio[precio_sel_str])
                st.rerun()
        else:
            st.warning("Este producto no tiene precios definidos.")

# --- 3. RESUMEN Y GENERACIÓN ---
st.header("3. Resumen y Generación")
with st.container(border=True):
    if not state.cotizacion_items:
        st.info("Añada productos para ver el resumen.")
    else:
        df_items = pd.DataFrame(state.cotizacion_items)
        
        # CORRECCIÓN: Se ajusta el formato para que sea válido y muestre decimales
        edited_df = st.data_editor(
            df_items,
            column_config={
                "Producto": st.column_config.TextColumn(disabled=True),
                "Referencia": st.column_config.TextColumn(disabled=True),
                "Precio Unitario": st.column_config.NumberColumn(format="$%.2f"),
                "Total": st.column_config.NumberColumn(format="$%.2f", disabled=True),
                "Descuento (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1, format="%.1f%%"),
                "Inventario": st.column_config.NumberColumn(disabled=True),
                "Costo": st.column_config.NumberColumn(disabled=True, format="$%.2f"),
                "Valor Descuento": st.column_config.NumberColumn(disabled=True, format="$%.2f")
            },
            use_container_width=True, hide_index=True, num_rows="dynamic")

        if edited_df.to_dict('records') != state.cotizacion_items:
            state.actualizar_items(edited_df)
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
        col_accion2.button("💾 Guardar en la Nube", use_container_width=True, type="primary", on_click=guardar_propuesta_en_gsheets, args=(workbook, state))

        if state.cliente_actual:
            col_pdf, col_email = st.columns(2)
            pdf_bytes = generar_pdf_profesional(state, workbook)
            col_pdf.download_button(
                label="📄 Descargar PDF", data=pdf_bytes,
                file_name=f"Propuesta_{state.numero_propuesta}.pdf",
                mime="application/pdf", use_container_width=True)
            
            with col_email:
                email_cliente = st.text_input("Enviar a:", value=state.cliente_actual.get(CLIENTE_EMAIL_COL, ""))
                if email_cliente:
                    asunto = f"Propuesta Comercial - {state.numero_propuesta}"
                    cuerpo = f"Estimado(a) {state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente')},\n\nAdjunto encontrará nuestra propuesta comercial.\n\nAtentamente,\n{state.vendedor}"
                    mailto_link = generar_mailto_link(email_cliente, asunto, cuerpo)
                    st.link_button("📧 Enviar por Email", mailto_link, use_container_width=True)
