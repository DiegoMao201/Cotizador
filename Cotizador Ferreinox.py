import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from fpdf import FPDF
import warnings

# Ignorar advertencias de openpyxl que a veces aparecen con Pandas y Excel
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador Profesional - Ferreinox SAS BIC", page_icon="🔩", layout="wide")

# --- ESTILOS Y DISEÑO ---
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
CLIENTE_NOMBRE_COL = 'Nombre'; CLIENTE_NIT_COL = 'NIF'; CLIENTE_TEL_COL = 'Teléfono'; CLIENTE_DIR_COL = 'Dirección'
CLIENTES_COLS_REQUERIDAS = [CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL]


# --- CLASE PDF PROFESIONAL (REDiseñada)---
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = "Ferreinox SAS BIC"
        self.company_nit = "NIT: 800.224.617-8"
        self.company_address = "Carrera 13 #19-26, Pereira, Risaralda"
        self.company_contact = "Tel: (606) 333 0101 | www.ferreinox.co"

    def header(self):
        if LOGO_FILE_PATH.exists(): self.image(str(LOGO_FILE_PATH), 10, 8, 50)
        self.set_y(12)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(10, 37, 64) # Azul oscuro Ferreinox
        self.cell(0, 10, 'PROPUESTA COMERCIAL', 0, 1, 'R')
        self.set_font('Helvetica', '', 10)
        self.cell(0, 5, f"Propuesta #: {st.session_state.get('numero_propuesta', 'N/A')}", 0, 1, 'R')
        self.ln(10)

    def footer(self):
        # Posición a 4.5 cm del final para dejar espacio a la imagen
        if FOOTER_IMAGE_PATH.exists(): self.image(str(FOOTER_IMAGE_PATH), 8, self.h - 45, 200)
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_profesional(cliente, items_df, subtotal, descuento_total, iva_valor, total_general, observaciones):
    pdf = PDF('P', 'mm', 'Letter')
    pdf.add_page()
    PRIMARY_COLOR = (10, 37, 64); LIGHT_GREY = (245, 245, 245)
    
    # --- SECCIÓN DE DATOS ---
    pdf.set_y(pdf.get_y() + 5)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(*LIGHT_GREY)
    pdf.cell(97.5, 7, 'CLIENTE', 1, 0, 'C', fill=True)
    pdf.cell(2.5, 7, '', 0, 0)
    pdf.cell(95, 7, 'DETALLES DE LA PROPUESTA', 1, 1, 'C', fill=True)
    
    y_before = pdf.get_y()
    
    pdf.set_font('Helvetica', '', 9)
    cliente_info = (f"Nombre: {cliente.get(CLIENTE_NOMBRE_COL, 'N/A')}\n"
                    f"NIF/C.C.: {cliente.get(CLIENTE_NIT_COL, 'N/A')}\n"
                    f"Dirección: {cliente.get(CLIENTE_DIR_COL, 'N/A')}\n"
                    f"Teléfono: {cliente.get(CLIENTE_TEL_COL, 'N/A')}")
    pdf.multi_cell(97.5, 5, cliente_info, 1, 'L')
    y_after_cliente = pdf.get_y()

    pdf.set_y(y_before)
    pdf.set_x(10 + 97.5 + 2.5)
    propuesta_info = (f"Fecha de Emisión: {datetime.now().strftime('%d/%m/%Y')}\n"
                      f"Validez de la Oferta: 15 días\n"
                      f"Asesor Comercial: {st.session_state.get('vendedor', 'No especificado')}")
    pdf.multi_cell(95, 5, propuesta_info, 1, 'L')
    y_after_propuesta = pdf.get_y()

    pdf.set_y(max(y_after_cliente, y_after_propuesta) + 5)
    
    pdf.set_font('Helvetica', '', 10)
    intro_text = (f"Estimado(a) {cliente.get(CLIENTE_NOMBRE_COL, 'Cliente')},\n\n"
                  "Agradecemos la oportunidad de presentarle esta propuesta. En Ferreinox SAS BIC, nos comprometemos a "
                  "ofrecer soluciones de la más alta calidad con el respaldo y la asesoría que su proyecto merece. "
                  "A continuación, detallamos los productos solicitados:")
    pdf.multi_cell(0, 5, intro_text, 0, 'L')
    pdf.ln(8)

    # --- TABLA DE ITEMS ---
    pdf.set_font('Helvetica', 'B', 10); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    col_widths = [20, 80, 15, 25, 25, 25]; headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, h in enumerate(headers): pdf.cell(col_widths[i], 10, h, 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font('Helvetica', '', 9)
    for _, row in items_df.iterrows():
        pdf.set_fill_color(*LIGHT_GREY if pdf.page_no() % 2 == 0 else (255,255,255))
        pdf.set_text_color(200, 0, 0) if row.get('Inventario', 0) <= 0 else pdf.set_text_color(0)
        
        y_before_row = pdf.get_y()
        # Usar multi_cell para las celdas de texto para un ajuste automático de altura
        pdf.multi_cell(col_widths[0], 6, str(row['Referencia']), border='LRB', align='C')
        y_after_ref = pdf.get_y()
        pdf.set_y(y_before_row)
        pdf.set_x(pdf.get_x() + col_widths[0])
        
        pdf.multi_cell(col_widths[1], 6, row['Producto'], border='LRB', align='L')
        y_after_prod = pdf.get_y()
        pdf.set_y(y_before_row)
        pdf.set_x(pdf.get_x() + col_widths[0] + col_widths[1])

        row_height = max(y_after_ref, y_after_prod) - y_before_row

        pdf.set_text_color(0) # Restablecer color para las cifras
        pdf.cell(col_widths[2], row_height, str(row['Cantidad']), 'LRB', 0, 'C')
        pdf.cell(col_widths[3], row_height, f"${row['Precio Unitario']:,.0f}", 'LRB', 0, 'R')
        pdf.cell(col_widths[4], row_height, f"{row['Descuento (%)']}%", 'LRB', 0, 'C')
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(col_widths[5], row_height, f"${row['Total']:,.0f}", 'LRB', 1, 'R')
        pdf.set_font('Helvetica', '', 9)
    
    pdf.set_text_color(0)
    
    # --- SECCIÓN DE TOTALES ---
    if pdf.get_y() > 180: pdf.add_page()
    
    y_totals = pdf.get_y()
    pdf.set_x(105)
    pdf.set_font('Helvetica', '', 10)
    
    pdf.cell(50, 8, 'Subtotal Bruto:', 'TLR', 0, 'R'); pdf.cell(50, 8, f"${subtotal:,.0f}", 'TR', 1, 'R')
    pdf.set_x(105); pdf.cell(50, 8, 'Descuento Total:', 'LR', 0, 'R'); pdf.cell(50, 8, f"-${descuento_total:,.0f}", 'R', 1, 'R')
    pdf.set_x(105); pdf.cell(50, 8, 'Base Gravable:', 'LR', 0, 'R'); pdf.cell(50, 8, f"${(subtotal - descuento_total):,.0f}", 'R', 1, 'R')
    pdf.set_x(105); pdf.cell(50, 8, 'IVA (19%):', 'LR', 0, 'R'); pdf.cell(50, 8, f"${iva_valor:,.0f}", 'R', 1, 'R')
    pdf.set_x(105); pdf.set_font('Helvetica', 'B', 14); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    pdf.cell(50, 12, 'TOTAL A PAGAR:', 'BLR', 0, 'R', fill=True); pdf.cell(50, 12, f"${total_general:,.0f}", 'BR', 1, 'R', fill=True)
    pdf.set_text_color(0)
    
    pdf.set_y(y_totals)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(90, 7, 'Notas y Terminos de la Propuesta:', 0, 1)
    pdf.set_font('Helvetica', '', 8)
    pdf.multi_cell(90, 5, observaciones, 'T', 'L')
    
    pdf.set_y(pdf.get_y() + 5)
    pdf.set_font('Helvetica', 'B', 10); pdf.cell(90, 7, 'Nuestro Compromiso de Valor:', 0, 1, 'L')
    pdf.set_font('Helvetica', '', 8)
    pdf.multi_cell(90, 5, u"• Asesoría experta para la selección del producto ideal.\n"
                           u"• Garantía directa en todos nuestros productos.\n"
                           u"• Amplio stock para entrega inmediata en referencias seleccionadas.", 0, 'L')
    
    return bytes(pdf.output())

# --- FUNCIONES DE CARGA Y GESTIÓN DE DATOS ---
@st.cache_data
def cargar_y_procesar_datos_completos():
    df_prods = pd.read_excel(PRODUCTOS_FILE_PATH, engine='openpyxl')
    df_prods[REFERENCIA_COL] = df_prods[REFERENCIA_COL].astype(str).str.strip()
    
    if INVENTARIO_FILE_PATH.exists():
        df_inv = pd.read_excel(INVENTARIO_FILE_PATH, engine='openpyxl')
        df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
        df_inv[REFERENCIA_COL] = df_inv[REFERENCIA_COL].astype(str).str.strip()
        inv_total = df_inv.groupby(REFERENCIA_COL)['Stock'].sum().reset_index()
        df_final = pd.merge(df_prods, inv_total, on=REFERENCIA_COL, how='left')
        df_final['Stock'].fillna(0, inplace=True)
    else:
        df_final = df_prods
        df_final['Stock'] = -1
    
    df_final['Busqueda'] = df_final[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_final[REFERENCIA_COL] + ")"
    df_final.dropna(subset=[NOMBRE_PRODUCTO_COL, REFERENCIA_COL], inplace=True)
    con_stock = df_final[df_final['Stock'] > 0].shape[0] if INVENTARIO_FILE_PATH.exists() else 0
    sin_stock = len(df_final) - con_stock if INVENTARIO_FILE_PATH.exists() else 0
    
    return df_final, con_stock, sin_stock

@st.cache_data
def cargar_clientes():
    if not CLIENTES_FILE_PATH.exists(): return pd.DataFrame(columns=CLIENTES_COLS_REQUERIDAS)
    return pd.read_excel(CLIENTES_FILE_PATH, engine='openpyxl')

def guardar_cliente_nuevo(nuevo_cliente_dict):
    try:
        df_existente = cargar_clientes()
        
        nuevo_cliente_df = pd.DataFrame([nuevo_cliente_dict])
        
        if nuevo_cliente_dict[CLIENTE_NIT_COL] not in df_existente[CLIENTE_NIT_COL].values:
             df_actualizado = pd.concat([df_existente, nuevo_cliente_df], ignore_index=True)
             df_actualizado.to_excel(CLIENTES_FILE_PATH, index=False)
             st.cache_data.clear()
             return True
        else:
             st.toast(f"El cliente con NIT {nuevo_cliente_dict[CLIENTE_NIT_COL]} ya existe.", icon="⚠️")
             return False
    except Exception as e:
        st.error(f"No se pudo guardar el cliente: {e}")
        return False

# --- INICIALIZACIÓN DE LA APLICACIÓN Y ESTADO DE SESIÓN ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
if 'numero_propuesta' not in st.session_state: st.session_state.numero_propuesta = f"PROP-{datetime.now().strftime('%Y%m%d-%H%M')}"
if 'observaciones' not in st.session_state: 
    st.session_state.observaciones = ("Forma de Pago: 50% Anticipo, 50% Contra-entrega.\n"
                                      "Tiempos de Entrega: 3-5 días hábiles para productos en stock.\n"
                                      "Garantía: Productos cubiertos por garantía de fábrica. No cubre mal uso.")

df_productos, con_stock, sin_stock = cargar_y_procesar_datos_completos()
df_clientes = cargar_clientes()

# --- INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Profesional Ferreinox SAS BIC")
with st.sidebar:
    if LOGO_FILE_PATH.exists(): st.image(str(LOGO_FILE_PATH))
    st.title("⚙️ Búsqueda y Config.")
    termino_busqueda = st.text_input("Buscar Producto:", placeholder="Nombre o referencia...")
    st.text_input("Vendedor/Asesor:", key="vendedor", placeholder="Tu nombre")
    with st.expander("Diagnóstico de Archivos", expanded=False):
        st.write(f"Logo (`{LOGO_FILE_NAME}`): {'✅' if LOGO_FILE_PATH.exists() else '❌'}")
        st.write(f"Pie de Página (`{FOOTER_IMAGE_NAME}`): {'✅' if FOOTER_IMAGE_PATH.exists() else '❌'}")
        st.write(f"Clientes (`{CLIENTES_FILE_NAME}`): {'✅' if CLIENTES_FILE_PATH.exists() else '❌ No encontrado'}")
        st.write(f"Precios (`{PRODUCTOS_FILE_NAME}`): {'✅' if PRODUCTOS_FILE_PATH.exists() else '❌'}")
        st.write(f"Inventario (`{INVENTARIO_FILE_NAME}`): {'✅' if INVENTARIO_FILE_PATH.exists() else '⚠️ No se usará'}")
        if INVENTARIO_FILE_PATH.exists(): st.info(f"Refs. con Stock: {con_stock} | Sin Stock: {sin_stock}")

df_filtrado = df_productos[df_productos['Busqueda'].str.contains(termino_busqueda, case=False, na=False)] if termino_busqueda else df_productos

# --- FLUJO DE COTIZACIÓN EN PANTALLA ---

with st.container(border=True):
    st.header("👤 1. Datos del Cliente")
    tab_existente, tab_nuevo = st.tabs(["Seleccionar Cliente Existente", "Registrar Cliente Nuevo"])
    
    with tab_existente:
        if df_clientes is not None and not df_clientes.empty:
            df_clientes_validos = df_clientes.dropna(subset=[CLIENTE_NOMBRE_COL])
            nombres_clientes = df_clientes_validos[CLIENTE_NOMBRE_COL].astype(str).unique().tolist()
            lista_clientes = [""] + sorted(nombres_clientes)
            
            cliente_sel_nombre = st.selectbox("Clientes guardados:", lista_clientes, index=0, key="cliente_selector")
            if cliente_sel_nombre: 
                st.session_state.cliente_actual = df_clientes_validos[df_clientes_validos[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0].to_dict()
                st.info(f"Cliente seleccionado: **{st.session_state.cliente_actual[CLIENTE_NOMBRE_COL]}**")
        else:
            st.info("No hay clientes guardados. Puede registrar uno en la pestaña 'Registrar Cliente Nuevo'.")

    with tab_nuevo:
        with st.form("form_new_client"):
            nombre = st.text_input(f"{CLIENTE_NOMBRE_COL}*"); nit = st.text_input(CLIENTE_NIT_COL)
            tel = st.text_input(CLIENTE_TEL_COL); direc = st.text_input(CLIENTE_DIR_COL)
            if st.form_submit_button("💾 Guardar y Usar Cliente"):
                if not nombre or not nit: st.warning("El Nombre y el NIF son obligatorios.")
                else:
                    nuevo_cliente = {CLIENTE_NOMBRE_COL: nombre, CLIENTE_NIT_COL: nit, CLIENTE_TEL_COL: tel, CLIENTE_DIR_COL: direc}
                    if guardar_cliente_nuevo(nuevo_cliente):
                        st.session_state.cliente_actual = nuevo_cliente
                        st.success(f"Cliente '{nombre}' guardado y seleccionado!")
                        st.rerun()

with st.container(border=True):
    st.header("📦 2. Agregar Productos")
    producto_sel_str = st.selectbox("Buscar y seleccionar:", options=df_filtrado['Busqueda'], index=None, placeholder="Escriba para buscar...")
    
    if termino_busqueda and df_filtrado.empty: st.info("No se encontraron productos con ese término de búsqueda.")

    if producto_sel_str:
        info_producto = df_filtrado[df_filtrado['Busqueda'] == producto_sel_str].iloc[0]
        st.subheader(f"Producto: {info_producto[NOMBRE_PRODUCTO_COL]}")
        stock_actual = info_producto.get('Stock', -1)
        if stock_actual == -1: st.info("No se está monitoreando el inventario para este producto.")
        elif stock_actual <= 0: st.warning(f"⚠️ ¡Atención! No hay inventario disponible para este producto.", icon="📦")
        # <<< CORRECCIÓN FINAL: Se reemplaza el caracter no soportado por un emoji estándar >>>
        else: st.success(f"✅ Hay **{int(stock_actual)}** unidades en stock.", icon="📦")

        col1, col2 = st.columns([2,1]); 
        with col1:
            opciones_precio = {f"{l} - ${info_producto.get(l, 0):,.0f}": (l, info_producto.get(l, 0)) for l in PRECIOS_COLS if pd.notna(info_producto.get(l))}
            precio_sel_str = st.radio("Listas de Precio:", options=opciones_precio.keys())
        with col2:
            cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1)
            if st.button("➕ Agregar a la Cotización", use_container_width=True, type="primary"):
                lista_aplicada, precio_unitario = opciones_precio[precio_sel_str]
                st.session_state.cotizacion_items.append({
                    "Referencia": info_producto[REFERENCIA_COL], "Producto": info_producto[NOMBRE_PRODUCTO_COL],
                    "Cantidad": cantidad, "Precio Unitario": precio_unitario, "Descuento (%)": 0, "Total": cantidad * precio_unitario,
                    "Inventario": stock_actual
                })
                st.toast(f"✅ Agregado!", icon="🛒"); st.rerun()

with st.container(border=True):
    st.header("🛒 3. Resumen y Generación de Propuesta")
    if not st.session_state.cotizacion_items: st.info("Añada productos para ver el resumen.")
    else:
        edited_df = st.data_editor(pd.DataFrame(st.session_state.cotizacion_items),
            column_config={
                "Producto": st.column_config.TextColumn("Producto", width="large"), "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
                "Descuento (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1, format="%d%%"),
                "Precio Unitario": st.column_config.NumberColumn(format="$%.0f"), "Total": st.column_config.NumberColumn(format="$%.0f"),
                "Inventario": None, "Referencia": st.column_config.TextColumn("Ref.")
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
        
        st.text_area("Observaciones y Términos (aparecerán en el PDF):", key="observaciones", height=120)
        st.divider()
        st.subheader("Resumen Financiero")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Subtotal Bruto", f"${subtotal_bruto:,.0f}")
        m2.metric("Descuento Total", f"-${descuento_total:,.0f}")
        m3.metric("IVA (19%)", f"${iva_valor:,.0f}")
        m4.metric("TOTAL GENERAL", f"${total_general:,.0f}")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Vaciar Propuesta", use_container_width=True):
                st.session_state.cotizacion_items = []
                st.session_state.observaciones = ("Forma de Pago: 50% Anticipo, 50% Contra-entrega.\n"
                                                  "Tiempos de Entrega: 3-5 días hábiles para productos en stock.\n"
                                                  "Garantía: Productos cubiertos por garantía de fábrica. No cubre mal uso.")
                st.session_state.numero_propuesta = f"PROP-{datetime.now().strftime('%Y%m%d-%H%M')}"
                st.rerun()
        with col2:
            if st.session_state.get('cliente_actual'):
                df_cot_items = pd.DataFrame(recalculated_items)
                pdf_data = generar_pdf_profesional(st.session_state.cliente_actual, df_cot_items, subtotal_bruto, descuento_total, iva_valor, total_general, st.session_state.observaciones)
                file_name = f"Propuesta_{st.session_state.numero_propuesta}_{st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente').replace(' ', '_')}.pdf"
                st.download_button("📄 Descargar Propuesta PDF", pdf_data, file_name, "application/pdf", use_container_width=True, type="primary")
            else: st.warning("Seleccione un cliente para poder generar la propuesta.")
