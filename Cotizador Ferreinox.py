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

# --- RUTA A LA NUEVA IMAGEN DE PROMOCIÓN ---
PROMO_IMAGE_PATH = Path("viniltex pintuco colores tipo 1.png")

# --- SIDEBAR GLOBAL ---
with st.sidebar:
    if LOGO_FILE_PATH.exists():
        st.image(str(LOGO_FILE_PATH), use_container_width=True)
    st.title("Navegación")

# --- NUEVO CENTRO DE PROMOCIONES ---

st.title("🚀 Centro de Promociones Activas")
st.header("¡Impulsa tus Ventas con las Ofertas del Mes!")
st.markdown("---")

# --- TARJETA DE PROMOCIÓN: VINILTEX ---
with st.container(border=True):
    col_img, col_text = st.columns([2, 3]) # Columna de imagen un poco más pequeña

    with col_img:
        if PROMO_IMAGE_PATH.exists():
            st.image(str(PROMO_IMAGE_PATH), use_container_width=True)
        else:
            st.warning("⚠️ No se encontró la imagen de la promoción 'viniltex pintuco colores tipo 1.png'. Asegúrate de que esté en la carpeta principal.")

    with col_text:
        st.markdown("### ¡Dale Color a tus Proyectos con Viniltex!")
        st.info(
            """
            Calidad superior, cubrimiento insuperable y una paleta de colores que inspira. 
            ¡Es el momento perfecto para ofrecer a tus clientes lo mejor de Pintuco y aumentar tus ventas!
            """
        )
        
        # Métrica para resaltar el descuento
        st.metric(
            label="Descuento Exclusivo en TODA la línea Viniltex",
            value="6% OFF"
        )
        
        st.markdown("**¡Aprovecha esta oportunidad!** Recuerda aplicar el descuento al cotizar.")
        
        # Botón de llamado a la acción
        if st.button("Ir al Cotizador y Aplicar Promo 🔩", type="primary", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")

st.markdown("---")
st.caption("Aquí aparecerán todas las promociones vigentes. ¡Revísalas constantemente!")

# Puedes copiar y pegar el bloque "with st.container(border=True):" 
# para añadir más promociones en el futuro.
