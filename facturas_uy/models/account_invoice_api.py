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

from openerp import models, fields, api, _, exceptions
from openerp.exceptions import except_orm

_logger = logging.getLogger(__name__)


class account_invoice_ext_api(models.Model):
    _inherit = 'account.invoice'

    # TODO: GAP 247.2 Modificando este metodo para que coja la fecha de asiento y no la fecha de factura
    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_invoice_tax = self.env['account.invoice.tax']
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise except_orm(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise except_orm(_('No Invoice Lines!'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice

            company_currency = inv.company_id.currency_id
            # create the analytical lines, one move line per invoice line
            iml = inv._get_analytic_lines()
            # check if taxes are all computed
            compute_taxes = account_invoice_tax.compute(inv.with_context(lang=inv.partner_id.lang))
            inv.check_tax_lines(compute_taxes)

            # I disabled the check_total feature
            if self.env['res.users'].has_group('account.group_supplier_inv_check_total'):
                if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (
                    inv.currency_id.rounding / 2.0):
                    raise except_orm(_('Bad Total!'), _(
                        'Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise except_orm(_('Error!'), _(
                        "Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

            # one move line per tax line
            iml += account_invoice_tax.move_line_get(inv.id)

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = inv.number

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, ref, iml)

            name = inv.supplier_invoice_number or inv.name or '/'
            totlines = []
            if inv.payment_term:
                totlines = inv.with_context(ctx).payment_term.compute(total, date_invoice)[0]
            if totlines:
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'ref': ref
                })

            date = date_invoice

            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)

            line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            if journal.centralisation:
                raise except_orm(_('User Error!'),
                                 _(
                                     'You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            # 001 Cambios para cuando es cero
            line = self.modify_move_lines(line)
            # 001 - Fin cambios de contabilizacion

            line = inv.finalize_invoice_move_lines(line)
            move_date = inv.date_invoice
            if inv.entry_date:
                move_date = inv.entry_date
            move_vals = {
                'ref': inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal.id,
                'date': move_date,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            ctx['company_id'] = inv.company_id.id
            # period = inv.period_id
            # if not period:
            period = self.env['account.period'].with_context(ctx).find(move_date)[:1]
            if period:
                move_vals['period_id'] = period.id
                for i in line:
                    i[2]['period_id'] = period.id

            ctx['invoice'] = inv
            move = account_move.with_context(ctx).create(move_vals)
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'period_id': period.id,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
        self._log_event()
        return True

    # def modify_move_lines(self, cr, uid, move_lines, inv, context=None):
    def modify_move_lines(self, move_lines):
        mov_line = []
        for inv in self:
            account_id = inv.journal_id.default_credit_account_id and inv.journal_id.default_credit_account_id.id
            amount_currency = 0
            for elem in move_lines:
                if inv.type in ('out_refund', 'in_refund'):
                    if (not elem[2]['credit'] and not elem[2]['debit'] and inv.invoice_line[0].price_subtotal > 0):
                        if account_id == elem[2]['account_id']:
                            amount_currency = abs(elem[2]['amount_currency'])
                        else:
                            amount_currency = -abs(elem[2]['amount_currency'])
                        elem[2].update({'amount_currency': amount_currency})
                    elif (not elem[2]['credit'] and not elem[2]['debit'] and inv.invoice_line[0].price_subtotal < 0):
                        if account_id == elem[2]['account_id']:
                            amount_currency = -abs(elem[2]['amount_currency'])
                        else:
                            amount_currency = abs(elem[2]['amount_currency'])
                        elem[2].update({'amount_currency': amount_currency})
                elif inv.type in ('out_invoice', 'in_invoice'):
                    if (not elem[2]['credit'] and not elem[2]['debit']):
                        if account_id == elem[2]['account_id']:
                            amount_currency = -abs(elem[2]['amount_currency'])
                        else:
                            amount_currency = abs(elem[2]['amount_currency'])
                        elem[2].update({'amount_currency': amount_currency})
                mov_line.append((0, 0, elem[2]))
        return mov_line



class account_invoice_line(models.Model):
    _name = "account.invoice.line"
    _inherit = "account.invoice.line"
    product_id = fields.Many2one(required=False)
