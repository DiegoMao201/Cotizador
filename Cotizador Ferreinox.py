import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador Inteligente - Ferreinox SAS BIC", page_icon="🔩", layout="wide")

# --- ESTILOS ---
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
REFERENCIA_COL = 'Referencia'
NOMBRE_PRODUCTO_COL = 'Descripción'
INVENTARIO_COL = 'Stock'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
PRODUCTOS_COLS_REQUERIDAS = [REFERENCIA_COL, NOMBRE_PRODUCTO_COL] + PRECIOS_COLS
CLIENTE_NOMBRE_COL = 'Nombre'; CLIENTE_NIT_COL = 'NIF'; CLIENTE_TEL_COL = 'Teléfono'; CLIENTE_DIR_COL = 'Dirección'
CLIENTES_COLS_REQUERIDAS = [CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL]
INVENTARIO_COLS_REQUERIDAS = [REFERENCIA_COL, INVENTARIO_COL]


# --- CLASE PDF PROFESIONAL ---
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = "Ferreinox SAS BIC"; self.company_nit = "NIT: 800.224.617-8"
        self.company_address = "Carrera 13 #19-26, Pereira, Risaralda"
        self.company_contact = "Tel: (606) 333 0101 | www.ferreinox.co"

    def header(self):
        self.set_fill_color(10, 37, 64); self.rect(0, 0, 216, 30, 'F')
        if LOGO_FILE_PATH.exists(): self.image(str(LOGO_FILE_PATH), 15, 8, 45)
        self.set_y(10); self.set_font('Helvetica', 'B', 18); self.set_text_color(255, 255, 255)
        self.cell(0, 8, self.company_name, 0, 1, 'C')
        self.set_font('Helvetica', '', 9); self.cell(0, 5, self.company_nit, 0, 1, 'C')

    def footer(self):
        if FOOTER_IMAGE_PATH.exists(): self.image(str(FOOTER_IMAGE_PATH), 8, 252, 200)
        self.set_y(-15); self.set_font('Helvetica', 'I', 8); self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_profesional(cliente, items_df, subtotal, descuento_total, iva_valor, total_general, obs):
    pdf = PDF('P', 'mm', 'Letter')
    pdf.add_page()
    PRIMARY_COLOR = (10, 37, 64); LIGHT_GREY = (245, 245, 245)
    
    pdf.set_y(35); pdf.set_font('Helvetica', 'B', 10); pdf.set_text_color(80)
    pdf.cell(97.5, 7, 'DATOS DEL CLIENTE', 0, 0, 'L'); pdf.cell(97.5, 7, 'DATOS DE LA EMPRESA', 0, 1, 'L')
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 97.5, pdf.get_y()); pdf.line(pdf.get_x() + 102.5, pdf.get_y(), pdf.get_x() + 195, pdf.get_y())
    pdf.set_font('Helvetica', '', 10); pdf.set_text_color(0)
    y_before = pdf.get_y()
    pdf.multi_cell(97.5, 6, f"{cliente.get(CLIENTE_NOMBRE_COL, 'N/A')}\nNIF/C.C.: {cliente.get(CLIENTE_NIT_COL, 'N/A')}\n"
                            f"Dirección: {cliente.get(CLIENTE_DIR_COL, 'N/A')}\nTeléfono: {cliente.get(CLIENTE_TEL_COL, 'N/A')}", 0, 'L')
    pdf.set_y(y_before); pdf.set_x(112.5)
    pdf.multi_cell(97.5, 6, f"{pdf.company_name}\n{pdf.company_address}\n{pdf.company_contact}\nFecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 'L')
    pdf.set_y(max(pdf.get_y(), y_before + 24) + 5)

    pdf.set_font('Helvetica', 'B', 10); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    col_widths = [20, 75, 15, 25, 25, 25]; headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, h in enumerate(headers): pdf.cell(col_widths[i], 10, h, 0, 0, 'C', fill=True)
    pdf.ln()

    fill = True
    for _, row in items_df.iterrows():
        fill = not fill; pdf.set_fill_color(*LIGHT_GREY) if fill else pdf.set_fill_color(255, 255, 255)
        
        # Lógica de alerta por inventario
        if row.get('Inventario', 0) <= 0: pdf.set_text_color(255, 0, 0)
        else: pdf.set_text_color(0)
        
        pdf.set_font('Helvetica', '', 9)
        pdf.cell(col_widths[0], 10, str(row['Referencia']), 0, 0, 'C', fill)
        pdf.cell(col_widths[1], 10, row['Producto'], 0, 0, 'L', fill)
        pdf.cell(col_widths[2], 10, str(row['Cantidad']), 0, 0, 'C', fill)
        pdf.cell(col_widths[3], 10, f"${row['Precio Unitario']:,.2f}", 0, 0, 'R', fill)
        pdf.cell(col_widths[4], 10, f"{row['Descuento (%)']}%", 0, 0, 'C', fill)
        pdf.set_font('Helvetica', 'B', 9) # Total de línea en negrita
        pdf.cell(col_widths[5], 10, f"${row['Total']:,.2f}", 0, 0, 'R', fill)
        pdf.ln()
    pdf.set_text_color(0) # Resetear color de texto
    
    def add_total_line(label, value, is_bold=False, is_large=False):
        pdf.set_font('Helvetica', 'B' if is_bold else '', 16 if is_large else 11); pdf.set_x(112.5)
        pdf.cell(45, 8, label, 0, 0, 'R'); pdf.cell(40, 8, value, 0, 1, 'R')
    add_total_line('Subtotal:', f"${subtotal:,.2f}"); add_total_line('Descuento:', f"-${descuento_total:,.2f}")
    add_total_line('Base Gravable:', f"${(subtotal - descuento_total):,.2f}", is_bold=True)
    add_total_line('IVA (19%):', f"${iva_valor:,.2f}")
    add_total_line('TOTAL:', f"${total_general:,.2f}", is_bold=True, is_large=True)

    pdf.set_y(200); pdf.set_font('Helvetica', 'B', 10); pdf.cell(0, 7, 'Observaciones:', 0, 1); pdf.set_font('Helvetica', '', 8)
    pdf.multi_cell(0, 5, obs if obs else "Ninguna.", border=0, align='L'); pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 10); pdf.cell(0, 7, 'Términos y Condiciones:', 0, 1); pdf.set_font('Helvetica', '', 8)
    terminos = (f"- Validez de la oferta: {15} días.\n- Para confirmar su pedido, contacte a su asesor de ventas.")
    pdf.multi_cell(0, 5, terminos, align='L')
    
    return bytes(pdf.output())

@st.cache_data
def cargar_y_procesar_datos():
    df_prods = pd.read_excel(PRODUCTOS_FILE_PATH)
    df_inv = pd.read_excel(INVENTARIO_FILE_PATH)
    # Sumar inventario por referencia
    inv_total = df_inv.groupby(REFERENCIA_COL)[INVENTARIO_COL].sum().reset_index()
    # Cruzar con productos
    df_final = pd.merge(df_prods, inv_total, on=REFERENCIA_COL, how='left')
    df_final[INVENTARIO_COL].fillna(0, inplace=True)
    return df_final

# --- INICIALIZACIÓN ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
if 'observaciones' not in st.session_state: st.session_state.observaciones = ""

df_productos = cargar_y_procesar_datos()
df_clientes = cargar_datos(CLIENTES_FILE_PATH, []) if CLIENTES_FILE_PATH.exists() else pd.DataFrame(columns=CLIENTES_COLS_REQUERIDAS)

# --- INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Inteligente Ferreinox SAS BIC")

with st.sidebar:
    # ... (código de sidebar y diagnóstico sin cambios) ...

# ... (código de la interfaz sin cambios) ...

with st.container(border=True): # Cotización Final
    # ...
    # Lógica de recálculo
    recalculated_items = []
    for row in edited_df.to_dict('records'):
        row['Total'] = (row['Cantidad'] * row['Precio Unitario']) * (1 - row['Descuento (%)'] / 100.0)
        recalculated_items.append(row)
    st.session_state.cotizacion_items = recalculated_items
    
    # ...
    # Descarga de PDF
    if st.session_state.cliente_actual:
        df_cot_items = pd.DataFrame(recalculated_items)
        # Añadir info de inventario a los items de la cotización para el PDF
        df_cot_items_con_stock = pd.merge(df_cot_items, df_productos[[REFERENCIA_COL, INVENTARIO_COL]], on=REFERENCIA_COL, how='left')
        df_cot_items_con_stock[INVENTARIO_COL].fillna(0, inplace=True)

        pdf_data = generar_pdf_profesional(st.session_state.cliente_actual, df_cot_items_con_stock, subtotal_bruto, descuento_total, iva_valor, total_general, st.session_state.observaciones)
        st.download_button(...)
