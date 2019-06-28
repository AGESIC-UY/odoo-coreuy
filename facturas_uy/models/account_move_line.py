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
import time
from openerp import netsvc
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class account_move_reconcile(osv.osv):
    _name = "account.move.reconcile"
    _inherit = "account.move.reconcile"

    def reconcile_partial_check(self, cr, uid, ids, type='auto', context=None):
        total = 0.0
        currency_id = False
        for rec in self.browse(cr, uid, ids, context=context):
            for line in rec.line_partial_ids:
                currency_id = line.account_id.currency_id or line.company_id.currency_id
                if line.account_id.currency_id:
                    total += line.fixed_amount_currency_unround
                else:
                    total += (line.debit or 0.0) - (line.credit or 0.0)
        if currency_id and self.pool.get('res.currency').is_zero(cr, uid, currency_id, total):
            self.pool.get('account.move.line').write(cr, uid,
                map(lambda x: x.id, rec.line_partial_ids),
                {'reconcile_id': rec.id },
                context=context
            )
        return True

class tc_account_move_line(osv.osv):
    _inherit = "account.move.line"

    def reconcile_partial(self, cr, uid, ids, type='auto', context=None, writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        move_rec_obj = self.pool.get('account.move.reconcile')
        merges = []
        unmerge = []
        total = 0.0
        merges_rec = []
        company_list = []
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            if company_list and not line.company_id.id in company_list:
                raise osv.except_osv(_('Warning!'), _('To reconcile the entries company should be the same for all entries.'))
            company_list.append(line.company_id.id)

        for line in self.browse(cr, uid, ids, context=context):
            if line.account_id.currency_id:
                currency_id = line.account_id.currency_id
            else:
                currency_id = line.company_id.currency_id
            if line.reconcile_id:
                raise osv.except_osv(_('Warning'), _("Journal Item '%s' (id: %s), Move '%s' is already reconciled!") % (line.name, line.id, line.move_id.name))
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    if line2.state != 'valid':
                        raise osv.except_osv(_('Warning'), _("Journal Item '%s' (id: %s) cannot be used in a reconciliation as it is not balanced!") % (line2.name, line2.id))
                    if not line2.reconcile_id:
                        if line2.id not in merges:
                            merges.append(line2.id)
                        if line2.account_id.currency_id:
                            total += line2.fixed_amount_currency_unround
                        else:
                            total += (line2.debit or 0.0) - (line2.credit or 0.0)
                merges_rec.append(line.reconcile_partial_id.id)
            else:
                unmerge.append(line.id)
                if line.account_id.currency_id:
                    total += line.fixed_amount_currency_unround
                else:
                    total += (line.debit or 0.0) - (line.credit or 0.0)
        if self.pool.get('res.currency').is_zero(cr, uid, currency_id, total):
            res = self.reconcile(cr, uid, merges+unmerge, context=context, writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
            return res
        # marking the lines as reconciled does not change their validity, so there is no need
        # to revalidate their moves completely.
        reconcile_context = dict(context, novalidate=True)
        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_partial_ids': map(lambda x: (4,x,False), merges+unmerge)
        }, context=reconcile_context)
        move_rec_obj.reconcile_partial_check(cr, uid, [r_id] + merges_rec, context=reconcile_context)
        return r_id

    def reconcile(self, cr, uid, ids, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False, context=None):
        account_obj = self.pool.get('account.account')
        move_obj = self.pool.get('account.move')
        move_rec_obj = self.pool.get('account.move.reconcile')
        partner_obj = self.pool.get('res.partner')
        currency_obj = self.pool.get('res.currency')
        lines = self.browse(cr, uid, ids, context=context)
        unrec_lines = filter(lambda x: not x['reconcile_id'], lines)
        credit = debit = 0.0
        currency = 0.0
        account_id = False
        partner_id = False
        if context is None:
            context = {}
        company_list = []
        for line in self.browse(cr, uid, ids, context=context):
            if company_list and not line.company_id.id in company_list:
                raise osv.except_osv(_('Warning!'), _('To reconcile the entries company should be the same for all entries.'))
            company_list.append(line.company_id.id)
        for line in unrec_lines:
            if line.state <> 'valid':
                raise osv.except_osv(_('Error!'),
                        _('Entry "%s" is not valid !') % line.name)
            credit += line['credit']
            debit += line['debit']
            currency += line['amount_currency'] or 0.0
            account_id = line['account_id']['id']
            partner_id = (line['partner_id'] and line['partner_id']['id']) or False
        writeoff = debit - credit

        # Ifdate_p in context => take this date
        if context.has_key('date_p') and context['date_p']:
            date=context['date_p']
        else:
            date = time.strftime('%Y-%m-%d')

        cr.execute('SELECT account_id, reconcile_id '\
                   'FROM account_move_line '\
                   'WHERE id IN %s '\
                   'GROUP BY account_id,reconcile_id',
                   (tuple(ids), ))
        r = cr.fetchall()
        #TODO: move this check to a constraint in the account_move_reconcile object
        if len(r) != 1:
            raise osv.except_osv(_('Error'), _('Entries are not of the same account or already reconciled ! '))
        if not unrec_lines:
            raise osv.except_osv(_('Error!'), _('Entry is already reconciled.'))
        account = account_obj.browse(cr, uid, account_id, context=context)
        if not account.reconcile:
            raise osv.except_osv(_('Error'), _('The account is not defined to be reconciled !'))
        if r[0][1] != None:
            raise osv.except_osv(_('Error!'), _('Some entries are already reconciled.'))

        # currency_company_is_zero = currency_obj.is_zero(cr, uid, account.company_id.currency_id, writeoff)
        # currency_is_zero = currency_obj.is_zero(cr, uid, account.currency_id, currency)

        if (not currency_obj.is_zero(cr, uid, account.company_id.currency_id, writeoff)) or \
           (account.currency_id and (not currency_obj.is_zero(cr, uid, account.currency_id, currency))):
            ## NOTE: By irabaza
            ## Si voucher.ro_writeoff_fields es True la cuenta es para ajuste por redondeo, no para diferencia de cambio
            if writeoff_acc_id and 'voucher' in context and context['voucher'].ro_writeoff_fields:
                writeoff_acc_id = False

            if not writeoff_acc_id:
                # writeoff_acc_id = 52377
                if 'write_off_account_id' in context and context.get('write_off_account_id',False):
                    writeoff_acc_id = context.get('write_off_account_id',False)
                    writeoff_journal_id = writeoff_journal_id or context.get('writeoff_journal_id',False)
                    writeoff_period_id = writeoff_period_id or context.get('writeoff_period_id',False)
                else:
                    # writeoff_acc_id = 166  #Salta el error cuando necesita la cuenta para el desajuste
                    # tomar 'writeoff_acc_id' de la cuenta 'Diferencia de cambio ganada / perdida' configuradas en la compañía
                    if writeoff > 0:
                        writeoff_acc_id = account.company_id.expense_currency_exchange_account_id.id
                    else:
                        writeoff_acc_id = account.company_id.income_currency_exchange_account_id.id
            if not writeoff_acc_id:
                # raise osv.except_osv(_('Warning!'), _('ERROR WRITE OFF ACCOUNT move_line_ext in line 111 - You have to provide an account for the write off/exchange difference entry.'))
                raise osv.except_osv(_('Warning!'), _('You have to provide an account for the write off/exchange difference entry.'))
            if writeoff > 0:
                debit = writeoff
                credit = 0.0
                self_credit = writeoff
                self_debit = 0.0
            else:
                debit = 0.0
                credit = -writeoff
                self_credit = 0.0
                self_debit = -writeoff
            # If comment exist in context, take it
            if 'comment' in context and context['comment']:
                libelle = context['comment']
            else:
                libelle = _('Write-Off')

            cur_obj = self.pool.get('res.currency')
            cur_id = False
            amount_currency_writeoff = 0.0
            if context.get('company_currency_id',False) != context.get('currency_id',False):
                cur_id = context.get('currency_id',False)
                for line in unrec_lines:
                    if line.currency_id and line.currency_id.id == context.get('currency_id',False):
                        amount_currency_writeoff += line.amount_currency
                    else:
                        tmp_amount = cur_obj.compute(cr, uid, line.account_id.company_id.currency_id.id, context.get('currency_id',False), abs(line.debit-line.credit), context={'date': line.date})
                        amount_currency_writeoff += (line.debit > 0) and tmp_amount or -tmp_amount

            writeoff_lines = [
                (0, 0, {
                    'name': libelle,
                    'debit': self_debit,
                    'credit': self_credit,
                    'account_id': account_id,
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and -1 * amount_currency_writeoff or (account.currency_id.id and -1 * currency or 0.0)
                }),
                (0, 0, {
                    'name': libelle,
                    'debit': debit,
                    'credit': credit,
                    'account_id': writeoff_acc_id,
                    'analytic_account_id': context.get('analytic_id', False),
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and amount_currency_writeoff or (account.currency_id.id and currency or 0.0)
                })
            ]

            writeoff_move_id = move_obj.create(cr, uid, {
                'period_id': writeoff_period_id,
                'journal_id': writeoff_journal_id,
                'date':date,
                'desajuste': True, # cambio, chaviano 26/08
                # 'ref': libelle == 'Write-Off' and 'Write-Off' or False, # cambio, chaviano 26/08
                'state': 'draft',
                'line_id': writeoff_lines
            }, context=context)

            writeoff_line_ids = self.search(cr, uid, [('move_id', '=', writeoff_move_id), ('account_id', '=', account_id)])
            if account_id == writeoff_acc_id:
                writeoff_line_ids = [writeoff_line_ids[1]]
            ids += writeoff_line_ids

        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_id': map(lambda x: (4, x, False), ids),
            'line_partial_ids': map(lambda x: (3, x, False), ids)
        }, context=context)
        wf_service = netsvc.LocalService("workflow")
        # the id of the move.reconcile is written in the move.line (self) by the create method above
        # because of the way the line_id are defined: (4, x, False)
        for id in ids:
            wf_service.trg_trigger(uid, 'account.move.line', id, cr)

        if lines and lines[0]:
            partner_id = lines[0].partner_id and lines[0].partner_id.id or False
            if partner_id and not partner_obj.has_something_to_reconcile(cr, uid, partner_id, context=context):
                partner_obj.mark_as_reconciled(cr, uid, [partner_id], context=context)
        return r_id

    def _amount_residual(self, cr, uid, ids, field_names, args, context=None):
        """
           This function returns the residual amount on a receivable or payable account.move.line.
           By default, it returns an amount in the currency of this journal entry (maybe different
           of the company currency), but if you pass 'residual_in_company_currency' = True in the
           context then the returned amount will be in company currency.
        """
        # RAGU todos los comportamientos _unround
        # RAGU al usar redondeos se pierde saldo en pagos parciales y multicurrency. Corregido.
        res = {}
        if context is None:
            context = {}
        cur_obj = self.pool.get('res.currency')
        for move_line in self.browse(cr, uid, ids, context=context):
            res[move_line.id] = {
                'amount_residual': 0.0,
                'amount_residual_currency': 0.0,
            }

            if move_line.reconcile_id:
                continue
            if not move_line.account_id.type in ('payable', 'receivable'):
                #this function does not suport to be used on move lines not related to payable or receivable accounts
                continue

            if move_line.currency_id:
                move_line_total = move_line.amount_currency
                move_line_total_unround = move_line.fixed_amount_currency_unround or move_line.amount_currency_unround
                sign = move_line.amount_currency < 0 and -1 or 1
            else:
                move_line_total = move_line.debit - move_line.credit
                move_line_total_unround = move_line.debit - move_line.credit
                sign = (move_line.debit - move_line.credit) < 0 and -1 or 1

            context_unreconciled = context.copy()
            if move_line.currency_id and move_line.currency_id.id != move_line.company_id.currency_id.id:
                line_total_in_company_currency = cur_obj.compute(cr, uid, move_line.currency_id.id, move_line.company_id.currency_id.id, move_line.amount_currency, round=False, context=context_unreconciled)
            else:
                line_total_in_company_currency =  move_line.debit - move_line.credit

            if move_line.reconcile_partial_id:
                for payment_line in move_line.reconcile_partial_id.line_partial_ids:
                    if payment_line.id == move_line.id:
                        continue
                    if payment_line.currency_id and move_line.currency_id and payment_line.currency_id.id == move_line.currency_id.id:
                            move_line_total += payment_line.amount_currency
                            move_line_total_unround += payment_line.fixed_amount_currency_unround or payment_line.amount_currency_unround
                    else:
                        if move_line.currency_id:
                            context_unreconciled.update({'date': payment_line.date})
                            amount_in_foreign_currency = cur_obj.compute(cr, uid, move_line.company_id.currency_id.id, move_line.currency_id.id, (payment_line.debit - payment_line.credit), round=False, context=context_unreconciled)
                            move_line_total += amount_in_foreign_currency
                            move_line_total_unround += amount_in_foreign_currency
                        else:
                            move_line_total += (payment_line.debit - payment_line.credit)
                            move_line_total_unround += (payment_line.debit - payment_line.credit)
                    if payment_line.currency_id and payment_line.currency_id.id != payment_line.company_id.currency_id.id:
                        line_total_in_company_currency += cur_obj.compute(cr, uid, payment_line.currency_id.id, payment_line.company_id.currency_id.id,
                                        payment_line.fixed_amount_currency_unround or payment_line.amount_currency_unround, round=False, context=context_unreconciled)
                    else:
                        line_total_in_company_currency += (payment_line.debit - payment_line.credit)

            result = move_line_total
            result_unround = move_line_total_unround

            # echaviano, cambios en residual
            # RAGU ajustes a residual para soportar pagos parciales sin perder por redondeo
            # residual_currency = sign * (move_line.currency_id and self.pool.get('res.currency').round(cr, uid, move_line.currency_id, result) or result)
            residual_currency_unround = sign * result_unround

            # OJO: REVISAR
            residual = sign * line_total_in_company_currency
            if 'type' in context and context.get('type',False) and 'invoice_id' in context and context.get('invoice_id',False):
                # residual = residual_currency and cur_obj.compute(cr, uid, move_line.currency_id.id, move_line.company_id.currency_id.id, residual_currency, round=False, context=context_unreconciled) or line_total_in_company_currency
                residual = residual_currency_unround and cur_obj.compute(cr, uid, move_line.currency_id.id, move_line.company_id.currency_id.id, residual_currency_unround, round=False, context=context_unreconciled) or line_total_in_company_currency

            res[move_line.id]['amount_residual_currency_unround'] =  sign * result_unround
            res[move_line.id]['amount_residual_currency'] =  sign * (move_line.currency_id and self.pool.get('res.currency').round(cr, uid, move_line.currency_id, result) or result)
            res[move_line.id]['amount_residual'] = residual
        return res


    _columns = {
        'amount_residual_currency_unround': fields.function(_amount_residual, string='Residual Amount in Currency', multi="residual", help="The residual amount on a receivable or payable of a journal entry expressed in its currency (maybe different of the company currency)."),
        'amount_residual_currency': fields.function(_amount_residual, string='Residual Amount in Currency', multi="residual", help="The residual amount on a receivable or payable of a journal entry expressed in its currency (maybe different of the company currency)."),
        'amount_residual': fields.function(_amount_residual, string='Residual Amount', multi="residual", help="The residual amount on a receivable or payable of a journal entry expressed in the company currency."),
    }

tc_account_move_line()
