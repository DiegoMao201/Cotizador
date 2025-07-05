# utils.py
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from fpdf import FPDF
from zoneinfo import ZoneInfo
import gspread
from urllib.parse import quote

# --- CONSTANTES ---
BASE_DIR = Path.cwd()
LOGO_FILE_PATH = BASE_DIR / 'superior.png'
FOOTER_IMAGE_PATH = BASE_DIR / 'inferior.jpg'
FONT_FILE_PATH = BASE_DIR / 'DejaVuSans.ttf'
GOOGLE_SHEET_NAME = "Productos"

# Columnas y Estados
REFERENCIA_COL, NOMBRE_PRODUCTO_COL, COSTO_COL, STOCK_COL = 'Referencia', 'Descripción', 'Costo', 'Stock'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL, CLIENTE_EMAIL_COL = 'Nombre', 'NIF', 'Teléfono', 'Dirección', 'Email'
ESTADOS_COTIZACION = ['Borrador', 'Enviada', 'Aprobada', 'Rechazada', 'Pedido para Logística']

# Constante de Impuestos
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
    """
    Genera el PDF de la propuesta comercial a partir del objeto de estado.
    """
    pdf = PDF(numero_propuesta=state.numero_propuesta, orientation='P', unit='mm', format='Letter')

    if pdf.font_family != 'DejaVu' and FONT_FILE_PATH.exists():
        st.warning(f"No se pudo cargar la fuente personalizada. Se usará una fuente estándar.")
    
    # Asegurar que tenemos todos los datos del cliente
    cliente_data = state.cliente_actual
    if CLIENTE_NIT_COL not in cliente_data and cliente_data.get(CLIENTE_NOMBRE_COL):
        _, df_clientes = cargar_datos_maestros(workbook)
        cliente_df = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_data[CLIENTE_NOMBRE_COL]]
        if not cliente_df.empty:
            cliente_data = cliente_df.iloc[0].to_dict()

    pdf.add_page()
    PRIMARY_COLOR = (10, 37, 64)
    LIGHT_GREY = (245, 245, 245)

    # --- SECCIÓN DE DATOS DE CLIENTE Y PROPUESTA ---
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.set_fill_color(*LIGHT_GREY)
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
    y_after_propuesta = pdf.get_y()
    pdf.set_y(max(y_after_cliente, y_after_propuesta) + 5)
    
    # --- TEXTO INTRODUCTORIO ---
    pdf.set_font(pdf.font_family, '', 10)
    intro_text = (f"Estimado(a) {cliente_data.get(CLIENTE_NOMBRE_COL, 'Cliente')},\n\n"
                  "Agradecemos la oportunidad de presentarle esta propuesta comercial. A continuación, detallamos los productos solicitados:")
    pdf.multi_cell(0, 5, intro_text, 0, 'L')
    pdf.ln(8)

    # --- TABLA DE ITEMS ---
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.set_text_color(255)
    col_widths = [20, 80, 15, 25, 25, 25]
    headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, h in enumerate(headers): pdf.cell(col_widths[i], 10, h, 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font(pdf.font_family, '', 9)
    pdf.set_text_color(0)
    items_df = pd.DataFrame(state.cotizacion_items)

    for _, row in items_df.iterrows():
        # Lógica de cálculo de altura de fila para texto largo
        y_before_row = pdf.get_y()
        # Simular la altura de las dos celdas con MultiCell para obtener la máxima
        pdf.multi_cell(col_widths[0], 6, str(row['Referencia']), border=0, align='C', dry_run=True)
        h1 = pdf.get_y() - y_before_row
        pdf.set_y(y_before_row)
        pdf.multi_cell(col_widths[1], 6, str(row['Producto']), border=0, align='L', dry_run=True)
        h2 = pdf.get_y() - y_before_row
        row_height = max(h1, h2, 6) # Mínimo 6
        pdf.set_y(y_before_row)

        pdf.cell(col_widths[0], row_height, str(row['Referencia']), border='LRB', align='C')
        pdf.set_x(pdf.get_x() + col_widths[0])

        if row.get('Inventario', 0) <= 0:
            pdf.set_text_color(200, 0, 0)
            pdf.cell(col_widths[1], row_height, str(row['Producto']) + " (Sin Stock)", border='LRB', align='L')
            pdf.set_text_color(0)
        else:
            pdf.cell(col_widths[1], row_height, str(row['Producto']), border='LRB', align='L')
        
        pdf.set_x(pdf.get_x() + col_widths[1])
        
        pdf.cell(col_widths[2], row_height, str(row['Cantidad']), 'LRB', 0, 'C')
        pdf.cell(col_widths[3], row_height, f"${row['Precio Unitario']:,.0f}", 'LRB', 0, 'R')
        pdf.cell(col_widths[4], row_height, f"{row['Descuento (%)']}%", 'LRB', 0, 'C')
        pdf.set_font(pdf.font_family, 'B', 9)
        pdf.cell(col_widths[5], row_height, f"${row['Total']:,.0f}", 'LRB', 1, 'R')
        pdf.set_font(pdf.font_family, '', 9)
    
    pdf.set_text_color(0)
    pdf.ln(2)

    # --- SECCIÓN DE TOTALES Y OBSERVACIONES ---
    items_sin_stock = [item['Producto'] for item in state.cotizacion_items if item.get('Inventario', 0) <= 0]
    observaciones_finales = state.observaciones
    if items_sin_stock:
        adv = "\n\nADVERTENCIA: Productos sin stock pueden tener un tiempo de entrega mayor."
        if adv not in observaciones_finales:
             observaciones_finales += adv

    if pdf.get_y() > 190: pdf.add_page()
    
    y_start_bottom = pdf.get_y()
    
    # Bloque de Observaciones (izquierdo)
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.cell(90, 7, 'Notas y Términos:', 0, 1)
    pdf.set_font(pdf.font_family, '', 8)
    pdf.multi_cell(90, 5, observaciones_finales, 'T', 'L')
    y_after_obs = pdf.get_y()

    # Bloque de Totales (derecho)
    pdf.set_y(y_start_bottom)
    totals_start_x = 105
    pdf.set_x(totals_start_x)
    pdf.set_font(pdf.font_family, '', 10)
    pdf.cell(50, 8, 'Subtotal Bruto:', 'TLR', 0, 'R'); pdf.cell(50, 8, f"${state.subtotal_bruto:,.0f}", 'TR', 1, 'R')
    pdf.set_x(totals_start_x); pdf.cell(50, 8, 'Descuento Total:', 'LR', 0, 'R'); pdf.cell(50, 8, f"-${state.descuento_total:,.0f}", 'R', 1, 'R')
    pdf.set_x(totals_start_x); pdf.cell(50, 8, 'Base Gravable:', 'LR', 0, 'R'); pdf.cell(50, 8, f"${state.base_gravable:,.0f}", 'R', 1, 'R')
    pdf.set_x(totals_start_x); pdf.cell(50, 8, f'IVA ({TASA_IVA:.0%}):', 'LR', 0, 'R'); pdf.cell(50, 8, f"${state.iva_valor:,.0f}", 'R', 1, 'R')
    pdf.set_x(totals_start_x); pdf.set_font(pdf.font_family, 'B', 14); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    pdf.cell(50, 12, 'TOTAL A PAGAR:', 'BLR', 0, 'R', fill=True); pdf.cell(50, 12, f"${state.total_general:,.0f}", 'BR', 1, 'R', fill=True)
    pdf.set_text_color(0)
        
    return bytes(pdf.output())


# --- CONEXIÓN Y CARGA DE DATOS (Sin cambios significativos) ---
@st.cache_resource
def connect_to_gsheets():
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        return gc.open(GOOGLE_SHEET_NAME)
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None

def _clean_numeric_column(series):
    return pd.to_numeric(
        series.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
        errors='coerce'
    ).fillna(0)

@st.cache_data(ttl=300)
def cargar_datos_maestros(_workbook):
    if not _workbook:
        return pd.DataFrame(), pd.DataFrame()
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

def guardar_propuesta_en_gsheets(workbook, state):
    if not state.cliente_actual:
        st.error("❌ No se puede guardar. Por favor, seleccione un cliente.")
        return
    if not state.cotizacion_items:
        st.error("❌ No se puede guardar. La cotización no tiene productos.")
        return

    try:
        cotizaciones_sheet = workbook.worksheet("Cotizaciones")
        items_sheet = workbook.worksheet("Cotizaciones_Items")
        fecha_actual = datetime.now(ZoneInfo("America/Bogota")).strftime('%Y-%m-%d %H:%M:%S')

        header_row = [
            state.numero_propuesta, fecha_actual, state.vendedor,
            state.cliente_actual.get(CLIENTE_NOMBRE_COL, ''), state.cliente_actual.get(CLIENTE_NIT_COL, ''),
            state.status, state.subtotal_bruto, state.descuento_total,
            state.total_general, state.observaciones, state.cliente_actual.get(CLIENTE_EMAIL_COL, '')
        ]

        items_rows = []
        for item in state.cotizacion_items:
            item_row = [
                state.numero_propuesta, item.get('Referencia', ''), item.get('Producto', ''),
                item.get('Cantidad', 0), item.get('Precio Unitario', 0),
                item.get('Descuento (%)', 0), item.get('Total', 0) # Usa el total ya calculado
            ]
            items_rows.append(item_row)

        cotizaciones_sheet.append_row(header_row, value_input_option='USER_ENTERED')
        if items_rows:
            items_sheet.append_rows(items_rows, value_input_option='USER_ENTERED')
        st.success(f"✅ ¡Propuesta '{state.numero_propuesta}' guardada en la nube!")

    except gspread.exceptions.WorksheetNotFound:
        st.error("❌ Error: No se encontraron las hojas 'Cotizaciones' o 'Cotizaciones_Items'.")
    except Exception as e:
        st.error(f"❌ Ocurrió un error al guardar en Google Sheets: {e}")


@st.cache_data(ttl=60)
def listar_propuestas_df(_workbook):
    if not _workbook: return pd.DataFrame()
    try:
        sheet = _workbook.worksheet("Cotizaciones")
        records = sheet.get_all_records(head=1)
        if not records: return pd.DataFrame()
        
        df = pd.DataFrame(records)
        columnas_esperadas = ['numero_propuesta', 'fecha', 'cliente_nombre', 'total_general', 'status']
        for col in columnas_esperadas:
            if col not in df.columns:
                df[col] = 'N/A'
        
        df = df[columnas_esperadas]
        df = df.rename(columns={
            'numero_propuesta': 'N° Propuesta', 'fecha': 'Fecha', 
            'cliente_nombre': 'Cliente', 'total_general': 'Total', 'status': 'Estado'
        })

        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error al listar propuestas: {e}")
        return pd.DataFrame()

def get_full_proposal_data(numero_propuesta, _workbook):
    if not _workbook: return None
    try:
        cot_sheet = _workbook.worksheet("Cotizaciones")
        all_headers = cot_sheet.get_all_records()
        header_data = next((r for r in all_headers if str(r.get('numero_propuesta')) == str(numero_propuesta)), None)

        if not header_data:
            st.error(f"No se encontró la propuesta '{numero_propuesta}'.")
            return None

        items_sheet = _workbook.worksheet("Cotizaciones_Items")
        all_items = items_sheet.get_all_records()
        items_propuesta = [item for item in all_items if str(item.get('numero_propuesta')) == str(numero_propuesta)]

        return {"header": header_data, "items": items_propuesta}
    except Exception as e:
        st.error(f"Error al obtener datos de la propuesta: {e}")
        return None

# --- OTRAS UTILIDADES ---
def generar_mailto_link(destinatario, asunto, cuerpo):
    """Genera un enlace mailto seguro."""
    return f"mailto:{destinatario}?subject={quote(asunto)}&body={quote(cuerpo)}"
