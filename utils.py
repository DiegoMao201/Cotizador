# utils.py
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from datetime import datetime
from io import BytesIO
import re
import urllib.parse
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- INICIO DEL CAMBIO ---
# Se añade una función centralizada y robusta para convertir strings a precios (números flotantes).
# Esta función es capaz de interpretar correctamente números con comas como decimales (ej: "19.766,38")
# y también formatos americanos (ej: "19,766.38").
def parse_price(value):
    """
    Convierte un valor (generalmente un string) a un float, manejando
    diferentes formatos de separadores de miles y decimales.
    - Elimina símbolos de moneda y espacios.
    - Interpreta correctamente '1.234,56' y '1,234.56'.
    - Devuelve 0.0 si el valor es inválido o vacío.
    """
    if value is None or pd.isna(value):
        return 0.0
    
    # Convierte a string, elimina espacios, símbolos de moneda y porcentaje.
    s = str(value).strip().replace('$', '').replace('%', '')
    if not s:
        return 0.0

    # Detecta el formato basado en el último separador encontrado.
    last_comma = s.rfind(',')
    last_dot = s.rfind('.')

    # Si la coma aparece después del último punto, asumimos que la coma es el decimal.
    # Formato: 1.234,56
    if last_comma > last_dot:
        # Quitamos los puntos (miles) y reemplazamos la coma (decimal) por un punto.
        s = s.replace('.', '').replace(',', '.')
    # Si el punto aparece después de la última coma (o si no hay comas).
    # Formato: 1,234.56 o 1234.56
    else:
        # Quitamos las comas (miles). El punto decimal ya está en su lugar.
        s = s.replace(',', '')
    
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0
# --- FIN DEL CAMBIO ---


# --- CONSTANTES ---
LOGO_FILE_PATH = Path("superior.png")
TASA_IVA = 0.19
COLOR_AZUL = (0, 51, 102)

# --- Nombres de las hojas de Google Sheets ---
PROPUESTAS_SHEET_NAME = "Cotizaciones"
DETALLE_PROPUESTAS_SHEET_NAME = "Cotizaciones_Items"
PRODUCTOS_SHEET_NAME = "Productos"
CLIENTES_SHEET_NAME = "Clientes"

# --- Nombres de las columnas ---
CLIENTE_NOMBRE_COL = "Nombre"
CLIENTE_EMAIL_COL = "E-Mail"
NOMBRE_PRODUCTO_COL = "Descripción"
PRECIOS_COLS = [
    "Detallista 801 lista 2", "Publico 800 Lista 1",
    "Publico 345 Lista 1 complementarios", "Lista 346 Lista Complementarios",
    "Lista 100123 Construaliados"
]
PROPUESTA_CLIENTE_COL = "cliente_nombre"
ESTADOS_COTIZACION = ["Borrador", "Enviada", "Aceptada", "Rechazada"]

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def connect_to_gsheets():
    """Establece la conexión con Google Sheets y Google Drive."""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ],
        )
        client = gspread.authorize(creds)
        workbook = client.open_by_key(st.secrets["gsheets"]["spreadsheet_key"])
        workbook.creds = creds
        return workbook
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets o Drive: {e}")
        return None

# --- CARGA DE DATOS (CON OPTIMIZACIÓN PARA BÚSQUEDA) ---
@st.cache_data(ttl=600)
def cargar_datos_maestros(_workbook):
    """Carga los dataframes de productos y clientes y crea un índice de búsqueda."""
    if not _workbook:
        return pd.DataFrame(), pd.DataFrame()
    try:
        productos_sheet = _workbook.worksheet(PRODUCTOS_SHEET_NAME)
        df_productos = pd.DataFrame(productos_sheet.get_all_records())

        # --- OPTIMIZACIÓN CLAVE: Crear un índice de búsqueda ---
        df_productos['search_index'] = (
            df_productos[NOMBRE_PRODUCTO_COL].astype(str) + ' ' +
            df_productos['Referencia'].astype(str) + ' ' +
            df_productos.get('Categoria', pd.Series(index=df_productos.index, dtype=str)).fillna('')
        ).str.lower()
        
        clientes_sheet = _workbook.worksheet(CLIENTES_SHEET_NAME)
        df_clientes = pd.DataFrame(clientes_sheet.get_all_records())
        return df_productos, df_clientes
    except Exception as e:
        st.error(f"Ocurrió un error al cargar los datos maestros: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- NUEVO MOTOR DE BÚSQUEDA INTELIGENTE ---
def buscar_productos_inteligentemente(query, df_productos, categoria="Todas"):
    """
    Busca productos basado en un sistema de puntuación de múltiples palabras clave.
    """
    if not query and categoria == "Todas":
        return pd.DataFrame()

    resultados = df_productos.copy()
    if categoria != "Todas":
        resultados = resultados[resultados['Categoria'] == categoria]

    if not query:
        return resultados

    query_words = set(query.lower().split())

    def calcular_score(row):
        score = 0
        search_text = row['search_index']
        for word in query_words:
            if word in search_text:
                score += 1
        return score

    resultados['score'] = resultados.apply(calcular_score, axis=1)
    resultados_filtrados = resultados[resultados['score'] > 0]
    resultados_ordenados = resultados_filtrados.sort_values(by='score', ascending=False)
    return resultados_ordenados

def get_tiendas_from_df(df_productos):
    if df_productos.empty:
        return []
    stock_cols = [col for col in df_productos.columns if col.lower().startswith('stock ')]
    tiendas = [col.split(' ', 1)[1] for col in stock_cols]
    return sorted(tiendas)

@st.cache_data(ttl=60)
def listar_propuestas_df(_workbook):
    if not _workbook:
        return pd.DataFrame()
    try:
        sheet = _workbook.worksheet(PROPUESTAS_SHEET_NAME)
        return pd.DataFrame(sheet.get_all_records())
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def listar_detalle_propuestas_df(_workbook):
    if not _workbook:
        return pd.DataFrame()
    try:
        sheet = _workbook.worksheet(DETALLE_PROPUESTAS_SHEET_NAME)
        return pd.DataFrame(sheet.get_all_records())
    except Exception:
        return pd.DataFrame()

def handle_save(workbook, state):
    if not state.cliente_actual:
        st.warning("Por favor, seleccione un cliente antes de guardar.")
        return
    if not state.tienda_despacho:
        st.warning("Por favor, seleccione una Tienda de Despacho antes de guardar.")
        return
    if not state.cotizacion_items:
        st.warning("No hay productos en la cotización para guardar.")
        return
    with st.spinner("Guardando propuesta..."):
        if state.numero_propuesta and "TEMP" not in state.numero_propuesta:
            exito, mensaje = actualizar_propuesta_en_sheets(workbook, state)
        else:
            exito, mensaje = guardar_nueva_propuesta_en_sheets(workbook, state)
        if exito:
            st.success(mensaje)
            st.balloons()
            st.cache_data.clear()
        else:
            st.error(mensaje)

def guardar_nueva_propuesta_en_sheets(workbook, state):
    try:
        propuestas_sheet = workbook.worksheet(PROPUESTAS_SHEET_NAME)
        detalle_sheet = workbook.worksheet(DETALLE_PROPUESTAS_SHEET_NAME)
        last_id = len(propuestas_sheet.get_all_records())
        nuevo_numero = f"PROP-{datetime.now().year}-{last_id + 1:04d}"
        state.set_numero_propuesta(nuevo_numero)
        propuesta_row = [
            state.numero_propuesta, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), state.vendedor,
            state.cliente_actual.get(CLIENTE_NOMBRE_COL, ""), state.cliente_actual.get("NIF", ""),
            state.status, float(state.subtotal_bruto), float(state.descuento_total),
            float(state.total_general), float(state.costo_total), float(state.margen_absoluto),
            float(state.margen_porcentual), state.observaciones, state.tienda_despacho
        ]
        propuestas_sheet.append_row(propuesta_row, value_input_option='USER_ENTERED')
        detalle_rows = []
        for item in state.cotizacion_items:
            descuento_valor = (item.get('Cantidad', 0) * item.get('Precio Unitario', 0)) * (item.get('Descuento (%)', 0) / 100)
            detalle_rows.append([
                state.numero_propuesta, item.get('Referencia', ''), item.get('Producto', ''),
                int(item.get('Cantidad', 0)), float(item.get('Precio Unitario', 0)),
                float(item.get('Costo', 0)), float(item.get('Descuento (%)', 0)),
                float(item.get('Total', 0)), int(item.get('Stock', 0)), float(descuento_valor)
            ])
        if detalle_rows:
            detalle_sheet.append_rows(detalle_rows, value_input_option='USER_ENTERED')
        return True, f"Propuesta {state.numero_propuesta} guardada con éxito."
    except Exception as e:
        return False, f"Error al guardar la nueva propuesta: {e}"

def actualizar_propuesta_en_sheets(workbook, state):
    try:
        propuestas_sheet = workbook.worksheet(PROPUESTAS_SHEET_NAME)
        detalle_sheet = workbook.worksheet(DETALLE_PROPUESTAS_SHEET_NAME)
        cell = propuestas_sheet.find(state.numero_propuesta)
        if not cell:
            return False, f"Error: No se encontró la propuesta {state.numero_propuesta} para actualizar."
        propuesta_row_updated = [
            state.numero_propuesta, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), state.vendedor,
            state.cliente_actual.get(CLIENTE_NOMBRE_COL, ""), state.cliente_actual.get("NIF", ""),
            state.status, float(state.subtotal_bruto), float(state.descuento_total),
            float(state.total_general), float(state.costo_total), float(state.margen_absoluto),
            float(state.margen_porcentual), state.observaciones, state.tienda_despacho
        ]
        propuestas_sheet.update(f'A{cell.row}:{chr(65 + len(propuesta_row_updated) - 1)}{cell.row}', [propuesta_row_updated], value_input_option='USER_ENTERED')
        registros_detalle = detalle_sheet.get_all_records()
        filas_a_borrar = [i + 2 for i, record in enumerate(registros_detalle) if record.get('numero_propuesta') == state.numero_propuesta]
        if filas_a_borrar:
            for row_num in sorted(filas_a_borrar, reverse=True):
                detalle_sheet.delete_rows(row_num)
        detalle_rows_nuevos = []
        for item in state.cotizacion_items:
            descuento_valor = (item.get('Cantidad', 0) * item.get('Precio Unitario', 0)) * (item.get('Descuento (%)', 0) / 100)
            detalle_rows_nuevos.append([
                state.numero_propuesta, item.get('Referencia', ''), item.get('Producto', ''),
                int(item.get('Cantidad', 0)), float(item.get('Precio Unitario', 0)),
                float(item.get('Costo', 0)), float(item.get('Descuento (%)', 0)),
                float(item.get('Total', 0)), int(item.get('Stock', 0)), float(descuento_valor)
            ])
        if detalle_rows_nuevos:
            detalle_sheet.append_rows(detalle_rows_nuevos, value_input_option='USER_ENTERED')
        return True, f"Propuesta {state.numero_propuesta} actualizada con éxito."
    except Exception as e:
        return False, f"Error al actualizar la propuesta: {e}"

# --- INICIO DE LA MODIFICACIÓN PARA CLIENTES NUEVOS ---
def crear_nuevo_cliente(workbook, nombre, nif, email, telefono, direccion):
    """
    Añade un nuevo cliente a la hoja "Clientes" y devuelve su información.
    
    Esta función ahora retorna tres valores:
    1.  `bool`: True si fue exitoso, False si hubo un error.
    2.  `str`: Un mensaje de éxito o error.
    3.  `dict` o `None`: Un diccionario con los datos del nuevo cliente si fue exitoso,
        para poder cargarlo inmediatamente en la aplicación.
    """
    if not all([nombre, nif]):
        return False, "El Nombre y el NIF/C.C. son obligatorios.", None

    try:
        clientes_sheet = workbook.worksheet(CLIENTES_SHEET_NAME)
        
        # Estructura del nuevo cliente como un diccionario.
        # ¡Asegúrate de que los nombres de las claves coincidan con las cabeceras de tu G-Sheet!
        nuevo_cliente_dict = {
            "Nombre": nombre,
            "NIF": nif,
            "E-Mail": email,
            "Teléfono": telefono,
            "Dirección": direccion
        }
        
        # Obtiene las cabeceras de la hoja para asegurar el orden correcto al insertar.
        headers = clientes_sheet.row_values(1)
        # Crea la lista de valores en el orden correcto. Si una columna no existe, la omite.
        nueva_fila_cliente = [nuevo_cliente_dict.get(h, "") for h in headers]
        
        clientes_sheet.append_row(nueva_fila_cliente, value_input_option='USER_ENTERED')
        
        # IMPORTANTE: Limpiar el caché de datos para que la app recargue la lista de clientes.
        st.cache_data.clear()
        
        mensaje_exito = f"✅ ¡Éxito! Cliente '{nombre}' creado. Ya puedes seleccionarlo para cotizar."
        
        # Devuelve el éxito, el mensaje y el diccionario del nuevo cliente.
        return True, mensaje_exito, nuevo_cliente_dict
        
    except Exception as e:
        mensaje_error = f"❌ Error al crear el nuevo cliente: {e}"
        return False, mensaje_error, None
# --- FIN DE LA MODIFICACIÓN ---


class PDF(FPDF):
    def __init__(self, document_title="PROPUESTA COMERCIAL", **kwargs):
        super().__init__(**kwargs)
        self.set_margins(left=10, top=10, right=10)
        self.set_auto_page_break(True, margin=45)
        self.document_title = document_title

    def header(self):
        if LOGO_FILE_PATH.exists():
            self.image(str(LOGO_FILE_PATH), x=10, y=8, w=80)
        self.set_y(18)
        self.set_x(-95)
        self.set_font('Arial', 'B', 18)
        self.set_text_color(*COLOR_AZUL)
        self.cell(90, 10, self.document_title, 0, 1, 'R')
        self.set_y(42)
        self.line(10, self.get_y(), 200, self.get_y())

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(*COLOR_AZUL)
        self.set_text_color(255)
        self.cell(0, 8, f" {title}", 0, 1, 'L', 1)
        self.set_text_color(0)
        self.ln(4)

    def footer(self):
        self.set_y(-40)
        self.set_font('Arial', 'B', 7)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 5, '', 'T', 1, 'C')
        y_inicial_footer = self.get_y()
        self.set_font('Arial', 'B', 8)
        self.cell(47, 5, 'PEREIRA', 0, 0, 'C', True)
        self.cell(1, 5, '', 0, 0, 'C')
        self.cell(47, 5, 'DOSQUEBRADAS', 0, 0, 'C', True)
        self.cell(1, 5, '', 0, 0, 'C')
        self.cell(47, 5, 'ARMENIA', 0, 0, 'C', True)
        self.cell(1, 5, '', 0, 0, 'C')
        self.cell(46, 5, 'MANIZALES', 0, 1, 'C', True)
        self.set_y(y_inicial_footer + 5)
        self.set_font('Arial', '', 7)
        self.multi_cell(47, 3.5, 'CR 13 19-26 Parque Olaya\nP.B.X. (606) 333 0101 opcion 1\n310 830 5302', 0, 'C')
        self.set_y(y_inicial_footer + 5)
        self.set_x(58)
        self.multi_cell(47, 3.5, 'CR 10 17-56 Ópalo\nTel. (606) 322 3868\n310 856 1506', 0, 'C')
        self.set_y(y_inicial_footer + 5)
        self.set_x(106)
        self.multi_cell(47, 3.5, 'CR 19 11-05 San Francisco\nPBX. (606) 333 0101 opcion 3\n316 521 9904', 0, 'C')
        self.set_y(y_inicial_footer + 5)
        self.set_x(154)
        self.multi_cell(46, 3.5, 'CL 16 21-32 San Antonio\nPBX. (606) 333 0101 opcion 4\n313 608 6232', 0, 'C')
        self.set_y(y_inicial_footer + 17)
        self.set_font('Arial', 'I', 6)
        self.cell(47, 5, 'tiendopintucopereira@ferreinox.co', 0, 0, 'C')
        self.cell(1, 5, '', 0, 0, 'C')
        self.cell(47, 5, 'tiendapintucodosquebradas@ferreinox.co', 0, 0, 'C')
        self.cell(1, 5, '', 0, 0, 'C')
        self.cell(47, 5, 'tiendapintucoarmenio@ferreinox.co', 0, 0, 'C')
        self.cell(1, 5, '', 0, 0, 'C')
        self.cell(46, 5, 'tiendapintucomanizales@ferreinox.co', 0, 1, 'C')
        self.set_y(-10)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_profesional(state, workbook):
    if state.status == 'Aceptada':
        documento_titulo = 'PEDIDO DE VENTA'
        numero_documento_label = "Pedido #:"
    else:
        documento_titulo = 'PROPUESTA COMERCIAL'
        numero_documento_label = "Propuesta #:"

    pdf = PDF(orientation='P', unit='mm', format='A4', document_title=documento_titulo)
    pdf.add_page()
    start_y_info = 47
    pdf.set_y(start_y_info)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0)
    pdf.cell(95, 7, f"DATOS DEL {documento_titulo.split(' ')[0]}", border=1, ln=0, align='C', fill=True)
    pdf.set_x(105)
    pdf.cell(95, 7, "CLIENTE", border=1, ln=1, align='C', fill=True)
    y_after_headers = pdf.get_y()
    pdf.set_font('Arial', '', 9)
    prop_content = (f"**{numero_documento_label}** {state.numero_propuesta}\n"
                    f"**Fecha de Emisión:** {datetime.now().strftime('%d/%m/%Y')}\n"
                    f"**Validez de la Oferta:** 15 días\n"
                    f"**Asesor Comercial:** {state.vendedor}")
    pdf.multi_cell(95, 5, prop_content, border='LR', markdown=True)
    y_prop = pdf.get_y()
    pdf.set_y(y_after_headers)
    pdf.set_x(105)
    
    # --- INICIO: CORRECCIÓN DEL ERROR DE CODIFICACIÓN ---
    nombre_saneado = str(state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'N/A')).encode('latin-1', 'replace').decode('latin-1')
    nif_saneado = str(state.cliente_actual.get('NIF', 'N/A')).encode('latin-1', 'replace').decode('latin-1')
    direccion_saneada = str(state.cliente_actual.get('Dirección', 'N/A')).encode('latin-1', 'replace').decode('latin-1')
    telefono_saneado = str(state.cliente_actual.get('Teléfono', 'N/A')).encode('latin-1', 'replace').decode('latin-1')

    client_content = (f"**Nombre:** {nombre_saneado}\n"
                      f"**NIF/C.C.:** {nif_saneado}\n"
                      f"**Dirección:** {direccion_saneada}\n"
                      f"**Teléfono:** {telefono_saneado}")
    # --- FIN: CORRECCIÓN DEL ERROR DE CODIFICACIÓN ---

    pdf.multi_cell(95, 5, client_content, border='LR', markdown=True)
    y_cli = pdf.get_y()
    max_y = max(y_prop, y_cli)
    pdf.line(10, y_after_headers, 10, max_y)
    pdf.line(105, y_after_headers, 105, max_y)
    pdf.line(10, max_y, 105, max_y)
    pdf.line(105, max_y, 200, max_y)
    pdf.set_y(max_y + 5)
    pdf.set_font('Arial', '', 10)
    
    nombre_cliente = str(state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente')).encode('latin-1', 'replace').decode('latin-1')
    
    mensaje_motivacional = (f"**Apreciado/a {nombre_cliente},**\n"
                            "Nos complace presentarle esta propuesta comercial diseñada a su medida. En Ferreinox, nuestro compromiso es su satisfacción, "
                            "ofreciendo soluciones de la más alta calidad y servicio.")
    pdf.multi_cell(0, 5, mensaje_motivacional, 0, 'J', markdown=True)
    pdf.ln(10)
    pdf.chapter_title('Detalle de la Cotización')
    pdf.set_fill_color(*COLOR_AZUL)
    pdf.set_text_color(255)
    pdf.set_font('Arial', 'B', 10)
    column_widths = [20, 85, 15, 25, 20, 25]
    columns = ['Ref.', 'Producto', 'Cant.', 'Precio U.', 'Desc. (%)', 'Total']
    for i, col in enumerate(columns):
        pdf.cell(column_widths[i], 8, col, 1, 0, 'C', 1)
    pdf.ln()
    pdf.set_text_color(0)
    pdf.set_font('Arial', '', 9)
    for item in state.cotizacion_items:
        # --- INICIO DEL CAMBIO: Lógica de resaltado mejorada ---
        # Se resalta en rojo si la cantidad solicitada es MAYOR que el stock disponible.
        if item.get('Cantidad', 0) > item.get('Stock', 0):
            pdf.set_text_color(255, 0, 0)
        # --- FIN DEL CAMBIO ---
        try:
            ref = str(item.get('Referencia', '')).encode('latin-1', 'replace').decode('latin-1')
            prod = str(item.get('Producto', '')).encode('latin-1', 'replace').decode('latin-1')
        except:
            ref = str(item.get('Referencia', ''))
            prod = str(item.get('Producto', ''))
        pdf.cell(column_widths[0], 7, ref, 1, 0, 'L')
        pdf.cell(column_widths[1], 7, prod, 1, 0, 'L')
        pdf.cell(column_widths[2], 7, str(item.get('Cantidad', 0)), 1, 0, 'C')
        pdf.cell(column_widths[3], 7, f"${item.get('Precio Unitario', 0):,.2f}", 1, 0, 'R')
        pdf.cell(column_widths[4], 7, f"{item.get('Descuento (%)', 0):.1f}%", 1, 0, 'C')
        pdf.cell(column_widths[5], 7, f"${item.get('Total', 0):,.2f}", 1, 1, 'R')
        pdf.set_text_color(0)
    y_final_tabla = pdf.get_y()
    altura_estimada_final = 40
    if state.observaciones:
        altura_estimada_final += 20
    if y_final_tabla + altura_estimada_final > 252:
        pdf.add_page()
        y_final_tabla = pdf.get_y()
    else:
        y_final_tabla += 5
    pdf.set_y(y_final_tabla)
    pdf.set_x(120)
    pdf.set_font('Arial', 'B', 10)
    base_gravable = state.subtotal_bruto - state.descuento_total
    pdf.cell(40, 7, 'Subtotal:', 0, 0, 'R')
    pdf.cell(40, 7, f'${state.subtotal_bruto:,.2f}', 0, 1, 'R')
    pdf.set_x(120)
    pdf.cell(40, 7, 'Descuento:', 0, 0, 'R')
    pdf.cell(40, 7, f'-${state.descuento_total:,.2f}', 0, 1, 'R')
    pdf.set_x(120)
    pdf.cell(40, 7, 'Base Gravable:', 0, 0, 'R')
    pdf.cell(40, 7, f'${base_gravable:,.2f}', 0, 1, 'R')
    pdf.set_x(120)
    pdf.cell(40, 7, f'IVA ({TASA_IVA:.0%}):', 0, 0, 'R')
    pdf.cell(40, 7, f'${state.iva_valor:,.2f}', 0, 1, 'R')
    pdf.set_x(120)
    pdf.line(120, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(1)
    pdf.set_x(120)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 8, 'TOTAL:', 0, 0, 'R')
    pdf.cell(40, 8, f'${state.total_general:,.2f}', 0, 1, 'R')
    y_despues_totales = pdf.get_y()
    y_advertencia = y_final_tabla

    # --- INICIO DEL CAMBIO: Lógica de advertencia de inventario mejorada y detallada ---
    items_con_faltante = []
    for item in state.cotizacion_items:
        cantidad_solicitada = item.get('Cantidad', 0)
        stock_disponible = item.get('Stock', 0)
        if cantidad_solicitada > stock_disponible:
            faltante = cantidad_solicitada - stock_disponible
            # Aseguramos la codificación correcta del nombre del producto
            nombre_producto_saneado = str(item.get('Producto', 'N/A')).encode('latin-1', 'replace').decode('latin-1')
            items_con_faltante.append({'nombre': nombre_producto_saneado, 'faltante': faltante})

    if items_con_faltante:
        pdf.set_y(y_final_tabla)
        pdf.set_x(10)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(*COLOR_AZUL)
        pdf.cell(100, 7, "ADVERTENCIA DE INVENTARIO", 0, 1, 'L')
        pdf.set_text_color(0)
        pdf.set_font('Arial', 'I', 8)
        pdf.set_text_color(194, 8, 8)
        
        # Mensaje general
        mensaje_general = ("La entrega de los artículos marcados en rojo estará sujeta a los tiempos de reposición de nuestro proveedor. "
                           "Le recomendamos confirmar las fechas de entrega con su asesor comercial.\n\n")

        # Detalle específico de unidades faltantes
        detalle_faltantes = "**Detalle de Faltantes:**\n"
        for item_faltante in items_con_faltante:
            # Usamos un guión para simular una lista, ya que el markdown de FPDF es limitado
            detalle_faltantes += f"- Para **{item_faltante['nombre']}**, es necesario solicitar **{item_faltante['faltante']}** unidad(es) adicional(es).\n"
        
        mensaje_completo = mensaje_general + detalle_faltantes
        
        pdf.multi_cell(100, 4, mensaje_completo, 0, 'J', markdown=True)
        pdf.set_text_color(0)
        y_advertencia = pdf.get_y()
    # --- FIN DEL CAMBIO ---

    pdf.set_y(max(y_despues_totales, y_advertencia) + 10)
    if state.observaciones:
        pdf.chapter_title('Observaciones Adicionales')
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, state.observaciones, border=1)
        pdf.ln(5)
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 5, '**Garantía:** Productos cubiertos por garantía de fábrica. No cubre mal uso.', border=1, markdown=True)
    try:
        buffer = BytesIO()
        pdf.output(buffer)
        return buffer.getvalue()
    except Exception as e:
        st.error(f"Error crítico al generar el PDF: {e}")
        return None

def enviar_email_seguro(destinatario, state, pdf_bytes, nombre_archivo, is_copy=False):
    try:
        email_emisor = st.secrets["email_credentials"]["smtp_user"]
        password_emisor = st.secrets["email_credentials"]["smtp_password"]
        smtp_server = st.secrets["email_credentials"]["smtp_server"]
        smtp_port = int(st.secrets["email_credentials"]["smtp_port"])
        msg = MIMEMultipart()
        if state.status == 'Aceptada':
            msg['Subject'] = f"Confirmación de su Pedido de Venta N° {state.numero_propuesta}"
        elif is_copy:
            msg['Subject'] = f"Copia de su Propuesta Comercial N° {state.numero_propuesta}"
        else:
            msg['Subject'] = f"Propuesta Comercial de Ferreinox - N° {state.numero_propuesta}"
        msg['From'] = email_emisor
        msg['To'] = destinatario
        cuerpo_email = f"Estimado/a {state.cliente_actual.get(CLIENTE_NOMBRE_COL)},\n\nAdjunto encontrará el documento N° {state.numero_propuesta} que hemos preparado para usted.\n\nQuedamos a su disposición para cualquier consulta.\n\nSaludos cordiales,\n{state.vendedor}\nFerreinox"
        msg.attach(MIMEText(cuerpo_email, 'plain'))
        if pdf_bytes:
            adjunto = MIMEApplication(pdf_bytes, _subtype="pdf")
            adjunto.add_header('Content-Disposition', 'attachment', filename=nombre_archivo)
            msg.attach(adjunto)
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(email_emisor, password_emisor)
            server.send_message(msg)
        return True, "Correo enviado exitosamente."
    except KeyError:
        return False, "Error de configuración: Asegúrate de que tu archivo 'secrets.toml' tenga la sección [email_credentials]."
    except Exception as e:
        return False, f"Error al enviar el correo: {e}"

def guardar_pdf_en_drive(workbook, pdf_bytes, nombre_archivo):
    try:
        shared_drive_id = st.secrets["gsheets"]["drive_folder_id"] 
        creds = workbook.creds
        service = build('drive', 'v3', credentials=creds)
        query = f"name='{nombre_archivo}' and '{shared_drive_id}' in parents and trashed=false"
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = response.get('files', [])
        media_body = MediaIoBaseUpload(BytesIO(pdf_bytes), mimetype='application/pdf', resumable=True)
        if files:
            existing_file_id = files[0].get('id')
            file = service.files().update(
                fileId=existing_file_id,
                media_body=media_body,
                fields='id',
                supportsAllDrives=True
            ).execute()
            file_id = file.get('id')
        else:
            file_metadata = {
                'name': nombre_archivo,
                'parents': [shared_drive_id]
            }
            file = service.files().create(
                body=file_metadata,
                media_body=media_body,
                fields='id',
                supportsAllDrives=True
            ).execute()
            file_id = file.get('id')
            permission = {'type': 'anyone', 'role': 'reader'}
            service.permissions().create(
                fileId=file_id, 
                body=permission,
                supportsAllDrives=True
            ).execute()
        return True, file_id
    except KeyError:
        return False, "Error de Configuración: Asegúrate de tener 'drive_folder_id' en tu archivo secrets.toml."
    except Exception as e:
        return False, f"Error al guardar/actualizar PDF en Drive: {e}"

def generar_boton_whatsapp(state, telefono, pdf_link=None):
    if not state.cliente_actual or not telefono:
        return ""
    telefono_limpio = re.sub(r'\D', '', str(telefono))
    whatsapp_number = f"57{telefono_limpio}"
    nombre_cliente = state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente')
    numero_propuesta_limpio = state.numero_propuesta.replace('TEMP-', '')

    if state.status == 'Aceptada':
        documento_label = "PEDIDO DE VENTA"
    else:
        documento_label = "PROPUESTA COMERCIAL"
    
    mensaje_base = f"Hola {nombre_cliente}, te compartimos el {documento_label} N° {numero_propuesta_limpio} de parte de Ferreinox SAS BIC."
    
    if pdf_link:
        mensaje_completo = (f"{mensaje_base}\n\n"
                            f"Puedes revisar el PDF del documento en el siguiente enlace:\n{pdf_link}\n\n"
                            "No olvides consultar información adicional en www.ferreinox.co")
    else:
        mensaje_completo = mensaje_base
    mensaje_codificado = urllib.parse.quote(mensaje_completo)
    url_whatsapp = f"https://wa.me/{whatsapp_number}?text={mensaje_codificado}"
    boton_html = f"""
    <style>
    .whatsapp-button {{
        background-color: #25D366; color: white; padding: 10px 24px; border: none;
        border-radius: 4px; text-align: center; text-decoration: none;
        display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer;
        font-family: 'Source Sans Pro', sans-serif; width: 100%; box-sizing: border-box;
    }}
    .whatsapp-button:hover {{ background-color: #128C7E; color: white; text-decoration: none; }}
    </style>
    <a href="{url_whatsapp}" target="_blank" style="text-decoration: none;">
        <button class="whatsapp-button">🔗 Enviar por WhatsApp</button>
    </a>
    """
    return boton_html

# --- SUGERENCIAS PARA UN CÓDIGO 300% MEJOR ---

# 1.  **Modularización y Clases de Estado (State Management):**
#     Tu código utiliza un objeto `state` que se pasa entre funciones. Esto funciona, pero a medida
#     que la app crece, puede volverse difícil de rastrear.
#     -   **Sugerencia:** Considera encapsular toda la lógica de la cotización (items, cliente, totales, etc.)
#         en una clase `Cotizacion`. El `st.session_state` de Streamlit podría almacenar una instancia
#         de esta clase. Esto haría el código más limpio y orientado a objetos.
#         Ej: `st.session_state.cotizacion_actual = Cotizacion(vendedor='NombreVendedor')`
#         Luego podrías llamar métodos como `st.session_state.cotizacion_actual.agregar_item(producto)`
#         o `st.session_state.cotizacion_actual.guardar(workbook)`.

# 2.  **Manejo de Errores Específico:**
#     Usas `except Exception as e:`, que es bueno para capturar todo, pero a veces es mejor
#     capturar errores específicos para dar mensajes más claros al usuario.
#     -   **Sugerencia:** En `connect_to_gsheets`, podrías capturar `gspread.exceptions.SpreadsheetNotFound`
#         o `google.auth.exceptions.RefreshError` por separado para informar al usuario exactamente
#         qué falló (ej: "La hoja de cálculo no se encontró" o "Error de autenticación, revise las credenciales").

# 3.  **Abstracción de la Lógica de Google Sheets:**
#     Las funciones para guardar y actualizar (`guardar_nueva_propuesta...`, `actualizar_propuesta...`)
#     mezclan la lógica de negocio (formatear datos de la propuesta) con la lógica de acceso a datos (llamar a `gspread`).
#     -   **Sugerencia:** Crea una clase `GoogleSheetManager` que maneje todas las interacciones con `gspread`.
#         Esta clase tendría métodos como `get_dataframe(sheet_name)`, `append_row(sheet_name, data)`,
#         `update_rows(...)`. Tu lógica principal solo llamaría a estos métodos, sin preocuparse por los
#         detalles de `gspread`. Esto hace que el código sea más fácil de probar y mantener.

# 4.  **Codificación de Caracteres (PDF):**
#     La línea `.encode('latin-1', 'replace').decode('latin-1')` es un parche común para `FPDF`, que no maneja
#     UTF-8 de forma nativa. Esto puede fallar con ciertos caracteres especiales.
#     -   **Sugerencia (A largo plazo):** Si la generación de PDF es crítica y necesitas soporte robusto para
#         caracteres internacionales (tildes, ñ, etc.), considera librerías como `reportlab` o `WeasyPrint`.
#         Aunque tienen una curva de aprendizaje mayor, manejan UTF-8 sin problemas y ofrecen más control
#         sobre el diseño. Por ahora, tu solución es un buen workaround.

# 5.  **Consistencia y Constantes:**
#     Tienes muchas constantes para nombres de hojas y columnas, ¡lo cual es excelente!
#     -   **Sugerencia:** Asegúrate de usar estas constantes en *todos* los lugares. Por ejemplo, en la función
#         `crear_nuevo_cliente` modificada, usé claves como "NIF", "Teléfono". Sería aún mejor definirlas
#         como constantes (ej: `CLIENTE_NIF_COL = "NIF"`) para evitar errores de tipeo y facilitar cambios futuros.

# 6.  **Optimización de la Actualización en Google Sheets:**
#     La función `actualizar_propuesta_en_sheets` busca todas las filas de detalle, las borra una por una
#     y luego añade las nuevas. Para hojas con miles de detalles, esto puede ser lento.
#     -   **Sugerencia:** `gspread` tiene una función `batch_update`. Podrías construir una sola solicitud
#         para borrar el rango de filas antiguas y otra para insertar las nuevas. Esto reduce el número de
#         llamadas a la API de Google y es significativamente más rápido. Es más complejo de implementar
#         pero vale la pena para aplicaciones de alto rendimiento.

# 7.  **Uso de Type Hinting:**
#     Python moderno se beneficia enormemente del "type hinting" (pistas de tipo) para mejorar la
#     legibilidad y la detección de errores.
#     -   **Sugerencia:** Añade tipos a las firmas de tus funciones.
#         Ej: `def crear_nuevo_cliente(workbook: gspread.Workbook, nombre: str, ...) -> tuple[bool, str, dict | None]:`
#         Esto no afecta la ejecución pero ayuda a los desarrolladores (y a herramientas como VSCode) a
#         entender qué tipo de datos espera y devuelve cada función.
