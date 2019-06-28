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
from openerp.exceptions import ValidationError

class grp_account_voucher(models.Model):
    _inherit= 'account.voucher'

    topay_amount = fields.Float('Total a pagar', compute = '_compute_topay_amount')
    apply_round = fields.Boolean('Ajuste por redondeo')
    comment = fields.Char(default=_('Ajuste por redondeo'))

    currency_id = fields.Many2one('res.currency', string=u'Moneda', compute='_get_journal_currency', store=True,
                                  required=True)

    @api.multi
    @api.depends('journal_id.currency', 'company_id.currency_id')
    def _get_journal_currency(self):
        for rec in self:
            rec.currency_id = rec.journal_id.currency and rec.journal_id.currency.id or rec.company_id.currency_id.id

    def get_topay_amount(self):
        self.ensure_one()
        debit = credit = 0
        for line in self.line_dr_ids:
            debit += line.amount
        for line in self.line_cr_ids:
            credit += line.amount
        currency_id = self.currency_id or self.company_id.currency_id
        if self.type == 'receipt':
            return currency_id.round(credit - debit)
        else:
            return currency_id.round(debit - credit)

    @api.depends('line_dr_ids.reconcile','line_dr_ids.amount','line_cr_ids.reconcile','line_cr_ids.amount')
    def _compute_topay_amount(self):
        for rec in self:
            rec.topay_amount = rec.get_topay_amount()

    @api.multi
    def action_topay_amount(self):
        for rec in self:
            rec.amount = round(self.get_topay_amount(), 0) if self.apply_round else self.get_topay_amount()
            if rec.writeoff_amount:
                company = rec.company_id or self.env.user.company_id
                currency_id = rec.journal_id.currency and rec.journal_id.currency.id or company.currency_id.id
                AjusteRedondeo = self.env['grp.ajuste.redondeo'].sudo()
                ajuste_red = AjusteRedondeo.search([('moneda','=',currency_id),('company_id','=',company.id)], limit=1)
                if ajuste_red and abs(rec.writeoff_amount) < ajuste_red.ajuste_redondeo:
                    vals = {'payment_option': 'with_writeoff'}
                    if (rec.type in ('payment','purchase') and \
                        ((rec.writeoff_amount>0 and company.expense_rounding_adjust_account_id) or \
                        (rec.writeoff_amount<0 and company.income_rounding_adjust_account_id))) or \
                       (rec.type in ('receipt','sale') and \
                        ((rec.writeoff_amount>0 and company.income_rounding_adjust_account_id) or \
                        (rec.writeoff_amount<0 and company.expense_rounding_adjust_account_id))):
                        vals['writeoff_acc_id'] = rec.writeoff_amount>0 and (rec.type in ('payment','purchase') and company.expense_rounding_adjust_account_id.id or company.income_rounding_adjust_account_id.id) \
                                                    or (rec.type in ('payment','purchase') and company.income_rounding_adjust_account_id.id or company.expense_rounding_adjust_account_id.id)
                        vals['ro_writeoff_fields'] = True
                    rec.write(vals)

    @api.onchange('writeoff_amount')
    def _onchange_writeoff_amount(self):
        if self.writeoff_amount:
            company = self.company_id or self.env.user.company_id
            currency_id = self.journal_id.currency and self.journal_id.currency.id or company.currency_id.id
            AjusteRedondeo = self.env['grp.ajuste.redondeo'].sudo()
            ajuste_red = AjusteRedondeo.search([('moneda','=',currency_id),('company_id','=',company.id)], limit=1)
            if ajuste_red and abs(self.writeoff_amount) < ajuste_red.ajuste_redondeo:
                self.payment_option = 'with_writeoff'
                if (self.type in ('payment','purchase') and \
                    ((self.writeoff_amount>0 and company.expense_rounding_adjust_account_id) or \
                    (self.writeoff_amount<0 and company.income_rounding_adjust_account_id))) or \
                   (self.type in ('receipt','sale') and \
                    ((self.writeoff_amount>0 and company.income_rounding_adjust_account_id) or \
                    (self.writeoff_amount<0 and company.expense_rounding_adjust_account_id))):
                    self.writeoff_acc_id = self.writeoff_amount>0 and (self.type in ('payment','purchase') and company.expense_rounding_adjust_account_id.id or company.income_rounding_adjust_account_id.id) \
                                            or (self.type in ('payment','purchase') and company.income_rounding_adjust_account_id.id or company.expense_rounding_adjust_account_id.id)
                    self.ro_writeoff_fields = True
            else:
                self.payment_option = 'without_writeoff'
                self.writeoff_acc_id = False
                self.ro_writeoff_fields = False



class grp_account_voucher_line(models.Model):
    _inherit= 'account.voucher.line'

    origin_voucher_id = fields.Many2one('account.voucher','Documento de pago de origen')

    @api.constrains('amount', 'amount_unreconciled')
    def check_amounts(self):
        if not self._context.get('opi',False) and not self._context.get('devolucion_viatico',False) and not self._context.get('purchase_receipt',False) and not self.voucher_id.type == u'sale' and self.amount_unreconciled < self.amount:
            raise ValidationError(u'El Importe de las líneas no debe ser mayor que el Saldo inicial')
