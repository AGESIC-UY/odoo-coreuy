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

from openerp import models, fields, api

_logger = logging.getLogger(__name__)

# TODO SPRING 5 GRP 50

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    amount_currency_unround = fields.Float('Amount Currency Unround', compute='_compute_amount_currency_unround')
    fixed_amount_currency_unround = fields.Float('GRP AMOUNT CURRENCY UNROUND', digits=(12, 6))

    @api.model
    def create(self, vals):
        company_currency_id = self.env.user.company_id.currency_id
        move_line_currency_id = self.env['res.currency'].search(
            [('id', '=', vals.get('currency_id', False) or company_currency_id.id)], limit=1)
        if vals.get('date'):
            _date = vals['date']
        elif vals.get('move_id'):
            _date = self.env['account.move'].search([('id','=',vals['move_id'])], limit=1).date
        else:
            _date = fields.Date.today()
        vals['fixed_amount_currency_unround'] = company_currency_id.with_context({'date': _date}).compute(vals.get('debit',0.0) - vals.get('credit',0.0),move_line_currency_id,round=False)
        res = super(AccountMoveLine, self).create(vals)
        return res

    @api.multi
    @api.depends('date','currency_id','debit','credit')
    def _compute_amount_currency_unround(self):
        company_currency_id = self.env.user.company_id.currency_id
        for rec in self:
            rec.amount_currency_unround = company_currency_id.with_context({'date': rec.date}).compute(rec.debit-rec.credit, rec.currency_id or company_currency_id, round=False)