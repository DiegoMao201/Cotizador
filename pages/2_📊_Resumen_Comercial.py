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

    numeric_cols_prop = ['total_final', 'margen_absoluto', 'subtotal', 'descuento', 'margen_porcentual']
    for col in numeric_cols_prop:
        if col in df_propuestas.columns:
            df_propuestas[col] = df_propuestas[col].astype(str).str.replace(r'[$,%]', '', regex=True)
            df_propuestas[col] = pd.to_numeric(df_propuestas[col], errors='coerce').fillna(0)
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

# --- KPIs PRINCIPALES ---
st.header("Indicadores Clave de Rendimiento (KPIs)")

if df_filtrado.empty:
    st.info("No hay datos que coincidan con los filtros seleccionados.")
else:
    total_cotizado = df_filtrado['total_final'].sum()
    margen_total = df_filtrado['margen_absoluto'].sum()
    num_propuestas = len(df_filtrado)

    df_aceptadas = df_filtrado[df_filtrado['status'] == 'Aceptada']
    ventas_cerradas = df_aceptadas['total_final'].sum()
    
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
            fig_status = px.pie(
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

    with tab3:
        st.subheader("Rendimiento por Tienda de Despacho")
        df_con_tienda = df_filtrado.dropna(subset=['tienda_despacho'])
        if not df_con_tienda.empty and 'tienda_despacho' in df_con_tienda.columns and df_con_tienda['tienda_despacho'].str.strip().astype(bool).any():
            analisis_tienda = df_con_tienda[df_con_tienda['tienda_despacho'] != ''].groupby('tienda_despacho').agg(
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
        st.subheader("Análisis de Rendimiento de Productos")
        if df_items_filtrado.empty:
            st.info("No hay items de productos para los filtros seleccionados.")
        else:
            df_propuestas_reducido = df_filtrado[['numero_propuesta', 'margen_absoluto', 'total_final']].copy()
            df_propuestas_reducido['margen_porc_propuesta'] = (df_propuestas_reducido['margen_absoluto'] / df_propuestas_reducido['total_final']).fillna(0)
            
            df_items_enriquecido = pd.merge(df_items_filtrado, df_propuestas_reducido[['numero_propuesta', 'margen_porc_propuesta']], on='numero_propuesta', how='left')
            df_items_enriquecido['margen_estimado_item'] = df_items_enriquecido['Total_Item'] * df_items_enriquecido['margen_porc_propuesta']

            analisis_productos = df_items_enriquecido.groupby('Producto').agg(
                Valor_Cotizado=('Total_Item', 'sum'),
                Unidades_Cotizadas=('Cantidad', 'sum'),
                Margen_Estimado=('margen_estimado_item', 'sum'),
                Num_Cotizaciones=('numero_propuesta', 'nunique')
            ).reset_index()
            
            st.markdown("##### Insights Clave de Productos")
            col1, col2, col3 = st.columns(3)
            if not analisis_productos.empty:
                with col1:
                    producto_estrella = analisis_productos.loc[analisis_productos['Margen_Estimado'].idxmax()]
                    st.markdown("**⭐ Producto Estrella (Más Rentable)**")
                    st.caption(producto_estrella['Producto'])
                    st.metric(label="Margen Estimado", value=f"${producto_estrella['Margen_Estimado']:,.0f}")
                
                with col2:
                    caballo_batalla = analisis_productos.loc[analisis_productos['Unidades_Cotizadas'].idxmax()]
                    st.markdown("**🐎 Caballo de Batalla (Más Cotizado)**")
                    st.caption(caballo_batalla['Producto'])
                    st.metric(label="Unidades Cotizadas", value=f"{caballo_batalla['Unidades_Cotizadas']:,.0f}")

                with col3:
                    mas_popular = analisis_productos.loc[analisis_productos['Num_Cotizaciones'].idxmax()]
                    st.markdown("**🔥 Más Popular (En más cotizaciones)**")
                    st.caption(mas_popular['Producto'])
                    st.metric(label="Apariciones", value=f"{mas_popular['Num_Cotizaciones']}")
            st.divider()

            st.markdown("##### Tabla de Análisis de Productos")
            # --- CAMBIO: Se elimina column_config para asegurar la visualización de los valores ---
            st.dataframe(
                analisis_productos.sort_values(by="Valor_Cotizado", ascending=False),
                use_container_width=True, 
                hide_index=True
            )

    with tab5:
        st.subheader("Análisis de Comportamiento de Clientes")
        analisis_clientes = df_filtrado.groupby('cliente_nombre').agg(
            Valor_Cotizado=('total_final', 'sum'),
            Ventas_Cerradas=('total_final', lambda x: x[df_filtrado.loc[x.index, 'status'] == 'Aceptada'].sum()),
            Margen_Total=('margen_absoluto', 'sum'),
            Num_Cotizaciones=('numero_propuesta', 'count')
        ).reset_index()

        analisis_clientes['Tasa_Conversion'] = (analisis_clientes['Ventas_Cerradas'] / analisis_clientes['Valor_Cotizado'] * 100).fillna(0)
        analisis_clientes['Margen_Promedio'] = (analisis_clientes['Margen_Total'] / analisis_clientes['Ventas_Cerradas'] * 100).fillna(0)

        if not analisis_clientes.empty:
            st.markdown("##### Insights Clave de Clientes")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                cliente_mvp = analisis_clientes.loc[analisis_clientes['Ventas_Cerradas'].idxmax()]
                st.markdown("**🏆 Cliente MVP (Más Compra)**")
                st.caption(cliente_mvp['cliente_nombre'])
                st.metric(label="Ventas Cerradas", value=f"${cliente_mvp['Ventas_Cerradas']:,.0f}")

            with col2:
                cliente_leal = analisis_clientes.loc[analisis_clientes['Num_Cotizaciones'].idxmax()]
                st.markdown("**🤝 Cliente Frecuente**")
                st.caption(cliente_leal['cliente_nombre'])
                st.metric(label="N° de Cotizaciones", value=f"{cliente_leal['Num_Cotizaciones']}")

            with col3:
                oportunidades = analisis_clientes[analisis_clientes['Num_Cotizaciones'] >= 2]
                if not oportunidades.empty:
                    oportunidad = oportunidades.sort_values('Tasa_Conversion').iloc[0]
                    st.markdown("**🎯 Oportunidad de Seguimiento**")
                    st.caption(oportunidad['cliente_nombre'])
                    st.metric(label="Tasa de Conversión", value=f"{oportunidad['Tasa_Conversion']:.1f}%")
                else:
                    st.markdown("**🎯 Oportunidad de Seguimiento**")
                    st.info("No hay suficientes datos para identificar una oportunidad clara.")

            st.divider()

            st.markdown("##### Tabla de Análisis de Clientes")
            # --- CAMBIO: Se elimina column_config para asegurar la visualización de los valores ---
            st.dataframe(
                analisis_clientes.sort_values(by="Valor_Cotizado", ascending=False),
                use_container_width=True, 
                hide_index=True
            )

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
            df_display = df_filtrado[columnas_existentes].rename(columns=columnas_a_mostrar)
            
            # --- CAMBIO: Se elimina column_config para asegurar la visualización de los valores ---
            st.dataframe(
                df_display.sort_values(by='Fecha', ascending=False),
                use_container_width=True,
                hide_index=True,
            )
