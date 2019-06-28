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
import openerp.addons.decimal_precision as dp


class grp_orden_compra_linea(osv.osv):
    _inherit = 'purchase.order.line'

    def _qty_compute(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for po_line in self.browse(cr, uid, ids, context=context):
            res[po_line.id] = {
                'qty_invoiced': 0.0,
                'qty_pendiente': 0.0,
            }

            qty_invoiced = 0.0
            qty_aj_invoiced = 0.0
            for line in po_line.invoice_lines:
                if line.invoice_id.state not in ['draft', 'cancel', 'cancel_sice',
                                                 'cancel_siif'] and line.product_id.id == po_line.product_id.id:
                    qty_invoiced += line.quantity
                if line.invoice_id.state not in ['draft', 'cancel', 'cancel_sice',
                                                 'cancel_siif'] and not line.invoice_id.ajustar_facturas and line.product_id.id == po_line.product_id.id:
                    qty_aj_invoiced += line.quantity

            res[po_line.id]['qty_invoiced'] = qty_invoiced
            res[po_line.id]['qty_pendiente'] = po_line.product_qty - qty_aj_invoiced

        return res

    _columns = {
        'qty_invoiced': fields.function(_qty_compute, multi='cantidades', string=u'Cantidad facturada', type='float',
                                        digits_compute=dp.get_precision('Account')),
        'qty_pendiente': fields.function(_qty_compute, multi='cantidades', string=u'Cantidad pendiente', type='float',
                                         digits_compute=dp.get_precision('Account')),
    }


grp_orden_compra_linea()

#
#
#
#
# class PurchaseOrderLine(models.Model):
#     _inherit = 'purchase.order.line'
#
#     @api.v7
#     def _qty_compute(self, cr, uid, ids, name, arg, context=None):
#         res = {}
#         for po_line in self.browse(cr, uid, ids, context=context):
#             res[po_line.id] = {
#                 'qty_invoiced': 0.0,
#                 'qty_pendiente': 0.0,
#             }
#
#             qty_invoiced = 0.0
#             qty_aj_invoiced = 0.0
#             for line in po_line.invoice_lines:
#                 if line.invoice_id.state not in ['draft', 'cancel', 'cancel_sice', 'cancel_siif'] and line.product_id.id == po_line.product_id.id:
#                     qty_invoiced += line.quantity
#                 if line.invoice_id.state not in ['draft', 'cancel', 'cancel_sice', 'cancel_siif'] and not line.invoice_id.ajustar_facturas and line.product_id.id == po_line.product_id.id:
#                     qty_aj_invoiced += line.quantity
#
#             res[po_line.id]['qty_invoiced'] = qty_invoiced
#             res[po_line.id]['qty_pendiente'] = po_line.product_qty - qty_aj_invoiced
#
#         return res
