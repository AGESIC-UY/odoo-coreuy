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

from openerp import models, fields, api, exceptions, _
from openerp import tools


class GrpPaidConsult(models.Model):
    _name = 'grp.paid.consult'
    _auto = False
    _description = 'Consulta factura/pago con distinta UE'

    voucher_id = fields.Many2one('account.voucher', string=u'Número de pago',
                                 domain="[('state', 'in', ['posted']),('journal_id.operating_unit_id', '!=', 'invoice_id.operating_unit_id')]",
                                 required=True)
    voucher_line_id = fields.Many2one('account.voucher.line', string='Linea asiento contable')
    date = fields.Date(string=u'Fecha', related='voucher_id.date')
    journal_id = fields.Many2one('account.journal', string=u'Diario')
    voucher_ue_id = fields.Many2one('operating.unit', string=u'UE del diario')
    invoice_id = fields.Many2one('account.invoice', string=u'Comprobante de pago')
    invoice_ue_id = fields.Many2one('operating.unit', string=u'UE del Comprobante')
    amount = fields.Float(string=u'Importe del pago', related='voucher_line_id.amount')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_paid_consult')
        cr.execute("""
            CREATE OR replace VIEW grp_paid_consult AS (
                SELECT
                    avl.id AS id,
                    av.id AS voucher_id,
                    avl.id AS voucher_line_id,
                    av.journal_id AS journal_id,
                    aj.operating_unit_id AS voucher_ue_id,
                    ai.id AS invoice_id,
                    ai.operating_unit_id AS invoice_ue_id
                    FROM account_voucher AS av
                    INNER JOIN  account_voucher_line avl ON avl.voucher_id = av.id
                    INNER JOIN account_move_line aml ON avl.move_line_id = aml.id
                    INNER JOIN account_move am ON aml.move_id = am.id
                    INNER JOIN  account_invoice ai ON ai.move_id = am.id
                    INNER JOIN account_journal aj ON av.journal_id = aj.id
                    WHERE av.state = 'posted' AND av."type" = 'payment'
                    AND aj.operating_unit_id <> ai.operating_unit_id AND avl.amount > 0
                    ORDER BY voucher_id
            )
        """)
