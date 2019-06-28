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

from openerp import api, fields, models

SUB_TIPO_SOLICITUD = [
    ('normal', 'Normal'),
    ('compra_uca', 'Compra por UCA'),
]

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    compra_uca_ids = fields.One2many('grp.compras.solicitud.uca', string='Compras UCA', compute='_get_uca_info')
    number_uca = fields.Char(u'Nro.Licitación UCA', compute='_get_uca_info')
    sub_tipo_solicitud = fields.Selection(SUB_TIPO_SOLICITUD, 'Sub-Tipo Solicitud', compute='_get_uca_info')

    @api.multi
    @api.depends('pedido_compra_id.number_uca', 'pedido_compra_id.compra_uca_ids', 'pedido_compra_id.sub_tipo_solicitud')
    def _get_uca_info(self):
        for rec in self:
            if rec.pedido_compra_id:
                rec.sub_tipo_solicitud = rec.pedido_compra_id.sub_tipo_solicitud
                rec.number_uca = rec.pedido_compra_id.number_uca
                rec.compra_uca_ids = rec.pedido_compra_id.compra_uca_ids
            else:
                rec.sub_tipo_solicitud = False
                rec.number_uca = False
                rec.compra_uca_ids = False

