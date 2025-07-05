# pages/1_📄_Consultas.py
import streamlit as st
import pandas as pd
from utils import listar_propuestas_df, ESTADOS_COTIZACION

st.set_page_config(page_title="Consulta de Propuestas", page_icon="📄", layout="wide")
st.title("📄 Consulta y Gestión de Propuestas")

df_propuestas = listar_propuestas_df()

if df_propuestas.empty:
    st.warning("No se encontraron propuestas guardadas en la base de datos.")
else:
    # --- FILTROS ---
    st.header("🔍 Filtros de Búsqueda")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        clientes_unicos = ["Todos"] + sorted(df_propuestas['Cliente'].unique().tolist())
        cliente_seleccionado = st.selectbox("Filtrar por Cliente:", clientes_unicos)

    with col2:
        estados_seleccionados = st.multiselect("Filtrar por Estado:", options=ESTADOS_COTIZACION, placeholder="Seleccione uno o más estados")
    
    with col3:
        # Filtro por rango de fechas
        min_date = df_propuestas['Fecha'].min().date()
        max_date = df_propuestas['Fecha'].max().date()
        rango_fechas = st.date_input(
            "Filtrar por Fecha:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

    # --- APLICAR FILTROS ---
    df_filtrado = df_propuestas.copy()
    if cliente_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Cliente'] == cliente_seleccionado]
    
    if estados_seleccionados:
        df_filtrado = df_filtrado[df_filtrado['Estado'].isin(estados_seleccionados)]
    
    if len(rango_fechas) == 2:
        start_date, end_date = pd.to_datetime(rango_fechas[0]), pd.to_datetime(rango_fechas[1])
        df_filtrado = df_filtrado[df_filtrado['Fecha'].dt.date.between(start_date.date(), end_date.date())]

    # --- VISUALIZACIÓN DE DATOS ---
    st.divider()
    st.header("📊 Resultados")
    
    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY hh:mm a"),
            "Total": st.column_config.NumberColumn("Total", format="$%d")
        }
    )

    st.header("⚙️ Acciones")
    propuestas_para_seleccionar = df_filtrado['N° Propuesta'].tolist()
    
    if propuestas_para_seleccionar:
        prop_seleccionada = st.selectbox(
            "Seleccione una propuesta para ver acciones:",
            options=[""] + propuestas_para_seleccionar
        )

        if prop_seleccionada:
            st.info(f"Ha seleccionado la propuesta **{prop_seleccionada}**.")
            
            # Crear un enlace a la página principal con el parámetro de la propuesta
            st.page_link(
                "Cotizador_Ferreinox.py",
                label="✏️ Cargar para Editar en Cotizador",
                icon="✏️",
                query_params={"load_quote": prop_seleccionada}
            )
            st.caption("Al hacer clic, será redirigido a la página principal con los datos de esta propuesta cargados.")
    else:
        st.info("Ninguna propuesta coincide con los filtros seleccionados.")
