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

# --- CONSTANTES ---
# Asegúrate de tener este archivo en la misma carpeta que el script
LOGO_FILE_PATH = Path("superior.png") 
TASA_IVA = 0.19
# Color corporativo azul oscuro
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
STOCK_COL = "Stock"
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
    """Establece la conexión con Google Sheets usando las credenciales de Streamlit."""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        client = gspread.authorize(creds)
        workbook = client.open_by_key(st.secrets["gsheets"]["spreadsheet_key"])
        return workbook
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None

# --- CARGA DE DATOS ---
@st.cache_data(ttl=600)
def cargar_datos_maestros(_workbook):
    """Carga los dataframes de productos y clientes desde Google Sheets."""
    if not _workbook:
        return pd.DataFrame(), pd.DataFrame()
    try:
        productos_sheet = _workbook.worksheet(PRODUCTOS_SHEET_NAME)
        df_productos = pd.DataFrame(productos_sheet.get_all_records())
        # Crear una columna de búsqueda combinando nombre y referencia
        df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos['Referencia'].astype(str) + ")"
        
        clientes_sheet = _workbook.worksheet(CLIENTES_SHEET_NAME)
        df_clientes = pd.DataFrame(clientes_sheet.get_all_records())
        return df_productos, df_clientes
    except Exception as e:
        st.error(f"Ocurrió un error al cargar los datos maestros: {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=60)
def listar_propuestas_df(_workbook):
    """Obtiene un DataFrame con todas las propuestas guardadas."""
    if not _workbook:
        return pd.DataFrame()
    try:
        sheet = _workbook.worksheet(PROPUESTAS_SHEET_NAME)
        return pd.DataFrame(sheet.get_all_records())
    except Exception:
        return pd.DataFrame()

# --- ACCIONES DE GUARDADO ---
def handle_save(workbook, state):
    """Gestiona el proceso de guardado, ya sea creando o actualizando una propuesta."""
    if not state.cliente_actual:
        st.warning("Por favor, seleccione un cliente antes de guardar.")
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
    """Guarda una nueva propuesta y sus detalles en las hojas correspondientes."""
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
            float(state.margen_porcentual), state.observaciones
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
    """Actualiza una propuesta existente y sus detalles."""
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
            float(state.margen_porcentual), state.observaciones
        ]
        propuestas_sheet.update(f'A{cell.row}:{chr(65 + len(propuesta_row_updated) - 1)}{cell.row}', [propuesta_row_updated], value_input_option='USER_ENTERED')
        
        # Eliminar detalles antiguos
        registros_detalle = detalle_sheet.get_all_records()
        filas_a_borrar = [i + 2 for i, record in enumerate(registros_detalle) if record.get('numero_propuesta') == state.numero_propuesta]
        if filas_a_borrar:
            for row_num in sorted(filas_a_borrar, reverse=True):
                detalle_sheet.delete_rows(row_num)
                
        # Añadir detalles nuevos
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

# --- GENERACIÓN DE PDF PROFESIONAL CON DISEÑO PERSONALIZADO ---
class PDF(FPDF):
    """Clase personalizada para generar el PDF con encabezado y pie de página."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_margins(left=10, top=10, right=10)
        self.set_auto_page_break(True, margin=45)

    def header(self):
        # Logo más grande
        if LOGO_FILE_PATH.exists():
            self.image(str(LOGO_FILE_PATH), x=10, y=8, w=80) 
        
        # Posición Y para el bloque de la derecha
        self.set_y(18) 
        self.set_x(-95)
        
        # Título "PROPUESTA COMERCIAL"
        self.set_font('Arial', 'B', 18) 
        self.set_text_color(*COLOR_AZUL)
        self.cell(90, 10, 'PROPUESTA COMERCIAL', 0, 1, 'R')
        
        # Línea separadora
        self.set_y(42)
        self.line(10, self.get_y(), 200, self.get_y())

    def chapter_title(self, title):
        """Crea un título de sección con fondo de color."""
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(*COLOR_AZUL)
        self.set_text_color(255) # Blanco
        self.cell(0, 8, f" {title}", 0, 1, 'L', 1)
        self.set_text_color(0) # Restaurar a negro
        self.ln(4)

    def footer(self):
        """Crea un pie de página complejo con información de contacto y paginación."""
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
    """Genera el archivo PDF completo con la nueva estructura y contenido."""
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()

    # **CAMBIO: Bloque de información con recuadros**
    start_y_info = 47
    pdf.set_y(start_y_info)
    
    # Encabezados de los recuadros
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(240, 240, 240) # Gris claro para el fondo del título
    pdf.set_text_color(0)
    pdf.cell(95, 7, "DATOS DE LA PROPUESTA", border=1, ln=0, align='C', fill=True)
    pdf.set_x(105)
    pdf.cell(95, 7, "CLIENTE", border=1, ln=1, align='C', fill=True)
    
    y_after_headers = pdf.get_y()

    # Contenido de los recuadros
    pdf.set_font('Arial', '', 9)
    
    # Contenido de la izquierda
    prop_content = (
        f"**Propuesta #:** {state.numero_propuesta}\n"
        f"**Fecha de Emisión:** {datetime.now().strftime('%d/%m/%Y')}\n"
        f"**Validez de la Oferta:** 15 días\n"
        f"**Asesor Comercial:** {state.vendedor}"
    )
    pdf.multi_cell(95, 5, prop_content, border='LR', markdown=True)
    y_prop = pdf.get_y()
    
    # Contenido de la derecha
    pdf.set_y(y_after_headers)
    pdf.set_x(105)
    client_content = (
        f"**Nombre:** {state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'N/A')}\n"
        f"**NIF/C.C.:** {state.cliente_actual.get('NIF', 'N/A')}\n"
        f"**Dirección:** {state.cliente_actual.get('Dirección', 'N/A')}\n"
        f"**Teléfono:** {state.cliente_actual.get('Teléfono', 'N/A')}"
    )
    pdf.multi_cell(95, 5, client_content, border='LR', markdown=True)
    y_cli = pdf.get_y()

    # Líneas inferiores de los recuadros
    max_y = max(y_prop, y_cli)
    pdf.line(10, y_after_headers, 10, max_y) # Línea izquierda del primer cuadro
    pdf.line(105, y_after_headers, 105, max_y) # Línea izquierda del segundo cuadro
    pdf.line(10, max_y, 105, max_y) # Línea inferior del primer cuadro
    pdf.line(105, max_y, 200, max_y) # Línea inferior del segundo cuadro

    # Ajustar Y para el siguiente elemento
    pdf.set_y(max_y + 5)

    # **CAMBIO: Mensaje motivacional más corto**
    pdf.set_font('Arial', '', 10)
    nombre_cliente = state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'Cliente')
    mensaje_motivacional = (
        f"**Apreciado/a {nombre_cliente},**\n"
        "Nos complace presentarle esta propuesta comercial diseñada a su medida. En Ferreinox, nuestro compromiso es su satisfacción, "
        "ofreciendo soluciones de la más alta calidad y servicio."
    )
    pdf.multi_cell(0, 5, mensaje_motivacional, 0, 'J', markdown=True)
    pdf.ln(10)

    # Tabla de Productos
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

    # Lógica de Totales y Advertencia de Inventario
    y_final_tabla = pdf.get_y()
    
    altura_estimada_final = 40 
    if state.observaciones:
        altura_estimada_final += 20
    if y_final_tabla + altura_estimada_final > 252:
        pdf.add_page()
        y_final_tabla = pdf.get_y()
    else:
        y_final_tabla += 5

    # Bloque de Totales (Columna Derecha)
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

    # Bloque de Advertencia de Inventario (Columna Izquierda)
    y_advertencia = y_final_tabla
    productos_sin_stock = [item['Producto'] for item in state.cotizacion_items if item.get('Stock', 0) <= 0]
    if productos_sin_stock:
        pdf.set_y(y_final_tabla)
        pdf.set_x(10)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(*COLOR_AZUL)
        pdf.cell(100, 7, "ADVERTENCIA DE INVENTARIO", 0, 1, 'L')
        pdf.set_text_color(0)
        
        pdf.set_font('Arial', 'I', 8)
        pdf.set_text_color(194, 8, 8)
        mensaje_stock = (
            "La entrega de los artículos marcados en rojo estará sujeta a los tiempos de reposición de nuestro proveedor. "
            "Le recomendamos confirmar las fechas de entrega con su asesor comercial."
        )
        pdf.multi_cell(100, 4, mensaje_stock, 0, 'J')
        pdf.set_text_color(0)
        y_advertencia = pdf.get_y()

    # Ajustar Y a la celda más alta y añadir bloques finales
    pdf.set_y(max(y_despues_totales, y_advertencia) + 10)

    if state.observaciones:
        pdf.chapter_title('Observaciones Adicionales')
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, state.observaciones, border=1)
        pdf.ln(5)

    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 5, '**Garantía:** Productos cubiertos por garantía de fábrica. No cubre mal uso.', border=1, markdown=True)
    
    # Salida segura del PDF
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
        # --- CORRECCIÓN ---
        # Se ajustan las claves para que coincidan con el archivo secrets.toml ([email_credentials])
        email_emisor = st.secrets["email_credentials"]["smtp_user"]
        password_emisor = st.secrets["email_credentials"]["smtp_password"]
        smtp_server = st.secrets["email_credentials"]["smtp_server"]
        smtp_port = int(st.secrets["email_credentials"]["smtp_port"]) # El puerto debe ser un entero

        msg = MIMEMultipart()
        
        if is_copy:
            msg['Subject'] = f"Copia de su Propuesta Comercial N° {state.numero_propuesta}"
        else:
            msg['Subject'] = f"Propuesta Comercial de Ferreinox - N° {state.numero_propuesta}"
            
        msg['From'] = email_emisor
        msg['To'] = destinatario
        
        cuerpo_email = f"Estimado/a {state.cliente_actual.get(CLIENTE_NOMBRE_COL)},\n\nAdjunto encontrará la propuesta comercial N° {state.numero_propuesta} que hemos preparado para usted.\n\nQuedamos a su disposición para cualquier consulta.\n\nSaludos cordiales,\n{state.vendedor}\nFerreinox"
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
        # Mensaje de error más específico para guiar al usuario
        return False, "Error de configuración: Asegúrate de que tu archivo 'secrets.toml' tenga la sección [email_credentials] con las claves smtp_user, smtp_password, smtp_server y smtp_port."
    except Exception as e:
        return False, f"Error al enviar el correo: {e}"
