import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from fpdf import FPDF
import warnings
from zoneinfo import ZoneInfo
import gspread
from gspread_dataframe import set_with_dataframe

# --- 0. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador Profesional - Ferreinox SAS BIC", page_icon="🔩", layout="wide")

# --- 1. ESTILOS Y DISEÑO ---
# (Se mantiene tu CSS original para la apariencia)
st.markdown("""
<style>
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        border: 1px solid #e6e6e6; border-radius: 10px; padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); background-color: #ffffff;
    }
    h1 { border-bottom: 3px solid #0A2540; padding-bottom: 10px; color: #0A2540; }
    h2 { border-bottom: 2px solid #0062df; padding-bottom: 5px; color: #0A2540; }
    .stButton>button {
        color: #ffffff; background-color: #0062df; border: none; border-radius: 5px;
        padding: 10px 20px; font-weight: bold; transition: background-color 0.3s ease;
    }
    .stButton>button:hover { background-color: #003d8a; }
</style>
""", unsafe_allow_html=True)


# --- 2. CONFIGURACIÓN DE RUTAS, NOMBRES Y CONSTANTES ---
try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path.cwd()

# Rutas de archivos locales (para assets como logo y fuente)
LOGO_FILE_NAME = 'superior.png'
FOOTER_IMAGE_NAME = 'inferior.jpg'
FONT_FILE_NAME = 'DejaVuSans.ttf'
LOGO_FILE_PATH = BASE_DIR / LOGO_FILE_NAME
FOOTER_IMAGE_PATH = BASE_DIR / FOOTER_IMAGE_NAME
FONT_FILE_PATH = BASE_DIR / FONT_FILE_NAME

# Configuración de Google Sheets
GOOGLE_SHEET_NAME = "Productos" # Nombre de tu Libro de Cálculo principal

# Nombres de columnas clave
REFERENCIA_COL = 'Referencia'
NOMBRE_PRODUCTO_COL = 'Descripción'
COSTO_COL = 'Costo'
STOCK_COL = 'Stock'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
CLIENTE_NOMBRE_COL = 'Nombre'; CLIENTE_NIT_COL = 'NIF'; CLIENTE_TEL_COL = 'Teléfono'; CLIENTE_DIR_COL = 'Dirección'


# --- 3. CLASE PDF Y GENERACIÓN (Tu código original) ---
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = "Ferreinox SAS BIC"; self.company_nit = "NIT: 800.224.617-8"
        self.company_address = "Carrera 13 #19-26, Pereira, Risaralda"; self.company_contact = "Tel: (606) 333 0101 | www.ferreinox.co"
        if FONT_FILE_PATH.exists():
            self.add_font('DejaVu', '', str(FONT_FILE_PATH), uni=True); self.add_font('DejaVu', 'B', str(FONT_FILE_PATH), uni=True)
            self.font_family = 'DejaVu'
        else: self.font_family = 'Helvetica'
    def header(self):
        if LOGO_FILE_PATH.exists(): self.image(str(LOGO_FILE_PATH), 10, 8, 80)
        self.set_y(12); self.set_font(self.font_family, 'B', 20); self.set_text_color(10, 37, 64)
        self.cell(0, 10, 'PROPUESTA COMERCIAL', 0, 1, 'R'); self.set_font(self.font_family, '', 10)
        self.cell(0, 5, f"Propuesta #: {st.session_state.get('numero_propuesta', 'N/A')}", 0, 1, 'R'); self.ln(15)
    def footer(self):
        if FOOTER_IMAGE_PATH.exists(): self.image(str(FOOTER_IMAGE_PATH), 8, self.h - 45, 200)
        self.set_y(-15); self.set_font(self.font_family, '', 8); self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_profesional(cliente, items_df, subtotal, descuento_total, iva_valor, total_general, observaciones):
    # La lógica detallada de tu función para generar el PDF se mantiene intacta.
    # Por brevedad, no se repiten las 80 líneas aquí, pero se asume que está completa.
    pdf = PDF('P', 'mm', 'Letter'); pdf.add_page()
    # ... (Todo tu código de creación de celdas, multiceldas, colores, etc. va aquí) ...
    return bytes(pdf.output())

# --- 4. FUNCIONES DE DATOS (Conexión y Lógica con Google Sheets) ---

@st.cache_resource
def connect_to_gsheets():
    """Establece conexión con Google Sheets usando los secretos de Streamlit."""
    try:
        # Intenta obtener las credenciales desde los secretos de Streamlit
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        workbook = gc.open(GOOGLE_SHEET_NAME)
        return workbook
    except Exception as e:
        # Si falla, muestra un error claro y amigable
        st.error(
            "**Error de conexión con Google Sheets: No se pudieron cargar las credenciales.**\n\n"
            f"**Detalle:** `st.secrets` no tiene la clave `gcp_service_account`.\n\n"
            "**Solución:**\n"
            "1.  Asegúrate de tener una carpeta `.streamlit` en tu proyecto.\n"
            "2.  Dentro de esa carpeta, debe existir un archivo llamado `secrets.toml`.\n"
            "3.  El contenido de `secrets.toml` debe tener el formato correcto con tus credenciales de Google.\n\n"
            "*Si estás desplegando en Streamlit Community Cloud, debes agregar estos secretos en la configuración de la aplicación.*"
        )
        return None

@st.cache_data(ttl=300)
def cargar_datos_maestros():
    """Carga los datos de Productos y Clientes desde Google Sheets."""
    workbook = connect_to_gsheets()
    if not workbook: return pd.DataFrame(), pd.DataFrame()
    try:
        prods_sheet = workbook.worksheet("Productos")
        df_productos = pd.DataFrame(prods_sheet.get_all_records())
        df_productos[REFERENCIA_COL] = df_productos[REFERENCIA_COL].astype(str).str.strip()
        df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos[REFERENCIA_COL] + ")"
        df_productos.dropna(subset=[NOMBRE_PRODUCTO_COL, REFERENCIA_COL], inplace=True)
        
        clientes_sheet = workbook.worksheet("Clientes")
        df_clientes = pd.DataFrame(clientes_sheet.get_all_records())
        return df_productos, df_clientes
    except Exception as e:
        st.error(f"Error al cargar datos maestros desde las hojas de cálculo: {e}"); return pd.DataFrame(), pd.DataFrame()

def guardar_cliente_nuevo(workbook, nuevo_cliente_dict):
    """Guarda un nuevo cliente en la hoja de 'Clientes'."""
    try:
        sheet = workbook.worksheet("Clientes")
        df_clientes_actuales = pd.DataFrame(sheet.get_all_records())
        if nuevo_cliente_dict[CLIENTE_NIT_COL] and nuevo_cliente_dict[CLIENTE_NIT_COL] in df_clientes_actuales[CLIENTE_NIT_COL].astype(str).values:
            st.toast(f"El cliente con NIT {nuevo_cliente_dict[CLIENTE_NIT_COL]} ya existe.", icon="⚠️"); return False
        sheet.append_row(list(nuevo_cliente_dict.values())); st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"No se pudo guardar el cliente en Google Sheets: {e}"); return False

def guardar_propuesta_en_gsheets(workbook, status):
    """Guarda la propuesta actual, su estado y rentabilidad en Google Sheets."""
    prop_num = st.session_state.numero_propuesta; items = st.session_state.cotizacion_items
    if not items: st.warning("No hay productos para guardar."); return
    
    # Cálculos financieros y de rentabilidad
    subtotal_bruto = sum(item['Cantidad'] * item['Precio Unitario'] for item in items)
    descuento_total = sum((item['Cantidad'] * item['Precio Unitario']) * (item['Descuento (%)'] / 100.0) for item in items)
    base_gravable = subtotal_bruto - descuento_total; iva_valor = base_gravable * 0.19; total_general = base_gravable + iva_valor
    costo_total_items = sum(item['Cantidad'] * item.get('Costo_Unitario', 0) for item in items)
    margen_abs = base_gravable - costo_total_items; margen_porc = (margen_abs / base_gravable) * 100 if base_gravable > 0 else 0

    header_data = [prop_num, datetime.now(ZoneInfo('America/Bogota')).isoformat(), st.session_state.get('vendedor', ''), st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, ''), st.session_state.cliente_actual.get(CLIENTE_NIT_COL, ''), status, subtotal_bruto, descuento_total, total_general, costo_total_items, margen_abs, margen_porc]
    items_data = [[prop_num, item['Referencia'], item['Producto'], item['Cantidad'], item['Precio Unitario'], item.get('Costo_Unitario', 0), item['Descuento (%)'], item['Total']] for item in items]
    
    try:
        with st.spinner("Guardando en la nube..."):
            cot_sheet = workbook.worksheet("Cotizaciones"); items_sheet = workbook.worksheet("Cotizaciones_Items")
            # Lógica para borrar y sobreescribir si la propuesta ya existe
            # ... (código detallado para findall y delete_rows) ...
        st.toast(f"✅ Propuesta '{prop_num}' guardada con estado '{status}'."); st.cache_data.clear()
    except Exception as e: st.error(f"Error al guardar en Google Sheets: {e}")

@st.cache_data(ttl=60)
def listar_propuestas_guardadas(workbook):
    """Lee la hoja de Cotizaciones y devuelve una lista para el selectbox."""
    if not workbook: return []
    try:
        records = workbook.worksheet("Cotizaciones").get_all_records()
        propuestas = [(f"[{r.get('status', 'N/A')}] {r.get('numero_propuesta', 'S/N')} - {r.get('cliente_nombre', 'N/A')}", r.get('numero_propuesta')) for r in records]
        return sorted(propuestas, key=lambda x: x[1], reverse=True)
    except Exception: return []

def cargar_propuesta_desde_gsheets(workbook, numero_propuesta):
    """Carga una propuesta y sus ítems desde Google Sheets."""
    # ... (código detallado de la función cargar_propuesta_desde_gsheets) ...
    pass

# --- 5. INICIALIZACIÓN DE ESTADO DE SESIÓN ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
if 'numero_propuesta' not in st.session_state: st.session_state.numero_propuesta = f"PROP-{datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d-%H%M%S')}"
if 'observaciones' not in st.session_state: st.session_state.observaciones = ("Forma de Pago: 50% Anticipo, 50% Contra-entrega.\n" "Tiempos de Entrega: 3-5 días hábiles...\n" "Garantía: Productos cubiertos por garantía...")

# --- 6. CARGA DE DATOS Y LÓGICA PRINCIPAL ---
workbook = connect_to_gsheets()
if workbook:
    df_productos, df_clientes = cargar_datos_maestros()
else:
    st.stop() # Detiene la ejecución si no hay conexión

# --- 7. INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Profesional Ferreinox SAS BIC (Cloud)")

with st.sidebar:
    st.image(str(LOGO_FILE_PATH), use_container_width=True) if LOGO_FILE_PATH.exists() else st.title("Ferreinox")
    st.title("⚙️ Controles")
    st.text_input("Vendedor/Asesor:", key="vendedor", placeholder="Tu nombre")
    st.divider()

    st.header("📂 Cargar Propuesta")
    propuestas_guardadas = listar_propuestas_guardadas(workbook)
    opciones_propuestas = {display: file for display, file in propuestas_guardadas}
    propuesta_a_cargar_display = st.selectbox("Seleccionar propuesta:", [""] + list(opciones_propuestas.keys()))
    if st.button("Cargar Propuesta") and propuesta_a_cargar_display:
        cargar_propuesta_desde_gsheets(workbook, opciones_propuestas[propuesta_a_cargar_display])

    with st.expander("Diagnóstico del Sistema"):
        st.write(f"Logo (`{LOGO_FILE_NAME}`): {'✅' if LOGO_FILE_PATH.exists() else '❌'}")
        st.write(f"Fuente PDF (`{FONT_FILE_NAME}`): {'✅' if FONT_FILE_PATH.exists() else '⚠️'}")
        st.write(f"Conexión Google Sheets: {'✅' if workbook else '❌'}")

# Búsqueda de productos
termino_busqueda = st.text_input("Buscar Producto por Nombre o Referencia:", placeholder="Ej: 'Tornillo', 'Pintura', '102030'")
if termino_busqueda and not df_productos.empty:
    palabras_clave = [palabra for palabra in termino_busqueda.strip().split() if palabra]
    df_filtrado = df_productos.copy()
    for palabra in palabras_clave:
        df_filtrado = df_filtrado[df_filtrado['Busqueda'].str.contains(palabra, case=False, na=False)]
else:
    df_filtrado = df_productos

# --- FLUJO DE COTIZACIÓN EN PANTALLA ---

# Bloque 1: Datos del Cliente
with st.container(border=True):
    st.header("👤 1. Datos del Cliente")
    tab_existente, tab_nuevo = st.tabs(["Seleccionar Cliente Existente", "Registrar Cliente Nuevo"])
    with tab_existente:
        # ... (código para seleccionar cliente, usando df_clientes) ...
        pass
    with tab_nuevo:
        with st.form("form_new_client"):
            # ... (formulario para nuevo cliente) ...
            if st.form_submit_button("💾 Guardar y Usar Cliente"):
                # ... (lógica para guardar cliente, llama a guardar_cliente_nuevo(workbook, ...)) ...
                pass

# Bloque 2: Agregar Productos
with st.container(border=True):
    st.header("📦 2. Agregar Productos")
    producto_sel_str = st.selectbox("Buscar y seleccionar:", options=df_filtrado['Busqueda'], index=None, placeholder="Escriba para buscar...")
    if producto_sel_str:
        info_producto = df_filtrado[df_filtrado['Busqueda'] == producto_sel_str].iloc[0]
        # ... (código para mostrar info del producto, listas de precio, etc.) ...
        if st.button("➕ Agregar a la Cotización", use_container_width=True, type="primary"):
            st.session_state.cotizacion_items.append({
                "Referencia": info_producto[REFERENCIA_COL], "Producto": info_producto[NOMBRE_PRODUCTO_COL],
                "Cantidad": cantidad, "Precio Unitario": precio_unitario, "Descuento (%)": 0, "Total": cantidad * precio_unitario,
                "Inventario": pd.to_numeric(info_producto.get(STOCK_COL, 0)),
                "Costo_Unitario": pd.to_numeric(info_producto.get(COSTO_COL, 0))
            })
            st.rerun()

# Bloque 3: Resumen y Acciones
with st.container(border=True):
    st.header("🛒 3. Resumen y Generación de Propuesta")
    if not st.session_state.cotizacion_items:
        st.info("Añada productos para ver el resumen.")
    else:
        # Data Editor (tu código original)
        edited_df = st.data_editor(...)
        
        # Resumen Financiero (tu código original)
        st.subheader("Resumen Financiero")
        # ... (cálculos y st.metric) ...

        # Observaciones
        st.text_area("Observaciones y Términos:", key="observaciones", height=100)
        st.divider()

        # Acciones: Guardar, Vaciar, Descargar PDF
        st.subheader("Acciones Finales")
        col_accion1, col_accion2 = st.columns([2, 1])
        with col_accion1:
            status_actual = st.selectbox("Establecer Estado:", options=['Borrador', 'Enviada', 'Aprobada', 'Rechazada', 'Pedido para Logística'])
        with col_accion2:
            st.write(""); st.button("💾 Guardar en la Nube", use_container_width=True, type="primary", on_click=guardar_propuesta_en_gsheets, args=(workbook, status_actual))
        
        st.divider()
        col_final1, col_final2 = st.columns(2)
        with col_final1:
            if st.button("🗑️ Vaciar Propuesta", use_container_width=True):
                # ... (lógica para vaciar) ...
                st.rerun()
        with col_final2:
            if st.session_state.get('cliente_actual'):
                df_cot_items = pd.DataFrame(st.session_state.cotizacion_items)
                # ... (lógica de tu botón descargar PDF) ...
                st.download_button("📄 Descargar Propuesta PDF", data=pdf_data, ...)
            else:
                st.warning("Seleccione un cliente para generar PDF.")
