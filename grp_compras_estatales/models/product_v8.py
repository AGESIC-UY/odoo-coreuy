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

from openerp import fields, models, api

import logging
_logger = logging.getLogger(__name__)

class Product(models.Model):
    _inherit = 'product.template'
    
    @api.model
    def _get_products_v8(self):
        products = []
        for prodtmpl in self.browse(self._ids):
            products += [x.id for x in prodtmpl.product_variant_ids]
        return products
    
    @api.model
    def _get_act_window_dict_v8(self, name):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        res = mod_obj.xmlid_to_res_id(name, raise_if_not_found=True)
        result = act_obj.browse(res).read()[0]
        return result

    @api.multi
    def action_open_quants(self):
        # Buscando los almacenes donde el usuario sea responsable
        wh_ids = self.env['stock.warehouse'].search([('encargado_ids', 'in', [self.env.user.id])]).ids
        products = self._get_products_v8()
        result = self._get_act_window_dict_v8('stock.product_open_quants')
        result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "]),('warehouse_id', 'in', [" + ','.join(map(str, wh_ids)) + "])]"
        result['context'] = "{'search_default_warehouse_id_group': 1,'search_default_locationgroup': 1, 'search_default_internal_loc': 1}"
        return result
