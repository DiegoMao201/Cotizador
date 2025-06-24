import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador Profesional - Ferreinox SAS BIC", page_icon="🔩", layout="wide")

# --- ESTILOS ---
st.markdown("""<style> ... (código de estilos sin cambios) ... </style>""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DE RUTAS Y NOMBRES ---
try: BASE_DIR = Path(__file__).resolve().parent
except NameError: BASE_DIR = Path.cwd()

PRODUCTOS_FILE_NAME = 'lista_precios.xlsx'
CLIENTES_FILE_NAME = 'Clientes.xlsx'
LOGO_FILE_NAME = 'Logotipo Ferreinox SAS BIC 2024.png'
FOOTER_IMAGE_NAME = 'INFO-MEMBRESIA-INFERIOR.jpg' # Corregido según tu captura

PRODUCTOS_FILE_PATH = BASE_DIR / PRODUCTOS_FILE_NAME
CLIENTES_FILE_PATH = BASE_DIR / CLIENTES_FILE_NAME
LOGO_FILE_PATH = BASE_DIR / LOGO_FILE_NAME
FOOTER_IMAGE_PATH = BASE_DIR / FOOTER_IMAGE_NAME

# Columnas
REFERENCIA_COL = 'Referencia'; NOMBRE_PRODUCTO_COL = 'Descripción'; DESC_ADICIONAL_COL = 'Descripción Adicional'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
PRODUCTOS_COLS_REQUERIDAS = [REFERENCIA_COL, NOMBRE_PRODUCTO_COL, DESC_ADICIONAL_COL] + PRECIOS_COLS
CLIENTE_NOMBRE_COL = 'Nombre'; CLIENTE_NIT_COL = 'NIF'; CLIENTE_TEL_COL = 'Teléfono'; CLIENTE_DIR_COL = 'Dirección'
CLIENTES_COLS_REQUERIDAS = [CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL]


# --- CLASE PDF PROFESIONAL (VERSIÓN DE DISEÑO AVANZADO) ---
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = "Ferreinox SAS BIC"
        self.company_nit = "NIT: 800.224.617-8"
        self.company_address = "Calle 14 #15-32, Dosquebradas, Risaralda"
        self.company_contact = "Tel: (606) 330 4539 | www.ferreinox.co"

    def header(self):
        # Fondo de color para el encabezado
        self.set_fill_color(10, 37, 64) # Azul Oscuro Ferreinox
        self.rect(0, 0, 216, 30, 'F')
        
        # Logo
        if LOGO_FILE_PATH.exists():
            self.image(str(LOGO_FILE_PATH), 15, 8, 30)
        
        # Título
        self.set_y(10)
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, self.company_name, 0, 1, 'C')
        self.set_font('Helvetica', '', 9)
        self.cell(0, 5, self.company_nit, 0, 1, 'C')
        self.ln(10)

    def footer(self):
        if FOOTER_IMAGE_PATH.exists():
            self.image(str(FOOTER_IMAGE_PATH), 8, 252, 200)

def generar_pdf_excepcional(cliente, items_df, subtotal, descuento_total, iva_valor, total_general):
    pdf = PDF('P', 'mm', 'Letter')
    pdf.add_page()
    
    PRIMARY_COLOR = (10, 37, 64); LIGHT_GREY = (245, 245, 245); BORDER_COLOR = (220, 220, 220)
    
    pdf.set_y(35)
    
    # --- BLOQUE DE DOS COLUMNAS: CLIENTE Y EMPRESA ---
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(80)
    pdf.cell(97.5, 7, 'DATOS DEL CLIENTE', 0, 0, 'L')
    pdf.cell(97.5, 7, 'DATOS DE LA EMPRESA', 0, 1, 'L')
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 97.5, pdf.get_y())
    pdf.line(pdf.get_x() + 102.5, pdf.get_y(), pdf.get_x() + 195, pdf.get_y())

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0)
    
    # Datos del cliente (columna izquierda)
    y_before = pdf.get_y()
    pdf.multi_cell(97.5, 6, f"{cliente.get(CLIENTE_NOMBRE_COL, 'N/A')}\n"
                            f"NIF/C.C.: {cliente.get(CLIENTE_NIT_COL, 'N/A')}\n"
                            f"Dirección: {cliente.get(CLIENTE_DIR_COL, 'N/A')}\n"
                            f"Teléfono: {cliente.get(CLIENTE_TEL_COL, 'N/A')}", 0, 'L')
    y_after_cliente = pdf.get_y()
    
    # Datos de la empresa (columna derecha)
    pdf.set_y(y_before)
    pdf.set_x(112.5)
    pdf.multi_cell(97.5, 6, f"{pdf.company_name}\n"
                            f"{pdf.company_address}\n"
                            f"{pdf.company_contact}\n"
                            f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 'L')
    y_after_empresa = pdf.get_y()

    pdf.set_y(max(y_after_cliente, y_after_empresa) + 5)

    # --- Tabla de Productos ---
    pdf.set_font('Helvetica', 'B', 10); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    col_widths = [20, 75, 15, 25, 25, 25]; headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, h in enumerate(headers): pdf.cell(col_widths[i], 10, h, 0, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font('Helvetica', '', 9); pdf.set_text_color(0); fill = True
    for _, row in items_df.iterrows():
        fill = not fill
        pdf.set_fill_color(*LIGHT_GREY) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(col_widths[0], 10, str(row['Referencia']), 0, 0, 'C', fill)
        pdf.cell(col_widths[1], 10, row['Producto'], 0, 0, 'L', fill)
        pdf.cell(col_widths[2], 10, str(row['Cantidad']), 0, 0, 'C', fill)
        pdf.cell(col_widths[3], 10, f"${row['Precio Unitario']:,.2f}", 0, 0, 'R', fill)
        pdf.cell(col_widths[4], 10, f"{row['Descuento (%)']}%", 0, 0, 'C', fill)
        pdf.cell(col_widths[5], 10, f"${row['Total']:,.2f}", 0, 0, 'R', fill)
        pdf.ln()
    pdf.ln(1)

    # --- Sección de Totales ---
    pdf.set_x(112.5)
    pdf.set_fill_color(*LIGHT_GREY)
    pdf.rect(112.5, pdf.get_y(), 92.5, 36, 'F')
    
    def add_total_line(label, value_str, is_bold=False, is_large=False):
        style = 'B' if is_bold else ''; size = 16 if is_large else 10
        pdf.set_font('Helvetica', style, size)
        pdf.set_x(117.5); pdf.cell(45, 7, label, 0, 0, 'R'); pdf.cell(40, 7, value_str, 0, 1, 'R')

    add_total_line('Subtotal:', f"${subtotal:,.2f}")
    add_total_line('Descuento Total:', f"-${descuento_total:,.2f}")
    add_total_line('Base Gravable:', f"${(subtotal - descuento_total):,.2f}", is_bold=True)
    add_total_line('IVA (19%):', f"${iva_valor:,.2f}")
    add_total_line('TOTAL A PAGAR:', f"${total_general:,.2f}", is_bold=True, is_large=True)

    # --- Términos, Firma y Condiciones ---
    pdf.set_y(pdf.get_y() + 10 if pdf.get_y() < 180 else 200) # Anclaje inteligente
    
    # Línea de Firma
    pdf.set_y(pdf.get_y() + 15)
    pdf.line(20, pdf.get_y(), 90, pdf.get_y())
    pdf.set_y(pdf.get_y() + 1)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(95, 5, 'Firma Autorizada', 0, 1, 'C')

    pdf.set_y(pdf.get_y() + 5)
    pdf.set_font('Helvetica', 'B', 10); pdf.cell(0, 7, 'Términos y Condiciones:', 0, 1)
    pdf.set_font('Helvetica', '', 8); pdf.set_text_color(80)
    dias_validez = 15; fecha_vencimiento = datetime.now() + timedelta(days=dias_validez)
    terminos = (f"- Validez de la oferta hasta el {fecha_vencimiento.strftime('%d de %B de %Y')}."
                " Precios sujetos a cambio sin previo aviso después de esta fecha.\n"
                "- Forma de pago: 50% anticipado para procesar la orden, 50% contra entrega.\n"
                "- Tiempo de entrega: 2-3 días hábiles en el Eje Cafetero. "
                "No incluye costos de envío fuera del área metropolitana.\n"
                "- Para confirmar su pedido, por favor contacte a su asesor de ventas. ¡Gracias por su confianza!")
    pdf.multi_cell(0, 5, terminos, align='L')
    
    return bytes(pdf.output())
    
# --- FUNCIONES DE CARGA Y VERIFICACIÓN ---
@st.cache_data
def cargar_datos(path, cols_num):
    if not path.exists(): return None
    try: return pd.read_excel(path).astype({c: 'float' for c in cols_num if c in pd.read_excel(path).columns})
    except Exception as e: st.exception(e); return None

# ... (El resto del código de la app no necesita cambios y se omite aquí por brevedad) ...
def verificar_columnas(df, columnas, nombre):
    if df is None: return False
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes: st.error(f"Error en '{nombre}': Faltan columnas: **{', '.join(faltantes)}**"); return False
    return True
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
df_productos_bruto = cargar_datos(PRODUCTOS_FILE_PATH, PRECIOS_COLS)
df_clientes = cargar_datos(CLIENTES_FILE_PATH, [])
if df_productos_bruto is None or (df_clientes is None and CLIENTES_FILE_PATH.exists()): st.stop()
if not verificar_columnas(df_productos_bruto, PRODUCTOS_COLS_REQUERIDAS, PRODUCTOS_FILE_NAME) or \
   (df_clientes is not None and not verificar_columnas(df_clientes, CLIENTES_COLS_REQUERIDAS, CLIENTES_FILE_NAME)):
    st.error("Faltan columnas en los archivos. Revise la sección de diagnóstico."); st.stop()
df_productos = df_productos_bruto.dropna(subset=[NOMBRE_PRODUCTO_COL, REFERENCIA_COL]).copy()
st.title("🔩 Cotizador Profesional Ferreinox SAS BIC")
with st.sidebar:
    if LOGO_FILE_PATH.exists(): st.image(str(LOGO_FILE_PATH))
    st.title("⚙️ Búsqueda")
    df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos[REFERENCIA_COL].astype(str) + ")"
    termino_busqueda = st.text_input("Buscar Producto:", placeholder="Nombre o referencia...")
    with st.expander("Diagnóstico de Archivos"):
        st.write(f"Logo: { '✅ Encontrado' if LOGO_FILE_PATH.exists() else '❌ NO ENCONTRADO'}")
        st.write(f"Pie de Página: { '✅ Encontrado' if FOOTER_IMAGE_PATH.exists() else '❌ NO ENCONTRADO'}")
        st.write(f"Clientes: { '✅ Encontrado' if CLIENTES_FILE_PATH.exists() else '❌ NO ENCONTRADO'}")
        st.write(f"Precios: { '✅ Encontrado' if PRODUCTOS_FILE_PATH.exists() else '❌ NO ENCONTRADO'}")
df_filtrado = df_productos[df_productos['Busqueda'].str.contains(termino_busqueda, case=False, na=False)] if termino_busqueda else df_productos
with st.container(border=True): # Cliente
    st.header("👤 1. Datos del Cliente")
    # ... (código de cliente sin cambios) ...
with st.container(border=True): # Agregar Productos
    st.header("📦 2. Agregar Productos")
    # ... (código de agregar productos sin cambios) ...
with st.container(border=True): # Cotización Final
    st.header("🛒 3. Cotización Final")
    if not st.session_state.cotizacion_items: st.info("El carrito está vacío.")
    else:
        # ... (código de la tabla editable sin cambios) ...
        recalculated_items = # ... (lógica de recálculo sin cambios) ...
        # ... (cálculo de totales sin cambios) ...
        st.divider()
        st.subheader("Resumen Financiero")
        # ... (métricas sin cambios) ...
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Vaciar Cotización", use_container_width=True): st.session_state.cotizacion_items = []; st.rerun()
        with col2:
            if st.session_state.cliente_actual:
                pdf_data = generar_pdf_excepcional(st.session_state.cliente_actual, pd.DataFrame(recalculated_items), subtotal_bruto, descuento_total, iva_valor, total_general)
                st.download_button("📄 Descargar Cotización PDF", pdf_data, f"Cotizacion_{st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente')}_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True, type="primary")
            else: st.warning("Seleccione un cliente para descargar.")
