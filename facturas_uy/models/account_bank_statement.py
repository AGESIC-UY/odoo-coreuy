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
from openerp.tools.translate import _
import time

import logging
_logger = logging.getLogger(__name__)

class grp_account_bank_statement(osv.osv):

    _inherit = "account.bank.statement"

    #001-modificacion de asientos-Inicio
    def _prepare_move_line_vals(self, cr, uid, st_line, move_id, debit, credit, currency_id = False,
                amount_currency= False, account_id = False, analytic_id = False,
                partner_id = False, context=None):
        """Prepare the dict of values to create the move line from a
           statement line. All non-mandatory args will replace the default computed one.
           This method may be overridden to implement custom move generation (making sure to
           call super() to establish a clean extension chain).

           :param browse_record st_line: account.bank.statement.line record to
                  create the move from.
           :param int/long move_id: ID of the account.move to link the move line
           :param float debit: debit amount of the move line
           :param float credit: credit amount of the move line
           :param int/long currency_id: ID of currency of the move line to create
           :param float amount_currency: amount of the debit/credit expressed in the currency_id
           :param int/long account_id: ID of the account to use in the move line if different
                  from the statement line account ID
           :param int/long analytic_id: ID of analytic account to put on the move line
           :param int/long partner_id: ID of the partner to put on the move line
           :return: dict of value to create() the account.move.line
        """
        # PCARBALLO Chequeo si las cuentas coinciden o no para saber que signo se le asigna al monto.
        # MODIFICACION PARA CASOS DE DECIMALES- echaviano 30/10
        if debit == 0.0 and credit == 0.0 and abs(amount_currency) == 0.0:
            amount_currency = st_line.amount > 0 and -1 * st_line.amount or abs(st_line.amount)

        acc_id = account_id or st_line.account_id.id
        cur_id = currency_id or st_line.statement_id.currency.id
        par_id = partner_id or (((st_line.partner_id) and st_line.partner_id.id) or False)

        #PCARBALLO
        return {
            'name': st_line.name,
            'date': st_line.date,
            'ref': st_line.ref,
            'move_id': move_id,
            'partner_id': par_id,
            'account_id': acc_id,
            'credit': credit,
            'debit': debit,
            'statement_id': st_line.statement_id.id,
            'journal_id': st_line.statement_id.journal_id.id,
            'period_id': st_line.statement_id.period_id.id,
            'currency_id': amount_currency and cur_id,
            'amount_currency': amount_currency,
            'analytic_account_id': analytic_id,
        }

    #MVARELA 30/09: se sobreescribe balance_check para controlar solo si el diario tiene marcada la opcion cash_control
    def balance_check(self, cr, uid, st_id, journal_type='bank', context=None):
        st = self.browse(cr, uid, st_id, context=context)
        if st.journal_id.cash_control:
            return super(grp_account_bank_statement, self).balance_check(cr, uid, st_id, journal_type, context=context)
        return True

    def _prepare_move(self, cr, uid, st_line, st_line_number, context=None):
        """Prepare the dict of values to create the move from a
           statement line. This method may be overridden to implement custom
           move generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record st_line: account.bank.statement.line record to
                  create the move from.
           :param char st_line_number: will be used as the name of the generated account move
           :return: dict of value to create() the account.move
        """
        period_id = st_line.statement_id.period_id.id
        period = self.pool.get('account.period').find(cr, uid, st_line.date, context=context)
        if period:
            period_id = period[0]
        return {
            'journal_id': st_line.statement_id.journal_id.id,
            'period_id': period_id,
            'date': st_line.date,
            'name': st_line_number,
            'ref': st_line.ref,
        }

grp_account_bank_statement()

class account_move_line(osv.osv):
    _inherit = "account.move.line"

    # este metodo no se si pasarlo, queda por las dudas
    def reconcile(self, cr, uid, ids, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False, context=None):
        if not writeoff_acc_id:
            linea = self.browse(cr, uid, ids[0], context=context)
            if linea.company_id:
                cuenta = linea.partner_id.property_account_payable.id
                if cuenta:
                    writeoff_acc_id = cuenta
        return super(account_move_line, self).reconcile(cr, uid, ids, type=type, writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id, context=context)

    _columns = {
        #002 - Agregando cambio para cuando hay diferencia monedas
        'exchange_line': fields.boolean('Exchange Line'),
    }

account_move_line()

class grp_account_bank_statement_line(osv.osv):

    _inherit = "account.bank.statement.line"

    _columns = {
        # 'date': fields.date('Date', required=True),
        'entry_date': fields.date(u'Fecha',required=True),
        'state': fields.related('statement_id', 'state', type='selection',
                                selection=[('draft', 'New'), ('open', 'Open'), ('confirm', 'Closed')],
                                string=u'Status', store=False),
    }

    _defaults = {
        # 'state': 'draft',
        'entry_date': lambda *a: time.strftime('%Y-%m-%d'),
        'date': lambda *a: time.strftime('%Y-%m-%d')

    }

    def onchange_date(self, cr, uid, ids, entry_date,context=None):
        res = {'value': {}}
        if entry_date:
            res['value'].update({'date': entry_date})

        return res



grp_account_bank_statement_line()
