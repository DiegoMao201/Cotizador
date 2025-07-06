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
from urllib.parse import quote
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoUploader

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador Ferreinox", layout="wide")


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
CLIENTE_TELEFONO_COL = "Teléfono" # Nombre de la columna en Sheets
NOMBRE_PRODUCTO_COL = "Descripción"
STOCK_COL = "Stock"
PRECIOS_COLS = [
    "Detallista 801 lista 2", "Publico 800 Lista 1",
    "Publico 345 Lista 1 complementarios", "Lista 346 Lista Complementarios",
    "Lista 100123 Construaliados"
]
PROPUESTA_CLIENTE_COL = "cliente_nombre"
ESTADOS_COTIZACION = ["Borrador", "Enviada", "Aceptada", "Rechazada"]

# --- CONEXIONES A SERVICIOS DE GOOGLE ---
@st.cache_resource
def connect_to_gsheets():
    """Establece la conexión con Google Sheets."""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
        )
        client = gspread.authorize(creds)
        workbook = client.open_by_key(st.secrets["gsheets"]["spreadsheet_key"])
        return workbook, creds
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None, None

@st.cache_resource
def get_drive_service(_creds):
    """Construye y devuelve un objeto de servicio de la API de Google Drive."""
    if not _creds:
        st.error("No hay credenciales para conectar con Google Drive.")
        return None
    try:
        service = build('drive', 'v3', credentials=_creds)
        return service
    except Exception as e:
        st.error(f"Error al conectar con Google Drive: {e}")
        return None

def upload_pdf_to_drive_and_get_link(service, pdf_bytes, file_name):
    """Sube un archivo PDF a Google Drive y devuelve un enlace compartible."""
    if not service:
        return None, "El servicio de Google Drive no está disponible."
    try:
        folder_id = st.secrets.get("gsheets", {}).get("drive_folder_id")
        file_metadata = {'name': file_name, 'mimeType': 'application/pdf'}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaIoUploader(BytesIO(pdf_bytes), mimetype='application/pdf', resumable=True)
        
        with st.spinner(f"Subiendo {file_name} a Google Drive..."):
            file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
            file_id = file.get('id')
            service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()

        st.success("PDF subido a Google Drive con éxito.")
        return file.get('webViewLink'), None
    except Exception as e:
        error_message = f"Error al subir el PDF a Google Drive: {e}"
        st.error(error_message)
        return None, error_message

# --- CARGA DE DATOS ---
@st.cache_data(ttl=600)
def cargar_datos_maestros(_workbook):
    """Carga los dataframes de productos y clientes desde Google Sheets."""
    if not _workbook:
        return pd.DataFrame(), pd.DataFrame()
    try:
        productos_sheet = _workbook.worksheet(PRODUCTOS_SHEET_NAME)
        df_productos = pd.DataFrame(productos_sheet.get_all_records())
        df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos['Referencia'].astype(str) + ")"
        
        clientes_sheet = _workbook.worksheet(CLIENTES_SHEET_NAME)
        df_clientes = pd.DataFrame(clientes_sheet.get_all_records())
        return df_productos, df_clientes
    except Exception as e:
        st.error(f"Ocurrió un error al cargar los datos maestros: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- ACCIONES DE GUARDADO Y ENVÍO ---
def handle_save(workbook, state):
    """Gestiona el proceso de guardado de una propuesta."""
    if not state.get('cliente_actual'):
        st.warning("Por favor, seleccione un cliente antes de guardar.")
        return
    if not state.get('cotizacion_items'):
        st.warning("No hay productos en la cotización para guardar.")
        return
        
    with st.spinner("Guardando propuesta..."):
        if state.get('numero_propuesta') and "TEMP" not in state.get('numero_propuesta'):
            exito, mensaje = actualizar_propuesta_en_sheets(workbook, state)
        else:
            exito, mensaje = guardar_nueva_propuesta_en_sheets(workbook, state)
            
        if exito:
            st.success(mensaje)
            st.balloons()
            st.cache_data.clear()
        else:
            st.error(mensaje)

def handle_whatsapp_share(state, drive_service, workbook):
    """Genera el PDF, lo sube a Drive y prepara un enlace de WhatsApp."""
    if not state.get('cliente_actual'):
        st.warning("Por favor, seleccione un cliente para generar el enlace.")
        return
    if not state.get('cotizacion_items'):
        st.warning("No hay productos en la cotización para compartir.")
        return
    
    phone_number_raw = state.get('cliente_telefono_editable', '')
    if not phone_number_raw:
        st.error("El cliente no tiene un número de teléfono registrado o el campo está vacío.")
        return
    
    # Formatear número para WhatsApp: quitar caracteres no numéricos y asegurar prefijo 57
    phone_number = "".join(filter(str.isdigit, str(phone_number_raw)))
    if not phone_number.startswith("57"):
        phone_number = "57" + phone_number

    with st.spinner("Generando PDF para compartir..."):
        pdf_bytes = generar_pdf_profesional(state, workbook)
    if not pdf_bytes:
        st.error("No se pudo generar el PDF.")
        return

    file_name = f"Propuesta_{state.get('numero_propuesta', 'TEMP')}_{state['cliente_actual'].get(CLIENTE_NOMBRE_COL, 'Cliente')}.pdf"
    link, error = upload_pdf_to_drive_and_get_link(drive_service, pdf_bytes, file_name)
    if error:
        return

    nombre_cliente = state['cliente_actual'].get(CLIENTE_NOMBRE_COL, 'Cliente').split(' ')[0]
    mensaje = (
        f"¡Hola {nombre_cliente}! 👋\n\n"
        f"Te saluda {state.get('vendedor', 'tu asesor')} de Ferreinox.\n\n"
        f"Adjunto el enlace a tu propuesta comercial N° {state.get('numero_propuesta', 'Borrador')}:\n"
        f"{link}\n\n"
        "Quedo a tu disposición para cualquier consulta. ¡Que tengas un excelente día!"
    )
    whatsapp_url = f"https://wa.me/{phone_number}?text={quote(mensaje)}"
    
    # Usamos st.markdown para crear un botón que abre en una nueva pestaña
    st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="width:100%; padding: 10px; background-color: #25D366; color: white; border: none; border-radius: 5px; cursor: pointer;">✅ ¡Listo! Haz clic para enviar por WhatsApp</button></a>', unsafe_allow_html=True)

def handle_email_send(state, workbook):
    """Genera el PDF y lo envía por correo electrónico."""
    if not state.get('cliente_actual'):
        st.warning("Por favor, seleccione un cliente para enviar el correo.")
        return
    if not state.get('cotizacion_items'):
        st.warning("No hay productos en la cotización para enviar.")
        return

    destinatario = state.get('cliente_email_editable', '')
    if not destinatario:
        st.error("El cliente no tiene un correo electrónico registrado o el campo está vacío.")
        return

    with st.spinner("Generando y enviando PDF por correo..."):
        pdf_bytes = generar_pdf_profesional(state, workbook)
        if not pdf_bytes:
            st.error("Fallo al generar el PDF, no se puede enviar el correo.")
            return
        
        nombre_archivo = f"Propuesta_{state.get('numero_propuesta', 'TEMP')}_{state['cliente_actual'].get(CLIENTE_NOMBRE_COL, 'Cliente')}.pdf"
        exito, mensaje = enviar_email_seguro(destinatario, state, pdf_bytes, nombre_archivo)
        
        if exito:
            st.success(mensaje)
        else:
            st.error(mensaje)


def guardar_nueva_propuesta_en_sheets(workbook, state):
    """Guarda una nueva propuesta y sus detalles en las hojas correspondientes."""
    try:
        propuestas_sheet = workbook.worksheet(PROPUESTAS_SHEET_NAME)
        detalle_sheet = workbook.worksheet(DETALLE_PROPUESTAS_SHEET_NAME)
        
        last_id = len(propuestas_sheet.get_all_records())
        nuevo_numero = f"PROP-{datetime.now().year}-{last_id + 1:04d}"
        state['numero_propuesta'] = nuevo_numero
        
        propuesta_row = [
            state['numero_propuesta'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), state.get('vendedor'),
            state['cliente_actual'].get(CLIENTE_NOMBRE_COL, ""), state['cliente_actual'].get("NIF", ""),
            state.get('status'), float(state.get('subtotal_bruto')), float(state.get('descuento_total')),
            float(state.get('total_general')), float(state.get('costo_total')), float(state.get('margen_absoluto')),
            float(state.get('margen_porcentual')), state.get('observaciones')
        ]
        propuestas_sheet.append_row(propuesta_row, value_input_option='USER_ENTERED')
        
        detalle_rows = []
        for item in state['cotizacion_items']:
            descuento_valor = (item.get('Cantidad', 0) * item.get('Precio Unitario', 0)) * (item.get('Descuento (%)', 0) / 100)
            detalle_rows.append([
                state['numero_propuesta'], item.get('Referencia', ''), item.get('Producto', ''),
                int(item.get('Cantidad', 0)), float(item.get('Precio Unitario', 0)),
                float(item.get('Costo', 0)), float(item.get('Descuento (%)', 0)),
                float(item.get('Total', 0)), int(item.get('Stock', 0)), float(descuento_valor)
            ])
            
        if detalle_rows:
            detalle_sheet.append_rows(detalle_rows, value_input_option='USER_ENTERED')
            
        return True, f"Propuesta {state['numero_propuesta']} guardada con éxito."
    except Exception as e:
        return False, f"Error al guardar la nueva propuesta: {e}"

def actualizar_propuesta_en_sheets(workbook, state):
    """Actualiza una propuesta existente y sus detalles."""
    try:
        propuestas_sheet = workbook.worksheet(PROPUESTAS_SHEET_NAME)
        detalle_sheet = workbook.worksheet(DETALLE_PROPUESTAS_SHEET_NAME)
        
        cell = propuestas_sheet.find(state['numero_propuesta'])
        if not cell:
            return False, f"Error: No se encontró la propuesta {state['numero_propuesta']} para actualizar."
            
        propuesta_row_updated = [
            state['numero_propuesta'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), state.get('vendedor'),
            state['cliente_actual'].get(CLIENTE_NOMBRE_COL, ""), state['cliente_actual'].get("NIF", ""),
            state.get('status'), float(state.get('subtotal_bruto')), float(state.get('descuento_total')),
            float(state.get('total_general')), float(state.get('costo_total')), float(state.get('margen_absoluto')),
            float(state.get('margen_porcentual')), state.get('observaciones')
        ]
        propuestas_sheet.update(f'A{cell.row}:{chr(65 + len(propuesta_row_updated) - 1)}{cell.row}', [propuesta_row_updated], value_input_option='USER_ENTERED')
        
        registros_detalle = detalle_sheet.get_all_records()
        filas_a_borrar = [i + 2 for i, record in enumerate(registros_detalle) if record.get('numero_propuesta') == state['numero_propuesta']]
        if filas_a_borrar:
            for row_num in sorted(filas_a_borrar, reverse=True):
                detalle_sheet.delete_rows(row_num)
                
        detalle_rows_nuevos = []
        for item in state['cotizacion_items']:
            descuento_valor = (item.get('Cantidad', 0) * item.get('Precio Unitario', 0)) * (item.get('Descuento (%)', 0) / 100)
            detalle_rows_nuevos.append([
                state['numero_propuesta'], item.get('Referencia', ''), item.get('Producto', ''),
                int(item.get('Cantidad', 0)), float(item.get('Precio Unitario', 0)),
                float(item.get('Costo', 0)), float(item.get('Descuento (%)', 0)),
                float(item.get('Total', 0)), int(item.get('Stock', 0)), float(descuento_valor)
            ])
            
        if detalle_rows_nuevos:
            detalle_sheet.append_rows(detalle_rows_nuevos, value_input_option='USER_ENTERED')
            
        return True, f"Propuesta {state['numero_propuesta']} actualizada con éxito."
    except Exception as e:
        return False, f"Error al actualizar la propuesta: {e}"

# --- GENERACIÓN DE PDF ---
class PDF(FPDF):
    """Clase personalizada para generar el PDF con encabezado y pie de página."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_margins(left=10, top=10, right=10)
        self.set_auto_page_break(True, margin=45)

    def header(self):
        if LOGO_FILE_PATH.exists():
            self.image(str(LOGO_FILE_PATH), x=10, y=8, w=80) 
        self.set_y(18) 
        self.set_x(-95)
        self.set_font('Arial', 'B', 18) 
        self.set_text_color(*COLOR_AZUL)
        self.cell(90, 10, 'PROPUESTA COMERCIAL', 0, 1, 'R')
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
        self.cell(47, 5, 'PEREIRA', 0, 0, 'C', True); self.cell(1, 5, '', 0, 0, 'C')
        self.cell(47, 5, 'DOSQUEBRADAS', 0, 0, 'C', True); self.cell(1, 5, '', 0, 0, 'C')
        self.cell(47, 5, 'ARMENIA', 0, 0, 'C', True); self.cell(1, 5, '', 0, 0, 'C')
        self.cell(46, 5, 'MANIZALES', 0, 1, 'C', True)
        self.set_y(y_inicial_footer + 5); self.set_font('Arial', '', 7)
        self.multi_cell(47, 3.5, 'CR 13 19-26 Parque Olaya\nP.B.X. (606) 333 0101 opcion 1\n310 830 5302', 0, 'C')
        self.set_y(y_inicial_footer + 5); self.set_x(58)
        self.multi_cell(47, 3.5, 'CR 10 17-56 Ópalo\nTel. (606) 322 3868\n310 856 1506', 0, 'C')
        self.set_y(y_inicial_footer + 5); self.set_x(106)
        self.multi_cell(47, 3.5, 'CR 19 11-05 San Francisco\nPBX. (606) 333 0101 opcion 3\n316 521 9904', 0, 'C')
        self.set_y(y_inicial_footer + 5); self.set_x(154)
        self.multi_cell(46, 3.5, 'CL 16 21-32 San Antonio\nPBX. (606) 333 0101 opcion 4\n313 608 6232', 0, 'C')
        self.set_y(y_inicial_footer + 17); self.set_font('Arial', 'I', 6)
        self.cell(47, 5, 'tiendopintucopereira@ferreinox.co', 0, 0, 'C'); self.cell(1, 5, '', 0, 0, 'C')
        self.cell(47, 5, 'tiendapintucodosquebradas@ferreinox.co', 0, 0, 'C'); self.cell(1, 5, '', 0, 0, 'C')
        self.cell(47, 5, 'tiendapintucoarmenio@ferreinox.co', 0, 0, 'C'); self.cell(1, 5, '', 0, 0, 'C')
        self.cell(46, 5, 'tiendapintucomanizales@ferreinox.co', 0, 1, 'C')
        self.set_y(-10); self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_profesional(state, workbook):
    """Genera el archivo PDF completo con la nueva estructura y contenido."""
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    start_y_info = 47
    pdf.set_y(start_y_info)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(240, 240, 240) 
    pdf.set_text_color(0)
    pdf.cell(95, 7, "DATOS DE LA PROPUESTA", border=1, ln=0, align='C', fill=True)
    pdf.set_x(105)
    pdf.cell(95, 7, "CLIENTE", border=1, ln=1, align='C', fill=True)
    
    y_after_headers = pdf.get_y()
    pdf.set_font('Arial', '', 9)
    
    prop_content = (
        f"**Propuesta #:** {state.get('numero_propuesta', 'Borrador')}\n"
        f"**Fecha de Emisión:** {datetime.now().strftime('%d/%m/%Y')}\n"
        f"**Validez de la Oferta:** 15 días\n"
        f"**Asesor Comercial:** {state.get('vendedor', 'No especificado')}"
    )
    pdf.multi_cell(95, 5, prop_content, border='LR', markdown=True)
    y_prop = pdf.get_y()
    
    pdf.set_y(y_after_headers)
    pdf.set_x(105)
    client_content = (
        f"**Nombre:** {state['cliente_actual'].get(CLIENTE_NOMBRE_COL, 'N/A')}\n"
        f"**NIF/C.C.:** {state['cliente_actual'].get('NIF', 'N/A')}\n"
        f"**Dirección:** {state['cliente_actual'].get('Dirección', 'N/A')}\n"
        f"**Teléfono:** {state.get('cliente_telefono_editable', 'N/A')}"
    )
    pdf.multi_cell(95, 5, client_content, border='LR', markdown=True)
    y_cli = pdf.get_y()

    max_y = max(y_prop, y_cli)
    pdf.line(10, y_after_headers, 10, max_y) 
    pdf.line(105, y_after_headers, 105, max_y) 
    pdf.line(10, max_y, 105, max_y) 
    pdf.line(105, max_y, 200, max_y) 

    pdf.set_y(max_y + 5)
    pdf.set_font('Arial', '', 10)
    nombre_cliente = state['cliente_actual'].get(CLIENTE_NOMBRE_COL, 'Cliente')
    mensaje_motivacional = (
        f"**Apreciado/a {nombre_cliente},**\n"
        "Nos complace presentarle esta propuesta comercial diseñada a su medida. En Ferreinox, nuestro compromiso es su satisfacción, "
        "ofreciendo soluciones de la más alta calidad y servicio."
    )
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
    
    for item in state['cotizacion_items']:
        if item.get('Stock', 0) <= 0:
            pdf.set_text_color(255, 0, 0)
        
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
    if state.get('observaciones'): altura_estimada_final += 20
    if y_final_tabla + altura_estimada_final > 252:
        pdf.add_page()
        y_final_tabla = pdf.get_y()
    else:
        y_final_tabla += 5

    pdf.set_y(y_final_tabla)
    pdf.set_x(120)
    pdf.set_font('Arial', 'B', 10)
    base_gravable = state.get('subtotal_bruto', 0) - state.get('descuento_total', 0)
    pdf.cell(40, 7, 'Subtotal:', 0, 0, 'R'); pdf.cell(40, 7, f"${state.get('subtotal_bruto', 0):,.2f}", 0, 1, 'R')
    pdf.set_x(120); pdf.cell(40, 7, 'Descuento:', 0, 0, 'R'); pdf.cell(40, 7, f'-${state.get('descuento_total', 0):,.2f}', 0, 1, 'R')
    pdf.set_x(120); pdf.cell(40, 7, 'Base Gravable:', 0, 0, 'R'); pdf.cell(40, 7, f'${base_gravable:,.2f}', 0, 1, 'R')
    pdf.set_x(120); pdf.cell(40, 7, f'IVA ({TASA_IVA:.0%}):', 0, 0, 'R'); pdf.cell(40, 7, f'${state.get("iva_valor", 0):,.2f}', 0, 1, 'R')
    pdf.set_x(120); pdf.line(120, pdf.get_y(), 200, pdf.get_y()); pdf.ln(1)
    pdf.set_x(120); pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 8, 'TOTAL:', 0, 0, 'R'); pdf.cell(40, 8, f'${state.get("total_general", 0):,.2f}', 0, 1, 'R')
    y_despues_totales = pdf.get_y()

    y_advertencia = y_final_tabla
    productos_sin_stock = [item['Producto'] for item in state['cotizacion_items'] if item.get('Stock', 0) <= 0]
    if productos_sin_stock:
        pdf.set_y(y_final_tabla); pdf.set_x(10)
        pdf.set_font('Arial', 'B', 10); pdf.set_text_color(*COLOR_AZUL)
        pdf.cell(100, 7, "ADVERTENCIA DE INVENTARIO", 0, 1, 'L')
        pdf.set_text_color(0); pdf.set_font('Arial', 'I', 8); pdf.set_text_color(194, 8, 8)
        mensaje_stock = ("La entrega de los artículos marcados en rojo estará sujeta a los tiempos de reposición. "
                         "Le recomendamos confirmar las fechas de entrega con su asesor comercial.")
        pdf.multi_cell(100, 4, mensaje_stock, 0, 'J')
        pdf.set_text_color(0)
        y_advertencia = pdf.get_y()

    pdf.set_y(max(y_despues_totales, y_advertencia) + 10)
    if state.get('observaciones'):
        pdf.chapter_title('Observaciones Adicionales')
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, state.get('observaciones'), border=1)
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
    """Envía el correo electrónico con el PDF adjunto de forma segura."""
    try:
        email_emisor = st.secrets["email_credentials"]["smtp_user"]
        password_emisor = st.secrets["email_credentials"]["smtp_password"]
        smtp_server = st.secrets["email_credentials"]["smtp_server"]
        smtp_port = int(st.secrets["email_credentials"]["smtp_port"])
        msg = MIMEMultipart()
        msg['Subject'] = f"Propuesta Comercial de Ferreinox - N° {state.get('numero_propuesta', 'Borrador')}"
        msg['From'] = email_emisor
        msg['To'] = destinatario
        cuerpo_email = f"Estimado/a {state['cliente_actual'].get(CLIENTE_NOMBRE_COL)},\n\nAdjunto encontrará la propuesta comercial N° {state.get('numero_propuesta', 'Borrador')} que hemos preparado para usted.\n\nQuedamos a su disposición para cualquier consulta.\n\nSaludos cordiales,\n{state.get('vendedor')}\nFerreinox"
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
        return False, "Error de configuración: Revisa tu archivo 'secrets.toml'."
    except Exception as e:
        return False, f"Error al enviar el correo: {e}"

# --- APLICACIÓN PRINCIPAL DE STREAMLIT ---
def main():
    st.title("Cotizador Profesional Ferreinox")

    # Inicializar estado de la sesión
    if 'cotizacion_items' not in st.session_state:
        st.session_state.cotizacion_items = []
        st.session_state.cliente_actual = None
        st.session_state.numero_propuesta = f"TEMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        # Otros valores iniciales
        st.session_state.vendedor = "Diego Mauricio Garcia"
        st.session_state.status = "Borrador"
        st.session_state.observaciones = ""
        st.session_state.subtotal_bruto = 0.0
        st.session_state.descuento_total = 0.0
        st.session_state.total_general = 0.0
        st.session_state.costo_total = 0.0
        st.session_state.margen_absoluto = 0.0
        st.session_state.margen_porcentual = 0.0
        st.session_state.iva_valor = 0.0
        st.session_state.cliente_email_editable = ""
        st.session_state.cliente_telefono_editable = ""

    # Conectar a servicios de Google
    workbook, g_creds = connect_to_gsheets()
    drive_service = get_drive_service(g_creds)

    if workbook is None or drive_service is None:
        st.error("No se pudo conectar a los servicios de Google. La aplicación no puede continuar.")
        st.stop()
    
    df_productos, df_clientes = cargar_datos_maestros(workbook)

    # --- SELECCIÓN DE CLIENTE Y DATOS EDITABLES ---
    st.header("1. Datos del Cliente")
    clientes_lista = [f"{row[CLIENTE_NOMBRE_COL]} ({row['NIF']})" for index, row in df_clientes.iterrows()]
    cliente_seleccionado_str = st.selectbox("Seleccione un cliente", options=clientes_lista, index=None, placeholder="Buscar cliente por nombre o NIF...")
    
    if cliente_seleccionado_str:
        nif_cliente = cliente_seleccionado_str.split('(')[-1].replace(')', '')
        cliente_data = df_clientes[df_clientes['NIF'] == nif_cliente].iloc[0].to_dict()
        if st.session_state.cliente_actual is None or st.session_state.cliente_actual['NIF'] != cliente_data['NIF']:
            st.session_state.cliente_actual = cliente_data
            st.session_state.cliente_email_editable = cliente_data.get(CLIENTE_EMAIL_COL, "")
            st.session_state.cliente_telefono_editable = cliente_data.get(CLIENTE_TELEFONO_COL, "")

    if st.session_state.cliente_actual:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.cliente_email_editable = st.text_input("Correo Electrónico del Cliente", value=st.session_state.cliente_email_editable)
        with col2:
            st.session_state.cliente_telefono_editable = st.text_input("Teléfono del Cliente (con indicativo)", value=st.session_state.cliente_telefono_editable)
    
    # Resto de la interfaz de la app (añadir productos, ver tabla, etc.)
    # ... (Aquí iría la lógica para añadir productos a la cotización) ...
    # Por simplicidad, esta parte se omite, pero debería existir en tu app real.

    st.header("2. Acciones")
    if st.session_state.cliente_actual:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Guardar Propuesta", use_container_width=True):
                handle_save(workbook, st.session_state)
        with col2:
            if st.button("📲 Enviar por WhatsApp", use_container_width=True):
                handle_whatsapp_share(st.session_state, drive_service, workbook)
        with col3:
            if st.button("📧 Enviar por Email", use_container_width=True):
                handle_email_send(st.session_state, workbook)
    else:
        st.info("Seleccione un cliente para habilitar las acciones de guardado y envío.")

if __name__ == "__main__":
    main()

