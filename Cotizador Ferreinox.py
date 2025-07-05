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
    /* Estilos (sin cambios) */
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
    numero_a_cargar = st.query_params["load_quote"]
    cargar_propuesta_a_sesion(numero_a_cargar)
    st.query_params.clear() # Limpia el parámetro para no recargar en cada rerun

# --- INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Profesional")

with st.sidebar:
    if LOGO_FILE_PATH.exists():
        st.image(str(LOGO_FILE_PATH), use_container_width=True)
    st.title("⚙️ Controles")
    st.session_state.vendedor_en_uso = st.text_input("Vendedor/Asesor:", value=st.session_state.vendedor_en_uso, placeholder="Tu nombre")
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
        cliente_sel_nombre = st.selectbox(
            "Buscar o seleccionar cliente:",
            options=lista_clientes,
            placeholder="Escribe para buscar...",
            index=0 if not st.session_state.cliente_actual else lista_clientes.index(st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, ''))
        )
        if cliente_sel_nombre:
            st.session_state.cliente_actual = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0].to_dict()
            st.success(f"Cliente en cotización: **{st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, '')}**")

        with st.expander("➕ Registrar Cliente Nuevo"):
            # Formulario de registro... (sin cambios)
            pass

with col_cotizador:
    with st.container(border=True):
        st.subheader("📦 2. Agregar Productos")
        producto_sel_str = st.selectbox("Buscar producto:", options=[""] + df_productos['Busqueda'].tolist(), index=0, placeholder="Escribe para buscar por nombre o referencia...")
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
                    # Lógica para agregar item (sin cambios)
                    pass
    
    with st.container(border=True):
        st.subheader("🛒 3. Resumen y Generación")
        if not st.session_state.cotizacion_items:
            st.info("Añada productos para ver el resumen.")
        else:
            # Data editor, resumen financiero y botones (sin cambios en la lógica)
            pass
