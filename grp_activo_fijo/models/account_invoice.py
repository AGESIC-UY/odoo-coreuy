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

from openerp import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    nc_asset = fields.Boolean(string='NC de Activo Fijo')

    @api.multi
    def invoice_validate(self):
        res = super(account_invoice, self).invoice_validate()
        for record in self:
            if record.nc_asset and record.invoice_line.filtered(lambda x: x.product_es_activo_fijo == True):
                ir_model_data = self.env['ir.model.data']
                _model, group_id = ir_model_data.get_object_reference('grp_activo_fijo', 'grp_af_responsable_financiero')
                users = self.env['res.users'].search([('groups_id', 'in', group_id),('operating_unit_ids','in',record.operating_unit_id.id)])
                partner_ids = []
                number = record.number or ''
                supplier_invoice_number = record.factura_original and record.factura_original.supplier_invoice_number or''
                if users:
                    partner_ids = [user.partner_id.id for user in users]
                body = u"Se ha contabilizado una nota de crédito relacionada con un activo fijo. " \
                       u"El número de nota de crédito de GRP es %s y la factura asociada es %s." % (number, supplier_invoice_number)
                self.message_post(partner_ids=partner_ids,
                                  body=body,
                                  subtype='mail.mt_comment')
            # Se crean registros de Obras en curso si existe alguna para crear
            obras_curso_pool = self.env['grp.obras.curso.linea']
            for line in record.invoice_line:
                if line.obra_editable:
                    dictionary = {
                        'descripcion': line.name,
                        'producto_id': line.product_id.id,
                        'factura_id': record.id,
                        'factura_ref': record.supplier_invoice_number,
                        'obra_en_curso': line.obra.id,
                        'importe': line.monto_moneda_base,
                        'estado_factura': record.state,
                        'activado': False,
                        'no_activar': False,
                        'categoria_activo_id': line.asset_category_id.id,
                        'account_id': line.account_id.id,
                    }
                    create_id = obras_curso_pool.create(dictionary)
        return res

    @api.multi
    def action_cancel(self):
        res = super(account_invoice, self).action_cancel()
        for inv in self:
            if inv.doc_type in ['3en1_invoice','invoice'] or self._context.get('doc_type', False):
                for line in inv.invoice_line:
                    if line.asset_category_id and line.product_stockable and line.purchase_line_id:
                        # Actualizar el dato Nro. factura GRP
                        stock_moves = line.purchase_line_id.move_ids | line.purchase_line_id.move_ids.mapped('returned_move_ids')
                        stock_moves = stock_moves.filtered(lambda r: r.state != 'cancel')
                        pickings = stock_moves.mapped('picking_id')
                        if pickings:
                            domain = [('invoice_id','!=',False),
                                      ('product_id','=',line.product_id.id),
                                      ('origin_picking_id','in',pickings.ids),
                                     ]
                            assets = self.env['account.asset.asset'].sudo().search(domain, order='id desc', limit=line.quantity)
                            if assets:
                                assets.write({'invoice_id': False})
        return res
