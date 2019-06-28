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

from openerp import models, fields, api, _

SENTENCIA_ORDENANZA = [
    ('compra_uca', 'Compra por UCA'),
    ('normal', 'Normal'),
]

class grp_solicitud_compra_v8(models.Model):
    _inherit = 'grp.solicitud.compra'
    _name = 'grp.solicitud.compra'

    provider_id = fields.Many2one('res.partner', 'Proveedor')
    number_uca = fields.Char(u'Nro.Licitación UCA', size=10,
                             compute='_compute_solicitud_recursos_items', multi='items', store=True)
    sentencia_ordenanza = fields.Selection(SENTENCIA_ORDENANZA, string='Sub-Tipo Solicitud',
                                           compute='_compute_solicitud_recursos_items', multi='items', store=True)
    number = fields.Char(u'Número item UCA')

    def _crear_solicitud_linea(self, cr, uid, browse_id, context=None):
        if not context:
            context = {}
        sr_pool = self.pool.get('grp.compras.solicitud.recursos.almacen').search(cr, uid, [('sr_id','=',browse_id.grp_id.id)])
        almacen = False
        if len(sr_pool):
            almacen = self.pool.get('grp.compras.solicitud.recursos.almacen').browse(cr, uid, sr_pool[0], context=context)
        if almacen and almacen.sentencia_ordenanza == 'compra_uca' and almacen.compra_uca_ids:
            # Si la linea de UCA no tiene linea de solicitud, entonces
            # hace la busqueda por product_id
            # Si la linea de UCA tiene linea de solicitud, entonces
            # hace la busqueda por solicitud_line_id
            uca_line = almacen.compra_uca_ids.filtered(
                lambda x: (not x.solicitud_line_id and x.product_id.id == browse_id.product_id.id) or
                          (x.solicitud_line_id and x.solicitud_line_id.id == browse_id.id)
            )
            if uca_line:
                self.pool.get('grp.solicitud.compra').create(cr, uid, {
                    'product_id': browse_id.product_id.id,
                    'cantidad_solicitada': context.get('es_wizard',
                                                       False) and browse_id.cantidad_pedida or browse_id.cantidad_solicitada,
                    'linea_solicitud_recursos_id': browse_id.id,
                    'solicitante_id': browse_id.grp_id.solicitante_id and browse_id.grp_id.solicitante_id.id or uid,
                    'company_id': self.pool.get('res.company')._company_default_get(cr, uid, 'product.template',
                                                                                    context=context),
                    'precio_estimado': uca_line[0].price,
                    'description': browse_id.descripcion,
                    'inciso': browse_id.grp_id.inciso,
                    'u_e': browse_id.grp_id.u_e,
                    'origen': browse_id.grp_id.department_id.name,
                    'department_id': browse_id.grp_id.department_id.id,

                    'provider_id': uca_line[0].provider_id.id,
                    'number': uca_line[0].number
                })
        else:
            return super(grp_solicitud_compra_v8, self)._crear_solicitud_linea(cr, uid, browse_id, context=context)
        return True

    @api.multi
    @api.depends('linea_solicitud_recursos_id.grp_id')
    def _compute_solicitud_recursos_items(self):
        SolicitudRecurso = self.env['grp.compras.solicitud.recursos.almacen']
        for rec in self:
            solicitud_recurso = False
            if rec.linea_solicitud_recursos_id and rec.linea_solicitud_recursos_id.grp_id:
                solicitud_recurso = SolicitudRecurso.search([('sr_id', '=', rec.linea_solicitud_recursos_id.grp_id.id)],
                                                            limit=1)
            if solicitud_recurso:
                rec.number_uca = solicitud_recurso.number_uca
                rec.sentencia_ordenanza = solicitud_recurso.sentencia_ordenanza
            else:
                rec.number_uca = False
                rec.sentencia_ordenanza = False
