import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Cotizador Maestro - Ferreinox SAS",
    page_icon="🔩",
    layout="wide"
)

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
try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path.cwd()

PRODUCTOS_FILE_NAME = 'lista_precios.xlsx'
CLIENTES_FILE_NAME = 'Clientes.xlsx'
LOGO_FILE_NAME = 'Logotipo Ferreinox SAS BIC 2024.png'

PRODUCTOS_FILE_PATH = BASE_DIR / PRODUCTOS_FILE_NAME
CLIENTES_FILE_PATH = BASE_DIR / CLIENTES_FILE_NAME
LOGO_FILE_PATH = BASE_DIR / LOGO_FILE_NAME

# Columnas del archivo de productos
REFERENCIA_COL = 'Referencia'
NOMBRE_PRODUCTO_COL = 'Descripción'
DESC_ADICIONAL_COL = 'Descripción Adicional'
PRECIOS_COLS = [
    'Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios',
    'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados'
]
PRODUCTOS_COLS_REQUERIDAS = [REFERENCIA_COL, NOMBRE_PRODUCTO_COL, DESC_ADICIONAL_COL] + PRECIOS_COLS

# Columnas del archivo de clientes
CLIENTE_NOMBRE_COL = 'Nombre'
CLIENTE_NIT_COL = 'NIF'
CLIENTE_TEL_COL = 'Teléfono'
CLIENTE_DIR_COL = 'Dirección'
CLIENTES_COLS_REQUERIDAS = [CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL]


# --- CLASE PARA GENERAR PDF PROFESIONAL ---
class PDF(FPDF):
    def header(self):
        if LOGO_FILE_PATH.exists(): self.image(str(LOGO_FILE_PATH), 10, 8, 33)
        self.set_font('Helvetica', 'B', 15); self.cell(80); self.cell(30, 10, 'Cotización', 0, 0, 'C'); self.ln(20)

    def footer(self):
        self.set_y(-15); self.set_font('Helvetica', 'I', 8); self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_cotizacion(cliente, items_df, subtotal, descuento_total, iva_valor, total_general):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Helvetica', '', 12)
    fecha_actual = datetime.now().strftime("%d/%m/%Y"); numero_cotizacion = datetime.now().strftime("%Y%m%d-%H%M")
    pdf.cell(0, 10, f'Fecha: {fecha_actual}', 0, 1); pdf.cell(0, 10, f'Cotización No: {numero_cotizacion}', 0, 1); pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 12); pdf.cell(0, 10, 'Cliente:', 0, 1); pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 7, f"Nombre: {cliente.get(CLIENTE_NOMBRE_COL, 'N/A')}", 0, 1)
    pdf.cell(0, 7, f"NIF/C.C.: {cliente.get(CLIENTE_NIT_COL, 'N/A')}", 0, 1); pdf.ln(10)

    pdf.set_font('Helvetica', 'B', 10)
    col_widths = [20, 75, 15, 25, 25, 25]
    headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, header in enumerate(headers): pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
    pdf.ln()

    pdf.set_font('Helvetica', '', 9)
    for _, row in items_df.iterrows():
        pdf.cell(col_widths[0], 10, str(row['Referencia']), 1)
        pdf.cell(col_widths[1], 10, row['Producto'], 1)
        pdf.cell(col_widths[2], 10, str(row['Cantidad']), 1, 0, 'C')
        pdf.cell(col_widths[3], 10, f"${row['Precio Unitario']:,.2f}", 1, 0, 'R')
        pdf.cell(col_widths[4], 10, f"{row['Descuento (%)']}%", 1, 0, 'C')
        pdf.cell(col_widths[5], 10, f"${row['Total']:,.2f}", 1, 0, 'R')
        pdf.ln()

    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 12)
    def add_total_line(label, value_str):
        pdf.set_x(-80); pdf.cell(40, 10, label, 0, 0, 'R'); pdf.cell(30, 10, value_str, 0, 1, 'R')
    
    add_total_line('Subtotal:', f"${subtotal:,.2f}")
    add_total_line('Descuento Total:', f"-${descuento_total:,.2f}")
    add_total_line('Base Gravable:', f"${(subtotal - descuento_total):,.2f}")
    add_total_line('IVA (19%):', f"${iva_valor:,.2f}")
    pdf.set_font('Helvetica', 'B', 14)
    add_total_line('TOTAL:', f"${total_general:,.2f}")
    
    # CORRECCIÓN DEL ERROR: .output() ya devuelve bytes, no necesita .encode()
    return pdf.output()

# --- FUNCIONES DE CARGA Y VERIFICACIÓN ---
@st.cache_data
def cargar_datos(path_archivo, columnas_num):
    nombre_archivo = path_archivo.name
    if not path_archivo.exists(): return None
    try:
        df = pd.read_excel(path_archivo)
        for col in columnas_num:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e: st.exception(e); return None

def verificar_columnas(df, columnas, nombre):
    if df is None: return False
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes: st.error(f"Error en '{nombre}': Faltan columnas: **{', '.join(faltantes)}**"); return False
    return True

# --- INICIALIZACIÓN ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}

df_productos_bruto = cargar_datos(PRODUCTOS_FILE_PATH, PRECIOS_COLS)
df_clientes = cargar_datos(CLIENTES_FILE_PATH, [])

if not verificar_columnas(df_productos_bruto, PRODUCTOS_COLS_REQUERIDAS, PRODUCTOS_FILE_NAME): st.stop()
if df_clientes is not None and not verificar_columnas(df_clientes, CLIENTES_COLS_REQUERIDAS, CLIENTES_FILE_NAME): st.stop()

df_productos = df_productos_bruto.dropna(subset=[NOMBRE_PRODUCTO_COL, REFERENCIA_COL]).copy()

# --- INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Maestro Ferreinox SAS")

with st.sidebar:
    if LOGO_FILE_PATH.exists(): st.image(str(LOGO_FILE_PATH))
    st.title("⚙️ Búsqueda")
    df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos[REFERENCIA_COL].astype(str) + ")"
    termino_busqueda = st.text_input("Buscar Producto:", placeholder="Nombre o referencia...")

df_filtrado = df_productos[df_productos['Busqueda'].str.contains(termino_busqueda, case=False, na=False)] if termino_busqueda else df_productos

# ... (Sección de Cliente sin cambios) ...
with st.container(border=True): # Cliente
    st.header("👤 1. Datos del Cliente")
    tab_existente, tab_nuevo = st.tabs(["Seleccionar Cliente Existente", "Registrar Cliente Nuevo"])
    
    with tab_existente:
        if df_clientes is not None:
            lista_clientes = [""] + df_clientes[CLIENTE_NOMBRE_COL].tolist()
            cliente_sel_nombre = st.selectbox("Clientes guardados:", lista_clientes, index=0)
            if cliente_sel_nombre: st.session_state.cliente_actual = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0].to_dict()
        else: st.info("No se pudo cargar el archivo de clientes.")
    
    with tab_nuevo:
        with st.form("form_nuevo_cliente"):
            nombre = st.text_input(f"{CLIENTE_NOMBRE_COL}*"); nit = st.text_input(CLIENTE_NIT_COL)
            tel = st.text_input(CLIENTE_TEL_COL); direc = st.text_input(CLIENTE_DIR_COL)
            if st.form_submit_button("Usar este Cliente"):
                if not nombre: st.warning("El nombre es obligatorio.")
                else:
                    st.session_state.cliente_actual = {CLIENTE_NOMBRE_COL: nombre, CLIENTE_NIT_COL: nit, CLIENTE_TEL_COL: tel, CLIENTE_DIR_COL: direc}
                    st.success(f"Cliente '{nombre}' listo.")

with st.container(border=True): # Agregar Productos
    st.header("📦 2. Agregar Productos")
    producto_sel_str = st.selectbox("Buscar y seleccionar:", options=df_filtrado['Busqueda'], index=None, placeholder="Escriba para buscar...")
    if producto_sel_str:
        info_producto = df_filtrado[df_filtrado['Busqueda'] == producto_sel_str].iloc[0]
        st.subheader(f"Producto: {info_producto[NOMBRE_PRODUCTO_COL]}")
        col1, col2 = st.columns([2,1]); 
        with col1:
            opciones_precio = {f"{l} - ${info_producto.get(l, 0):,.2f}": (l, info_producto.get(l, 0)) for l in PRECIOS_COLS}
            precio_sel_str = st.radio("Precio:", options=opciones_precio.keys())
        with col2:
            cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1)
            if st.button("➕ Agregar", use_container_width=True, type="primary"):
                lista_aplicada, precio_unitario = opciones_precio[precio_sel_str]
                st.session_state.cotizacion_items.append({
                    "Referencia": info_producto[REFERENCIA_COL], "Producto": info_producto[NOMBRE_PRODUCTO_COL],
                    "Cantidad": cantidad, "Precio Unitario": precio_unitario, "Descuento (%)": 0, "Total": cantidad * precio_unitario
                }); st.toast(f"✅ Agregado!", icon="🛒"); st.rerun()

with st.container(border=True): # Cotización Final
    st.header("🛒 3. Cotización Final")
    if not st.session_state.cotizacion_items: st.info("El carrito está vacío.")
    else:
        st.markdown("**Puede editar Cantidad, Producto y Descuento. Use (🗑️) para eliminar filas.**")
        
        # --- EDITOR DE DATOS AVANZADO ---
        edited_df = st.data_editor(
            pd.DataFrame(st.session_state.cotizacion_items),
            column_config={
                "Producto": st.column_config.TextColumn(width="large"),
                "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
                "Descuento (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1, format="%d%%"),
                "Precio Unitario": st.column_config.NumberColumn(format="$%.2f"),
                "Total": st.column_config.NumberColumn(format="$%.2f"),
            },
            disabled=["Referencia", "Precio Unitario", "Total"],
            hide_index=True, use_container_width=True,
            num_rows="dynamic" # PERMITE AGREGAR Y ELIMINAR FILAS
        )

        # --- RE-CÁLCULO AUTOMÁTICO TRAS EDICIÓN ---
        recalculated_items = []
        for row in edited_df.to_dict('records'):
            subtotal_item = row['Cantidad'] * row['Precio Unitario']
            descuento_valor = subtotal_item * (row['Descuento (%)'] / 100.0)
            row['Total'] = subtotal_item - descuento_valor
            recalculated_items.append(row)
        st.session_state.cotizacion_items = recalculated_items
        
        # --- CÁLCULO DE TOTALES FINALES ---
        subtotal_bruto = sum(item['Cantidad'] * item['Precio Unitario'] for item in recalculated_items)
        descuento_total = sum((item['Cantidad'] * item['Precio Unitario']) * (item['Descuento (%)'] / 100.0) for item in recalculated_items)
        base_gravable = subtotal_bruto - descuento_total
        iva_valor = base_gravable * 0.19
        total_general = base_gravable + iva_valor

        st.divider()
        st.subheader("Resumen Financiero")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Subtotal Bruto", f"${subtotal_bruto:,.2f}")
        m2.metric("Descuento Total", f"-${descuento_total:,.2f}")
        m3.metric("IVA (19%)", f"${iva_valor:,.2f}")
        m4.metric("Total General", f"${total_general:,.2f}", delta_color="off")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Vaciar Cotización", use_container_width=True): st.session_state.cotizacion_items = []; st.rerun()
        with col2:
            if st.session_state.cliente_actual:
                pdf_data = generar_pdf_cotizacion(st.session_state.cliente_actual, edited_df, subtotal_bruto, descuento_total, iva_valor, total_general)
                st.download_button("📄 Descargar Cotización en PDF", pdf_data, f"Cotizacion_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True, type="primary")
            else: st.warning("Seleccione un cliente para descargar.")
