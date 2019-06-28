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

from openerp import models, fields, api

# TODO Spring 8 GAP 230 M
class grp_account_invoice(models.Model):
    _inherit = 'account.invoice'

    sin_procedimiento_sice = fields.Boolean('Sin procedimiento SICE', compute='_compute_sin_procedimiento_sice')

    @api.depends('orden_compra_id')
    def _compute_sin_procedimiento_sice(self):
        for record in self:
            if record.orden_compra_id and record.orden_compra_id.pedido_compra_id and record.orden_compra_id.pedido_compra_id.tipo_compra.idTipoCompra == 'SP':
                record.sin_procedimiento_sice = True
            else:
                record.sin_procedimiento_sice = False
