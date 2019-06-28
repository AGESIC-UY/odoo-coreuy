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

import logging

from openerp import models, api

_logger = logging.getLogger(__name__)


class GrpContratoProveedores(models.Model):
    _inherit = 'grp.contrato.proveedores'
    _description = "Alta de Contrato de Proveedores"

    # Deben impactar las facturas ajustadas
    @api.one
    @api.depends('afectaciones_ids')
    def _compute_total_obligado(self):
        invoice_obj = self.env['account.invoice']
        total_obligado = 0.0
        if self.afectaciones_ids:
            invoice = invoice_obj.search([('ajustar_facturas', '=', True),
                                          ('afectacion_id', 'in',
                                           self.afectaciones_ids.ids),
                                          ('doc_type', '=',
                                           'obligacion_invoice'),
                                          ('state', '=', 'open')])
            total_obligado = sum(map(lambda x: x.importe, invoice.mapped(lambda x: x.llpapg_ids)))
        self.total_obligado = total_obligado

    # Deben impactar las facturas ajustadas
    @api.one
    @api.depends('invoice_ids', 'invoice_line_ids')
    def _compute_total_factura(self):
        total_factura = 0.0
        if not self.contrato_general_id.exists():
            orden_linea_ids = self.orden_compra_ids.mapped(
                lambda x: x.order_line
            ).filtered(
                lambda x: x.cotizaciones_linea_id.id == self.nro_line_adj_id.id
            )
            for rec in self.invoice_ids.mapped(lambda x: x.invoice_line).filtered(
                    lambda x: x.orden_compra_linea_id.id in orden_linea_ids.ids and x.invoice_id.state in ['open', 'intervened','sice', 'prioritized', 'paid'] and x.invoice_id.ajustar_facturas):
                total_factura += rec.price_unit * rec.quantity
        elif self.invoice_line_ids:
            total_factura = sum([x.importe_imp_incl for x in self.invoice_line_ids.filtered(lambda x: x.invoice_id.state in ['open', 'intervened','sice', 'prioritized', 'paid'] and x.invoice_id.ajustar_facturas)])
        self.total_factura = total_factura

    # No deben impactar las facturas asociadas
    @api.one
    def _compute_cantidad_pendiente(self):
        for rec in self:
            if rec.contrato_general_id:
                purchase_order_ids = self.env["purchase.order"].search([('contrato_id','=',rec.contrato_general_id.id),
                                                                    ('partner_id','=',rec.nro_line_adj_id.proveedor_cot_id.id),
                                                                    ('currency_oc','=',rec.nro_line_adj_id.currency.id)])
                invoice_line_ids = self.env['account.invoice.line'].search([('orden_compra_linea_id.order_id','in',purchase_order_ids.ids),
                                                                            ('product_id.grp_sice_cod','=',rec.codigo_articulo),
                                                                            ('invoice_id.state', 'in',['open', 'sice','intervened', 'prioritized','forced', 'paid']),
                                                                            ('invoice_id.ajustar_facturas', '=', False)
                                                                            ])
            else:
                purchase_order_ids = self.env["purchase.order"].search([('contrato_id', '=', rec.id)])
                invoice_line_ids = self.env['account.invoice.line'].search(
                    [('orden_compra_linea_id.order_id', 'in', purchase_order_ids.ids),
                     ('invoice_id.state', 'in', ['open', 'sice','intervened', 'prioritized', 'forced', 'paid'])
                     ])
            total_facturado = sum(map(lambda x: x.quantity, invoice_line_ids))
            rec.cantidad_pendiente = rec.cantidad - total_facturado
