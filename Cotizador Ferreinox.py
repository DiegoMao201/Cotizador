import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador Profesional - Ferreinox SAS BIC", page_icon="🔩", layout="wide")

# --- ESTILOS Y DISEÑO ---
st.markdown("""
<style>
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        border: 1px solid #e6e6e6; border-radius: 10px; padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); background-color: #ffffff;
    }
    h2 { border-bottom: 2px solid #0A2540; padding-bottom: 5px; color: #0A2540; }
    .stButton>button {
        color: #ffffff; background-color: #0062df; border: none; border-radius: 5px;
        padding: 10px 20px; font-weight: bold; transition: background-color 0.3s ease;
    }
    .stButton>button:hover { background-color: #003d8a; }
</style>
""", unsafe_allow_html=True)


# --- CONFIGURACIÓN DE RUTAS Y NOMBRES ---
try: BASE_DIR = Path(__file__).resolve().parent
except NameError: BASE_DIR = Path.cwd()

PRODUCTOS_FILE_NAME = 'lista_precios.xlsx'
CLIENTES_FILE_NAME = 'Clientes.xlsx'
INVENTARIO_FILE_NAME = 'Rotacion.xlsx'
LOGO_FILE_NAME = 'superior.png'
FOOTER_IMAGE_NAME = 'inferior.jpg'

PRODUCTOS_FILE_PATH = BASE_DIR / PRODUCTOS_FILE_NAME
CLIENTES_FILE_PATH = BASE_DIR / CLIENTES_FILE_NAME
INVENTARIO_FILE_PATH = BASE_DIR / INVENTARIO_FILE_NAME
LOGO_FILE_PATH = BASE_DIR / LOGO_FILE_NAME
FOOTER_IMAGE_PATH = BASE_DIR / FOOTER_IMAGE_NAME

# Columnas
REFERENCIA_COL = 'Referencia'; NOMBRE_PRODUCTO_COL = 'Descripción'
INVENTARIO_COL = 'Stock'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
PRODUCTOS_COLS_REQUERIDAS = [REFERENCIA_COL, NOMBRE_PRODUCTO_COL] + PRECIOS_COLS
CLIENTE_NOMBRE_COL = 'Nombre'; CLIENTE_NIT_COL = 'NIF'; CLIENTE_TEL_COL = 'Teléfono'; CLIENTE_DIR_COL = 'Dirección'
CLIENTES_COLS_REQUERIDAS = [CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL]
INVENTARIO_COLS_REQUERIDAS = [REFERENCIA_COL, INVENTARIO_COL]


# --- CLASE PDF PROFESIONAL (Sin cambios) ---
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = "Ferreinox SAS BIC"; self.company_nit = "NIT: 800.224.617-8"
        self.company_address = "Carrera 13 #19-26, Pereira, Risaralda"
        self.company_contact = "Tel: (606) 333 0101 | www.ferreinox.co"

    def header(self):
        # ... (código del header sin cambios)
    def footer(self):
        # ... (código del footer sin cambios)

# ... (Función generar_pdf_profesional sin cambios)

# --- FUNCIONES DE CARGA Y VERIFICACIÓN ---
@st.cache_data
def cargar_archivo_excel(path):
    """Función genérica y segura para cargar un archivo Excel."""
    if not path.exists():
        return None
    try:
        return pd.read_excel(path)
    except Exception as e:
        st.error(f"Error al leer el archivo {path.name}:")
        st.exception(e)
        return None

# --- INICIALIZACIÓN Y PROCESAMIENTO DE DATOS ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
if 'observaciones' not in st.session_state: st.session_state.observaciones = ""

# Carga de datos brutos
df_productos_bruto = cargar_archivo_excel(PRODUCTOS_FILE_PATH)
df_clientes = cargar_archivo_excel(CLIENTES_FILE_PATH)
df_inventario_bruto = cargar_archivo_excel(INVENTARIO_FILE_PATH)

# --- Panel de Diagnóstico ---
with st.sidebar:
    st.image(str(LOGO_FILE_PATH)) if LOGO_FILE_PATH.exists() else st.warning("Logo no encontrado")
    st.title("⚙️ Búsqueda")
    termino_busqueda = st.text_input("Buscar Producto:", placeholder="Nombre o referencia...")
    
    with st.expander("Diagnóstico de Archivos", expanded=True):
        st.write(f"Logo (`{LOGO_FILE_NAME}`): {'✅' if LOGO_FILE_PATH.exists() else '❌'}")
        st.write(f"Pie de Página (`{FOOTER_IMAGE_NAME}`): {'✅' if FOOTER_IMAGE_PATH.exists() else '❌'}")
        st.write(f"Clientes (`{CLIENTES_FILE_NAME}`): {'✅' if df_clientes is not None else '❌'}")
        st.write(f"Precios (`{PRODUCTOS_FILE_NAME}`): {'✅' if df_productos_bruto is not None else '❌'}")
        st.write(f"Inventario (`{INVENTARIO_FILE_NAME}`): {'✅' if df_inventario_bruto is not None else '⚠️'}")

    # --- NUEVA SECCIÓN DE DEPURACIÓN ---
    with st.expander("Depuración de Referencias"):
        if df_productos_bruto is not None:
            st.write("Primeras 5 Referencias de `lista_precios.xlsx`:")
            st.dataframe(df_productos_bruto[[REFERENCIA_COL]].head())
        if df_inventario_bruto is not None:
            st.write("Primeras 5 Referencias de `Rotacion.xlsx`:")
            st.dataframe(df_inventario_bruto[[REFERENCIA_COL]].head())


# --- Lógica de Negocio Principal ---
if df_productos_bruto is None:
    st.error("No se pudo cargar el archivo de precios. La aplicación no puede continuar.")
    st.stop()

# Limpieza y cruce de datos
df_productos = df_productos_bruto.dropna(subset=[NOMBRE_PRODUCTO_COL, REFERENCIA_COL]).copy()
df_productos[REFERENCIA_COL] = df_productos[REFERENCIA_COL].astype(str).str.strip()

if df_inventario_bruto is not None:
    df_inventario = df_inventario_bruto.copy()
    df_inventario[REFERENCIA_COL] = df_inventario[REFERENCIA_COL].astype(str).str.strip()
    df_inventario[INVENTARIO_COL] = pd.to_numeric(df_inventario[INVENTARIO_COL], errors='coerce').fillna(0)
    inv_total = df_inventario.groupby(REFERENCIA_COL)[INVENTARIO_COL].sum().reset_index()
    df_productos = pd.merge(df_productos, inv_total, on=REFERENCIA_COL, how='left')
    df_productos[INVENTARIO_COL].fillna(0, inplace=True)
else:
    df_productos[INVENTARIO_COL] = -1

df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos[REFERENCIA_COL] + ")"
con_stock = df_productos[df_productos[INVENTARIO_COL] > 0].shape[0] if df_inventario_bruto is not None else 0
sin_stock = len(df_productos) - con_stock if df_inventario_bruto is not None else 0
if 'con_stock' not in st.session_state:
    st.session_state.con_stock = con_stock
    st.session_state.sin_stock = sin_stock

# Actualizar diagnóstico con cifras calculadas
st.sidebar.info(f"Refs. con Stock: {st.session_state.con_stock} | Refs. sin Stock: {st.session_state.sin_stock}")


df_filtrado = df_productos[df_productos['Busqueda'].str.contains(termino_busqueda, case=False, na=False)] if termino_busqueda else df_productos

# --- El resto de la interfaz (UI) ---
st.title("🔩 Cotizador Profesional Ferreinox SAS BIC")
# ... (Aquí iría el resto del código de la interfaz que ya tenías, completo y sin omisiones)
# ... Por favor, copia esa sección desde el último código completo que te proporcioné.
