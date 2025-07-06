# pages/2_📊_Resumen_Comercial.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils import connect_to_gsheets, listar_propuestas_df, listar_detalle_propuestas_df
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Resumen Comercial", page_icon="📊", layout="wide")
st.title("📊 Resumen Comercial y Análisis Gerencial")

# --- CONEXIÓN Y CARGA DE DATOS ---
workbook = connect_to_gsheets()
if not workbook:
    st.error("La aplicación no puede continuar sin conexión a la base de datos.")
    st.stop()

@st.cache_data(ttl=600)
def cargar_y_preparar_datos():
    df_propuestas = listar_propuestas_df(workbook)
    df_items = listar_detalle_propuestas_df(workbook)
    
    # --- Usando los nombres de columna exactos que proporcionaste ---
    numeric_cols_prop = ['total_final', 'margen_absoluto']
    
    for col in numeric_cols_prop:
        if col in df_propuestas.columns:
            df_propuestas[col] = pd.to_numeric(df_propuestas[col], errors='coerce').fillna(0)
        else:
            st.error(f"Error Crítico: La columna '{col}' no se encuentra en tu hoja 'Cotizaciones'. Por favor, verifica el nombre.")
            return pd.DataFrame(), pd.DataFrame() # Devuelve dataframes vacíos para detener la ejecución

    df_propuestas['fecha_creacion'] = pd.to_datetime(df_propuestas['fecha_creacion'], errors='coerce')
    df_propuestas = df_propuestas.dropna(subset=['fecha_creacion'])
    
    # --- Usando los nombres de columna exactos que proporcionaste ---
    numeric_cols_items = ['Cantidad', 'Total_Item']
    for col in numeric_cols_items:
        if col in df_items.columns:
            df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0)
        else:
            st.error(f"Error Crítico: La columna '{col}' no se encuentra en tu hoja 'Cotizaciones_Items'. Por favor, verifica el nombre.")
            return pd.DataFrame(), pd.DataFrame() # Devuelve dataframes vacíos para detener la ejecución
        
    return df_propuestas, df_items

df_propuestas, df_items = cargar_y_preparar_datos()

if df_propuestas.empty:
    st.warning("No hay datos de propuestas para analizar o ocurrió un error al cargar.")
    st.stop()

# --- FILTROS GLOBALES EN LA BARRA LATERAL ---
st.sidebar.header("Filtros del Dashboard")
vendedores = sorted(df_propuestas['vendedor'].dropna().unique())
vendedor_sel = st.sidebar.multiselect("Vendedor", options=vendedores, default=vendedores)

min_date = df_propuestas['fecha_creacion'].min().date()
max_date = df_propuestas['fecha_creacion'].max().date()

fecha_rango = st.sidebar.date_input(
    "Rango de Fechas",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Aplicar filtros
if len(fecha_rango) == 2:
    df_filtrado = df_propuestas[
        (df_propuestas['fecha_creacion'].dt.date >= fecha_rango[0]) &
        (df_propuestas['fecha_creacion'].dt.date <= fecha_rango[1])
    ]
else:
    df_filtrado = df_propuestas.copy()

df_filtrado = df_filtrado[df_filtrado['vendedor'].isin(vendedor_sel)]
propuestas_filtradas_ids = df_filtrado['numero_propuesta'].tolist()
df_items_filtrado = df_items[df_items['numero_propuesta'].isin(propuestas_filtradas_ids)]

# --- KPIs PRINCIPALES ---
st.header("Indicadores Clave de Rendimiento (KPIs)")
total_cotizado = df_filtrado['total_final'].sum()
margen_total = df_filtrado['margen_absoluto'].sum()
margen_porc = (margen_total / total_cotizado) * 100 if total_cotizado > 0 else 0
num_propuestas = len(df_filtrado)

df_aceptadas = df_filtrado[df_filtrado['status'] == 'Aceptada']
ventas_cerradas = df_aceptadas['total_final'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Valor Total Cotizado", f"${total_cotizado:,.0f}")
col2.metric("Ventas Cerradas (Aceptadas)", f"${ventas_cerradas:,.0f}")
col3.metric("Margen Bruto Total", f"${margen_total:,.0f}")
col4.metric("Margen Promedio", f"{margen_porc:.2f}%")

st.divider()

# --- PESTAÑAS DE ANÁLISIS ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Resumen General", "👥 Análisis por Vendedor", "📦 Top Productos", "🏢 Top Clientes"])

with tab1:
    st.subheader("Estado y Evolución de las Propuestas")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        status_counts = df_filtrado['status'].value_counts()
        # --- CAMBIO: Se usa px.pie en lugar de px.donut ---
        fig_status = px.pie(
            status_counts, 
            values=status_counts.values, 
            names=status_counts.index, 
            title="Distribución de Estados",
            hole=0.4 # Este parámetro crea el efecto de dona
        )
        fig_status.update_traces(textinfo='percent+label', pull=[0.05, 0, 0, 0])
        st.plotly_chart(fig_status, use_container_width=True)

    with col2:
        df_filtrado['mes'] = df_filtrado['fecha_creacion'].dt.to_period('M').astype(str)
        evolucion_mensual = df_filtrado.groupby('mes')['total_final'].sum().reset_index()
        fig_evolucion = px.line(
            evolucion_mensual,
            x='mes',
            y='total_final',
            title="Evolución del Valor Cotizado por Mes",
            markers=True,
            labels={'mes': 'Mes', 'total_final': 'Valor Cotizado'}
        )
        st.plotly_chart(fig_evolucion, use_container_width=True)

with tab2:
    st.subheader("Rendimiento por Vendedor")
    analisis_vendedor = df_filtrado.groupby('vendedor').agg(
        total_cotizado=('total_final', 'sum'),
        margen_total=('margen_absoluto', 'sum'),
        numero_propuestas=('numero_propuesta', 'count')
    ).reset_index().sort_values('total_cotizado', ascending=False)
    
    fig_vendedor = px.bar(
        analisis_vendedor,
        x='vendedor',
        y=['total_cotizado', 'margen_total'],
        title="Valor Cotizado y Margen por Vendedor",
        labels={'vendedor': 'Vendedor', 'value': 'Valor en $'},
        barmode='group'
    )
    st.plotly_chart(fig_vendedor, use_container_width=True)
    st.dataframe(analisis_vendedor, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Productos más Relevantes")
    col1, col2 = st.columns(2)
    
    with col1:
        top_productos_valor = df_items_filtrado.groupby('Producto')['Total_Item'].sum().nlargest(20).reset_index()
        fig_prod_valor = px.bar(
            top_productos_valor,
            x='Total_Item',
            y='Producto',
            orientation='h',
            title="Top 20 Productos por Valor Cotizado",
            labels={'Producto': 'Producto', 'Total_Item': 'Valor Total Cotizado'}
        ).update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_prod_valor, use_container_width=True)
        
    with col2:
        top_productos_rotacion = df_items_filtrado.groupby('Producto')['Cantidad'].sum().nlargest(20).reset_index()
        fig_prod_rotacion = px.bar(
            top_productos_rotacion,
            x='Cantidad',
            y='Producto',
            orientation='h',
            title="Top 20 Productos por Rotación (Unidades)",
            labels={'Producto': 'Producto', 'Cantidad': 'Unidades Cotizadas'}
        ).update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_prod_rotacion, use_container_width=True)

with tab4:
    st.subheader("Clientes más Importantes")
    col1, col2 = st.columns(2)

    with col1:
        top_clientes_valor = df_filtrado.groupby('cliente_nombre')['total_final'].sum().nlargest(20).reset_index()
        fig_cli_valor = px.bar(
            top_clientes_valor,
            x='total_final',
            y='cliente_nombre',
            orientation='h',
            title="Top 20 Clientes por Valor Cotizado",
            labels={'cliente_nombre': 'Cliente', 'total_final': 'Valor Total Cotizado'}
        ).update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_cli_valor, use_container_width=True)
        
    with col2:
        top_clientes_margen = df_filtrado.groupby('cliente_nombre')['margen_absoluto'].sum().nlargest(20).reset_index()
        fig_cli_margen = px.bar(
            top_clientes_margen,
            x='margen_absoluto',
            y='cliente_nombre',
            orientation='h',
            title="Top 20 Clientes por Margen Generado",
            labels={'cliente_nombre': 'Cliente', 'margen_absoluto': 'Margen Total Generado'}
        ).update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_cli_margen, use_container_width=True)
