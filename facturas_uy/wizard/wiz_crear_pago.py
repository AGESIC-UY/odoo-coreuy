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

from openerp import netsvc

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import time, datetime
from openerp import SUPERUSER_ID

class crear_pago_wiz(osv.osv_memory):
    _name = 'wiz_crear_pago'
    _description = 'Crear pago factura'

    def _get_aux_account_id(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        account_id = company.income_currency_exchange_account_id and company.income_currency_exchange_account_id.id or company.expense_currency_exchange_account_id and company.expense_currency_exchange_account_id.id
        if not account_id:
            raise osv.except_osv(_('Insufficient Configuration!'),_("You should configure the 'The Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        return account_id

    _columns = {
        'date': fields.date(u"Fecha"),
        'journal_id':fields.many2one('account.journal', 'Journal', required=True),
        'amount': fields.float('Total', digits_compute=dp.get_precision('Account'), required=True),
        'partner_id':fields.many2one('res.partner', 'Partner', change_default=1),
    }

    _defaults = {
        'date': lambda *a:time.strftime('%Y-%m-%d'),
        # 'writeoff_acc_aux_id': _get_aux_account_id,
    }

    def button_wzrd_crear_pago(self, cr, uid, ids, context = None):
        if context is None:
            context = {}
        invoice_obj = self.pool.get('account.invoice')
        wiz = self.browse(cr,uid,ids,context=context)[0]
        active_ids = context.get('active_ids',[])
        invoice_obj.automatic_pay_invoice_aux(cr, uid, active_ids, wiz.journal_id.id, wiz.amount or 0.0, wiz.date, context=context)
        return {'type': 'ir.actions.act_window_close'}

crear_pago_wiz()