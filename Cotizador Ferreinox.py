# -*- coding: utf-8 -*-
# Cotizador_Ferreinox.py (Script Principal MODIFICADO)
import streamlit as st
from utils import LOGO_FILE_PATH
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import tempfile

# --- CONFIGURACIÓN GLOBAL DE LA APLICACIÓN ---
st.set_page_config(
    page_title="Cotizador Ferreinox",
    page_icon="🔩",
    layout="wide"
)

# --- RUTAS A LOS ARCHIVOS ---
PROMO_IMAGE_PATH = Path("viniltex pintuco colores tipo 1.png")
FONT_PATH = Path("Anton-Regular.ttf")
TEKBOND1_PATH = Path("tekbond1.png")
TEKBOND2_PATH = Path("tekbond2.png")
TEKBOND3_PATH = Path("tekbond3.png")
TEKBOND4_PATH = Path("tekbond4.png")

# --- SIDEBAR GLOBAL ---
with st.sidebar:
    if LOGO_FILE_PATH.exists():
        st.image(str(LOGO_FILE_PATH), use_container_width=True)
    st.title("Navegación")


# --- FUNCIÓN PARA CREAR IMAGEN DE PROMOCIÓN ---
def crear_imagen_teleferia(width=800, height=450):
    """
    Crea una imagen promocional para la Teleferia usando Pillow y la guarda en un archivo temporal.
    Retorna la ruta al archivo temporal.
    """
    azul_oscuro = (0, 51, 102)
    amarillo_acento = (255, 204, 0)
    blanco = (255, 255, 255)

    img = Image.new('RGB', (width, height), color=azul_oscuro)
    draw = ImageDraw.Draw(img)

    try:
        font_titulo = ImageFont.truetype(str(FONT_PATH), 120)
        font_subtitulo = ImageFont.truetype(str(FONT_PATH), 55)
        font_texto = ImageFont.truetype(str(FONT_PATH), 40)
    except IOError:
        st.error(f"No se encontró la fuente en la ruta: {FONT_PATH}. Asegúrate de que 'Anton-Regular.ttf' esté en la carpeta.")
        font_titulo = ImageFont.load_default()
        font_subtitulo = ImageFont.load_default()
        font_texto = ImageFont.load_default()

    draw.text((40, 20), "TELEFERIA", font=font_titulo, fill=amarillo_acento)
    draw.line([(40, 150), (width - 40, 150)], fill=amarillo_acento, width=5)
    draw.text((40, 170), "¡ÚLTIMA OPORTUNIDAD!", font=font_subtitulo, fill=blanco)
    draw.text((40, 250), "COMPRA A", font=font_texto, fill=blanco)
    draw.text((220, 250), "PRECIO VIEJO", font=font_texto, fill=amarillo_acento)
    draw.text((40, 320), "+ DESCUENTOS", font=font_texto, fill=blanco)
    draw.text((310, 320), "ACUMULABLES", font=font_texto, fill=amarillo_acento)

    draw.rectangle([(width - 290, height - 80), (width, height)], fill=amarillo_acento)
    draw.text((width - 275, height - 75), "ESTE JUEVES", font=font_subtitulo, fill=azul_oscuro)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        img.save(tmp_file, format="PNG")
        temp_path = tmp_file.name

    return temp_path

# --- CENTRO DE PROMOCIONES ---

st.title("🚀 Centro de Promociones Activas")
st.header("¡Impulsa tus Ventas con las Ofertas del Mes!")
st.markdown("---")

# --- TARJETA DE PROMOCIÓN 2: TELEFERIA (GENERADA CON CÓDIGO) ---
with st.container(border=True):
    col_img_tele, col_text_tele = st.columns([2, 3])

    with col_img_tele:
        st.markdown("##### **Evento Especial de la Semana**")
        ruta_imagen_teleferia = crear_imagen_teleferia()
        st.image(ruta_imagen_teleferia, use_container_width=True)

    with col_text_tele:
        st.markdown("### 📞 ¡Prepárate para la TELEFERIA!")
        st.warning(
            """
            **¡No dejes pasar el tren!** Esta es la última llamada para que tus clientes aseguren
            los productos que necesitan a precios que no volverán.
            """
        )

        st.metric(
            label="Condición Especial",
            value="PRECIOS ANTIGUOS"
        )

        st.markdown("Recuerda a tus clientes que **todos los descuentos y ofertas actuales son acumulables** con esta oportunidad única. ¡Es el mejor momento para cerrar grandes negocios!")

        if st.button("Revisar Listas de Precios 💵", type="primary", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")

st.markdown("---")

# --- TARJETA DE PROMOCIÓN 1: VINILTEX (IMAGEN ESTÁTICA) ---
with st.container(border=True):
    col_img, col_text = st.columns([2, 3])

    with col_img:
        if PROMO_IMAGE_PATH.exists():
            st.image(str(PROMO_IMAGE_PATH), use_container_width=True)
        else:
            st.warning("⚠️ No se encontró la imagen de la promoción 'viniltex pintuco colores tipo 1.png'.")

    with col_text:
        st.markdown("### ¡Dale Color a tus Proyectos con Viniltex!")
        st.info(
            """
            Calidad superior, cubrimiento insuperable y una paleta de colores que inspira.
            ¡Es el momento perfecto para ofrecer a tus clientes lo mejor de Pintuco!
            """
        )

        st.metric(
            label="Descuento Exclusivo en TODA la línea Viniltex",
            value="6% OFF"
        )

        st.markdown("**¡Aprovecha esta oportunidad!** Recuerda aplicar el descuento al cotizar.")

        if st.button("Ir al Cotizador y Aplicar Promo 🔩", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")

st.markdown("---")

# --- TARJETA DE PROMOCIÓN 3: TEKBOND 1 ---
with st.container(border=True):
    col_img_tekbond1, col_text_tekbond1 = st.columns([2, 3])

    with col_img_tekbond1:
        if TEKBOND1_PATH.exists():
            st.image(str(TEKBOND1_PATH), use_container_width=True)
        else:
            st.warning(f"⚠️ No se encontró la imagen de la promoción '{TEKBOND1_PATH.name}'.")

    with col_text_tekbond1:
        st.markdown("### ¡Descubre la Potencia de Tekbond!")
        st.info("Productos de alta calidad para tus proyectos de fijación y sellado.")
        if st.button("Ver Productos Tekbond 🛠️", key="tek1", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")

st.markdown("---")

# --- TARJETA DE PROMOCIÓN 4: TEKBOND 2 ---
with st.container(border=True):
    col_img_tekbond2, col_text_tekbond2 = st.columns([2, 3])

    with col_img_tekbond2:
        if TEKBOND2_PATH.exists():
            st.image(str(TEKBOND2_PATH), use_container_width=True)
        else:
            st.warning(f"⚠️ No se encontró la imagen de la promoción '{TEKBOND2_PATH.name}'.")

    with col_text_tekbond2:
        st.markdown("### ¡Innovación y Resistencia con Tekbond!")
        st.info("Soluciones adhesivas para profesionales y entusiastas del DIY.")
        if st.button("Explorar la Gama Tekbond 🔩", key="tek2", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")

st.markdown("---")

# --- TARJETA DE PROMOCIÓN 5: TEKBOND 3 ---
with st.container(border=True):
    col_img_tekbond3, col_text_tekbond3 = st.columns([2, 3])

    with col_img_tekbond3:
        if TEKBOND3_PATH.exists():
            st.image(str(TEKBOND3_PATH), use_container_width=True)
        else:
            st.warning(f"⚠️ No se encontró la imagen de la promoción '{TEKBOND3_PATH.name}'.")

    with col_text_tekbond3:
        st.markdown("### ¡Rendimiento Superior Garantizado con Tekbond!")
        st.info("Adhesivos y selladores diseñados para los trabajos más exigentes.")
        if st.button("Conoce la Calidad Tekbond 💪", key="tek3", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")

st.markdown("---")

# --- TARJETA DE PROMOCIÓN 6: TEKBOND 4 ---
with st.container(border=True):
    col_img_tekbond4, col_text_tekbond4 = st.columns([2, 3])

    with col_img_tekbond4:
        if TEKBOND4_PATH.exists():
            st.image(str(TEKBOND4_PATH), use_container_width=True)
        else:
            st.warning(f"⚠️ No se encontró la imagen de la promoción '{TEKBOND4_PATH.name}'.")

    with col_text_tekbond4:
        st.markdown("### ¡Las Mejores Soluciones en Adhesión son de Tekbond!")
        st.info("Encuentra el producto Tekbond ideal para cada una de tus necesidades.")
        if st.button("Descubre las Soluciones Tekbond ✨", key="tek4", use_container_width=True):
            st.switch_page("pages/0_⚙️_Cotizador.py")

st.markdown("---")
st.caption("Aquí aparecerán todas las promociones vigentes. ¡Revísalas constantemente!")
