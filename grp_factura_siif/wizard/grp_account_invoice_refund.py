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

from openerp import models, api, fields

_logger = logging.getLogger(__name__)


# TODO: R SPRING 9 GAP 65
class grpAccountInvoiceRefund(models.TransientModel):
    _name = "account.invoice.refund"
    _inherit = "account.invoice.refund"

    tipo_nota_credito = fields.Selection([('A', u'A - Aumento'), ('R', u'R - Reducción'), ('D', u'D - Devolución al crédito')], 'Tipo')

    @api.multi
    def invoice_refund(self):
        to_return = super(grpAccountInvoiceRefund, self).invoice_refund(context=self._context)
        invoice_refund_id = to_return['domain'][1][2][0]
        origin_invoice_id = self.env['account.invoice'].browse(self._context['active_id'])
        origin_invoice_id.llpapg_ids.copy({'invoice_id': invoice_refund_id})
        # origin_invoice_id.ret_summary_line.copy({'invoice_id': invoice_refund_id})
        # origin_invoice_id.invoice_ret_line_ids.copy({'invoice_id': invoice_refund_id})
        # origin_invoice_id.invoice_ret_irpf_lines.copy({'invoice_id': invoice_refund_id})
        origin_invoice_id.invoice_ret_global_line_ids.copy({'invoice_id': invoice_refund_id})
        values = {
            'inciso_siif_id': origin_invoice_id.inciso_siif_id.id,
            'ue_siif_id': origin_invoice_id.ue_siif_id.id,
            'beneficiario_siif_id': origin_invoice_id.beneficiario_siif_id.id,
            'rupe_cuenta_bancaria_id': origin_invoice_id.rupe_cuenta_bancaria_id.id,
            'siif_tipo_ejecucion': origin_invoice_id.siif_tipo_ejecucion.id,
            'siif_concepto_gasto': origin_invoice_id.siif_concepto_gasto.id,
            'siif_financiamiento': origin_invoice_id.siif_financiamiento.id,
            'siif_codigo_sir': origin_invoice_id.siif_codigo_sir.id,
            'siif_nro_fondo_rot': origin_invoice_id.siif_nro_fondo_rot.id,
            'siif_tipo_documento': origin_invoice_id.siif_tipo_documento.id,
            'fiscalyear_siif_id': origin_invoice_id.fiscalyear_siif_id.id,
            'siif_descripcion': origin_invoice_id.siif_descripcion,
            'fecha_tipo_cambio': origin_invoice_id.fecha_tipo_cambio,
            'res_partner_bank_id': origin_invoice_id.res_partner_bank_id.id,
            'date_due': origin_invoice_id.date_due,
            # 'tipo_nota_credito': self._context.get('tipo_nota_credito', False),
            'tipo_nota_credito': self.tipo_nota_credito,
            'doc_type': origin_invoice_id.doc_type,
            'operating_unit_id': origin_invoice_id.operating_unit_id.id,
            'tc_presupuesto': origin_invoice_id.tc_presupuesto
            # 'ajuste_obligacion': True if origin_invoice_id.tipo_ejecucion_codigo_rel != 'P' else False,
        }
        if self.tipo_nota_credito:
            values.update({'doc_type': 'ajuste_invoice', 'entry_date': origin_invoice_id.entry_date})
            if self.tipo_nota_credito == 'A':
                values.update({'type': origin_invoice_id.type})

        self.env['account.invoice'].browse(invoice_refund_id).write(values)

        #facturas de fondo rotatorio
        if origin_invoice_id.tipo_ejecucion_codigo_rel == 'P':
            res = self.env['ir.model.data'].get_object_reference('account', 'invoice_supplier_form')
            return {
                'display_name': u'Nota de Crédito de FR',
                'name': u'Nota de Crédito de FR',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_id': [res and res[1] or False],
                'view_mode': 'form',
                'res_model': 'account.invoice',
                'res_id': invoice_refund_id,
                'views': [(res[1], 'form')],
            }
        #facturas con tipo de ejecucion != P
        elif origin_invoice_id.tipo_ejecucion_codigo_rel:
            res = self.env['ir.model.data'].get_object_reference('grp_factura_siif', 'view_account_form_credit_note')
            return {
                    'display_name': u'Ajuste de Obligación',
                    'name': u'Ajuste de Obligación',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_id': [res and res[1] or False],
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'res_id': invoice_refund_id,
                    'views': [(res[1], 'form')],
                }
        #otras facturas
        else:
            return to_return

    @api.onchange('tipo_nota_credito')
    def onchange_tipo_nota_credito(self):
        if self.tipo_nota_credito and self.tipo_nota_credito == 'A':
            self.journal_id = False