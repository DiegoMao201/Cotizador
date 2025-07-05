import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from fpdf import FPDF
import warnings
from zoneinfo import ZoneInfo
import gspread
from gspread_dataframe import set_with_dataframe

# --- 0. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador Profesional - Ferreinox SAS BIC", page_icon="🔩", layout="wide")

# --- ESTILOS Y DISEÑO (Sin cambios) ---
st.markdown("""
<style>
    /* Estilos CSS (sin cambios) */
</style>
""")

# --- 1. CONFIGURACIÓN DE RUTAS, NOMBRES Y CONEXIÓN ---

# Nombres de archivos locales (para assets)
try: BASE_DIR = Path(__file__).resolve().parent
except NameError: BASE_DIR = Path.cwd()
LOGO_FILE_NAME = 'superior.png'; FOOTER_IMAGE_NAME = 'inferior.jpg'; FONT_FILE_NAME = 'DejaVuSans.ttf'
LOGO_FILE_PATH = BASE_DIR / LOGO_FILE_NAME; FOOTER_IMAGE_PATH = BASE_DIR / FOOTER_IMAGE_NAME; FONT_FILE_PATH = BASE_DIR / FONT_FILE_NAME

# Configuración de Google Sheets
GOOGLE_SHEET_NAME = "Productos" # Nombre del Libro de Cálculo

# Nombres de columnas clave
REFERENCIA_COL = 'Referencia'; NOMBRE_PRODUCTO_COL = 'Descripción'; COSTO_COL = 'Costo'
CLIENTE_NOMBRE_COL = 'Nombre'; CLIENTE_NIT_COL = 'NIF'; CLIENTE_TEL_COL = 'Teléfono'; CLIENTE_DIR_COL = 'Dirección'

@st.cache_resource
def connect_to_gsheets():
    """Establece conexión con Google Sheets usando los secretos de Streamlit."""
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        workbook = gc.open(GOOGLE_SHEET_NAME)
        return workbook
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}. Revisa la configuración de 'secrets.toml' y los permisos.")
        return None

# --- 2. CLASE PDF Y GENERACIÓN (Sin cambios lógicos) ---
class PDF(FPDF):
    # El código de la clase PDF no cambia.
    pass

def generar_pdf_profesional(cliente, items_df, subtotal, descuento_total, iva_valor, total_general, observaciones):
    # La lógica para generar el PDF no cambia.
    pass


# --- 3. FUNCIONES DE DATOS (LECTURA Y ESCRITURA EN GSHEETS) ---

@st.cache_data(ttl=300) # Cache de 5 minutos
def cargar_datos_maestros():
    """Carga los datos de Productos y Clientes desde Google Sheets."""
    workbook = connect_to_gsheets()
    if not workbook: return pd.DataFrame(), pd.DataFrame()
    try:
        prods_sheet = workbook.worksheet("Productos")
        df_productos = pd.DataFrame(prods_sheet.get_all_records())
        df_productos[REFERENCIA_COL] = df_productos[REFERENCIA_COL].astype(str).str.strip()
        df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " (" + df_productos[REFERENCIA_COL] + ")"
        df_productos.dropna(subset=[NOMBRE_PRODUCTO_COL, REFERENCIA_COL], inplace=True)
        
        clientes_sheet = workbook.worksheet("Clientes")
        df_clientes = pd.DataFrame(clientes_sheet.get_all_records())
        return df_productos, df_clientes
    except Exception as e:
        st.error(f"Error al cargar datos maestros: {e}")
        return pd.DataFrame(), pd.DataFrame()

def guardar_cliente_nuevo(nuevo_cliente_dict):
    """Guarda un nuevo cliente en la hoja de 'Clientes'."""
    # La lógica para guardar un cliente nuevo no cambia.
    pass

def guardar_propuesta_en_gsheets(status):
    """Guarda la propuesta actual, su estado y rentabilidad en Google Sheets."""
    workbook = connect_to_gsheets()
    if not workbook:
        st.error("No se pudo conectar a Google Sheets para guardar.")
        return

    prop_num = st.session_state.numero_propuesta
    items = st.session_state.cotizacion_items
    
    if not items:
        st.warning("No hay productos en la cotización para guardar.")
        return

    # Cálculos de rentabilidad
    subtotal_bruto = sum(item['Cantidad'] * item['Precio Unitario'] for item in items)
    descuento_total = sum((item['Cantidad'] * item['Precio Unitario']) * (item['Descuento (%)'] / 100.0) for item in items)
    base_gravable = subtotal_bruto - descuento_total
    iva_valor = base_gravable * 0.19
    total_general = base_gravable + iva_valor
    
    costo_total_items = sum(item['Cantidad'] * item.get('Costo_Unitario', 0) for item in items)
    margen_abs = base_gravable - costo_total_items
    margen_porc = (margen_abs / base_gravable) * 100 if base_gravable > 0 else 0

    # Fila para la hoja "Cotizaciones"
    header_data = [
        prop_num, datetime.now(ZoneInfo('America/Bogota')).isoformat(), st.session_state.get('vendedor', ''),
        st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, ''), st.session_state.cliente_actual.get(CLIENTE_NIT_COL, ''),
        status, subtotal_bruto, descuento_total, total_general,
        costo_total_items, margen_abs, margen_porc
    ]
    
    # Filas para la hoja "Cotizaciones_Items"
    items_data = []
    for item in items:
        items_data.append([
            prop_num, item['Referencia'], item['Producto'], item['Cantidad'],
            item['Precio Unitario'], item.get('Costo_Unitario', 0), 
            item['Descuento (%)'], item['Total']
        ])
        
    try:
        with st.spinner("Guardando en la nube..."):
            cot_sheet = workbook.worksheet("Cotizaciones")
            items_sheet = workbook.worksheet("Cotizaciones_Items")
            
            # Borrar registros antiguos para evitar duplicados al sobreescribir
            cell_list_cot = cot_sheet.findall(prop_num)
            if cell_list_cot: cot_sheet.delete_rows(cell_list_cot[0].row)
            
            cell_list_items = items_sheet.findall(prop_num)
            if cell_list_items:
                # Agrupamos por fila para borrar en un solo batch
                rows_to_delete = sorted([cell.row for cell in cell_list_items], reverse=True)
                for row_num in rows_to_delete:
                    # Hacemos un try/except por si la fila ya fue borrada en un batch anterior
                    try: items_sheet.delete_rows(row_num)
                    except: pass

            # Añadir nuevos registros
            cot_sheet.append_row(header_data)
            if items_data: items_sheet.append_rows(items_data, value_input_option='USER_ENTERED')
            
        st.toast(f"✅ Propuesta '{prop_num}' guardada en la nube con estado '{status}'.")
        st.cache_data.clear() # Limpia la caché para que la lista de propuestas se actualice
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")

@st.cache_data(ttl=60)
def listar_propuestas_guardadas():
    """Lee la hoja de Cotizaciones y devuelve una lista para el selectbox."""
    workbook = connect_to_gsheets()
    if not workbook: return []
    try:
        sheet = workbook.worksheet("Cotizaciones")
        records = sheet.get_all_records()
        propuestas = []
        for record in records:
            display_name = f"[{record.get('status', 'N/A')}] {record.get('numero_propuesta', 'S/N')} - {record.get('cliente_nombre', 'N/A')}"
            propuestas.append((display_name, record.get('numero_propuesta')))
        propuestas.sort(key=lambda x: x[1], reverse=True)
        return propuestas
    except Exception as e:
        return []

def cargar_propuesta_desde_gsheets(numero_propuesta):
    """Carga una propuesta y sus ítems desde Google Sheets."""
    workbook = connect_to_gsheets()
    if not workbook: return
    try:
        with st.spinner(f"Cargando propuesta {numero_propuesta}..."):
            # Cargar datos de la cabecera
            cot_sheet = workbook.worksheet("Cotizaciones")
            header_record = cot_sheet.find(numero_propuesta)
            if not header_record:
                st.error("No se encontró la propuesta."); return
            header_data = dict(zip(cot_sheet.row_values(1), cot_sheet.row_values(header_record.row)))

            # Cargar items
            items_sheet = workbook.worksheet("Cotizaciones_Items")
            all_items = items_sheet.get_all_records()
            items_propuesta = [item for item in all_items if item['numero_propuesta'] == numero_propuesta]

        # Poblar sesión
        st.session_state.numero_propuesta = header_data['numero_propuesta']
        st.session_state.vendedor = header_data.get('vendedor', '')
        st.session_state.cliente_actual = {
            CLIENTE_NOMBRE_COL: header_data.get('cliente_nombre'), CLIENTE_NIT_COL: header_data.get('cliente_nit'),
            CLIENTE_DIR_COL: '', CLIENTE_TEL_COL: ''
        }
        
        # Reconstruir los items para el estado de sesión
        recalculated_items = []
        for item_db in items_propuesta:
            total = (float(item_db['Cantidad']) * float(item_db['Precio_Unitario'])) * (1 - float(item_db['Descuento_Porc']) / 100.0)
            recalculated_items.append({
                "Referencia": item_db['Referencia'], "Producto": item_db['Producto'],
                "Cantidad": int(item_db['Cantidad']), "Precio Unitario": float(item_db['Precio_Unitario']),
                "Costo_Unitario": float(item_db['Costo_Unitario']), "Descuento (%)": float(item_db['Descuento_Porc']), 
                "Total": total, "Inventario": -1 # El inventario no se guarda, se consulta en vivo
            })
        st.session_state.cotizacion_items = recalculated_items

        st.toast(f"✅ Propuesta '{numero_propuesta}' cargada.")
        st.rerun()
    except Exception as e:
        st.error(f"Error al cargar desde Google Sheets: {e}")


# --- 4. INICIALIZACIÓN DE LA APLICACIÓN Y ESTADO DE SESIÓN ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
if 'numero_propuesta' not in st.session_state: st.session_state.numero_propuesta = f"PROP-{datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d-%H%M%S')}"
if 'observaciones' not in st.session_state: st.session_state.observaciones = "Forma de Pago: ...\nTiempos de Entrega: ...\nGarantía: ..."

# Carga de datos centralizada
df_productos, df_clientes = cargar_datos_maestros()


# --- 5. INTERFAZ DE USUARIO ---
st.title("🔩 Cotizador Profesional Ferreinox SAS BIC (Cloud)")

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image(str(LOGO_FILE_PATH), use_column_width=True) if LOGO_FILE_PATH.exists() else st.title("Ferreinox")
    st.title("⚙️ Controles")
    st.text_input("Vendedor/Asesor:", key="vendedor", placeholder="Tu nombre")
    st.divider()

    st.header("📂 Cargar Propuesta")
    propuestas_guardadas = listar_propuestas_guardadas()
    if not propuestas_guardadas:
        st.info("No hay propuestas guardadas en la nube.")
    else:
        opciones_propuestas = {display_name: file_name for display_name, file_name in propuestas_guardadas}
        propuesta_a_cargar_display = st.selectbox("Seleccionar propuesta:", options=[""] + list(opciones_propuestas.keys()), index=0)
        if st.button("Cargar Propuesta") and propuesta_a_cargar_display:
            propuesta_a_cargar_file = opciones_propuestas[propuesta_a_cargar_display]
            cargar_propuesta_desde_gsheets(propuesta_a_cargar_file)
    # ... (resto del sidebar como diagnóstico de archivos, etc.)

# --- CUERPO PRINCIPAL ---
termino_busqueda = st.text_input("Buscar Producto por Nombre o Referencia:", placeholder="Ej: 'Tornillo', 'Pintura', '102030'")
# (La lógica de filtrado inteligente va aquí...)

# Sección 1: Datos del Cliente
with st.container(border=True):
    st.header("👤 1. Datos del Cliente")
    # (El código de las tabs de cliente no cambia)

# Sección 2: Agregar Productos
with st.container(border=True):
    st.header("📦 2. Agregar Productos")
    if termino_busqueda:
        # Lógica de filtrado...
        pass
    
    # IMPORTANTE: Al agregar un producto, ahora también guardamos su costo
    # ...
    # if st.button("➕ Agregar a la Cotización", ...):
    #     info_producto = ...
    #     st.session_state.cotizacion_items.append({
    #         "Referencia": info_producto[REFERENCIA_COL], 
    #         "Producto": info_producto[NOMBRE_PRODUCTO_COL],
    #         # ... otros campos ...
    #         "Costo_Unitario": pd.to_numeric(info_producto.get(COSTO_COL, 0), errors='coerce'),
    #         "Inventario": pd.to_numeric(info_producto.get('Stock', 0), errors='coerce')
    #     })

# Sección 3: Resumen y Acciones
with st.container(border=True):
    st.header("🛒 3. Resumen y Generación de Propuesta")
    if not st.session_state.cotizacion_items:
        st.info("Añada productos para ver el resumen.")
    else:
        # El data editor y los cálculos de totales no cambian
        edited_df = st.data_editor(...)
        
        st.text_area("Observaciones y Términos:", key="observaciones", height=100)
        st.divider()
        st.subheader("Acciones de la Propuesta")

        # NUEVO: Selector de Estado y Botón de Guardado
        col_accion1, col_accion2 = st.columns([2,1])
        with col_accion1:
            status_actual = st.selectbox(
                "Establecer Estado de la Propuesta:",
                options=['Borrador', 'Enviada', 'Aprobada', 'Rechazada', 'Pedido para Logística'],
                help="Elige el estado antes de guardar. 'Pedido para Logística' es visible para el equipo de despachos."
            )
        with col_accion2:
            st.write("") # Espacio para alinear verticalmente el botón
            if st.button("💾 Guardar en la Nube", use_container_width=True, type="primary"):
                guardar_propuesta_en_gsheets(status_actual)

        st.divider()
        col_final1, col_final2 = st.columns(2)
        with col_final1:
            if st.button("🗑️ Vaciar Propuesta Actual", use_container_width=True):
                # Lógica para vaciar la propuesta...
                st.rerun()
        with col_final2:
            if st.session_state.get('cliente_actual'):
                # Lógica para generar y descargar el PDF...
                pass
            else:
                st.warning("Seleccione un cliente para generar el PDF.")
