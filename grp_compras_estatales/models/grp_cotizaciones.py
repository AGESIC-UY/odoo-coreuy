# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Enterprise Management Solution
#    GRP Estado Uruguay
#    Copyright (C) 2017 Quanam (ATEL SA., Uruguay)
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

import logging

_logger = logging.getLogger(__name__)

from openerp.osv import osv, fields
import datetime
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import date, datetime
import time
from collections import defaultdict
from suds import WebFault
from suds.client import Client

# ================================================================
## COTIZACIONES
# ================================================================

LISTA_ESTADOS_COT = [
    ('draft', 'Borrador'),
    ('validado', u'Validado'),
    ('aprobado_sice', 'Aprobado SICE'),
    ('cancelado', 'Cancelado'),
]

_editable = {'draft': [('readonly', False)]}


class grp_cotizaciones(osv.osv):
    _name = 'grp.cotizaciones'
    _inherit = ['mail.thread']
    _description = 'Adjudicaciones'
    _order = 'id desc'

    def _get_location(self, cr, uid, cotizacion, context=None):
        if cotizacion.operating_unit_id and len(cotizacion.operating_unit_id.location_ids) == 1:
            return cotizacion.operating_unit_id.location_ids.id
        else:
            return False

    def _get_picking(self, cr, uid, location_id, context=None):
        if isinstance(location_id,(tuple,list)):
            location_id = location_id[0]

        loc_obj = self.pool.get("stock.location")
        type_obj = self.pool.get('stock.picking.type')
        # Need to search for a picking type
        src_loc = loc_obj.browse(cr, uid, location_id, context=context)
        wh = loc_obj.get_warehouse(cr, uid, src_loc, context=context)
        domain = [('code', '=', 'incoming')]
        if wh:
            domain += [('warehouse_id', '=', wh)]
        pick_type_id = type_obj.search(cr, uid, domain, context=context)

        if len(pick_type_id) > 0:
            pick_type_id = pick_type_id[0]
        return pick_type_id

    def get_total_pesos(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        if context is None:
            context = {}
        context = dict(context)
        currency_obj = self.pool.get('res.currency')
        for cotiz in self.browse(cr, uid, ids, context=context):
            total = 0
            base_currency_id = cotiz.company_currency_id.id
            for aceptadas in cotiz.sice_page_aceptadas:
                moneda = aceptadas.currency.id
                if moneda != base_currency_id:
                    context.update({'pricelist_type': 'presupuesto'})
                    subttal_base = currency_obj.compute(cr, uid, moneda, base_currency_id, aceptadas.subtotal, context)
                    total += subttal_base
                else:
                    total += aceptadas.subtotal
            res[cotiz.id] = total
        return res

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            if record.name != '/':
                res.append((record.id, record.name))
            else:
                res.append((record.id, 'ADJ Borrador'))
        return res

    _columns = {
        # Cabezal
        'state': fields.selection(LISTA_ESTADOS_COT, 'Estado', size=86, readonly=True),
        'name': fields.char(u'Adjudicación', size=256, readonly=False),
        'company_id': fields.many2one('res.company', u'Compañía', readonly=True),
        'comprador_id': fields.many2one('res.users', 'Comprador', size=256, readonly=True,
                                        states={'draft': [('readonly', False)]}),
        'proveedor_id': fields.many2one('res.partner', 'Proveedor', size=256, readonly=True,
                                        states={'draft': [('readonly', False)]}),
        'pedido_compra_id': fields.many2one('grp.pedido.compra', 'Pedido de Compras', required=False,
                               domain=[('state', 'in', ['confirmado', 'sice'])], readonly=True,
                               states={'draft': [('readonly', False)]}),
        'fecha_respuesta': fields.date('Fecha', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}),
        'plazo_entrega': fields.date('Plazo Entrega', readonly=True, states={'draft': [('readonly', False)]}),
        # 'recomendada_CAA': fields.boolean('Recomendada CAA', readonly=True, states={'draft': [('readonly', False)]}),
        'tipo_compra': fields.related('pedido_compra_id', 'tipo_compra', type='many2one', relation='sicec.tipo.compra',
                                      string='Tipo de Compra', readonly=True, store=True),
        'adjudicada': fields.boolean('Adjudicada', readonly=True, states={'draft': [('readonly', False)]}),
        'sice_numeracion': fields.related('pedido_compra_id', 'sice_id_compra', type='integer', string=u'Numeración SICE',
                                          help=u'Nro. SICE', states={'draft': [('readonly', False)]}),
        'sice_descripcion': fields.text(u'Descripción'),
        'cod_estado_SICE': fields.char(u'Código Estado SICE'),  # OCULTO
        'cod_estado_SICE_adj': fields.char(u'Código Estado SICE Adjudicado'),  # OCULTO
        'estado_SICE': fields.char(u'Descripción Estado SICE'),  # OCULTO
        # campos que definen las pestañas
        'sice_page_aceptadas': fields.one2many('grp.cotizaciones.lineas.aceptadas', 'pedido_cot_id',
                                               'Productos Aceptados', readonly=True,
                                               states={'draft': [('readonly', False)]}),
        'sice_page_rechazadas': fields.one2many('grp.cotizaciones.lineas.rechazadas', 'pedido_cot_id_2',
                                                'Productos Rechazados', readonly=True,
                                                states={'draft': [('readonly', False)]}),
        'page_apg': fields.related('pedido_compra_id', 'apg_ids', type='one2many',
                                    domain="[('state','not in',['inicio','nuevo'])]",
                                    relation='grp.compras.apg', readonly=1),
        # Esto no se esta mostrando ahora
        # Pestaña Llave Presupuestal  (ESTOS CAMPOS NO SE ESTAN MOSTRANDO AHORA)
        'page_llave': fields.one2many('grp.cotizaciones.lineas.llave', 'pedido_cot_id_4', 'Llave Presupuestal'),
        # Pestaña Cotizacion
        'observaciones': fields.text('Observaciones'),
        # Pestaña Terminos y Condiciones
        'plazo_pago': fields.char('Plazo de pago', readonly=True, states={'draft': [('readonly', False)]}),
        'terminos_condiciones': fields.text(u'Términos y Condiciones', readonly=True,
                                            states={'draft': [('readonly', False)]}),
        # Pestaña Ampliacion
        # Ver detalles en GAP de ampliacion
        # Ordenes de compra
        'purchase_order_ids': fields.one2many('purchase.order', 'doc_origen', 'Orden de Compra'),
        # Campos Ocultos
        'codigo_item_SICE': fields.integer(u'Código Item SICE'),
        'nro_item_SICE': fields.integer(u'Nro. Item SICE'),
        'Cod_Variante': fields.char(u'Código Variante'),
        'CodMedidaVariante': fields.char('CodMedidaVariante'),
        'valor_variante': fields.char('Valor Variante'),
        'CodUnidadVariante': fields.char(u'Código Unidad Variante'),
        'DescUnidadVariante': fields.char('Descuento Unidad Variante'),
        'CodColor': fields.char(u'Código Color'),
        'color': fields.char('Color'),
        'CodDetalleVariante': fields.char(u'Código Detalle Variante'),
        'DescDetalleVariante': fields.char(u'Descripción Detalle Variante'),
        'CodMarca': fields.char(u'Código Marca'),
        'DescMarca': fields.char(u'Descripción Marca'),
        'IdVariacion': fields.char(u'id Variación'),
        'DescVariacion': fields.char(u'Descripción Variación'),
        'id_compra': fields.char('id_compra'),
        'TipoDocProv': fields.char('Tipo Documento Proveedor'),
        'nro_doc_prov': fields.integer(u'Nro. Documento Proveedor'),
        'CodArticulo': fields.char('Cod_Art'),
        'CodUnidad': fields.char('CodUnidad'),
        'impuesto': fields.float('impuesto'),
        'porcentaje_impuesto': fields.integer('porcentaje impuesto'),
        'variante': fields.char('Variante'),
        # echaviano
        'total_estimado': fields.function(get_total_pesos, string='Total estimado pesos',
                                          digits_compute=dp.get_precision('Cantidad')),
        'company_currency_id': fields.related('company_id', 'currency_id', type='many2one', relation='res.currency',
                                         string='Moneda empresa', store=False, readonly=True),
        # 017 Relacion con Ampliacion
        'pdc_ampliacion_ids': fields.one2many('grp.pedido.compra', 'adj_origen_ampliacion_id',
                                              string=u'Pedidos Ampliados'),
        'lines_ampliacion_ids': fields.one2many('grp.cotizaciones.lineas.ampliadas', 'pedido_cot_id_5',
                                                string=u'Línea de Pedidos Ampliados'),
        'integracion_sice': fields.related('company_id', 'integracion_sice', type='boolean', string='Integracion Sice'),
        'ampliacion': fields.boolean(u'Ampliación', readonly=True),
        'nro_ampliacion': fields.related('pedido_compra_id', 'nro_ampliacion', type='integer',
                                         string=u'Nro. Ampliación', size=2, readonly=True),
        'nro_pedido_original_id': fields.many2one('grp.pedido.compra', u'Nro. Pedido Original', readonly=True),
        'nro_adjudicacion_original_id': fields.many2one('grp.cotizaciones', u'Nro. Adjudicación Original',
                                                        readonly=True),
    }

    _defaults = {
        'state': 'draft',
        'name': '/',
        'company_id': lambda s, cr, uid, c: s.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, c).company_id.id,
        'comprador_id': lambda obj, cr, uid, context: uid,
    }

    def onchage_pedido_compra(self, cr, uid, ids, pedido_compra, context=None):
        value = {}
        if pedido_compra:
            pedido = self.pool.get('grp.pedido.compra').browse(cr, uid, pedido_compra, context=None)
            # values_apgs = []
            # if ids:
            #     values_apgs.append((5,))
            # for compra_apg in pedido.apg_ids:
            #     if compra_apg.state not in ('inicio', 'nuevo'):
            #         values_apgs.append((0, 0, {
            #             'apg_id': compra_apg.id,
            #             'descripcion_apg': compra_apg.descripcion,
            #             'monto_apg': compra_apg.monto,
            #             'currency': compra_apg.moneda.id,
            #             'fecha_apg': compra_apg.fecha,
            #             'nro_afectacion_apg': compra_apg.nro_afectacion_siif  # compra_apg.sice_nro, cambio 19/03
            #         }))
            value = {
                'tipo_compra': pedido.tipo_compra.id,
                # 'page_apg': values_apgs,
                'sice_numeracion': pedido.sice_id_compra,
            }
        return {'value': value}


    def button_validar_adjudicacion_sice(self, cr, uid, ids, context=None):
        for r in self.browse(cr, uid, ids, context=context):
            cr.execute(
                " select * from grp_cotizaciones_lineas_aceptadas where pedido_cot_id = %(cot_id)s and product_id is null",
                {'cot_id': r.id})
            if cr.rowcount > 0:
                raise osv.except_osv('Error!', u'Todas las líneas deben tener Producto')
            else:
                self.write(cr, uid, [r.id], {'state': 'validado'}, context=context)
        return True

    # echaviano  ver OC
    def button_view_OC(self, cr, uid, ids, context=None):
        if not ids:
            return False
        purchase_ord_ids = []
        po = self.browse(cr, uid, ids, context=context)[0]
        if not po.purchase_order_ids:
            return
        for order in po.purchase_order_ids:
            purchase_ord_ids.append(order.id)

        if purchase_ord_ids:
            data_pool = self.pool.get('ir.model.data')
            action_model, action_id = data_pool.get_object_reference(cr, uid, 'grp_compras_estatales',
                                                                     'purchase_form2_action')
            if action_model:
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                action['domain'] = "[('id','in', [" + ','.join(map(str, purchase_ord_ids)) + "])]"
            return action

    def crear_solicitud_compra(self, cr, uid, ids, context=None):
        pool_sc = self.pool.get('grp.solicitud.compra')
        for lines in self.browse(cr, uid, ids, context=context)[0].grp_sr_id:
            pool_sc.create(cr, 1, {
                'product_id': lines.product_id.id,
                'cantidad_solicitada': lines.cantidad_solicitada,
                'linea_solicitud_recursos_id': lines.id,
                'solicitante_id': uid,
                'company_id': self.pool.get('res.company')._company_default_get(cr, uid, 'product.template',
                                                                                context=context),
                'precio_estimado': lines.product_id.standard_price,
                'description': lines.descripcion,
                'inciso': lines.grp_id.inciso,
                'u_e': lines.grp_id.u_e
            })
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        obj = self.pool.get('grp.cotizaciones').browse(cr, uid, id, context=context)
        aceptadas_list = []
        for id_line in obj.sice_page_aceptadas:
            aceptadas_list.append((0, 0, {
                'ampliar': id_line.ampliar,
                'proveedor_cot_id': id_line.proveedor_cot_id.id,
                'product_id': id_line.product_id.id,
                'name': id_line.name,
                'cantidad': id_line.cantidad,
                'uom_id': id_line.uom_id.id,
                'precio': id_line.precio,
                'codigo_impuesto': id_line.codigo_impuesto,
                'codigo_articulo': id_line.codigo_articulo,
                'currency': id_line.currency.id,
                'iva': [(6, 0, [line.id for line in id_line.iva])],
                'odg': id_line.odg,
                'atributos': id_line.atributos,
                'id_variacion': id_line.id_variacion,
                'id_item': id_line.id_item,
                'desc_variacion': id_line.desc_variacion}))
        default.update({
            'state': 'draft',
            'company_id': obj.company_id.id,
            'pedido_compra_id': obj.pedido_compra_id.id,
            'fecha_respuesta': obj.fecha_respuesta,
            'adjudicada': obj.adjudicada,
            # 'recomendada_CAA': obj.recomendada_CAA,
            'tipo_compra': obj.tipo_compra.id,
            'sice_descripcion': obj.sice_descripcion,
            'sice_page_aceptadas': aceptadas_list,
        })
        return super(grp_cotizaciones, self).copy(cr, uid, id, default=default, context=context)

    def unlink(self, cr, uid, ids, context=None):
        cotizacion = self.read(cr, uid, ids, ['state', 'name'], context=context)
        unlink_ids = []
        for s in cotizacion:
            state = 'Validado'
            if s['state'] == 'aprobado_sice': state = 'Aprobado SICE'
            if s['state'] in ['draft']:
                unlink_ids.append(s['id'])
            else:
                if len(ids) > 1:
                    raise osv.except_osv(_('Acción inválida!'),
                                         _('Solamente puede eliminar adjudicaciones en estado borrador.'))
                else:
                    raise osv.except_osv(_('Acción inválida!'),
                                         _('La adjudicación %s no se puede eliminar porque está en estado %s.') % (
                                             s['name'], state,))
        return super(grp_cotizaciones, self).unlink(cr, uid, unlink_ids, context=context)

    def act_cotizaciones_validado(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context = dict(context)
        for r in self.browse(cr, uid, ids, context=context):
            fiscalyear_obj = self.pool.get('account.fiscalyear')
            uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            fecha_hoy = r.fecha_respuesta
            if fecha_hoy:
                fiscal_year_id = fiscalyear_obj.search(cr, uid,
                                                       [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
                                                        ('company_id', '=', uid_company_id)], context=context)
                fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
                context.update({'fiscalyear_id': fiscal_year_id})
            sequence = self.pool.get('ir.sequence').get(cr, uid, 'cotizacion.requisition.number', context=context)
            ind= sequence.index('-') +1
            seq_number = sequence[0:ind] +r.company_id.inciso + sequence[ind:len(sequence)]
            self.write(cr, uid, [r.id], {'state': 'validado', 'name': seq_number}, context=context)
            # self.pool.get('grp.pedido.compra').write(cr, uid, r.pedido_compra_id.id, {'nro_adj': r.id}, context=context)
        return True

    def trans_validar(self, cr, uid, ids, context=None):
        rec = self.browse(cr, uid, ids[0], context)
        if not rec.sice_page_aceptadas:
            raise osv.except_osv(_('Acción inválida!'), _('Debe definir al menos un producto en las líneas.'))
        if not rec.total_estimado > 0:
            raise osv.except_osv(_('Acción inválida!'), _('El total estimado en pesos debe ser mayor a cero.'))
        return True

    def act_cotizaciones_cancelado(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancelado'}, context=context)
        return True

    # 001 Inicio, crea un pedido de compra a partir de la adjudicacion
    def button_adjudicacion_ampliar_pc(self, cr, uid, ids, context=None):
        if not ids:
            return False
        purchase_ord_ids = []
        newlines = []
        pedido_data = {}
        adj = self.browse(cr, uid, ids, context=context)[0]
        moneda = False
        for line in adj.sice_page_aceptadas:
            taxes = []
            for tax in line.iva:
                if tax:
                    taxes.append(tax.id)

            if line.currency and not moneda:
                moneda = line.currency

            newlines.append((0, 0, {
                'product_id': line.product_id and line.product_id.id or False,
                'precio_estimado': line.precio,
                'uom_id': line.uom_id and line.uom_id.id,  # 010 Inicio incidencia pasar um
                'iva': len(taxes) and [(6, 0, [x for x in taxes])] or [],  # incidencia agregar IVA
                'cantidad_comprar_sice': line.cantidad,
                'cotizacion_linea_id': line.id,  # campo enlace con la linea de la adjudicacion
                # 004 Agregar campos a las lineas de pedidos de compra
                'partner_id': line.proveedor_cot_id and line.proveedor_cot_id.id or False,
                'id_variacion': line.id_variacion,  # campo enlace con la linea de la adjudicacion
                'id_item': line.id_item,  # campo enlace con la linea de la adjudicacion
                # 004 Fin de campos adicionales
            }))
        # nivel cabezal
        largo = len(adj.pedido_compra_id.name)
        # pos = -1 * (largo-5)
        numero = largo > 5 and adj.pedido_compra_id.name[-5:] or False
        inciso = adj.pedido_compra_id.company_id.inciso
        pedido_data['name'] = numero and ('%s-%s-%s-%s') % (date.today().year, inciso, 'AMP', numero) or False
        # pedido_data['proc_urg'] = adj.pedido_compra_id.proc_urg
        pedido_data['tipo_compra'] = adj.pedido_compra_id.tipo_compra and adj.pedido_compra_id.tipo_compra.id or False
        pedido_data['sub_tipo_compra'] = adj.pedido_compra_id.sub_tipo_compra and adj.pedido_compra_id.sub_tipo_compra.id or False
        pedido_data['ampliacion'] = True
        pedido_data['nro_adj'] = adj.id  # adj.name  023 21/09  incidencia 354
        #se toma la moneda de la primer linea, si no encuentra ninguna (no deberia pasar) se toma la del pedido original
        if moneda:
            pedido_data['moneda'] = moneda.id
        else:
            pedido_data['moneda'] = adj.pedido_compra_id.moneda and adj.pedido_compra_id.moneda.id
        pedido_data['pc_origen_ampliacion_id'] = adj.pedido_compra_id and adj.pedido_compra_id.id or False
        pedido_data['adj_origen_ampliacion_id'] = adj.id
        pedido_data['operating_unit_id'] = adj.pedido_compra_id.operating_unit_id.id
        pedido_data['sicec_uc_id'] = adj.pedido_compra_id.sicec_uc_id.id
        # nivel de lineas
        pedido_data['lineas_ids'] = newlines
        # Crear el nuevo pedido de compra con los ids de las solicitudes de compra que se seleccionaron
        pedido_obj = self.pool.get('grp.pedido.compra')
        pc_id = pedido_obj.create(cr, uid, pedido_data, context=context)

        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'grp_compras_estatales',
                                                                       'view_pedidos_compra_form')
        view_id = view_ref and view_ref[1] or False
        if not ids:
            return False
        ctx = (context or {}).copy()
        if pc_id:
            return {
                'name': _('Pedido de Compra'),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': [view_id],
                'res_model': 'grp.pedido.compra',
                'context': ctx,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'current',
                'res_id': pc_id or False,
            }
        return True

    def button_Crear_OC(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context=dict(context)
        order_pool = self.pool.get('purchase.order')
        product_product = self.pool.get('product.product')
        order_ids = []
        rate_date = time.strftime('%Y-%m-%d')
        for cotizacion in self.browse(cr, uid, ids, context=context):
            pc_apg_id = False
            if cotizacion.pedido_compra_id.id:
                if cotizacion.pedido_compra_id.apg_ids:
                    for apg in cotizacion.pedido_compra_id.apg_ids:
                        # if apg.state != 'anulada':
                        if apg.state in ['afectado']:
                            pc_apg_id = apg.id
                            break
                else:
                    raise osv.except_osv('Error!', u'No hay APG asociada al pedido de compra.')

            ordenes_a_crear = defaultdict(lambda:[])
            for lineas in cotizacion.sice_page_aceptadas:
                key = str(lineas.proveedor_cot_id.id) + str(lineas.currency.id)
                ordenes_a_crear[key].append(lineas)
                # ordenes_a_crear[lineas.proveedor_cot_id.id].append(lineas)
            for k,v in ordenes_a_crear.items():
                newlines = []
                cotizacion_values_lines = []
                if v[0].currency.id:
                    context.update({'date': rate_date})
                    currency = self.pool.get('res.currency').browse(cr, uid, v[0].currency.id, context=context)
                    rate = currency.rate_presupuesto
                else:
                    raise osv.except_osv ( 'Error!', u'Debe definir la moneda!' )
                #001 - Default location
                loc_id = self._get_location(cr, uid, cotizacion, context=context)
                if loc_id:
                    picking_aux = self._get_picking(cr, uid, loc_id)
                else:
                    picking_aux = False
                values = {
                    'doc_origen' : cotizacion.id,
                    'origin' : cotizacion.name, # agregado
                    'notes' : cotizacion.observaciones, # agregado por incidencia 12/02, cambiado a notes
                    'descripcion' : cotizacion.sice_descripcion, # agregado por incidencia dia 13/03
                    # 'type' : 'cancilleria',     # agregado   comentado echaviano
                    'partner_id' : v[0].proveedor_cot_id.id,
                    'pedido_compra_id' : cotizacion.pedido_compra_id.id or False,
                    'pc_apg_id' : pc_apg_id or False,
                    'currency_oc' : v[0].currency.id,
                    'cod_moneda' : v[0].cod_moneda.id,
                    'tipo_de_cambio': rate or False,
                    'fecha_tipo_cambio_oc': rate_date,
                    # 'currency_oc' : cotizacion.currency.id,
                    'order_line' : newlines,
                    'page_apg_oc': False,
                    # 'location_id' : v[0].product_id and v[0].product_id.property_stock_inventory and v[0].product_id.property_stock_inventory.id or False,
                    'location_id' : loc_id,
                    # 'location_id' : self.pool.get('stock.inventory.line')._default_stock_location(cr,uid),
                    'pricelist_id' : self.pool.get('res.partner').browse(cr,SUPERUSER_ID,v[0].proveedor_cot_id.id).property_product_pricelist_purchase.id,
                    #'picking_type_id': 6, # echaviano, esto no se como sacarlo
                    'picking_type_id': picking_aux,
                }

                for linea_apg in cotizacion.page_apg:
                    cotizacion_values_lines.append((0,0, {
                        'nro_apg': linea_apg.id,
                        'descripcion_apg': linea_apg.descripcion,
                        'monto_apg': linea_apg.monto,
                        'currency': linea_apg.moneda.id,
                        'fecha_apg': linea_apg.fecha,
                        'nro_afectacion_apg': linea_apg.nro_afectacion_siif,
                    }))
                if cotizacion_values_lines:
                    values.update({'page_apg_oc': cotizacion_values_lines})
                # inicializando diccionario lineas agrupadas
                #002 Inicio
                lineas_crear = defaultdict(lambda:[])
                for lines in v:
                    if not lines.product_id:
                        raise osv.except_osv('Error!', u'No hay producto definido en alguna línea de la adjudicación!' )
                    key = str(lines.product_id.id)
                    lineas_crear[key].append(lines)
                data_prod_group = defaultdict(lambda:[])
                for k,v in lineas_crear.items():
                    first_taxes = []
                    rest_taxes = []
                    sum_ttal = 0.0
                    sum_cantidad = 0.0
                    i = 0
                    for elem in v:
                        sum_ttal += elem.precio * elem.cantidad  #elem.subtotal
                        sum_cantidad += elem.cantidad
                        if elem.iva:
                            ivas = [x.id for x in elem.iva]
                            if i==0:
                                first_taxes.append(ivas)
                            else:
                                rest_taxes.append(ivas)
                        i+=1
                    if first_taxes:
                        # if len(first_taxes[0]) != len(rest_taxes[0]):
                        #     raise osv.except_osv('Error!', u'Los impuestos de los productos deben ser correspondientes!' )
                        for tax in first_taxes[0]:
                            for rtax in rest_taxes:
                                if tax not in rtax or len(first_taxes[0]) != len(rtax):
                                    raise osv.except_osv('Error!', u'Los impuestos de los productos deben ser correspondientes!' )

                    data_prod_group[k]={'precio': sum_ttal / sum_cantidad, 'cantidad':sum_cantidad }

                    # 'taxes_id':  [(6, 0, [x.id for x in v[0].iva])],
                    # data_prod_group[k].append({'precio': sum_ttal / sum_cantidad, 'cantidad':sum_cantidad })
                    # precio promedio y cantidad

                for k,v in lineas_crear.items():
                    dummy, prod_name = product_product.name_get(cr, uid, v[0].product_id.id, context=context)[0]
                    newlines.append((0,0,{
                            'product_id' : v[0].product_id.id,
                            'product_uom' : v[0].uom_id.id,
                            'name' : prod_name or v[0].product_id.product_tmpl_id.description or '', # incidencia
                            'date_planned' : cotizacion.fecha_respuesta,
                            'product_qty' : data_prod_group[k]['cantidad'], #  v[0].cantidad,
                            # 'product_qty' : lines.product_requested_qty,
                            'price_unit' : data_prod_group[k]['precio'], #lines.precio,
                            'taxes_id':  [(6, 0, [x.id for x in v[0].iva])],
                            # 'taxes_id' :  [(6, 0, [x.id for x in lines.tax_id])],
                            #MVARELA 24_03 - Campos intefaz SICE
                            'id_variacion': v[0].id_variacion,
                            'id_item': v[0].id_item,
                            'cod_moneda': v[0].cod_moneda.id,
                            'desc_variacion': v[0].desc_variacion,
                            'cotizaciones_linea_id': v[0].id,  # TODO: SPRING 12 GAP 67 K

                    }))
                #002 Fin
                id_order = order_pool.create(cr, uid, values, context=context)
                order_ids.append(id_order)
        if order_ids:
            data_pool = self.pool.get('ir.model.data')
            # action_model,action_id = data_pool.get_object_reference(cr, uid, 'purchase', 'purchase_form_action')
            # comentado, echaviano 12/01
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'grp_compras_estatales', 'purchase_form2_action')
            if action_model:
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                action['domain'] = "[('id','in', ["+','.join(map(str,order_ids))+"])]"
            return action

        return True

    # 003 Crear OC para seleccionar ampliaciones
    def button_Crear_OC_Select(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'grp_compras_estatales', 'view_crear_oc_wizard')
        res_id = res and res[1] or False

        cot = self.browse(cr, uid, ids, context=context)
        cot = cot[0]
        ctx = dict(context)
        ctx.update({
            'default_pedido_compra_adjudicacion_id': cot.pedido_compra_id and cot.pedido_compra_id.id,
            'default_act_id': ids[0],
        })
        return {
            'name': "Crear orden de compras",
            'view_mode': 'form',
            'view_id': res_id,
            'view_type': 'form',
            'res_model': 'grp.wiz.crear.oc',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    # 003 Crear OC a partir de la ampliacion + grp.cotizaciones.lineas.ampliadas
    def button_Crear_OC_adjudicacion_ampliada(self, cr, uid, ids, pedido_compra_id, context=None):
        order_pool = self.pool.get('purchase.order')
        product_product = self.pool.get('product.product')

        order_ids = []

        pc_apg_id = False
        if pedido_compra_id.apg_ids:
            for apg in pedido_compra_id.apg_ids:
                # if apg.state != 'anulada':
                if apg.state in ['afectado']:
                    pc_apg_id = apg.id
                    break
        else:
            raise osv.except_osv('Error!', u'No hay APG asociada al pedido de compra.')

        cotizacion = self.browse(cr, uid, ids, context=context)[0]
        moneda_base = pedido_compra_id.company_id.currency_id.id

        ordenes_a_crear = defaultdict(lambda: [])
        for line_ampliacion in cotizacion.lines_ampliacion_ids:
            if line_ampliacion.pc_ampliado_id.id == pedido_compra_id.id:
                key = str(line_ampliacion.proveedor_cot_id.id) + str(line_ampliacion.currency.id)
                ordenes_a_crear[key].append(line_ampliacion)

                # ordenes_a_crear[lineas.proveedor_cot_id.id].append(lineas)
        for k, v in ordenes_a_crear.items():
            newlines = []
            cotizacion_values_lines = []
            apg_values_lines = []
            if v[0].currency.id:
                ctx = context.copy()
                ctx.update({'date': time.strftime('%Y-%m-%d')})
                currency = self.pool.get('res.currency').browse(cr, uid, v[0].currency.id, context=ctx)
                rate = currency.rate
            else:
                raise osv.except_osv('Error!', u'Debe definir la moneda!')
            values = {
                'descripcion': v[0].sice_descripcion or False,  # campo nuevo agregado en lineas sice ampliacion
                'partner_id': v[0].proveedor_cot_id.id,
                'pedido_compra_id': v[0].pc_ampliado_id.id or False,
                'pc_apg_id': pc_apg_id or False,
                'currency_oc': v[0].currency.id,
                'cod_moneda': v[0].cod_moneda.id,
                'tipo_de_cambio': rate or False,
                'order_line': newlines,
                'page_apg_oc': False,
                'location_id': self._get_location(cr, uid, cotizacion, context=context),
                'pricelist_id': self.pool.get('res.partner').browse(cr, SUPERUSER_ID, v[
                    0].proveedor_cot_id.id).property_product_pricelist_purchase.id,
            }

            # Para la APG
            if pedido_compra_id.apg_ids:
                for apg in pedido_compra_id.apg_ids:
                    if apg.id == pc_apg_id:
                        apg_values_lines.append((0, 0, {
                            'nro_apg': apg.id,
                            'descripcion_apg': apg.descripcion,
                            'monto_apg': apg.monto_divisa,  # puede ser monto pesos  monto
                            'currency': apg.moneda.id,
                            'fecha_apg': apg.fecha,
                            'nro_afectacion_apg': apg.nro_afectacion_siif
                        }))
                if apg_values_lines:
                    values.update({'page_apg_oc': apg_values_lines})

            # inicializando diccionario lineas agrupadas
            lineas_crear = defaultdict(lambda: [])
            for lines in v:
                if not lines.product_id:
                    raise osv.except_osv('Error!', u'No hay producto definido en alguna línea de la adjudicación!')
                key = str(lines.product_id.id)
                lineas_crear[key].append(lines)
            data_prod_group = defaultdict(lambda: [])
            for k, v in lineas_crear.items():
                first_taxes = []
                rest_taxes = []
                sum_ttal = 0.0
                sum_cantidad = 0.0
                i = 0
                for elem in v:
                    sum_ttal += elem.precio * elem.cantidad  # elem.subtotal
                    sum_cantidad += elem.cantidad
                    if elem.iva:
                        ivas = [x.id for x in elem.iva]
                        if i == 0:
                            first_taxes.append(ivas)
                        else:
                            rest_taxes.append(ivas)
                    i += 1
                if first_taxes:
                    # if len(first_taxes[0]) != len(rest_taxes[0]):
                    #     raise osv.except_osv('Error!', u'Los impuestos de los productos deben ser correspondientes!' )
                    for tax in first_taxes[0]:
                        for rtax in rest_taxes:
                            if tax not in rtax or len(first_taxes[0]) != len(rtax):
                                raise osv.except_osv('Error!',
                                                     u'Los impuestos de los productos deben ser correspondientes!')

                data_prod_group[k] = {'precio': sum_ttal / sum_cantidad, 'cantidad': sum_cantidad}

            for k, v in lineas_crear.items():
                dummy, prod_name = product_product.name_get(cr, uid, v[0].product_id.id, context=context)[0]
                newlines.append((0, 0, {
                    'product_id': v[0].product_id.id,
                    'product_uom': v[0].uom_id.id,
                    'name': prod_name or v[0].product_id.product_tmpl_id.description or '',  # incidencia
                    'date_planned': cotizacion.fecha_respuesta,
                    'product_qty': data_prod_group[k]['cantidad'],  # v[0].cantidad,
                    'price_unit': data_prod_group[k]['precio'],  # lines.precio,
                    'taxes_id': [(6, 0, [x.id for x in v[0].iva])],
                    # MVARELA 24_03 - Campos intefaz SICE
                    # 'id_variacion': v[0].id_variacion,
                    # 'id_item': v[0].id_item,
                    # 'cod_moneda': v[0].cod_moneda.id,
                    'cotizaciones_linea_id': v[0].id,  # TODO: SPRING 12 GAP 67 K
                }))
            id_order = order_pool.create(cr, uid, values, context=context)
            order_ids.append(id_order)
        if order_ids:
            data_pool = self.pool.get('ir.model.data')
            action_model, action_id = data_pool.get_object_reference(cr, uid, 'grp_compras_estatales',
                                                                     'purchase_form2_action')
            if action_model:
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                action['domain'] = "[('id','in', [" + ','.join(map(str, order_ids)) + "])]"
            return action
        return True

    # TODO GAP 200 SPRING 6
    def button_crear_adjudicacion(self, cr, uid, ids, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        # res = mod_obj.get_object_reference(cr, uid, 'grp_factura_sice', 'view_importar_adjudicacion_wizard')
        # res_id = res and res[1] or False
        res_id = ir_model_data.get_object_reference(cr, uid, 'grp_compras_estatales', 'view_grp_cot_form')[1]

        cot = self.browse(cr, uid, ids, context=context)
        cot = cot[0]

        vals = {}
        vals['ampliacion'] = True
        vals['nro_adjudicacion_original_id'] = cot.id
        vals['nro_pedido_original_id'] = cot.pedido_compra_id.id
        vals['state'] = 'draft'
        # vals['pedido_compra_domain_ids'] = self.pool.get('grp.pedido.compra').search(cr,uid,[('apg_ids','!=',False),('ampliacion','=',True),('nro_adj','=',cot.id)],context = context)
        vals['fecha_respuesta'] = cot.fecha_respuesta
        fnct_id = self.pool.get('grp.cotizaciones').create(cr, uid, vals)

        return {
            'name': "Adjudicación",
            'view_mode': 'form',
            'view_id': res_id,
            'view_type': 'form',
            'res_model': 'grp.cotizaciones',
            'views': [(res_id, 'form')],
            'res_id': fnct_id,
            'target': 'current',
            'type': 'ir.actions.act_window',
            # 'context': context,
        }


grp_cotizaciones()


class grp_cotizaciones_lineas_aceptadas(osv.osv):
    _name = 'grp.cotizaciones.lineas.aceptadas'
    _description = u'Lineas de adjudicación de pedidos aceptadas'
    _rec_name = 'product_id'

    def _get_tax(self, cr, uid, context=None):
        if context is None: context = {}
        journal_pool = self.pool.get('account.journal')
        journal_id = context.get('journal_id', False)
        if not journal_id:
            ttype = context.get('type', 'bank')
            res = journal_pool.search(cr, uid, [('type', '=', ttype)], limit=1)
            if not res:
                return False
            journal_id = res[0]

        if not journal_id:
            return False
        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        account_id = journal.default_credit_account_id or journal.default_debit_account_id
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0].id
            return tax_id
        return False

    def _get_subtotal(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            #si viene de SICE ya tengo el valor, sino lo calculo
            if line.precioTotal:
                res[line.id] = line.precioTotal
            else:
                taxes = tax_obj.compute_all(cr, uid, line.iva, line.precio, line.cantidad, product=line.product_id)
                res[line.id] = taxes['total_included']
        return res

    _columns = {
        # campo enlace
        'pedido_cot_id': fields.many2one('grp.cotizaciones', 'Solicitado', ondelete='cascade'),
        'ampliar': fields.boolean('Ampliar'),
        'proveedor_cot_id': fields.many2one('res.partner', 'Proveedor', required=True),
        'product_id': fields.many2one('product.product', u'Producto', ondelete='set null', select=True),  # Producto
        'name': fields.char(u'Descripción Producto'),
        'cantidad': fields.float('Cantidad', required=True),
        'uom_id': fields.many2one('product.uom', 'UdM', required=True),  # TODO debe cargar su valor en la funcion
        'precio': fields.float('Precio Unitario', required=True),
        'precio_sice': fields.float('Precio s/imp', digits_compute=dp.get_precision('Product Price'),
                                    help='Precio unitario del producto devuelto por sice en el ws' "Precio s/imp"),
        # 029 - Devolucion de sice
        'codigo_impuesto': fields.char(u'Código Impuesto'),
        'codigo_articulo': fields.integer(u'Código Artículo'),
        'currency': fields.many2one('res.currency', 'Moneda', ),  # CAMPO PARA INTERFAZ SICE
        'subtotal': fields.function(_get_subtotal, type='float', digits_compute=dp.get_precision('Account'),
                                    string='Subtotal', store=True),
        'precioTotal': fields.float(string='Precio Total', digits_compute=dp.get_precision('Account')),
        # 133 - Cambios de ws sice
        'iva': fields.many2many('account.tax', 'cotizacion_lineas_aceptadas_tax', 'linea_sice_aceptadas_cotizac_id',
                                'tax_id', 'IVA'),
        'odg': fields.integer('OdG'),
        'atributos': fields.char('Atributos'),
        # MVARELA 24_03 - Nuevos campos necesarios para integracion SICE
        'id_variacion': fields.integer(u'Id Variación '),
        'id_item': fields.integer('Id Item'),
        'desc_variacion': fields.char(u'Descripción variación'),
        'cod_moneda': fields.many2one('sicec.moneda', u'Código moneda SICE'),
    }

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        value = {}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            taxes = []
            for tax in prod.product_tmpl_id.supplier_taxes_id:
                taxes.append(tax.id)
            value = {
                'codigo_articulo': prod.grp_sice_cod,
                'uom_id': prod.product_tmpl_id.uom_id.id,
                'iva': taxes,
            }
        return {'value': value}

    _defaults = {
        'name': u'Descripción',
        'ampliar': False,
    }


grp_cotizaciones_lineas_aceptadas()


# ================================================================

class grp_cotizaciones_lineas_ampliacion(osv.osv):
    _name = 'grp.cotizaciones.lineas.ampliadas'
    _description = u'Lineas de adjudicación ampliación'
    _rec_name = 'product_id'

    def _get_subtotal(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            taxes = tax_obj.compute_all(cr, uid, line.iva, line.precio, line.cantidad, product=line.product_id)
            res[line.id] = taxes['total_included']
        return res

    _columns = {
        # campo enlace
        'pedido_cot_id_5': fields.many2one('grp.cotizaciones', u'Adjudicación', ondelete='cascade'),
        'pc_ampliado_id': fields.many2one('grp.pedido.compra', u'Pedido de Compra', ondelete='restrict'),
        'proveedor_cot_id': fields.many2one('res.partner', 'Proveedor', required=True),
        'product_id': fields.many2one('product.product', u'Producto', ondelete='set null', select=True),  # Producto
        'name': fields.char(u'Descripción Producto'),
        'cantidad': fields.float('Cantidad', required=True),
        'uom_id': fields.many2one('product.uom', 'UdM', required=True),  # TODO debe cargar su valor en la funcion
        'precio': fields.float('Precio Unitario', required=True),
        'codigo_impuesto': fields.char(u'Código Impuesto'),
        'codigo_articulo': fields.integer(u'Código Artículo'),
        'currency': fields.many2one('res.currency', 'Moneda', ),  # CAMPO PARA INTERFAZ SICE
        'subtotal': fields.function(_get_subtotal, type='float', digits_compute=dp.get_precision('Account'),
                                    string='Subtotal', store=True),
        'iva': fields.many2many('account.tax', 'cotizacion_lineas_ampliadas_tax', 'linea_sice_ampliac_cotizac_id',
                                'tax_id', 'IVA'),
        'odg': fields.integer('OdG'),
        'atributos': fields.char('Atributos'),
        'sice_descripcion': fields.char(u'Descripción', help=u'Objeto de Compra Ampliación'),
        # ObjetoCompra de la Ampliación
        # MVARELA 24_03 - Nuevos campos necesarios para integracion SICE
        'id_variacion': fields.integer(u'Id Variación '),
        'id_item': fields.integer('Id Item'),
        'desc_variacion': fields.char(u'Descripción variación'),
        'cod_moneda': fields.many2one('sicec.moneda', u'Código moneda SICE'),
    }

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        value = {}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            taxes = []
            for tax in prod.product_tmpl_id.supplier_taxes_id:
                taxes.append(tax.id)
            value = {
                'codigo_articulo': prod.grp_sice_cod,
                'uom_id': prod.product_tmpl_id.uom_id.id,
                'iva': taxes,
            }
        return {'value': value}


grp_cotizaciones_lineas_ampliacion()


class grp_cotizaciones_lineas_rechazadas(osv.osv):
    _name = 'grp.cotizaciones.lineas.rechazadas'
    _description = u'Lineas de adjudicación de pedidos no encotnradas en sice'
    _columns = {
        # campo enlace
        'pedido_cot_id_2': fields.many2one('grp.cotizaciones', 'Solicitado', ondelete='cascade'),
        'product_id': fields.many2one('product.product', u'Producto', ondelete='set null', select=True, required=True),
        # Producto
        'descripcion': fields.char(u'Descripción del Producto'),
        'product_requested_qty': fields.integer('Cantidad'),
        'u_d_m': fields.char('Unidad de medida'),
        'precio_sin_iva': fields.char('Precio sin IVA'),
        'codigo_impuesto': fields.char(u'Código Impuesto'),
        'subtotal': fields.float('Subtotal'),
        'total': fields.float('Total'),
        'variante': fields.char('variante'),
        'currency': fields.many2one('res.currency', 'Moneda'),

    }


grp_cotizaciones_lineas_rechazadas()


# Posiblemente esta clase se elimine
class grp_cotizaciones_lineas_llave(osv.osv):
    _name = 'grp.cotizaciones.lineas.llave'
    _description = u'Lineas de adjudicación de Llave Presupuestal'
    _columns = {
        # campo enlace
        'pedido_cot_id_4': fields.many2one('grp.cotizaciones', 'Llave Presupuestal', ondelete='cascade'),
        'programa': fields.char('Programa'),
        'odg': fields.char('ODG'),
        'auxiliar': fields.char('Auxiliar'),
        'disponible': fields.char('Disponible'),
    }


grp_cotizaciones_lineas_llave()
