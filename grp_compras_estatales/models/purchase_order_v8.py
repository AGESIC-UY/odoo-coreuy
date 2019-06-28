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

from openerp import models, fields, api, _, exceptions
import openerp.addons.decimal_precision as dp

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    location_id = fields.Many2one(required=False)
    picking_type_id = fields.Many2one(required=False)
    location_ids_related = fields.Many2many('stock.location', related='operating_unit_id.location_ids', readonly=True)

    is_picking_required = fields.Boolean(compute='_compute_picking_required',store=False)

    @api.one
    @api.depends('order_line.product_id')
    def _compute_picking_required(self):
        if not any(line.product_id.type in ('product','consu') for line in self.order_line):
            self.is_picking_required = False
        else:
            self.is_picking_required = True


    def _compute_facturas_borrador(self):
        for record in self:
            tiene_borrador = False
            for invoice in record.invoice_ids:
                if invoice.state == 'draft':
                    tiene_borrador = True
            record.tiene_factura_borrador = tiene_borrador

    tiene_factura_borrador = fields.Boolean(string=u"Tiene asociadas facturas en borrador?", compute='_compute_facturas_borrador', default=False)
    operating_unit_id = fields.Many2one(comodel_name='operating.unit', string='Unidad ejecutora responsable',
                                        related='pedido_compra_id.operating_unit_id', readonly=True, store=True)
    attachment_ids = fields.Many2many(compute='get_attachments_docs',
                                      comodel_name='ir.attachment',
                                      string=u'Documentos asociados')
    es_migracion = fields.Boolean(u'Es migración?', related='pedido_compra_id.es_migracion', readonly=True)

    @api.multi
    @api.depends('pedido_compra_id')
    def get_attachments_docs(self):
        pool_apg = self.env['grp.compras.apg']
        pool_invoice = self.env['account.invoice']
        pool_voucher = self.env['account.voucher']
        pool_adj = self.env['grp.cotizaciones']
        for oc in self:
            domain = False
            if oc.pedido_compra_id:
                if oc.pedido_compra_id.lineas_ids:
                    solicitudes = []
                    srs = []
                    for linea in oc.pedido_compra_id.lineas_ids:
                        if linea.solicitud_compra_id:
                            solicitudes.append(linea.solicitud_compra_id.id)
                            srs.append(linea.solicitud_compra_id.solicitud_recursos_id.id)
                    pc = oc.pedido_compra_id
                    apg_ids = pool_apg.suspend_security().search([('pc_id', '=', pc.id), ('state', 'not in', ['anulada'])])
                    inv_ids = pool_invoice.suspend_security().search([('orden_compra_id', '=', oc.id),
                                                            ('state', 'not in', ['cancel', 'cancel_siif', 'cancel_sice'])])
                    av_ids = pool_voucher.suspend_security().search([('invoice_id', 'in', inv_ids.ids),('state', 'not in', ['cancel'])])
                    adj_ids = pool_adj.suspend_security().search([('pedido_compra_id', '=', pc.id), ('state', 'not in', ['cancelado'])])
                    # if len(solicitudes):
                    domain = ['|','|','|','|','|','|','|', '&',('res_id','=',oc.id),('res_model','=','purchase.order'),
                      '&',('res_id','in',solicitudes),('res_model','=','grp.solicitud.compra'),
                      '&',('res_id','in',srs),('res_model','=','grp.compras.solicitud.recursos.almacen'),
                      '&', ('res_id','=',oc.pedido_compra_id.id),('res_model','=','grp.pedido.compra'),
                      '&', ('res_id', 'in', apg_ids.ids), ('res_model', '=', 'grp.compras.apg'),
                      '&', ('res_id', 'in', inv_ids.ids), ('res_model', '=', 'account.invoice'),
                      '&', ('res_id', 'in', av_ids.ids), ('res_model', '=', 'account.voucher'),
                      '&', ('res_id', 'in', adj_ids.ids), ('res_model', '=', 'grp.cotizaciones'),
                    ]

                if not domain:
                    domain = ['|', '&',('res_id','=',oc.id), ('res_model','=','purchase.order'),
                              '&', ('res_id','=',oc.pedido_compra_id.id), ('res_model','=','grp.pedido.compra')]
            if not domain:
                domain = [('res_id','=',oc.id), ('res_model','=','purchase.order')]
            docs = self.env['ir.attachment'].search(domain)
            oc.attachment_ids = docs.ids

    # RAGU chequeando cantidades pendientes antes de confirmar compra
    # TODO: C SPRING 13 GAP 451
    def _check_product_qty(self):
        for line in self.order_line:
            if line.cotizaciones_linea_id and line.product_qty > line.cotizaciones_linea_id.cantidad_pendiente_oc:
                raise exceptions.ValidationError(
                    u'No puede confirmar la orden de compra, la cantidad de la linea: %s, es mayor que la cantidad pendiente en OC de la linea adjudicada: %s' % (line.product_qty, line.cotizaciones_linea_id.cantidad_pendiente_oc))

    @api.one
    def _check_pc_state(self):
        if self.pedido_compra_id and self.pedido_compra_id.state in ['cancelado_sice', 'cancelado']:
            raise exceptions.ValidationError(
                    u'No puede confirmar la orden de compra. El pedido de compra asociado está cancelado.')

    # RAGU chequeando cantidades pendientes antes de confirmar compra
    @api.multi
    def wkf_confirm_order(self):
        self.ensure_one()
        self._check_pc_state()
        self._check_product_qty()
        super(PurchaseOrder, self).wkf_confirm_order()

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    precio_sin_iva = fields.Float('Precio sin IVA', digits_compute=(16,4), compute='_compute_precio_sin_iva')
    grp_sice_cod = fields.Integer(string=u'Código SICE', related='product_id.grp_sice_cod', readonly=True)
    cotizaciones_linea_id = fields.Many2one('grp.cotizaciones.lineas.aceptadas', string=u'Línea de adjudicación')

    @api.depends('price_subtotal', 'product_qty')
    def _compute_precio_sin_iva(self):
        for line in self:
            res = round(line.price_subtotal / line.product_qty, 4)
            line.precio_sin_iva = res

    @api.constrains('product_qty')
    def _check_quantities(self):
        for rec in self:
            if not rec.product_qty:
                raise exceptions.ValidationError(_(u'Debe ingresar una cantidad no nula.'))
