# --- ARCHIVO: cotizador_streamlit.py ---

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador Optimizado - Ferreinox SAS BIC", page_icon="🔩", layout="wide")

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
BASE_DIR = Path(__file__).resolve().parent if '__file__' in globals() else Path.cwd()
PRODUCTOS_FILE_PATH = BASE_DIR / 'lista_precios.xlsx'
CLIENTES_FILE_PATH = BASE_DIR / 'Clientes.xlsx'
INVENTARIO_FILE_PATH = BASE_DIR / 'Rotacion.xlsx'
LOGO_FILE_PATH = BASE_DIR / 'superior.png'
FOOTER_IMAGE_PATH = BASE_DIR / 'inferior.jpg'

# Columnas
REFERENCIA_COL = 'Referencia'
NOMBRE_PRODUCTO_COL = 'Descripción'
INVENTARIO_COL = 'Stock'
CLIENTE_NOMBRE_COL = 'Nombre'
CLIENTE_NIT_COL = 'NIF'
CLIENTE_TEL_COL = 'Teléfono'
CLIENTE_DIR_COL = 'Dirección'
PRECIOS_COLS = [
    'Detallista 801 lista 2', 'Publico 800 Lista 1',
    'Publico 345 Lista 1 complementarios',
    'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados'
]

# --- CLASE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(10, 37, 64)
        self.rect(0, 0, 216, 30, 'F')
        if LOGO_FILE_PATH.exists():
            self.image(str(LOGO_FILE_PATH), 15, 8, 45)
        self.set_y(10)
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "Ferreinox SAS BIC", 0, 1, 'C')

    def footer(self):
        if FOOTER_IMAGE_PATH.exists():
            self.image(str(FOOTER_IMAGE_PATH), 8, 252, 200)
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    df = pd.read_excel(PRODUCTOS_FILE_PATH)
    df[REFERENCIA_COL] = df[REFERENCIA_COL].astype(str).str.strip()
    inv = pd.read_excel(INVENTARIO_FILE_PATH) if INVENTARIO_FILE_PATH.exists() else pd.DataFrame(columns=[REFERENCIA_COL, INVENTARIO_COL])
    inv[REFERENCIA_COL] = inv[REFERENCIA_COL].astype(str).str.strip()
    inv_total = inv.groupby(REFERENCIA_COL)[INVENTARIO_COL].sum().reset_index()
    df = pd.merge(df, inv_total, on=REFERENCIA_COL, how='left')
    df[INVENTARIO_COL] = df[INVENTARIO_COL].fillna(0)
    df['Busqueda'] = df[NOMBRE_PRODUCTO_COL].astype(str) + ' (' + df[REFERENCIA_COL].astype(str) + ')'
    return df

@st.cache_data
def cargar_clientes():
    return pd.read_excel(CLIENTES_FILE_PATH) if CLIENTES_FILE_PATH.exists() else pd.DataFrame(columns=[CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL])

# --- INICIALIZACIÓN ---
if 'items' not in st.session_state: st.session_state['items'] = []
if 'cliente' not in st.session_state: st.session_state['cliente'] = {}
if 'observaciones' not in st.session_state: st.session_state['observaciones'] = ""

productos = cargar_datos()
clientes = cargar_clientes()

# --- UI ---
st.title("🔩 Cotizador Ferreinox SAS BIC")

# --- CLIENTE ---
st.header("👤 Cliente")
tab1, tab2 = st.tabs(["Existente", "Nuevo"])
with tab1:
    cliente_nombres = [""] + clientes[CLIENTE_NOMBRE_COL].tolist()
    seleccionado = st.selectbox("Buscar Cliente", cliente_nombres)
    if seleccionado:
        st.session_state['cliente'] = clientes[clientes[CLIENTE_NOMBRE_COL] == seleccionado].iloc[0].to_dict()

with tab2:
    with st.form("nuevo_cliente"):
        nombre = st.text_input("Nombre*")
        nit = st.text_input("NIF")
        tel = st.text_input("Teléfono")
        direc = st.text_input("Dirección")
        if st.form_submit_button("Guardar Cliente"):
            if nombre:
                st.session_state['cliente'] = {CLIENTE_NOMBRE_COL: nombre, CLIENTE_NIT_COL: nit, CLIENTE_TEL_COL: tel, CLIENTE_DIR_COL: direc}
                st.success("Cliente cargado.")
            else:
                st.error("El nombre es obligatorio.")

# --- PRODUCTOS ---
st.header("📦 Agregar Productos")
busqueda = st.text_input("Buscar Producto")
filtrado = productos[productos['Busqueda'].str.contains(busqueda, case=False)] if busqueda else productos
seleccion = st.selectbox("Seleccionar Producto", filtrado['Busqueda'])
if seleccion:
    prod = filtrado[filtrado['Busqueda'] == seleccion].iloc[0]
    st.write(f"**{prod[NOMBRE_PRODUCTO_COL]}**")
    precio_dict = {f"{p} - ${prod[p]:,.2f}": (p, prod[p]) for p in PRECIOS_COLS}
    precio_str = st.radio("Precio", list(precio_dict.keys()))
    cant = st.number_input("Cantidad", 1, 1000, 1)
    if cant > prod[INVENTARIO_COL]:
        st.warning(f"Solo hay {prod[INVENTARIO_COL]} unidades disponibles")
    elif st.button("Agregar al carrito"):
        ref = prod[REFERENCIA_COL]
        ya_existe = False
        for item in st.session_state['items']:
            if item['Referencia'] == ref:
                item['Cantidad'] += cant
                item['Total'] = item['Cantidad'] * item['Precio']
                ya_existe = True
                break
        if not ya_existe:
            _, precio = precio_dict[precio_str]
            st.session_state['items'].append({
                'Referencia': ref, 'Producto': prod[NOMBRE_PRODUCTO_COL], 'Cantidad': cant,
                'Precio': precio, 'Descuento': 0, 'Inventario': prod[INVENTARIO_COL],
                'Total': cant * precio
            })
        st.rerun()

# --- COTIZACIÓN ---
st.header("🛒 Cotización Final")
if not st.session_state['items']:
    st.info("No hay productos en la cotización.")
else:
    df = pd.DataFrame(st.session_state['items'])
    for item in df.to_dict('records'):
        if item['Cantidad'] > item['Inventario']:
            st.warning(f"⚠️ {item['Producto']} sin suficiente inventario.")

    edited = st.data_editor(df, use_container_width=True,
        column_config={
            'Descuento': st.column_config.NumberColumn(min_value=0, max_value=100),
            'Precio': st.column_config.NumberColumn(format="$%.2f"),
            'Total': st.column_config.NumberColumn(format="$%.2f"),
            'Inventario': None
        }, disabled=["Referencia", "Precio", "Inventario", "Total"],
        num_rows="dynamic")

    for item in edited:
        item['Total'] = item['Cantidad'] * item['Precio'] * (1 - item['Descuento']/100)
    st.session_state['items'] = edited

    subtotal = sum(i['Cantidad'] * i['Precio'] for i in edited)
    descuento = sum((i['Cantidad'] * i['Precio']) * i['Descuento']/100 for i in edited)
    base = subtotal - descuento
    iva = base * 0.19
    total = base + iva

    st.text_area("Observaciones", key="observaciones")
    st.metric("Total a Pagar", f"${total:,.2f}")

    if st.button("📄 Generar PDF"):
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 10, f"Cliente: {st.session_state['cliente'].get(CLIENTE_NOMBRE_COL, 'N/A')}", ln=1)
        for item in edited:
            pdf.cell(0, 8, f"{item['Producto']} x{item['Cantidad']} - ${item['Total']:,.2f}", ln=1)
        pdf.ln(5); pdf.cell(0, 10, f"Total: ${total:,.2f}", ln=1)
        pdf.ln(5); pdf.multi_cell(0, 5, st.session_state['observaciones'])

        st.download_button("⬇️ Descargar PDF", pdf.output(dest='S').encode('latin-1'),
                           file_name=f"Cotizacion_{datetime.now().strftime('%Y%m%d')}.pdf",
                           mime="application/pdf")

    if st.button("🗑️ Vaciar cotización"):
        st.session_state['items'] = []
        st.session_state['observaciones'] = ""
        st.rerun()


