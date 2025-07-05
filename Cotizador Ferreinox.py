# Cotizador_Ferreinox.py
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from utils import (
    cargar_datos_maestros, connect_to_gsheets, generar_pdf_profesional,
    guardar_propuesta_en_gsheets, cargar_propuesta_a_sesion,
    CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL,
    PRECIOS_COLS, STOCK_COL, REFERENCIA_COL, NOMBRE_PRODUCTO_COL, COSTO_COL,
    LOGO_FILE_PATH, FONT_FILE_PATH, ESTADOS_COTIZACION
)

# --- CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
st.set_page_config(page_title="Cotizador Profesional", page_icon="🔩", layout="wide")
st.markdown("""
<style>
    .st-emotion-cache-1y4p8pa { padding-top: 2rem; }
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        border: 1px solid #e6e6e6; border-radius: 10px; padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); background-color: #ffffff;
    }
    h1 { border-bottom: 3px solid #0A2540; padding-bottom: 10px; color: #0A2540; }
    h2 { border-bottom: 2px solid #0062df; padding-bottom: 5px; color: #0A2540; }
    .stButton>button { color: #ffffff; background-color: #0062df; border: none; border-radius: 5px; padding: 10px 20px; font-weight: bold; transition: background-color 0.3s ease; }
    .stButton>button:hover { background-color: #003d8a; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE SESIÓN ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
if 'numero_propuesta' not in st.session_state: st.session_state.numero_propuesta = f"PROP-{datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d-%H%M%S')}"
if 'observaciones' not in st.session_state: st.session_state.observaciones = ("Forma de Pago: 50% Anticipo, 50% Contra-entrega.\n" "Tiempos de Entrega: 3-5 días hábiles para productos en stock.\n" "Garantía: Productos cubiertos por garantía de fábrica. No cubre mal uso.")
if 'vendedor_en_uso' not in st.session_state: st.session_state.vendedor_en_uso = ""

# --- CARGA DE DATOS ---
workbook = connect_to_gsheets()
if workbook:
    df_productos, df_clientes = cargar_datos_maestros()
else:
    st.warning("La aplicación no puede continuar sin conexión a la base de datos.")
    st.stop()

# --- LÓGICA PARA CARGAR COTIZACIÓN DESDE OTRA PÁGINA ---
if "load_quote" in st.query_params:
    numero_a_cargar = st.query_params.pop("load_quote")
    cargar_propuesta_a_sesion(numero_a_cargar)

# --- INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Profesional")

with st.sidebar:
    if LOGO_FILE_PATH.exists():
        st.image(str(LOGO_FILE_PATH), use_container_width=True)
    st.title("⚙️ Controles")
    st.session_state.vendedor_en_uso = st.text_input("Vendedor/Asesor:", value=st.session_state.vendedor_en_uso, placeholder="Tu nombre")
    st.divider()
    if st.button("🗑️ Iniciar Cotización Nueva", use_container_width=True):
        st.session_state.cotizacion_items = []
        st.session_state.cliente_actual = {}
        st.session_state.numero_propuesta = f"PROP-{datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d-%H%M%S')}"
        st.success("Listo para una nueva cotización.")
        st.rerun()
    st.divider()
    with st.expander("Diagnóstico del Sistema"):
        st.write(f"Logo: {'✅' if LOGO_FILE_PATH.exists() else '❌'}")
        st.write(f"Fuente PDF: {'✅' if FONT_FILE_PATH.exists() else '⚠️'}")
        st.write(f"Conexión Google Sheets: {'✅' if workbook else '❌'}")

col_controles, col_cotizador = st.columns([1, 2])

with col_controles:
    with st.container(border=True):
        st.subheader("👤 1. Cliente")
        lista_clientes = [""] + sorted(df_clientes[CLIENTE_NOMBRE_COL].unique().tolist())
        
        # Encuentra el índice del cliente actual para fijar el selectbox
        try:
            current_client_name = st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, "")
            idx = lista_clientes.index(current_client_name) if current_client_name in lista_clientes else 0
        except ValueError:
            idx = 0

        cliente_sel_nombre = st.selectbox(
            "Buscar o seleccionar cliente:",
            options=lista_clientes,
            placeholder="Escribe para buscar...",
            index=idx
        )
        if cliente_sel_nombre:
            st.session_state.cliente_actual = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0].to_dict()
            st.success(f"Cliente en cotización: **{st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, '')}**")

        with st.expander("➕ Registrar Cliente Nuevo"):
            with st.form("form_new_client"):
                nombre = st.text_input(f"{CLIENTE_NOMBRE_COL}*"); nit = st.text_input(CLIENTE_NIT_COL)
                tel = st.text_input(CLIENTE_TEL_COL); direc = st.text_input(CLIENTE_DIR_COL)
                if st.form_submit_button("💾 Guardar y Usar Cliente"):
                    if not nombre or not nit: st.warning("El Nombre y el NIF son obligatorios.")
                    else:
                        nuevo_cliente = {CLIENTE_NOMBRE_COL: nombre, CLIENTE_NIT_COL: nit, CLIENTE_TEL_COL: tel, CLIENTE_DIR_COL: direc}
                        # Lógica para guardar...
                        st.rerun()
    
    with st.container(border=True):
        st.subheader("📦 2. Agregar Productos")
        producto_sel_str = st.selectbox("Buscar producto:", options=[""] + df_productos['Busqueda'].tolist(), index=0, placeholder="Escribe para buscar...")
        if producto_sel_str:
            info_producto = df_productos[df_productos['Busqueda'] == producto_sel_str].iloc[0]
            st.write(f"**Producto:** {info_producto[NOMBRE_PRODUCTO_COL]}")
            c1, c2 = st.columns(2)
            c1.metric("Stock Disponible", f"{int(info_producto.get(STOCK_COL, 0))} uds.")
            with c2:
                cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1)
            opciones_precio = { f"{l} - ${info_producto.get(l, 0):,.0f}": info_producto.get(l, 0) for l in PRECIOS_COLS if pd.notna(info_producto.get(l)) and info_producto.get(l) > 0 }
            if opciones_precio:
                precio_sel_str = st.radio("Listas de Precio:", options=opciones_precio.keys())
                if st.button("➕ Agregar a la Cotización", use_container_width=True, type="primary"):
                    precio_unitario = pd.to_numeric(opciones_precio[precio_sel_str])
                    st.session_state.cotizacion_items.append({
                        "Referencia": info_producto[REFERENCIA_COL], "Producto": info_producto[NOMBRE_PRODUCTO_COL],
                        "Cantidad": cantidad, "Precio Unitario": precio_unitario, "Descuento (%)": 0, "Total": cantidad * precio_unitario,
                        "Inventario": info_producto.get(STOCK_COL, 0), "Costo_Unitario": info_producto.get(COSTO_COL, 0)
                    })
                    st.rerun()
            else:
                st.warning("Este producto no tiene precios definidos.")

with col_cotizador:
    # ### CAMBIO: Resumen y botones restaurados a la página principal ###
    with st.container(border=True):
        st.subheader("🛒 3. Resumen y Generación")
        if not st.session_state.cotizacion_items:
            st.info("Añada productos para ver el resumen.")
        else:
            edited_df = st.data_editor(
                pd.DataFrame(st.session_state.cotizacion_items),
                column_config={
                    "Producto": st.column_config.TextColumn("Producto", width="large"), "Cantidad": st.column_config.NumberColumn(min_value=1),
                    "Descuento (%)": st.column_config.NumberColumn(min_value=0, max_value=100, format="%d%%"),
                    "Precio Unitario": st.column_config.NumberColumn(format="$%.0f"), "Total": st.column_config.NumberColumn(format="$%.0f"),
                    "Inventario": None, "Referencia": st.column_config.TextColumn("Ref."), "Costo_Unitario": None
                },
                disabled=["Referencia", "Producto", "Precio Unitario", "Total", "Costo_Unitario", "Inventario"],
                hide_index=True, use_container_width=True, num_rows="dynamic"
            )
            recalculated_items = []
            for row in edited_df.to_dict('records'):
                row['Total'] = (row['Cantidad'] * row['Precio Unitario']) * (1 - row['Descuento (%)'] / 100.0)
                recalculated_items.append(row)
            st.session_state.cotizacion_items = recalculated_items
            
            subtotal_bruto = sum(item['Cantidad'] * item['Precio Unitario'] for item in recalculated_items)
            descuento_total = sum((item['Cantidad'] * item['Precio Unitario']) * (item['Descuento (%)'] / 100.0) for item in recalculated_items)
            base_gravable = subtotal_bruto - descuento_total; iva_valor = base_gravable * 0.19; total_general = base_gravable + iva_valor
            
            st.subheader("Resumen Financiero")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Subtotal Bruto", f"${subtotal_bruto:,.0f}"); m2.metric("Descuento Total", f"-${descuento_total:,.0f}")
            m3.metric("IVA (19%)", f"${iva_valor:,.0f}"); m4.metric("TOTAL GENERAL", f"${total_general:,.0f}")
            
            st.text_area("Observaciones y Términos:", key="observaciones", height=100)
            st.divider()

            st.subheader("Acciones Finales")
            col_accion1, col_accion2 = st.columns([2, 1])
            with col_accion1:
                status_actual = st.selectbox("Establecer Estado:", options=ESTADOS_COTIZACION)
            with col_accion2:
                st.write(""); st.button("💾 Guardar en la Nube", use_container_width=True, type="primary", on_click=guardar_propuesta_en_gsheets, args=(workbook, status_actual, st.session_state.observaciones))
            
            if st.session_state.get('cliente_actual'):
                df_cot_items = pd.DataFrame(st.session_state.cotizacion_items)
                pdf_data = generar_pdf_profesional(st.session_state.cliente_actual, df_cot_items, subtotal_bruto, descuento_total, iva_valor, total_general, st.session_state.observaciones)
                file_name = f"Propuesta_{st.session_state.numero_propuesta}_{st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente').replace(' ', '_')}.pdf"
                st.download_button("📄 Descargar Propuesta PDF", data=pdf_data, file_name=file_name, mime="application/pdf", use_container_width=True)
            else:
                st.warning("Seleccione un cliente para generar PDF.")
