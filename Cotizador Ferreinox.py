import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Cotizador Profesional - Ferreinox SAS",
    page_icon="🔩",
    layout="wide"
)

# --- ESTILOS Y DISEÑO ---
st.markdown("""
<style>
    /* Mejora la apariencia de los contenedores */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        background-color: #ffffff;
    }
    /* Títulos de las secciones */
    h2 {
        border-bottom: 2px solid #0A2540;
        padding-bottom: 5px;
        color: #0A2540;
    }
    /* Botón principal de acción */
    .stButton>button {
        color: #ffffff;
        background-color: #0062df; /* Un azul más vibrante */
        border: none;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: bold;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #003d8a;
    }
</style>
""", unsafe_allow_html=True)


# --- CONFIGURACIÓN DE NOMBRES Y ARCHIVOS (¡CORREGIDO!) ---
# Esto centraliza la configuración para facilitar futuros cambios.

# Nombres de archivos
PRODUCTOS_FILE = 'lista_precios.xlsx'
CLIENTES_FILE = 'Clientes.xlsx'
LOGO_FILE = 'LOGO FERREINOX SAS BIC 2024.png'

# Columnas del archivo de productos (NOMBRES REALES DE TU ARCHIVO)
REFERENCIA_COL = 'Referencia'
NOMBRE_PRODUCTO_COL = 'Descripción'
DESC_ADICIONAL_COL = 'Descripción Adicional'
PRECIOS_COLS = [
    'Detallista 801 lista 2',
    'Publico 800 Lista 1',
    'Publico 345 Lista 1 complementarios',
    'Lista 346 Lista Complementarios',
    'Lista 100123 Construaliados'
]
PRODUCTOS_COLS_REQUERIDAS = [REFERENCIA_COL, NOMBRE_PRODUCTO_COL, DESC_ADICIONAL_COL] + PRECIOS_COLS

# Columnas del archivo de clientes (Estos no dieron error, se asumen correctos)
CLIENTE_NOMBRE_COL = 'Nombre'
CLIENTE_NIT_COL = 'NIT'
CLIENTE_TEL_COL = 'Teléfono'
CLIENTE_DIR_COL = 'Dirección'
CLIENTES_COLS_REQUERIDAS = [CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL]


# --- FUNCIONES AUXILIARES ---

@st.cache_data
def cargar_datos(archivo, columnas_num):
    """Carga datos desde un archivo Excel y convierte columnas a numérico."""
    if not os.path.exists(archivo):
        st.error(f"Error Crítico: No se encontró el archivo '{archivo}'. Por favor, asegúrate de que esté en la misma carpeta que la aplicación.")
        return None
    try:
        df = pd.read_excel(archivo)
        for col in columnas_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo '{archivo}': {e}")
        return None

def verificar_columnas(df, columnas_requeridas, nombre_archivo):
    """Verifica que todas las columnas necesarias existan en el DataFrame."""
    if df is None:
        return False
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if columnas_faltantes:
        st.error(f"Error de Configuración en '{nombre_archivo}':")
        st.error(f"Faltan las siguientes columnas: **{', '.join(columnas_faltantes)}**")
        st.warning("Por favor, revisa que los nombres de las columnas en tu archivo Excel coincidan exactamente con los definidos en el script (incluyendo tildes y mayúsculas).")
        return False
    return True

# --- INICIALIZACIÓN Y CARGA DE DATOS ---

# Inicializar estado de sesión para el carrito
if 'cotizacion_items' not in st.session_state:
    st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state:
    st.session_state.cliente_actual = {}

# Cargar los datos
df_productos = cargar_datos(PRODUCTOS_FILE, PRECIOS_COLS)
df_clientes = cargar_datos(CLIENTES_FILE, [])

# --- VERIFICACIÓN DE ARRANQUE ---
# Si la verificación falla, la app se detiene aquí con un mensaje claro.
if not verificar_columnas(df_productos, PRODUCTOS_COLS_REQUERIDAS, PRODUCTOS_FILE):
    st.stop()
# Se asume que el archivo de clientes es opcional o sus columnas están bien.
if df_clientes is not None and not verificar_columnas(df_clientes, CLIENTES_COLS_REQUERIDAS, CLIENTES_FILE):
    st.stop()
    
# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, use_column_width=True)
    st.title("⚙️ Opciones de Búsqueda")
    
    # Combinar columnas para una búsqueda más potente
    df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " " + df_productos[REFERENCIA_COL].astype(str)
    
    termino_busqueda_nombre = st.text_input(f"Buscar por '{NOMBRE_PRODUCTO_COL}' o '{REFERENCIA_COL}':", key="search_name")
    termino_busqueda_desc = st.text_input(f"Buscar por '{DESC_ADICIONAL_COL}':", key="search_desc")

# --- FILTRADO DE DATOS ---
df_filtrado = df_productos.copy()
if termino_busqueda_nombre:
    df_filtrado = df_filtrado[df_filtrado['Busqueda'].str.contains(termino_busqueda_nombre, case=False, na=False)]
if termino_busqueda_desc:
    df_filtrado = df_filtrado[df_filtrado[DESC_ADICIONAL_COL].str.contains(termino_busqueda_desc, case=False, na=False)]

# --- CUERPO PRINCIPAL DE LA APLICACIÓN ---
st.title("🔩 Cotizador Profesional Ferreinox SAS")
st.markdown("Herramienta interactiva para la creación de cotizaciones de venta.")

# --- SECCIÓN DE CLIENTES ---
with st.container(border=True):
    st.header("👤 1. Datos del Cliente")
    tab_existente, tab_nuevo = st.tabs(["Seleccionar Cliente Existente", "Registrar Cliente Nuevo"])
    
    with tab_existente:
        if df_clientes is not None:
            lista_clientes = [""] + df_clientes[CLIENTE_NOMBRE_COL].tolist()
            cliente_sel_nombre = st.selectbox("Clientes guardados:", lista_clientes, help="Seleccione un cliente de la lista para cargar sus datos.", index=0)
            if cliente_sel_nombre:
                info_cliente = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0]
                st.session_state.cliente_actual = info_cliente.to_dict()
        else:
            st.info("No se cargó el archivo de clientes. Solo se pueden registrar clientes nuevos.")
    
    with tab_nuevo:
        with st.form("form_nuevo_cliente"):
            st.markdown("Rellene los datos para un cliente no registrado.")
            nombre_nuevo = st.text_input(f"{CLIENTE_NOMBRE_COL}*")
            nit_nuevo = st.text_input(CLIENTE_NIT_COL)
            tel_nuevo = st.text_input(CLIENTE_TEL_COL)
            dir_nueva = st.text_input(CLIENTE_DIR_COL)
            if st.form_submit_button("Usar este Cliente"):
                if not nombre_nuevo:
                    st.warning("El nombre del cliente es obligatorio.")
                else:
                    st.session_state.cliente_actual = {
                        CLIENTE_NOMBRE_COL: nombre_nuevo, CLIENTE_NIT_COL: nit_nuevo,
                        CLIENTE_TEL_COL: tel_nuevo, CLIENTE_DIR_COL: dir_nueva
                    }
                    st.success(f"Cliente '{nombre_nuevo}' listo para la cotización.")

# --- SECCIÓN DE AGREGAR PRODUCTOS ---
with st.container(border=True):
    st.header("📦 2. Agregar Productos")
    
    col_prod, col_precio = st.columns([1.5, 1])

    with col_prod:
        st.subheader("Seleccionar Producto")
        if not df_filtrado.empty:
            producto_sel_str = st.selectbox("Resultados de la búsqueda:", 
                                            options=df_filtrado[NOMBRE_PRODUCTO_COL] + " (" + df_filtrado[REFERENCIA_COL].astype(str) + ")",
                                            label_visibility="collapsed")
        else:
            st.warning("No se encontraron productos con los criterios de búsqueda.")
            producto_sel_str = None

    if producto_sel_str:
        nombre_real_prod = producto_sel_str.split(" (")[0]
        info_producto = df_productos[df_productos[NOMBRE_PRODUCTO_COL] == nombre_real_prod].iloc[0]

        with col_precio:
            st.subheader("Elegir Precio y Cantidad")
            
            opciones_precio = {f"{lista} - ${info_producto.get(lista, 0):,.2f}": (lista, info_producto.get(lista, 0)) for lista in PRECIOS_COLS}
            
            precio_sel_str = st.radio("Listas de precios disponibles:", options=opciones_precio.keys(), label_visibility="collapsed")
            
            col_cant, col_btn = st.columns([1, 2])
            with col_cant:
                cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1, label_visibility="collapsed")
            with col_btn:
                if st.button("➕ Agregar al Carrito", use_container_width=True):
                    lista_aplicada, precio_unitario = opciones_precio[precio_sel_str]
                    st.session_state.cotizacion_items.append({
                        "Referencia": info_producto[REFERENCIA_COL], "Producto": info_producto[NOMBRE_PRODUCTO_COL],
                        "Cantidad": cantidad, "Lista Aplicada": lista_aplicada,
                        "Precio Unitario": precio_unitario, "Total": cantidad * precio_unitario
                    })
                    st.toast(f"✅ '{nombre_real_prod}' agregado!", icon="🛒")
                    st.rerun()

# --- SECCIÓN DE COTIZACIÓN FINAL ---
with st.container(border=True):
    st.header("🛒 3. Cotización Actual")

    # Mostrar información del cliente seleccionado
    if st.session_state.cliente_actual:
        cliente = st.session_state.cliente_actual
        st.info(f"**Cliente:** {cliente.get(CLIENTE_NOMBRE_COL, 'N/A')} | **NIT/C.C.:** {cliente.get(CLIENTE_NIT_COL, 'N/A')}")
    else:
        st.warning("No se ha seleccionado ningún cliente para la cotización.")

    if not st.session_state.cotizacion_items:
        st.write("El carrito de cotización está vacío.")
    else:
        df_cotizacion = pd.DataFrame(st.session_state.cotizacion_items)
        df_display = df_cotizacion.copy()
        
        # Formateo de columnas para visualización
        for col in ['Precio Unitario', 'Total']:
            df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
            
        st.dataframe(df_display[['Referencia', 'Producto', 'Cantidad', 'Lista Aplicada', 'Precio Unitario', 'Total']], 
                     use_container_width=True, hide_index=True)
        
        total_cotizacion = df_cotizacion['Total'].sum()
        st.subheader(f"TOTAL: ${total_cotizacion:,.2f}")
        
        # --- ACCIONES DE LA COTIZACIÓN ---
        col_limpiar, col_descargar = st.columns(2)
        with col_limpiar:
            if st.button("🗑️ Vaciar Cotización", use_container_width=True, type="secondary"):
                st.session_state.cotizacion_items = []
                st.toast("🗑️ Cotización limpiada.", icon="🧹")
                st.rerun()

        with col_descargar:
            # Preparar el contenido del archivo de texto para descargar
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            numero_cotizacion = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            contenido_txt = f"COTIZACIÓN FERREINOX SAS\n"
            contenido_txt += f"================================\n"
            contenido_txt += f"Fecha: {fecha_actual}\n"
            contenido_txt += f"Número de Cotización: {numero_cotizacion}\n\n"
            
            if st.session_state.cliente_actual:
                cliente = st.session_state.cliente_actual
                contenido_txt += f"CLIENTE\n"
                contenido_txt += f"--------------------------------\n"
                contenido_txt += f"Nombre: {cliente.get(CLIENTE_NOMBRE_COL, 'N/A')}\n"
                contenido_txt += f"NIT/C.C.: {cliente.get(CLIENTE_NIT_COL, 'N/A')}\n"
                contenido_txt += f"Teléfono: {cliente.get(CLIENTE_TEL_COL, 'N/A')}\n"
                contenido_txt += f"Dirección: {cliente.get(CLIENTE_DIR_COL, 'N/A')}\n\n"
            
            contenido_txt += f"ITEMS\n"
            contenido_txt += f"--------------------------------\n"
            contenido_txt += f"{'Cant.':<5} {'Producto':<40} {'Precio U.':>15} {'Total':>15}\n"
            contenido_txt += f"-"*80 + "\n"
            for _, row in df_cotizacion.iterrows():
                precio_u_str = f"${row['Precio Unitario']:,.2f}"
                total_str = f"${row['Total']:,.2f}"
                contenido_txt += f"{row['Cantidad']:<5} {row['Producto']:<40} {precio_u_str:>15} {total_str:>15}\n"
            
            contenido_txt += f"\n" + "="*80 + "\n"
            contenido_txt += f"{'TOTAL:':>62} ${total_cotizacion:,.2f}\n"

            st.download_button(
                label="📄 Descargar Cotización (.txt)",
                data=contenido_txt,
                file_name=f"Cotizacion_{numero_cotizacion}.txt",
                mime="text/plain",
                use_container_width=True,
                type="primary"
            )
