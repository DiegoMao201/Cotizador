# state.py
import streamlit as st
import pandas as pd
from datetime import datetime
from utils import DETALLE_PROPUESTAS_SHEET_NAME, PROPUESTAS_SHEET_NAME, TASA_IVA, cargar_datos_maestros

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
        self.subtotal_bruto = 0.0
        self.descuento_total = 0.0
        self.iva_valor = 0.0
        self.total_general = 0.0
        self.recalcular_totales()

    def set_numero_propuesta(self, numero):
        self.numero_propuesta = numero
        self.persist_to_session()

    def set_cliente(self, cliente_dict):
        """Establece el cliente actual para la cotización."""
        self.cliente_actual = cliente_dict
        self.persist_to_session()

    def set_vendedor(self, nombre_vendedor):
        """Establece el vendedor."""
        self.vendedor = nombre_vendedor
        self.persist_to_session()

    def agregar_item(self, producto_dict, cantidad, precio_unitario):
        """Agrega un nuevo producto a la lista de la cotización."""
        total_item = cantidad * precio_unitario
        nuevo_item = {
            'Referencia': producto_dict.get('Referencia', 'N/A'),
            'Producto': producto_dict.get('Producto', 'N/A'),
            'Cantidad': cantidad,
            'Precio Unitario': precio_unitario,
            'Descuento (%)': 0.0, # El descuento inicial es 0
            'Total': total_item,
            'Stock': producto_dict.get('Stock', 0)
        }
        self.cotizacion_items.append(nuevo_item)
        self.recalcular_totales()
        self.persist_to_session()

    def actualizar_items_desde_vista(self, df_vista):
        """Actualiza la lista completa de items a partir del DataFrame editado en la UI."""
        nuevos_items = []
        # Crear un mapa de referencia a item para búsqueda rápida
        mapa_items_actuales = {item['Referencia']: item for item in self.cotizacion_items}

        for _, row in df_vista.iterrows():
            item_completo = mapa_items_actuales.get(row['Referencia'], {})
            item_actualizado = {
                **item_completo, # Mantiene datos no visibles como el Stock
                'Cantidad': row['Cantidad'],
                'Precio Unitario': row['Precio Unitario'],
                'Descuento (%)': row['Descuento (%)'],
            }
            nuevos_items.append(item_actualizado)
        
        self.cotizacion_items = nuevos_items
        self.recalcular_totales()
        self.persist_to_session()

    def recalcular_totales(self):
        """Recalcula todos los totales basados en los items actuales."""
        subtotal = 0
        descuento_total_valor = 0
        
        for item in self.cotizacion_items:
            cantidad = item.get('Cantidad', 0)
            precio = item.get('Precio Unitario', 0)
            descuento_pct = item.get('Descuento (%)', 0)
            
            total_bruto_item = cantidad * precio
            descuento_valor_item = total_bruto_item * (descuento_pct / 100)
            total_neto_item = total_bruto_item - descuento_valor_item
            
            item['Total'] = total_neto_item
            subtotal += total_bruto_item
            descuento_total_valor += descuento_valor_item

        self.subtotal_bruto = subtotal
        self.descuento_total = descuento_total_valor
        subtotal_neto = self.subtotal_bruto - self.descuento_total
        self.iva_valor = subtotal_neto * TASA_IVA
        self.total_general = subtotal_neto + self.iva_valor

    def reiniciar_cotizacion(self):
        """Resetea el estado a sus valores iniciales."""
        self.__init__()
        self.persist_to_session()
        st.success("Se ha iniciado una nueva cotización.")

    def cargar_desde_gheets(self, numero_propuesta, workbook, silent=False):
        """Carga el estado completo de una propuesta desde Google Sheets."""
        try:
            propuestas_sheet = workbook.worksheet(PROPUESTAS_SHEET_NAME)
            propuesta_data = propuestas_sheet.find(numero_propuesta)
            if not propuesta_data:
                if not silent: st.error(f"No se encontró la propuesta {numero_propuesta}.")
                return False
            
            propuesta_row = propuestas_sheet.row_values(propuesta_data.row)
            self.numero_propuesta = propuesta_row[0]
            
            clientes_df, _ = cargar_datos_maestros(workbook)
            cliente_nombre = propuesta_row[2]
            cliente_info = clientes_df[clientes_df['Cliente'] == cliente_nombre]
            if not cliente_info.empty:
                self.cliente_actual = cliente_info.iloc[0].to_dict()

            self.vendedor = propuesta_row[3]
            self.status = propuesta_row[5]
            self.observaciones = propuesta_row[6]

            detalle_sheet = workbook.worksheet(DETALLE_PROPUESTAS_SHEET_NAME)
            all_items = detalle_sheet.get_all_records()
            productos_df, _ = cargar_datos_maestros(workbook)
            
            self.cotizacion_items = []
            items_propuesta = [item for item in all_items if item.get('N° Propuesta') == numero_propuesta]

            for item_row in items_propuesta:
                descuento_cargado = float(str(item_row.get('Descuento', '0')).replace(',', '.') or 0)
                
                stock_actual = 0
                info_producto = productos_df[productos_df['Referencia'] == item_row.get('Referencia')]
                if not info_producto.empty:
                    stock_actual = info_producto.iloc[0].get('Stock', 0)

                item_cargado = {
                    'Referencia': item_row.get('Referencia'),
                    'Producto': item_row.get('Producto'),
                    'Cantidad': int(item_row.get('Cantidad', 0)),
                    'Precio Unitario': float(str(item_row.get('Precio Unitario', '0')).replace(',', '.') or 0),
                    'Descuento (%)': descuento_cargado,
                    'Total': float(str(item_row.get('Total', '0')).replace(',', '.') or 0),
                    'Stock': stock_actual
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
        """Guarda la instancia actual en st.session_state."""
        st.session_state.state = self
