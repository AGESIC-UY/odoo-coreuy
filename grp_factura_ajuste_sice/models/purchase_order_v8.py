# -*- coding: utf-8 -*-

from openerp import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _prepare_invoice_grp(self, order, line_ids):
        """Prepare the dict of values to create the new invoice for a
           purchase order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: purchase.order record to invoice
           :param list(int) line_ids: list of invoice line IDs that must be
                                      attached to the invoice
           :return: dict of value to create() the invoice
        """
        inv_data = super(PurchaseOrder, self)._prepare_invoice_grp(order, line_ids)

        # Si el purchase_order esta en estado done, se crea una factura de ajuste
        # que no se le pueda modificar el campo ajustar_facturas (readonly)
        # if order.state == 'done' or (order.state == 'confirmed' and sum(order.order_line.mapped('qty_pendiente')) == 0 and len(order.order_line.mapped('invoice_lines')) != len(order.order_line)):
        if order.state == 'done' or (order.state == 'confirmed' and order.order_line.get_total_qty_pendiente() == 0):
            inv_data.update({
                'ajustar_facturas': True,
                'ajustar_facturas_readonly': True
            })
        return inv_data

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    def get_total_qty_pendiente(self):
        qty_pendiente = 0
        for rec in self:
            qty_invoiced = sum(rec.invoice_lines.filtered(lambda x: x.invoice_id and x.invoice_id.state not in ['draft', 'cancel', 'cancel_sice', 'cancel_siif'] and x.product_id.id == rec.product_id.id).mapped('quantity'))
            qty_pendiente += rec.product_qty - qty_invoiced
        return qty_pendiente