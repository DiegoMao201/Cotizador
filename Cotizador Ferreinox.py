# -*- coding: utf-8 -*-
# Cotizador_Ferreinox.py (Script Principal MODIFICADO)
import streamlit as st
from utils import LOGO_FILE_PATH
from pathlib import Path

# --- CONFIGURACIÓN GLOBAL DE LA APLICACIÓN ---
st.set_page_config(
    page_title="Cotizador Ferreinox",
    page_icon="🔩",
    layout="wide"
)

# --- RUTAS A LOS ARCHIVOS DE PROMOCIONES ACTIVAS ---
TEKBOND1_PATH = Path("tekbond1.jpeg")
TEKBOND2_PATH = Path("tekbond2.jpeg")
TEKBOND3_PATH = Path("tekbond3.jpeg")
TEKBOND4_PATH = Path("tekbond4.jpeg")


# --- SIDEBAR GLOBAL ---
with st.sidebar:
    if LOGO_FILE_PATH.exists():
        st.image(str(LOGO_FILE_PATH), use_container_width=True)
    st.title("Navegación")


# --- CENTRO DE PROMOCIONES ---
st.title("🚀 Centro de Promociones Activas")
st.header("¡Impulsa tus Ventas con las Ofertas del Mes!")
st.markdown("---")


# --- SECCIÓN DE PROMOCIONES TEKBOND EN FORMATO 2x2 ---
st.subheader("💥 Promociones Exclusivas Tekbond")

# --- PRIMERA FILA DE PROMOCIONES TEKBOND ---
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        if TEKBOND1_PATH.exists():
            st.image(str(TEKBOND1_PATH), use_container_width=True)
        else:
            st.warning(f"⚠️ No se encontró la imagen '{TEKBOND1_PATH.name}'.")
        
        st.markdown("##### ¡Descubre la Potencia Tekbond!")
        st.info("Productos de alta calidad para tus proyectos de fijación y sellado.")
        
        if st.button("Ver Productos Tekbond 🛠️", key="tek1", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")

with col2:
    with st.container(border=True):
        if TEKBOND2_PATH.exists():
            st.image(str(TEKBOND2_PATH), use_container_width=True)
        else:
            st.warning(f"⚠️ No se encontró la imagen '{TEKBOND2_PATH.name}'.")
        
        st.markdown("##### ¡Innovación y Resistencia!")
        st.info("Soluciones adhesivas para profesionales y entusiastas del DIY.")

        if st.button("Explorar la Gama Tekbond 🔩", key="tek2", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")

# --- SEGUNDA FILA DE PROMOCIONES TEKBOND ---
col3, col4 = st.columns(2)

with col3:
    with st.container(border=True):
        if TEKBOND3_PATH.exists():
            st.image(str(TEKBOND3_PATH), use_container_width=True)
        else:
            st.warning(f"⚠️ No se encontró la imagen '{TEKBOND3_PATH.name}'.")

        st.markdown("##### ¡Rendimiento Superior Garantizado!")
        st.info("Adhesivos y selladores diseñados para los trabajos más exigentes.")
        
        if st.button("Conoce la Calidad Tekbond 💪", key="tek3", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")

with col4:
    with st.container(border=True):
        if TEKBOND4_PATH.exists():
            st.image(str(TEKBOND4_PATH), use_container_width=True)
        else:
            st.warning(f"⚠️ No se encontró la imagen '{TEKBOND4_PATH.name}'.")
        
        st.markdown("##### ¡Soluciones para cada Necesidad!")
        st.info("Encuentra el producto Tekbond ideal para cada aplicación.")

        if st.button("Descubre las Soluciones Tekbond ✨", key="tek4", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")


st.markdown("---")
st.caption("Aquí aparecerán todas las promociones vigentes. ¡Revísalas constantemente!")
