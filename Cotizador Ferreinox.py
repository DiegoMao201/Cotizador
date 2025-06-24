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
        self.set_font('Helvetica', '', 9); self.cell(0, 5, self.company_nit, 0, 1, 'C'); self.ln(10)

    def footer(self):
        if FOOTER_IMAGE_PATH.exists(): self.image(str(FOOTER_IMAGE_PATH), 8, 252, 200)
        self.set_y(-15); self.set_font('Helvetica', 'I', 8); self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_profesional(cliente, items_df, subtotal, descuento_total, iva_valor, total_general, observaciones):
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
    y_after_cliente = pdf.get_y()
    
    pdf.set_y(y_before); pdf.set_x(112.5)
    pdf.multi_cell(97.5, 6, f"{pdf.company_name}\n{pdf.company_address}\n{pdf.company_contact}\nFecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 'L')
    pdf.set_y(max(y_after_cliente, y_after_empresa) + 5)

    pdf.set_font('Helvetica', 'B', 10); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    col_widths = [20, 75, 15, 25, 25, 25]; headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, h in enumerate(headers): pdf.cell(col_widths[i], 10, h, 0, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font('Helvetica', '', 9); fill = True
    for _, row in items_df.iterrows():
        fill = not fill; pdf.set_fill_color(*LIGHT_GREY) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(255, 0, 0) if row.get('Inventario', 0) <= 0 else pdf.set_text_color(0)
        pdf.cell(col_widths[0], 10, str(row['Referencia']), 0, 0, 'C', fill)
        pdf.cell(col_widths[1], 10, row['Producto'], 0, 0, 'L', fill)
        pdf.cell(col_widths[2], 10, str(row['Cantidad']), 0, 0, 'C', fill)
        pdf.cell(col_widths[3], 10, f"${row['Precio Unitario']:,.2f}", 0, 0, 'R', fill)
        pdf.cell(col_widths[4], 10, f"{row['Descuento (%)']}%", 0, 0, 'C', fill)
        pdf.set_font('Helvetica', 'B', 9); pdf.cell(col_widths[5], 10, f"${row['Total']:,.2f}", 0, 0, 'R', fill); pdf.set_font('Helvetica', '', 9)
        pdf.ln()
    pdf.set_text_color(0)
    
    def add_total_line(label, value_str, is_bold=False, is_large=False):
        style = 'B' if is_bold else ''; size = 16 if is_large else 10
        pdf.set_font('Helvetica', style, size); pdf.set_x(112.5)
        pdf.cell(45, 8, label, 0, 0, 'R'); pdf.cell(40, 8, value_str, 0, 1, 'R')
    add_total_line('Subtotal:', f"${subtotal:,.2f}"); add_total_line('Descuento Total:', f"-${descuento_total:,.2f}")
    add_total_line('Base Gravable:', f"${(subtotal - descuento_total):,.2f}", is_bold=True)
    add_total_line('IVA (19%):', f"${iva_valor:,.2f}"); add_total_line('TOTAL A PAGAR:', f"${total_general:,.2f}", is_bold=True, is_large=True)

    pdf.set_y(195); pdf.set_font('Helvetica', 'B', 10); pdf.cell(0, 7, 'Observaciones Adicionales:', 0, 1)
    pdf.set_font('Helvetica', '', 8); pdf.set_text_color(0)
    pdf.multi_cell(0, 5, observaciones if observaciones else "Ninguna.", border=0, align='L'); pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 10); pdf.cell(0, 7, 'Términos y Condiciones:', 0, 1)
    pdf.set_font('Helvetica', '', 8); pdf.set_text_color(80)
    terminos = (f"- Validez de la oferta: {15} días.\n- Para confirmar su pedido, contacte a su asesor de ventas.")
    pdf.multi_cell(0, 5, terminos, align='L')
    
    return bytes(pdf.output())

# --- FUNCIONES DE CARGA Y VERIFICACIÓN ---
@st.cache_data
def cargar_archivo_excel(path):
    if not path.exists(): return None
    try: return pd.read_excel(path)
    except Exception as e: st.error(f"Error al leer {path.name}:"); st.exception(e); return None

def verificar_columnas(df, columnas, nombre):
    if df is None: return False
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes: st.error(f"Error en '{nombre}': Faltan columnas: **{', '.join(faltantes)}**"); return False
    return True

# --- INICIALIZACIÓN ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
if 'observaciones' not in st.session_state: st.session_state.observaciones = ""

# Carga de datos brutos
df_productos_bruto = cargar_archivo_excel(PRODUCTOS_FILE_PATH)
df_clientes = cargar_archivo_excel(CLIENTES_FILE_PATH)
df_inventario_bruto = cargar_archivo_excel(INVENTARIO_FILE_PATH)

st.title("🔩 Cotizador Profesional Ferreinox SAS BIC")

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
    st.error("No se pudo cargar el archivo de precios. La aplicación no puede continuar."); st.stop()

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
if 'con_stock' not in st.session_state: st.session_state.con_stock = con_stock; st.session_state.sin_stock = sin_stock
st.sidebar.info(f"Refs. con Stock: {st.session_state.con_stock} | Refs. sin Stock: {st.session_state.sin_stock}")

df_filtrado = df_productos[df_productos['Busqueda'].str.contains(termino_busqueda, case=False, na=False)] if termino_busqueda else df_productos

# --- Interfaz de Cliente ---
with st.container(border=True):
    st.header("👤 1. Datos del Cliente")
    tab_existente, tab_nuevo = st.tabs(["Seleccionar Cliente Existente", "Registrar Cliente Nuevo"])
    with tab_existente:
        if df_clientes is not None:
            lista_clientes = [""] + df_clientes[CLIENTE_NOMBRE_COL].tolist()
            cliente_sel_nombre = st.selectbox("Clientes guardados:", lista_clientes, index=0)
            if cliente_sel_nombre: st.session_state.cliente_actual = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0].to_dict()
        else: st.info("No se pudo cargar el archivo de clientes.")
    with tab_nuevo:
        with st.form("form_new_client", clear_on_submit=True):
            nombre = st.text_input(f"{CLIENTE_NOMBRE_COL}*"); nit = st.text_input(CLIENTE_NIT_COL)
            tel = st.text_input(CLIENTE_TEL_COL); direc = st.text_input(CLIENTE_DIR_COL)
            if st.form_submit_button("Usar este Cliente"):
                if not nombre: st.warning("El nombre es obligatorio.")
                else:
                    st.session_state.cliente_actual = {CLIENTE_NOMBRE_COL: nombre, CLIENTE_NIT_COL: nit, CLIENTE_TEL_COL: tel, CLIENTE_DIR_COL: direc}
                    st.success(f"Cliente '{nombre}' listo."); st.rerun()

# --- Interfaz para Agregar Productos ---
with st.container(border=True):
    st.header("📦 2. Agregar Productos")
    producto_sel_str = st.selectbox("Buscar y seleccionar:", options=df_filtrado['Busqueda'], index=None, placeholder="Escriba para buscar...")
    if producto_sel_str:
        info_producto = df_filtrado[df_filtrado['Busqueda'] == producto_sel_str].iloc[0]
        st.subheader(f"Producto: {info_producto[NOMBRE_PRODUCTO_COL]}")
        if info_producto[INVENTARIO_COL] <= 0 and info_producto[INVENTARIO_COL] != -1:
            st.warning(f"⚠️ ¡Atención! No hay inventario disponible para este producto.", icon="📦")
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
                    "Cantidad": cantidad, "Precio Unitario": precio_unitario, "Descuento (%)": 0, "Total": cantidad * precio_unitario,
                    "Inventario": info_producto[INVENTARIO_COL]
                }); st.toast(f"✅ Agregado!", icon="🛒"); st.rerun()

# --- Interfaz de Cotización Final ---
with st.container(border=True):
    st.header("🛒 3. Cotización Final")
    if not st.session_state.cotizacion_items: st.info("El carrito está vacío.")
    else:
        st.markdown("**Puede editar Cantidad, Producto y Descuento. Use (🗑️) para eliminar filas.**")
        edited_df = st.data_editor(pd.DataFrame(st.session_state.cotizacion_items),
            column_config={
                "Producto": st.column_config.TextColumn(width="large"), "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
                "Descuento (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1, format="%d%%"),
                "Precio Unitario": st.column_config.NumberColumn(format="$%.2f"), "Total": st.column_config.NumberColumn(format="$%.2f"),
                "Inventario": None
            },
            disabled=["Referencia", "Precio Unitario", "Total"], hide_index=True, use_container_width=True, num_rows="dynamic")
        
        recalculated_items = []
        for row in edited_df.to_dict('records'):
            row['Total'] = (row['Cantidad'] * row['Precio Unitario']) * (1 - row['Descuento (%)'] / 100.0)
            recalculated_items.append(row)
        st.session_state.cotizacion_items = recalculated_items
        
        subtotal_bruto = sum(item['Cantidad'] * item['Precio Unitario'] for item in recalculated_items)
        descuento_total = sum((item['Cantidad'] * item['Precio Unitario']) * (item['Descuento (%)'] / 100.0) for item in recalculated_items)
        base_gravable = subtotal_bruto - descuento_total
        iva_valor = base_gravable * 0.19
        total_general = base_gravable + iva_valor
        
        st.text_area("Observaciones Adicionales (aparecerán en el PDF):", key="observaciones", height=100)
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
            if st.button("🗑️ Vaciar Cotización", use_container_width=True):
                st.session_state.cotizacion_items = []; st.session_state.observaciones = ""; st.rerun()
        with col2:
            if st.session_state.cliente_actual:
                df_cot_items_con_stock = pd.DataFrame(recalculated_items)
                pdf_data = generar_pdf_profesional(st.session_state.cliente_actual, df_cot_items_con_stock, subtotal_bruto, descuento_total, iva_valor, total_general, st.session_state.observaciones)
                st.download_button("📄 Descargar Cotización PDF", pdf_data, f"Cotizacion_{st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente')}_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True, type="primary")
            else: st.warning("Seleccione un cliente para descargar.")
