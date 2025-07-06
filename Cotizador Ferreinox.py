# Cotizador_Ferreinox.py (Script Principal)
import streamlit as st
from utils import LOGO_FILE_PATH

# --- CONFIGURACIÓN GLOBAL DE LA APLICACIÓN ---
# Esto se aplicará a todas las páginas.
st.set_page_config(
    page_title="Cotizador Ferreinox",
    page_icon="🔩",
    layout="wide"
)

# --- SIDEBAR GLOBAL ---
# Elementos que quieres que aparezcan en todas las páginas.
with st.sidebar:
    if LOGO_FILE_PATH.exists():
        st.image(str(LOGO_FILE_PATH), use_container_width=True)
    st.title("Navegación")

# --- PÁGINA DE INICIO ---
# Un mensaje de bienvenida en la página principal.
st.title("Bienvenido al Sistema de Cotizaciones Ferreinox")
st.markdown("---")
st.header("Por favor, seleccione una página en el menú de la izquierda para comenzar.")
st.info(
    """
    - **0_⚙️_Cotizador:** Para crear o editar propuestas.
    - **1_📄_Consultas:** Para buscar, filtrar y gestionar propuestas existentes.
    """
)
