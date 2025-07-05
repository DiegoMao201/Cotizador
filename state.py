# state.py
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from utils import * # Importar todo desde utils, incluyendo la nueva constante TASA_IVA

class QuoteState:
    """
    Una clase para gestionar de forma centralizada el estado de una cotización.
    Encapsula los ítems, el cliente, los cálculos y las observaciones.
    """
    def __init__(self):
        self.numero_propuesta = st.session_state.get('numero_propuesta', self._generar_nuevo_numero())
        self.cotizacion_items = st.session_state.get('cotizacion_items', [])
        self.cliente_actual = st.session_state.get('cliente_actual', {})
        self.observaciones = st.session_state.get('observaciones', self._default_obs())
        self.vendedor = st.session_state.get('vendedor_en_uso', "")
        self.status = st.session_state.get('status_cotizacion', ESTADOS_COTIZACION[0])
        self.subtotal_bruto = 0
        self.descuento_total = 0
        self.base_gravable = 0
        self.iva_valor = 0
        self.total_general = 0
        self.recalcular_totales()

    def _generar_nuevo_numero(self):
        """Genera un nuevo número de propuesta único."""
        return f"PROP-{datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d-%H%M%S')}"

    def _default_obs(self):
        """Devuelve las observaciones por defecto."""
        return ("Forma de Pago: 50% Anticipo, 50% Contra-entrega.\n"
                "Tiempos de Entrega: 3-5 días hábiles para productos en stock.\n"
                "Garantía: Productos cubiertos por garantía de fábrica. No cubre mal uso.")

    def persist_to_session(self):
        """Guarda el estado actual en st.session_state para mantenerlo entre reruns."""
        st.session_state.numero_propuesta = self.numero_propuesta
        st.session_state.cotizacion_items = self.cotizacion_items
        st.session_state.cliente_actual = self.cliente_actual
        st.session_state.observaciones = self.observaciones
        st.session_state.vendedor_en_uso = self.vendedor
        st.session_state.status_cotizacion = self.status

    def set_vendedor(self, nombre_vendedor):
        """Actualiza el nombre del vendedor."""
        self.vendedor = nombre_vendedor
        self.persist_to_session()

    def set_cliente(self, cliente_dict):
        """Establece el cliente para la cotización."""
        self.cliente_actual = cliente_dict
        self.persist_to_session()

    def agregar_item(self, producto_info, cantidad, precio_unitario):
        """Añade un nuevo ítem a la cotización."""
        if not self.cliente_actual:
            st.warning("Por favor, selecciona un cliente antes de agregar productos.")
            return

        nuevo_item = {
            'Referencia': producto_info.get(REFERENCIA_COL, 'N/A'),
            'Producto': producto_info.get(NOMBRE_PRODUCTO_COL, ''),
            'Cantidad': cantidad,
            'Precio Unitario': precio_unitario,
            'Descuento (%)': 0.0,
            'Inventario': producto_info.get(STOCK_COL, 0), # Guardamos el stock para referencia
            'Total': 0 # Se calculará en recalcular_totales
        }
        self.cotizacion_items.append(nuevo_item)
        st.toast(f"✅ '{producto_info.get(NOMBRE_PRODUCTO_COL, '')}' agregado.", icon="👍")
        self.recalcular_totales()
        self.persist_to_session()

    def actualizar_items(self, edited_df):
        """Actualiza la lista de ítems desde el data_editor."""
        self.cotizacion_items = edited_df.to_dict('records')
        self.recalcular_totales()
        self.persist_to_session()

    def recalcular_totales(self):
        """(Re)calcula todos los totales financieros de la cotización."""
        if not self.cotizacion_items:
            self.subtotal_bruto = self.descuento_total = self.base_gravable = self.iva_valor = self.total_general = 0
            return

        df = pd.DataFrame(self.cotizacion_items)
        df['Total Bruto'] = df['Cantidad'] * df['Precio Unitario']
        df['Valor Descuento'] = df['Total Bruto'] * (df['Descuento (%)'] / 100)
        df['Total'] = df['Total Bruto'] - df['Valor Descuento']

        self.subtotal_bruto = df['Total Bruto'].sum()
        self.descuento_total = df['Valor Descuento'].sum()
        self.base_gravable = df['Total'].sum()
        self.iva_valor = self.base_gravable * TASA_IVA  # Usando la constante
        self.total_general = self.base_gravable + self.iva_valor
        
        # Actualizamos la lista de items con el total calculado
        self.cotizacion_items = df.to_dict('records')


    def reiniciar_cotizacion(self):
        """Limpia el estado actual para una nueva cotización de forma segura."""
        claves_a_borrar = [
            'numero_propuesta', 'cotizacion_items', 'cliente_actual',
            'observaciones', 'vendedor_en_uso', 'status_cotizacion', 'state'
        ]
        for key in claves_a_borrar:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    def cargar_desde_gheets(self, numero_a_cargar, workbook, silent=False):
        """Carga una propuesta existente desde Google Sheets."""
        data = get_full_proposal_data(numero_a_cargar, workbook)
        if data:
            self.numero_propuesta = data['header'].get('numero_propuesta', numero_a_cargar)
            self.observaciones = data['header'].get('observaciones', self._default_obs())
            self.vendedor = data['header'].get('vendedor', '')
            self.status = data['header'].get('status', ESTADOS_COTIZACION[0])

            # Cargar cliente
            df_clientes = cargar_datos_maestros(workbook)[1]
            cliente_nombre = data['header'].get('cliente_nombre')
            if cliente_nombre and not df_clientes.empty:
                cliente_encontrado = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_nombre]
                if not cliente_encontrado.empty:
                    self.cliente_actual = cliente_encontrado.iloc[0].to_dict()
                else:
                    self.cliente_actual = {} # Limpiar si el cliente ya no existe
            
            # Cargar items
            self.cotizacion_items = data['items']
            self.recalcular_totales()
            
            if not silent:
                self.persist_to_session()
                st.toast(f"✅ Propuesta '{numero_a_cargar}' cargada.")
                if "load_quote" in st.query_params:
                    st.query_params.clear()
            return True
        return False
