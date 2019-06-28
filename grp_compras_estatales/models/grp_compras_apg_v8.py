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

# ================================================================
#       Autorización para gastar
# ================================================================

class grp_compras_apg(models.Model):
    _name = 'grp.compras.apg'
    _inherit = ['grp.compras.apg']

    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Unidad ejecutora responsable',
        required=True,
        default=lambda self: (self.env['res.users'].operating_unit_default_get(self.env.uid))
    )
    attachment_ids = fields.Many2many(compute='get_attachments_docs',
                                      comodel_name='ir.attachment',
                                      string=u'Documentos asociados')

    @api.multi
    @api.depends('pc_id')
    def get_attachments_docs(self):
        pool_po = self.env['purchase.order']
        pool_invoice = self.env['account.invoice']
        pool_voucher = self.env['account.voucher']
        pool_adj = self.env['grp.cotizaciones']
        for apg in self:
            domain = False
            solicitudes = []
            srs = []
            for linea in apg.pc_id.lineas_ids:
                if linea.solicitud_compra_id:
                    solicitudes.append(linea.solicitud_compra_id.id)
                    srs.append(linea.solicitud_compra_id.solicitud_recursos_id.id)
            po_ids = pool_po.suspend_security().search([('pedido_compra_id', '=', apg.pc_id.id), ('state', 'not in', ['cancel'])])
            inv_ids = pool_invoice.suspend_security().search([('orden_compra_id', 'in', po_ids.ids),
                                                    ('state', 'not in', ['cancel', 'cancel_siif', 'cancel_sice'])])
            av_ids = pool_voucher.suspend_security().search([('invoice_id', 'in', inv_ids.ids),('state', 'not in', ['cancel'])])
            adj_ids = pool_adj.suspend_security().search([('pedido_compra_id', '=', apg.pc_id.id), ('state', 'not in', ['cancelado'])])
            # if len(solicitudes):
            domain = ['|','|','|','|','|','|', '|', '&', ('res_id', '=', apg.id), ('res_model', '=', 'grp.compras.apg'),
                      '&', ('res_id', '=', apg.pc_id.id), ('res_model', '=', 'grp.pedido.compra'),
                      '&', ('res_id', 'in', solicitudes), ('res_model', '=', 'grp.solicitud.compra'),
                      '&', ('res_id', 'in', srs), ('res_model', '=', 'grp.compras.solicitud.recursos.almacen'),
                      '&', ('res_id', 'in', po_ids.ids), ('res_model', '=', 'purchase.order'),
                      '&', ('res_id', 'in', inv_ids.ids), ('res_model', '=', 'account.invoice'),
                      '&', ('res_id', 'in', av_ids.ids), ('res_model', '=', 'account.voucher'),
                      '&', ('res_id', 'in', adj_ids.ids), ('res_model', '=', 'grp.cotizaciones'),
                      ]

            if not domain:
                domain = [('res_id', '=', apg.id), ('res_model', '=', 'grp.compras.apg')]
            docs = self.env['ir.attachment'].search(domain)
            apg.attachment_ids = docs.ids

