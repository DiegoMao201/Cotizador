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

# --- CONSTANTES (Ajusta según tu configuración) ---
LOGO_FILE_PATH = Path("logo.png")
TASA_IVA = 0.19

# --- Nombres de las hojas de cálculo ---
PROPUESTAS_SHEET_NAME = "Cotizaciones"
DETALLE_PROPUESTAS_SHEET_NAME = "Cotizaciones_Items"
PRODUCTOS_SHEET_NAME = "Productos"
CLIENTES_SHEET_NAME = "Clientes"

# --- Nombres de las columnas (Corregidos según tus datos) ---
# Hoja Clientes
CLIENTE_NOMBRE_COL = "Nombre"
CLIENTE_EMAIL_COL = "E-Mail"
# Hoja Productos
NOMBRE_PRODUCTO_COL = "Descripción"
STOCK_COL = "Stock"
# Listas de Precios de la hoja Productos
PRECIOS_COLS = [
    "Detallista 801 lista 2",
    "Publico 800 Lista 1",
    "Publico 345 Lista 1 complementarios",
    "Lista 346 Lista Complementarios",
    "Lista 100123 Construaliados"
]
# Hoja Cotizaciones
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
        
        if NOMBRE_PRODUCTO_COL not in df_productos.columns:
            st.error(f"Error Crítico: La columna '{NOMBRE_PRODUCTO_COL}' no existe en la hoja '{PRODUCTOS_SHEET_NAME}'.")
            return pd.DataFrame(), pd.DataFrame()
            
        df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos['Referencia'].astype(str) + ")"
        
        clientes_sheet = _workbook.worksheet(CLIENTES_SHEET_NAME)
        df_clientes = pd.DataFrame(clientes_sheet.get_all_records())
        return df_productos, df_clientes
    except gspread.exceptions.WorksheetNotFound as e:
        st.error(f"Error: No se encontró la hoja de cálculo '{e.worksheet_name}'. Revisa los nombres en utils.py.")
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Ocurrió un error al cargar los datos maestros: {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=60)
def listar_propuestas_df(_workbook):
    try:
        sheet = _workbook.worksheet(PROPUESTAS_SHEET_NAME)
        return pd.DataFrame(sheet.get_all_records())
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"No se encontró la hoja '{PROPUESTAS_SHEET_NAME}'. No se pueden listar propuestas.")
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
        # Forzar la recarga de los datos cacheados después de guardar
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
            state.numero_propuesta,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            state.vendedor,
            state.cliente_actual.get(CLIENTE_NOMBRE_COL, ""),
            state.cliente_actual.get("NIF", ""),
            state.status,
            state.subtotal_bruto,
            state.descuento_total,
            state.total_general,
            None, None, None,
            state.observaciones
        ]
        propuestas_sheet.append_row(propuesta_row, value_input_option='USER_ENTERED')

        detalle_rows = []
        for item in state.cotizacion_items:
            # CORREGIDO: Cálculo del valor del descuento
            descuento_valor = (item.get('Cantidad', 0) * item.get('Precio Unitario', 0)) * (item.get('Descuento (%)', 0) / 100)
            detalle_rows.append([
                state.numero_propuesta,
                item.get('Referencia', ''),
                item.get('Producto', ''),
                item.get('Cantidad', 0),
                item.get('Precio Unitario', 0),
                None,
                item.get('Descuento (%)', 0),
                item.get('Total', 0),
                item.get('Stock', 0),
                descuento_valor
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
            state.subtotal_bruto,
            state.descuento_total,
            state.total_general,
            None, None, None,
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
            # CORREGIDO: Cálculo del valor del descuento
            descuento_valor = (item.get('Cantidad', 0) * item.get('Precio Unitario', 0)) * (item.get('Descuento (%)', 0) / 100)
            detalle_rows_nuevos.append([
                state.numero_propuesta,
                item.get('Referencia', ''),
                item.get('Producto', ''),
                item.get('Cantidad', 0),
                item.get('Precio Unitario', 0),
                None,
                item.get('Descuento (%)', 0),
                item.get('Total', 0),
                item.get('Stock', 0),
                descuento_valor
            ])
        if detalle_rows_nuevos:
            detalle_sheet.append_rows(detalle_rows_nuevos, value_input_option='USER_ENTERED')

        return True, f"Propuesta {state.numero_propuesta} actualizada con éxito."
    except Exception as e:
        return False, f"Error al actualizar la propuesta: {e}"


# --- GENERACIÓN DE PDF ---
class PDF(FPDF):
    def header(self):
        if LOGO_FILE_PATH.exists():
            self.image(str(LOGO_FILE_PATH), 10, 8, 33)
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'Propuesta Comercial', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_profesional(state, workbook):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)

    pdf.cell(100, 10, f"Propuesta N°: {state.numero_propuesta}", 0, 0)
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%Y-%m-%d')}", 0, 1, 'R')
    pdf.cell(100, 10, f"Cliente: {state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'N/A')}", 0, 0)
    pdf.cell(0, 10, f"Vendedor: {state.vendedor}", 0, 1, 'R')
    pdf.cell(100, 10, f"Email: {state.cliente_actual.get(CLIENTE_EMAIL_COL, 'N/A')}", 0, 1)
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 10, 'Referencia', 1, 0, 'C')
    pdf.cell(75, 10, 'Producto', 1, 0, 'C')
    pdf.cell(20, 10, 'Cantidad', 1, 0, 'C')
    pdf.cell(25, 10, 'Vlr. Unitario', 1, 0, 'C')
    pdf.cell(15, 10, 'Desc.', 1, 0, 'C')
    pdf.cell(25, 10, 'Total', 1, 1, 'C')

    pdf.set_font('Arial', '', 9)
    productos_sin_stock = []
    for item in state.cotizacion_items:
        if item.get('Stock', 1) <= 0:
            pdf.set_text_color(255, 0, 0)
            productos_sin_stock.append(item.get('Producto'))
        
        pdf.cell(30, 10, str(item.get('Referencia', '')), 1, 0)
        pdf.cell(75, 10, str(item.get('Producto', '')), 1, 0)
        pdf.cell(20, 10, str(item.get('Cantidad', 0)), 1, 0, 'C')
        pdf.cell(25, 10, f"${item.get('Precio Unitario', 0):,.2f}", 1, 0, 'R')
        pdf.cell(15, 10, f"{item.get('Descuento (%)', 0):.1f}%", 1, 0, 'C')
        pdf.cell(25, 10, f"${item.get('Total', 0):,.2f}", 1, 1, 'R')

        pdf.set_text_color(0, 0, 0)

    pdf.ln(5)
    pdf.cell(130)
    pdf.cell(30, 8, 'Subtotal:', 1, 0)
    pdf.cell(30, 8, f"${state.subtotal_bruto:,.2f}", 1, 1, 'R')
    pdf.cell(130)
    pdf.cell(30, 8, 'Descuentos:', 1, 0)
    pdf.cell(30, 8, f"-${state.descuento_total:,.2f}", 1, 1, 'R')
    pdf.cell(130)
    pdf.cell(30, 8, f'IVA ({TASA_IVA:.0%}):', 1, 0)
    pdf.cell(30, 8, f"${state.iva_valor:,.2f}", 1, 1, 'R')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(130)
    pdf.cell(30, 8, 'TOTAL:', 1, 0)
    pdf.cell(30, 8, f"${state.total_general:,.2f}", 1, 1, 'R')
    pdf.ln(10)

    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, f"Observaciones: {state.observaciones}")
    
    if productos_sin_stock:
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, "ATENCIÓN: Los productos marcados en rojo no tienen stock disponible. La entrega dependerá de la importación.", 0, 1)
        pdf.set_text_color(0, 0, 0)

    # CORREGIDO: Se elimina .encode('latin-1') ya que pdf.output() devuelve bytes
    return pdf.output()

# --- ENVÍO DE EMAIL ---
def enviar_email_seguro(destinatario, state, pdf_bytes, nombre_archivo, is_copy=False):
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

        cuerpo_email = f"""
        Estimado/a {state.cliente_actual.get(CLIENTE_NOMBRE_COL)},

        Adjunto encontrará la propuesta comercial N° {state.numero_propuesta} que hemos preparado para usted.

        Quedamos a su disposición para cualquier consulta.

        Saludos cordiales,
        {state.vendedor}
        Ferreinox
        """
        msg.attach(MIMEText(cuerpo_email, 'plain'))

        adjunto = MIMEApplication(pdf_bytes, _subtype="pdf")
        adjunto.add_header('Content-Disposition', 'attachment', filename=nombre_archivo)
        msg.attach(adjunto)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_emisor, password_emisor)
            server.send_message(msg)
            
        return True, "Correo enviado exitosamente."
    except Exception as e:
        return False, f"Error al enviar el correo: {e}"
