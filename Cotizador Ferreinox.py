import streamlit as st
import pandas as pd
import numpy as np
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
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
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
GOOGLE_SHEET_NAME = "Productos"

# Nombres de columnas clave
REFERENCIA_COL = 'Referencia'
NOMBRE_PRODUCTO_COL = 'Descripción'
COSTO_COL = 'Costo'
STOCK_COL = 'Stock'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
CLIENTE_NOMBRE_COL = 'Nombre'
CLIENTE_NIT_COL = 'NIF'
CLIENTE_TEL_COL = 'Teléfono'
CLIENTE_DIR_COL = 'Dirección'
CLIENTES_COLS_REQUERIDAS = [CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL]

# --- 3. CLASE PDF Y GENERACIÓN (Tu código original completo) ---
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = "Ferreinox SAS BIC"
        self.company_nit = "NIT: 800.224.617-8"
        self.company_address = "Carrera 13 #19-26, Pereira, Risaralda"
        self.company_contact = "Tel: (606) 333 0101 | www.ferreinox.co"
        
        if FONT_FILE_PATH.exists():
            self.add_font('DejaVu', '', str(FONT_FILE_PATH), uni=True)
            self.add_font('DejaVu', 'B', str(FONT_FILE_PATH), uni=True)
            self.font_family = 'DejaVu'
        else:
            self.font_family = 'Helvetica'

    def header(self):
        if LOGO_FILE_PATH.exists(): self.image(str(LOGO_FILE_PATH), 10, 8, 80)
        self.set_y(12)
        self.set_font(self.font_family, 'B', 20)
        self.set_text_color(10, 37, 64)
        self.cell(0, 10, 'PROPUESTA COMERCIAL', 0, 1, 'R')
        self.set_font(self.font_family, '', 10)
        self.cell(0, 5, f"Propuesta #: {st.session_state.get('numero_propuesta', 'N/A')}", 0, 1, 'R')
        self.ln(15)

    def footer(self):
        if FOOTER_IMAGE_PATH.exists(): self.image(str(FOOTER_IMAGE_PATH), 8, self.h - 45, 200)
        self.set_y(-15)
        self.set_font(self.font_family, '', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_profesional(cliente, items_df, subtotal, descuento_total, iva_valor, total_general, observaciones):
    pdf = PDF('P', 'mm', 'Letter')
    
    if pdf.font_family != 'DejaVu':
        st.error(f"Error Crítico de PDF: No se encontró el archivo de fuente '{FONT_FILE_NAME}'.")
        st.stop()

    pdf.add_page()
    PRIMARY_COLOR = (10, 37, 64); LIGHT_GREY = (245, 245, 245)
    
    pdf.set_font(pdf.font_family, 'B', 10); pdf.set_fill_color(*LIGHT_GREY)
    pdf.cell(97.5, 7, 'CLIENTE', 1, 0, 'C', fill=True); pdf.cell(2.5, 7, '', 0, 0); pdf.cell(95, 7, 'DETALLES DE LA PROPUESTA', 1, 1, 'C', fill=True)
    
    y_before = pdf.get_y(); pdf.set_font(pdf.font_family, '', 9)
    cliente_info = (f"Nombre: {cliente.get(CLIENTE_NOMBRE_COL, 'N/A')}\n" f"NIF/C.C.: {cliente.get(CLIENTE_NIT_COL, 'N/A')}\n" f"Dirección: {cliente.get(CLIENTE_DIR_COL, 'N/A')}\n" f"Teléfono: {cliente.get(CLIENTE_TEL_COL, 'N/A')}")
    pdf.multi_cell(97.5, 5, cliente_info, 1, 'L'); y_after_cliente = pdf.get_y()

    pdf.set_y(y_before); pdf.set_x(10 + 97.5 + 2.5)
    
    fecha_actual_colombia = datetime.now(ZoneInfo("UTC")).astimezone(ZoneInfo("America/Bogota"))
    propuesta_info = (f"Fecha de Emisión: {fecha_actual_colombia.strftime('%d/%m/%Y')}\n" f"Validez de la Oferta: 15 días\n" f"Asesor Comercial: {st.session_state.get('vendedor', 'No especificado')}")
    pdf.multi_cell(95, 5, propuesta_info, 1, 'L'); y_after_propuesta = pdf.get_y()

    pdf.set_y(max(y_after_cliente, y_after_propuesta) + 5)
    
    pdf.set_font(pdf.font_family, '', 10)
    intro_text = (f"Estimado(a) {cliente.get(CLIENTE_NOMBRE_COL, 'Cliente')},\n\n" "Agradecemos la oportunidad de presentarle esta propuesta. En Ferreinox SAS BIC, nos comprometemos a " "ofrecer soluciones de la más alta calidad con el respaldo y la asesoría que su proyecto merece. " "A continuación, detallamos los productos solicitados:")
    pdf.multi_cell(0, 5, intro_text, 0, 'L'); pdf.ln(8)

    pdf.set_font(pdf.font_family, 'B', 10); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    col_widths = [20, 80, 15, 25, 25, 25]; headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, h in enumerate(headers): pdf.cell(col_widths[i], 10, h, 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font(pdf.font_family, '', 9)
    for _, row in items_df.iterrows():
        pdf.set_fill_color(*LIGHT_GREY if pdf.page_no() % 2 == 0 else (255,255,255))
        pdf.set_text_color(200, 0, 0) if row.get('Inventario', 0) <= 0 else pdf.set_text_color(0)
        
        y_before_row = pdf.get_y()
        pdf.multi_cell(col_widths[0], 6, str(row['Referencia']), border='LRB', align='C'); y_after_ref = pdf.get_y()
        pdf.set_y(y_before_row); pdf.set_x(pdf.get_x() + col_widths[0])
        pdf.multi_cell(col_widths[1], 6, str(row['Producto']), border='LRB', align='L'); y_after_prod = pdf.get_y()
        pdf.set_y(y_before_row); pdf.set_x(pdf.get_x() + col_widths[0] + col_widths[1])

        row_height = max(y_after_ref, y_after_prod) - y_before_row

        pdf.set_text_color(0)
        pdf.cell(col_widths[2], row_height, str(row['Cantidad']), 'LRB', 0, 'C')
        pdf.cell(col_widths[3], row_height, f"${row['Precio Unitario']:,.0f}", 'LRB', 0, 'R')
        pdf.cell(col_widths[4], row_height, f"{row['Descuento (%)']}%", 'LRB', 0, 'C')
        pdf.set_font(pdf.font_family, 'B', 9)
        pdf.cell(col_widths[5], row_height, f"${row['Total']:,.0f}", 'LRB', 1, 'R')
        pdf.set_font(pdf.font_family, '', 9)
    
    pdf.set_text_color(0); pdf.ln(12)
    
    if pdf.get_y() > 195: pdf.add_page()
    
    y_totals = pdf.get_y(); pdf.set_x(105); pdf.set_font(pdf.font_family, '', 10)
    pdf.cell(50, 8, 'Subtotal Bruto:', 'TLR', 0, 'R'); pdf.cell(50, 8, f"${subtotal:,.0f}", 'TR', 1, 'R')
    pdf.set_x(105); pdf.cell(50, 8, 'Descuento Total:', 'LR', 0, 'R'); pdf.cell(50, 8, f"-${descuento_total:,.0f}", 'R', 1, 'R')
    pdf.set_x(105); pdf.cell(50, 8, 'Base Gravable:', 'LR', 0, 'R'); pdf.cell(50, 8, f"${(subtotal - descuento_total):,.0f}", 'R', 1, 'R')
    pdf.set_x(105); pdf.cell(50, 8, 'IVA (19%):', 'LR', 0, 'R'); pdf.cell(50, 8, f"${iva_valor:,.0f}", 'R', 1, 'R')
    pdf.set_x(105); pdf.set_font(pdf.font_family, 'B', 14); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    pdf.cell(50, 12, 'TOTAL A PAGAR:', 'BLR', 0, 'R', fill=True); pdf.cell(50, 12, f"${total_general:,.0f}", 'BR', 1, 'R', fill=True)
    pdf.set_text_color(0); pdf.set_y(y_totals); pdf.set_font(pdf.font_family, 'B', 10)
    pdf.cell(90, 7, 'Notas y Términos de la Propuesta:', 0, 1); pdf.set_font(pdf.font_family, '', 8)
    pdf.multi_cell(90, 5, observaciones, 'T', 'L'); pdf.set_y(pdf.get_y() + 5)
    pdf.set_font(pdf.font_family, 'B', 10); pdf.cell(90, 7, 'Nuestro Compromiso de Valor:', 0, 1, 'L'); pdf.set_font(pdf.font_family, '', 8)
    pdf.multi_cell(90, 5, "• Asesoría experta...\n• Garantía directa...\n• Amplio stock...", 0, 'L')
    
    return bytes(pdf.output())

# --- 4. FUNCIONES DE DATOS (Conexión y Lógica con Google Sheets) ---

@st.cache_resource
def connect_to_gsheets():
    """Establece conexión con Google Sheets usando los secretos de Streamlit."""
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        workbook = gc.open(GOOGLE_SHEET_NAME)
        return workbook
    except Exception as e:
        st.error(
            "**Error de conexión con Google Sheets: No se pudieron cargar las credenciales.**\n\n"
            "Por favor, asegúrate de que el archivo `.streamlit/secrets.toml` existe y está bien configurado con las credenciales de la cuenta de servicio de Google, y que esa cuenta tiene permisos de 'Editor' sobre el archivo de Google Sheets."
        )
        return None

### CAMBIO REALIZADO ###
# Se eliminó el parámetro 'workbook' de la función.
@st.cache_data(ttl=300)
def cargar_datos_maestros():
    """Carga los datos de Productos y Clientes desde Google Sheets."""
    ### CAMBIO REALIZADO ###
    # La conexión se obtiene directamente aquí, aprovechando el caché de @st.cache_resource.
    workbook = connect_to_gsheets()
    if not workbook: return pd.DataFrame(), pd.DataFrame()
    try:
        prods_sheet = workbook.worksheet("Productos")
        df_productos = pd.DataFrame(prods_sheet.get_all_records())
        df_productos[REFERENCIA_COL] = df_productos[REFERENCIA_COL].astype(str).str.strip()
        df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos[REFERENCIA_COL] + ")"
        for col in [COSTO_COL, STOCK_COL]:
            df_productos[col] = pd.to_numeric(df_productos[col], errors='coerce').fillna(0)
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
        if nuevo_cliente_dict[CLIENTE_NIT_COL] and str(nuevo_cliente_dict[CLIENTE_NIT_COL]) in df_clientes_actuales[CLIENTE_NIT_COL].astype(str).values:
            st.toast(f"El cliente con NIT {nuevo_cliente_dict[CLIENTE_NIT_COL]} ya existe.", icon="⚠️"); return False
        sheet.append_row(list(nuevo_cliente_dict.values())); st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"No se pudo guardar el cliente en Google Sheets: {e}"); return False

def guardar_propuesta_en_gsheets(workbook, status):
    """Guarda la propuesta actual, su estado y rentabilidad en Google Sheets."""
    if not workbook: st.error("Sin conexión a Google Sheets."); return
    prop_num = st.session_state.numero_propuesta; items = st.session_state.cotizacion_items
    if not items: st.warning("No hay productos en la cotización para guardar."); return
    
    subtotal_bruto = sum(item['Cantidad'] * item['Precio Unitario'] for item in items)
    descuento_total = sum((item['Cantidad'] * item['Precio Unitario']) * (item['Descuento (%)'] / 100.0) for item in items)
    base_gravable = subtotal_bruto - descuento_total; iva_valor = base_gravable * 0.19; total_general = base_gravable + iva_valor
    costo_total_items = sum(item['Cantidad'] * item.get('Costo_Unitario', 0) for item in items)
    margen_abs = base_gravable - costo_total_items; margen_porc = (margen_abs / base_gravable) * 100 if base_gravable > 0 else 0

    header_data = [prop_num, datetime.now(ZoneInfo('America/Bogota')).isoformat(), st.session_state.get('vendedor', ''), st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, ''), str(st.session_state.cliente_actual.get(CLIENTE_NIT_COL, '')), status, subtotal_bruto, descuento_total, total_general, costo_total_items, margen_abs, margen_porc]
    items_data = [[prop_num, item['Referencia'], item['Producto'], item['Cantidad'], item['Precio Unitario'], item.get('Costo_Unitario', 0), item['Descuento (%)'], item['Total']] for item in items]
    
    try:
        with st.spinner("Guardando en la nube..."):
            cot_sheet = workbook.worksheet("Cotizaciones"); items_sheet = workbook.worksheet("Cotizaciones_Items")
            
            # Borrar registros antiguos para evitar duplicados al sobreescribir
            cell_list = cot_sheet.findall(prop_num)
            if cell_list: cot_sheet.delete_rows(cell_list[0].row)
            
            cell_list_items = items_sheet.findall(prop_num)
            if cell_list_items:
                rows_to_delete = sorted(list(set(cell.row for cell in cell_list_items)), reverse=True)
                for row_num in rows_to_delete:
                    try: items_sheet.delete_rows(row_num)
                    except Exception: continue

            cot_sheet.append_row(header_data, value_input_option='USER_ENTERED')
            if items_data: items_sheet.append_rows(items_data, value_input_option='USER_ENTERED')
            
        st.toast(f"✅ Propuesta '{prop_num}' guardada con estado '{status}'."); st.cache_data.clear()
    except Exception as e: st.error(f"Error al guardar en Google Sheets: {e}")

### CAMBIO REALIZADO ###
# Se eliminó el parámetro 'workbook' de la función.
@st.cache_data(ttl=60)
def listar_propuestas_guardadas():
    """Lee la hoja de Cotizaciones y devuelve una lista para el selectbox."""
    ### CAMBIO REALIZADO ###
    # La conexión se obtiene directamente aquí.
    workbook = connect_to_gsheets()
    if not workbook: return []
    try:
        records = workbook.worksheet("Cotizaciones").get_all_records()
        propuestas = [(f"[{r.get('status', 'N/A')}] {r.get('numero_propuesta', 'S/N')} - {r.get('cliente_nombre', 'N/A')}", r.get('numero_propuesta')) for r in records]
        return sorted(propuestas, key=lambda x: x[1], reverse=True)
    except Exception: return []

def cargar_propuesta_desde_gsheets(workbook, numero_propuesta):
    """Carga una propuesta y sus ítems desde Google Sheets."""
    if not workbook: return
    try:
        with st.spinner(f"Cargando propuesta {numero_propuesta}..."):
            cot_sheet = workbook.worksheet("Cotizaciones")
            header_record = cot_sheet.find(numero_propuesta)
            if not header_record: st.error("No se encontró la propuesta."); return
            header_data = dict(zip(cot_sheet.row_values(1), cot_sheet.row_values(header_record.row)))

            items_sheet = workbook.worksheet("Cotizaciones_Items")
            all_items = items_sheet.get_all_records(numericise_ignore=['all'])
            items_propuesta = [item for item in all_items if item['numero_propuesta'] == numero_propuesta]

        st.session_state.numero_propuesta = header_data['numero_propuesta']
        st.session_state.vendedor = header_data.get('vendedor', '')
        st.session_state.cliente_actual = {
            CLIENTE_NOMBRE_COL: header_data.get('cliente_nombre'), CLIENTE_NIT_COL: header_data.get('cliente_nit'),
            CLIENTE_DIR_COL: '', CLIENTE_TEL_COL: ''
        }
        
        recalculated_items = []
        for item_db in items_propuesta:
            cantidad = float(item_db['Cantidad']); precio = float(item_db['Precio_Unitario']); desc = float(item_db['Descuento_Porc'])
            total = (cantidad * precio) * (1 - desc / 100.0)
            recalculated_items.append({
                "Referencia": item_db['Referencia'], "Producto": item_db['Producto'],
                "Cantidad": int(cantidad), "Precio Unitario": precio,
                "Costo_Unitario": float(item_db.get('Costo_Unitario', 0)), "Descuento (%)": desc, "Total": total, "Inventario": -1
            })
        st.session_state.cotizacion_items = recalculated_items

        st.toast(f"✅ Propuesta '{numero_propuesta}' cargada."); st.rerun()
    except Exception as e: st.error(f"Error al cargar desde Google Sheets: {e}")

# --- 5. INICIALIZACIÓN DE ESTADO DE SESIÓN ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
if 'numero_propuesta' not in st.session_state: st.session_state.numero_propuesta = f"PROP-{datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d-%H%M%S')}"
if 'observaciones' not in st.session_state: st.session_state.observaciones = ("Forma de Pago: 50% Anticipo, 50% Contra-entrega.\n" "Tiempos de Entrega: 3-5 días hábiles para productos en stock.\n" "Garantía: Productos cubiertos por garantía de fábrica. No cubre mal uso.")

# --- 6. CARGA DE DATOS Y LÓGICA PRINCIPAL ---
workbook = connect_to_gsheets()
if workbook:
    ### CAMBIO REALIZADO ###
    # La función ahora se llama sin parámetros.
    df_productos, df_clientes = cargar_datos_maestros()
else:
    st.warning("No se pudo establecer conexión con la base de datos en la nube. La aplicación no puede continuar.")
    st.stop()

# --- 7. INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Profesional Ferreinox SAS BIC (Cloud)")

with st.sidebar:
    st.image(str(LOGO_FILE_PATH), use_container_width=True) if LOGO_FILE_PATH.exists() else st.title("Ferreinox")
    st.title("⚙️ Controles")
    st.text_input("Vendedor/Asesor:", key="vendedor", placeholder="Tu nombre")
    st.divider()

    st.header("📂 Cargar Propuesta")
    ### CAMBIO REALIZADO ###
    # La función ahora se llama sin parámetros.
    propuestas_guardadas = listar_propuestas_guardadas()
    opciones_propuestas = {display: file for display, file in propuestas_guardadas}
    propuesta_a_cargar_display = st.selectbox("Seleccionar propuesta:", [""] + list(opciones_propuestas.keys()), index=0, help="Carga una cotización previamente guardada.")
    if st.button("Cargar Propuesta") and propuesta_a_cargar_display:
        cargar_propuesta_desde_gsheets(workbook, opciones_propuestas[propuesta_a_cargar_display])

    with st.expander("Diagnóstico del Sistema"):
        st.write(f"Logo (`{LOGO_FILE_NAME}`): {'✅' if LOGO_FILE_PATH.exists() else '❌'}")
        st.write(f"Fuente PDF (`{FONT_FILE_NAME}`): {'✅' if FONT_FILE_PATH.exists() else '⚠️'}")
        st.write(f"Conexión Google Sheets: {'✅' if workbook else '❌'}")

termino_busqueda = st.text_input("Buscar Producto por Nombre o Referencia:", placeholder="Ej: 'Tornillo', 'Pintura', '102030'")
if termino_busqueda and not df_productos.empty:
    palabras_clave = [palabra for palabra in termino_busqueda.strip().split() if palabra]
    df_filtrado = df_productos.copy()
    for palabra in palabras_clave:
        df_filtrado = df_filtrado[df_filtrado['Busqueda'].str.contains(palabra, case=False, na=False)]
else:
    df_filtrado = df_productos

with st.container(border=True):
    st.header("👤 1. Datos del Cliente")
    tab_existente, tab_nuevo = st.tabs(["Seleccionar Cliente Existente", "Registrar Cliente Nuevo"])
    with tab_existente:
        if not df_clientes.empty:
            nombres_clientes = [""] + sorted(df_clientes[CLIENTE_NOMBRE_COL].astype(str).unique().tolist())
            cliente_sel_nombre = st.selectbox("Clientes guardados:", nombres_clientes)
            if cliente_sel_nombre:
                st.session_state.cliente_actual = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0].to_dict()
                st.info(f"Cliente seleccionado: **{st.session_state.cliente_actual[CLIENTE_NOMBRE_COL]}**")
        else:
            st.info("No hay clientes guardados.")
    with tab_nuevo:
        with st.form("form_new_client"):
            nombre = st.text_input(f"{CLIENTE_NOMBRE_COL}*"); nit = st.text_input(CLIENTE_NIT_COL)
            tel = st.text_input(CLIENTE_TEL_COL); direc = st.text_input(CLIENTE_DIR_COL)
            if st.form_submit_button("💾 Guardar y Usar Cliente"):
                if not nombre or not nit: st.warning("El Nombre y el NIF son obligatorios.")
                else:
                    nuevo_cliente = {CLIENTE_NOMBRE_COL: nombre, CLIENTE_NIT_COL: nit, CLIENTE_TEL_COL: tel, CLIENTE_DIR_COL: direc}
                    if guardar_cliente_nuevo(workbook, nuevo_cliente):
                        st.session_state.cliente_actual = nuevo_cliente; st.success(f"Cliente '{nombre}' guardado y seleccionado!"); st.rerun()

with st.container(border=True):
    st.header("📦 2. Agregar Productos")
    producto_sel_str = st.selectbox("Buscar y seleccionar producto:", options=df_filtrado['Busqueda'], index=None, placeholder="Escriba para buscar...")
    if producto_sel_str:
        info_producto = df_filtrado[df_filtrado['Busqueda'] == producto_sel_str].iloc[0]
        st.subheader(f"Producto: {info_producto[NOMBRE_PRODUCTO_COL]}")
        stock_actual = info_producto.get(STOCK_COL, 0)
        if stock_actual <= 0: st.warning(f"⚠️ ¡Atención! No hay inventario disponible.", icon="📦")
        else: st.success(f"✅ Hay **{int(stock_actual)}** unidades en stock.", icon="📦")

        col1, col2 = st.columns([3, 2]);
        with col1:
            opciones_precio = {f"{l} - ${pd.to_numeric(info_producto.get(l, 0), errors='coerce'):,.0f}": info_producto.get(l, 0) for l in PRECIOS_COLS if pd.notna(info_producto.get(l))}
            if opciones_precio: precio_sel_str = st.radio("Listas de Precio:", options=opciones_precio.keys())
            else: st.warning("Este producto no tiene precios definidos."); precio_sel_str = None
        with col2:
            cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1)
            if precio_sel_str and st.button("➕ Agregar a la Cotización", use_container_width=True, type="primary"):
                precio_unitario = pd.to_numeric(opciones_precio[precio_sel_str])
                st.session_state.cotizacion_items.append({
                    "Referencia": info_producto[REFERENCIA_COL], "Producto": info_producto[NOMBRE_PRODUCTO_COL],
                    "Cantidad": cantidad, "Precio Unitario": precio_unitario, "Descuento (%)": 0, "Total": cantidad * precio_unitario,
                    "Inventario": stock_actual, "Costo_Unitario": info_producto.get(COSTO_COL, 0)
                })
                st.rerun()

with st.container(border=True):
    st.header("🛒 3. Resumen y Generación de Propuesta")
    if not st.session_state.cotizacion_items:
        st.info("Añada productos para ver el resumen.")
    else:
        edited_df = st.data_editor(pd.DataFrame(st.session_state.cotizacion_items),
            column_config={
                "Producto": st.column_config.TextColumn("Producto", width="large"), "Cantidad": st.column_config.NumberColumn(min_value=1),
                "Descuento (%)": st.column_config.NumberColumn(min_value=0, max_value=100, format="%d%%"),
                "Precio Unitario": st.column_config.NumberColumn(format="$%.0f"), "Total": st.column_config.NumberColumn(format="$%.0f"),
                "Inventario": None, "Referencia": st.column_config.TextColumn("Ref."), "Costo_Unitario": None
            },
            disabled=["Referencia", "Producto", "Precio Unitario", "Total", "Costo_Unitario", "Inventario"],
            hide_index=True, use_container_width=True, num_rows="dynamic")

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
            status_actual = st.selectbox("Establecer Estado:", options=['Borrador', 'Enviada', 'Aprobada', 'Rechazada', 'Pedido para Logística'])
        with col_accion2:
            st.write(""); st.button("💾 Guardar en la Nube", use_container_width=True, type="primary", on_click=guardar_propuesta_en_gsheets, args=(workbook, status_actual))
        
        st.divider()
        col_final1, col_final2 = st.columns(2)
        with col_final1:
            if st.button("🗑️ Vaciar Propuesta", use_container_width=True):
                st.session_state.cotizacion_items = []; st.session_state.cliente_actual = {}; st.session_state.numero_propuesta = f"PROP-{datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d-%H%M%S')}"
                st.rerun()
        with col_final2:
            if st.session_state.get('cliente_actual'):
                df_cot_items = pd.DataFrame(st.session_state.cotizacion_items)
                pdf_data = generar_pdf_profesional(st.session_state.cliente_actual, df_cot_items, subtotal_bruto, descuento_total, iva_valor, total_general, st.session_state.observaciones)
                file_name = f"Propuesta_{st.session_state.numero_propuesta}_{st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente').replace(' ', '_')}.pdf"
                st.download_button("📄 Descargar Propuesta PDF", data=pdf_data, file_name=file_name, mime="application/pdf", use_container_width=True)
            else:
                st.warning("Seleccione un cliente para generar PDF.")
