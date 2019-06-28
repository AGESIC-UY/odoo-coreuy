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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class product_template_ext(osv.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    _columns = {
        'retencion_ok':fields.boolean(u'Retención'),
    }
    _defaults = {
        'retencion_ok' : False,
    }
product_template_ext()


class account_global_retention_line_ext(osv.osv):
    _inherit = "account.global.retention.line"

    _columns = {
        #Agregando producto a retencion. Producto de tipo retencion
        'product_id': fields.many2one('product.product', string='Product', domain=[('retencion_ok','=',True),('property_account_expense.type','=','other')], help=u"El producto asociado a la retención."),
    }

    def onchange_product_id(self, cr, uid, ids, product_id):
        context = {}
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            return {'value':{'account_id': product.property_account_expense and product.property_account_expense.id or False}}
        return {'value':{'account_id': False}}

account_global_retention_line_ext()