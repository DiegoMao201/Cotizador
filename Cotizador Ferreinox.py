import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador Profesional - Ferreinox SAS BIC", page_icon="🔩", layout="wide")

# --- ESTILOS ---
st.markdown("""<style> ... (código de estilos sin cambios) ... </style>""", unsafe_allow_html=True) # Omitido por brevedad

# --- CONFIGURACIÓN DE RUTAS Y NOMBRES ---
try: BASE_DIR = Path(__file__).resolve().parent
except NameError: BASE_DIR = Path.cwd()

PRODUCTOS_FILE_NAME = 'lista_precios.xlsx'
CLIENTES_FILE_NAME = 'Clientes.xlsx'
LOGO_FILE_NAME = 'Logotipo Ferreinox SAS BIC 2024.png'
FOOTER_IMAGE_NAME = 'INFO-MEMBRETE-INFERIOR.jpg'

PRODUCTOS_FILE_PATH = BASE_DIR / PRODUCTOS_FILE_NAME
CLIENTES_FILE_PATH = BASE_DIR / CLIENTES_FILE_NAME
LOGO_FILE_PATH = BASE_DIR / LOGO_FILE_NAME
FOOTER_IMAGE_PATH = BASE_DIR / FOOTER_IMAGE_NAME

# Columnas (sin cambios)
REFERENCIA_COL = 'Referencia'; NOMBRE_PRODUCTO_COL = 'Descripción'; DESC_ADICIONAL_COL = 'Descripción Adicional'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
PRODUCTOS_COLS_REQUERIDAS = [REFERENCIA_COL, NOMBRE_PRODUCTO_COL, DESC_ADICIONAL_COL] + PRECIOS_COLS
CLIENTE_NOMBRE_COL = 'Nombre'; CLIENTE_NIT_COL = 'NIF'; CLIENTE_TEL_COL = 'Teléfono'; CLIENTE_DIR_COL = 'Dirección'
CLIENTES_COLS_REQUERIDAS = [CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL]


# --- CLASE PDF PROFESIONAL ---
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = "Ferreinox SAS BIC"
        self.company_details_1 = "NIT: 900.XXX.XXX-X"
        self.company_details_2 = "Pereira - Manizales - Armenia - Dosquebradas"

    def header(self):
        # Fondo de color para el encabezado
        self.set_fill_color(10, 37, 64) # Azul oscuro corporativo
        self.rect(0, 0, 216, 40, 'F')
        
        # Logo
        if LOGO_FILE_PATH.exists():
            self.image(str(LOGO_FILE_PATH), 15, 12, 40)
        
        # Título
        self.set_y(12)
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(255, 255, 255) # Texto blanco
        self.cell(0, 10, self.company_name, 0, 1, 'C')
        self.set_font('Helvetica', 'I', 10)
        self.cell(0, 7, self.company_details_1, 0, 1, 'C')
        self.cell(0, 5, self.company_details_2, 0, 1, 'C')
        self.ln(10)

    def footer(self):
        # Pie de página con imagen de membrete
        if FOOTER_IMAGE_PATH.exists():
            self.image(str(FOOTER_IMAGE_PATH), 0, 254, 216) # Posición y ancho completo
        self.set_y(-15) # Posición del número de página
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_profesional(cliente, items_df, subtotal, descuento_total, iva_valor, total_general):
    pdf = PDF('P', 'mm', 'Letter') # Tamaño carta
    pdf.add_page()
    
    # --- Colores ---
    PRIMARY_COLOR = (10, 37, 64); LIGHT_GREY = (240, 240, 240)
    
    # --- Bloque de Información Cliente y Fecha ---
    pdf.set_y(45) # Bajar después del header
    pdf.set_font('Helvetica', '', 11)
    
    # Caja para info del cliente
    pdf.set_fill_color(*LIGHT_GREY)
    pdf.rounded_rect(10, pdf.get_y(), 125, 22, 3.5, 'F')
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(10, 8, '', 0, 0) # Espaciador
    pdf.cell(115, 8, 'Cotizado Para:', 0, 0, 'L')
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(65, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(10, 7, '', 0, 0)
    pdf.cell(115, 7, f"Nombre: {cliente.get(CLIENTE_NOMBRE_COL, 'N/A')}", 0, 1, 'L')
    pdf.cell(10, 7, '', 0, 0)
    pdf.cell(115, 7, f"NIF/C.C.: {cliente.get(CLIENTE_NIT_COL, 'N/A')}", 0, 1, 'L')
    pdf.ln(10)

    # --- Tabla de Productos ---
    pdf.set_font('Helvetica', 'B', 10); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    col_widths = [20, 75, 15, 25, 25, 25]; headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, h in enumerate(headers): pdf.cell(col_widths[i], 10, h, 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font('Helvetica', '', 9); pdf.set_text_color(0); fill = False
    for _, row in items_df.iterrows():
        pdf.set_fill_color(*LIGHT_GREY)
        pdf.cell(col_widths[0], 10, str(row['Referencia']), 'LR', 0, 'C', fill)
        pdf.cell(col_widths[1], 10, row['Producto'], 'LR', 0, 'L', fill)
        pdf.cell(col_widths[2], 10, str(row['Cantidad']), 'LR', 0, 'C', fill)
        pdf.cell(col_widths[3], 10, f"${row['Precio Unitario']:,.2f}", 'LR', 0, 'R', fill)
        pdf.cell(col_widths[4], 10, f"{row['Descuento (%)']}%", 'LR', 0, 'C', fill)
        pdf.cell(col_widths[5], 10, f"${row['Total']:,.2f}", 'LR', 0, 'R', fill)
        pdf.ln(); fill = not fill
    pdf.cell(sum(col_widths), 0, '', 'T') # Línea final de la tabla
    pdf.ln(5)

    # --- Sección de Totales ---
    def add_total_line(label, value, is_bold=False, is_large=False):
        style = 'B' if is_bold else ''; size = 16 if is_large else 11
        pdf.set_font('Helvetica', style, size)
        pdf.set_x(105); pdf.cell(50, 8, label, 0, 0, 'R'); pdf.cell(40, 8, value, 0, 1, 'R')

    add_total_line('Subtotal:', f"${subtotal:,.2f}")
    add_total_line('Descuento Total:', f"-${descuento_total:,.2f}")
    add_total_line('Base Gravable:', f"${(subtotal - descuento_total):,.2f}", is_bold=True)
    add_total_line('IVA (19%):', f"${iva_valor:,.2f}")
    add_total_line('TOTAL A PAGAR:', f"${total_general:,.2f}", is_bold=True, is_large=True)

    # --- Términos y Condiciones Anclados al Fondo ---
    pdf.set_y(200) # Posición fija para uniformidad
    pdf.set_font('Helvetica', 'B', 10); pdf.cell(0, 7, 'Observaciones y Términos:', 0, 1)
    pdf.set_font('Helvetica', '', 8); pdf.set_text_color(80)
    dias_validez = 15; fecha_vencimiento = datetime.now() + timedelta(days=dias_validez)
    terminos = (f"- Esta cotización es válida hasta el {fecha_vencimiento.strftime('%d/%m/%Y')}.\n"
                f"- Los precios no incluyen costos de envío.\n"
                f"- Tiempo de entrega: 2-3 días hábiles tras confirmación de la orden.\n"
                f"- Forma de pago: 50% anticipado, 50% contra entrega.\n"
                f"- Para confirmar su pedido, por favor contacte a su asesor de ventas. ¡Gracias por su confianza!")
    pdf.multi_cell(0, 5, terminos, align='L')
    
    return bytes(pdf.output())

# --- FUNCIONES DE CARGA Y VERIFICACIÓN ---
@st.cache_data
def cargar_datos(path, cols_num):
    if not path.exists(): return None
    try: return pd.read_excel(path).astype({c: 'float' for c in cols_num if c in pd.read_excel(path).columns})
    except Exception: return None
# ... (El resto del código de la app, que es la interfaz, no necesita cambios y se omite aquí por brevedad) ...
# ... Pero se incluirá en el bloque de código final para el usuario ...
# --- INICIALIZACIÓN ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
df_productos_bruto = cargar_datos(PRODUCTOS_FILE_PATH, PRECIOS_COLS)
df_clientes = cargar_datos(CLIENTES_FILE_PATH, [])
if df_productos_bruto is None or (df_clientes is None and CLIENTES_FILE_PATH.exists()): st.stop()
if not all(c in df_productos_bruto.columns for c in PRODUCTOS_COLS_REQUERIDAS) or \
   (df_clientes is not None and not all(c in df_clientes.columns for c in CLIENTES_COLS_REQUERIDAS)):
    st.error("Faltan columnas en los archivos. Revise la sección de diagnóstico."); st.stop()
df_productos = df_productos_bruto.dropna(subset=[NOMBRE_PRODUCTO_COL, REFERENCIA_COL]).copy()

# --- INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Profesional Ferreinox SAS BIC")
with st.sidebar:
    if LOGO_FILE_PATH.exists(): st.image(str(LOGO_FILE_PATH))
    st.title("⚙️ Búsqueda")
    df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos[REFERENCIA_COL].astype(str) + ")"
    termino_busqueda = st.text_input("Buscar Producto:", placeholder="Nombre o referencia...")
    
    # Diagnóstico de Archivos
    with st.expander("Diagnóstico de Archivos"):
        st.write(f"Logo: { '✅ Encontrado' if LOGO_FILE_PATH.exists() else '❌ NO ENCONTRADO'}")
        st.write(f"Pie de Página: { '✅ Encontrado' if FOOTER_IMAGE_PATH.exists() else '❌ NO ENCONTRADO'}")
        st.write(f"Clientes: { '✅ Encontrado' if CLIENTES_FILE_PATH.exists() else '❌ NO ENCONTRADO'}")
        st.write(f"Precios: { '✅ Encontrado' if PRODUCTOS_FILE_PATH.exists() else '❌ NO ENCONTRADO'}")

df_filtrado = df_productos[df_productos['Busqueda'].str.contains(termino_busqueda, case=False, na=False)] if termino_busqueda else df_productos

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
        edited_df = st.data_editor(pd.DataFrame(st.session_state.cotizacion_items),
            column_config={
                "Producto": st.column_config.TextColumn(width="large"), "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
                "Descuento (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1, format="%d%%"),
                "Precio Unitario": st.column_config.NumberColumn(format="$%.2f"), "Total": st.column_config.NumberColumn(format="$%.2f"),
            },
            disabled=["Referencia", "Precio Unitario", "Total"], hide_index=True, use_container_width=True, num_rows="dynamic")
        recalculated_items = []
        for row in edited_df.to_dict('records'):
            subtotal_item = row['Cantidad'] * row['Precio Unitario']
            descuento_valor = subtotal_item * (row['Descuento (%)'] / 100.0)
            row['Total'] = subtotal_item - descuento_valor
            recalculated_items.append(row)
        st.session_state.cotizacion_items = recalculated_items
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
                pdf_data = generar_pdf_profesional(st.session_state.cliente_actual, pd.DataFrame(recalculated_items), subtotal_bruto, descuento_total, iva_valor, total_general)
                st.download_button("📄 Descargar Cotización PDF", pdf_data, f"Cotizacion_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True, type="primary")
            else: st.warning("Seleccione un cliente para descargar.")
