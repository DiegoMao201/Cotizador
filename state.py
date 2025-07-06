# state.py
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from utils import *

class QuoteState:
    def __init__(self):
        self.numero_propuesta = st.session_state.get('numero_propuesta', self._generar_nuevo_numero())
        self.cotizacion_items = st.session_state.get('cotizacion_items', [])
        self.cliente_actual = st.session_state.get('cliente_actual', {})
        self.observaciones = st.session_state.get('observaciones', self._default_obs())
        self.vendedor = st.session_state.get('vendedor_en_uso', "")
        self.status = st.session_state.get('status_cotizacion', ESTADOS_COTIZACION[0])
        self.is_loaded_from_sheet = st.session_state.get('is_loaded_from_sheet', False) # NUEVO
        self.subtotal_bruto = 0
        self.descuento_total = 0
        self.base_gravable = 0
        self.iva_valor = 0
        self.total_general = 0
        self.costo_total = 0
        self.recalcular_totales()

    def _generar_nuevo_numero(self):
        return f"PROP-{datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d-%H%M%S')}"

    def _default_obs(self):
        return ("Forma de Pago: 50% Anticipo, 50% Contra-entrega.\n"
                "Tiempos de Entrega: 3-5 días hábiles para productos en stock.\n"
                "Garantía: Productos cubiertos por garantía de fábrica. No cubre mal uso.")

    def persist_to_session(self):
        st.session_state.numero_propuesta = self.numero_propuesta
        st.session_state.cotizacion_items = self.cotizacion_items
        st.session_state.cliente_actual = self.cliente_actual
        st.session_state.observaciones = self.observaciones
        st.session_state.vendedor_en_uso = self.vendedor
        st.session_state.status_cotizacion = self.status
        st.session_state.is_loaded_from_sheet = self.is_loaded_from_sheet # NUEVO

    def set_vendedor(self, nombre_vendedor):
        self.vendedor = nombre_vendedor
        self.persist_to_session()

    def set_cliente(self, cliente_dict):
        self.cliente_actual = cliente_dict
        self.persist_to_session()

    def agregar_item(self, producto_info, cantidad, precio_unitario):
        if not self.cliente_actual:
            st.warning("Por favor, selecciona un cliente antes de agregar productos.")
            return
        nuevo_item = {
            'Referencia': producto_info.get(REFERENCIA_COL, 'N/A'),
            'Producto': producto_info.get(NOMBRE_PRODUCTO_COL, ''),
            'Cantidad': cantidad,
            'Precio Unitario': precio_unitario,
            'Descuento (%)': 0.0,
            'Inventario': producto_info.get(STOCK_COL, 0),
            'Costo': producto_info.get(COSTO_COL, 0),
            'Total': 0,
            'Valor Descuento': 0
        }
        self.cotizacion_items.append(nuevo_item)
        st.toast(f"✅ '{producto_info.get(NOMBRE_PRODUCTO_COL, '')}' agregado.", icon="�")
        self.recalcular_totales()
        self.persist_to_session()

    def actualizar_items_desde_vista(self, edited_df):
        """NUEVO: Actualiza el estado desde la vista editable del data_editor."""
        # Itera sobre los items editados y actualiza los valores correspondientes en el estado original
        for index, row in edited_df.iterrows():
            if index < len(self.cotizacion_items):
                self.cotizacion_items[index]['Cantidad'] = row['Cantidad']
                self.cotizacion_items[index]['Precio Unitario'] = row['Precio Unitario']
                self.cotizacion_items[index]['Descuento (%)'] = row['Descuento (%)']
        
        # Elimina items si el usuario los borró en la UI
        if len(edited_df) < len(self.cotizacion_items):
            self.cotizacion_items = self.cotizacion_items[:len(edited_df)]
            
        self.recalcular_totales()
        self.persist_to_session()

    def recalcular_totales(self):
        if not self.cotizacion_items:
            self.subtotal_bruto = self.descuento_total = self.base_gravable = self.iva_valor = self.total_general = self.costo_total = 0
            return

        df = pd.DataFrame(self.cotizacion_items)
        
        cols_to_process = ['Cantidad', 'Precio Unitario', 'Descuento (%)', 'Costo']
        for col in cols_to_process:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0

        df['Total Bruto'] = df['Cantidad'] * df['Precio Unitario']
        df['Valor Descuento'] = df['Total Bruto'] * (df['Descuento (%)'] / 100)
        df['Total'] = df['Total Bruto'] - df['Valor Descuento']
        df['Costo Total Item'] = df['Cantidad'] * df['Costo']

        self.subtotal_bruto = df['Total Bruto'].sum()
        self.descuento_total = df['Valor Descuento'].sum()
        self.base_gravable = df['Total'].sum()
        self.iva_valor = self.base_gravable * TASA_IVA
        self.total_general = self.base_gravable + self.iva_valor
        self.costo_total = df['Costo Total Item'].sum()
        
        self.cotizacion_items = df.to_dict('records')

    def reiniciar_cotizacion(self):
        claves_a_borrar = [
            'numero_propuesta', 'cotizacion_items', 'cliente_actual',
            'observaciones', 'vendedor_en_uso', 'status_cotizacion', 'is_loaded_from_sheet'
        ]
        for key in claves_a_borrar:
            if key in st.session_state:
                del st.session_state[key]
        # Reinicia el estado creando una nueva instancia
        st.session_state.state = QuoteState()
        st.rerun()

    def cargar_desde_gheets(self, numero_a_cargar, workbook, silent=False):
        data = get_full_proposal_data(numero_a_cargar, workbook)
        if data:
            self.numero_propuesta = data['header'].get('numero_propuesta', numero_a_cargar)
            self.observaciones = data['header'].get('observaciones', self._default_obs())
            self.vendedor = data['header'].get('vendedor', '')
            self.status = data['header'].get('status', ESTADOS_COTIZACION[0])
            self.is_loaded_from_sheet = True # MARCA COMO COTIZACIÓN CARGADA
            
            df_clientes = cargar_datos_maestros(workbook)[1]
            cliente_nombre = data['header'].get('cliente_nombre')
            if cliente_nombre and not df_clientes.empty:
                cliente_encontrado = df_clientes[df_clientes[CLIENTE_NOMBRE_COL] == cliente_nombre]
                self.cliente_actual = {} if cliente_encontrado.empty else cliente_encontrado.iloc[0].to_dict()
            
            self.cotizacion_items = data['items']
            self.recalcular_totales()
            
            if not silent:
                self.persist_to_session()
                st.toast(f"✅ Propuesta '{numero_a_cargar}' cargada.")
            return True
        return False
