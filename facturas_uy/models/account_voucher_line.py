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
import logging
_logger = logging.getLogger(__name__)


class account_voucher_line_ext(osv.osv):
    _inherit = 'account.voucher.line'

    # If the payment is in the same currency than the invoice, we keep the same amount
    # Otherwise, we compute from invoice currency to payment currency
    def _compute_balance(self, cr, uid, ids, name, args, context=None):
        currency_pool = self.pool.get('res.currency')
        rs_data = {}
        for line in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            ctx.update({'date': line.voucher_id.date})
            voucher_rate = self.pool.get('res.currency').read(cr, uid, line.voucher_id.currency_id.id, ['rate'], context=ctx)['rate']
            ctx.update({
                'voucher_special_currency': line.voucher_id.payment_rate_currency_id and line.voucher_id.payment_rate_currency_id.id or False,
                'voucher_special_currency_rate': line.voucher_id.payment_rate * voucher_rate})
            res = {}
            company_currency = line.voucher_id.journal_id.company_id.currency_id.id
            voucher_currency = line.voucher_id.currency_id and line.voucher_id.currency_id.id or company_currency

            # echaviano, moneda original, puede ser de factura relacionada o el move_line relacionado
            # invoice_currency = line.voucher_id.invoice_id and line.voucher_id.invoice_id.currency_id.id or False
            # original_currency = line.move_line_id.currency_id and line.move_line_id.currency_id.id or False

            move_line = line.move_line_id or False

            if not move_line:
                res['amount_original'] = 0.0
                res['amount_original_move_line'] = 0.0
                res['amount_unreconciled'] = 0.0
            elif move_line.currency_id and voucher_currency==move_line.currency_id.id:
                res['amount_original'] = abs(move_line.amount_currency)
                res['amount_original_move_line'] = abs(move_line.amount_currency)
                res['amount_unreconciled'] = abs(move_line.amount_residual_currency)
            else:
                # Metodo original
                # Cambio de forma de calculo de metodo
                if line.currency_id and move_line.amount_currency and move_line.currency_id and move_line.currency_id.id != company_currency:
                # if company_currency != voucher_currency:
                    res['amount_original'] = currency_pool.compute(cr, uid, move_line.currency_id.id, company_currency, abs(move_line.amount_currency) or 0.0, context=ctx)
                    res['amount_original_move_line'] = currency_pool.compute(cr, uid, company_currency, voucher_currency, move_line.credit or move_line.debit or 0.0, context=ctx)
                    # res['amount_unreconciled'] = currency_pool.compute(cr, uid, move_line.currency_id.id, company_currency, abs(move_line.amount_residual_currency), context=ctx)
                    # RAGU nuevo monto a reconciliar sin el uso de aproximaciones.
                    # res['amount_unreconciled'] = currency_pool.compute(cr, uid, move_line.currency_id.id, company_currency, abs(move_line.amount_residual_currency_unround), context=ctx)
                    res['amount_unreconciled'] = currency_pool.compute(cr, uid, move_line.currency_id.id, company_currency, abs(move_line.amount_residual_currency), context=ctx)
                else:
                    res['amount_original'] = currency_pool.compute(cr, uid, company_currency, voucher_currency, move_line.credit or move_line.debit or 0.0, context=ctx)
                    res['amount_original_move_line'] = currency_pool.compute(cr, uid, company_currency, voucher_currency, move_line.credit or move_line.debit or 0.0, context=ctx)
                    res['amount_unreconciled'] = currency_pool.compute(cr, uid, company_currency, voucher_currency, abs(move_line.amount_residual), context=ctx)
             # montos y restante, fin

            rs_data[line.id] = res
        return rs_data

    _columns = {
        'amount_original_move_line': fields.function(_compute_balance, multi='dc', type='float', string='Original', store=True, digits_compute=dp.get_precision('Account')),
        'amount_original': fields.function(_compute_balance, multi='dc', type='float', string='Original Amount', store=True, digits_compute=dp.get_precision('Account')),
        'amount_unreconciled': fields.function(_compute_balance, multi='dc', type='float', string='Open Balance', store=True, digits_compute=dp.get_precision('Account')),
    }
