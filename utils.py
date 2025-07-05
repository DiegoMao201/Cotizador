# utils.py
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from fpdf import FPDF
from zoneinfo import ZoneInfo
import gspread

# --- CONFIGURACIÓN DE CONSTANTES ---
BASE_DIR = Path.cwd()
LOGO_FILE_PATH = BASE_DIR / 'superior.png'
FOOTER_IMAGE_PATH = BASE_DIR / 'inferior.jpg'
FONT_FILE_PATH = BASE_DIR / 'DejaVuSans.ttf'
GOOGLE_SHEET_NAME = "Productos"
REFERENCIA_COL, NOMBRE_PRODUCTO_COL, COSTO_COL, STOCK_COL = 'Referencia', 'Descripción', 'Costo', 'Stock'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL = 'Nombre', 'NIF', 'Teléfono', 'Dirección'
ESTADOS_COTIZACION = ['Borrador', 'Enviada', 'Aprobada', 'Rechazada', 'Pedido para Logística']

# --- CLASE PDF (sin cambios) ---
class PDF(FPDF):
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

# --- FUNCIONES DE DATOS ---
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

@st.cache_data(ttl=60)
def listar_propuestas_df():
    workbook = connect_to_gsheets()
    if not workbook: return pd.DataFrame()
    try:
        all_values = workbook.worksheet("Cotizaciones").get_all_values()
        if len(all_values) < 2: return pd.DataFrame()

        headers = all_values[0]
        records = all_values[1:]
        df = pd.DataFrame(records, columns=headers)

        # ### CAMBIO: Solución al error 'fecha_iso' ###
        # Renombrar columnas clave por su posición para evitar KeyErrors
        # Asume que las columnas están en el orden en que se guardan
        rename_map = {
            df.columns[0]: 'N° Propuesta',
            df.columns[1]: 'Fecha',
            df.columns[3]: 'Cliente',
            df.columns[5]: 'Estado',
            df.columns[8]: 'Total'
        }
        df.rename(columns=rename_map, inplace=True)

        # Limpieza de datos
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Total'] = pd.to_numeric(df['Total'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
        
        return df[['N° Propuesta', 'Fecha', 'Cliente', 'Total', 'Estado']]
    except Exception as e:
        st.error(f"Error al listar propuestas: {e}")
        return pd.DataFrame()

def guardar_propuesta_en_gsheets(workbook, status, observaciones):
    if not workbook: st.error("Sin conexión a Google Sheets."); return
    prop_num = st.session_state.numero_propuesta; items = st.session_state.cotizacion_items
    if not items: st.warning("No hay productos en la cotización para guardar."); return
    subtotal_bruto = sum(item['Cantidad'] * item['Precio Unitario'] for item in items)
    descuento_total = sum((item['Cantidad'] * item['Precio Unitario']) * (item['Descuento (%)'] / 100.0) for item in items)
    base_gravable = subtotal_bruto - descuento_total; iva_valor = base_gravable * 0.19; total_general = base_gravable + iva_valor
    costo_total_items = sum(item['Cantidad'] * item.get('Costo_Unitario', 0) for item in items)
    margen_abs = base_gravable - costo_total_items; margen_porc = (margen_abs / base_gravable) * 100 if base_gravable > 0 else 0
    vendedor_actual = st.session_state.get('vendedor_en_uso', '')
    
    # Se añade 'observaciones' a los datos guardados
    header_data = [prop_num, datetime.now(ZoneInfo("America/Bogota")).isoformat(), vendedor_actual, st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, ''), str(st.session_state.cliente_actual.get(CLIENTE_NIT_COL, '')), status, subtotal_bruto, descuento_total, total_general, costo_total_items, margen_abs, margen_porc, observaciones]
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

def cargar_propuesta_a_sesion(numero_propuesta):
    workbook = connect_to_gsheets()
    if not workbook:
        st.error("No hay conexión para cargar la propuesta.")
        return
    try:
        cot_sheet = workbook.worksheet("Cotizaciones")
        header_record = cot_sheet.find(numero_propuesta)
        if not header_record: st.error("No se encontró la propuesta."); return
        header_data_list = cot_sheet.row_values(header_record.row)
        header_keys = cot_sheet.row_values(1)
        header_data = dict(zip(header_keys, header_data_list))

        items_sheet = workbook.worksheet("Cotizaciones_Items")
        all_items = items_sheet.get_all_records(numericise_ignore=['all'])
        items_propuesta = [item for item in all_items if str(item['numero_propuesta']) == str(numero_propuesta)]
        
        st.session_state.vendedor_en_uso = header_data.get('vendedor', '')
        st.session_state.numero_propuesta = header_data['numero_propuesta']
        st.session_state.observaciones = header_data.get('observaciones', st.session_state.get('observaciones', ''))

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
        st.toast(f"✅ Propuesta '{numero_propuesta}' cargada en el cotizador.");
    except Exception as e:
        st.error(f"Error al procesar la carga de la propuesta: {e}")
