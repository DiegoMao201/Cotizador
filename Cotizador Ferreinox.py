import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Cotizador Ferreinox SAS",
    page_icon="📄",
    layout="wide"
)

# --- ESTILOS PERSONALIZADOS (CSS) ---
COLOR_PRIMARIO = "#0A2540"  # Un azul oscuro corporativo
COLOR_SECUNDARIO = "#F0F2F6" 
st.markdown(f"""
<style>
    .main .block-container {{ padding-top: 2rem; padding-bottom: 2rem; padding-left: 5rem; padding-right: 5rem; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARIO}; }}
    .stButton>button {{ color: #ffffff; background-color: {COLOR_PRIMARIO}; border-radius: 8px; border: none; padding: 10px 20px; font-weight: bold; }}
    .stButton>button:hover {{ background-color: #1E4976; color: #ffffff; }}
</style>
""", unsafe_allow_html=True)

# --- NOMBRES DE COLUMNAS DEFINITIVOS (DE TUS IMÁGENES) ---
# --- COLUMNAS DE 'lista_precios.xlsx' ---
REFERENCIA_COL = 'Referencia'
NOMBRE_PRODUCTO_COL = 'Descripción'
DESC_ADICIONAL_COL = 'Descripción Adicional'
# Nombres exactos de las listas de precios
PRECIOS_COLS = [
    'Detallista Pbl Pinturas',
    'Público Pbl Pinturas',
    'Público Pbl Complementarios',
    'Lista Detal Pbl Complementarios',
    'Lista CONSTRUALIADOS'
]

# --- COLUMNAS DE 'Clientes.xlsx' ---
CLIENTE_NOMBRE_COL = 'Nombre'
CLIENTE_NIT_COL = 'NIT'
CLIENTE_TEL_COL = 'Teléfono'
CLIENTE_DIR_COL = 'Dirección'

# --- FUNCIONES DE CARGA DE DATOS ---
@st.cache_data
def cargar_datos(archivo_excel, columnas_numericas=[]):
    try:
        df = pd.read_excel(archivo_excel)
        for col in columnas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error(f"Error al leer el archivo {archivo_excel}: {e}")
        return pd.DataFrame()

# --- INICIALIZAR EL ESTADO DE LA SESIÓN ---
if 'cotizacion_items' not in st.session_state:
    st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state:
    st.session_state.cliente_actual = {}

# --- CARGA DE DATOS ---
df_productos = cargar_datos('lista_precios.xlsx', PRECIOS_COLS)
df_clientes = cargar_datos('Clientes.xlsx')

if df_productos is None:
    st.error("FATAL: Archivo 'lista_precios.xlsx' no encontrado. La aplicación no puede continuar.")
    st.stop()
if df_clientes is None:
    st.warning("AVISO: Archivo 'Clientes.xlsx' no encontrado. Solo se podrán registrar clientes nuevos.")
    df_clientes = pd.DataFrame(columns=[CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL])

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("LOGO FERREINOX SAS BIC 2024.png", use_column_width=True)
    st.title("🛠️ Buscar Producto")

    df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " " + df_productos[REFERENCIA_COL].astype(str)
    
    termino_busqueda_nombre = st.text_input(f"Buscar por '{NOMBRE_PRODUCTO_COL}' o '{REFERENCIA_COL}':")
    termino_busqueda_desc = st.text_input(f"Buscar por '{DESC_ADICIONAL_COL}':")
    
# --- LÓGICA DE FILTRADO ---
df_filtrado = df_productos.copy()
if termino_busqueda_nombre:
    df_filtrado = df_filtrado[df_filtrado['Busqueda'].str.contains(termino_busqueda_nombre, case=False, na=False)]
if termino_busqueda_desc and DESC_ADICIONAL_COL in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado[DESC_ADICIONAL_COL].str.contains(termino_busqueda_desc, case=False, na=False)]

# --- INTERFAZ PRINCIPAL ---
st.title("📄 Cotizador Interactivo - Ferreinox SAS")
st.divider()

# --- GESTIÓN DE CLIENTES ---
st.header("👤 Datos del Cliente")
tab_existente, tab_nuevo = st.tabs(["Seleccionar Cliente Existente", "Registrar Cliente Nuevo"])
with tab_existente:
    if not df_clientes.empty:
        lista_clientes = ["Seleccione un cliente"] + df_clientes[CLIENTE_NOMBRE_COL].tolist()
        cliente_seleccionado_nombre = st.selectbox("Clientes guardados:", lista_clientes)
        if cliente_seleccionado_nombre != "Seleccione un cliente":
            info_cliente = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_seleccionado_nombre].iloc[0]
            st.session_state.cliente_actual = { "Nombre": info_cliente[CLIENTE_NOMBRE_COL], "NIT": info_cliente[CLIENTE_NIT_COL], "Teléfono": info_cliente[CLIENTE_TEL_COL], "Dirección": info_cliente[CLIENTE_DIR_COL] }
    else:
        st.info("No se cargó el archivo de clientes.")
with tab_nuevo:
    with st.form("form_nuevo_cliente"):
        nombre_nuevo = st.text_input(f"{CLIENTE_NOMBRE_COL}*")
        nit_nuevo = st.text_input(CLIENTE_NIT_COL)
        tel_nuevo = st.text_input(CLIENTE_TEL_COL)
        dir_nueva = st.text_input(CLIENTE_DIR_COL)
        if st.form_submit_button("Usar este Cliente"):
            if not nombre_nuevo: st.warning("El nombre es obligatorio.")
            else:
                st.session_state.cliente_actual = { "Nombre": nombre_nuevo, "NIT": nit_nuevo, "Teléfono": tel_nuevo, "Dirección": dir_nueva }
                st.success(f"Cliente '{nombre_nuevo}' listo.")

if st.session_state.cliente_actual:
    cliente = st.session_state.cliente_actual
    with st.expander("Ver Cliente Seleccionado", expanded=True):
        st.markdown(f"**Nombre:** `{cliente.get('Nombre')}` | **NIT/C.C.:** `{cliente.get('NIT')}` | **Teléfono:** `{cliente.get('Teléfono')}`")

st.divider()

# --- SECCIÓN INTERACTIVA PARA AGREGAR PRODUCTOS ---
st.header("📦 Agregar Productos a la Cotización")
col1, col2 = st.columns([2, 1.5])

with col1:
    st.subheader("1. Busque y seleccione el producto")
    if not df_filtrado.empty:
        producto_seleccionado_str = st.selectbox(
            "Resultados de la búsqueda:",
            options=df_filtrado[NOMBRE_PRODUCTO_COL] + " (" + df_filtrado[REFERENCIA_COL].astype(str) + ")"
        )
    else:
        st.warning("No se encontraron productos.")
        producto_seleccionado_str = None

with col2:
    st.subheader("2. Elija precio y cantidad")
    if producto_seleccionado_str:
        nombre_real_producto = producto_seleccionado_str.split(" (")[0]
        info_producto = df_productos[df_productos[NOMBRE_PRODUCTO_COL] == nombre_real_producto].iloc[0]

        opciones_precio = {}
        for lista_precio in PRECIOS_COLS:
            if lista_precio in info_producto:
                precio = info_producto.get(lista_precio, 0)
                opciones_precio[f"{lista_precio} - ${precio:,.2f}"] = (lista_precio, precio)

        precio_seleccionado_str = st.radio(
            "Precios disponibles para este ítem:",
            options=opciones_precio.keys()
        )
        
        col_cantidad, col_boton = st.columns(2)
        
        with col_cantidad:
            cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1, label_visibility="collapsed")
        
        with col_boton:
            if st.button("➕ Agregar", use_container_width=True):
                lista_aplicada, precio_unitario = opciones_precio[precio_seleccionado_str]
                
                st.session_state.cotizacion_items.append({
                    "Referencia": info_producto[REFERENCIA_COL],
                    "Producto": info_producto[NOMBRE_PRODUCTO_COL],
                    "Cantidad": cantidad,
                    "Lista Aplicada": lista_aplicada,
                    "Precio Unitario": precio_unitario,
                    "Total": cantidad * precio_unitario
                })
                st.success(f"'{nombre_real_producto}' agregado.")
                st.rerun()

st.divider()

# --- SECCIÓN DE LA COTIZACIÓN ACTUAL ---
st.header("🛒 Cotización Actual")

if not st.session_state.cotizacion_items:
    st.info("La cotización está vacía.")
else:
    df_cotizacion = pd.DataFrame(st.session_state.cotizacion_items)
    df_cotizacion = df_cotizacion[['Referencia', 'Producto', 'Cantidad', 'Lista Aplicada', 'Precio Unitario', 'Total']]
    
    df_display = df_cotizacion.copy()
    df_display['Precio Unitario'] = df_display['Precio Unitario'].apply(lambda x: f"${x:,.2f}")
    df_display['Total'] = df_display['Total'].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    total_cotizacion = df_cotizacion['Total'].sum()
    st.subheader(f"Total de la Cotización: ${total_cotizacion:,.2f}")
    
    if st.button("🗑️ Limpiar Cotización"):
        st.session_state.cotizacion_items = []
        st.rerun()
