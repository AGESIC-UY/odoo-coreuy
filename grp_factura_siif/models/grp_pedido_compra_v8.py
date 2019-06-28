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

from openerp import api, exceptions, fields, models
import time

class grpPedidoCompra(models.Model):
    _inherit = 'grp.pedido.compra'

    @api.model
    def _prepare_apg_values(self, pedido):
        res = super(grpPedidoCompra, self)._prepare_apg_values(pedido)

        fiscalyear_obj = self.env['account.fiscalyear']
        fecha_hoy = time.strftime('%Y-%m-%d')
        company_id = self.env.user.company_id
        inciso = company_id.inciso

        fiscal_year = fiscalyear_obj.search([('date_start', '<=', fecha_hoy),
                                                ('date_stop', '>=', fecha_hoy),
                                                ('company_id', '=', company_id.id)], limit=1)
        fiscal_year_id = fiscal_year and fiscal_year.id

        if fiscal_year_id:
            res.update({'fiscalyear_siif_id': fiscal_year_id})
            pres_inciso_obj = self.env['grp.estruc_pres.inciso']
            pres_inciso = pres_inciso_obj.search([('fiscal_year_id', '=', fiscal_year_id),('inciso','=',inciso)], limit=1)
            inciso_id = pres_inciso and pres_inciso.id

            if inciso_id:
                res.update({'inciso_siif_id': inciso_id})
                pres_ue_obj = self.env['grp.estruc_pres.ue']
                pres_ue = pres_ue_obj.search([('inciso_id', '=', inciso_id),('ue','=', pedido.operating_unit_id.unidad_ejecutora)], limit=1)
                pres_ue_id = pres_ue and pres_ue.id

                if pres_ue_id:
                    res.update({'ue_siif_id': pres_ue_id})

        return res
