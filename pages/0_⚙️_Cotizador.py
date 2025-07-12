# pages/0_⚙️_Cotizador.py
import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import dropbox
import io
import time
import re

# Importaciones de tus otros módulos (asegúrate de que existan)
from state import QuoteState
from utils import *

# --- INICIO: CONFIGURACIÓN PARA LA ACTUALIZACIÓN DE DATOS ---

# Nombre de tu libro de cálculo en Google Sheets
GOOGLE_SHEET_NAME = "Productos"
# Nombre de la hoja específica a actualizar
PRODUCTOS_SHEET_NAME = "Productos"

# Mapeo completo de los códigos de almacén a los nombres de columna deseados.
ALMACEN_NOMBRE_MAPPING = {
    '155': 'Stock CEDI',
    '156': 'Stock ARMENIA',
    '157': 'Stock Manizales',
    '158': 'Stock Opalo',
    '189': 'Stock Olaya',
    '238': 'Stock Laureles',
    '439': 'Stock FerreBox',
}

# --- FIN: CONFIGURACIÓN PARA LA ACTUALIZACIÓN DE DATOS ---


# --- INICIO: FUNCIONES PARA LA ACTUALIZACIÓN DE STOCK Y PRECIOS ---

def download_csv_from_dropbox() -> io.StringIO | None:
    """
    Se conecta a Dropbox usando los secretos de Streamlit, descarga el archivo CSV
    y lo devuelve como un objeto StringIO en memoria.
    """
    print("Intentando conectar y descargar desde Dropbox...")
    try:
        dbx_creds = st.secrets["dropbox"]
        # Usa el refresh_token para obtener un token de acceso de corta duración
        with dropbox.Dropbox(
            app_key=dbx_creds["app_key"],
            app_secret=dbx_creds["app_secret"],
            oauth2_refresh_token=dbx_creds["refresh_token"]
        ) as dbx:
            # Comprobar la conexión
            dbx.users_get_current_account()
            print("Conexión a Dropbox exitosa.")

            file_path = dbx_creds["file_path"]
            print(f"Descargando archivo: {file_path}")
            
            _, res = dbx.files_download(path=file_path)
            
            # El contenido está en bytes, lo decodificamos a string con la codificación correcta
            # y lo envolvemos en un StringIO para que pandas lo pueda leer como un archivo.
            content = res.content.decode('latin1')
            print(f"Archivo descargado exitosamente ({len(content)} bytes).")
            return io.StringIO(content)

    except dropbox.exceptions.AuthError as e:
        st.error(f"Error de autenticación con Dropbox. Revisa tus tokens. Detalle: {e}")
        print(f"Error de autenticación con Dropbox: {e}")
        return None
    except dropbox.exceptions.ApiError as e:
        st.error(f"No se pudo encontrar o acceder al archivo en Dropbox. Revisa la ruta '{st.secrets['dropbox']['file_path']}'. Detalle: {e}")
        print(f"Error de API de Dropbox: {e}")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error inesperado al conectar con Dropbox. Detalle: {e}")
        print(f"Error inesperado en Dropbox: {e}")
        return None


def run_stock_and_price_update(workbook: gspread.Spreadsheet) -> tuple[bool, str]:
    """
    Orquesta todo el proceso de actualización:
    1. Descarga el CSV de Dropbox.
    2. Procesa los datos con Pandas.
    3. Actualiza la hoja de Google Sheets.
    Devuelve un tuple (éxito, mensaje).
    """
    st.toast("Iniciando descarga de datos desde Dropbox...", icon="📦")
    csv_file_object = download_csv_from_dropbox()
    if not csv_file_object:
        return False, "Falló la descarga de datos desde Dropbox. No se pudo continuar."

    # 2. Definir nombres de columna y leer el archivo CSV en memoria
    nombres_columnas_csv = [
        'DEPARTAMENTO', 'REFERENCIA', 'DESCRIPCION', 'MARCA', 'PESO_ARTICULO',
        'UNIDADES_VENDIDAS', 'STOCK', 'COSTO_PROMEDIO_UND', 'CODALMACEN',
        'LEAD_TIME_PROVEEDOR', 'HISTORIAL_VENTAS'
    ]

    try:
        st.toast("Procesando archivo de datos...", icon="⚙️")
        print("Leyendo el archivo CSV desde el objeto en memoria...")
        df_crudo = pd.read_csv(
            csv_file_object,
            encoding='latin1',
            delimiter='|',
            header=None,
            names=nombres_columnas_csv,
            dtype={'REFERENCIA': str, 'CODALMACEN': str, 'STOCK': str, 'COSTO_PROMEDIO_UND': str}
        )
        df_crudo['CODALMACEN'] = df_crudo['CODALMACEN'].str.strip()
        print(f"Se encontraron {len(df_crudo)} registros en el archivo de datos.")
    except Exception as e:
        return False, f"ERROR: No se pudo leer el archivo CSV. Causa: {e}"

    # 3. Leer la hoja de Productos "maestra" actual de Google Sheets
    try:
        st.toast("Leyendo la hoja maestra de productos...", icon="📄")
        print(f"Leyendo la hoja maestra '{PRODUCTOS_SHEET_NAME}' desde Google Sheets...")
        productos_sheet = workbook.worksheet(PRODUCTOS_SHEET_NAME)
        df_productos_maestro = pd.DataFrame(productos_sheet.get_all_records(numericise_ignore=['all']))
        df_productos_maestro['Referencia'] = df_productos_maestro['Referencia'].astype(str).str.strip()
        print(f"Se encontraron {len(df_productos_maestro)} productos en la hoja maestra.")
    except gspread.exceptions.WorksheetNotFound:
        return False, f"ERROR: No se encontró la hoja llamada '{PRODUCTOS_SHEET_NAME}'."
    except Exception as e:
        return False, f"ERROR: No se pudo leer la hoja de productos maestra. Causa: {e}"

    # 4. Preparar y combinar la información
    print("Iniciando transformación de datos...")
    df_crudo['STOCK'] = pd.to_numeric(df_crudo['STOCK'], errors='coerce').fillna(0).astype(int)
    df_crudo['COSTO_PROMEDIO_UND'] = pd.to_numeric(df_crudo['COSTO_PROMEDIO_UND'], errors='coerce').fillna(0)
    df_crudo['VALOR_TOTAL_SKU'] = df_crudo['STOCK'] * df_crudo['COSTO_PROMEDIO_UND']

    df_costo_agregado = df_crudo.groupby('REFERENCIA').agg(
        Stock_Total=('STOCK', 'sum'),
        Valor_Total_Inventario=('VALOR_TOTAL_SKU', 'sum')
    ).reset_index()

    df_costo_agregado['Costo'] = df_costo_agregado['Valor_Total_Inventario'] / df_costo_agregado['Stock_Total']
    df_costo_agregado['Costo'].fillna(0, inplace=True)
    df_costo_agregado['Costo'] = df_costo_agregado['Costo'].astype(int)
    df_costo_agregado.rename(columns={'REFERENCIA': 'Referencia'}, inplace=True)

    df_crudo['NOMBRE_TIENDA'] = df_crudo['CODALMACEN'].map(ALMACEN_NOMBRE_MAPPING)
    df_crudo_mapeado = df_crudo.dropna(subset=['NOMBRE_TIENDA'])

    if not df_crudo_mapeado.empty:
        df_stock_por_tienda = df_crudo_mapeado.pivot_table(
            index='REFERENCIA', columns='NOMBRE_TIENDA', values='STOCK',
            aggfunc='sum', fill_value=0
        ).reset_index()
        df_stock_por_tienda.rename(columns={'REFERENCIA': 'Referencia'}, inplace=True)
    else:
        df_stock_por_tienda = pd.DataFrame(columns=['Referencia'])

    columnas_a_eliminar = ['Costo'] + list(ALMACEN_NOMBRE_MAPPING.values())
    df_maestro_base = df_productos_maestro.drop(columns=columnas_a_eliminar, errors='ignore')

    df_actualizado = pd.merge(df_maestro_base, df_costo_agregado[['Referencia', 'Costo']], on='Referencia', how='left')
    df_actualizado = pd.merge(df_actualizado, df_stock_por_tienda, on='Referencia', how='left')

    columnas_posibles_stock = list(ALMACEN_NOMBRE_MAPPING.values())
    columnas_existentes_stock = [col for col in columnas_posibles_stock if col in df_actualizado.columns]

    if columnas_existentes_stock:
        df_actualizado[columnas_existentes_stock] = df_actualizado[columnas_existentes_stock].fillna(0).astype(int)
    
    df_actualizado['Costo'] = df_actualizado['Costo'].fillna(0).astype(int)
    print("Datos combinados y listos para subir.")

    # 5. Escribir el DataFrame final de vuelta a Google Sheets
    try:
        st.toast("Actualizando base de datos en la nube... ¡Casi listo!", icon="☁️")
        print(f"Actualizando la hoja '{PRODUCTOS_SHEET_NAME}' en Google Sheets...")
        productos_sheet.clear()
        set_with_dataframe(productos_sheet, df_actualizado, include_index=False, resize=True, allow_formulas=False)
        print("--- ✅ ¡Actualización completada exitosamente! ---")
        return True, "¡Éxito! Los precios y stocks han sido actualizados."
    except Exception as e:
        return False, f"ERROR: No se pudo escribir en Google Sheets. Causa: {e}"


# --- FIN: FUNCIONES PARA LA ACTUALIZACIÓN DE STOCK Y PRECIOS ---


# --- INICIO: CÓDIGO ORIGINAL DEL COTIZADOR ---

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide", page_title="Cotizador Profesional")

# =============================================================================
# --- INYECCIÓN DE ESTILO (CSS) PARA UN LOOK PROFESIONAL ---
# =============================================================================
st.markdown("""
<style>
    /* Fuente principal y color de fondo */
    body {
        font-family: 'Inter', sans-serif;
    }

    /* Estilo de los contenedores principales */
    .st-emotion-cache-183lzff {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    /* Estilo para los encabezados de sección */
    .section-header {
        font-size: 24px;
        font-weight: 600;
        color: #003366; /* Azul corporativo */
        border-bottom: 2px solid #003366;
        padding-bottom: 10px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    
    /* Mejoras en los botones */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #003366;
        color: #003366;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #003366;
        color: white;
        border: 1px solid #003366;
    }
    
    /* Botón primario (Agregar, Guardar, etc.) */
    .stButton>button[data-testid="baseButton-primary"] {
        background-color: #ff4b4b; /* Rojo para acciones primarias */
        color: white;
        border: none;
    }
    .stButton>button[data-testid="baseButton-primary"]:hover {
        background-color: #cc0000;
    }

</style>
""", unsafe_allow_html=True)


# --- TÍTULO Y CARGA DE DATOS ---
st.title("🔩 Cotizador Profesional Ferreinox")
st.markdown("Herramienta de alta eficiencia para la creación y gestión de propuestas comerciales.")

# Conexión principal a Google Sheets (usada por todo el cotizador)
workbook = connect_to_gsheets()
if not workbook:
    st.error("La aplicación no puede continuar sin conexión a la base de datos.")
    st.stop()

# Inicialización del estado de la cotización
if 'state' not in st.session_state:
    st.session_state.state = QuoteState()
state = st.session_state.state

# --- ESTADOS PARA LA BÚSQUEDA ---
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'selected_product_string' not in st.session_state:
    st.session_state.selected_product_string = None


# --- Lógica para cargar cotizaciones ---
if st.session_state.get('load_quote'):
    numero_a_cargar = st.session_state.pop('load_quote')
    state.cargar_desde_gheets(numero_a_cargar, workbook)
    st.rerun()

# --- BARRA LATERAL DE CONTROLES ---
with st.sidebar:
    st.title("⚙️ Controles")
    if state.numero_propuesta and "TEMP" not in state.numero_propuesta:
        st.info(f"✍️ **Modo Edición:**\nCotización **{state.numero_propuesta}**.")
    else:
        st.info("✨ **Modo Creación:**\nEstás creando una cotización nueva.")
    
    def actualizar_vendedor():
        state.set_vendedor(st.session_state.vendedor_input)
    st.text_input(
        "Vendedor/Asesor:", value=state.vendedor,
        placeholder="Tu nombre", on_change=actualizar_vendedor, key="vendedor_input"
    )
    st.button("🗑️ Iniciar Cotización Nueva", use_container_width=True, on_click=state.reiniciar_cotizacion)
    st.divider()

    # --- INICIO: SECCIÓN DE ADMINISTRACIÓN CON EL BOTÓN DE ACTUALIZACIÓN ---
    st.markdown("#### 🗂️ Administración")
    if st.button("🔄 Actualizar Precios y Stocks", use_container_width=True, help="Sincroniza los datos de productos desde Dropbox a la base de datos en la nube."):
        with st.spinner("Iniciando actualización completa... Este proceso puede tardar unos segundos. Por favor, espera."):
            success, message = run_stock_and_price_update(workbook)
        
        if success:
            st.success(message)
            time.sleep(2)  # Pausa para que el usuario lea el mensaje
            st.cache_data.clear()  # Limpia la caché para forzar la recarga de datos
            st.rerun()
        else:
            st.error(message)
    # --- FIN: SECCIÓN DE ADMINISTRACIÓN ---

# Carga de datos maestros (ahora se benefician de la limpieza de caché)
df_productos, df_clientes = cargar_datos_maestros(workbook)

# --- PASO 1: CLIENTE ---
st.markdown("<h2 class='section-header'>👤 1. Datos del Cliente</h2>", unsafe_allow_html=True)
with st.container(border=True):
    if df_clientes.empty:
        st.warning("No hay clientes en la base de datos.")
    else:
        lista_clientes = [""] + sorted(df_clientes[CLIENTE_NOMBRE_COL].dropna().astype(str).unique().tolist())
        current_client_name = state.cliente_actual.get(CLIENTE_NOMBRE_COL, "")
        try:
            idx = lista_clientes.index(current_client_name) if current_client_name else 0
        except ValueError:
            idx = 0
        cliente_sel_nombre = st.selectbox("Selecciona un cliente existente:", options=lista_clientes, index=idx)
        if cliente_sel_nombre and cliente_sel_nombre != current_client_name:
            cliente_dict = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0].to_dict()
            state.set_cliente(cliente_dict)
            st.rerun()
    if state.cliente_actual:
        st.success(f"Cliente seleccionado: **{state.cliente_actual.get(CLIENTE_NOMBRE_COL, '')}**")
        
    with st.expander("➕ Crear un nuevo cliente"):
        with st.form("nuevo_cliente_form", clear_on_submit=True):
            st.markdown("###### Ingresa los datos del nuevo cliente")
            nombre = st.text_input("Nombre del Cliente*", placeholder="Ej: Ferretería El Martillo Feliz")
            nif = st.text_input("NIF/C.C.*", placeholder="Ej: 900.123.456-7")
            email = st.text_input("E-Mail", placeholder="Ej: compras@ferreteria.com")
            telefono = st.text_input("Teléfono", placeholder="Ej: 3101234567")
            direccion = st.text_input("Dirección", placeholder="Ej: Cra 10 # 5-20")
            
            submitted = st.form_submit_button("Crear Cliente", use_container_width=True)
            if submitted:
                with st.spinner("Guardando cliente..."):
                    exito, mensaje = crear_nuevo_cliente(
                        workbook,
                        nombre=nombre, nif=nif, email=email,
                        telefono=telefono, direccion=direccion
                    )
                if exito:
                    st.success(mensaje)
                    st.cache_data.clear()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(mensaje)


# --- PASO 2: TIENDA ---
st.markdown("<h2 class='section-header'>🏬 2. Tienda de Despacho</h2>", unsafe_allow_html=True)
with st.container(border=True):
    lista_tiendas = get_tiendas_from_df(df_productos)
    if not lista_tiendas:
        st.error("No se pudieron detectar las tiendas desde la base de datos.")
    else:
        try:
            idx_tienda = lista_tiendas.index(state.tienda_despacho) if state.tienda_despacho else 0
        except ValueError:
            idx_tienda = 0
        tienda_seleccionada = st.selectbox(
            "Selecciona la tienda para consultar stock y despachar:",
            options=lista_tiendas, index=idx_tienda,
            placeholder="Elige una tienda..."
        )
        if tienda_seleccionada and tienda_seleccionada != state.tienda_despacho:
            state.set_tienda(tienda_seleccionada)
            st.rerun()
    if state.tienda_despacho:
        st.success(f"Tienda para despacho: **{state.tienda_despacho}**")
    else:
        st.warning("Debes seleccionar una tienda para poder agregar productos.")

# ==============================================================================
# --- PASO 3: BUSCADOR DE PRODUCTOS CON BOTÓN DE LIMPIEZA ---
# ==============================================================================
st.markdown("<h2 class='section-header'>📦 3. Agregar Productos</h2>", unsafe_allow_html=True)
with st.container(border=True):
    if df_productos.empty:
        st.warning("No hay productos en la base de datos para seleccionar.")
    else:
        col_search, col_clear, col_filters = st.columns([6, 1, 5])
        with col_search:
            st.session_state.search_query = st.text_input(
                "**Buscar productos:**", value=st.session_state.search_query,
                placeholder="Ej: viniltex blanco galon", label_visibility="collapsed"
            )
        with col_clear:
            st.write("")
            st.write("")
            if st.button("✖️", help="Limpiar búsqueda"):
                st.session_state.search_query = ""
                st.rerun()
        with col_filters:
            lista_categorias = ["Todas"]
            if 'Categoria' in df_productos.columns:
                lista_categorias += sorted(df_productos['Categoria'].dropna().unique().tolist())
            categoria_seleccionada = st.selectbox(
                "**Filtrar por categoría:**", options=lista_categorias, label_visibility="collapsed"
            )

        resultados = buscar_productos_inteligentemente(
            st.session_state.search_query, df_productos, categoria_seleccionada
        )

        producto_seleccionado = None
        if not resultados.empty:
            options_dict = {"-- Elige un producto de los resultados --": None}
            # La columna de stock ahora se llama 'Stock ' + nombre de tienda, ej: 'Stock CEDI'
            stock_col_name = state.tienda_despacho
            
            for _, row in resultados.head(50).iterrows():
                stock_disponible = row.get(stock_col_name, 0)
                option_string = f"{row[NOMBRE_PRODUCTO_COL]} | Ref: {row['Referencia']} | Stock: {stock_disponible}"
                options_dict[option_string] = row['Referencia']

            selected_option = st.selectbox(
                f"**Resultados de la búsqueda ({len(resultados)} encontrados):**",
                options=list(options_dict.keys()), index=0, key="results_selectbox"
            )
            
            selected_ref = options_dict[selected_option]
            if selected_ref:
                producto_seleccionado_df = resultados[resultados['Referencia'] == selected_ref]
                if not producto_seleccionado_df.empty:
                    producto_seleccionado = producto_seleccionado_df.iloc[0]

        elif st.session_state.search_query:
            st.warning("No se encontraron productos para tu búsqueda.")
        else:
            st.info("Utiliza el buscador y los filtros para encontrar productos.")
        
        st.divider()

        if producto_seleccionado is not None:
            st.markdown(f"#### Producto Seleccionado")
            
            opciones_precio = {}
            for col_name in PRECIOS_COLS:
                raw_price = producto_seleccionado.get(col_name)
                parsed_price = parse_price(raw_price)
                if parsed_price > 0:
                    opciones_precio[col_name] = parsed_price

            col_info, col_actions = st.columns([3, 2])
            with col_info:
                st.markdown(f"**{producto_seleccionado[NOMBRE_PRODUCTO_COL]}**")
                st.caption(f"Referencia: {producto_seleccionado['Referencia']}")
            
            with col_actions:
                if not opciones_precio:
                    st.error("Este producto no tiene precios definidos.")
                else:
                    precio_sel_str = st.radio(
                        "Lista de Precio:", options=opciones_precio.keys(),
                        format_func=lambda key: f"{key}: ${opciones_precio[key]:,.2f}",
                        horizontal=True, key=f"price_{producto_seleccionado['Referencia']}"
                    )
                    cantidad = st.number_input(
                        "Cantidad:", min_value=1, value=1, step=1,
                        key=f"qty_{producto_seleccionado['Referencia']}"
                    )
                    if st.button("➕ Agregar a la Cotización", type="primary", use_container_width=True, disabled=not state.tienda_despacho):
                        state.agregar_item(producto_seleccionado.to_dict(), cantidad, opciones_precio[precio_sel_str])
                        st.toast(f"✅ Añadido: {producto_seleccionado[NOMBRE_PRODUCTO_COL]}", icon="🎉")
                        time.sleep(1)
                        st.rerun()

# ==============================================================================
# --- PASO 4: RESUMEN Y GENERACIÓN ---
# ==============================================================================
st.markdown("<h2 class='section-header'>📝 4. Resumen y Generación</h2>", unsafe_allow_html=True)
with st.container(border=True):
    if not state.cotizacion_items:
        st.info("Cuando agregues productos, aparecerán aquí para que puedas editar las cantidades, precios y descuentos.")
    else:
        st.markdown("#### Items de la Cotización")
        df_items = pd.DataFrame(state.cotizacion_items)
        columnas_visibles = ['Referencia', 'Producto', 'Cantidad', 'Precio Unitario', 'Descuento (%)', 'Total']
        df_display = df_items[columnas_visibles]

        edited_df = st.data_editor(
            df_display,
            column_config={
                "Referencia": st.column_config.TextColumn(disabled=True),
                "Producto": st.column_config.TextColumn(label="Descripción", width="large", required=True),
                "Cantidad": st.column_config.NumberColumn(label="Cant.", required=True, min_value=1),
                "Precio Unitario": st.column_config.NumberColumn(label="Vlr. Unitario", format="$%.2f", required=True),
                "Descuento (%)": st.column_config.NumberColumn(label="Desc. %", min_value=0, max_value=100, step=1, format="%.1f%%", required=True),
                "Total": st.column_config.NumberColumn(label="Total", format="$%.2f", disabled=True),
            },
            use_container_width=True, hide_index=True, num_rows="dynamic", key="data_editor_items")
        
        if edited_df.to_dict('records') != df_display.to_dict('records'):
            state.actualizar_items_desde_vista(edited_df)
            st.rerun()

        st.divider()
        st.markdown("#### Resumen Financiero")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Subtotal Bruto", f"${state.subtotal_bruto:,.2f}")
        m2.metric("Descuento Total", f"-${state.descuento_total:,.2f}")
        m3.metric(f"IVA ({TASA_IVA:.0%})", f"${state.iva_valor:,.2f}")
        m4.metric("TOTAL GENERAL", f"${state.total_general:,.2f}")

        st.divider()
        st.markdown("#### Observaciones y Estado")
        col_obs, col_status = st.columns(2)
        with col_obs:
            state.observaciones = st.text_area("Observaciones y Términos:", value=state.observaciones, height=120, on_change=state.persist_to_session)
        with col_status:
            idx_status = ESTADOS_COTIZACION.index(state.status) if state.status in ESTADOS_COTIZACION else 0
            state.status = st.selectbox("Establecer Estado de la Propuesta:", options=ESTADOS_COTIZACION, index=idx_status, on_change=state.persist_to_session)

        if state.cliente_actual:
            st.divider()
            st.subheader("Acciones Finales")
            col_accion1, col_accion2 = st.columns([2, 1])
            col_accion2.button("💾 Guardar Cambios en la Nube", use_container_width=True, type="primary", on_click=handle_save, args=(workbook, state))

            pdf_bytes = generar_pdf_profesional(state, workbook)
            pdf_prefix = "Pedido" if state.status == "Aceptada" else "Propuesta"
            nombre_archivo_pdf = f"{pdf_prefix}_{state.numero_propuesta.replace('TEMP-', 'BORRADOR-')}.pdf"

            st.divider()
            st.subheader("Documento y Envío por Correo")
            col_pdf, col_email = st.columns(2)

            col_pdf.download_button(
                label="📄 Descargar PDF", data=pdf_bytes,
                file_name=nombre_archivo_pdf, mime="application/pdf", use_container_width=True,
                disabled=(pdf_bytes is None)
            )
            with col_email:
                email_cliente = st.text_input("Enviar a:", value=state.cliente_actual.get(CLIENTE_EMAIL_COL, ""))
                if st.button("📧 Enviar por Email", use_container_width=True, disabled=(pdf_bytes is None)):
                    if email_cliente:
                        with st.spinner("Enviando correo..."):
                            exito, mensaje = enviar_email_seguro(email_cliente, state, pdf_bytes, nombre_archivo_pdf)
                            if exito: st.success(mensaje)
                            else: st.error(mensaje)
                    else:
                        st.warning("Por favor, ingrese un correo electrónico de destino.")

            st.divider()
            st.subheader("Compartir por WhatsApp")

            telefono_cliente = st.text_input(
                "Teléfono del Cliente:",
                value=state.cliente_actual.get("Teléfono", "")
            )
            
            if st.button("🚀 Preparar y Compartir por WhatsApp", use_container_width=True, type="primary", disabled=(not telefono_cliente or pdf_bytes is None)):
                with st.spinner("Subiendo PDF y preparando mensaje..."):
                    exito_drive, resultado_drive = guardar_pdf_en_drive(workbook, pdf_bytes, nombre_archivo_pdf)
                    if exito_drive:
                        file_id = resultado_drive
                        link_pdf_publico = f"https://drive.google.com/file/d/{file_id}/view"
                        whatsapp_html = generar_boton_whatsapp(state, telefono_cliente, link_pdf_publico)
                        st.markdown(whatsapp_html, unsafe_allow_html=True)
                    else:
                        st.error(resultado_drive)
# --- FIN: CÓDIGO ORIGINAL DEL COTIZADOR ---
