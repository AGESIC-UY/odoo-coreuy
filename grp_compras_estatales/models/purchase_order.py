# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
#    Proyecto:   GRP
#    Fecha:      2014
#    Autor:      Quanam
#    Compañia:  Quanam - www.quanam.com
#    Adecuacion: Compras
##############################################################################
# Ref  Id Tarea   Desa       Fecha        Descripcion
# --------------------------------------------------------------------------------------------
##############################################################################

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
import datetime
import time
from lxml import etree
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from datetime import datetime
from openerp import netsvc
from suds import WebFault
from suds.client import Client
import math

import logging

_logger = logging.getLogger(__name__)

class grp_orden_compra(osv.osv):
    _inherit = 'purchase.order'

    # PCARBALLO selection plazo_entrega
    _PLAZOS_ENTREGA = [
        ('INM', 'Inmediata'),
        ('15D', u'15 días'),
        ('30D', u'30 días'),
        ('45D', u'45 días'),
        ('60D', u'60 días'),
        ('100D', u'100 días'),
        ('ACOOR', 'A Coordinar'),
    ]

    _METODOS_PAGO = [
        ('CON', 'Contado'),
        ('15DF', u'15 días fecha factura'),
        ('30DF', u'30 días fecha factura'),
        ('45DF', u'45 días fecha factura'),
        ('60DF', u'60 días fecha factura'),
        ('APLIEG', u'De acuerdo a Pliego'),
        ('ACONT', u'De acuerdo a Contrato'),
        ('ADETA', u'De acuerdo a detalle'),
    ]
    # PCARBALLO

    # TODO Spring 6 GAP 468
    STATE_SELECTION = [
        ('draft', 'Draft PO'),
        ('sent', 'RFQ Sent'),
        ('bid', 'Bid Received'),
        # ('in_approved', u'En Aprobación'), # cambiado por estado en_aprobacion por incidencia 592
        # ('en_aprobacion', u'En Aprobación'),
        # 004 Inicio  echaviano
        # ('in_auth_odg', u'En Autorización Ordenador'), # incidencia 111 , cambiado de Autorizado ODF a En Autorización ODG
        # cambiar Autorizado ODG y En Autorizacion ODG por Auotrizado Ordenador y En Autorización Ordenador
        # 004 Fin
        ('confirmed', 'OC Confirmado'),
        ('approved', 'Purchase Confirmed'),
        # De flag pasar a estados despues de aprobada 03/11
        # ('en_auth_ordenador',u'En Autorización Ordenador'),
        # ('in_auth_odg',u'En Autorización Ordenador'),
        # ('auth_ordenador',u'Autorizada Ordenador'),
        # ('enviar_sice', u'Enviado a SICE'), # quitado como estado
        ('except_picking', u'Shipping Exception'),
        ('except_invoice', u'Invoice Exception'),
        # ('oc_confirmado', u'Comprometido'),  #Comprometido'),
        # ('oc_confirmado', u'OC Confirmado'),  # Comprometido'),
        # ('committed', 'Comprometido'),
        ('done', u'OC Cerrada'),
        ('closed', 'Done'),
        ('cancel', 'Cancelled'),
        # ('rejected', 'Rechazado'),  por ahora es el mismo que cancelar
        # ('accepted_odg', 'Autorizado ODG'),   es el mismo que Pedido de Compras = Purchase Order, no puedo cambiarlo
        #  para no cambiar lo original de la orden de compras
    ]

    # #PCAR
    # ODG_SELECTION = [
    #     ('prim', 'Primario'),
    #     ('sec', 'Secundario'),
    # ]
    # #PCAR

    def _get_tipo_compra(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        pedido_compra_obj = self.pool.get('grp.pedido.compra')
        for purchase in self.browse(cr, uid, ids, context=context):
            res[purchase.id] = '-'
            if purchase.pedido_compra_id:
                pedidoc = pedido_compra_obj.browse(cr, uid, [purchase.pedido_compra_id.id], context=context)[0]
                if pedidoc:
                    res[purchase.id] = pedidoc.tipo_compra.descTipoCompra
                else:
                    res[purchase.id] = '-'
        return res

    # 007-Inicio
    def _get_recibir_prod(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            cond = False
            for line in obj.order_line:
                cond = cond or (line.product_id.type in ['product', 'consu'])
            res[obj.id] = cond
        return res

    # 007-Fin

    def onchange_location(self, cr, uid, ids, location_id, context=None):
        value = {}
        if location_id:
            ubicacion = self.pool.get('stock.location').browse(cr, uid, location_id, context=context)
            warehouse = self.pool.get('stock.location').get_warehouse(cr, uid, ubicacion, context=None)
            pick_type_id = self.pool.get('stock.picking.type').search(cr, uid, [('code', '=', 'incoming'),
                                                                                ('warehouse_id', '=', warehouse)])
            if len(pick_type_id) > 0:
                pick_type_id = pick_type_id[0]
            value.update({'picking_type_id': pick_type_id, 'pick_type_cpy': pick_type_id})
        return {'value': value}

    def _get_copy(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.picking_type_id.id
        return res

    def _get_referencia_cpy(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.referencia
        return res

    def _get_tipo_compra_cpy(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.tipo_compra.id
        return res

    def _get_total_lineas(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = len(rec.order_line) or 0
        return res

    def _get_tipo_de_cambio_fnc ( self, cr, uid, ids, fieldname, args, context = None ):
        res = { }
        for lines in self.browse ( cr, uid, ids, context = context ):
            res[lines.id] = lines.tipo_de_cambio
        return res

    def _get_responsable_siif_editable(self, cr, uid, ids, fields, args, context=None):
        res = {}
        in_grp = self.pool.get('res.users').has_group(cr,uid,'grp_seguridad.grp_compras_apg_Responsable_SIIF')
        for record in self.browse ( cr, uid, ids, context = context ):
            res[record.id] = {
                'responsable_siif_editable': (True and record.state in ('confirmed') and in_grp) or False,
                'resp_siif_en_financiero': (True and record.en_financiero and in_grp) or False,
            }
        return res

    # Incidencia 016 Inicio
    def _get_total_convert(self, cr, uid, ids, fields, args, context=None):
        res = {}
        context = dict(context)
        currency_obj = self.pool.get('res.currency')
        orders = self.browse(cr, uid, ids, context=context)
        for order in orders:
            res[order.id] = {
                'amount_untaxed':0,
                'amount_tax':0,
            }
            moneda = order.currency_oc.id
            moneda_base = order.company_id.currency_id.id
            if moneda != moneda_base:
                context.update({'date': order.fecha_tipo_cambio_oc or time.strftime('%Y-%m-%d'), 'pricelist_type':'presupuesto'})
                # monto = currency_obj.compute(cr, uid, moneda, moneda_base, order.amount_total, context)
                # cambio el round del monto total en pesos 19/11
                amount_mb = round(currency_obj.compute(cr, uid, moneda, moneda_base, order.amount_total, context=context))
            else:
                amount_mb = round(order.amount_total)

            res[order.id]['amount_total_base'] = amount_mb or 0
            res[order.id]['amount_total_cpy'] = round(order.amount_total)
        return res
    # Incidencia 016 Fin metodo

    def _get_dif_moneda_fnc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for order in self.browse(cr,uid,ids,context=context):
            # moneda = order.currency_oc.id
            # moneda_base = order.company_id.currency_id.id
            res[order.id] = True and order.currency_oc.id != order.company_currency_id.id or False
        return res

    # agregados, para modificacion de wkf - 08/01
    def _invoiced_grp(self, cursor, user, ids, name, arg, context=None):
        res = {}
        # verificar que todas las lineas tengan facturadas las cantidades
        for purchase in self.browse(cursor, user, ids, context=context):
            if purchase.invoice_method == 'picking':
                res[purchase.id] = True
            else:
                res[purchase.id] = all(line.qty_invoiced == line.product_qty for line in purchase.order_line)
            # res[purchase.id] = all(line.cantidad_facturada == line.product_qty for line in purchase.order_line)
        return res

    def _default_es_apg_jefe_compras(self, cr, uid, context=None):
        return (self.pool.get('res.users').has_group(cr,uid,'grp_seguridad.grp_compras_apg_Jefe_de_compras_2') and (uid!=SUPERUSER_ID) ) or (uid==SUPERUSER_ID)

    def _default_es_apg_jefe_financiero(self, cr, uid, context=None):
        return (self.pool.get('res.users').has_group(cr,uid,'grp_seguridad.grp_compras_apg_Jefe_de_compras') and (uid!=SUPERUSER_ID) ) or (uid==SUPERUSER_ID)


    def _es_apg_jefe(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = (self.pool.get('res.users').has_group(cr,uid,'grp_seguridad.grp_compras_apg_Jefe_de_compras_2') and (uid!=SUPERUSER_ID) ) or (uid==SUPERUSER_ID)
        return res

    def _es_apg_jefe_financiero(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = (self.pool.get('res.users').has_group(cr,uid,'grp_seguridad.grp_compras_apg_Jefe_de_compras') and (uid!=SUPERUSER_ID) ) or (uid==SUPERUSER_ID)
        return res

    def _es_resp_siif(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = (self.pool.get('res.users').has_group(cr,uid,'grp_seguridad.grp_compras_apg_Responsable_SIIF') and (uid!=SUPERUSER_ID) ) or (uid==SUPERUSER_ID)
        return res

    def _es_almacenero(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = (self.pool.get('res.users').has_group(cr,uid,'grp_seguridad.grp_compras_sr_Encargado_de_almacen') and (uid!=SUPERUSER_ID) ) or (uid==SUPERUSER_ID)
        return res

    def _apg_no_afectada(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.pc_apg_id and rec.pc_apg_id.state != 'afectado' or False
        return res

    def _default_es_almacenero(self, cr, uid, context=None):
        return (self.pool.get('res.users').has_group(cr,uid,'grp_seguridad.grp_compras_sr_Encargado_de_almacen') and (uid!=SUPERUSER_ID) ) or (uid==SUPERUSER_ID)

    #002 Pasado 03/11
    def get_comprometido(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for order in self.browse(cr,uid,ids,context=context):
            res[order.id] = order.comprometido and u'SI' or u'NO'
        return res

    #002 Pasado 03/11
    def get_numero_afectacion(self, cr, uid, ids, name, args, context=None):
        result = {}
        for rec in self.browse(cr,uid,ids,context=context):
            result[rec.id]= rec.pc_apg_id and rec.pc_apg_id.nro_afectacion_siif or 0
        return result

    # #009 - Comprobacion de compra directa
    # def _get_es_cd(self, cr, uid, ids, name, args, context=None):
    #     res = {}
    #     for rec in self.browse(cr, uid, ids, context=context):
    #         dt = datetime.strptime(rec.date_order, '%Y-%m-%d %H:%M:%S')
    #         anio = dt.year
    #         # _logger.info("ANIO: %s", anio)
    #         monto_compras_id = self.pool.get('grp.monto.compras').search(cr, uid, [('anio_vigencia','=',anio)])
    #         monto_compras_obj = self.pool.get('grp.monto.compras').browse(cr, uid, monto_compras_id, context=context)
    #         desc = 'NA'
    #         if rec.pedido_compra_id and rec.pedido_compra_id.tipo_compra.idTipoCompra == 'CD':
    #             monto = 0.0
    #             for line in monto_compras_obj.linea_ids:
    #                 if line.tipo_compra_id.idTipoCompra == 'CD':
    #                     monto = line.hasta
    #             # _logger.info("TIPO COMPRAA: %s", monto)
    #             if rec.amount_total_base <= (monto/2):
    #                 desc = 'MENOR'
    #             else:
    #                 desc = 'MAYOR'
    #         res[rec.id] = desc
    #     return res

    # Se sobreescribe metodo _count_all del estandar
    # ahora no solo cuenta los picking de la OC, sino tambien sus reversiones
    def _count_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for purchase in self.browse(cr, uid, ids, context=context):
            res[purchase.id] = {
                'shipment_count': 0,
                'invoice_count': len(purchase.invoice_ids),
            }
            pick_ids = []
            for p in purchase.picking_ids:
                if p.state in ['done']:
                    p_ids = self.pool.get('stock.picking').search(cr, uid, [('origin', '=', p.name)])
                    pick_ids += p_ids
            res[purchase.id]['shipment_count'] = len(purchase.picking_ids) + len(pick_ids)
        return res

    _columns = {
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True,
                                  help="The status of the purchase order or the quotation request. A quotation is a purchase order in a 'Draft' status. Then the order has to be confirmed by the user, the status switch to 'Confirmed'. Then the supplier must confirm the order to change the status to 'Approved'. When the purchase order is paid and received, the status becomes 'Done'. If a cancel action occurs in the invoice or in the reception of goods, the status becomes in exception.",
                                  select=True, track_visibility='onchange'),
        'responsable_siif_editable': fields.function(_get_responsable_siif_editable, multi='editable', type='boolean'),
        'resp_siif_en_financiero': fields.function(_get_responsable_siif_editable, multi='editable', type='boolean'),
        'tipo_de_cambio_fnc': fields.function(_get_tipo_de_cambio_fnc, string='Tipo de cambio', type='float',
                                              digits=(10, 5)),
        'fecha_tipo_cambio_oc': fields.date('Fecha de tipo de cambio'),
        'company_currency_id': fields.related('company_id', 'currency_id', type="many2one", relation="res.currency",
                                         string="Moneda empresa", readonly=True),
        'diference_moneda': fields.function(_get_dif_moneda_fnc, string='Diferente moneda', type='boolean'),
        'amount_total_base': fields.function(_get_total_convert, multi='amount', string=u'Total estimado pesos',
                                             type='float', digits=(16, 0)),
    # digits_compute=dp.get_precision ( 'Cantidad' ) ),
        'amount_total_cpy': fields.function(_get_total_convert, multi='amount', string=u'Total', type='float',
                                            digits=(16, 0)),  # digits_compute=dp.get_precision ( 'Cantidad' ) ),

        # 'sequence': fields.char(u'Id. Ordenes de Compra', size=32, readonly=True),
        'pedido_compra_id': fields.many2one('grp.pedido.compra', 'Pedido de Compra', help=u'Pedido de compra'),
        'doc_origen': fields.many2one('grp.cotizaciones', 'Documento de Origen', help=u'Cotización'),
        # 'odg_cot': fields.many2one('res.users', 'Ordenador del Gasto', help='Ordenador del gasto'),
        'currency_oc': fields.many2one('res.currency', 'Moneda'),
        'tipo_de_cambio': fields.float('Tipo de cambio', digits=(10, 5)),
        'nro_compromiso': fields.char('Nro. de compromiso'),
        'descripcion': fields.text(u'Descripción', size=200),  # Descripcion incidencia agregar observacion igual que PC
        'plazo_pago': fields.char('Plazo de entrega'),  # Plazo de pago
        'terminos_condiciones': fields.text(u'Condiciones de pago'),  # Términos y Condiciones
        'dependencia_lugar': fields.char(u'Dependencia y lugar', size=50),  # nuevo campo agregar
        'sice_nro': fields.integer(string=u'Nro. SICE', help=u'Nro. SICE'),
        # Interfaz SIIF
        # Campos APG
        'pc_apg_id': fields.many2one('grp.compras.apg', u'Nro. de APG'),
        # Pestaña APG
        'page_apg_oc': fields.one2many('grp.cotizaciones.lineas.apg.oc', 'order_id', 'APG'),
        'tipo_compra_char': fields.function(_get_tipo_compra, string='Tipo de compra', type='char'),
        'cod_moneda': fields.many2one('sicec.moneda', u'Código moneda SICE'),
        'plazo_entrega': fields.boolean('Plazo de entrega inmediata'),
        'pick_type_cpy': fields.function(_get_copy, type='many2one', relation='stock.picking.type', string=u"Almacén"),
        'plazo_entrega_sel': fields.selection(_PLAZOS_ENTREGA, u'Plazo de entrega'),
        'forma_pago': fields.selection(_METODOS_PAGO, u'Forma de pago'),
        'centro_de_costos': fields.many2one('account.analytic.account', u'Centro de costos'),
        'boton_recibir_prod': fields.function(_get_recibir_prod, type='boolean', string=u"Recibir productos?"),
        'referencia': fields.char('Referencia'),
        'referencia_cpy': fields.function(_get_referencia_cpy, type='char', string='Referencia'),
        'horario_dir': fields.text(u'Dirección y horario'),
        'total_lineas': fields.function(_get_total_lineas, method=True, type='integer', string=u'Total líneas'),

        'tipo_compra': fields.related('pedido_compra_id', 'tipo_compra', type='many2one', relation='sicec.tipo.compra',
                                      string='Tipo de Compra', store=True),
        'invoiced_grp': fields.function(_invoiced_grp, string=u'Invoice All Received', type='boolean',
                                        help="It indicates that an invoice has been paid"),
        'es_apg_jefe_compras': fields.function(_es_apg_jefe, type='boolean', string=u'Es jefe de compras?'),
        'es_apg_jefe_financiero': fields.function(_es_apg_jefe_financiero, type='boolean',
                                                  string=u'Es jefe financiero?'),
        'es_almacenero': fields.function(_es_almacenero, type='boolean', string=u'Es almacenero?'),
        'sice_nro_oc': fields.integer(u'Nro. OC SICE', track_visibility='onchange'),
        'sice_id_oc': fields.integer(u'Id OC SICE', track_visibility='onchange'),
        'enviado_sice': fields.boolean(u'Enviado SICE'),
        'en_financiero': fields.boolean(u'En Financiero'),

        'comprometido': fields.boolean(u'Comprometido'),
        'comprometido_char': fields.function(get_comprometido, type='char', string=u'Comprometido'),
        'nro_afectacion_siif': fields.function(get_numero_afectacion, string=u'Nro Afectación SIIF', type='integer'),
        'unidad': fields.many2one('hr.department', 'Unidad'),
        # 'tipo_odg': fields.selection(ODG_SELECTION, 'Tipo de ODG'),
        # 'se_envia_sice': fields.boolean(u'Se envía a SICE?'),
        # 'se_envia_siif': fields.boolean(u'Se envía a SIIF?'),
        # 'es_cd_mayor_menor': fields.function(_get_es_cd, type='char', size=10, string='Es compra directa'),
        'mostrar_apg_no_afectada': fields.function(_apg_no_afectada, type='boolean', string=u'APG no afectada?'),
        'shipment_count': fields.function(_count_all, type='integer', string='Incoming Shipments', multi=True),
        'invoice_count': fields.function(_count_all, type='integer', string='Invoices', multi=True)
    }

    _defaults = {
        'recibir_prod_pres': False,
        'currency_oc': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.currency_id.id,
        'es_apg_jefe_compras': _default_es_apg_jefe_compras,
        'es_apg_jefe_financiero': _default_es_apg_jefe_financiero,
        'es_almacenero': _default_es_almacenero,
    }

    def onchange_centro_de_costos(self, cr, uid, ids, centro_de_costos, context=None):
        value = {}
        if centro_de_costos:
            analytic_obj = self.pool.get('account.analytic.account').browse(cr, uid, centro_de_costos, context=context)[
                0]
            ref = analytic_obj.code
            value.update({'referencia': ref, 'referencia_cpy': ref})
        return {'value': value}

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        if values.get('currency_oc', False) and not values.get('currency_id', False):
            values['currency_id'] = values['currency_oc']
        # Si no viene el año fiscal en el contexto, lo intento obtener de values
        # si no viene en values lo obtengo de la fecha actual
        if not context.get('fiscalyear_id', False):
            fiscalyear_obj = self.pool.get('account.fiscalyear')
            uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            fiscal_year = values.get('fiscalyear_siif_id', False)
            fecha_hoy = values.get('date_order', False)
            context = dict(context)
            if fiscal_year:
                context.update({'fiscalyear_id': fiscal_year})
            elif fecha_hoy:
                fiscal_year_id = fiscalyear_obj.search(cr, uid,
                                                       [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
                                                        ('company_id', '=', uid_company_id)], context=context)
                fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
                context.update({'fiscalyear_id': fiscal_year_id})
        # values['name'] = self.pool.get('ir.sequence').get(cr, uid, 'oc.number', context=context)
        sequence = self.pool.get('ir.sequence').get(cr, uid, 'oc.number', context=context)
        ind= sequence.index('-') +1
        inciso = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.inciso
        values['name'] = sequence[0:ind] +inciso + sequence[ind:len(sequence)]
        if values.get('order_line', False):
            for line in values['order_line']:
                if isinstance(line[2], dict):
                    if line[2].get('price_unit', False):
                        # _logger.info("Precio unitario: %s", line[2]['price_unit'])
                        if line[2]['price_unit'] == 0:
                            raise osv.except_osv(('Error!'), ('El precio unitario debe ser no nulo.'))
        # # Cuando se viene copiando no valida
        # if values.get('pedido_compra_id', False) and not context.has_key('copy') and not context.get('copy', False):
        #     if not values.get('pc_apg_id', False):
        #         raise osv.except_osv(('Error!'), ('Debe seleccionar una APG asociada al pedido de compras.'))
        #     if values.get('pc_apg_id', False):
        #         apg = self.pool.get('grp.compras.apg').browse(cr, uid, values.get('pc_apg_id'))
        #         # if apg.state not in ['autorizado_ODG', 'afectado']:
        #         if apg.state != 'afectado':
        #             raise osv.except_osv(('Error!'),
        #                                  (u'La APG seleccionada no está en estado Afectado.'))
        #                                  # ('La apg seleccionada no está en estado Autorizado o Afectado.'))
        return super(grp_orden_compra, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if values.get('currency_oc', False) and 'currency_id' not in values:
            values['currency_id'] = values['currency_oc']
        if values.get('order_line', False):
            for line in values['order_line']:
                if isinstance(line[2], dict):
                    if line[2].get('price_unit', False):
                        if line[2]['price_unit'] == 0:
                            raise osv.except_osv(('Error!!'), ('El precio unitario debe ser no nulo.'))
        # if values.get('pedido_compra_id', False):
        #     id_pedido = values.get('pedido_compra_id', False)
        #     pedido = self.pool.get('grp.pedido.compra').browse(cr, uid, id_pedido)
        #
        #     apg_autorizado = False
        #     if pedido.apg_ids:
        #         for apg in pedido.apg_ids:
        #             # if apg.state in ['autorizado_ODG',
        #             #                  'afectado']:  # Puede ser afectado, pues se supone que paso ya por el autorizado
        #             if apg.state == 'afectado':
        #                 apg_autorizado = True
        #                 break
        #     if not apg_autorizado:
        #         raise osv.except_osv(('Error!'),
        #                              (u'El pedido de compra seleccionado no tiene APGs en estado Afectado.'))

        return super(grp_orden_compra, self).write(cr, uid, ids, values, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for purchase in self.browse(cr, uid, ids, context=context):
            for pick in purchase.picking_ids:
                if pick.state not in ('draft','cancel'):
                    raise osv.except_osv(
                        _('Unable to cancel this purchase order.'),
                        _('First cancel all receptions related to this purchase order.'))
            for pick in purchase.picking_ids:
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_cancel', cr)
            for inv in purchase.invoice_ids:
                if inv and inv.state not in ('cancel','draft','cancel_sice','cancel_siif'):
                    raise osv.except_osv(
                        _('Unable to cancel this purchase order.'),
                        _('Primero tiene que cancelar todas las facturas relacionas con este pedido de compra.'))
                if inv and inv.state in ('draft',):
                    wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_cancel', cr)
        self.write(cr,uid,ids,{'state':'cancel'})

        for (id, name) in self.name_get(cr, uid, ids):
            wf_service.trg_validate(uid, 'purchase.order', id, 'purchase_cancel', cr)
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'doc_origen': False,
            'origin': False,
            'name': 'OC Borrador',
            'nro_compromiso': False,
            'pc_apg_id': False,
            'page_apg_oc': [],
            'enviado_sice': False,
            'en_financiero': False,
            'comprometido': False,
            # 'en_auth_ordenador': False,
            # 'auth_ordenador': False,
        })
        context = context or {}
        context=dict(context)
        context.update({'copy':True}) #Perder el control de estado desafectado cuando se copia
        return super(grp_orden_compra, self).copy(cr, uid, id, default, context)

    def onchange_pedido(self, cr, uid, ids, pedido_compra_id, doc_origen, context=None):
        if context is None:
            context = dict({})
        result = {}
        result.setdefault('value', {})
        result['value'] = {'sice_nro': False, 'pc_apg_id': False, 'page_apg_oc': []}

        # desvincular existentes
        if ids:
            self.write(cr, uid, ids, {'pc_apg_id': False, 'page_apg_oc': [(5,)]}, context=context)
            # AGREGAR CAMBIO PARA V8 pues da error 26/11
            pedido = self.browse(cr, uid, ids)
            result['value'].update({'currency_oc': pedido.currency_oc.id or False,
                                    'currency_id': pedido.currency_oc.id or False,
                                    'pricelist_id': pedido.pricelist_id.id or False,
                                    # 'odg_cot': pedido.odg_cot and pedido.odg_cot.id or False,
                                    'partner_id': pedido.partner_id and pedido.partner_id.id or False,
                                    'fecha_tipo_cambio_oc': pedido.fecha_tipo_cambio_oc or False,
                                    'date_order': pedido.date_order or False,
                                    'centro_de_costos': pedido.centro_de_costos and pedido.centro_de_costos.id or False,
                                    'location_id': pedido.location_id and pedido.location_id.id or False})
        order_line_ids = []
        if not pedido_compra_id:
            return result
        pc = self.pool.get('grp.pedido.compra').browse(cr, uid, pedido_compra_id, context=context)

        result['value'].update({'pc_apg_id': False})
        default_apg_ids = []
        if pc.apg_ids:
            for apg in pc.apg_ids:
                default_apg_ids.append(apg.id)
            default_tuple_apg_ids = tuple(default_apg_ids)
            default_apg_id = max(default_tuple_apg_ids)
            result['value'].update({'pc_apg_id': default_apg_id})

        if pc.moneda:
            result['value'].update({'currency_oc': pc.moneda.id, 'currency_id': pc.moneda.id })

        result['value'].update({'sice_nro': pc.sice_id_compra, 'pedido_compra_id': pedido_compra_id})

        for linea in pc.lineas_ids:
            descrp = linea.sc_descripcion
            if not descrp:
                descrp = linea.product_id.name
            order_line_ids.append((0, 0, {'product_id': linea.product_id.id,
                                          'name': descrp,
                                          'date_planned': datetime.today().strftime("%Y-%m-%d"),
                                          'product_qty': linea.cantidad_comprar_sice,
                                          'product_uom': linea.uom_id.id,
                                          'price_unit': linea.precio_estimado,
                                          'taxes_id': [(6, 0, [x.id for x in linea.iva])],
                                          'state': 'draft'}))
        result['value'].update({'order_line': order_line_ids})
        return result

    def onchange_pc_apg_id(self, cr, uid, ids, pc_apg_id, pedido_compra_id, context=None):
        result = {'value': {}}
        return result

    def onchange_date_currency_id(self, cr, uid, ids, currency_id, date_order, context=None):
        if context is None:
            context = {}
        context = dict(context)
        if not currency_id:
            if ids:
                self.write(cr, uid, ids, {'tipo_de_cambio': False})
            return {'value': {'tipo_de_cambio': False}}
        if date_order:
            context.update({'date': date_order})
        else:
            context.update({'date': time.strftime('%Y-%m-%d')})
        currency = self.pool.get('res.currency').browse(cr, uid, currency_id, context=context)
        # Cambio al tipo de cambio moneda para presupuesto 09/10
        rate = 0
        if currency.rate_presupuesto != 0:
            rate = currency.rate_presupuesto
        if ids:
            self.write(cr, uid, ids, {'tipo_de_cambio': rate, 'tipo_de_cambio_fnc':rate})
        return {'value': {'tipo_de_cambio': rate, 'tipo_de_cambio_fnc':rate, 'currency_id': currency_id }}

    # def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
    #     if context is None:
    #         context = {}
    #     # Modificando vista para que abra custom
    #     if context.get('search_view_ref', False):
    #         if view_type == 'search':
    #             name_view = self.env['ir.ui.view'].search([('name', '=', context.get('search_view_ref'))])
    #             if name_view:
    #                 view_id = name_view[0].id
    #     res = super(grp_orden_compra, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
    #                                                             context=context,
    #                                                             toolbar=toolbar, submenu=submenu)
    #     model_data_obj = self.pool.get('ir.model.data')
    #     res_groups_obj = self.pool.get('res.groups')
    #     usr_obj = self.pool.get('res.users')
    #     # PCAR
    #     es_ord_sec = usr_obj.has_group(cr, uid, 'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_secundario')
    #     es_ord_prim = usr_obj.has_group(cr, uid, 'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_primario')
    #
    #     group_verifier_id = False
    #     if es_ord_prim:
    #         group_verifier_id = model_data_obj._get_id(cr, uid, 'grp_seguridad',
    #                                                    'grp_compras_apg_Ordenador_del_gasto_primario')
    #     elif es_ord_sec:
    #         group_verifier_id = model_data_obj._get_id(cr, uid, 'grp_seguridad',
    #                                                    'grp_compras_apg_Ordenador_del_gasto_secundario')
    #     else:
    #         group_verifier_id = model_data_obj._get_id(cr, uid, 'grp_seguridad',
    #                                                    'grp_compras_apg_Ordenador_del_gasto')
    #     # PCAR
    #     if group_verifier_id:
    #         res_id = model_data_obj.read(cr, uid, [group_verifier_id], ['res_id'])[0]['res_id']
    #         group_verifier = res_groups_obj.browse(cr, uid, res_id, context=context)
    #         group_user_ids = [user.id for user in group_verifier.users]
    #         domain_user = str([('id', 'in', group_user_ids)])
    #     if domain_user:
    #         doc = etree.XML(res['arch'])
    #         for node in doc.xpath("//field[@name='odg_cot']"):
    #             node.set('domain', domain_user)
    #         res['arch'] = etree.tostring(doc)
    #     return res

    # def purchase_send_approve_btn(self, cr, uid, ids, context=None):
    #     wf_service = netsvc.LocalService("workflow")
    #     self.write(cr,uid,ids,{'state':'en_aprobacion'})
    #     #TODO: Revisar esto, por que llama de nuevo a la señal que lo disparo???
    #     for (id, name) in self.name_get(cr, uid, ids):
    #         wf_service.trg_validate(uid, 'purchase.order', id, 'purchase_send_approve', cr)
    #     return True

    # #001-Inicio
    # #Onchange que al cambiar el campo odg_cot se modifica el valor del campo tipo_odg.
    # def onchange_odg_cot(self, cr, uid, ids, odg_id):
    #     if odg_id:
    #         usr_obj = self.pool.get('res.users')
    #         es_ord_prim = usr_obj.has_group(cr,odg_id,'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_primario')
    #         #es_ord_sec = usr_obj.has_group(cr,odg_id,'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_secundario')
    #         if es_ord_prim:
    #             return {'value': {'tipo_odg': 'prim'}}
    #         else:
    #             return {'value': {'tipo_odg': 'sec'}}
    #     else:
    #         return {}

    # sobreescribiendo el metodo original
    #006 Inicio
    def action_cancel_draft(self, cr, uid, ids, context=None):
        if not len(ids):
            return False
        values = {
            'en_financiero':False,
            'enviado_sice': False,
            # 'en_auth_ordenador': False,
            # 'auth_ordenador': False,
        }
        self.write(cr, uid, ids, values, context)
        return super(grp_orden_compra,self).action_cancel_draft(cr, uid, ids, context=context)
    #006 Fin

    # # Cambiado, echaviano 19/01
    # def purchase_send_to_approve(self, cr, uid, ids, context=None):
    #     #PCAR 27 01 2016
    #     # PCARBALLO : se comprueba que el ODG seleccionado sea del tipo correspondiente segun el total.
    #     self_obj = self.pool.get('purchase.order').browse(cr, uid, ids[0], context=context)
    #     _logger.info("Ordenador: %s", self_obj.odg_cot.name)
    #     if self_obj.odg_cot:
    #         dt = datetime.today()
    #         anio = dt.year
    #         monto_compras_id = self.pool.get('grp.monto.aprobacion').search(cr, uid, [('anio_vigencia','=',anio)])
    #         if not monto_compras_id:
    #             raise osv.except_osv((u'Error!!'), (u'No tiene configurado los montos de aprobación por rol para el año ' + str(anio)))
    #         monto_compras_obj = self.pool.get('grp.monto.aprobacion').browse(cr, uid, monto_compras_id, context=context)
    #         _logger.info("Monto compras ID: %s OBJ: %s Anio vigencia: %s",monto_compras_id,monto_compras_obj,anio)
    #         monto_hasta_p = 0
    #         monto_desde_p = 0
    #         monto_hasta_s = 0
    #         monto_desde_s = 0
    #         _logger.info("MONTO COMPRASSS :     %s", monto_compras_obj)
    #         for line in monto_compras_obj[0].linea_ids:
    #             if line.tipo_trans == 'apg' and line.rol_id == 'odg_p':
    #                 monto_hasta_p = line.hasta
    #                 monto_desde_p = line.desde
    #             elif line.tipo_trans == 'apg' and line.rol_id == 'odg_s':
    #                 monto_hasta_s = line.hasta
    #                 monto_desde_s = line.desde
    #         _logger.info("MONTOS PRIMARIO: %s %s", monto_desde_p, monto_hasta_p)
    #         _logger.info("MONTOS SECUNDARIO: %s %s", monto_desde_s, monto_hasta_s)
    #         total = self_obj.amount_total_base
    #         if total >= monto_desde_p and total <= monto_hasta_p:
    #             if not self.pool.get('res.users').has_group(cr, self_obj.odg_cot.id, 'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_primario'):
    #                 _logger.info(" no Es primario y si aprueba ese monto")
    #                 raise osv.except_osv(('Error!!'), ('El ODG seleccionado no es un ODG primario.'))
    #         elif total >= monto_desde_s and total <= monto_hasta_s:
    #             if not self.pool.get('res.users').has_group(cr, self_obj.odg_cot.id, 'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_secundario'):
    #                 _logger.info("no Es secundario y si aprueba ese monto")
    #                 raise osv.except_osv(('Error!!'), ('El ODG seleccionado no es un ODG secundario.'))
    #     else:
    #         raise osv.except_osv(('Error!!'), ('Por favor, seleccione un ODG.'))
    #     #008- Cambios ECHAVIANO
    #     # Esto es lo que hace el metodo estandar
    #     # Cambiado metodo
    #     # self.write(cr, uid, ids, {'state': 'approved', 'date_approve': fields.date.context_today(self,cr,uid,context=context)})
    #     # self.write(cr,uid,ids,{'state':'approved'})
    #     self.button_enviar_autorizar(cr, uid, ids)
    #     #PCAR 27 01 2016
    #     return True

    # def button_confirmar_oc(self, cr, uid, ids, context=None):
    #     # PCARBALLO : se comprueba que el ODG seleccionado sea del tipo correspondiente segun el total
    #     self_obj = self.pool.get('purchase.order').browse(cr, uid, ids[0], context=context)
    #     _logger.info("Ordenador: %s", self_obj.odg_cot.name)
    #     wf_service = netsvc.LocalService("workflow")
    #     if self_obj.odg_cot:
    #         if self_obj.pedido_compra_id.tipo_compra.idTipoCompra in ['LA','LP']:
    #             _logger.info("PASA EL CONTROL DE LA LP")
    #             if not self.pool.get('res.users').has_group(cr, self_obj.odg_cot.id, 'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_primario'):
    #                 _logger.info("NO ES ODG PRIMARIO")
    #                 raise osv.except_osv(('Error!!'), ('En una licitacion abreviada o publica, el ODG seleccionado debe ser un ODG primario.'))
    #             else:
    #                 self.write(cr,uid,ids,{'state':'oc_confirmado'}) #007 - Se compromete en purchase_commit
    #                 for (id, name) in self.name_get(cr, uid, ids):
    #                     wf_service.trg_validate(uid, 'purchase.order', id, 'automatic_confirm', cr)
    #                 #     Agregado echaviano, 15/02 esto es lo que pasa de workflow
    #                 return True
    #
    #         dt = datetime.today()
    #         anio = dt.year
    #         monto_compras_id = self.pool.get('grp.monto.aprobacion').search(cr, uid, [('anio_vigencia','=',anio)])
    #         if not monto_compras_id:
    #             raise osv.except_osv(('Error!!'), (u'Debe configurar los montos de aprobación para el año %s.' % anio))
    #         monto_compras = self.pool.get('grp.monto.aprobacion').browse(cr, uid, monto_compras_id, context=context)
    #         monto_hasta_p = 0
    #         monto_desde_p = 0
    #         monto_hasta_s = 0
    #         monto_desde_s = 0
    #         _logger.info("MONTO COMPRASSS : %s", monto_compras)
    #         if monto_compras:
    #             for line in monto_compras[0].linea_ids:
    #                 if line.tipo_trans == 'apg' and line.rol_id == 'odg_p':
    #                     monto_hasta_p = line.hasta
    #                     monto_desde_p = line.desde
    #                 elif line.tipo_trans == 'apg' and line.rol_id == 'odg_s':
    #                     monto_hasta_s = line.hasta
    #                     monto_desde_s = line.desde
    #         _logger.info("MONTOS PRIMARIO: %s %s", monto_desde_p, monto_hasta_p)
    #         _logger.info("MONTOS SECUNDARIO: %s %s", monto_desde_s, monto_hasta_s)
    #         total = self_obj.amount_total_base
    #         if total >= monto_desde_p and total <= monto_hasta_p:
    #             if self.pool.get('res.users').has_group(cr, self_obj.odg_cot.id, 'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_primario'):
    #                 _logger.info("Es primario y aprueba ese monto")
    #                 # self.write(cr,uid,ids,{'state':'approved'})
    #                 # Comentado, echaviano 19/01
    #                 #PCAR 27 01 2016
    #                 #PCAR 28 01 2016
    #                 self.write(cr,uid,ids,{'state':'oc_confirmado'}) #007 - Se compromete en purchase_commit
    #                 for (id, name) in self.name_get(cr, uid, ids):
    #                     wf_service.trg_validate(uid, 'purchase.order', id, 'automatic_confirm', cr)
    #                 #     Agregado echaviano, 15/02 esto es lo que pasa de workflow
    #                 return True
    #             else:
    #                 _logger.info(" no Es primario y si aprueba ese monto")
    #                 raise osv.except_osv(('Error!!'), ('El ODG seleccionado no es un ODG primario.'))
    #         elif total >= monto_desde_s and total <= monto_hasta_s:
    #             if self.pool.get('res.users').has_group(cr, self_obj.odg_cot.id, 'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_secundario'):
    #                 _logger.info("Es secundario y si aprueba ese monto")
    #                 #PCAR 27 01 2016
    #                 #PCAR 28 01 2016
    #                 self.write(cr,uid,ids,{'state':'oc_confirmado'}) #007 - Quitado comprometido
    #                 for (id, name) in self.name_get(cr, uid, ids):
    #                     wf_service.trg_validate(uid, 'purchase.order', id, 'automatic_confirm', cr)
    #                 #     Agregado echaviano, 15/02 esto es lo que pasa de workflow
    #                 return True
    #             else:
    #                 _logger.info("no Es secundario y si aprueba ese monto")
    #                 raise osv.except_osv(('Error!!'), ('El ODG seleccionado no es un ODG secundario.'))
    #     else:
    #         raise osv.except_osv(('Error!!'), ('Por favor, seleccione un ODG.'))

    #008- Sobreescribiendo metodo original, se llama en automatic_confirm
    #TODO: ver si se deja el estado original 'confirm'
    # def wkf_confirm_order(self, cr, uid, ids, context=None):
    #     res = super(grp_orden_compra,self).wkf_confirm_order(cr, uid, ids, context=context)
    #     self.write(cr,uid,ids,{'state':'oc_confirmado'})
    #     return res
    # def wkf_confirm_order(self, cr, uid, ids, context=None):
    #     todo = []
    #     for po in self.browse(cr, uid, ids, context=context):
    #         if not any(line.state != 'cancel' for line in po.order_line):
    #             raise osv.except_osv(_('Error!'),_('You cannot confirm a purchase order without any purchase order line.'))
    #         if po.invoice_method == 'picking' and not any([l.product_id and l.product_id.type in ('product', 'consu') and l.state != 'cancel' for l in po.order_line]):
    #             raise osv.except_osv(
    #                 _('Error!'),
    #                 _("You cannot confirm a purchase order with Invoice Control Method 'Based on incoming shipments' that doesn't contain any stockable item."))
    #         for line in po.order_line:
    #             if line.state=='draft':
    #                 todo.append(line.id)
    #     self.pool.get('purchase.order.line').action_confirm(cr, uid, todo, context)
    #     for id in ids:
    #         self.write(cr, uid, [id], {'state' : 'confirmed', 'validator' : uid}, context=context)
    #     return True

    def has_stockable_product(self, cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            for order_line in order.order_line:
                if order_line.state == 'cancel':
                    continue
                if order_line.product_id and \
                  (order_line.product_id.type=='product' or \
                  (order_line.product_id.type=='consu' and not order_line.product_id.no_inventory)):
                    return True
        return False

    def action_picking_create(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids):
            source_loc = False
            if order.picking_type_id and order.picking_type_id.default_location_src_id:
                source_loc = order.picking_type_id.default_location_src_id.id
            picking_vals = {
                'picking_type_id': order.picking_type_id.id,
                'partner_id': order.partner_id.id,
                'date': order.date_order,
                'origin': order.name,
                'location_id': source_loc,
                'location_dest_id': order.location_id and order.location_id.id or False
            }
            picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
            self._create_stock_moves(cr, uid, order, order.order_line, picking_id, context=context)
        return picking_id

    def _create_stock_moves(self, cr, uid, order, order_lines, picking_id=False, context=None):
        order_line_ids = []
        for order_line in order_lines:
            if order_line.state == 'cancel' or \
               not order_line.product_id or \
               order_line.product_id.type=='service' or \
              (order_line.product_id.type=='consu' and order_line.product_id.no_inventory):
                continue
            order_line_ids.append(order_line.id)
        new_order_lines = self.pool['purchase.order.line'].browse(cr, uid, order_line_ids, context=context)
        super(grp_orden_compra, self)._create_stock_moves(cr, uid, order, new_order_lines, picking_id=picking_id, context=context)

    def wkf_approve_order(self, cr, uid, ids, context=None):
        # 008 - Sobreescribiendo metodo estandar para que no realice el write
        # self.write(cr, uid, ids, {'state': 'approved', 'date_approve': fields.date.context_today(self,cr,uid,context=context)})
        return True

    #001-Fin
    def purchase_rechazar_btn(self, cr, uid, ids, context=None):
        return self.action_cancel(cr, uid, ids, context=context)

    # Metodo sobreescrito del estandar
    # Se agregan ademas los picking que son reversiones de las transferencias de la OC
    def view_picking(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)

        pick_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            pick_ids += [picking.id for picking in po.picking_ids]

        # Esta parte cambia con respecto al estandar
        for p in po.picking_ids:
            if p.state in ['done']:
                p_ids = self.pool.get('stock.picking').search(cr, uid, [('origin', '=', p.name)])
                pick_ids += p_ids
        # Fin de la parte custom

        action['context'] = {}
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False
        return action

    #002-sobreescribiendo metodo de cancelacion estandar
    def action_cancel(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for purchase in self.browse(cr, uid, ids, context=context):
            for pick in purchase.picking_ids:
                if pick.state in ('done'):
                    # Chequear reversiones parciales
                    for move_line in pick.move_lines:
                        qty = 0
                        for ret_mov in move_line.returned_move_ids:
                            qty += ret_mov.product_uom_qty
                        if qty < move_line.product_uom_qty:
                            raise osv.except_osv(
                                _('Unable to cancel this purchase order.'),
                                _('Existen transferencias revertidas parcialmente para esta orden.'))
                elif pick.state not in ('draft', 'cancel'):
                    raise osv.except_osv(
                        _('Unable to cancel this purchase order.'),
                        _('First cancel all receptions related to this purchase order.'))
            for pick in purchase.picking_ids:
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_cancel', cr)
            for inv in purchase.invoice_ids:
                if inv and inv.state not in ('cancel','draft','cancel_sice','cancel_siif'):
                    raise osv.except_osv(
                        _('Unable to cancel this purchase order.'),
                        _('Primero tiene que cancelar todas las facturas relacionas con este pedido de compra.'))
                if inv and inv.state in ('draft',):
                    wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_cancel', cr)
        self.write(cr,uid,ids,{'state':'cancel'})

        for (id, name) in self.name_get(cr, uid, ids):
            wf_service.trg_validate(uid, 'purchase.order', id, 'purchase_cancel', cr)
        return True

    # #enviar a autorizar
    # def button_enviar_autorizar(self, cr, uid, ids, context=None):
    #     self.write(cr,uid,ids,{'state':'in_auth_odg'})
    #     return True

    # def button_autorizar(self, cr, uid, ids, context=None):
    #     self.write(cr,uid,ids,{'state':'auth_ordenador'})
    #     return True

    #012- incidencia 619 - Finalizar de la OC
    def button_finalizar(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'state':'closed'})
        return True
    #012-Fin

    def purchase_commit(self, cr, uid, ids, context=None):
        # self.write(cr,uid,ids,{'state':'oc_confirmado', 'comprometido':True})
        self.write(cr,uid,ids,{'comprometido':True})
        # que disparará la interfaz a SIIF.
        return True
        # ('accepted_odg', 'Autorizado ODG'),   Pendiente, porque es el mismo workflow de Orden de Compras, boton Confirmar Pedido

    def picking_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'shipped':1,'state':'confirmed'}, context=context) #commited
        return True

    def invoice_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'confirmed'}, context=context) # commited
        return True

    # Pasado chequeo de facturas, 08/01
    def check_invoices(self, cr, uid, ids, context=None):
        for purchase in self.browse(cr, uid, ids, context=context):
            if purchase.invoice_method == 'picking':
                return False
            else:
                all_invoiced = all(line.qty_invoiced == line.product_qty for line in purchase.order_line)
                # _logger.info('INVOICED %s',all_invoiced)
                if not all_invoiced:
                   # self.write(cr, uid, purchase.id, {'state':'confirmed_oc'}, context=context)
                   return True
        return False

    # heredando ver factura original para cancilleria
    # def view_invoice(self, cr, uid, ids, context=None):
    #TODO: si ya existe una factura en estado borrador, que no cree una nueva y que me lleve a la que existe
    def btn_view_create_invoice(self, cr, uid, ids, context=None):
        return self.action_invoice_create_grp(cr, uid, ids, context=context)

    # en financiero - incidencia 227 wkf   cambiado 05/11  echavianos
    def button_enviar_financiero(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'en_financiero':True})
        # que disparará la interfaz a SIIF.
        return True

    # Se hereda el estandar y se agregan nuevos campos, se modifica el quantity
    def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
        res = super(grp_orden_compra, self)._prepare_inv_line(cr, uid, account_id, order_line, context=context)
        res['id_item'] = order_line.id_item or False
        res['id_variacion'] = order_line.id_variacion or False
        res['nro_oc'] = order_line.order_id.sice_id_oc or False
        res['desc_variacion'] = order_line.desc_variacion or False
        res['quantity'] = order_line.qty_pendiente
        return res

    def _prepare_invoice_grp(self, cr, uid, order, line_ids, context=None):
        """Prepare the dict of values to create the new invoice for a
           purchase order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: purchase.order record to invoice
           :param list(int) line_ids: list of invoice line IDs that must be
                                      attached to the invoice
           :return: dict of value to create() the invoice
        """
        if context is None:
            context = {}
        context = dict(context)
        journal_ids = self.pool['account.journal'].search(
            cr, uid, [('type', '=', 'purchase'),
                      ('company_id', '=', order.company_id.id)],
            limit=1)
        if not journal_ids:
            raise osv.except_osv(
                _('Error!'),
                _('Define purchase journal for this company: "%s" (id:%d).') % \
                (order.company_id.name, order.company_id.id))

        # CAMBIOS 26/11
        context.update({'date': time.strftime('%Y-%m-%d')})
        currency = self.pool.get('res.currency').browse(cr, uid, order.currency_oc.id, context=context)
        rate = 1
        if currency.rate_silent != 0:
            rate = currency.rate
        # Incidencia de fecha tipo de cambio 13/10
        ctx = context.copy()
        ctx.update({'date': order.fecha_tipo_cambio_oc or time.strftime('%Y-%m-%d')})
        currency2 = self.pool.get('res.currency').browse(cr, uid, order.currency_oc.id, context=ctx)
        rate_presup = 1
        if currency2.rate_silent != 0 and currency2.rate_presupuesto != 0:
            rate_presup = currency2.rate_presupuesto
        moneda_base = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context).company_id.currency_id.id
        diferent_currency = order.currency_oc.id <> moneda_base and True or False
        # FIN CAMBIOS

        inv_data = {
            # 1 - CAMPOS UTEC
            'orden_compra_id': order.id,
            # 'currency_id' : orders[0].currency_oc.id, #orders[0].pricelist_id.currency_id.id, modified 13/04
            'cod_moneda': order.cod_moneda.id,
            'tipo_de_cambio_fnc': rate,
            'currency_rate': rate,
            'date_invoice': time.strftime('%Y-%m-%d'),
            # agregando tc de presupuesto 13/10
            'fecha_tipo_cambio': order.fecha_tipo_cambio_oc or time.strftime('%Y-%m-%d'),
            'diferent_currency': diferent_currency,
            'tc_presupuesto': diferent_currency and rate_presup or False,
            # 1 - FIN CAMPOS UTEC
            'name': False,  # order.partner_ref or order.name,
            # no pasar name, echaviano 08/01
            'reference': order.partner_ref or order.name,
            'account_id': order.partner_id.property_account_payable.id,
            'type': 'in_invoice',
            'partner_id': order.partner_id.id,
            'currency_id': order.currency_id.id,
            'journal_id': len(journal_ids) and journal_ids[0] or False,
            'invoice_line': [(6, 0, line_ids)],
            'origin': order.name,
            'fiscal_position': order.fiscal_position.id or False,
            'payment_term': order.payment_term_id.id or False,
            'company_id': order.company_id.id,
            'operating_unit_id': order.operating_unit_id.id,
        }

        # 010 - Para cuando se va a actualizar, cambios 19/02
        if 'update' in context and context.get('update', False):
            inv_data = {
                # 1 - CAMPOS UTEC
                'orden_compra_id': order.id,
                # 'currency_id' : orders[0].currency_oc.id, #orders[0].pricelist_id.currency_id.id, modified 13/04
                'cod_moneda': order.cod_moneda.id,
                'tipo_de_cambio_fnc': rate,
                'currency_rate': rate,
                # 010- 'date_invoice': time.strftime('%Y-%m-%d'), # En modificacion no pasar
                # agregando tc de presupuesto 13/10
                'fecha_tipo_cambio': order.fecha_tipo_cambio_oc or time.strftime('%Y-%m-%d'),
                'diferent_currency': diferent_currency,
                'tc_presupuesto': diferent_currency and rate_presup or False,
                # 1 - FIN CAMPOS UTEC
                # no pasar name, echaviano 08/01
                'reference': order.partner_ref or order.name,
                # 010- 'account_id': order.partner_id.property_account_payable.id, # En modificacion no pasar
                # 010- 'type': 'in_invoice', # En modificacion no pasar
                # 010- 'partner_id': order.partner_id.id,  #No pasar en update
                'currency_id': order.currency_id.id,
                'journal_id': len(journal_ids) and journal_ids[0] or False,
                # 010- 'invoice_line': [(6, 0, line_ids)],  # En modificacion no pasar invoice line
                'origin': order.name,
                'fiscal_position': order.fiscal_position.id or False,
                'payment_term': order.payment_term_id.id or False,
                # 010- 'company_id': order.company_id.id, # En modificacion no pasar invoice line
                # 'serie_factura': 'TEST1', # echaviano
            }

        return inv_data


    # Sobreescribiendo metodo original
    # Creando nuevo metodo 11/01
    def action_invoice_create_grp(self, cr, uid, ids, context=None):
        """Generates invoice for given ids of purchase orders and links that invoice ID to purchase order.
        :param ids: list of ids of purchase orders.
        :return: ID of created invoice.
        :rtype: int
        """
        context = dict(context or {})

        inv_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')

        # 05-AGREGADO
        inv_ids = []
        inv_first_ids = []
        inv = False
        first_inv_draft = False
        # 010-Cambios para la primera factura
        for po in self.browse(cr, uid, ids, context=context):
            for invoice in po.invoice_ids:
                inv_first_ids.append(invoice.id)
                inv = invoice
        # if not inv_first_ids:
        #     raise osv.except_osv(_('Error!'), _('Please create Invoices.'))
            # choose the view_mode accordingly
        if inv_first_ids and len(inv_first_ids) == 1:
            if inv.state == 'draft':
                context.update({'update': 1})
                first_inv_draft = True
                # return self.invoice_open_in_view(cr, uid, ids, inv_first_ids, context=context)

        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        for order in self.browse(cr, uid, ids, context=context):
            context.pop('force_company', None)
            if order.company_id.id != uid_company_id:
                # if the company of the document is different than the current user company, force the company in the context
                # then re-do a browse to read the property fields for the good company.
                context['force_company'] = order.company_id.id
                order = self.browse(cr, uid, order.id, context=context)

            # generate invoice line correspond to PO line and link that to created invoice (inv_id) and PO line
            inv_lines = []
            for po_line in order.order_line:
                acc_id = self._choose_account_from_po_line(cr, uid, po_line, context=context)
                inv_line_data = self._prepare_inv_line(cr, uid, acc_id, po_line, context=context)
                inv_line_id = inv_line_obj.create(cr, uid, inv_line_data, context=context)
                inv_lines.append(inv_line_id)
                po_line.write({'invoice_lines': [(4, inv_line_id)]})

            # get invoice data and create invoice
            # inv_data = self._prepare_invoice(cr, uid, order, inv_lines, context=context)  # cambiando metodo
            inv_data = self._prepare_invoice_grp(cr, uid, order, inv_lines, context=context)

            # 010-Cambios para primera factura
            if first_inv_draft and inv:
                # Se actualiza la primera
                inv_obj.write(cr, uid, inv.id, inv_data, context=context)
                inv_id = inv.id
            else:
                # Solo se modifica
                inv_id = inv_obj.create(cr, uid, inv_data, context=context)

            # compute the invoice
            inv_obj.button_compute(cr, uid, [inv_id], context=context, set_total=True)

            # Link this new invoice to related purchase order
            order.write({'invoice_ids': [(4, inv_id)]})
            inv_ids.append(inv_id)
        if context.get('desde_workflow', False):
            return inv_id
        else:
            return self.invoice_open_in_view(cr, uid, ids, inv_ids, context=context)

    def action_invoice_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context = dict(context)
        context.update({'desde_workflow': True})
        return self.action_invoice_create_grp(cr, uid, ids, context=context)


    # 010 - Abrir factura(s) creadas
    def invoice_open_in_view(self, cr, uid, ids, inv_ids, context=None):
        res = False
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
        res_id = res and res[1] or False

        return {
            'name': _(u'Factura de proveedores'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'in_invoice', 'journal_type': 'purchase'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }
        return res

    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
        res = super(grp_orden_compra, self)._prepare_order_line_move(cr, uid, order, order_line, picking_id, group_id, context=context)
        price_unit = order_line.price_unit # precio iva incluido
        if order_line.product_uom.id != order_line.product_id.uom_id.id:
            price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
        diff_currency = order.currency_oc.id != order.company_id.currency_id.id
        if diff_currency:
            ctx = dict(context or {})
            ctx.update({'date': order.fecha_tipo_cambio_oc or time.strftime('%Y-%m-%d'), 'pricelist_type':'presupuesto'})
            price_unit = self.pool.get('res.currency').compute(cr, uid, order.currency_oc.id, order.company_id.currency_id.id, price_unit, round=False, context=ctx)
        for r in res:
            r['price_unit'] = price_unit
            if diff_currency:
                r['acc_entry_currency_id'] = order.currency_oc.id
                r['acc_entry_amount_currency'] = order_line.price_unit
        return res

grp_orden_compra()


class grp_orden_compra_linea(osv.osv):
    _inherit = 'purchase.order.line'

    # def _qty_verify(self, cr, uid, ids, name, arg, context=None):
    #     res = {}
    #     for po_line in self.browse(cr, uid, ids, context=context):
    #         qty_invoiced = 0.0
    #         for line in po_line.invoice_lines:
    #             if line.invoice_id.state not in ['draft', 'cancel', 'cancel_sice', 'cancel_siif'] and line.product_id.id == po_line.product_id.id:
    #                 qty_invoiced += line.quantity
    #         res[po_line.id] = qty_invoiced
    #     return res
    #
    # #007 Inicio
    # def _qty_pendiente(self, cr, uid, ids, name, arg, context=None):
    #     res = {}
    #     for po_line in self.browse(cr, uid, ids, context=context):
    #         if po_line.order_id.invoice_method != 'picking':
    #             res[po_line.id] = po_line.product_qty - po_line.qty_invoiced
    #         else:
    #             res[po_line.id] = 0.0
    #     return res
    # #007 Fin

    def _qty_compute(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for po_line in self.browse(cr, uid, ids, context=context):
            res[po_line.id] = {
                'qty_invoiced': 0.0,
                'qty_pendiente': 0.0,
            }
            qty_invoiced = 0.0
            for line in po_line.invoice_lines:
                if line.invoice_id.state not in ['draft', 'cancel', 'cancel_sice', 'cancel_siif'] and line.product_id.id == po_line.product_id.id:
                    qty_invoiced += line.quantity
            res[po_line.id]['qty_invoiced'] = qty_invoiced
            res[po_line.id]['qty_pendiente'] = po_line.product_qty - qty_invoiced

        return res

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
                            partner_id, date_order=False, fiscal_position_id=False,
                            date_planned=False, name=False, price_unit=False, state='draft', context=None):
        res = super(grp_orden_compra_linea, self).onchange_product_id(cr, uid, ids, pricelist_id, product_id, qty,
                                                                      uom_id, partner_id, date_order=False,
                                                                      fiscal_position_id=False, date_planned=False,
                                                                      name=False, price_unit=False, state='draft',
                                                                      context=context)
        res['value'].pop('price_unit', None)
        res['value'].pop('name', None)
        res['value'].pop('taxes_id',None)
        return res

    _columns = {
        'qty_invoiced': fields.function(_qty_compute, multi='cantidades', string=u'Cantidad facturada',type='float',digits_compute= dp.get_precision('Account')),
        'qty_pendiente': fields.function(_qty_compute, multi='cantidades', string=u'Cantidad pendiente',type='float',digits_compute= dp.get_precision('Account')), #007 Incidencia cantidad pendiente
        'id_variacion': fields.integer(u'Id Variación '),
        'id_item': fields.integer('Id Item'),
        'desc_variacion': fields.char(u'Descripción variación'),
    }

    _defaults = {
        'qty_invoiced': lambda *a: 0.0,
    }

    # _sql_constraints = [
    #     ('product_uniq', 'unique (order_id,product_id)', u'El producto debe ser único por orden !')
    # ]

grp_orden_compra_linea()


class grp_cotizaciones_lineas_apg_oc(osv.osv):
    _name = 'grp.cotizaciones.lineas.apg.oc'
    _description = u'Lineas de cotización de APG en Ordenes de Compra'
    _columns = {
        # campo enlace
        'order_id': fields.many2one('purchase.order', 'APG', ondelete='cascade'),
        # 'nro_apg': fields.integer(u'Nro. de APG'),
        'nro_apg': fields.many2one('grp.compras.apg', u'Nro. de APG'),
        'descripcion_apg': fields.char(u'Descripción'),
        'monto_apg': fields.float('Monto'),
        'currency': fields.many2one('res.currency', 'Moneda'),
        'fecha_apg': fields.date('Fecha'),
        'nro_afectacion_apg': fields.integer(u'Nro. de Afectación'),
    }


grp_cotizaciones_lineas_apg_oc()
