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
REFERENCIA_COL, NOMBRE_PRODUCTO_COL, COSTO_COL, STOCK_COL = 'Referencia', 'Descripción', 'Costo', 'Stock'
PRECIOS_COLS = ['Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios', 'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados']
CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL, CLIENTE_EMAIL_COL = 'Nombre', 'NIF', 'Teléfono', 'Dirección', 'Email'
ESTADOS_COTIZACION = ['Borrador', 'Enviada', 'Aprobada', 'Rechazada', 'Pedido para Logística']

# --- CLASE PDF ---
# (La clase PDF se mantiene igual que en la respuesta anterior, omitida aquí por brevedad)
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
        self.cell(0, 5, f"Propuesta #: {self.numero_propuesta_actual}", 0, 1, 'R')
        self.ln(15)

    def footer(self):
        if FOOTER_IMAGE_PATH.exists(): self.image(str(FOOTER_IMAGE_PATH), 8, self.h - 45, 200)
        self.set_y(-15)
        self.set_font(self.font_family, '', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')


# --- GENERACIÓN DE PDF ---
# En utils.py

def generar_pdf_profesional(cliente, items_df, subtotal, descuento_total, iva_valor, total_general, observaciones_finales):
    """
    Genera el PDF de la propuesta comercial, incluyendo la sección de observaciones
    y la advertencia de inventario si es necesario.
    """
    pdf = PDF('P', 'mm', 'Letter')

    if pdf.font_family != 'DejaVu':
        st.error(f"Error Crítico de PDF: No se encontró la fuente '{FONT_FILE_NAME}'.")
        st.stop()

    pdf.add_page()
    PRIMARY_COLOR = (10, 37, 64)
    LIGHT_GREY = (245, 245, 245)

    # --- SECCIÓN DE DATOS DE CLIENTE Y PROPUESTA (Sin cambios) ---
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.set_fill_color(*LIGHT_GREY)
    pdf.cell(97.5, 7, 'CLIENTE', 1, 0, 'C', fill=True)
    pdf.cell(2.5, 7, '', 0, 0)
    pdf.cell(95, 7, 'DETALLES DE LA PROPUESTA', 1, 1, 'C', fill=True)
    
    y_before = pdf.get_y()
    pdf.set_font(pdf.font_family, '', 9)
    cliente_info = (f"Nombre: {cliente.get(CLIENTE_NOMBRE_COL, 'N/A')}\n"
                    f"NIF/C.C.: {cliente.get(CLIENTE_NIT_COL, 'N/A')}\n"
                    f"Dirección: {cliente.get(CLIENTE_DIR_COL, 'N/A')}\n"
                    f"Teléfono: {cliente.get(CLIENTE_TEL_COL, 'N/A')}")
    pdf.multi_cell(97.5, 5, cliente_info, 1, 'L')
    y_after_cliente = pdf.get_y()

    pdf.set_y(y_before)
    pdf.set_x(10 + 97.5 + 2.5)
    
    fecha_actual_colombia = datetime.now(ZoneInfo("America/Bogota"))
    propuesta_info = (f"Fecha de Emisión: {fecha_actual_colombia.strftime('%d/%m/%Y')}\n"
                      f"Validez de la Oferta: 15 días\n"
                      f"Asesor Comercial: {st.session_state.get('vendedor', 'No especificado')}")
    pdf.multi_cell(95, 5, propuesta_info, 1, 'L')
    y_after_propuesta = pdf.get_y()
    pdf.set_y(max(y_after_cliente, y_after_propuesta) + 5)
    
    # --- TEXTO INTRODUCTORIO (Sin cambios) ---
    pdf.set_font(pdf.font_family, '', 10)
    intro_text = (f"Estimado(a) {cliente.get(CLIENTE_NOMBRE_COL, 'Cliente')},\n\n"
                  "Agradecemos la oportunidad de presentarle esta propuesta comercial. A continuación, detallamos los productos solicitados:")
    pdf.multi_cell(0, 5, intro_text, 0, 'L')
    pdf.ln(8)

    # --- TABLA DE ITEMS (Con mejora para productos sin stock) ---
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.set_text_color(255)
    col_widths = [20, 80, 15, 25, 25, 25]
    headers = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, h in enumerate(headers): pdf.cell(col_widths[i], 10, h, 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font(pdf.font_family, '', 9)
    for _, row in items_df.iterrows():
        sin_stock = row.get('Inventario', 0) <= 0
        
        # ### CAMBIO: Se añade texto (Sin Stock) en rojo directamente en la descripción del producto ###
        producto_display = str(row['Producto'])
        
        y_before_row = pdf.get_y()
        pdf.multi_cell(col_widths[0], 6, str(row['Referencia']), border='LRB', align='C')
        y_after_ref = pdf.get_y()
        
        pdf.set_y(y_before_row)
        pdf.set_x(pdf.get_x() + col_widths[0])
        
        if sin_stock:
            pdf.set_text_color(200, 0, 0)
            pdf.multi_cell(col_widths[1], 6, producto_display + " (Sin Stock)", border='LRB', align='L')
            pdf.set_text_color(0) # Restablecer color para las otras celdas
        else:
            pdf.multi_cell(col_widths[1], 6, producto_display, border='LRB', align='L')
        
        y_after_prod = pdf.get_y()

        row_height = max(y_after_ref, y_after_prod) - y_before_row
        
        pdf.set_y(y_before_row)
        pdf.set_x(pdf.get_x() + col_widths[0] + col_widths[1])
        
        pdf.cell(col_widths[2], row_height, str(row['Cantidad']), 'LRB', 0, 'C')
        pdf.cell(col_widths[3], row_height, f"${row['Precio Unitario']:,.0f}", 'LRB', 0, 'R')
        pdf.cell(col_widths[4], row_height, f"{row['Descuento (%)']}%", 'LRB', 0, 'C')
        pdf.set_font(pdf.font_family, 'B', 9)
        pdf.cell(col_widths[5], row_height, f"${row['Total']:,.0f}", 'LRB', 1, 'R')
        pdf.set_font(pdf.font_family, '', 9)
    
    pdf.set_text_color(0)
    pdf.ln(2)

    # --- SECCIÓN DE TOTALES Y OBSERVACIONES RESTAURADA ---
    if pdf.get_y() > 190: # Ajuste de límite para asegurar que quepa
        pdf.add_page()
    
    y_start_bottom_section = pdf.get_y()

    # Bloque de Totales (lado derecho)
    totals_start_x = 105
    pdf.set_x(totals_start_x)
    pdf.set_font(pdf.font_family, '', 10)
    pdf.cell(50, 8, 'Subtotal Bruto:', 'TLR', 0, 'R'); pdf.cell(50, 8, f"${subtotal:,.0f}", 'TR', 1, 'R')
    pdf.set_x(totals_start_x); pdf.cell(50, 8, 'Descuento Total:', 'LR', 0, 'R'); pdf.cell(50, 8, f"-${descuento_total:,.0f}", 'R', 1, 'R')
    pdf.set_x(totals_start_x); pdf.cell(50, 8, 'Base Gravable:', 'LR', 0, 'R'); pdf.cell(50, 8, f"${(subtotal - descuento_total):,.0f}", 'R', 1, 'R')
    pdf.set_x(totals_start_x); pdf.cell(50, 8, 'IVA (19%):', 'LR', 0, 'R'); pdf.cell(50, 8, f"${iva_valor:,.0f}", 'R', 1, 'R')
    pdf.set_x(totals_start_x); pdf.set_font(pdf.font_family, 'B', 14); pdf.set_fill_color(*PRIMARY_COLOR); pdf.set_text_color(255)
    pdf.cell(50, 12, 'TOTAL A PAGAR:', 'BLR', 0, 'R', fill=True); pdf.cell(50, 12, f"${total_general:,.0f}", 'BR', 1, 'R', fill=True)
    pdf.set_text_color(0)

    # ### CAMBIO: Bloque de Observaciones (lado izquierdo) ###
    # Se posiciona al inicio de la sección, a la izquierda del bloque de totales.
    pdf.set_y(y_start_bottom_section)
    pdf.set_font(pdf.font_family, 'B', 10)
    pdf.cell(90, 7, 'Notas y Términos:', 0, 1) # Título de la sección
    pdf.set_font(pdf.font_family, '', 8)
    # El MultiCell ahora usa el texto `observaciones_finales` que ya incluye la advertencia de stock
    pdf.multi_cell(90, 5, observaciones_finales, 'T', 'L') 
    
    return bytes(pdf.output())


# --- CONEXIÓN Y CARGA DE DATOS MAESTROS ---
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
    """
    Carga los datos maestros de productos y clientes desde Google Sheets,
    manejando de forma robusta los valores vacíos para evitar TypeErrors.
    """
    if not _workbook:
        return pd.DataFrame(), pd.DataFrame()

    try:
        # --- Carga de Productos ---
        prods_sheet = _workbook.worksheet("Productos")
        df_productos = pd.DataFrame(prods_sheet.get_all_records())

        # 1. Eliminar filas donde las columnas clave son completamente vacías ANTES de procesar
        df_productos.dropna(subset=[NOMBRE_PRODUCTO_COL, REFERENCIA_COL], how='all', inplace=True)

        # 2. Convertir a string de forma segura para evitar errores en las operaciones de texto
        df_productos[NOMBRE_PRODUCTO_COL] = df_productos[NOMBRE_PRODUCTO_COL].astype(str)
        df_productos[REFERENCIA_COL] = df_productos[REFERENCIA_COL].astype(str)
        
        # 3. Crear la columna de búsqueda
        df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL] + " (" + df_productos[REFERENCIA_COL].str.strip() + ")"

        # 4. Limpiar columnas numéricas de forma segura
        for col in PRECIOS_COLS + [COSTO_COL]:
            if col in df_productos.columns:
                df_productos[col] = _clean_numeric_column(df_productos[col])
        
        if STOCK_COL in df_productos.columns:
            df_productos[STOCK_COL] = pd.to_numeric(df_productos[STOCK_COL], errors='coerce').fillna(0).astype(int)

        # --- Carga de Clientes ---
        clientes_sheet = _workbook.worksheet("Clientes")
        df_clientes = pd.DataFrame(clientes_sheet.get_all_records())

        if not df_clientes.empty:
            # Eliminar filas donde el nombre del cliente está vacío
            df_clientes.dropna(subset=[CLIENTE_NOMBRE_COL], inplace=True)
            df_clientes[CLIENTE_NOMBRE_COL] = df_clientes[CLIENTE_NOMBRE_COL].astype(str)

        return df_productos, df_clientes
        
    except Exception as e:
        st.error(f"Error al cargar datos maestros: {e}")
        return pd.DataFrame(), pd.DataFrame()


# --- LÓGICA DE NEGOCIO EN GOOGLE SHEETS ---

def guardar_propuesta_en_gsheets(workbook, state):
    """
    Guarda la cotización actual (header e items) en las hojas correspondientes
    de Google Sheets.
    """
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

        # Preparar fila de cabecera
        header_row = [
            state.numero_propuesta,
            fecha_actual,
            state.vendedor,
            state.cliente_actual.get(CLIENTE_NOMBRE_COL, ''),
            state.cliente_actual.get(CLIENTE_NIT_COL, ''),
            state.status,
            state.subtotal_bruto,
            state.descuento_total,
            state.total_general,
            state.observaciones,
            state.cliente_actual.get(CLIENTE_EMAIL_COL, '')
        ]

        # Preparar filas de items
        items_rows = []
        for item in state.cotizacion_items:
            # Re-calculamos el total por si acaso
            total_item = (item.get('Cantidad', 0) * item.get('Precio Unitario', 0)) * (1 - item.get('Descuento (%)', 0) / 100)
            item_row = [
                state.numero_propuesta,
                item.get('Referencia', ''),
                item.get('Producto', ''),
                item.get('Cantidad', 0),
                item.get('Precio Unitario', 0),
                item.get('Descuento (%)', 0),
                total_item
            ]
            items_rows.append(item_row)

        # Guardar datos
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
    """Lista un resumen de todas las propuestas guardadas."""
    if not _workbook: return pd.DataFrame()
    try:
        sheet = _workbook.worksheet("Cotizaciones")
        records = sheet.get_all_records()
        if not records: return pd.DataFrame()
        
        df = pd.DataFrame(records)
        # Asegurarse que las columnas esperadas existan
        columnas_requeridas = {
            'numero_propuesta': 'N° Propuesta', 'fecha': 'Fecha', 'cliente_nombre': 'Cliente',
            'total_general': 'Total', 'status': 'Estado'
        }
        df = df.rename(columns=columnas_requeridas)
        for col in columnas_requeridas.values():
            if col not in df.columns:
                df[col] = 'N/A' # Añadir columna vacía si no existe

        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
        return df[['N° Propuesta', 'Fecha', 'Cliente', 'Total', 'Estado']]
    except Exception as e:
        st.error(f"Error al listar propuestas: {e}")
        return pd.DataFrame()

def get_full_proposal_data(numero_propuesta, _workbook):
    """Obtiene todos los datos (header e items) de una propuesta específica."""
    if not _workbook: return None
    try:
        cot_sheet = _workbook.worksheet("Cotizaciones")
        all_headers = cot_sheet.get_all_records()
        header_data = next((r for r in all_headers if str(r.get('numero_propuesta')) == str(numero_propuesta)), None)

        if not header_data:
            st.error("No se encontró la cabecera de la propuesta.")
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
