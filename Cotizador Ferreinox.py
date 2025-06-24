import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Cotizador Avanzado - Ferreinox SAS",
    page_icon="🔩",
    layout="wide"
)

# --- ESTILOS Y DISEÑO ---
st.markdown("""
<style>
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        border: 1px solid #e6e6e6; border-radius: 10px; padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); background-color: #ffffff;
    }
    h2 { border-bottom: 2px solid #0A2540; padding-bottom: 5px; color: #0A2540; }
    .stButton>button {
        color: #ffffff; background-color: #0062df; border: none; border-radius: 5px;
        padding: 10px 20px; font-weight: bold; transition: background-color 0.3s ease;
    }
    .stButton>button:hover { background-color: #003d8a; }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DE NOMBRES Y ARCHIVOS ---
PRODUCTOS_FILE = 'lista_precios.xlsx'
CLIENTES_FILE = 'Clientes.xlsx'
LOGO_FILE = 'LOGO FERREINOX SAS BIC 2024.png'

# Columnas de productos
REFERENCIA_COL = 'Referencia'
NOMBRE_PRODUCTO_COL = 'Descripción'
DESC_ADICIONAL_COL = 'Descripción Adicional'
PRECIOS_COLS = [
    'Detallista 801 lista 2', 'Publico 800 Lista 1', 'Publico 345 Lista 1 complementarios',
    'Lista 346 Lista Complementarios', 'Lista 100123 Construaliados'
]
PRODUCTOS_COLS_REQUERIDAS = [REFERENCIA_COL, NOMBRE_PRODUCTO_COL, DESC_ADICIONAL_COL] + PRECIOS_COLS

# Columnas de clientes
CLIENTE_NOMBRE_COL = 'Nombre'
CLIENTE_NIT_COL = 'NIF'
CLIENTE_TEL_COL = 'Teléfono'
CLIENTE_DIR_COL = 'Dirección'
CLIENTES_COLS_REQUERIDAS = [CLIENTE_NOMBRE_COL, CLIENTE_NIT_COL, CLIENTE_TEL_COL, CLIENTE_DIR_COL]

# --- FUNCIONES AUXILIARES ---

@st.cache_data
def cargar_datos(archivo, columnas_num):
    if not os.path.exists(archivo): return None
    try:
        df = pd.read_excel(archivo)
        for col in columnas_num:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception: return None

def verificar_columnas(df, columnas_requeridas, nombre_archivo):
    if df is None: return False
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        st.error(f"Error en '{nombre_archivo}': Faltan las columnas: **{', '.join(faltantes)}**")
        return False
    return True

@st.cache_data
def get_image_as_base64(path):
    """Convierte una imagen local a base64 para incrustarla en HTML."""
    if not os.path.exists(path): return None
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

def generar_html_cotizacion(cliente, items_df, subtotal, descuento_valor, iva_valor, total_general, logo_base64):
    """Genera un string HTML profesional para la cotización."""
    fecha_actual = datetime.now().strftime("%d de %B de %Y")
    numero_cotizacion = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Construcción de la tabla de items en HTML
    items_html = ""
    for _, row in items_df.iterrows():
        items_html += f"""
        <tr>
            <td>{row['Referencia']}</td>
            <td>{row['Producto']}</td>
            <td>{row['Cantidad']}</td>
            <td>${row['Precio Unitario']:,.2f}</td>
            <td>${row['Total']:,.2f}</td>
        </tr>
        """
    # Plantilla HTML con estilos CSS incrustados
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; }}
            .invoice-box {{ max-width: 800px; margin: auto; padding: 30px; border: 1px solid #eee;
                           box-shadow: 0 0 10px rgba(0, 0, 0, .15); font-size: 16px; line-height: 24px; }}
            .invoice-box table {{ width: 100%; line-height: inherit; text-align: left; border-collapse: collapse; }}
            .invoice-box table td {{ padding: 5px; vertical-align: top; }}
            .invoice-box table tr.top table td {{ padding-bottom: 20px; }}
            .invoice-box table tr.top table td.title img {{ width: 100%; max-width: 200px; }}
            .invoice-box table tr.heading td {{ background: #eee; border-bottom: 1px solid #ddd; font-weight: bold; }}
            .invoice-box table tr.item td {{ border-bottom: 1px solid #eee; }}
            .invoice-box table tr.total td:nth-child(2) {{ border-top: 2px solid #eee; font-weight: bold; }}
            .text-right {{ text-align: right; }}
        </style>
    </head>
    <body>
        <div class="invoice-box">
            <table>
                <tr class="top">
                    <td colspan="5">
                        <table>
                            <tr>
                                <td class="title">
                                    {'<img src="data:image/png;base64,{logo_base64}">' if logo_base64 else '<h1>Ferreinox SAS</h1>'}
                                </td>
                                <td class="text-right">
                                    <b>Cotización #{numero_cotizacion}</b><br>
                                    Fecha: {fecha_actual}
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <tr>
                    <td colspan="5">
                        <b>Cliente:</b> {cliente.get(CLIENTE_NOMBRE_COL, 'N/A')}<br>
                        <b>NIF/C.C.:</b> {cliente.get(CLIENTE_NIT_COL, 'N/A')}<br>
                        <b>Dirección:</b> {cliente.get(CLIENTE_DIR_COL, 'N/A')}
                    </td>
                </tr>
                <tr class="heading">
                    <td>Referencia</td><td>Producto</td><td>Cant.</td><td class="text-right">Precio U.</td><td class="text-right">Total</td>
                </tr>
                {items_html}
            </table>
            <table style="margin-top: 20px;">
                <tr><td style="width: 70%;"></td><td class="text-right"><b>Subtotal:</b></td><td class="text-right">${subtotal:,.2f}</td></tr>
                <tr><td></td><td class="text-right"><b>Descuento:</b></td><td class="text-right">-${descuento_valor:,.2f}</td></tr>
                <tr><td></td><td class="text-right"><b>IVA (19%):</b></td><td class="text-right">${iva_valor:,.2f}</td></tr>
                <tr class="total"><td></td><td class="text-right"><b>Total General:</b></td><td class="text-right">${total_general:,.2f}</td></tr>
            </table>
        </div>
    </body>
    </html>
    """
    return html

# --- INICIALIZACIÓN Y CARGA DE DATOS ---
if 'cotizacion_items' not in st.session_state: st.session_state.cotizacion_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {}
if 'descuento_pct' not in st.session_state: st.session_state.descuento_pct = 0.0

df_productos = cargar_datos(PRODUCTOS_FILE, PRECIOS_COLS)
df_clientes = cargar_datos(CLIENTES_FILE, [])
logo_b64 = get_image_as_base64(LOGO_FILE)

if not verificar_columnas(df_productos, PRODUCTOS_COLS_REQUERIDAS, PRODUCTOS_FILE): st.stop()
if df_clientes is not None and not verificar_columnas(df_clientes, CLIENTES_COLS_REQUERIDAS, CLIENTES_FILE): st.stop()

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    if logo_b64: st.image(f"data:image/png;base64,{logo_b64}", use_column_width=True)
    st.title("⚙️ Opciones de Búsqueda")
    df_productos['Busqueda'] = df_productos[NOMBRE_PRODUCTO_COL].astype(str) + " " + df_productos[REFERENCIA_COL].astype(str)
    termino_busqueda_nombre = st.text_input(f"Buscar por '{NOMBRE_PRODUCTO_COL}' o '{REFERENCIA_COL}':")
    termino_busqueda_desc = st.text_input(f"Buscar por '{DESC_ADICIONAL_COL}':")

# --- FILTRADO DE DATOS ---
df_filtrado = df_productos.copy()
if termino_busqueda_nombre: df_filtrado = df_filtrado[df_filtrado['Busqueda'].str.contains(termino_busqueda_nombre, case=False, na=False)]
if termino_busqueda_desc: df_filtrado = df_filtrado[df_filtrado[DESC_ADICIONAL_COL].str.contains(termino_busqueda_desc, case=False, na=False)]

# --- CUERPO PRINCIPAL DE LA APLICACIÓN ---
st.title("🔩 Cotizador Avanzado Ferreinox SAS")

with st.container(border=True): # Cliente
    # ... (código de cliente sin cambios) ...
    st.header("👤 1. Datos del Cliente")
    tab_existente, tab_nuevo = st.tabs(["Seleccionar Cliente Existente", "Registrar Cliente Nuevo"])
    
    with tab_existente:
        if df_clientes is not None:
            lista_clientes = [""] + df_clientes[CLIENTE_NOMBRE_COL].tolist()
            cliente_sel_nombre = st.selectbox("Clientes guardados:", lista_clientes, help="Seleccione un cliente de la lista para cargar sus datos.", index=0)
            if cliente_sel_nombre:
                info_cliente = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_sel_nombre].iloc[0]
                st.session_state.cliente_actual = info_cliente.to_dict()
        else: st.info("No se cargó el archivo de clientes.")
    
    with tab_nuevo:
        with st.form("form_nuevo_cliente"):
            nombre_nuevo = st.text_input(f"{CLIENTE_NOMBRE_COL}*")
            nit_nuevo = st.text_input(CLIENTE_NIT_COL)
            tel_nuevo = st.text_input(CLIENTE_TEL_COL)
            dir_nueva = st.text_input(CLIENTE_DIR_COL)
            if st.form_submit_button("Usar este Cliente"):
                if not nombre_nuevo: st.warning("El nombre es obligatorio.")
                else:
                    st.session_state.cliente_actual = {
                        CLIENTE_NOMBRE_COL: nombre_nuevo, CLIENTE_NIT_COL: nit_nuevo,
                        CLIENTE_TEL_COL: tel_nuevo, CLIENTE_DIR_COL: dir_nueva
                    }
                    st.success(f"Cliente '{nombre_nuevo}' listo.")

with st.container(border=True): # Agregar Productos
    st.header("📦 2. Agregar Productos")
    col_prod, col_precio = st.columns([1.5, 1])

    with col_prod:
        if not df_filtrado.empty:
            producto_sel_str = st.selectbox("Resultados:", options=df_filtrado[NOMBRE_PRODUCTO_COL] + " (" + df_filtrado[REFERENCIA_COL].astype(str) + ")", index=None, placeholder="Escriba para buscar un producto...")
        else:
            st.warning("No se encontraron productos.")
            producto_sel_str = None

    # --- LÓGICA DE AGREGAR PRODUCTO (AHORA SEGURA) ---
    if producto_sel_str:
        nombre_real_prod = producto_sel_str.split(" (")[0]
        info_producto = df_productos[df_productos[NOMBRE_PRODUCTO_COL] == nombre_real_prod].iloc[0]
        with col_precio:
            opciones_precio = {f"{lista} - ${info_producto.get(lista, 0):,.2f}": (lista, info_producto.get(lista, 0)) for lista in PRECIOS_COLS}
            precio_sel_str = st.radio("Listas de precios:", options=opciones_precio.keys())
            col_cant, col_btn = st.columns([1, 2])
            with col_cant: cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1, label_visibility="collapsed")
            with col_btn:
                if st.button("➕ Agregar al Carrito", use_container_width=True):
                    lista_aplicada, precio_unitario = opciones_precio[precio_sel_str]
                    st.session_state.cotizacion_items.append({
                        "Referencia": info_producto[REFERENCIA_COL], "Producto": info_producto[NOMBRE_PRODUCTO_COL],
                        "Cantidad": cantidad, "Precio Unitario": precio_unitario, "Total": cantidad * precio_unitario
                    })
                    st.toast(f"✅ '{nombre_real_prod}' agregado!", icon="🛒")
                    st.rerun()

with st.container(border=True): # Cotización Final
    st.header("🛒 3. Cotización Final")
    if st.session_state.cliente_actual: st.info(f"**Cliente:** {st.session_state.cliente_actual.get(CLIENTE_NOMBRE_COL, 'N/A')}")
    else: st.warning("Seleccione un cliente para la cotización.")

    if not st.session_state.cotizacion_items:
        st.write("El carrito está vacío.")
    else:
        # --- EDITOR DE DATOS PARA MODIFICAR NOMBRES ---
        st.markdown("**Puede hacer doble clic en el nombre del producto para editarlo.**")
        edited_df = st.data_editor(
            pd.DataFrame(st.session_state.cotizacion_items),
            column_config={
                "Precio Unitario": st.column_config.NumberColumn(format="$ %(,.2f)"),
                "Total": st.column_config.NumberColumn(format="$ %(,.2f)"),
            },
            disabled=["Referencia", "Precio Unitario", "Total"], # Columnas no editables
            hide_index=True, use_container_width=True
        )
        # Actualizar el estado de sesión con los cambios del editor
        st.session_state.cotizacion_items = edited_df.to_dict('records')

        # --- CÁLCULOS DE TOTALES, DESCUENTO E IVA ---
        subtotal = sum(item['Total'] for item in st.session_state.cotizacion_items)
        
        st.subheader("Totales y Descuento")
        col_desc, col_totales = st.columns([1, 1.5])

        with col_desc:
            descuento_opciones = {f"{i}%": i/100.0 for i in range(16)} # Opciones de 0% a 15%
            st.session_state.descuento_pct = descuento_opciones[st.selectbox("Aplicar descuento:", options=descuento_opciones.keys())]

        with col_totales:
            descuento_valor = subtotal * st.session_state.descuento_pct
            subtotal_con_desc = subtotal - descuento_valor
            iva_valor = subtotal_con_desc * 0.19
            total_general = subtotal_con_desc + iva_valor

            st.markdown(f"""
            | Métrica | Valor |
            | :--- | ---: |
            | Subtotal | `${subtotal:,.2f}` |
            | Descuento ({st.session_state.descuento_pct:.0%}) | `- ${descuento_valor:,.2f}` |
            | **Base Gravable** | **`${subtotal_con_desc:,.2f}`** |
            | IVA (19%) | `${iva_valor:,.2f}` |
            | **Total General** | **`${total_general:,.2f}`** |
            """, unsafe_allow_html=True)

        st.divider()
        # --- ACCIONES DE LA COTIZACIÓN ---
        col_limpiar, col_descargar = st.columns(2)
        with col_limpiar:
            if st.button("🗑️ Vaciar Cotización", use_container_width=True, type="secondary"):
                st.session_state.cotizacion_items = []
                st.rerun()
        with col_descargar:
            html_content = generar_html_cotizacion(st.session_state.cliente_actual, edited_df, subtotal, descuento_valor, iva_valor, total_general, logo_b64)
            st.download_button(
                label="📄 Descargar Cotización Profesional",
                data=html_content,
                file_name=f"Cotizacion_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True, type="primary"
            )
