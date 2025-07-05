import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from fpdf import FPDF
import warnings
from zoneinfo import ZoneInfo
import gspread

# --- 0. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador Profesional - Ferreinox SAS BIC", page_icon="🔩", layout="wide")

# --- 1. ESTILOS Y DISEÑO ---
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
st.markdown("""
<style>
    .st-emotion-cache-1y4p8pa { padding-top: 2rem; }
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

# --- 2. CONFIGURACIÓN DE CONSTANTES ---
try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path.cwd()

LOGO_FILE_PATH = BASE_DIR / 'superior.png'
FOOTER_IMAGE_PATH = BASE_DIR / 'inferior.jpg'
FONT_FILE_PATH = BASE_DIR / 'DejaVuSans.ttf'
GOOGLE_SHEET_NAME = "Productos"
REFERENCIA_COL, NOMBRE_PRODUCTO_COL, COSTO_COL, STOCK_COL = 'Referencia', 'Descripción', 'Costo', 'Stock'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL = 'Nombre', 'NIF', 'Teléfono', 'Dirección'

# --- 3. CLASE PDF ---
class PDF(FPDF):
    # (El código de la clase PDF no cambia)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        st.error(f"Error Crítico de PDF: No se encontró la fuente '{FONT_FILE_PATH.name}'.")
        st.stop()
    pdf.add_page()
    PRIMARY_COLOR, LIGHT_GREY = (10, 37, 64), (245, 245, 245)
    vendedor_actual = st.session_state.get('vendedor_en_uso', 'No especificado')
    pdf.set_font(pdf.font_family, 'B', 10); pdf.set_fill_color(*LIGHT_GREY)
    pdf.cell(97.5, 7, 'CLIENTE', 1, 0, 'C', fill=True); pdf.cell(2.5, 7, '', 0, 0); pdf.cell(95, 7, 'DETALLES DE LA PROPUESTA', 1, 1, 'C', fill=True)
    y_before = pdf.get_y(); pdf.set_font(pdf.font_family, '', 9)
    cliente_info = (f"Nombre: {cliente.get(CLIENTE_NOMBRE_COL, 'N/A')}\n" f"NIF/C.C.: {cliente.get(CLIENTE_NIT_COL, 'N/A')}\n" f"Dirección: {cliente.get(CLIENTE_DIR_COL, 'N/A')}\n" f"Teléfono: {cliente.get(CLIENTE_TEL_COL, 'N/A')}")
    pdf.multi_cell(97.5, 5, cliente_info, 1, 'L'); y_after_cliente = pdf.get_y()
    pdf.set_y(y_before); pdf.set_x(10 + 97.5 + 2.5)
    fecha_actual_colombia = datetime.now(ZoneInfo("America/Bogota"))
    propuesta_info = (f"Fecha de Emisión: {fecha_actual_colombia.strftime('%d/%m/%Y')}\n" f"Validez de la Oferta: 15 días\n" f"Asesor Comercial: {vendedor_actual}")
    pdf.multi_cell(95, 5, propuesta_info, 1, 'L'); y_after_propuesta = pdf.get_y()
    pdf.set_y(max(y_after_cliente, y_after_propuesta) + 5)
    pdf.set_font(pdf.font_family, '', 10)
    intro_text = (f"Estimado(a) {cliente.get(CLIENTE_NOMBRE_COL, 'Cliente')},\n\nAgradecemos la oportunidad de presentarle esta propuesta comercial. A continuación, detallamos los productos solicitados:")
    pdf.multi_cell(0, 5, intro_text, 0, 'L'); pdf.ln(8)
    pdf.set_font(pdf.font_family, 'B', 10); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    col_widths = [20, 80, 15, 25, 25, 25]; headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, h in enumerate(headers): pdf.cell(col_widths[i], 10, h, 1, 0, 'C', fill=True)
    pdf.ln()
    pdf.set_font(pdf.font_family, '', 9)
    for _, row in items_df.iterrows():
        # ... (resto de la lógica de la tabla del PDF sin cambios)
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
    pdf.cell(90, 7, 'Notas y Términos:', 0, 1); pdf.set_font(pdf.font_family, '', 8)
    pdf.multi_cell(90, 5, observaciones, 'T', 'L');
    return bytes(pdf.output())

# --- 4. FUNCIONES DE DATOS ---
@st.cache_resource
def connect_to_gsheets():
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        return gc.open(GOOGLE_SHEET_NAME)
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None

@st.cache_data(ttl=300)
def cargar_datos_maestros():
    workbook = connect_to_gsheets()
    if not workbook: return pd.DataFrame(), pd.DataFrame()
    try:
        prods_sheet = workbook.worksheet("Productos")
        df_productos = pd.DataFrame(prods_sheet.get_all_records())
        df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos[REFERENCIA_COL].astype(str).str.strip() + ")"
        columnas_numericas = PRECIOS_COLS + [COSTO_COL, STOCK_COL]
        for col in columnas_numericas:
            if col in df_productos.columns:
                df_productos[col] = df_productos[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df_productos[col] = pd.to_numeric(df_productos[col], errors='coerce').fillna(0)
        df_productos.dropna(subset=[NOMBRE_PRODUCTO_COL, REFERENCIA_COL], inplace=True)
        clientes_sheet = workbook.worksheet("Clientes")
        df_clientes = pd.DataFrame(clientes_sheet.get_all_records())
        df_clientes[CLIENTE_NOMBRE_COL] = df_clientes[CLIENTE_NOMBRE_COL].astype(str)
        return df_productos, df_clientes
    except Exception as e:
        st.error(f"Error al cargar datos maestros: {e}")
        return pd.DataFrame(), pd.DataFrame()

def guardar_propuesta_en_gsheets(workbook, status):
    # (Función sin cambios)
    if not workbook: st.error("Sin conexión a Google Sheets."); return
    prop_num = st.session_state.numero_propuesta; items = st.session_state.cotizacion_items
    if not items: st.warning("No hay productos en la cotización para guardar."); return
    subtotal_bruto = sum(item['Cantidad'] * item['Precio Unitario'] for item in items)
    descuento_total = sum((item['Cantidad'] * item['Precio Unitario']) * (item['Descuento (%)'] / 100.0) for item in items)
    base_gravable = subtotal_bruto - descuento_total; iva_valor = base_gravable * 0.19; total_general = base_gravable + iva_valor
    costo_total_items = sum(item['Cantidad'] * item.get('Costo_Unitario', 0) for item in items)
    margen_abs = base_gravable - costo_total_items; margen_porc = (margen_abs / base_gravable) * 100 if base_gravable > 0 else 0
    vendedor_actual = st.session_state.get('vendedor_en_uso', '')
    header_data = [prop_num, datetime.now(ZoneInfo('America/Bogota')).isoformat(), vendedor_actual, st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, ''), str(st.session_state.cliente_actual.get(CLIENTE_NIT_COL, '')), status, subtotal_bruto, descuento_total, total_general, costo_total_items, margen_abs, margen_porc]
    items_data = [[prop_num, item['Referencia'], item['Producto'], item['Cantidad'], item['Precio Unitario'], item.get('Costo_Unitario', 0), item['Descuento (%)'], item['Total']] for item in items]
    try:
        with st.spinner("Guardando en la nube..."):
            cot_sheet = workbook.worksheet("Cotizaciones"); items_sheet = workbook.worksheet("Cotizaciones_Items")
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

@st.cache_data(ttl=60)
def listar_propuestas_guardadas():
    workbook = connect_to_gsheets()
    if not workbook: return []
    try:
        records = workbook.worksheet("Cotizaciones").get_all_records(numericise_ignore=['all'])
        propuestas = []
        for r in records:
            try:
                fecha_iso = r.get('fecha_iso', '')
                fecha_obj = datetime.fromisoformat(fecha_iso).astimezone(ZoneInfo("America/Bogota"))
                fecha_formateada = fecha_obj.strftime('%d/%m/%Y')
                total_str = str(r.get('total_general', '0')).replace('.', '').replace(',', '.')
                total_float = float(total_str)
                display = (f"#{r.get('numero_propuesta', 'S/N')} | {fecha_formateada} | " f"{r.get('cliente_nombre', 'N/A')} | ${total_float:,.0f} | {r.get('status', 'N/A')}")
                propuestas.append((display, r.get('numero_propuesta')))
            except (ValueError, TypeError):
                display = f"#{r.get('numero_propuesta', 'S/N')} - {r.get('cliente_nombre', 'N/A')}"
                propuestas.append((display, r.get('numero_propuesta')))
        return sorted(propuestas, key=lambda x: x[1], reverse=True)
    except Exception:
        return []

def cargar_propuesta_desde_gsheets(workbook, numero_propuesta):
    if not workbook: return
    try:
        with st.spinner(f"Cargando propuesta {numero_propuesta}..."):
            cot_sheet = workbook.worksheet("Cotizaciones")
            header_record = cot_sheet.find(numero_propuesta)
            if not header_record: st.error("No se encontró la propuesta."); return
            header_data = dict(zip(cot_sheet.row_values(1), cot_sheet.row_values(header_record.row)))
            items_sheet = workbook.worksheet("Cotizaciones_Items")
            all_items = items_sheet.get_all_records(numericise_ignore=['all'])
            items_propuesta = [item for item in all_items if str(item['numero_propuesta']) == str(numero_propuesta)]

        # ### CAMBIO: Solución definitiva al error de estado del vendedor ###
        # Se guarda el valor en una variable de sesión separada.
        st.session_state.vendedor_en_uso = header_data.get('vendedor', '')
        st.session_state.numero_propuesta = header_data['numero_propuesta']
        
        st.session_state.cliente_actual = {
            CLIENTE_NOMBRE_COL: header_data.get('cliente_nombre'),
            CLIENTE_NIT_COL: header_data.get('cliente_nit'),
            CLIENTE_DIR_COL: '', 'Teléfono': ''
        }
        recalculated_items = []
        for item_db in items_propuesta:
            cantidad = float(item_db.get('Cantidad', 0)); precio = float(item_db.get('Precio_Unitario', 0)); desc = float(item_db.get('Descuento_Porc', 0))
            total = (cantidad * precio) * (1 - desc / 100.0)
            recalculated_items.append({
                "Referencia": item_db['Referencia'], "Producto": item_db['Producto'],
                "Cantidad": int(cantidad), "Precio Unitario": precio,
                "Costo_Unitario": float(item_db.get('Costo_Unitario', 0)), "Descuento (%)": desc, "Total": total, "Inventario": -1
            })
        st.session_state.cotizacion_items = recalculated_items
        st.toast(f"✅ Propuesta '{numero_propuesta}' cargada.");
    except Exception as e: st.error(f"Error al cargar desde Google Sheets: {e}")

# --- 5. INICIALIZACIÓN DE SESIÓN ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
if 'numero_propuesta' not in st.session_state: st.session_state.numero_propuesta = f"PROP-{datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d-%H%M%S')}"
if 'observaciones' not in st.session_state: st.session_state.observaciones = ("Forma de Pago: 50% Anticipo, 50% Contra-entrega.\n" "Tiempos de Entrega: 3-5 días hábiles para productos en stock.\n" "Garantía: Productos cubiertos por garantía de fábrica. No cubre mal uso.")
if 'vendedor_en_uso' not in st.session_state: st.session_state.vendedor_en_uso = ""

# --- 6. CARGA INICIAL DE DATOS ---
workbook = connect_to_gsheets()
if workbook:
    df_productos, df_clientes = cargar_datos_maestros()
    propuestas_guardadas = listar_propuestas_guardadas()
else:
    st.warning("La aplicación no puede continuar sin conexión a la base de datos.")
    st.stop()

# --- 7. INTERFAZ DE USUARIO ---
st.title("Cotizador Profesional Ferreinox (Nube)")

with st.sidebar:
    if LOGO_FILE_PATH.exists():
        st.image(str(LOGO_FILE_PATH), use_container_width=True)
    else:
        st.title("Ferreinox")
    st.title("⚙️ Controles")
    # Este widget actualiza el estado del vendedor para NUEVAS propuestas.
    st.session_state.vendedor_en_uso = st.text_input("Vendedor/Asesor:", value=st.session_state.vendedor_en_uso, placeholder="Tu nombre")
    st.divider()
    with st.expander("Diagnóstico del Sistema"):
        st.write(f"Logo: {'✅' if LOGO_FILE_PATH.exists() else '❌'}")
        st.write(f"Fuente PDF: {'✅' if FONT_FILE_PATH.exists() else '⚠️'}")
        st.write(f"Conexión Google Sheets: {'✅' if workbook else '❌'}")

col_controles, col_cotizador = st.columns([1, 2])

with col_controles:
    with st.container(border=True):
        st.subheader("🎛️ Panel de Control")
        
        # ### CAMBIO: Filtro de cliente unificado en un solo selectbox con búsqueda ###
        lista_clientes = [""] + sorted(df_clientes[CLIENTE_NOMBRE_COL].unique().tolist())
        cliente_sel_nombre = st.selectbox(
            "👤 1. Cliente",
            options=lista_clientes,
            placeholder="Escribe para buscar o selecciona un cliente...",
            index=0 # No seleccionar ninguno por defecto
        )
        if cliente_sel_nombre:
            st.session_state.cliente_actual = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0].to_dict()
            st.success(f"Cliente seleccionado: **{st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, '')}**")

        with st.expander("➕ Registrar Cliente Nuevo"):
            # (Formulario sin cambios)
            with st.form("form_new_client"):
                nombre = st.text_input(f"{CLIENTE_NOMBRE_COL}*"); nit = st.text_input(CLIENTE_NIT_COL)
                tel = st.text_input(CLIENTE_TEL_COL); direc = st.text_input(CLIENTE_DIR_COL)
                if st.form_submit_button("💾 Guardar y Usar Cliente"):
                    if not nombre or not nit: st.warning("El Nombre y el NIF son obligatorios.")
                    else:
                        nuevo_cliente = {CLIENTE_NOMBRE_COL: nombre, CLIENTE_NIT_COL: nit, CLIENTE_TEL_COL: tel, CLIENTE_DIR_COL: direc}
                        if guardar_cliente_nuevo(workbook, nuevo_cliente):
                            st.session_state.cliente_actual = nuevo_cliente; st.success(f"Cliente '{nombre}' guardado y seleccionado!"); st.rerun()

        st.divider()
        st.subheader("📂 2. Cargar Propuesta")
        opciones_propuestas = {display: num for display, num in propuestas_guardadas}
        propuesta_a_cargar_display = st.selectbox("Buscar y seleccionar propuesta guardada:", [""] + list(opciones_propuestas.keys()))
        if st.button("Cargar Propuesta") and propuesta_a_cargar_display:
            numero_propuesta = opciones_propuestas[propuesta_a_cargar_display]
            cargar_propuesta_desde_gsheets(workbook, numero_propuesta)

with col_cotizador:
    # ### CAMBIO: Interfaz con pestañas para evitar saltos y mejorar la organización ###
    tab1, tab2 = st.tabs(["📝 Agregar Productos", "🛒 Resumen y Generación"])

    with tab1:
        st.subheader("Selecciona los productos para la cotización")
        producto_sel_str = st.selectbox("Buscar producto:", options=[""] + df_productos['Busqueda'].tolist(), index=0, placeholder="Escribe para buscar por nombre o referencia...")
        if producto_sel_str:
            info_producto = df_productos[df_productos['Busqueda'] == producto_sel_str].iloc[0]
            st.write(f"**Producto:** {info_producto[NOMBRE_PRODUCTO_COL]}")
            
            c1, c2 = st.columns(2)
            stock_actual = info_producto.get(STOCK_COL, 0)
            c1.metric("Stock Disponible", f"{int(stock_actual)} uds.", "✅" if stock_actual > 0 else "⚠️")
            with c2:
                cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1)
            
            # ### CAMBIO: Muestra el nombre completo de la lista de precios ###
            opciones_precio = {
                f"{l} - ${info_producto.get(l, 0):,.0f}": info_producto.get(l, 0) 
                for l in PRECIOS_COLS 
                if pd.notna(info_producto.get(l)) and info_producto.get(l) > 0
            }

            if opciones_precio:
                precio_sel_str = st.radio("Listas de Precio:", options=opciones_precio.keys())
                if st.button("➕ Agregar a la Cotización", use_container_width=True, type="primary"):
                    precio_unitario = pd.to_numeric(opciones_precio[precio_sel_str])
                    st.session_state.cotizacion_items.append({
                        "Referencia": info_producto[REFERENCIA_COL], "Producto": info_producto[NOMBRE_PRODUCTO_COL],
                        "Cantidad": cantidad, "Precio Unitario": precio_unitario, "Descuento (%)": 0, "Total": cantidad * precio_unitario,
                        "Inventario": stock_actual, "Costo_Unitario": info_producto.get(COSTO_COL, 0)
                    })
                    st.rerun() # Se necesita para refrescar la tabla de resumen
            else:
                st.warning("Este producto no tiene precios definidos.")

    with tab2:
        st.subheader("Revisa y genera la propuesta comercial")
        if not st.session_state.cotizacion_items:
            st.info("Añada productos en la pestaña anterior para ver el resumen.")
        else:
            edited_df = st.data_editor(
                pd.DataFrame(st.session_state.cotizacion_items),
                column_config={
                    "Producto": st.column_config.TextColumn("Producto", width="large"),
                    "Cantidad": st.column_config.NumberColumn(min_value=1),
                    "Descuento (%)": st.column_config.NumberColumn(min_value=0, max_value=100, format="%d%%"),
                    "Precio Unitario": st.column_config.NumberColumn(format="$%.0f"),
                    "Total": st.column_config.NumberColumn(format="$%.0f"),
                    "Inventario": None, "Referencia": st.column_config.TextColumn("Ref."), "Costo_Unitario": None
                },
                disabled=["Referencia", "Producto", "Precio Unitario", "Total", "Costo_Unitario", "Inventario"],
                hide_index=True, use_container_width=True, num_rows="dynamic"
            )

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
                    st.session_state.cotizacion_items = []
                    st.session_state.cliente_actual = {}
                    st.session_state.numero_propuesta = f"PROP-{datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d-%H%M%S')}"
                    st.rerun()
            with col_final2:
                if st.session_state.get('cliente_actual'):
                    df_cot_items = pd.DataFrame(st.session_state.cotizacion_items)
                    pdf_data = generar_pdf_profesional(st.session_state.cliente_actual, df_cot_items, subtotal_bruto, descuento_total, iva_valor, total_general, st.session_state.observaciones)
                    file_name = f"Propuesta_{st.session_state.numero_propuesta}_{st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente').replace(' ', '_')}.pdf"
                    st.download_button("📄 Descargar Propuesta PDF", data=pdf_data, file_name=file_name, mime="application/pdf", use_container_width=True)
                else:
                    st.warning("Seleccione un cliente para generar PDF.")
