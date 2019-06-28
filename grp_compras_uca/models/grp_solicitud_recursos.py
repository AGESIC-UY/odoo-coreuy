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

import time
from openerp.osv import osv, fields
from openerp import api, models, fields as fields_new_api
from openerp.exceptions import ValidationError
from openerp.tools.translate import _
from openerp.tools.sql import drop_view_if_exists


LISTA_ESTADOS_COT = [
    ('draft', 'Borrador'),
    ('comision_asesora', u'Comisión asesora'),
    ('devuelto_compras', 'Devuelto a compras'),
    ('validado', u'Validado'),
    ('in_approval', u'En aprobación'),
    ('approved', u'Aprobado'),
    ('in_authorization', u'En autorización'),
    ('authorized', u'Autorizado'),
    ('refused', u'Rechazado '),
    ('aprobado_sice', 'Aprobado SICE'),
    ('cancelado', 'Cancelado'),
]

class grp_compras_solicitud_recursos_almacen(osv.osv):
    _name = 'grp.compras.solicitud.recursos.almacen'
    _inherit = 'grp.compras.solicitud.recursos.almacen'

    _columns = {
        'sentencia_ordenanza': fields.selection([('normal', 'Normal'),
                      ('compra_uca', 'Compra por UCA'),
                      ('regularizacion', u'Regularización')], 'Sub-Tipo Solicitud', required=True),
        'compra_uca_ids': fields.one2many('grp.compras.solicitud.uca', 'solicitud_id', 'Compras UCA'),
        'number_uca': fields.char(u'Nro.Licitación UCA', size=10),
    }

    # TODO SPRING 7 GAP 465 R
    def _get_uca_dict(self):
        compra_uca = [(5,)]
        for solicitud_line in self.grp_sr_id:
            compra_uca.append(
                (0, 0, {'product_id': solicitud_line.product_id.id,
                        'quantity': solicitud_line.cantidad_solicitada,
                        'price': solicitud_line.monto,
                        'description': solicitud_line.descripcion,
                        'solicitud_line_id': solicitud_line.id,
                        'pedido_linea_id': False}))
        return compra_uca

    def onchange_compra_uca_ids(self, cr, uid, ids, sentencia_ordenanza, grp_sr_id, context=None):
        res = {'value': {}}
        compra_uca_ids = []
        solicitud = self.browse(cr, uid, ids, context)
        if sentencia_ordenanza == 'compra_uca':
            if solicitud.id:
                compra_uca_ids = solicitud._get_uca_dict()
            res['value']['compra_uca_ids'] = compra_uca_ids
        else:
            res['value']['compra_uca_ids'] = False
        return res

    def create(self, cr, uid, vals, context=None):
        new_sr_id = super(grp_compras_solicitud_recursos_almacen, self).create(cr, uid, vals, context=context)
        new_sr = self.browse(cr, uid, new_sr_id)
        if new_sr.sentencia_ordenanza == 'compra_uca':
            uca_vals = ({'compra_uca_ids': new_sr._get_uca_dict()})
            self.write(cr, uid, new_sr_id, uca_vals, context)
        return new_sr_id

    def write(self, cr, uid, ids, values, context=None):
        res = super(grp_compras_solicitud_recursos_almacen, self).write(cr, uid, ids, values, context=context)
        if values.get('grp_sr_id'):
            for rec in self.browse(cr,uid,ids,context):
                if rec.sentencia_ordenanza == 'compra_uca':
                    uca_vals = ({'compra_uca_ids': rec._get_uca_dict()})
                    self.write(cr, uid, rec.id, uca_vals, context)
        return res

    def act_sr_almacen_en_aprobacion(self, cr, uid, ids, context=None):
        for r in self.browse(cr, uid, ids, context=context):
            if r.sentencia_ordenanza in ['compra_uca']:
                for line_sr in r.grp_sr_id:
                    if not line_sr.product_id:
                        raise osv.except_osv(_(u'Error!'), _(u'Complete el campo Producto en las líneas de la SR.'))
                for line_uca in r.compra_uca_ids:
                    if not line_uca.description:
                        raise osv.except_osv(_(u'Error!'), _(u'Complete el campo Número item UCA en las líneas de UCA.'))
                    if not line_uca.number:
                        raise osv.except_osv(_(u'Error!'), _(u'Complete el campo Número item UCA en las líneas de UCA.'))
                    if not line_uca.price:
                        raise osv.except_osv(_(u'Error!'), _(u'Complete el campo Precio en las líneas de UCA.'))
                    if not line_uca.provider_id:
                        raise osv.except_osv(_(u'Error!'), _(u'Complete el campo Proveedor en las líneas de UCA.'))
        return super(grp_compras_solicitud_recursos_almacen, self).act_sr_almacen_en_aprobacion(cr, uid, ids, context=context)

class GrpComprasSolicitudRecursosAlmacenNewApi(models.Model):
    _inherit = 'grp.compras.solicitud.recursos.almacen'

    lineas_readonly = fields_new_api.Boolean("Linea editables", compute='_compute_lineas_readonly', default=False)

    @api.depends('tipo_sr', 'state')
    def _compute_lineas_readonly(self):
        for record in self:
            # Agrego control adicional para que la linea sea readonly para compras_uca fuera del estado inicio.
            if record.sentencia_ordenanza in ['compra_uca'] and record.state not in ['inicio']:
                record.lineas_readonly = True
            elif record.state in ['rechazado','aprobado','esperando_almacen']:
                record.lineas_readonly = True
            elif record.state == 'inicio':
                record.lineas_readonly = False
            elif record.state in ['codificando']:
                if self.env.user.has_group('grp_seguridad.grp_compras_sr_Encargado_de_almacen'):
                    record.lineas_readonly = False
                else:
                    record.lineas_readonly = True
            elif record.state == 'en_aprobacion':
                if record.tipo_sr == 'PL':
                    if self.env.user.has_group('grp_compras_estatales.grp_sr_aprobador_planif'):
                        record.lineas_readonly = False
                    else:
                        record.lineas_readonly = True
                else:
                    if self.env.user.has_group('grp_seguridad.grp_compras_sr_Aprobador'):
                        record.lineas_readonly = False
                    else:
                        record.lineas_readonly = True
                record.lineas_readonly = False
            else:
                record.lineas_readonly = False

class GrpComprasSolicitudRecursosLineSr(models.Model):
    _inherit = 'grp.compras.solicitud.recursos.line.sr'

    @api.depends('grp_id')
    def _get_sentencia_ordenanza(self):
        sr_alm_obj = self.env['grp.compras.solicitud.recursos.almacen']
        for rec in self:
            rec.sentencia_ordenanza = False
            if rec.grp_id:
                sr_id = sr_alm_obj.search([('sr_id', '=', rec.grp_id.id)])
                if sr_id:
                    rec.sentencia_ordenanza = sr_id.sentencia_ordenanza

    sentencia_ordenanza = fields_new_api.Selection(string=u'Sub-tipo Solicitud',
                                                   selection=[
                                                        ('normal', 'Normal'),
                                                        ('compra_uca', 'Compra por UCA'),
                                                   ],
                                                   compute='_get_sentencia_ordenanza')
    parent_state = fields_new_api.Selection(string='Estado Solicitud', related="grp_id.state", readonly=True, store=True)


# TODO: SPRING 7 GAP 465
class grp_compras_solicitud_uca(models.Model):
    _name = 'grp.compras.solicitud.uca'

    solicitud_id = fields_new_api.Many2one('grp.compras.solicitud.recursos.almacen', 'Solicitud')
    solicitud_line_id = fields_new_api.Many2one('grp.compras.solicitud.recursos.line.sr', u'Línea de la SR')
    pedido_id = fields_new_api.Many2one('grp.pedido.compra', 'Pedido de Compra')
    pedido_linea_id = fields_new_api.Many2one('grp.linea.pedido.compra', u'Línea de Pedido de Compra')
    solicitud_compra_id = fields_new_api.Many2one('grp.solicitud.compra', 'Pedido de Compra')
    product_id = fields_new_api.Many2one('product.product', 'Producto')
    uom_id = fields_new_api.Many2one('product.uom', string='UdM', related='product_id.uom_id')
    description = fields_new_api.Char(u'Descripción')
    quantity = fields_new_api.Float('Cantidad')
    price = fields_new_api.Float('Precio')
    provider_id = fields_new_api.Many2one('res.partner', 'Proveedor')
    number = fields_new_api.Char(u'Número item UCA')
    state_solicitud = fields_new_api.Selection(string=u'Estado', related='solicitud_id.state')
    state_compra = fields_new_api.Selection(string=u'Estado', related='pedido_id.state')
    sentencia_ordenanza = fields_new_api.Selection(string=u'Sub-tipo Solicitud',
                                                   related='solicitud_id.sentencia_ordenanza')
