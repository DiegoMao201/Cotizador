# utils.py
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from fpdf import FPDF
from zoneinfo import ZoneInfo
import gspread
from urllib.parse import quote
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# --- CONSTANTES ---
BASE_DIR = Path.cwd()
LOGO_FILE_PATH = BASE_DIR / 'superior.png'
FOOTER_IMAGE_PATH = BASE_DIR / 'inferior.jpg'
FONT_FILE_PATH = BASE_DIR / 'DejaVuSans.ttf'
GOOGLE_SHEET_NAME = "Productos"

REFERENCIA_COL, NOMBRE_PRODUCTO_COL, COSTO_COL, STOCK_COL = 'Referencia', 'Descripción', 'Costo', 'Stock'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL, CLIENTE_EMAIL_COL = 'Nombre', 'NIF', 'Teléfono', 'Dirección', 'E-Mail'
ESTADOS_COTIZACION = ['Borrador', 'Enviada', 'Aprobada', 'Rechazada', 'Pedido para Logística']
TASA_IVA = 0.19

# --- CLASE PDF ---
class PDF(FPDF):
    def __init__(self, numero_propuesta, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.numero_propuesta_actual = numero_propuesta
        self.font_family = 'Helvetica'
        if FONT_FILE_PATH.exists():
            try:
                self.add_font('DejaVu', '', str(FONT_FILE_PATH), uni=True)
                self.add_font('DejaVu', 'B', str(FONT_FILE_PATH), uni=True)
                self.font_family = 'DejaVu'
            except Exception as e:
                print(f"Advertencia: No se pudo cargar la fuente DejaVu. {e}")

    def header(self):
        if LOGO_FILE_PATH.exists(): self.image(str(LOGO_FILE_PATH), 10, 8, 80)
        self.set_y(12)
        self.set_font(self.font_family, 'B', 20)
        self.set_text_color(10, 37, 64)
        self.cell(0, 10, 'PROPUESTA COMERCIAL', 0, 1, 'R')
        self.set_font(self.font_family, '', 10)
        self.set_text_color(0)
        self.cell(0, 5, f"Propuesta #: {self.numero_propuesta_actual}", 0, 1, 'R')
        self.ln(15)

    def footer(self):
        if FOOTER_IMAGE_PATH.exists(): self.image(str(FOOTER_IMAGE_PATH), 8, self.h - 45, 200)
        self.set_y(-15)
        self.set_font(self.font_family, '', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# --- GENERACIÓN DE PDF ---
def generar_pdf_profesional(state, workbook):
    pdf = PDF(numero_propuesta=state.numero_propuesta, orientation='P', unit='mm', format='Letter')
    pdf.add_page()
    PRIMARY_COLOR = (10, 37, 64)

    # SECCIÓN DE DATOS DE CLIENTE Y PROPUESTA
    cliente_data = state.cliente_actual
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(97.5, 7, 'CLIENTE', 1, 0, 'C', fill=True)
    pdf.cell(2.5, 7, '', 0, 0)
    pdf.cell(95, 7, 'DETALLES DE LA PROPUESTA', 1, 1, 'C', fill=True)
    y_before = pdf.get_y()
    pdf.set_font(pdf.font_family, '', 9)
    cliente_info = (f"Nombre: {cliente_data.get(CLIENTE_NOMBRE_COL, 'N/A')}\n"
                    f"NIF/C.C.: {cliente_data.get(CLIENTE_NIT_COL, 'N/A')}\n"
                    f"Dirección: {cliente_data.get(CLIENTE_DIR_COL, 'N/A')}\n"
                    f"Teléfono: {cliente_data.get(CLIENTE_TEL_COL, 'N/A')}")
    pdf.multi_cell(97.5, 5, cliente_info, 1, 'L')
    y_after_cliente = pdf.get_y()
    pdf.set_y(y_before)
    pdf.set_x(10 + 97.5 + 2.5)
    fecha_actual_colombia = datetime.now(ZoneInfo("America/Bogota"))
    propuesta_info = (f"Fecha de Emisión: {fecha_actual_colombia.strftime('%d/%m/%Y')}\n"
                      f"Validez de la Oferta: 15 días\n"
                      f"Asesor Comercial: {state.vendedor or 'No especificado'}")
    pdf.multi_cell(95, 5, propuesta_info, 1, 'L')
    pdf.set_y(max(y_after_cliente, pdf.get_y()) + 5)
    
    # TEXTO INTRODUCTORIO
    pdf.set_font(pdf.font_family, '', 10)
    intro_text = (f"Estimado(a) {cliente_data.get(CLIENTE_NOMBRE_COL, 'Cliente')},\n\nAgradecemos la oportunidad de presentarle esta propuesta comercial...")
    pdf.multi_cell(0, 5, intro_text, 0, 'L')
    pdf.ln(8)
    
    # TABLA DE ITEMS
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.set_text_color(255)
    col_widths = {'ref': 20, 'prod': 80, 'cant': 15, 'pu': 25, 'desc': 25, 'total': 25}
    headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, h in enumerate(headers): pdf.cell(list(col_widths.values())[i], 10, h, 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font(pdf.font_family, '', 9)
    pdf.set_text_color(0)
    
    for item in state.cotizacion_items:
        line_height = 6
        text_to_wrap = str(item.get('Producto', ''))
        lines = pdf.multi_cell(col_widths['prod'], line_height, text_to_wrap, border=0, split_only=True)
        row_height = len(lines) * line_height if lines else line_height
        
        y_before_row = pdf.get_y()
        # Dibuja la celda de referencia con la altura calculada
        pdf.cell(col_widths['ref'], row_height, str(item.get('Referencia', '')), 'LRB', 0, 'C')
        
        # Guarda la posición X para la celda de producto
        x_prod = pdf.get_x()
        
        # Dibuja las celdas restantes, moviendo el cursor al final de la fila
        pdf.set_xy(x_prod + col_widths['prod'], y_before_row)
        pdf.cell(col_widths['cant'], row_height, str(item.get('Cantidad', 0)), 'LRB', 0, 'C')
        pdf.cell(col_widths['pu'], row_height, f"${item.get('Precio Unitario', 0):,.2f}", 'LRB', 0, 'R')
        pdf.cell(col_widths['desc'], row_height, f"{item.get('Descuento (%)', 0):.1f}%", 'LRB', 0, 'C')
        pdf.set_font(pdf.font_family, 'B', 9)
        pdf.cell(col_widths['total'], row_height, f"${item.get('Total', 0):,.2f}", 'LRB', 1, 'R')
        pdf.set_font(pdf.font_family, '', 9)
        
        # Vuelve a la posición correcta y dibuja la celda de producto que puede tener múltiples líneas
        pdf.set_xy(x_prod, y_before_row)
        if item.get('Inventario', 0) <= 0:
            pdf.set_text_color(200, 0, 0)
            pdf.multi_cell(col_widths['prod'], line_height, text_to_wrap + " (Sin Stock)", border='B', align='L')
            pdf.set_text_color(0)
        else:
            pdf.multi_cell(col_widths['prod'], line_height, text_to_wrap, border='B', align='L')
        
        # Mueve el cursor al final de la fila dibujada
        pdf.set_y(y_before_row + row_height)

    # SECCIÓN DE TOTALES Y OBSERVACIONES
    pdf.ln(10)
    y_start_bottom = pdf.get_y()
    totals_start_x = 115
    pdf.set_x(totals_start_x)
    pdf.set_font(pdf.font_family, '', 10)
    label_width, value_width = 45, 40
    pdf.cell(label_width, 8, 'Subtotal Bruto:', 0, 0, 'R'); pdf.cell(value_width, 8, f"${state.subtotal_bruto:,.2f}", 0, 1, 'R')
    pdf.set_x(totals_start_x); pdf.cell(label_width, 8, 'Descuento Total:', 0, 0, 'R'); pdf.cell(value_width, 8, f"-${state.descuento_total:,.2f}", 0, 1, 'R')
    pdf.set_x(totals_start_x); pdf.cell(label_width, 8, 'Base Gravable:', 0, 0, 'R'); pdf.cell(value_width, 8, f"${state.base_gravable:,.2f}", 0, 1, 'R')
    pdf.set_x(totals_start_x); pdf.cell(label_width, 8, f'IVA ({TASA_IVA:.0%}):', 0, 0, 'R'); pdf.cell(value_width, 8, f"${state.iva_valor:,.2f}", 0, 1, 'R')
    pdf.set_x(totals_start_x); pdf.line(totals_start_x, pdf.get_y(), totals_start_x + label_width + value_width, pdf.get_y()); pdf.ln(1)
    pdf.set_x(totals_start_x); pdf.set_font(pdf.font_family, 'B', 12); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    pdf.cell(label_width, 10, 'TOTAL A PAGAR:', 1, 0, 'C', fill=True); pdf.cell(value_width, 10, f"${state.total_general:,.2f}", 1, 1, 'R', fill=True)
    pdf.set_text_color(0)
    y_after_totals = pdf.get_y()
    pdf.set_y(y_start_bottom)
    observaciones_finales = state.observaciones
    if any(item.get('Inventario', 0) <= 0 for item in state.cotizacion_items):
        observaciones_finales += "\n\nADVERTENCIA: Productos sin stock pueden tener un tiempo de entrega mayor."
    pdf.set_font(pdf.font_family, 'B', 10); pdf.cell(100, 8, 'Notas y Términos:', 0, 1, 'L'); pdf.set_font(pdf.font_family, '', 8)
    pdf.multi_cell(100, 5, observaciones_finales, border=1, align='L')
    pdf.set_y(max(pdf.get_y(), y_after_totals))
    
    return bytes(pdf.output())

# --- CONEXIÓN Y CARGA DE DATOS ---
@st.cache_resource
def connect_to_gsheets():
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        return gc.open(GOOGLE_SHEET_NAME)
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None

def _clean_numeric_column(series):
    def clean_value(value):
        s_val = str(value).strip()
        if ',' in s_val:
            return s_val.replace('.', '').replace(',', '.')
        return s_val
    cleaned_series = series.apply(clean_value)
    cleaned_series = cleaned_series.str.replace(r'[^\d.]', '', regex=True)
    return pd.to_numeric(cleaned_series, errors='coerce').fillna(0)

@st.cache_data(ttl=300)
def cargar_datos_maestros(_workbook):
    if not _workbook: return pd.DataFrame(), pd.DataFrame()
    try:
        prods_sheet = _workbook.worksheet("Productos")
        df_productos = pd.DataFrame(prods_sheet.get_all_records())
        df_productos.dropna(subset=[NOMBRE_PRODUCTO_COL, REFERENCIA_COL], how='all', inplace=True)
        df_productos[NOMBRE_PRODUCTO_COL] = df_productos[NOMBRE_PRODUCTO_COL].astype(str)
        df_productos[REFERENCIA_COL] = df_productos[REFERENCIA_COL].astype(str)
        df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL] + " (" + df_productos[REFERENCIA_COL].str.strip() + ")"
        for col in PRECIOS_COLS + [COSTO_COL]:
            if col in df_productos.columns:
                df_productos[col] = _clean_numeric_column(df_productos[col])
        if STOCK_COL in df_productos.columns:
            df_productos[STOCK_COL] = pd.to_numeric(df_productos[STOCK_COL], errors='coerce').fillna(0).astype(int)
        clientes_sheet = _workbook.worksheet("Clientes")
        df_clientes = pd.DataFrame(clientes_sheet.get_all_records())
        if not df_clientes.empty:
            df_clientes.dropna(subset=[CLIENTE_NOMBRE_COL], inplace=True)
            df_clientes[CLIENTE_NOMBRE_COL] = df_clientes[CLIENTE_NOMBRE_COL].astype(str)
        return df_productos, df_clientes
    except Exception as e:
        st.error(f"Error al cargar datos maestros: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- LÓGICA DE NEGOCIO EN GOOGLE SHEETS ---
def crear_nueva_propuesta_en_gsheets(workbook, state):
    try:
        cotizaciones_sheet = workbook.worksheet("Cotizaciones")
        items_sheet = workbook.worksheet("Cotizaciones_Items")
        fecha_actual = datetime.now(ZoneInfo("America/Bogota")).isoformat()
        margen_abs = state.base_gravable - state.costo_total
        margen_porc = (margen_abs / state.base_gravable) if state.base_gravable > 0 else 0
        header_row = [
            state.numero_propuesta, fecha_actual, state.vendedor,
            state.cliente_actual.get(CLIENTE_NOMBRE_COL, ''), state.cliente_actual.get(CLIENTE_NIT_COL, ''),
            state.status, float(state.subtotal_bruto), float(state.descuento_total), float(state.total_general),
            float(state.costo_total), float(margen_abs), float(margen_porc), state.observaciones
        ]
        items_rows = []
        for item in state.cotizacion_items:
            item_row = [
                state.numero_propuesta, item.get('Referencia', ''), item.get('Producto', ''),
                int(item.get('Cantidad', 0)), float(item.get('Precio Unitario', 0)), float(item.get('Costo', 0)),
                float(item.get('Valor Descuento', 0)), float(item.get('Total', 0)), int(item.get('Inventario', 0))
            ]
            items_rows.append(item_row)
        cotizaciones_sheet.append_row(header_row, value_input_option='USER_ENTERED')
        if items_rows:
            items_sheet.append_rows(items_rows, value_input_option='USER_ENTERED')
        st.success(f"✅ ¡Propuesta '{state.numero_propuesta}' guardada en la nube!")
    except Exception as e:
        st.error(f"❌ Ocurrió un error al crear la propuesta en Google Sheets: {e}")

def actualizar_propuesta_en_gsheets(workbook, state):
    try:
        cotizaciones_sheet = workbook.worksheet("Cotizaciones")
        items_sheet = workbook.worksheet("Cotizaciones_Items")
        
        cell = cotizaciones_sheet.find(state.numero_propuesta)
        if not cell:
            st.error(f"No se encontró la propuesta {state.numero_propuesta} para actualizar. Se creará como nueva.")
            crear_nueva_propuesta_en_gsheets(workbook, state)
            return

        margen_abs = state.base_gravable - state.costo_total
        margen_porc = (margen_abs / state.base_gravable) if state.base_gravable > 0 else 0
        
        updated_header_row = [
            state.numero_propuesta, datetime.now(ZoneInfo("America/Bogota")).isoformat(), state.vendedor,
            state.cliente_actual.get(CLIENTE_NOMBRE_COL, ''), state.cliente_actual.get(CLIENTE_NIT_COL, ''),
            state.status, float(state.subtotal_bruto), float(state.descuento_total), float(state.total_general),
            float(state.costo_total), float(margen_abs), float(margen_porc), state.observaciones
        ]
        cotizaciones_sheet.update(f'A{cell.row}:M{cell.row}', [updated_header_row])

        all_items = items_sheet.get_all_records()
        df_items = pd.DataFrame(all_items)
        rows_to_delete = df_items[df_items['numero_propuesta'] == state.numero_propuesta].index.tolist()
        for i in sorted(rows_to_delete, reverse=True):
            items_sheet.delete_rows(i + 2)

        new_items_rows = []
        for item in state.cotizacion_items:
            item_row = [
                state.numero_propuesta, item.get('Referencia', ''), item.get('Producto', ''),
                int(item.get('Cantidad', 0)), float(item.get('Precio Unitario', 0)), float(item.get('Costo', 0)),
                float(item.get('Valor Descuento', 0)), float(item.get('Total', 0)), int(item.get('Inventario', 0))
            ]
            new_items_rows.append(item_row)
        
        if new_items_rows:
            items_sheet.append_rows(new_items_rows, value_input_option='USER_ENTERED')

        st.success(f"✅ ¡Propuesta '{state.numero_propuesta}' actualizada correctamente!")
    except Exception as e:
        st.error(f"❌ Ocurrió un error al actualizar la propuesta: {e}")

def handle_save(workbook, state):
    if state.is_loaded_from_sheet:
        actualizar_propuesta_en_gsheets(workbook, state)
    else:
        crear_nueva_propuesta_en_gsheets(workbook, state)
        state.is_loaded_from_sheet = True
        state.persist_to_session()

@st.cache_data(ttl=60)
def listar_propuestas_df(_workbook):
    if not _workbook: return pd.DataFrame()
    try:
        sheet = _workbook.worksheet("Cotizaciones")
        records = sheet.get_all_records(head=1)
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        columnas_map = {
            'numero_propuesta': 'N° Propuesta', 'fecha_creacion': 'Fecha', 
            'cliente_nombre': 'Cliente', 'total_final': 'Total', 'status': 'Estado'
        }
        df = df.rename(columns={k: v for k, v in columnas_map.items() if k in df.columns})
        for col_name in columnas_map.values():
            if col_name not in df.columns: df[col_name] = 'N/A'
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
        return df[list(columnas_map.values())]
    except Exception as e:
        st.error(f"Error al listar propuestas: {e}"); return pd.DataFrame()

def get_full_proposal_data(numero_propuesta, _workbook):
    if not _workbook: return None
    try:
        cot_sheet = _workbook.worksheet("Cotizaciones")
        header_data = next((r for r in cot_sheet.get_all_records() if str(r.get('numero_propuesta')) == str(numero_propuesta)), None)
        if not header_data:
            st.error(f"No se encontró la propuesta '{numero_propuesta}'.")
            return None
        items_sheet = _workbook.worksheet("Cotizaciones_Items")
        all_items_raw = items_sheet.get_all_records()
        items_propuesta = []
        for item in all_items_raw:
            if str(item.get('numero_propuesta')) == str(numero_propuesta):
                qty = pd.to_numeric(item.get('Cantidad'), errors='coerce') or 0
                pu = pd.to_numeric(item.get('Precio_Unitario'), errors='coerce') or 0
                discount_val = pd.to_numeric(item.get('Descuento_Total_Item'), errors='coerce') or 0
                total_bruto_item = qty * pu
                discount_perc = (discount_val / total_bruto_item * 100) if total_bruto_item > 0 else 0
                formatted_item = {
                    'Referencia': item.get('Referencia'),
                    'Producto': item.get('Producto'),
                    'Cantidad': qty,
                    'Precio Unitario': pu,
                    'Costo': pd.to_numeric(item.get('Costo_Unitario'), errors='coerce') or 0,
                    'Descuento (%)': discount_perc,
                    'Total': pd.to_numeric(item.get('Total_Item'), errors='coerce') or 0,
                    'Inventario': pd.to_numeric(item.get('Inventario'), errors='coerce') or 0
                }
                items_propuesta.append(formatted_item)
        return {"header": header_data, "items": items_propuesta}
    except Exception as e:
        st.error(f"Error al obtener datos de la propuesta: {e}")
        return None

def enviar_email_seguro(destinatario, state, pdf_bytes, nombre_archivo, is_copy=False):
    try:
        creds = st.secrets["email_credentials"]
        smtp_user = creds["smtp_user"]
        
        asunto = f"Propuesta Comercial de Ferreinox SAS BIC - {state.numero_propuesta}"
        if is_copy:
            asunto = f"Copia de Propuesta Comercial - {state.numero_propuesta}"

        cuerpo = f"""
Estimado(a) {state.cliente_actual.get('Nombre', 'Cliente')},

Es un placer para nosotros presentarle la propuesta comercial que hemos preparado especialmente para usted.
Adjunto a este correo encontrará el documento PDF con todos los detalles de los productos y servicios solicitados.

En Ferreinox SAS BIC, nos comprometemos con la calidad y el excelente servicio. Si tiene alguna pregunta o desea realizar algún ajuste, no dude en contactarnos.

Le invitamos a conocer más sobre nosotros y nuestro amplio catálogo de productos visitando nuestra página web:
https://www.ferreinox.co

Agradecemos su interés y confianza.

Cordialmente,

{state.vendedor}
Ferreinox SAS BIC
"""
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'plain'))

        part = MIMEApplication(pdf_bytes, Name=nombre_archivo)
        part['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        msg.attach(part)

        with smtplib.SMTP_SSL(creds["smtp_server"], creds["smtp_port"]) as server:
            server.login(smtp_user, creds["smtp_password"])
            server.send_message(msg)
        
        return True, "Correo enviado exitosamente."
    except Exception as e:
        return False, f"Error al enviar el correo: {e}"
