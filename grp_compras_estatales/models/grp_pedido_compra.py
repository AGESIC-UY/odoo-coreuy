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
from openerp.tools.translate import _
from collections import defaultdict
from openerp import netsvc
import openerp.addons.decimal_precision as dp
import time
from openerp import api
from openerp.exceptions import ValidationError


LISTA_ESTADOS = [
    ('inicio', 'Borrador'),
    ('confirmado', 'Confirmado'),
    ('sice', 'SICE'),
    ('cancelado_sice', u'Anulada'),
    ('cancelado', 'Cancelado'),
]

class grp_pedido_compra(osv.osv):
    _inherit = ['mail.thread']
    _name = 'grp.pedido.compra'
    _description = 'Pedidos de Compra'
    _order = 'id desc'



    @api.model
    def _update_prefix(self):
        sequence= self.env['ir.sequence']
        seq_ordenes_compra = sequence.search([('code','=','oc.number')])
        seq_pedido_compra = sequence.search([('code','=','pc.number')])
        seq_pedido_compra_cd = sequence.search([('name','=','Pedido de compra - CD')])
        seq_pedido_compra_ce = sequence.search([('name','=','Pedido de compra - CE')])
        seq_pedido_compra_cm = sequence.search([('name','=','Pedido de compra - CM')])
        seq_pedido_compra_ei = sequence.search([('name','=','Pedido de compra - EI')])
        seq_pedido_compra_fr = sequence.search([('name','=','Pedido de compra - FR')])
        seq_pedido_compra_la = sequence.search([('name','=','Pedido de compra - LA')])
        seq_pedido_compra_lp = sequence.search([('name','=','Pedido de compra - LP')])
        seq_cotizacion = sequence.search([('code','=','cotizacion.requisition.number')])
        seq_solicitud_compra = sequence.search([('code','=','solicitud.compra.number')])
        seq_solicitud_recursos = sequence.search([('code','=','resource.requisition.number')])
        seq_autorizacion_gastar = sequence.search([('code','=','apg.nroapg')])

        if seq_ordenes_compra:
            if seq_ordenes_compra.prefix != '%(fy)s--OC-':
                seq_ordenes_compra.write({'prefix':'%(fy)s--OC-'})

        if seq_pedido_compra:
            if seq_pedido_compra.prefix != '%(fy)s--x-':
                seq_pedido_compra.write({'prefix':'%(fy)s--x-'})

        if seq_pedido_compra_cd:
            if seq_pedido_compra_cd.prefix != '%(fy)s--CD-':
                seq_pedido_compra_cd.write({'prefix':'%(fy)s--CD-'})

        if seq_pedido_compra_ce:
            if seq_pedido_compra_ce.prefix != '%(fy)s--CE-':
                seq_pedido_compra_ce.write({'prefix':'%(fy)s--CE-'})

        if seq_pedido_compra_cm:
            if seq_pedido_compra_cm.prefix != '%(fy)s--CM-':
                seq_pedido_compra_cm.write({'prefix':'%(fy)s--CM-'})

        if seq_pedido_compra_la:
            if seq_pedido_compra_la.prefix != '%(fy)s--LA-':
                seq_pedido_compra_la.write({'prefix':'%(fy)s--LA-'})

        if seq_pedido_compra_lp:
            if seq_pedido_compra_lp.prefix != '%(fy)s--LP-':
                seq_pedido_compra_lp.write({'prefix':'%(fy)s--LP-'})

        if seq_pedido_compra_ei:
            if seq_pedido_compra_ei.prefix != '%(fy)s--EI-':
                seq_pedido_compra_ei.write({'prefix':'%(fy)s--EI-'})

        if seq_pedido_compra_fr:
            if seq_pedido_compra_fr.prefix != '%(fy)s--FR-':
                seq_pedido_compra_fr.write({'prefix':'%(fy)s--FR-'})

        if seq_cotizacion:
            if seq_cotizacion.prefix != '%(fy)s--ADJ-':
                seq_cotizacion.write({'prefix':'%(fy)s--ADJ-'})

        if seq_solicitud_compra:
            if seq_solicitud_compra.prefix != '%(fy)s--SC-':
                seq_solicitud_compra.write({'prefix':'%(fy)s--SC-'})

        if seq_solicitud_recursos:
            if seq_solicitud_recursos.prefix != '%(fy)s--SR-':
                seq_solicitud_recursos.write({'prefix':'%(fy)s--SR-'})

        if seq_autorizacion_gastar:
            if seq_autorizacion_gastar.prefix != '%(fy)s--APG-':
                seq_autorizacion_gastar.write({'prefix':'%(fy)s--APG-'})

        return True

    def _get_moneda(self, cr, uid, context=None):
        res = self.pool.get('res.users').read(cr, uid, [uid], ['company_id'], context=context)
        if res and res[0]['company_id']:
            company_id = res[0]['company_id'][0]
        else:
            return False
        res = self.pool.get('res.company').read(cr, uid, [company_id], ['currency_id'], context=context)
        if res and res[0]['currency_id']:
            currency_id = res[0]['currency_id'][0]
        else:
            return False
        return currency_id

    def _get_tipo_de_cambio_fnc(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=context):
            res[lines.id] = lines.tipo_de_cambio
        return res

    def _get_total_importe_divisa(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=context):
            total = 0
            for pedido in lines.lineas_ids:
                total += pedido.monto_divisa
            res[lines.id] = total
        return res

    def _get_total_importe_divisa_resumen(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=context):
            total = 0
            for pedido in lines.resumen_pedido_compra_ids:
                total += pedido.subtotal_divisa
            res[lines.id] = total
        return res

    def get_total_estimado_pesos(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        currency_obj = self.pool.get('res.currency')
        if context is None:
            context = {}
        context = dict(context)
        for pc in self.browse(cr, uid, ids, context=context):
            moneda = pc.moneda.id
            moneda_base = pc.company_id.currency_id.id
            amount_mb = round(pc.total_estimado_divisa_cpy)
            if moneda != moneda_base:
                context.update({'date': pc.date_start or time.strftime('%Y-%m-%d'),
                                'pricelist_type': 'presupuesto'})  # 131-pasado tc presupuesto 29/02, inc 476
                amount_mb = round(
                    currency_obj.compute(cr, uid, moneda, moneda_base, pc.total_estimado_divisa_cpy,
                                         context=context))
            res[pc.id] = round(amount_mb)
        return res

    def get_total_estimado_resumen(self, cr, uid, ids, fieldname, args, context=None):
        res = {}

        if context is None:
            context = {}
        context = dict(context)
        currency_obj = self.pool.get('res.currency')
        for pc in self.browse(cr, uid, ids, context=context):
            moneda = pc.moneda.id
            moneda_base = pc.company_id.currency_id.id
            amount_mb = round(pc.total_estimado_divisa)
            if moneda != moneda_base:
                context.update({'date': pc.date_start or time.strftime('%Y-%m-%d'),
                                'pricelist_type': 'presupuesto'})  # 131-pasado tc presupuesto 29/02, inc 476
                amount_mb = round(currency_obj.compute(cr, uid, moneda, moneda_base, pc.total_estimado_divisa,
                                                       context=context))
            res[pc.id] = round(amount_mb)
        return res

    def _es_compra_directa(self, cr, uid, ids, name, args, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.tipo_compra.idTipoCompra == 'CD':
                res[rec.id] = True
            else:
                res[rec.id] = False
        return res

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['name'], context=context)
        res = []
        for record in reads:
            res.append((record['id'], record['name']))
        return res

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
        for pedido in self.browse(cr, uid, ids, context=context):
            res[pedido.id] = {
                'amount_untaxed_cpy': 0.0,
                'amount_tax_cpy': 0.0,
                'total_estimado_divisa_cpy': 0.0,
            }
            val = val1 = 0.0
            cur = pedido.moneda

            for line in pedido.lineas_ids:
                val1 += line.monto_divisa
                for c in self.pool.get('account.tax').compute_all(cr, uid, line.iva, line.precio_estimado,
                                                                  line.cantidad_comprar_sice, line.product_id, None)[
                    'taxes']:
                    val += c.get('amount', 0.0)
            res[pedido.id]['amount_tax_cpy'] = cur_obj.round(cr, uid, cur, val)
            res[pedido.id]['amount_untaxed_cpy'] = cur_obj.round(cr, uid, cur, val1)
            res[pedido.id]['total_estimado_divisa_cpy'] = res[pedido.id]['amount_untaxed_cpy'] + res[pedido.id][
                'amount_tax_cpy']
        return res

    def _amount_all_summary(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
        for pedido in self.browse(cr, uid, ids, context=context):
            res[pedido.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'total_estimado_divisa': 0.0,
            }
            val = val1 = 0.0
            cur = pedido.moneda
            # Resumen
            for line in pedido.resumen_pedido_compra_ids:
                val1 += line.subtotal_divisa
                for c in self.pool.get('account.tax').compute_all(cr, uid, line.iva, line.precio_estimado,
                                                                  line.cantidad_a_comprar, line.product_id, None)[
                    'taxes']:
                    val += c.get('amount', 0.0)
            res[pedido.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[pedido.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[pedido.id]['total_estimado_divisa'] = res[pedido.id]['amount_untaxed'] + res[pedido.id]['amount_tax']
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('grp.linea.pedido.compra').browse(cr, uid, ids, context=context):
            result[line.pedido_compra_id.id] = True
        return result.keys()

    def _get_resumen(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('grp.resumen.pedido.compra').browse(cr, uid, ids, context=context):
            result[line.pedido_compra_id.id] = True
        return result.keys()



    def _get_tipo_licitacion( self, cr, uid, ids, name, args, context = None ):
        res = { }
        for record in self.browse(cr, uid, ids, context = context):
            res[record.id] = record.tipo_compra.idTipoCompra in ('LA','LP') and True or False
        return res


    def _sr_count(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for pedido in self.browse(cr, uid, ids, context=context):
            sr_ids = []
            for linea in pedido.lineas_ids:
                if linea.solicitud_compra_id and linea.solicitud_compra_id.solicitud_recursos_id and linea.solicitud_compra_id.solicitud_recursos_id.id not in sr_ids:
                    sr_ids.append(linea.solicitud_compra_id.solicitud_recursos_id.id)
            res[pedido.id] = len(sr_ids)
        return res

    _columns = {
        'name': fields.char('Nro. Pedido de Compra', size=32, readonly=False),
        'origin': fields.char('Documento original', size=32),
        'date_start': fields.date('Fecha creado', required=True),
        'description': fields.text(u'Descripción', size=250),  # Descripcion aumentar tamaño a de 100 a 250 caracteres
        'user_id': fields.many2one('res.users', 'Creado por'),
        'company_id': fields.many2one('res.company', 'Empresa', required=True),
        'resumen_pedido_compra_ids': fields.one2many('grp.resumen.pedido.compra', 'pedido_compra_id',
                                                     'Resumen de compra'),  # , ondelete='cascade'),
        'lineas_ids': fields.one2many('grp.linea.pedido.compra', 'pedido_compra_id', 'Solicitud de compra'),

        'apg_ids': fields.one2many('grp.compras.apg', 'pc_id', u'Autorización para gastar'),
        'moneda': fields.many2one('res.currency', 'Moneda', required=True),
        'company_currency_id': fields.related('company_id', 'currency_id', type='many2one', relation='res.currency',
                                         string='Moneda empresa', store=False, readonly=True),
        'tipo_de_cambio': fields.float('Tipo de cambio', digits=(10, 5)),
        'tipo_de_cambio_fnc': fields.function(_get_tipo_de_cambio_fnc, string='Tipo de cambio', type='float',
                                              digits=(10, 5)),
        'usr_solicitante': fields.many2one('res.users', 'Solicitado por'),
        'usr_aprobador': fields.many2one('res.users', 'Aprobado por'),
        'state': fields.selection(LISTA_ESTADOS, 'Estado', track_visibility='onchange'),
        'tipo_compra': fields.many2one('sicec.tipo.compra', 'Tipo de compra'),

        'sub_tipo_compra': fields.many2one('sicec.subtipo.compra', 'Sub tipo compra', domain=[]),

        'sice_date': fields.integer(u'Año de la Compra', size=4),

        'exep_art_33': fields.char(u'Excepción Art.33'),
        'sice_id_compra': fields.integer('ID SICE'),  # fields.integer('Id_Compra'),
        'sice_id_estado': fields.integer('Id_Estado'),
        'estado': fields.char('Estado'),
        'ampliacion': fields.boolean(u'Ampliación', readonly=True),
        'nro_ampliacion': fields.integer(u'N° Ampliación', size=2),  # 008 Editable
        'sice_id_compra_amp': fields.boolean('Id_Compra_Ampliacion'),
        'cond_pago_amp': fields.char("Condiciones de entrega", size=60),
        'forma_pago_amp': fields.char("Forma de pago", size=60),
        'tipo_licitacion': fields.function(_get_tipo_licitacion, string='Tipo licitacion', type='boolean'),
        'nro_adj': fields.many2one('grp.cotizaciones', string=u'Nro. de Adjudicación'),

        'link_adj': fields.many2one('grp.cotizaciones', u'Link de Adjudicación'),
        'total_estimado': fields.function(get_total_estimado_resumen, string='Total estimado pesos',
                                          digits_compute=dp.get_precision('Cantidad')),

        'total_estimado_cpy': fields.function(get_total_estimado_pesos, string='Total estimado pesos', digits=(16, 0)),

        'amount_untaxed_cpy': fields.function(_amount_all, digits_compute=dp.get_precision('Account'),
                                              string='Subtotal',
                                              store={
                                                  'grp.linea.pedido.compra': (_get_order, None, 10),
                                              }, multi="sums", help="Monto sin impuestos", track_visibility='always'),
        'amount_tax_cpy': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Impuesto',
                                          store={
                                              'grp.linea.pedido.compra': (_get_order, None, 10),
                                          }, multi="sums", help="Impuestos"),
        'total_estimado_divisa_cpy': fields.function(_amount_all, digits_compute=dp.get_precision('Account'),
                                                     string='Total estimado divisa',
                                                     store={
                                                         'grp.linea.pedido.compra': (_get_order, None, 10),
                                                     }, multi="sums", help="Monto total"),

        'amount_untaxed': fields.function(_amount_all_summary, digits_compute=dp.get_precision('Account'),
                                          string='Subtotal',
                                          store={
                                              'grp.resumen.pedido.compra': (_get_resumen, None, 10),
                                          }, multi="sumsr", help="Monto sin impuestos"),
        'amount_tax': fields.function(_amount_all_summary, digits_compute=dp.get_precision('Account'),
                                      string='Impuesto',
                                      store={
                                          'grp.resumen.pedido.compra': (_get_resumen, None, 10),
                                      }, multi="sumsr", help="Impuestos"),
        'total_estimado_divisa': fields.function(_amount_all_summary, digits_compute=dp.get_precision('Account'),
                                                 string='Total estimado divisa',
                                                 store={
                                                     'grp.resumen.pedido.compra': (_get_resumen, None, 10),
                                                 }, multi="sumsr", help="Monto total"),

        'es_compra_directa': fields.function(_es_compra_directa, type='boolean'),

        'nro_licitacion': fields.integer(u"Nro. de licitación"),

        'pc_origen_ampliacion_id': fields.many2one('grp.pedido.compra', string="Pedido de compra original"),
        'adj_origen_ampliacion_id': fields.many2one('grp.cotizaciones', string=u"Adjudicación original"),

        'tipo_de_resolucion': fields.selection([('1', u'Adjudicada totalmente'),
                                                ('2', u'Adjudicada parcialmente'),
                                                ], string=u'Tipo de Resolución'),
        'sr_count': fields.function(_sr_count, string='Solicitudes de recurso', type='integer'),

    }

    _defaults = {
        'state': 'inicio',
        'name': 'PC Borrador',
        'date_start': fields.date.context_today,
        'user_id': lambda self, cr, uid, context: uid,
        'usr_solicitante': lambda self, cr, uid, context: uid,
        'moneda': _get_moneda,
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid,
                                                                                                       'grp.pedido.compra',
                                                                                                       context=context),
    }

    def onchange_date_currency_id(self, cr, uid, ids, moneda, fecha):
        context = {}
        context = dict(context)
        if not moneda:
            return {'value': {'tipo_de_cambio': False}}
        if fecha:
            context.update({'date': fecha})
        else:
            context.update({'date': time.strftime('%Y-%m-%d')})
        currency = self.pool.get('res.currency').browse(cr, uid, moneda, context=context)
        rate = currency.rate_presupuesto  # cambio de rate por rate presupuesto 17/11
        return {'value': {'tipo_de_cambio': rate, 'tipo_de_cambio_fnc': rate}}

    def create(self, cr, uid, values, context=None):
        idcreado = super(grp_pedido_compra, self).create(cr, uid, values, context=context)
        sc_obj = self.pool.get('grp.solicitud.compra')
        # 023 Agregado cambios en la linea
        if 'lineas_ids' in values:
            lineas = values.get('lineas_ids')
            for line in lineas:
                sc_id = line[2] and 'solicitud_compra_id' in line[2] and line[2]['solicitud_compra_id'] or False
                if sc_id:
                    sc_obj.write(cr, uid, sc_id, {'pedido_compra_id': idcreado})
        self.resumir_lineas(cr, uid, [idcreado], context=context)
        return idcreado

    def write(self, cr, uid, ids, values, context=None):
        if not context:
            context = {}
        sc_obj = self.pool.get('grp.solicitud.compra')
        # 023 Agregado cambios en la linea
        if 'lineas_ids' in values:
            lineas = values.get('lineas_ids')
            for line in lineas:
                sc_id = line[2] and 'solicitud_compra_id' in line[2] and line[2]['solicitud_compra_id']
                if sc_id:
                    sc_obj.write(cr, uid, sc_id, {'pedido_compra_id': ids[0]})

        res = super(grp_pedido_compra, self).write(cr, uid, ids, values, context=None)
        # resumen_pedido_compra_ids
        if not context.get('resumen') and not values.get('resumen_pedido_compra_ids', False) and values.get(
                'lineas_ids', False):
            self.resumir_lineas(cr, uid, ids, context=context)
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        default_linea = {
            'solicitud_compra_id': False
        }
        new_child_ids = []
        for rec in self.browse(cr, uid, id, context=context):
            for i in rec.lineas_ids:
                child_id = self.pool.get('grp.linea.pedido.compra').copy(cr, uid, i.id, default_linea, context=context)
                if child_id:
                    new_child_ids.append(child_id)

            default.update({
                'name': 'PC Borrador',
                'state': 'inicio',
                'sice_id_compra': False,
                'apg_ids': False,
                'lineas_ids': [(6, 0, new_child_ids)],

            })

            return super(grp_pedido_compra, self).copy(cr, uid, id, default, context)


    def unlink(self, cr, uid, ids, context=None):
        orden_compras = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in orden_compras:
            if s['state'] in ['inicio']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_(u'Acción inválida!'),
                                     _('El pedido de compras ha sido validado, no se puede borrar.'))
        # automatically sending subflow upon deletion
        wf_service = netsvc.LocalService("workflow")
        for id in unlink_ids:
            wf_service.trg_validate(uid, 'grp.pedido.compra', id, 'button_wkf_pc_cancelar', cr)

        return super(grp_pedido_compra, self).unlink(cr, uid, unlink_ids, context=context)

    def _prepare_resumir_linea(self, cr, uid, ids, pedido, line, context=None):
        vals = {
            'product_id': line[0].product_id.id,
            'product_tmpl_id': line[0].product_id.product_tmpl_id.id,
            'uom_id': line[0].uom_id.id, #cambio de unidad de medida
            'precio_estimado': line[0].precio_estimado,
            'iva':  [(6, 0, [x.id for x in line[0].iva])],
            'cantidad_a_comprar':0,
            'subtotal':0,
            'subtotal_divisa':0,
        }
        if pedido.ampliacion:
            vals.update({
                # nuevos campos agregados a partir de integracion con siif
                'id_variacion': line[0].cotizacion_linea_id and line[0].cotizacion_linea_id.id_variacion,
                'id_item': line[0].cotizacion_linea_id and line[0].cotizacion_linea_id.id_item,
                'partner_id': line[0].cotizacion_linea_id and line[0].cotizacion_linea_id.proveedor_cot_id and line[0].cotizacion_linea_id.proveedor_cot_id.id or False,
            })
        qty_prod = 0
        price = 0
        for li in line:
            qty_prod += li.cantidad_comprar_sice
            price += (li.cantidad_comprar_sice * li.precio_estimado)
            vals.update({
                'cantidad_a_comprar': vals['cantidad_a_comprar'] + li.cantidad_comprar_sice
            })
        vals.update({ 'precio_estimado': price / qty_prod  })
        return vals


    def resumir_lineas(self, cr, uid, ids, context=None):
        resumen_pool = self.pool.get('grp.resumen.pedido.compra')
        ids = [ids] if not isinstance(ids,list) else ids
        for pedido in self.browse(cr,uid,ids,context=context):
            resumenes = []
            resumen_a_crear = defaultdict(lambda:[])
            for lineas in pedido.lineas_ids:
                resumen_a_crear[lineas.product_id.id].append(lineas)
            # if pedido.ampliacion:
            #     for k,v in resumen_a_crear.items():
            #         idvariacion = v[0].cotizacion_linea_id.id_variacion
            #         for elem in v:
            #             if not elem.cotizacion_linea_id.id_variacion or elem.cotizacion_linea_id.id_variacion != idvariacion:
            #                 raise osv.except_osv('Error!', u'El idVariacion del item %s debe ser distinto para diferentes proveedores.' % elem.product_id.product_tmpl_id.name)
            for k,v in resumen_a_crear.items():
                if pedido.ampliacion:
                    for linea_ampliada in v:
                        resumenes.append((0,0, self._prepare_resumir_linea(cr, uid, ids, pedido, line=[linea_ampliada], context=context)))
                else:
                    resumenes.append((0, 0, self._prepare_resumir_linea(cr, uid, ids, pedido, line=v, context=context)))
            linea_ids = [linea.id for linea in pedido.resumen_pedido_compra_ids]
            resumen_pool.unlink(cr,uid,linea_ids,context=context)
            self.write(cr,uid,pedido.id, { 'resumen_pedido_compra_ids': resumenes }, context={ 'resumen' : True })
        return True

    def _prepare_merge_line(self, cr, uid, ids, line, taxes=[], context=None):
        return {
            'solicitud_compra_id': line.id,
            'product_id': line.product_id and line.product_id.id or False,
            'precio_estimado': line.precio_estimado,
            'uom_id': line.uom_id and line.uom_id.id,  # 010 Inicio incidencia pasar um
            'iva': len(taxes) and [(6, 0, [x for x in taxes])] or [],
            'cantidad_comprar_sice': line.cantidad_solicitada
        }

    def _prepare_merge_sc(self, cr, uid, ids, context=None):
        pedido_data = {
            'description': 'Nueva solicitud',
            'lineas_ids': []
        }
        con_error = []
        for line in self.pool.get('grp.solicitud.compra').browse(cr, uid, ids, context=context):
            if line.product_id.id:
                prod = self.pool.get('product.product').browse(cr, uid, line.product_id.id, context=context)
                taxes = []
                for tax in prod.product_tmpl_id.supplier_taxes_id:
                    if tax:
                        taxes.append(tax.id)
                pedido_data['lineas_ids'].append((0, 0, self._prepare_merge_line(cr, uid, ids, line, taxes=taxes, context=context)))
            else:
                con_error.append([line.id, line.name])
        return pedido_data, con_error

    def do_merge_sc(self, cr, uid, ids, context=None):
        '''
            En ids recibimos los identificadores de las solicitudes que compondran el nuevo pedido de compra.
        '''
        # Datos necesarios para crear el nuevo pedido de compra
        pedido_data, con_error = self._prepare_merge_sc(cr, uid, ids, context=context)
        if len(con_error) > 1:
            raise osv.except_osv(_(u'Acción inválida!'), _('El pedido de compra debe tener referencia al producto.'))
        if len(con_error) == 1:
            raise osv.except_osv(_(u'Acción inválida!'),
                                 _('La solicitud de compra %s no tiene referencia al producto.' % (con_error[0][1])))
        # Crear el nuevo pedido de compra con los ids de las solicitudes de compra que se seleccionaron
        idpedido = self.create(cr, uid, pedido_data, context=context)
        # Hay que guardar este pedido de regreso 24/11
        self.pool.get('grp.solicitud.compra').write(cr, uid, ids, {'pedido_compra_id': idpedido}, context=context)
        return idpedido


    def onchange_tipo_compra(self, cr, uid, ids, context=None):
        return {'value': {'sub_tipo_compra': False}}

    def onchange_product_id(self, cr, uid, ids, product_id, uom_id, context=None):
        ''' Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        '''
        value = {'uom_id': ''}
        if product_id:
            prod = self.pool.get('product.template').browse(cr, uid, product_id, context=context)
            value = {'uom_id': prod.uom_id.id, 'precio_estimado': prod.standard_price}
        return {'value': value}

    def button_crear_apg(self, cr, uid, ids, context=None):
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'grp_compras_estatales',
                                                                       'view_apg_form')
        view_id = view_ref and view_ref[1] or False
        if not ids:
            return False
        # ids siempre es una lista de un solo elemento (PC)

        #Control pedido ampliado, debe enviarse a sice antes de crear APG (porque en siif necesita nro ampliacion)
        for pedido in self.browse(cr, uid, ids, context=context):
            if pedido.ampliacion and not pedido.sice_id_compra:
                raise osv.except_osv(_('Error!'), _(u'Para crear una APG de un pedido ampliado, primero debe enviar el pedido a SICE.'))

            apg_values = self._prepare_apg_values(cr, uid, pedido, context=context)

            apg_id = self.pool.get('grp.compras.apg').create(cr, uid, apg_values, context=context)

            if apg_id:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'grp.compras.apg',
                    'res_id': apg_id,
                }

    # link a las apgs asociadas
    def apg_tree_view(self, cr, uid, ids, context):
        rec = self.browse(cr, uid, ids[0], context)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'grp.compras.apg',
            'domain': [('pc_id', '=', rec.id)]
        }

    def oc_tree_view(self, cr, uid, ids, context):

        mod_obj = self.pool.get('ir.model.data')
        oc_ids = []

        orden_obj = self.pool.get('purchase.order')
        oc_ids = orden_obj.search(cr, uid, [('pedido_compra_id', '=', ids[0])])

        res = mod_obj.get_object_reference(cr, uid, 'purchase', 'purchase_order_form')
        res_id = res and res[1] or False

        action_model = False
        action = {}
        if not oc_ids:
            raise osv.except_osv(_('Error!'), _(u'No hay órdenes de compra asociada.'))

        if len(oc_ids) == 1:
            return {
                'name': _(u'Ordenes de compra'),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': [res_id],
                'res_model': 'purchase.order',
                # 'context': "{'type':'in_invoice', 'journal_type': 'purchase'}",
                'domain': [('state', 'not in', ('draft', 'sent', 'confirmed'))],
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'current',
                'res_id': oc_ids and oc_ids[0] or False,
            }

        action_model, action_id = mod_obj.get_object_reference(cr, uid, 'grp_compras_estatales',
                                                               'purchase_form2_action')
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', [" + ','.join(map(str, oc_ids)) + "])]"
        return action

    def adjudicacion_tree_view(self, cr, uid, ids, context):

        mod_obj = self.pool.get('ir.model.data')
        adj_ids = []

        adj_obj = self.pool.get('grp.cotizaciones')
        adj_ids = adj_obj.search(cr, uid, [('pedido_compra_id', '=', ids[0])])

        res = mod_obj.get_object_reference(cr, uid, 'grp_compras_estatales', 'view_grp_cot_form')
        res_id = res and res[1] or False

        action_model = False
        action = {}
        if not adj_ids:
            raise osv.except_osv(_('Error!'), _(u'No hay adjudicaciones asociadas.'))

        if len(adj_ids) == 1:
            return {
                'name': _(u'Adjudicaciones'),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': [res_id],
                'res_model': 'grp.cotizaciones',
                'domain': [],
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'current',
                'res_id': adj_ids and adj_ids[0] or False,
            }

        action_model, action_id = mod_obj.get_object_reference(cr, uid, 'grp_compras_estatales',
                                                               'action_grp_cotizaciones')
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', [" + ','.join(map(str, adj_ids)) + "])]"
        return action

    def button_view_sr(self, cr, uid, ids, context=None):
        for pedido in self.browse(cr, uid, ids, context=context):
            sr_ids = []
            for linea in pedido.lineas_ids:
                if linea.solicitud_compra_id and linea.solicitud_compra_id.solicitud_recursos_id and linea.solicitud_compra_id.solicitud_recursos_id.id not in sr_ids:
                    sr_ids.append(linea.solicitud_compra_id.solicitud_recursos_id.id)
            if not sr_ids:
                raise ValidationError(u"No existen Solicitudes de recurso para este Pedido de compra")
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'grp.compras.solicitud.recursos.almacen',
                'domain': [('id', 'in', sr_ids)]
            }

    def _prepare_apg_values(self, cr, uid, pedido, context=None):
        compras_apg_data = {}
        compras_apg_data['fecha'] = pedido.date_start
        compras_apg_data['moneda'] = pedido.moneda.id
        compras_apg_data['tipo_de_cambio'] = pedido.tipo_de_cambio
        compras_apg_data['descripcion'] = pedido.description
        compras_apg_data['nro_adj'] = pedido.nro_adj.name or False  # 023 incidencia 354  21/09
        compras_apg_data['pc_id'] = pedido.id
        compras_apg_data['monto_divisa'] = pedido.total_estimado_divisa_cpy  # 009 - Setear monto divisa
        compras_apg_data['name'] = 'APG Borrador'
        compras_apg_data['operating_unit_id'] = pedido.operating_unit_id.id
        values_resumen = []
        for linea in pedido.resumen_pedido_compra_ids:
            values_resumen.append((0, 0, {
                'product_id': linea.product_id.id,
                'product_tmpl_id': linea.product_tmpl_id.id,
                'precio_estimado': linea.precio_estimado,
                'iva': [(6, 0, [x.id for x in linea.iva])],
                'cantidad_a_comprar': linea.cantidad_a_comprar,
            }))
        compras_apg_data['lprapg_ids'] = values_resumen
        return compras_apg_data

    # workflow
    # actividades: se ejecutan las funciones al 'llegar' el flujo a la actividad (estado)

    def act_pc_inicio(self, cr, uid, ids, context=None):
        for pc in self.browse(cr, uid, ids, context=context):
            if pc.state != 'inicio':
                self.write(cr, uid, [pc.id], {'state': 'inicio'}, context=context)
        return True

    def check_montos_adjudicados(self, cr, uid, ids, context=None):
        for pedido in self.browse(cr, uid, ids, context=context):
            # monto en pesos de la adjudicacion
            total_adjudicado = pedido.nro_adj.total_estimado
            # calculo el total en pesos de otras ampliaciones asociadas a la adjudicacion
            total_ampliado = 0
            pedidos_ampliados_ids = self.search(cr, uid, [('ampliacion', '=', True),
                                                          ('nro_adj', '=', pedido.nro_adj.id),
                                                          ('state', 'not in', ['inicio', 'rechazado', 'cancelado', 'cancelado_sice']),
                                                          ('id', '!=', pedido.id)])
            if pedidos_ampliados_ids:
                for pedido_ampliado in self.browse(cr, uid, pedidos_ampliados_ids):
                    total_ampliado += pedido_ampliado.total_estimado
            # controlo que el total en pesos del pedido + total en pesos de otras ampliaciones no sea mayor al total adjudicado en pesos
            if pedido.total_estimado + total_ampliado > total_adjudicado:
                msj_error = u"El monto total de las ampliaciones (%s) no puede superar el monto adjudicado de la compra original (%s)" % (pedido.total_estimado + total_ampliado, total_adjudicado)
                raise osv.except_osv('Error!', msj_error)

    def act_pc_confirmado(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context = dict(context)
        # Por cada pedido confirmado
        for pedido in self.browse(cr, uid, ids, context=context):
            #control para ampliaciones
            if pedido.ampliacion and not pedido.renovacion:
                self.check_montos_adjudicados(cr, uid, [pedido.id], context=context)

            if pedido.name == 'PC Borrador':
                # Si el nombre es PC Borrador nunca se le asigno secuencia,
                # por lo tanto busco la secuencia correspondiente al tipo de compra y se la asigno.
                fiscalyear_obj = self.pool.get('account.fiscalyear')
                uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
                fecha_hoy = pedido.date_start
                if fecha_hoy:
                    fiscal_year_id = fiscalyear_obj.search(cr, uid, [('date_start', '<=', fecha_hoy),
                                                                     ('date_stop', '>=', fecha_hoy),
                                                                     ('company_id', '=', uid_company_id)],
                                                           context=context)
                    fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
                    context.update({'fiscalyear_id': fiscal_year_id})

                nombre_secuencia = 'Pedido de compra - ' + pedido.tipo_compra.idTipoCompra
                seq_obj = self.pool.get('ir.sequence')
                id_sec = seq_obj.search(cr, uid, [('name', '=', nombre_secuencia)])
                if len(id_sec) > 0:
                    sequence = seq_obj.get_id(cr, uid, id_sec[0], context=context)
                    ind= sequence.index('-') +1
                    nombrepc = sequence[0:ind] +pedido.company_id.inciso + sequence[ind:len(sequence)]
                    self.write(cr, uid, [pedido.id], {'state': 'confirmado', 'name': nombrepc}, context=context)
                else:
                    # En caso de no encontrar la secuencia, se muestra un mensaje de error
                    raise osv.except_osv('Error!',
                                         u'No está configurada la secuencia para el tipo de compra seleccionada!')
            else:
                # Si el nombre no es PC Borrador ya tiene secuencia, solo actualizo el estado
                self.write(cr, uid, [pedido.id], {'state': 'confirmado'}, context=context)
        return True

    def act_pc_cancelado(self, cr, uid, ids, context=None):
        # Acceder a la adjudicacion asignada al PC, chequear el estado
        for rec in self.browse(cr, uid, ids, context=context):
            pool_cotizaciones = self.pool.get('grp.cotizaciones')
            cot_id = pool_cotizaciones.search(cr, uid, [('pedido_compra_id', '=', rec.id)])
            if cot_id:
                if len(cot_id) > 0:
                    cot_id = cot_id[0]
                cot_obj = pool_cotizaciones.browse(cr, uid, cot_id)
                if cot_obj.state not in ['cancelado']:
                    raise osv.except_osv('Error!',
                                     u'No es posible cancelar un Pedido de Compra si '
                                     u'la adjudicación no está cancelada.')
        return self.write(cr, uid, ids, {'state': 'cancelado'}, context=context)

    def act_pc_sice(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'sice'}, context=context)

    def act_cancel_sice(self, cr, uid, ids, context=None):
        # Acceder a la adjudicacion asignada al PC, chequear el estado
        for rec in self.browse(cr, uid, ids, context=context):
            pool_cotizaciones = self.pool.get('grp.cotizaciones')
            cot_id = pool_cotizaciones.search(cr, uid, [('pedido_compra_id', '=', rec.id)])
            if cot_id:
                if len(cot_id) > 0:
                    cot_id = cot_id[0]
                cot_obj = pool_cotizaciones.browse(cr, uid, cot_id)
                if cot_obj.state not in ['cancelado']:
                    raise osv.except_osv('Error!',
                                     u'No es posible cancelar un Pedido de Compra si '
                                     u'la adjudicación no está cancelada.')
        self.write(cr, uid, ids, {'state': 'cancelado_sice'}, context=context)
        return True

    def act_cancel_sice_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'inicio'})
        wf_service = netsvc.LocalService("workflow")
        for pc_id in ids:
            wf_service.trg_delete(uid, 'grp.pedido.compra', pc_id, cr)
            wf_service.trg_create(uid, 'grp.pedido.compra', pc_id, cr)
        return True

    def act_cancelado_borrador(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            for line in rec.apg_ids:
                if line.state not in ['desafectado', 'anulada']:
                    raise osv.except_osv(u'Error!', u'Se deben anular las APG asociadas antes de poder cancelar'
                                                    u' el pedido de compra.')
        self.write(cr, uid, ids, {'state': 'inicio'}, context=context)
        wf_service = netsvc.LocalService("workflow")
        for pc_id in ids:
            wf_service.trg_delete(uid, 'grp.pedido.compra', pc_id, cr)
            wf_service.trg_create(uid, 'grp.pedido.compra', pc_id, cr)
        return True

    def verificar_datos(self, cr, uid, ids, pedido, tipo, context=None):
        pool_configuracion = self.pool.get('grp.monto.compras')
        pool_subconfig = self.pool.get('grp.linea.monto.compra')
        pool_linea_pc = self.pool.get('grp.linea.pedido.compra')
        pool_pc = self.pool.get('grp.pedido.compra')
        for detalle in pedido.lineas_ids:
            product = detalle.product_id
            query = """
                select l.id, l.pedido_compra_id from
                grp_linea_pedido_compra l,
                grp_pedido_compra pc,
                sicec_tipo_compra tc,
                product_product pp,
                product_template pt
                where l.pedido_compra_id in
                (select id
                from grp_pedido_compra
                where state not in ('inicio', 'cancelado_sice', 'cancelado') and
                l.pedido_compra_id = pc.id and
                pc.tipo_compra = tc.id and
                tc."idTipoCompra" in """
            if tipo == 'CD':
                query += "('CD')"
            else:
                query += "('CD', 'LA')"
            query += """
             and
                pc.id <> %(pc_id)s and
                extract(YEAR from date_start) = %(year)s) and
                l.product_id = pp.id and
                pp.id = %(prod_id)s and
                pp.product_tmpl_id = pt.id and
                pt.grp_sice_cod = %(sice_cod)s
            """
            cr.execute(query, {'pc_id': pedido.id,
                  'year': int(pedido.date_start.split('-')[0]),
                  'prod_id': product.id,
                  'sice_cod': product.grp_sice_cod})
            res = cr.fetchall()
            # hacer loop sobre los resultados, calcular el total de las lineas
            # y compararlas contra el monto maximo TOCAF para el tipo CD/LA
            total = 0
            for linea in res:
                linea_obj = pool_linea_pc.browse(cr, uid, linea[0])
                total += linea_obj.subtotal

            total_pedido = detalle.subtotal

            configuracion = pool_configuracion.search(cr, 1, [
                ('anio_vigencia', '=', pedido.date_start.split('-')[0]),
                ('activo_compras', '=', True)
            ], context=context)
            if not len(configuracion):
                raise osv.except_osv('Error!',
                                     u'No existe configuración activa para el periodo correspondiente.'
                                     u' Debe crear una configuración de montos para TOCAF y activarla o'
                                     u' contactar al administrador de sistema!')
            config = pool_configuracion.browse(cr, 1, configuracion, context=context)[0]
            subconfiguracion = pool_subconfig.search(cr, 1, [('monto_compra_id', '=', config.id),
                                                             ('tipo_compra_id', '=', pedido.tipo_compra.id)],
                                                     context=context)
            if not len(subconfiguracion):
                raise osv.except_osv('Error!',
                                     u'No hay montos especificados para el tipo de compra seleccionada. '
                                     u'Contactar al administrador de sistema!')
            subconfig = pool_subconfig.browse(cr, 1, subconfiguracion, context=context)[0]
            if subconfig.tipo_compra_id.idTipoCompra == pedido.tipo_compra.idTipoCompra\
                    and total_pedido + total > subconfig.hasta:
                return True
        return False

    def button_pc_inicio_validado(self, cr, uid, ids, context=None):
        # realizar validacion, si se cumple retorna el metodo que continua con la validacion
        # si no se cumple, invocar al wizard
        pool_configuracion = self.pool.get('grp.monto.compras')
        pool_subconfig = self.pool.get('grp.linea.monto.compra')
        pool_linea_pc = self.pool.get('grp.linea.pedido.compra')
        pedido = self.browse(cr, uid, ids, context=context)[0]

        for linea_pedido in pedido.lineas_ids:
            if linea_pedido.precio_estimado <= 0:
                raise osv.except_osv(u'Error!', u'El precio estimado para un producto no debe ser nulo ni negativo.')
            if linea_pedido.cantidad_comprar_sice <= 0:
                raise osv.except_osv(u'Error!', u'La cantidad a comprar para un producto no debe ser nula ni negativa.')
            if not linea_pedido.iva:
                raise osv.except_osv(u'Error!', u'Hay líneas del pedido que no tienen al menos'
                                                u' un valor en el campo IVA.')

        if not pedido.ampliacion:
            configuracion = pool_configuracion.search(cr, 1, [('anio_vigencia', '=', pedido.date_start.split('-')[0]),
                                                              ('activo_compras', '=', True)], context=context)
            if not len(configuracion):
                raise osv.except_osv('Error!',
                                     u'No existe configuración activa para el periodo correspondiente. Debe crear una configuración de montos para TOCAF y activarla o contactar al administrador de sistema!')
            config = pool_configuracion.browse(cr, 1, configuracion, context=context)[0]
            subconfiguracion = pool_subconfig.search(cr, 1, [('monto_compra_id', '=', config.id),
                                                             ('tipo_compra_id', '=', pedido.tipo_compra.id)],
                                                     context=context)
            if not len(subconfiguracion):
                raise osv.except_osv('Error!',
                                     u'No hay montos especificados para el tipo de compra seleccionada. Contactar al administrador de sistema!')
            subconfig = pool_subconfig.browse(cr, 1, subconfiguracion, context=context)[0]
            if pedido.total_estimado < subconfig.desde:
                raise osv.except_osv('Error!',
                                     u'Debe utilizar un tipo de compra acorde al monto solicitado (monto mínimo: $' + str(
                                         subconfig.desde) + ')!')
            if pedido.total_estimado > subconfig.hasta:
                raise osv.except_osv('Error!',
                                     u'Debe utilizar un tipo de compra acorde al monto solicitado (monto máximo: $' + str(
                                         subconfig.hasta) + ')!')

        verificacion = False
        if pedido.tipo_compra:
            if pedido.tipo_compra.idTipoCompra in ['CD']:
                # chequeo de compra directa
                verificacion = self.verificar_datos(cr, uid, ids, pedido, 'CD', context=context)
            elif pedido.tipo_compra.idTipoCompra in ['LA']:
                # chequeo de licitacion abreviada
                verificacion = self.verificar_datos(cr, uid, ids, pedido, 'LA', context=context)
        # si no es ninguno de esos tipos, pasa directo a validar el PC
        if verificacion:
            # disparo el wizard
            data_pool = self.pool.get('ir.model.data')
            action_model, action_id = data_pool.\
                get_object_reference(cr, uid,
                                     'grp_compras_estatales',
                                     'view_grp_alerta_validacion_procedimiento_compra')
            return {
                'name': "Alerta de Validación de Procedimiento de Compra",
                'res_model': "grp.alerta.validacion.procedimiento.wizard",
                'src_model': "grp.pedido.compra",
                'view_mode': "form",
                'target': "new",
                'type': 'ir.actions.act_window',
                'view_id': action_id,
            }
        else:
            wf_service = netsvc.LocalService('workflow')
            wf_service.trg_validate(uid, 'grp.pedido.compra', pedido.id, 'button_pc_inicio_validado', cr)
        return True

    def send_notification(self, cr, uid, rs_id, context=None):
        recurso_obj = self.browse(cr, uid, rs_id, context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        msg = _(u"Se realizará un procedimiento de compras (%s) por un importe que implica que"
                u" se supere el límite del tipo de procedimiento (%s) para el año en curso.") %\
               (recurso_obj.name, recurso_obj.tipo_compra.descTipoCompra)
        group_id = self.pool.get('res.groups').get_group_by_ref(cr,
                                                                uid,
                                                                'grp_seguridad.grp_compras_apg_Responsable_SIIF')
        partner_ids = []
        group_element = self.pool.get('res.groups').browse(cr, uid, group_id[0], context=context)
        users2 = group_element.users
        for user_ingroup in users2:
            # if user_ingroup.department_id.id == recurso_obj.departamento.id:
            partner_ids.append(user_ingroup.partner_id.id)
        if context is None:
            context = {}
        context = dict(context)
        context.update({'mail_notify_noemail': True})
        if partner_ids:
            self.message_post(cr, uid, [rs_id], body=msg, type='notification', subtype='mt_comment', partner_ids=partner_ids, context=context)
        return True

class grp_linea_pedido_compra(osv.osv):
    _name = 'grp.linea.pedido.compra'
    _description = 'Lineas de los pedidos de compra'

    ESTADO = [
        ('RECH', 'Rechazado'),
        ('PPROC', 'Postergado/Procedimiento'),
        ('PPRES', 'Postergado/Presupuesto')
    ]

    def _get_monto_divisa(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            taxes = tax_obj.compute_all(cr, uid, line.iva, line.precio_estimado, line.cantidad_comprar_sice, None, None)
            cur = line.pedido_compra_id.moneda
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])

        return res

    def _get_precio_real(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            cur = line.pedido_compra_id.moneda
            real_price = line.precio_estimado
            for tax in line.iva:
                tax_calc = tax_obj.compute_all(cr, uid, tax, line.precio_estimado, 1, None)
                if not tax.price_include:
                    real_price -= tax_calc['total']
            cur = line.pedido_compra_id.moneda
            res[line.id] = cur_obj.round(cr, uid, cur, real_price)
        return res

    def _get_importe_base(self, cr, uid, ids, fields, args, context=None):
        res = {}
        currency_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids, context=context):
            moneda = line.pedido_compra_id.moneda.id
            moneda_base = line.pedido_compra_id.company_id.currency_id.id
            context = dict(context)
            if moneda != moneda_base:
                context.update({'date': line.pedido_compra_id.date_start, 'pricelist_type': 'presupuesto'})
                monto = currency_obj.compute(cr, uid, moneda, moneda_base, line.monto_divisa, context=context)
                res[line.id] = {
                    'monto': monto or 0.0,
                    'monto_round': round(monto),
                }
            else:
                res[line.id] = {
                    'monto': line.monto_divisa or 0.0,
                    'monto_round': round(line.monto_divisa),
                }
        return res

    def buscar_unidades_ids(self, cr, uid, ids, name, args, context=None):
        grp_art_sice_obj = self.pool.get("grp.sice_art_serv_obra")
        result = {}
        um_codes = []
        if ids:
            prod_uom_object = self.pool.get('product.uom')
            for rec in self.browse(cr, uid, ids):
                result[rec.id] = False
                if rec.product_id.grp_sice_cod > 0:
                    articulo_sice_ids = grp_art_sice_obj.search(cr, 1, [('cod','=', rec.product_id.grp_sice_cod)])
                    if articulo_sice_ids:
                        articulo_sice_id = articulo_sice_ids[0]
                        articulo_sice = grp_art_sice_obj.browse(cr, 1, articulo_sice_id)
                        unidades_med_sice_ids = [x.id for x in articulo_sice.unidades_med_ids]
                        uom_ids = prod_uom_object.search(cr, 1, [('sice_uom_id','in',unidades_med_sice_ids)])
                        if uom_ids:
                            result[rec.id] = uom_ids
                else:
                    uom_ids = prod_uom_object.search(cr, uid, [('active', '=', True)], context=context)
                    if uom_ids:
                        result[rec.id] = uom_ids
        return result

    def _check_uom(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if line.product_id.uom_id.category_id.id != line.uom_id.category_id.id:
                return False
        return True

    def _get_subtotal(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.cantidad_comprar_sice * rec.precio_estimado
        return res

    _columns = {
        'pedido_compra_id': fields.many2one('grp.pedido.compra', 'Pedido de compra', ondelete='cascade'),
        'solicitud_compra_id': fields.many2one('grp.solicitud.compra', 'Solicitud de compra', ondelete='restrict'),
        'product_id': fields.many2one('product.product', u'Producto', ondelete='restrict', required=True),

        'uom_id': fields.many2one('product.uom', string='UdM', ondelete='restrict', required=True),
        'domain_art_uom_ids': fields.function(buscar_unidades_ids, method=True, type='many2many',
                                              relation='product.uom', string='Lista domain unidades de medida'),

        'odg': fields.related('product_id', 'grp_objeto_del_gasto', type='integer', readonly=True),
        'sc_descripcion': fields.related('solicitud_compra_id', 'description', string=u'Descripción', type='char',
                                         readonly=True),
        'cantidad_solicitada': fields.related('solicitud_compra_id', 'cantidad_solicitada',
                                              string='Cantidad solicitada', type='float', readonly=True, store=True),
        'precio_sin_iva': fields.function(_get_precio_real, type='float', digits_compute=(16,4),
                                          string='Precio sin iva', help='Precio real sin IVA.'),

        'precio_estimado': fields.float('Precio estimado', required=True, digits_compute=dp.get_precision('Cantidad')),
        'sice_cod_articulo': fields.related('product_id', 'grp_sice_cod', type='integer', string=u'Código',
                                            readonly=True),
        'sice_cod_unidad': fields.integer('CodUnidad'),  # TODO related
        'llave_presupuestal': fields.integer('Llave Presupuestal'),
        'cantidad_comprar_sice': fields.float('Cantidad a comprar', required=True),
        'iva': fields.many2many('account.tax', 'pedido_compra_line_tax', 'linea_pcompra_id', 'tax_id', 'IVA'),
        'descripcion': fields.text(u'Descripción'),  # required=True),
        'monto': fields.function(_get_importe_base, method=True, multi='importe_base', type='float',
                                 digits_compute=dp.get_precision('Cantidad'), string=u'Total estimado pesos'),
        'monto_round': fields.function(_get_importe_base, method=True, multi='importe_base', type='float',
                                       digits=(16, 0), string=u'Total estimado pesos'),
        'monto_divisa': fields.function(_get_monto_divisa, type='float', digits_compute=dp.get_precision('Cantidad'),
                                        string='Total estimado divisa'),
        'estado': fields.selection(ESTADO, 'Estado'),
        'cotizacion_linea_id': fields.many2one('grp.cotizaciones.lineas.aceptadas', string=u'Adjudicacion línea ref',
                                               ondelete='restrict'),
        'id_variacion': fields.integer(u'Id Variación'),
        'id_item': fields.integer(u'Id Item'),

        'partner_id': fields.many2one('res.partner', u'Proveedor'),  # Proveedor relacionado
        'tipoDocProv': fields.related('partner_id', 'tipo_doc_rupe', type='selection', store=True,
                                      selection=[('R', u'R - RUT'),
                                                 ('CI', u'CI - Cedula de Identidad'),
                                                 ('PS', u'PS - Pasaporte'),
                                                 ('NIE', u'NIE - Documento Extranjero')], string=u'Tipo Doc Proveedor'),

        'nroDocProv': fields.related('partner_id', 'nro_doc_rupe', type='char', store=True, size=43,
                                     string=u'Nro Doc Proveedor'),
        # cantidad_comprar_sice * precio_estimado
        'subtotal': fields.function(_get_subtotal, type='float', string=u"Subtotal"),
    }

    _sql_constraints = [
        ('solicitud_compra_uniq', 'unique (pedido_compra_id, solicitud_compra_id)',
         u'La solicitud de compra debe ser única por Pedido de Compra !'),
    ]

    _constraints = [
        (_check_uom,
         'You try to move a product using a UoM that is not compatible with the UoM of the product moved. Please use an UoM in the same UoM category.',
         ['uom_id']),
    ]

    _defaults = {
        'cantidad_comprar_sice': 1,
    }

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        value = {}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            taxes = []
            for tax in prod.product_tmpl_id.supplier_taxes_id:
                taxes.append(tax.id)
            value = {
                # 'precio_estimado': prod.product_tmpl_id.standard_price,
                'uom_id': prod.product_tmpl_id.uom_id.id,
                'sice_cod_articulo': prod.grp_sice_cod,
                'iva': taxes,
                'odg': prod.product_tmpl_id.grp_objeto_del_gasto
            }
            # domain de productos
            uom_domain_ids = []
            if prod.product_tmpl_id.domain_art_uom_ids:
                for art_uom_id in prod.product_tmpl_id.domain_art_uom_ids:
                    uom_domain_ids.append(art_uom_id.id)
            result_add = {'uom_id': [('id', 'in', uom_domain_ids)]}
            value.update({'domain': result_add})
            value.update({'domain_art_uom_ids': uom_domain_ids})

        return {'value': value}

    def onchage_linea(self, cr, uid, ids, solicitud_compra_id, context=None):
        value = {'sc_descripcion': False, }
        if solicitud_compra_id:
            linea = self.pool.get('grp.solicitud.compra').browse(cr, uid, solicitud_compra_id, context=None)
            value.update({
                'product_id': linea.product_id.id,
                'cantidad_solicitada': linea.cantidad_solicitada,
                'cantidad_comprar_sice': linea.cantidad_solicitada,
                'uom_id': linea.uom_id.id,
                'precio_estimado': linea.precio_estimado,
                'sc_descripcion': linea.description,
            })
        return {'value': value}

    def onchange_iva(self, cr, uid, ids, iva, cantidad_solicitada, precio_estimado, context=None):
        tax_obj = self.pool.get('account.tax')
        tax_ids = []
        for x in iva:
            if len(x[2]):
                tax_ids.append(x[2][0])
        if len(tax_ids) == 0:
            return {'value': {}}
        tax_brw = tax_obj.browse(cr, uid, tax_ids)
        taxes = tax_obj.compute_all(cr, uid, tax_brw, precio_estimado, cantidad_solicitada)
        value = {
            'monto_divisa': taxes['total_included'],
        }
        return {'value': value}

    def onchange_cantidad_comprar_sice(self, cr, uid, ids, cantidad_comprar_sice, precio_estimado, iva, context=None):
        tax_obj = self.pool.get('account.tax')
        tax_ids = []
        for x in iva:
            if len(x[2]):
                tax_ids.append(x[2][0])
        if len(tax_ids) == 0:
            return {'value': {}}
        tax_brw = tax_obj.browse(cr, uid, tax_ids)
        taxes = tax_obj.compute_all(cr, uid, tax_brw, precio_estimado, cantidad_comprar_sice)
        value = {
            'monto_divisa': taxes['total_included'],
        }
        return {'value': value}

    def onchange_cantidad_solicitada(self, cr, uid, ids, cantidad_solicitada, precio_estimado, iva, context=None):
        tax_obj = self.pool.get('account.tax')
        tax_ids = []
        for x in iva:
            if len(x[2]):
                tax_ids.append(x[2][0])
        if len(tax_ids) == 0:
            return {'value': {}}
        tax_brw = tax_obj.browse(cr, uid, tax_ids)
        taxes = tax_obj.compute_all(cr, uid, tax_brw, precio_estimado, cantidad_solicitada)
        value = {
            'monto_divisa': taxes['total_included'],
        }
        return {'value': value}

    def unlink(self, cr, uid, ids, context=None):
        linea = self.browse(cr, uid, ids)
        sc_id = linea.solicitud_compra_id and linea.solicitud_compra_id.id
        sc_obj = self.pool.get('grp.solicitud.compra')
        if sc_id:
            sc_obj.write(cr, uid, sc_id, {'pedido_compra_id': False})
        return super(grp_linea_pedido_compra, self).unlink(cr, uid, ids, context=context)

class grp_resumen_pedido_compra(osv.osv):
    _name = 'grp.resumen.pedido.compra'

    # 027 - Comentado esto
    def _get_monto_divisa(self, cr, uid, ids, fieldname, args, context=None):
        res = {}

        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            taxes = tax_obj.compute_all(cr, uid, line.iva, line.precio_estimado, line.cantidad_a_comprar, None, None)
            cur = line.pedido_compra_id.moneda
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res

    def _get_importe_base(self, cr, uid, ids, name, arg, context={}):
        res = {}
        currency_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids, context=context):
            moneda = line.pedido_compra_id.moneda.id
            moneda_base = line.pedido_compra_id.company_id.currency_id.id
            if moneda != moneda_base:
                context = dict(context)
                context.update({'date': line.pedido_compra_id.date_start, 'pricelist_type': 'presupuesto'})
                res[line.id] = currency_obj.compute(cr, uid, moneda, moneda_base, line.subtotal_divisa, context=context)
            else:
                res[line.id] = line.subtotal_divisa
        return res

    def _get_calcula_precios(self, cr, uid, ids, fields, args, context={}):
        res = {}
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                'precio_sin_iva': 0,
                'precio_estimado_pesos': 0,
                'precio_pesos_sin_iva': 0,
            }

            # Se calcula para cantidad = 1 asi se obtiene el precio unitario
            taxes = tax_obj.compute_all(cr, uid, line.iva, line.precio_estimado, 1, None, None)
            cur = line.pedido_compra_id.moneda
            real_price = cur_obj.round(cr, uid, cur, taxes['total'])
            precio_pesos = real_price
            precio_pesos_sin_iva = real_price

            moneda = line.pedido_compra_id.moneda.id
            moneda_base = line.pedido_compra_id.company_id.currency_id.id
            if moneda != moneda_base:
                context = dict(context)
                context.update({'date': line.pedido_compra_id.date_start, 'pricelist_type': 'presupuesto'})
                precio_pesos = cur_obj.compute(cr, uid, moneda, moneda_base, line.precio_estimado, context=context)
                #calculo precio sin iva, problemas de redondeo, conviero a USD primero y luego calculo sin impuestos
                impuestos_pesos = tax_obj.compute_all(cr, uid, line.iva, precio_pesos, 1, None, None)
                precio_pesos_sin_iva = impuestos_pesos['total']

            res[line.id] = {
                'precio_sin_iva': real_price,
                'precio_estimado_pesos': precio_pesos,
                'precio_pesos_sin_iva': precio_pesos_sin_iva
            }
        return res

    _columns = {
        'pedido_compra_id': fields.many2one('grp.pedido.compra', ondelete='cascade'),
        'product_id': fields.many2one('product.product', u'Producto', ondelete='restrict', required=True,
                                      readonly=True),
        'product_tmpl_id': fields.many2one('product.template', u'Producto', required=True, ondelete='restrict',
                                           readonly=True, select=True),
        'uom_id': fields.many2one('product.uom', string='UdM', readonly=True),
        'objeto_del_gasto': fields.related('product_id', 'grp_objeto_del_gasto', type='integer',
                                           string='Objeto del gasto', store=False, readonly=True),
        'llave_presupuestal': fields.char('Llave presupuestal'),
        'cantidad_a_comprar': fields.float('Cantidad a comprar', digits_compute=dp.get_precision('Cantidad'),
                                           required=True),
        'cantidad_entregada': fields.float('Cantidad entregada', digits_compute=dp.get_precision('Cantidad')),

        'precio_estimado': fields.float('Precio estimado divisa', digits_compute=dp.get_precision('Cantidad'),
                                        required=True),
        'precio_estimado_pesos': fields.function(_get_calcula_precios, type='float', multi='precios',
                                                 digits_compute=dp.get_precision('Cantidad'),
                                                 string='Precio estimado pesos'),
        'precio_sin_iva': fields.function(_get_calcula_precios, type='float', multi='precios',
                                          digits_compute=(16,4), string='Precio sin iva',
                                          help='Precio real sin IVA.'),
        'precio_pesos_sin_iva': fields.function(_get_calcula_precios, type='float', multi='precios',
                                          digits_compute=(16,4), string='Precio sin iva en pesos',
                                          help='Precio real sin IVA en Pesos.'),
        # Precio real calculado sin los impuestos en caso de impuesto incluido
        'iva': fields.many2many('account.tax', 'pedido_compra_line_resumen_tax', 'linea_resumen_pcompra_id', 'tax_id',
                                'IVA'),
        'subtotal': fields.function(_get_importe_base, type='float', digits_compute=dp.get_precision('Cantidad'),
                                    string='Total estimado pesos'),
        'subtotal_divisa': fields.function(_get_monto_divisa, type='float', digits_compute=dp.get_precision('Cantidad'),
                                           string='Total estimado divisa'),

        'id_variacion': fields.integer(u'Id Variación'),
        'id_item': fields.integer(u'Id Item'),

        'partner_id': fields.many2one('res.partner', u'Proveedor'),  # Proveedor relacionado
        'tipoDocProv': fields.related('partner_id', 'tipo_doc_rupe', type='selection', store=True,
                                      selection=[('R', u'R - RUT'),
                                                 ('CI', u'CI - Cedula de Identidad'),
                                                 ('PS', u'PS - Pasaporte'),
                                                 ('NIE', u'NIE - Documento Extranjero')], string=u'Tipo Doc Proveedor'),

        'nroDocProv': fields.related('partner_id', 'nro_doc_rupe', type='char', store=True, size=43,
                                     string=u'Nro Doc Proveedor'),
    }

    _defaults = {
        'cantidad_entregada': 0
    }
