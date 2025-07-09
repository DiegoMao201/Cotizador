# Cotizador_Ferreinox.py (Script Principal MODIFICADO)
import streamlit as st
from utils import LOGO_FILE_PATH
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import tempfile
--- CONFIGURACIÓN GLOBAL DE LA APLICACIÓN ---
st.set_page_config(
page_title="Cotizador Ferreinox",
page_icon="🔩",
layout="wide"
)

--- RUTAS A LOS ARCHIVOS ---
PROMO_IMAGE_PATH = Path("viniltex pintuco colores tipo 1.png")
FONT_PATH = Path("Anton-Regular.ttf")
TEKBOND1_PATH = Path("tekbond1.png")
TEKBOND2_PATH = Path("tekbond2.png")
TEKBOND3_PATH = Path("tekbond3.png")
TEKBOND4_PATH = Path("tekbond4.png")

--- SIDEBAR GLOBAL ---
with st.sidebar:
if LOGO_FILE_PATH.exists():
st.image(str(LOGO_FILE_PATH), use_container_width=True)
st.title("Navegación")

--- FUNCIÓN PARA CREAR IMAGEN DE PROMOCIÓN ---
def crear_imagen_teleferia(width=800, height=450):
"""
Crea una imagen promocional para la Teleferia usando Pillow y la guarda en un archivo temporal.
Retorna la ruta al archivo temporal.
"""
azul_oscuro = (0, 51, 102)
amarillo_acento = (255, 204, 0)
blanco = (255, 255, 255)

img = Image.new(&#39;RGB&#39;, (width, height), color=azul_oscuro)
draw = ImageDraw.Draw(img)

try:
    font_titulo = ImageFont.truetype(str(FONT_PATH), 120)
    font_subtitulo = ImageFont.truetype(str(FONT_PATH), 55)
    font_texto = ImageFont.truetype(str(FONT_PATH), 40)
except IOError:
    st.error(f&quot;No se encontró la fuente en la ruta: {FONT_PATH}. Asegúrate de que &#39;Anton-Regular.ttf&#39; esté en la carpeta.&quot;)
    font_titulo = ImageFont.load_default()
    font_subtitulo = ImageFont.load_default()
    font_texto = ImageFont.load_default()

draw.text((40, 20), &quot;TELEFERIA&quot;, font=font_titulo, fill=amarillo_acento)
draw.line([(40, 150), (width - 40, 150)], fill=amarillo_acento, width=5)
draw.text((40, 170), &quot;¡ÚLTIMA OPORTUNIDAD!&quot;, font=font_subtitulo, fill=blanco)
draw.text((40, 250), &quot;COMPRA A&quot;, font=font_texto, fill=blanco)
draw.text((220, 250), &quot;PRECIO VIEJO&quot;, font=font_texto, fill=amarillo_acento)
draw.text((40, 320), &quot;+ DESCUENTOS&quot;, font=font_texto, fill=blanco)
draw.text((310, 320), &quot;ACUMULABLES&quot;, font=font_texto, fill=amarillo_acento)

# --- AJUSTE REALIZADO AQUÍ ---
# Se hizo el rectángulo más ancho y se ajustó la posición del texto para que no se corte.
# Antes: draw.rectangle([(width - 260, height - 80), (width, height)], fill=amarillo_acento)
# Antes: draw.text((width - 240, height - 75), &quot;ESTE JUEVES&quot;, font=font_subtitulo, fill=azul_oscuro)

draw.rectangle([(width - 290, height - 80), (width, height)], fill=amarillo_acento)
draw.text((width - 275, height - 75), &quot;ESTE JUEVES&quot;, font=font_subtitulo, fill=azul_oscuro)

with tempfile.NamedTemporaryFile(suffix=&quot;.png&quot;, delete=False) as tmp_file:
    img.save(tmp_file, format=&quot;PNG&quot;)
    temp_path = tmp_file.name

return temp_path
--- CENTRO DE PROMOCIONES ---
st.title("🚀 Centro de Promociones Activas")
st.header("¡Impulsa tus Ventas con las Ofertas del Mes!")
st.markdown("---")

--- TARJETA DE PROMOCIÓN 2: TELEFERIA (GENERADA CON CÓDIGO) ---
with st.container(border=True):
col_img_tele, col_text_tele = st.columns([2, 3])

with col_img_tele:
    st.markdown(&quot;##### **Evento Especial de la Semana**&quot;)
    ruta_imagen_teleferia = crear_imagen_teleferia()
    st.image(ruta_imagen_teleferia, use_container_width=True)

with col_text_tele:
    st.markdown(&quot;### 📞 ¡Prepárate para la TELEFERIA!&quot;)
    st.warning(
        &quot;&quot;&quot;
        **¡No dejes pasar el tren!** Esta es la última llamada para que tus clientes aseguren
        los productos que necesitan a precios que no volverán.
        &quot;&quot;&quot;
    )

    st.metric(
        label=&quot;Condición Especial&quot;,
        value=&quot;PRECIOS ANTIGUOS&quot;
    )

    st.markdown(&quot;Recuerda a tus clientes que **todos los descuentos y ofertas actuales son acumulables** con esta oportunidad única. ¡Es el mejor momento para cerrar grandes negocios!&quot;)

    if st.button(&quot;Revisar Listas de Precios 💵&quot;, type=&quot;primary&quot;, use_container_width=True):
        st.switch_page(&quot;pages/0_⚙️_Cotizador.py&quot;)
st.markdown("---")

--- TARJETA DE PROMOCIÓN 1: VINILTEX (IMAGEN ESTÁTICA) ---
with st.container(border=True):
col_img, col_text = st.columns([2, 3])

with col_img:
    if PROMO_IMAGE_PATH.exists():
        st.image(str(PROMO_IMAGE_PATH), use_container_width=True)
    else:
        st.warning(&quot;⚠️ No se encontró la imagen de la promoción &#39;viniltex pintuco colores tipo 1.png&#39;.&quot;)

with col_text:
    st.markdown(&quot;### ¡Dale Color a tus Proyectos con Viniltex!&quot;)
    st.info(
        &quot;&quot;&quot;
        Calidad superior, cubrimiento insuperable y una paleta de colores que inspira.
        ¡Es el momento perfecto para ofrecer a tus clientes lo mejor de Pintuco!
        &quot;&quot;&quot;
    )

    st.metric(
        label=&quot;Descuento Exclusivo en TODA la línea Viniltex&quot;,
        value=&quot;6% OFF&quot;
    )

    st.markdown(&quot;**¡Aprovecha esta oportunidad!** Recuerda aplicar el descuento al cotizar.&quot;)

    if st.button(&quot;Ir al Cotizador y Aplicar Promo 🔩&quot;, use_container_width=True):
        st.switch_page(&quot;pages/0_⚙️_Cotizador.py&quot;)
st.markdown("---")

--- TARJETA DE PROMOCIÓN 3: TEKBOND 1 ---
with st.container(border=True):
col_img_tekbond1, col_text_tekbond1 = st.columns([2, 3])

with col_img_tekbond1:
    if TEKBOND1_PATH.exists():
        st.image(str(TEKBOND1_PATH), use_container_width=True)
    else:
        st.warning(f&quot;⚠️ No se encontró la imagen de la promoción &#39;{TEKBOND1_PATH.name}&#39;.&quot;)

with col_text_tekbond1:
    st.markdown(&quot;### ¡Descubre la Potencia de Tekbond!&quot;)
    st.info(&quot;Productos de alta calidad para tus proyectos de fijación y sellado.&quot;)
    if st.button(&quot;Ver Productos Tekbond 🛠️&quot;, use_container_width=True):
        st.switch_page(&quot;pages/0_⚙️_Cotizador.py&quot;)
st.markdown("---")

--- TARJETA DE PROMOCIÓN 4: TEKBOND 2 ---
with st.container(border=True):
col_img_tekbond2, col_text_tekbond2 = st.columns([2, 3])

with col_img_tekbond2:
    if TEKBOND2_PATH.exists():
        st.image(str(TEKBOND2_PATH), use_container_width=True)
    else:
        st.warning(f&quot;⚠️ No se encontró la imagen de la promoción &#39;{TEKBOND2_PATH.name}&#39;.&quot;)

with col_text_tekbond2:
    st.markdown(&quot;### ¡Innovación y Resistencia con Tekbond!&quot;)
    st.info(&quot;Soluciones adhesivas para profesionales y entusiastas del DIY.&quot;)
    if st.button(&quot;Explorar la Gama Tekbond 🔩&quot;, use_container_width=True):
        st.switch_page(&quot;pages/0_⚙️_Cotizador.py&quot;)
st.markdown("---")

--- TARJETA DE PROMOCIÓN 5: TEKBOND 3 ---
with st.container(border=True):
col_img_tekbond3, col_text_tekbond3 = st.columns([2, 3])

with col_img_tekbond3:
    if TEKBOND3_PATH.exists():
        st.image(str(TEKBOND3_PATH), use_container_width=True)
    else:
        st.warning(f&quot;⚠️ No se encontró la imagen de la promoción &#39;{TEKBOND3_PATH.name}&#39;.&quot;)

with col_text_tekbond3:
    st.markdown(&quot;### ¡Rendimiento Superior Garantizado con Tekbond!&quot;)
    st.info(&quot;Adhesivos y selladores diseñados para los trabajos más exigentes.&quot;)
    if st.button(&quot;Conoce la Calidad Tekbond 💪&quot;, use_container_width=True):
        st.switch_page(&quot;pages/0_⚙️_Cotizador.py&quot;)
st.markdown("---")

--- TARJETA DE PROMOCIÓN 6: TEKBOND 4 ---
with st.container(border=True):
col_img_tekbond4, col_text_tekbond4 = st.columns([2, 3])

with col_img_tekbond4:
    if TEKBOND4_PATH.exists():
        st.image(str(TEKBOND4_PATH), use_container_width=True)
    else:
        st.warning(f&quot;⚠️ No se encontró la imagen de la promoción &#39;{TEKBOND4_PATH.name}&#39;.&quot;)

with col_text_tekbond4:
    st.markdown(&quot;### ¡Las Mejores Soluciones en Adhesión son de Tekbond!&quot;)
    st.info(&quot;Encuentra el producto Tekbond ideal para cada una de tus necesidades.&quot;)
    if st.button(&quot;Descubre las Soluciones Tekbond ✨&quot;, use_container_width=True):
        st.switch_page(&quot;pages/0_⚙️_Cotizador.py&quot;)
