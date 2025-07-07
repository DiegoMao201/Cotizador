# pages/2_📊_Resumen_Comercial.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils import connect_to_gsheets, listar_propuestas_df, listar_detalle_propuestas_df

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Centro de Control Comercial", page_icon="🚀", layout="wide")
st.title("🚀 Centro de Control Comercial")
st.markdown("Análisis de rendimiento de ventas, márgenes y oportunidades.")

# --- CONEXIÓN Y CARGA DE DATOS ---
workbook = connect_to_gsheets()
if not workbook:
    st.error("La aplicación no puede continuar sin conexión a la base de datos.")
    st.stop()

@st.cache_data(ttl=300)
def cargar_y_preparar_datos():
    df_propuestas = listar_propuestas_df(workbook)
    df_items = listar_detalle_propuestas_df(workbook)
    
    if df_propuestas.empty or df_items.empty:
        return pd.DataFrame(), pd.DataFrame()

    # --- CAMBIO: LIMPIEZA DE DATOS MÁS ROBUSTA PARA EVITAR ERRORES DE FORMATO ---
    numeric_cols_prop = ['total_final', 'margen_absoluto', 'subtotal', 'descuento']
    for col in numeric_cols_prop:
        if col in df_propuestas.columns:
            # Forzar a string, limpiar caracteres no numéricos y luego convertir
            df_propuestas[col] = df_propuestas[col].astype(str).str.replace(r'[$,]', '', regex=True)
            df_propuestas[col] = pd.to_numeric(df_propuestas[col], errors='coerce').fillna(0)
        # No se muestra error si falta una columna no crítica para permitir flexibilidad
        elif col in ['total_final', 'margen_absoluto']:
             st.error(f"Error Crítico: La columna '{col}' no se encuentra en la hoja 'Cotizaciones'.")
             return pd.DataFrame(), pd.DataFrame()


    df_propuestas['fecha_creacion'] = pd.to_datetime(df_propuestas['fecha_creacion'], errors='coerce')
    df_propuestas = df_propuestas.dropna(subset=['fecha_creacion'])
    
    numeric_cols_items = ['Cantidad', 'Total_Item', 'Costo_Unitario', 'Precio_Unitario']
    for col in numeric_cols_items:
        if col in df_items.columns:
            df_items[col] = df_items[col].astype(str).str.replace(r'[$,]', '', regex=True)
            df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0)
        elif col in ['Cantidad', 'Total_Item']:
             st.error(f"Error Crítico: La columna '{col}' no se encuentra en la hoja 'Cotizaciones_Items'.")
             return pd.DataFrame(), pd.DataFrame()
             
    return df_propuestas, df_items

df_propuestas, df_items = cargar_y_preparar_datos()

if df_propuestas.empty:
    st.warning("No hay datos de propuestas para analizar o ocurrió un error al cargar.")
    st.stop()

# --- FILTROS GLOBALES EN LA BARRA LATERAL ---
st.sidebar.header("Filtros del Dashboard")
vendedores = ["Todos"] + sorted(df_propuestas['vendedor'].dropna().unique())
vendedor_sel = st.sidebar.selectbox("Vendedor", options=vendedores)

tiendas = ["Todas"] + sorted(df_propuestas[df_propuestas['tienda_despacho'] != '']['tienda_despacho'].dropna().unique())
tienda_sel = st.sidebar.selectbox("Tienda de Despacho", options=tiendas)


min_date = df_propuestas['fecha_creacion'].min().date()
max_date = df_propuestas['fecha_creacion'].max().date()

fecha_rango = st.sidebar.date_input(
    "Rango de Fechas",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    format="YYYY/MM/DD"
)

# Aplicar filtros
df_filtrado = df_propuestas.copy()
if len(fecha_rango) == 2:
    df_filtrado = df_filtrado[
        (df_filtrado['fecha_creacion'].dt.date >= fecha_rango[0]) &
        (df_filtrado['fecha_creacion'].dt.date <= fecha_rango[1])
    ]

if vendedor_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['vendedor'] == vendedor_sel]

if tienda_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado['tienda_despacho'] == tienda_sel]


propuestas_filtradas_ids = df_filtrado['numero_propuesta'].tolist()
df_items_filtrado = df_items[df_items['numero_propuesta'].isin(propuestas_filtradas_ids)]

# --- KPIs PRINCIPALES (MOVIDOS DEBAJO DE LOS FILTROS) ---
st.header("Indicadores Clave de Rendimiento (KPIs)")

if df_filtrado.empty:
    st.info("No hay datos que coincidan con los filtros seleccionados.")
else:
    total_cotizado = df_filtrado['total_final'].sum()
    margen_total = df_filtrado['margen_absoluto'].sum()
    num_propuestas = len(df_filtrado)

    df_aceptadas = df_filtrado[df_filtrado['status'] == 'Aceptada']
    ventas_cerradas = df_aceptadas['total_final'].sum()
    
    # --- NUEVO KPI: Tasa de Conversión ---
    tasa_conversion = (ventas_cerradas / total_cotizado) * 100 if total_cotizado > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Valor Total Cotizado", f"${total_cotizado:,.0f}")
    col2.metric("Ventas Cerradas", f"${ventas_cerradas:,.0f}")
    col3.metric("Tasa de Conversión", f"{tasa_conversion:.1f}%")
    col4.metric("Margen Bruto Total", f"${margen_total:,.0f}")
    col5.metric("N° de Cotizaciones", f"{num_propuestas}")

st.divider()

# --- PESTAÑAS DE ANÁLISIS ---
if not df_filtrado.empty:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Visión General", "👥 Por Vendedor", "🏪 Por Tienda", "📦 Top Productos", "🏢 Top Clientes"])

    with tab1:
        st.subheader("Estado y Evolución de las Propuestas")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            status_counts = df_filtrado['status'].value_counts()
            fig_status = px.donut(
                status_counts, values=status_counts.values, names=status_counts.index,
                title="Distribución de Estados", hole=0.4,
                color_discrete_map={'Aceptada': 'green', 'Enviada': 'orange', 'Borrador': 'grey', 'Rechazada': 'red'}
            )
            fig_status.update_traces(textinfo='percent+label', pull=[0.05, 0, 0, 0])
            st.plotly_chart(fig_status, use_container_width=True)

        with col2:
            df_filtrado['mes'] = df_filtrado['fecha_creacion'].dt.to_period('M').astype(str)
            evolucion = df_filtrado.groupby('mes').agg(
                Valor_Cotizado=('total_final', 'sum'),
                Ventas_Cerradas=('total_final', lambda x: x[df_filtrado.loc[x.index, 'status'] == 'Aceptada'].sum())
            ).reset_index()
            
            fig_evolucion = px.line(
                evolucion, x='mes', y=['Valor_Cotizado', 'Ventas_Cerradas'],
                title="Evolución de Valor Cotizado vs. Ventas Cerradas", markers=True,
                labels={'mes': 'Mes', 'value': 'Valor en $'},
            )
            st.plotly_chart(fig_evolucion, use_container_width=True)

    with tab2:
        st.subheader("Rendimiento por Vendedor")
        analisis_vendedor = df_filtrado.groupby('vendedor').agg(
            Valor_Cotizado=('total_final', 'sum'),
            Ventas_Cerradas=('total_final', lambda x: x[df_filtrado.loc[x.index, 'status'] == 'Aceptada'].sum()),
            Margen_Total=('margen_absoluto', 'sum'),
            Cotizaciones=('numero_propuesta', 'count')
        ).reset_index().sort_values('Valor_Cotizado', ascending=False)
        
        fig_vendedor = px.bar(
            analisis_vendedor, x='vendedor', y=['Valor_Cotizado', 'Ventas_Cerradas'],
            title="Valor Cotizado y Ventas por Vendedor", barmode='group',
            labels={'vendedor': 'Vendedor', 'value': 'Valor en $'}
        )
        st.plotly_chart(fig_vendedor, use_container_width=True)
        st.dataframe(analisis_vendedor, use_container_width=True, hide_index=True)

    # --- NUEVO: PESTAÑA DE ANÁLISIS POR TIENDA ---
    with tab3:
        st.subheader("Rendimiento por Tienda de Despacho")
        df_con_tienda = df_filtrado.dropna(subset=['tienda_despacho'])
        if not df_con_tienda.empty:
            analisis_tienda = df_con_tienda.groupby('tienda_despacho').agg(
                Valor_Cotizado=('total_final', 'sum'),
                Ventas_Cerradas=('total_final', lambda x: x[df_con_tienda.loc[x.index, 'status'] == 'Aceptada'].sum()),
                Cotizaciones=('numero_propuesta', 'count')
            ).reset_index().sort_values('Valor_Cotizado', ascending=False)
            
            fig_tienda = px.bar(
                analisis_tienda, x='tienda_despacho', y='Valor_Cotizado',
                title="Valor Total Cotizado por Tienda", color='tienda_despacho',
                labels={'tienda_despacho': 'Tienda', 'Valor_Cotizado': 'Valor Total en $'}
            )
            st.plotly_chart(fig_tienda, use_container_width=True)
            st.dataframe(analisis_tienda, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos con tienda de despacho asignada para los filtros seleccionados.")


    with tab4:
        st.subheader("Productos más Relevantes")
        if df_items_filtrado.empty:
            st.info("No hay items de productos para los filtros seleccionados.")
        else:
            top_productos_valor = df_items_filtrado.groupby('Producto')['Total_Item'].sum().nlargest(15).reset_index()
            fig_prod_valor = px.bar(
                top_productos_valor, x='Total_Item', y='Producto', orientation='h',
                title="Top 15 Productos por Valor Cotizado",
                labels={'Producto': '', 'Total_Item': 'Valor Total Cotizado'}
            ).update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_prod_valor, use_container_width=True)

    with tab5:
        st.subheader("Clientes más Importantes")
        top_clientes_valor = df_filtrado.groupby('cliente_nombre')['total_final'].sum().nlargest(15).reset_index()
        fig_cli_valor = px.bar(
            top_clientes_valor, x='total_final', y='cliente_nombre', orientation='h',
            title="Top 15 Clientes por Valor Cotizado",
            labels={'cliente_nombre': '', 'total_final': 'Valor Total Cotizado'}
        ).update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_cli_valor, use_container_width=True)

    # --- TABLA DE DETALLE AL FINAL DE LA PÁGINA ---
    st.divider()
    st.header("📄 Detalle de Propuestas Filtradas")
    with st.container(border=True):
        if not df_filtrado.empty:
            columnas_a_mostrar = {
                'numero_propuesta': 'N° Propuesta',
                'fecha_creacion': 'Fecha',
                'cliente_nombre': 'Cliente',
                'vendedor': 'Vendedor',
                'tienda_despacho': 'Tienda',
                'total_final': 'Valor Total',
                'margen_absoluto': 'Margen',
                'status': 'Estado'
            }
            columnas_existentes = [col for col in columnas_a_mostrar.keys() if col in df_filtrado.columns]
            df_display = df_filtrado[columnas_existentes].rename(columns=columnas_a_mostrar).sort_values(by='Fecha', ascending=False)
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Valor Total": st.column_config.NumberColumn(format="$ {:,.0f}"),
                    "Margen": st.column_config.NumberColumn(format="$ {:,.0f}"),
                    "Fecha": st.column_config.DateColumn(format="YYYY/MM/DD")
                }
            )
