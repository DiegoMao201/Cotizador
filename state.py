# state.py
import streamlit as st
import pandas as pd
from datetime import datetime
from utils import (
    DETALLE_PROPUESTAS_SHEET_NAME, PROPUESTAS_SHEET_NAME, TASA_IVA,
    cargar_datos_maestros, listar_propuestas_df, CLIENTE_NOMBRE_COL, NOMBRE_PRODUCTO_COL
)

class QuoteState:
    """Una clase para gestionar el estado de una cotización en la sesión de Streamlit."""

    def __init__(self):
        """Inicializa el estado de la cotización."""
        self.numero_propuesta = f"TEMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.cliente_actual = {}
        self.cotizacion_items = []
        self.vendedor = ""
        self.observaciones = "Precios sujetos a cambio sin previo aviso. Validez de la oferta: 15 días."
        self.status = "Borrador"
        
        # --- Atributos financieros ---
        self.subtotal_bruto = 0.0
        self.descuento_total = 0.0
        self.iva_valor = 0.0
        self.total_general = 0.0
        # --- NUEVOS ATRIBUTOS PARA COSTOS Y MARGEN ---
        self.costo_total = 0.0
        self.margen_absoluto = 0.0
        self.margen_porcentual = 0.0
        
        self.recalcular_totales()

    def set_numero_propuesta(self, numero):
        self.numero_propuesta = numero
        self.persist_to_session()

    def set_cliente(self, cliente_dict):
        self.cliente_actual = cliente_dict
        self.persist_to_session()

    def set_vendedor(self, nombre_vendedor):
        self.vendedor = nombre_vendedor
        self.persist_to_session()

    def agregar_item(self, producto_dict, cantidad, precio_unitario):
        """Agrega un nuevo producto, INCLUYENDO SU COSTO, a la cotización."""
        total_item = cantidad * precio_unitario
        nuevo_item = {
            'Referencia': producto_dict.get('Referencia', 'N/A'),
            'Producto': producto_dict.get(NOMBRE_PRODUCTO_COL, 'N/A'),
            'Cantidad': cantidad,
            'Precio Unitario': precio_unitario,
            'Descuento (%)': 0.0,
            'Total': total_item,
            'Stock': producto_dict.get('Stock', 0),
            # --- AÑADIDO: Guardar el costo del producto en el item ---
            'Costo': producto_dict.get('Costo', 0.0) 
        }
        self.cotizacion_items.append(nuevo_item)
        self.recalcular_totales()
        self.persist_to_session()

    def actualizar_items_desde_vista(self, df_vista):
        """Actualiza la lista de items desde el data_editor, incluyendo la descripción."""
        nuevos_items = []
        mapa_items_actuales = {item['Referencia']: item for item in self.cotizacion_items}

        for _, row in df_vista.iterrows():
            item_completo = mapa_items_actuales.get(row['Referencia'], {})
            item_actualizado = {
                **item_completo,
                # --- AÑADIDO: Permite actualizar el nombre del producto ---
                'Producto': row['Producto'],
                'Cantidad': row['Cantidad'],
                'Precio Unitario': row['Precio Unitario'],
                'Descuento (%)': row['Descuento (%)'],
            }
            nuevos_items.append(item_actualizado)
        
        self.cotizacion_items = nuevos_items
        self.recalcular_totales()
        self.persist_to_session()

    def recalcular_totales(self):
        """Recalcula TODOS los totales, incluyendo costos y márgenes."""
        subtotal_bruto = 0
        descuento_total_valor = 0
        costo_total_calculado = 0
        
        for item in self.cotizacion_items:
            cantidad = item.get('Cantidad', 0)
            precio = item.get('Precio Unitario', 0)
            costo = float(item.get('Costo', 0) or 0) # Asegurarse que el costo sea numérico
            descuento_pct = item.get('Descuento (%)', 0)
            
            total_bruto_item = cantidad * precio
            descuento_valor_item = total_bruto_item * (descuento_pct / 100)
            total_neto_item = total_bruto_item - descuento_valor_item
            
            item['Total'] = total_neto_item
            subtotal_bruto += total_bruto_item
            descuento_total_valor += descuento_valor_item
            # --- AÑADIDO: Calcular el costo total ---
            costo_total_calculado += cantidad * costo

        subtotal_neto = subtotal_bruto - descuento_total_valor
        
        # Actualizar todos los atributos del estado
        self.subtotal_bruto = subtotal_bruto
        self.descuento_total = descuento_total_valor
        self.iva_valor = subtotal_neto * TASA_IVA
        self.total_general = subtotal_neto + self.iva_valor
        self.costo_total = costo_total_calculado
        self.margen_absoluto = subtotal_neto - self.costo_total
        self.margen_porcentual = (self.margen_absoluto / subtotal_neto) * 100 if subtotal_neto != 0 else 0

    def reiniciar_cotizacion(self):
        self.__init__()
        self.persist_to_session()
        st.success("Se ha iniciado una nueva cotización.")

    def cargar_desde_gheets(self, numero_propuesta, workbook, silent=False):
        try:
            propuestas_df = listar_propuestas_df(workbook)
            detalle_sheet = workbook.worksheet(DETALLE_PROPUESTAS_SHEET_NAME)
            all_items_df = pd.DataFrame(detalle_sheet.get_all_records())
            productos_df, clientes_df = cargar_datos_maestros(workbook)

            propuesta_data = propuestas_df[propuestas_df['numero_propuesta'] == numero_propuesta]

            if propuesta_data.empty:
                if not silent: st.error(f"No se encontró la propuesta {numero_propuesta}.")
                return False
            
            propuesta_row = propuesta_data.iloc[0]
            self.numero_propuesta = propuesta_row['numero_propuesta']
            
            cliente_nombre = propuesta_row['cliente_nombre']
            cliente_info = clientes_df[clientes_df[CLIENTE_NOMBRE_COL] == cliente_nombre]
            if not cliente_info.empty:
                self.cliente_actual = cliente_info.iloc[0].to_dict()

            self.vendedor = propuesta_row['vendedor']
            self.status = propuesta_row['status']
            self.observaciones = propuesta_row['Observaciones']

            self.cotizacion_items = []
            items_propuesta = all_items_df[all_items_df['numero_propuesta'] == numero_propuesta]

            for _, item_row in items_propuesta.iterrows():
                # --- AÑADIDO: Cargar el costo al editar una cotización ---
                costo_unitario_cargado = float(str(item_row.get('Costo_Unitario', '0')).replace(',', '.') or 0)
                stock_actual = 0
                info_producto = productos_df[productos_df['Referencia'] == item_row.get('Referencia')]
                if not info_producto.empty:
                    stock_actual = info_producto.iloc[0].get('Stock', 0)
                    # Si el costo no está en la hoja de items, lo busca en la de productos
                    if costo_unitario_cargado == 0:
                         costo_unitario_cargado = float(info_producto.iloc[0].get('Costo', 0) or 0)

                item_cargado = {
                    'Referencia': item_row.get('Referencia'),
                    'Producto': item_row.get('Producto'),
                    'Cantidad': int(item_row.get('Cantidad', 0)),
                    'Precio Unitario': float(str(item_row.get('Precio_Unitario', '0')).replace(',', '.') or 0),
                    'Descuento (%)': float(str(item_row.get('Descuento_Porc', '0')).replace(',', '.') or 0),
                    'Total': float(str(item_row.get('Total_Item', '0')).replace(',', '.') or 0),
                    'Stock': stock_actual,
                    'Costo': costo_unitario_cargado
                }
                self.cotizacion_items.append(item_cargado)

            self.recalcular_totales()
            self.persist_to_session()
            if not silent: st.success(f"Propuesta {numero_propuesta} cargada para edición.")
            return True
        except Exception as e:
            if not silent: st.error(f"Error al cargar la propuesta: {e}")
            return False

    def persist_to_session(self):
        st.session_state.state = self
