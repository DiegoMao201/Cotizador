# Cotizador_Ferreinox.py
import streamlit as st
import pandas as pd
from state import QuoteState # Importar la nueva clase de estado
from utils import *

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cotizador Profesional", page_icon="🔩", layout="wide")
st.markdown("""<style> /* Estilos CSS... */ </style>""", unsafe_allow_html=True) # Estilos omitidos

# --- CARGA DE DATOS Y ESTADO ---
workbook = connect_to_gsheets()
if not workbook:
    st.error("La aplicación no puede continuar sin conexión a la base de datos."); st.stop()

# Inicializa el gestor de estado
st.session_state.state = QuoteState()
state = st.session_state.state

# Carga de datos maestros
df_productos, df_clientes = cargar_datos_maestros(workbook)

# Lógica para cargar una cotización desde la URL
if "load_quote" in st.query_params:
    numero_a_cargar = st.query_params.pop("load_quote")
    state.cargar_desde_gheets(numero_a_cargar, workbook)

# --- INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Profesional")

# --- SIDEBAR ---
with st.sidebar:
    if LOGO_FILE_PATH.exists():
        st.image(str(LOGO_FILE_PATH), use_container_width=True)
    st.title("⚙️ Controles")
    
    vendedor_actual = st.text_input(
        "Vendedor/Asesor:",
        value=state.vendedor,
        placeholder="Tu nombre",
        on_change=lambda: state.set_vendedor(st.session_state.vendedor_input),
        key="vendedor_input"
    )
    
    st.divider()
    if st.button("🗑️ Iniciar Cotización Nueva", use_container_width=True, on_click=state.reiniciar_cotizacion):
        st.rerun()

# --- 1. SELECCIÓN DE CLIENTE ---
st.header("1. Cliente")
with st.container(border=True):
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
        pass # Formulario de registro...

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
        
        opciones_precio = {
            f"{l} - ${info_producto.get(l, 0):,.0f}": info_producto.get(l, 0)
            for l in PRECIOS_COLS if pd.notna(info_producto.get(l)) and info_producto.get(l) > 0
        }
        
        if opciones_precio:
            precio_sel_str = st.radio("Listas de Precio:", options=opciones_precio.keys(), horizontal=True)
            if st.button("➕ Agregar a la Cotización", use_container_width=True, type="primary"):
                precio_unitario = opciones_precio[precio_sel_str]
                state.agregar_item(info_producto, cantidad, precio_unitario)
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
        
        # Editor de datos para ajustes finales
        edited_df = st.data_editor(
            df_items,
            column_config={
                "Precio Unitario": st.column_config.NumberColumn(format="$ %(value)d"),
                "Total": st.column_config.NumberColumn(format="$ %(value)d", disabled=True),
                "Descuento (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1),
                "Inventario": st.column_config.NumberColumn(disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )

        if edited_df.to_dict('records') != state.cotizacion_items:
            state.actualizar_items(edited_df)
            st.rerun()
            
        # Resumen financiero
        st.subheader("Resumen Financiero")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Subtotal Bruto", f"${state.subtotal_bruto:,.0f}")
        m2.metric("Descuento Total", f"-${state.descuento_total:,.0f}")
        m3.metric("IVA (19%)", f"${state.iva_valor:,.0f}")
        m4.metric("TOTAL GENERAL", f"${state.total_general:,.0f}")
        
        state.observaciones = st.text_area("Observaciones y Términos:", value=state.observaciones, height=100)
        
        st.divider()
        st.subheader("Acciones Finales")
        
        # Acciones de guardado y estado
        col_accion1, col_accion2 = st.columns([2, 1])
        state.status = col_accion1.selectbox("Establecer Estado:", options=ESTADOS_COTIZACION, index=ESTADOS_COTIZACION.index(state.status))
        col_accion2.write(""); col_accion2.button("💾 Guardar en la Nube", use_container_width=True, type="primary", on_click=guardar_propuesta_en_gsheets, args=(workbook, state))

        # Acciones de PDF y Email
        if state.cliente_actual:
            col_pdf, col_email = st.columns(2)
            
            pdf_bytes = generar_pdf_profesional(state)
            col_pdf.download_button(
                label="📄 Descargar PDF",
                data=pdf_bytes,
                file_name=f"Propuesta_{state.numero_propuesta}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
            with col_email:
                email_cliente = st.text_input("Enviar a:", value=state.cliente_actual.get(CLIENTE_EMAIL_COL, ""))
                if email_cliente:
                    asunto = f"Propuesta Comercial de Ferreinox SAS BIC - {state.numero_propuesta}"
                    cuerpo = f"Estimado(a) {state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente')},\n\nAdjunto encontrará nuestra propuesta comercial.\n\nGracias por su interés.\n\nAtentamente,\n{state.vendedor}"
                    mailto_link = generar_mailto_link(email_cliente, asunto, cuerpo)
                    st.link_button("📧 Enviar por Email", mailto_link, use_container_width=True)
