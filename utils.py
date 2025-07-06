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

# --- CONSTANTES ---
LOGO_FILE_PATH = Path("logo.png") # Asegúrate de tener este archivo
TASA_IVA = 0.19

# --- Nombres de las hojas ---
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

@st.cache_data(ttl=60)
def listar_propuestas_df(_workbook):
    try:
        sheet = _workbook.worksheet(PROPUESTAS_SHEET_NAME)
        return pd.DataFrame(sheet.get_all_records())
    except Exception:
        return pd.DataFrame()

# --- ACCIONES DE GUARDADO ---
def handle_save(workbook, state):
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
    try:
        propuestas_sheet = workbook.worksheet(PROPUESTAS_SHEET_NAME)
        detalle_sheet = workbook.worksheet(DETALLE_PROPUESTAS_SHEET_NAME)
        last_id = len(propuestas_sheet.get_all_records())
        nuevo_numero = f"PROP-{datetime.now().year}-{last_id + 1:04d}"
        state.set_numero_propuesta(nuevo_numero)

        # CORREGIDO: Convertir todos los números a tipos nativos de Python para evitar error JSON
        propuesta_row = [
            state.numero_propuesta,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            state.vendedor,
            state.cliente_actual.get(CLIENTE_NOMBRE_COL, ""),
            state.cliente_actual.get("NIF", ""),
            state.status,
            float(state.subtotal_bruto),
            float(state.descuento_total),
            float(state.total_general),
            float(state.costo_total),
            float(state.margen_absoluto),
            float(state.margen_porcentual),
            state.observaciones
        ]
        propuestas_sheet.append_row(propuesta_row, value_input_option='USER_ENTERED')

        detalle_rows = []
        for item in state.cotizacion_items:
            descuento_valor = (item.get('Cantidad', 0) * item.get('Precio Unitario', 0)) * (item.get('Descuento (%)', 0) / 100)
            detalle_rows.append([
                state.numero_propuesta,
                item.get('Referencia', ''),
                item.get('Producto', ''),
                int(item.get('Cantidad', 0)),
                float(item.get('Precio Unitario', 0)),
                float(item.get('Costo', 0)),
                float(item.get('Descuento (%)', 0)),
                float(item.get('Total', 0)),
                int(item.get('Stock', 0)),
                float(descuento_valor)
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
            state.numero_propuesta,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            state.vendedor,
            state.cliente_actual.get(CLIENTE_NOMBRE_COL, ""),
            state.cliente_actual.get("NIF", ""),
            state.status,
            float(state.subtotal_bruto),
            float(state.descuento_total),
            float(state.total_general),
            float(state.costo_total),
            float(state.margen_absoluto),
            float(state.margen_porcentual),
            state.observaciones
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
                state.numero_propuesta,
                item.get('Referencia', ''),
                item.get('Producto', ''),
                int(item.get('Cantidad', 0)),
                float(item.get('Precio Unitario', 0)),
                float(item.get('Costo', 0)),
                float(item.get('Descuento (%)', 0)),
                float(item.get('Total', 0)),
                int(item.get('Stock', 0)),
                float(descuento_valor)
            ])
        if detalle_rows_nuevos:
            detalle_sheet.append_rows(detalle_rows_nuevos, value_input_option='USER_ENTERED')

        return True, f"Propuesta {state.numero_propuesta} actualizada con éxito."
    except Exception as e:
        return False, f"Error al actualizar la propuesta: {e}"

# --- NUEVA Y COMPLETA GENERACIÓN DE PDF ---
class PDF(FPDF):
    def header(self):
        # Este header se deja vacío porque el encabezado se construirá manualmente en la función principal
        pass

    def footer(self):
        # Pie de página complejo
        self.set_y(-45)
        self.set_font('Arial', 'B', 7)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 5, '', 'T', 1, 'C') # Línea superior del footer

        # Direcciones
        y_inicial_footer = self.get_y()
        self.set_font('Arial', 'B', 8)
        self.cell(45, 5, 'PEREIRA', 0, 0, 'C', True)
        self.cell(5, 5, '', 0, 0, 'C')
        self.cell(45, 5, 'DOSQUEBRADAS', 0, 0, 'C', True)
        self.cell(5, 5, '', 0, 0, 'C')
        self.cell(45, 5, 'ARMENIA', 0, 0, 'C', True)
        self.cell(5, 5, '', 0, 0, 'C')
        self.cell(40, 5, 'MANIZALES', 0, 1, 'C', True)
        
        self.set_y(y_inicial_footer + 5)
        self.set_font('Arial', '', 7)
        self.multi_cell(45, 3.5, 'CR 13 19-26 Parque Olaya\nP.B.X. (606) 333 0101 opcion 1\n310 830 5302', 0, 'C')
        self.set_y(y_inicial_footer + 5)
        self.set_x(60)
        self.multi_cell(45, 3.5, 'CR 10 17-56 Ópalo\nTel. (606) 322 3868\n310 856 1506', 0, 'C')
        self.set_y(y_inicial_footer + 5)
        self.set_x(110)
        self.multi_cell(45, 3.5, 'CR 19 11-05 San Francisco\nPBX. (606) 333 0101 opcion 3\n316 521 9904', 0, 'C')
        self.set_y(y_inicial_footer + 5)
        self.set_x(160)
        self.multi_cell(40, 3.5, 'CL 16 21-32 San Antonio\nPBX. (606) 333 0101 opcion 4\n313 608 6232', 0, 'C')

        self.set_y(y_inicial_footer + 17)
        self.set_font('Arial', 'I', 6)
        self.cell(45, 5, 'tiendopintucopereira@ferreinox.co', 0, 0, 'C')
        self.cell(5, 5, '', 0, 0, 'C')
        self.cell(45, 5, 'tiendapintucodosquebradas@ferreinox.co', 0, 0, 'C')
        self.cell(5, 5, '', 0, 0, 'C')
        self.cell(45, 5, 'tiendapintucoarmenio@ferreinox.co', 0, 0, 'C')
        self.cell(5, 5, '', 0, 0, 'C')
        self.cell(40, 5, 'tiendapintucomanizales@ferreinox.co', 0, 1, 'C')
        
        # Redes y página
        self.set_y(-15)
        self.set_font('Arial', 'B', 9)
        self.cell(95, 10, '@Ferreinox Tienda Pintuco', 0, 0, 'L')
        self.cell(0, 10, 'www.ferreinox.co', 0, 0, 'R')
        
        # Número de página
        self.set_y(-10)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_profesional(state, workbook):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(True, margin=50) # Margen inferior para el footer complejo

    # Encabezado Manual
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(63, 15, 'SOCIEDADES', 0, 0, 'C')
    # Aquí puedes añadir tus logos con pdf.image si los tienes
    # pdf.image('logo1.png', x, y, w)
    pdf.cell(63, 15, 'Ferreinox GBIC', 0, 0, 'C')
    pdf.cell(64, 15, 'EVOLUCIONANDO JUNTOS', 0, 1, 'C')
    pdf.ln(5)

    # Título principal
    pdf.set_font('Arial', 'B', 14)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 10, 'PROPUESTA COMERCIAL', 0, 1, 'C', True)
    pdf.ln(5)

    # Información Cliente y Propuesta
    y_bloques = pdf.get_y()
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(95, 5, 'CLIENTE', 'B', 1, 'L')
    pdf.set_font('Arial', '', 9)
    pdf.cell(20, 5, 'Nombre:', 0, 0, 'L')
    pdf.multi_cell(75, 5, str(state.cliente_actual.get(CLIENTE_NOMBRE_COL, '')), 0, 'L')
    pdf.cell(20, 5, 'NIF/C.C.:', 0, 0, 'L')
    pdf.cell(75, 5, str(state.cliente_actual.get('NIF', '')), 0, 1, 'L')
    pdf.cell(20, 5, 'Direccion:', 0, 0, 'L')
    pdf.cell(75, 5, str(state.cliente_actual.get('Dirección', '')), 0, 1, 'L')
    pdf.cell(20, 5, 'Telefono:', 0, 0, 'L')
    pdf.cell(75, 5, str(state.cliente_actual.get('Teléfono', '')), 0, 1, 'L')
    
    pdf.set_y(y_bloques)
    pdf.set_x(110)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(90, 5, 'DETALLES DE LA PROPUESTA', 'B', 1, 'L')
    pdf.set_x(110)
    pdf.set_font('Arial', '', 9)
    pdf.cell(35, 5, 'Propuesta #:', 0, 0, 'L')
    pdf.cell(55, 5, state.numero_propuesta, 0, 1, 'L')
    pdf.set_x(110)
    pdf.cell(35, 5, 'Fecha de Emision:', 0, 0, 'L')
    pdf.cell(55, 5, datetime.now().strftime('%d/%m/%Y'), 0, 1, 'L')
    pdf.set_x(110)
    pdf.cell(35, 5, 'Validez de la Oferta:', 0, 0, 'L')
    pdf.cell(55, 5, '15 dias', 0, 1, 'L')
    pdf.set_x(110)
    pdf.cell(35, 5, 'Asesor Comercial:', 0, 0, 'L')
    pdf.cell(55, 5, state.vendedor, 0, 1, 'L')
    pdf.ln(10)

    # Tabla de productos
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(20, 7, 'Ref.', 1, 0, 'C', True)
    pdf.cell(90, 7, 'Producto', 1, 0, 'C', True)
    pdf.cell(15, 7, 'Cant.', 1, 0, 'C', True)
    pdf.cell(25, 7, 'Precio U.', 1, 0, 'C', True)
    pdf.cell(15, 7, 'Desc.', 1, 0, 'C', True)
    pdf.cell(25, 7, 'Total', 1, 1, 'C', True)

    pdf.set_font('Arial', '', 8)
    for item in state.cotizacion_items:
        if item.get('Stock', 1) <= 0:
            pdf.set_text_color(255, 0, 0)
        
        # Manejo de caracteres para evitar errores en FPDF
        try:
            ref = str(item.get('Referencia', '')).encode('latin-1', 'replace').decode('latin-1')
            prod = str(item.get('Producto', '')).encode('latin-1', 'replace').decode('latin-1')
        except:
            ref = str(item.get('Referencia', ''))
            prod = str(item.get('Producto', ''))

        pdf.cell(20, 7, ref, 1, 0)
        pdf.cell(90, 7, prod, 1, 0)
        pdf.cell(15, 7, str(item.get('Cantidad', 0)), 1, 0, 'C')
        pdf.cell(25, 7, f"${item.get('Precio Unitario', 0):,.2f}", 1, 0, 'R')
        pdf.cell(15, 7, f"{item.get('Descuento (%)', 0):.1f}%", 1, 0, 'C')
        pdf.cell(25, 7, f"${item.get('Total', 0):,.2f}", 1, 1, 'R')
        pdf.set_text_color(0, 0, 0)

    # Bloque de Totales y Notas
    y_final_tabla = pdf.get_y()
    if y_final_tabla > 220: # Si la tabla es muy larga, pasa a la siguiente página
        pdf.add_page()
        y_final_tabla = pdf.get_y()

    pdf.set_y(y_final_tabla + 5)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(95, 5, 'Notas y Terminos:', 'B', 0, 'L')
    pdf.cell(95, 5, '', 0, 1, 'L')
    pdf.set_font('Arial', '', 8)
    pdf.multi_cell(95, 4, state.observaciones, 0, 'L')
    
    # Tabla de totales a la derecha
    base_gravable = state.subtotal_bruto - state.descuento_total
    pdf.set_y(y_final_tabla + 5)
    pdf.set_x(120)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, 7, 'Subtotal Bruto:', 1, 0, 'R')
    pdf.cell(40, 7, f'${state.subtotal_bruto:,.2f}', 1, 1, 'R')
    pdf.set_x(120)
    pdf.cell(40, 7, 'Descuento Total:', 1, 0, 'R')
    pdf.cell(40, 7, f'-${state.descuento_total:,.2f}', 1, 1, 'R')
    pdf.set_x(120)
    pdf.cell(40, 7, 'Base Gravable:', 1, 0, 'R')
    pdf.cell(40, 7, f'${base_gravable:,.2f}', 1, 1, 'R')
    pdf.set_x(120)
    pdf.cell(40, 7, f'IVA ({TASA_IVA:.0%}):', 1, 0, 'R')
    pdf.cell(40, 7, f'${state.iva_valor:,.2f}', 1, 1, 'R')
    pdf.set_x(120)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(40, 8, 'TOTAL A PAGAR:', 1, 0, 'R', True)
    pdf.cell(40, 8, f'${state.total_general:,.2f}', 1, 1, 'R', True)

    # Mensaje de advertencia
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 8)
    pdf.set_text_color(255, 0, 0)
    pdf.multi_cell(0, 5, "ADVERTENCIA: Productos sin stock pueden tener un tiempo de entrega mayor.", 0, 'C')
    pdf.set_text_color(0, 0, 0)

    # Salida segura del PDF
    try:
        buffer = BytesIO()
        pdf.output(buffer)
        return buffer.getvalue()
    except Exception as e:
        st.error(f"Error critico al generar el PDF: {e}")
        return None

def enviar_email_seguro(destinatario, state, pdf_bytes, nombre_archivo, is_copy=False):
    # (Esta función se mantiene igual)
    try:
        email_emisor = st.secrets["email"]["user"]
        password_emisor = st.secrets["email"]["password"]
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
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_emisor, password_emisor)
            server.send_message(msg)
        return True, "Correo enviado exitosamente."
    except Exception as e:
        return False, f"Error al enviar el correo: {e}"
