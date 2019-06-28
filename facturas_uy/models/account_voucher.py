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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import float_compare, float_round
from openerp import SUPERUSER_ID
from openerp import netsvc
from openerp import SUPERUSER_ID, netsvc, api
import datetime
import time

import logging

_logger = logging.getLogger(__name__)

class res_currency(osv.osv):
    _inherit = "res.currency"

    def _get_current_rate(self, cr, uid, ids, raise_on_no_rate=True, context=None):
        context = dict(context or {})
        res = super(res_currency, self)._get_current_rate(cr, uid, ids, raise_on_no_rate, context=context)
        # irabaza => NOTE: Para monedas en que la Tasa de Cambio es muy alta/baja (Ej: UYU - UR) se necesita una
        #   mayor precisión decimal en ´´payment_rate´´ de 'acoount.voucher': (12,15)
        #   Si se redefine el campo estableciando la nueva precisión desimal y se redefine el fields_get
        #   para seguir mostrando solo 6 lugares decimales en la vista,
        #   el onchange devuelve el valor con precisión decimal correcta pero el widget visual
        #   envía el valor con 6 lugares decimales.
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        if context.get('voucher_special_currency_rate') and float_round(context['voucher_special_currency_rate'], precision_digits=prec+1) == 1.0:
            context.update({ 'voucher_special_currency_rate': 1.0 })
        if context.get('voucher_special_currency') in ids and context.get('voucher_special_currency_rate'):
            res[context.get('voucher_special_currency')] = context.get('voucher_special_currency_rate')
        return res

res_currency()

# PCARBALLO nueva clase heredada de account_voucher
class grp_facturas_account_voucher(osv.osv):
    _inherit = 'account.voucher'

    def _get_writeoff_amount_aux(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        currency_obj = self.pool.get('res.currency')
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            # sign = voucher.type == 'payment' and -1 or 1
            # sign_inv = voucher.invoice_id.type in ('out_invoice','in_refund') and -1 or 1
            # invoice_amount = voucher.invoice_id and voucher.invoice_id.amount_total or 0.0
            invoice_amount = voucher.invoice_id and voucher.invoice_id.residual or 0.0
            company_currency = self.pool.get('res.company').browse(cr, uid, voucher.company_id.id,
                                                                   context=context).currency_id

            journal_currency = voucher.journal_id.currency and voucher.journal_id.currency.id or company_currency.id
            amount_inv_in_company_currency = 0.0
            inv_currency = voucher.invoice_id and voucher.invoice_id.currency_id.id or False
            if journal_currency != inv_currency and voucher.invoice_id:
                ctx = dict(context, account_period_prefer_normal=True)
                ctx.update({'date': voucher.invoice_id.date_invoice})
                amount_inv_in_company_currency = self.pool.get('res.currency').compute(cr, uid,
                                                                                       voucher.invoice_id.currency_id.id,
                                                                                       journal_currency, invoice_amount,
                                                                                       True, context=ctx)
            else:
                amount_inv_in_company_currency = invoice_amount

            currency = voucher.currency_id or voucher.company_id.currency_id
            res[voucher.id] = amount_inv_in_company_currency != 0 and currency_obj.round(cr, uid, currency,
                                                                                         voucher.amount - amount_inv_in_company_currency) or 0.0
        return res

    _columns = {
        'invoice_id': fields.many2one('account.invoice', u'Factura relacionada'),
        'down_tc': fields.boolean(string=u'Bajada del tc', help=u'Bajada del tipo de cambio'),
        # verificar si bajo el tipo de cambio
        'up_tc': fields.boolean(string=u'Subida del tc', help=u'Subida del tipo de cambio'),
        # verificar si subio el tipo de cambio 006
        # Si cambio el TC y pago mayor o igual a total
        'writeoff_amount_aux': fields.function(_get_writeoff_amount_aux, string=u'Difference Amount Aux',
                                               type='float', readonly=True),
        # monto restante del pago segun diferencia de cambio
        'writeoff_acc_aux_id': fields.many2one('account.account', string=u'Auxiliary Account', readonly=True,
                                               states={'draft': [('readonly', False)]}),
        # TODO GAP 247 Spring 4: Agregando la fecha de asiento
        'entry_date': fields.date(u'Fecha asiento', readonly=True, select=True, states={'draft': [('readonly', False)]},
                                  help=u"Fecha efectiva para entradas contables.", copy=False),
        'ro_writeoff_fields': fields.boolean(string='Campos WriteOff Solo-Lectura', selectable=False, searchable=False),
    }

    _defaults = {
        'entry_date': datetime.date.today().strftime('%Y-%m-%d'),
        'journal_id': False
    }

    def onchange_date(self, cr, uid, ids, date, currency_id, payment_rate_currency_id, amount, company_id,
                      context=None):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        if context is None:
            context = {}
        res = {'value': {}}
        # set the period of the voucher
        period_pool = self.pool.get('account.period')
        currency_obj = self.pool.get('res.currency')
        ctx = context.copy()
        ctx.update({'company_id': company_id, 'account_period_prefer_normal': True})
        voucher_currency_id = currency_id or self.pool.get('res.company').browse(cr, uid, company_id,
                                                                                 context=ctx).currency_id.id
        pids = period_pool.find(cr, uid, date, context=ctx)
        if pids:
            res['value'].update({'period_id': pids[0]})
        if payment_rate_currency_id:
            ctx.update({'date': date})
            payment_rate = 1.0
            if payment_rate_currency_id != currency_id:
                tmp = currency_obj.browse(cr, uid, payment_rate_currency_id, context=ctx).rate
                payment_rate = tmp / currency_obj.browse(cr, uid, voucher_currency_id, context=ctx).rate
            vals = self.onchange_payment_rate_currency(cr, uid, ids, voucher_currency_id, payment_rate,
                                                       payment_rate_currency_id, date, amount, company_id,
                                                       context=context)
            vals['value'].update({'payment_rate': payment_rate})
            for key in vals.keys():
                res[key].update(vals[key])
        res['value'].update({'entry_date': date})
        return res

    def _get_aux_account_id(self, cr, uid, ids, down_tc=False, context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        # bajada del TC
        if down_tc:
            account_id = company.income_currency_exchange_account_id
            if not account_id:
                raise osv.except_osv(_('Insufficient Configuration!'), _(
                    "You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        else:
            account_id = company.expense_currency_exchange_account_id
            if not account_id:
                raise osv.except_osv(_('Insufficient Configuration!'), _(
                    "You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        return account_id

    def check_amount_cero_lines(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.amount == 0 and not voucher.line_dr_ids and not voucher.line_cr_ids:
                raise osv.except_osv('ValidateError!', u'No puede contabilizar un pago con saldo cero y sin líneas.')
        return True

    ## NOTE: Función ´´action_move_line_create´´ de 'account.voucher' no estaba pasando context al llamar ´´reconcile_partial´´ en account_voucher/account_voucher.py línea 1432
    #def action_move_line_create(self, cr, uid, ids, context=None):
    #    if context is None:
    #        context = {}
    #    ctx = context.copy()
    #    ctx.update({'voucher': self.browse(cr, uid, ids[0],context=ctx)})
    #    return super(grp_facturas_account_voucher, self).action_move_line_create(cr, uid, ids, context=ctx)
    def action_move_line_create(self, cr, uid, ids, context=None):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for voucher in self.browse(cr, uid, ids, context=context):
            context = dict(context, voucher=voucher) ## update context and pass in ´´reconcile_partial´´ function
            local_context = dict(context, force_company=voucher.journal_id.company_id.id)
            if voucher.move_id:
                continue
            company_currency = self._get_company_currency(cr, uid, voucher.id, context)
            current_currency = self._get_current_currency(cr, uid, voucher.id, context)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(cr, uid, voucher.id, context)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx.update({'date': voucher.date})
            # Create the account move record.
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, voucher.id, context=context), context=context)
            # Get the name of the account_move just created
            name = move_pool.browse(cr, uid, move_id, context=context).name
            # Create the first line of the voucher
            move_line_id = move_line_pool.create(cr, uid, self.first_move_line_get(cr,uid,voucher.id, move_id, company_currency, current_currency, local_context), local_context)
            move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
            line_total = move_line_brw.debit - move_line_brw.credit
            rec_list_ids = []
            if voucher.type == 'sale':
                line_total = line_total - self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            elif voucher.type == 'purchase':
                line_total = line_total + self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            # Create one move line per voucher line where amount is not 0.0
            line_total, rec_list_ids = self.voucher_move_line_create(cr, uid, voucher.id, line_total, move_id, company_currency, current_currency, context)
            rec_list_voucher_lines = context.get('rec_lst_voucher_lines', []) ##

            # Create the writeoff line if needed
            ml_writeoff = self.writeoff_move_line_get(cr, uid, voucher.id, line_total, move_id, name, company_currency, current_currency, local_context)
            if ml_writeoff:
                move_line_pool.create(cr, uid, ml_writeoff, local_context)
            # We post the voucher.
            self.write(cr, uid, [voucher.id], {
                'move_id': move_id,
                'state': 'posted',
                'number': name,
            })
            if voucher.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context={})
            # We automatically reconcile the account move lines.
            reconcile = False
            index = 0
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    context.pop('voucher_line', None)
                    if len(rec_list_voucher_lines) > index:
                        context.update({'voucher_line': rec_list_voucher_lines[index]})
                    context.update({'date_p': voucher.entry_date or voucher.date})
                    reconcile = move_line_pool.reconcile_partial(cr, uid, rec_ids, context=context, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id) ## pasar context
                index += 1

        return True



    # Metodo para enviar a crear  el asiento que crea es el en dolares, por el tipo de cambio
    def voucher_move_line_create_mod(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency,
                                     invoice_id, context=None):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).

        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        move_obj = self.pool.get('account.move')
        currency_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        tot_line = line_total
        rec_lst_ids = []
        # 002 - cambio 03
        rec_lst_mlines_negativos_ids = []

        date = self.read(cr, uid, voucher_id, ['date'], context=context)['date']
        ctx = context.copy()
        ctx.update({'date': date})
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
        voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
        ctx.update({
            'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate,
            'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False, })
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')

        for line in voucher.line_ids:
            if not line.amount and not (
                            line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit,
                                                                    precision_digits=prec) and not float_compare(
                        line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_currency.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
            # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
            # currency rate difference
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise osv.except_osv(_('Wrong voucher line'),
                                         _("The invoice you are willing to pay is not valid anymore."))
                sign = voucher.type in ('payment', 'purchase') and -1 or 1
                currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
            else:
                currency_rate_difference = 0.0
            move_line = {
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'currency_id': line.move_line_id and (
                    company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'

            if (line.type == 'dr'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': voucher.tax_id.id,
                })

            if move_line.get('account_tax_id', False):
                tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
                if not (tax_data.base_code_id and tax_data.tax_code_id):
                    raise osv.except_osv(_('No Account Base Code and Account Tax Code!'), _(
                        "You have to configure account base code and account tax code on the '%s' tax!") % (
                                             tax_data.name))

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = False
            # 007 Cambios de importes
            corregido = False
            ajuste_negativo = False
            if line.move_line_id:
                # We want to set it on the account move line as soon as the original line had a foreign currency
                if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                    # we compute the amount in that foreign currency.
                    if line.move_line_id.currency_id.id == current_currency:
                        if move_line['debit'] or move_line['credit']:
                            sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                            amount_currency = sign * (line.amount)
                        elif voucher.line_dr_ids or voucher.line_cr_ids and line.amount != 0:
                            if voucher.invoice_id and line.amount != 0:
                                if voucher.invoice_id.type in (
                                        'in_invoice', 'out_refund'):  # fact de proveedor o rectificativa de cliente
                                    sign = 1
                                elif voucher.invoice_id.type in ('in_refund'):  # rect de proveedor
                                    corregido = True
                                    sign = (line.amount > 0) and -1 or 1
                                    ajuste_negativo = voucher.invoice_id.amount_total < 0 and True or False
                                elif voucher.invoice_id.type in (
                                        'out_invoice'):  # de cliente, dividido en un else por si es un caso diferente, puede agregarse en la condicion de arriba
                                    sign = (line.amount > 0) and -1 or 1
                                amount_currency = sign * (line.amount)
                    else:
                        # if the rate is specified on the voucher, it will be used thanks to the special keys in the context
                        # otherwise we use the rates of the system
                        amount_currency = currency_obj.compute(cr, uid, company_currency,
                                                               line.move_line_id.currency_id.id,
                                                               move_line['debit'] - move_line['credit'], context=ctx)
                if line.amount == line.amount_unreconciled:
                    sign = voucher.type in ('payment', 'purchase') and -1 or 1
                    # Si estamos en los casos particulares anteriormente descritos,
                    # entonces el signo cambia, para evitar que foreign_currency_diff de un valor no nulo.
                    if corregido:
                        sign = sign * -1
                        foreign_currency_diff = sign * line.move_line_id.amount_residual_currency + amount_currency
                    else:
                        foreign_currency_diff = (line.move_line_id.amount_residual_currency - abs(amount_currency))
            # 004 Lineas en blanco
            rec_ids = []
            if amount_currency != 0.0 or amount != 0.0:
                # 007 Cambios
                if corregido and ajuste_negativo:
                    amount_currency = amount_currency * -1
                # 007 Fin de cambios signo
                move_line['amount_currency'] = amount_currency
                voucher_line = move_line_obj.create(cr, uid, move_line)
                rec_ids = [voucher_line, line.move_line_id.id]
            if len(rec_ids) == 0:
                rec_ids = [line.move_line_id.id]
            # cambio para lineas en banco
            # 004 Lineas en blanco Fin

            if not currency_obj.is_zero(cr, uid, voucher.company_id.currency_id, currency_rate_difference):
                # Change difference entry in company currency
                exch_lines = self._get_exchange_lines(cr, uid, line, move_id, currency_rate_difference,
                                                      company_currency, current_currency, context=context)
                new_id = move_line_obj.create(cr, uid, exch_lines[0], context)
                move_line_obj.create(cr, uid, exch_lines[1], context)
                rec_ids.append(new_id)

            if line.move_line_id and line.move_line_id.currency_id and not currency_obj.is_zero(cr, uid,
                                                                                                line.move_line_id.currency_id,
                                                                                                foreign_currency_diff):
                # si no subio el TC
                # Probando comentando aca, 15/09
                if line.move_line_id:
                    # Change difference entry in voucher currency
                    move_line_foreign_currency = {
                        'journal_id': line.voucher_id.journal_id.id,
                        'period_id': line.voucher_id.period_id.id,
                        'name': _('change') + ': ' + (line.name or '/'),
                        'account_id': line.account_id.id,
                        'move_id': move_id,
                        'partner_id': line.voucher_id.partner_id.id,
                        'currency_id': line.move_line_id.currency_id.id,
                        'amount_currency': -1 * foreign_currency_diff,
                        'quantity': 1,
                        'credit': 0.0,
                        'debit': 0.0,
                        'date': line.voucher_id.date,
                        # 009- pasando campo
                        'exchange_line': True,
                    }
                    new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context)
                    rec_ids.append(new_id)

            if line.move_line_id.id:
                rec_lst_ids.append(rec_ids)
        return (tot_line, rec_lst_ids, rec_lst_mlines_negativos_ids)

    # metodo nuevo modificado echaviano 07/08
    def writeoff_move_line_get_mod(self, cr, uid, voucher_id, line_total, move_id, name, company_currency,
                                   current_currency, invoice_id, context=None):
        '''
        Set a dict to be use to create the writeoff move line.

        :param voucher_id: Id of voucher what we are creating account_move.
        :param line_total: Amount remaining to be allocated on lines.
        :param move_id: Id of account move where this line will be added.
        :param name: Description of account move line.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: mapping between fieldname and value of account move line to create
        :rtype: dict
        '''
        currency_obj = self.pool.get('res.currency')
        move_line = {}

        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context)
        current_currency_obj = voucher.currency_id or voucher.journal_id.company_id.currency_id

        # Cambio elemento 5
        if not currency_obj.is_zero(cr, uid, current_currency_obj, line_total):
            diff = line_total
            account_id = False
            divisa = False
            write_off_name = ''
            if voucher.payment_option == 'with_writeoff':
                account_id = voucher.writeoff_acc_id.id
                write_off_name = voucher.comment
            elif voucher.type in ('sale', 'receipt'):
                account_id = voucher.partner_id.property_account_receivable.id
            elif voucher.type == 'payment':  # modificacion para que agarre la cuenta -- Cambio elemento 5
                account_id = invoice_id.account_id and invoice_id.account_id.id or False
                divisa = invoice_id.account_id.currency_id and invoice_id.account_id.currency_id.id and invoice_id.account_id.currency_id.id <> company_currency and True or False
            else:
                account_id = voucher.partner_id.property_account_payable.id
            # Cambio elemento 5 Fin
            sign = voucher.type == 'payment' and -1 or 1
            # 001 De la cuenta de la factura y no la del proveedor
            if divisa:
                move_line = {
                    'name': write_off_name or name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'credit': diff > 0 and diff or 0.0,
                    'debit': diff < 0 and -diff or 0.0,
                    'amount_currency': company_currency <> current_currency and (
                        sign * -1 * voucher.writeoff_amount) or 0.0,
                    'currency_id': invoice_id.account_id.currency_id and invoice_id.account_id.currency_id.id or False,
                    'analytic_account_id': voucher.analytic_id and voucher.analytic_id.id or False,
                }
            else:
                move_line = {
                    'name': write_off_name or name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'credit': diff > 0 and diff or 0.0,
                    'debit': diff < 0 and -diff or 0.0,
                    'amount_currency': company_currency <> current_currency and (
                        sign * -1 * voucher.writeoff_amount) or 0.0,
                    'currency_id': company_currency <> current_currency and current_currency or False,
                    'analytic_account_id': voucher.analytic_id and voucher.analytic_id.id or False,
                }
        return move_line

    # METODOS PARA CUANDO SUBE EL TIPO DE CAMBIO
    def button_proforma_auxiliary_voucher(self, cr, uid, ids, context=None):
        context = context or {}
        wf_service = netsvc.LocalService("workflow")
        for vid in ids:
            if 'invoice_id' in context and context.get('invoice_id') and context.get('type', False) == 'payment':
                self.write(cr, uid, vid, {'invoice_id': context.get('invoice_id')}, context)
            #Se valida el voucher solo si viene en el contexto 'validar' en True
            if context.get('validar',False):
                wf_service.trg_validate(uid, 'account.voucher', vid, 'proforma_voucher_auxiliary', cr)

        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher',
                                                                            'view_vendor_payment_form')
        vou = self.browse(cr, uid, ids[0], context=context)
        return {
            'name': _("Voucher Payment"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': vou.id,
            }

    def proforma_voucher_auxiliary(self, cr, uid, ids, context=None):
        for voucher in self.browse(cr, uid, ids, context=context):
            if not voucher.up_tc and not voucher.down_tc:
                return self.action_move_line_create(cr, uid, ids, context=context)
        self.action_move_line_create_change_tc(cr, uid, ids, context=context)
        return True

    def button_proforma_voucher(self, cr, uid, ids, context=None):
        context = context or {}
        for vid in ids:
            if 'invoice_id' in context and context.get('invoice_id') and 'type' in context and context.get('type',
                                                                                                           False) == 'payment':
                self.write(cr, uid, vid, {'invoice_id': context.get('invoice_id')}, context)
        context.update({'entry_date': True})
        return super(grp_facturas_account_voucher, self).button_proforma_voucher(cr, uid, ids, context=context)

    # refefiniendo metodo
    # TODO: GAP 247 Modificando el nuevo campo Fecha asiento en base al campo Fecha
    def onchange_date_change_tc(self, cr, uid, ids, date, currency_id, payment_rate_currency_id, amount, company_id,
                                rate, partner_id, journal_id, ttype, context=None):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        if context is None:
            context = {}
        res = {'value': {}}
        # set the period of the voucher
        period_pool = self.pool.get('account.period')
        currency_obj = self.pool.get('res.currency')
        ctx = context.copy()
        ctx.update({'company_id': company_id, 'account_period_prefer_normal': True})
        voucher_currency_id = currency_id or self.pool.get('res.company').browse(cr, uid, company_id,
                                                                                 context=ctx).currency_id.id
        pids = period_pool.find(cr, uid, date, context=ctx)
        if pids:
            res['value'].update({'period_id': pids[0]})
        if payment_rate_currency_id:
            ctx.update({'date': date})
            payment_rate = 1.0
            if payment_rate_currency_id != currency_id:
                tmp = currency_obj.browse(cr, uid, payment_rate_currency_id, context=ctx).rate
                payment_rate = tmp / currency_obj.browse(cr, uid, voucher_currency_id, context=ctx).rate
            vals = self.onchange_payment_rate_currency(cr, uid, ids, voucher_currency_id, payment_rate,
                                                       payment_rate_currency_id, date, amount, company_id,
                                                       context=context)
            vals['value'].update({'payment_rate': payment_rate})
            for key in vals.keys():
                res[key].update(vals[key])

        vals2 = self.onchange_amount_change_tc(cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype,
                                               date, payment_rate_currency_id, company_id, context=context)
        for key in vals2.keys():
            res[key].update(vals2[key])

        res['value'].update({'entry_date': date})

        return res

    def onchange_amount_change_tc(self, cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date,
                                  payment_rate_currency_id, company_id, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update({'date': date})
        # read the voucher rate with the right date in the context
        currency_id = currency_id or self.pool.get('res.company').browse(cr, uid, company_id,
                                                                         context=ctx).currency_id.id
        voucher_rate = self.pool.get('res.currency').read(cr, uid, currency_id, ['rate'], context=ctx)['rate']
        ctx.update({
            'voucher_special_currency': payment_rate_currency_id,
            'voucher_special_currency_rate': rate * voucher_rate})
        res = self.recompute_voucher_new_lines(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date,
                                               context=ctx)
        vals = self.onchange_rate(cr, uid, ids, rate, amount, currency_id, payment_rate_currency_id, company_id,
                                  context=ctx)
        for key in vals.keys():
            res[key].update(vals[key])

        # 005 Inicio de correccion en bajada de TC en pago
        values = res['value']
        lines = 'line_dr_ids' in values and values['line_dr_ids'] or False
        # 005 Fin declaracion variables

        if 'invoice_id' in context and context.get('invoice_id') and context.get('type', False) == 'payment':
            invoice_obj = self.pool.get('account.invoice')
            invoice = invoice_obj.browse(cr, uid, context.get('invoice_id'), context)

            journal_pool = self.pool.get('account.journal')
            company_currency = self.pool.get('res.company').browse(cr, uid, company_id, context=context).currency_id

            if amount and currency_id and journal_id:
                payment_currency = context.get('payment_expected_currency', False)

                journal = journal_pool.browse(cr, uid, journal_id, context=context)
                journal_currency = currency_id
                if journal.currency:
                    journal_currency = journal.currency.id

                down_tc = False
                up_tc = False

                # se asume siempre que se va a pagar con una moneda distinta a la moneda de la factura
                if journal_currency != invoice.currency_id.id:
                    ctx = dict(context, account_period_prefer_normal=True)
                    ctx.update({'date': invoice.date_invoice})
                    amount_inv_in_company_currency = self.pool.get('res.currency').compute(cr, uid,
                                                                                           invoice.currency_id.id,
                                                                                           journal_currency,
                                                                                           invoice.residual,
                                                                                           context=ctx)
                    res['value']['writeoff_amount_aux'] = amount - round(amount_inv_in_company_currency)
                    total_residual_pay = False
                    currency_rate_antes = invoice.currency_rate or 1

                    ctx_now = dict(context)
                    ctx_now.update({'date': date or datetime.date.today().strftime('%Y-%m-%d')})
                    currency_now = self.pool.get('res.currency').browse(cr, uid, invoice.currency_id.id,
                                                                        context=ctx_now)

                    # 006 Bajada y Subida del TC
                    down_tc = currency_rate_antes > currency_now.rate and True or False
                    up_tc = currency_rate_antes < currency_now.rate and True or False

                # Calculo del down tc
                elif invoice.currency_id.id != company_currency.id:
                    # si la moneda de la factura es distinta a la de la compañia
                    # asumo que la cuenta de la factura es la moneda extranjera, company_currency el rate = 1
                    currency_rate_antes = invoice.currency_rate or 1

                    ctx_now = dict(context)
                    ctx_now.update({'date': date or datetime.date.today().strftime('%Y-%m-%d')})
                    currency_now = self.pool.get('res.currency').browse(cr, uid, invoice.currency_id.id,
                                                                        context=ctx_now)

                    # 006 Bajada y Subida del TC
                    down_tc = currency_rate_antes > currency_now.rate and True or False
                    up_tc = currency_rate_antes < currency_now.rate and True or False

                res['value']['writeoff_acc_aux_id'] = self._get_aux_account_id(cr, uid, ids, down_tc,
                                                                               context=context).id
                # res['value']['writeoff_amount_aux'] = amount - invoice.residual
                res['value']['down_tc'] = down_tc
                res['value']['up_tc'] = up_tc  # si la moneda es la misma no hay que hacer la correccion
        return res

    def onchange_journal_new(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype,
                             company_id, context=None):
        if context is None:
            context = {}
        if not journal_id:
            return False
        journal_pool = self.pool.get('account.journal')
        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        account_id = journal.default_credit_account_id or journal.default_debit_account_id
        tax_id = False
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0].id

        vals = {'value': {}}
        if ttype in ('sale', 'purchase'):
            vals = self.onchange_price(cr, uid, ids, line_ids, tax_id, partner_id, context)
            vals['value'].update({'tax_id': tax_id, 'amount': amount})
        currency_id = False
        if journal.currency:
            currency_id = journal.currency.id
        else:
            currency_id = journal.company_id.currency_id.id
        vals['value'].update({'currency_id': currency_id})
        # in case we want to register the payment directly from an invoice, it's confusing to allow to switch the journal
        # without seeing that the amount is expressed in the journal currency, and not in the invoice currency. So to avoid
        # this common mistake, we simply reset the amount to 0 if the currency is not the invoice currency.
        if context.get('payment_expected_currency') and currency_id != context.get('payment_expected_currency'):
            vals['value']['amount'] = 0
            amount = 0

        change_tc = False
        line_total_received = line_ids and line_ids[0] or False  # revisar este campo

        if 'invoice_id' in context and context.get('invoice_id') and context.get('type', False) == 'payment':
            change_tc = True
            invoice_obj = self.pool.get('account.invoice')
            invoice = invoice_obj.browse(cr, uid, context.get('invoice_id'), context)

            company_currency = self.pool.get('res.company').browse(cr, uid, company_id, context=context).currency_id

            if amount and currency_id and journal_id:
                payment_currency = context.get('payment_expected_currency', False)

                journal = journal_pool.browse(cr, uid, journal_id, context=context)
                journal_currency = currency_id
                if journal.currency:
                    journal_currency = journal.currency.id

                down_tc = False
                up_tc = False
                writeoff_amount_aux = 0.0

                # se asume siempre que se va a pagar con una moneda distinta a la moneda de la factura
                if journal_currency != invoice.currency_id.id:
                    ctx = dict(context, account_period_prefer_normal=True)
                    ctx.update({'date': invoice.date_invoice})
                    amount_inv_in_company_currency = self.pool.get('res.currency').compute(cr, uid,
                                                                                           invoice.currency_id.id,
                                                                                           journal_currency,
                                                                                           invoice.residual,
                                                                                           context=ctx)
                    writeoff_amount_aux = amount - round(amount_inv_in_company_currency)
                    # else:
                    #     res['value']['writeoff_amount_aux'] = amount - invoice.amount_total
                    total_residual_pay = False

                    currency_rate_antes = invoice.currency_rate or 1

                    ctx_now = dict(context)
                    ctx_now.update({'date': date or datetime.date.today().strftime('%Y-%m-%d')})
                    currency_now = self.pool.get('res.currency').browse(cr, uid, invoice.currency_id.id,
                                                                        context=ctx_now)
                    # 006 Bajada y Subida del TC
                    down_tc = currency_rate_antes > currency_now.rate and True or False
                    up_tc = currency_rate_antes < currency_now.rate and True or False

                # Calculo del down tc
                elif invoice.currency_id.id != company_currency.id:
                    # si la moneda de la factura es distinta a la de la compañia
                    # asumo que la cuenta de la factura es la moneda extranjera, company_currency el rate = 1
                    currency_rate_antes = invoice.currency_rate or 1

                    ctx_now = dict(context)
                    ctx_now.update({'date': date or datetime.date.today().strftime('%Y-%m-%d')})
                    currency_now = self.pool.get('res.currency').browse(cr, uid, invoice.currency_id.id,
                                                                        context=ctx_now)
                    # 006 Bajada y Subida del TC
                    down_tc = currency_rate_antes > currency_now.rate and True or False
                    up_tc = currency_rate_antes < currency_now.rate and True or False

                writeoff_acc_aux_id = self._get_aux_account_id(cr, uid, ids, down_tc,
                                                               context=context) and self._get_aux_account_id(cr, uid,
                                                                                                             ids,
                                                                                                             down_tc,
                                                                                                             context=context).id

                vals['value'].update({'writeoff_acc_aux_id': writeoff_acc_aux_id, 'up_tc': up_tc, 'down_tc': down_tc,
                                      'writeoff_amount_aux': writeoff_amount_aux})

        if partner_id:
            res = self.onchange_partner_id_new(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date,
                                               context)
            for key in res.keys():
                vals[key].update(res[key])
        return vals

    def onchange_partner_id_new(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date,
                                context=None):
        if not journal_id:
            return {}
        if context is None:
            context = {}
        # TODO: comment me and use me directly in the sales/purchases views
        res = self.basic_onchange_partner(cr, uid, ids, partner_id, journal_id, ttype, context=context)
        if ttype in ['sale', 'purchase']:
            return res
        ctx = context.copy()
        # not passing the payment_rate currency and the payment_rate in the context but it's ok because they are reset in recompute_payment_rate
        ctx.update({'date': date})
        vals = self.recompute_voucher_new_lines(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date,
                                                context=ctx)
        vals2 = self.recompute_payment_rate(cr, uid, ids, vals, currency_id, date, ttype, journal_id, amount,
                                            context=context)
        for key in vals.keys():
            res[key].update(vals[key])
        for key in vals2.keys():
            res[key].update(vals2[key])
        # TODO: can probably be removed now
        # TODO: onchange_partner_id() should not returns [pre_line, line_dr_ids, payment_rate...] for type sale, and not
        # [pre_line, line_cr_ids, payment_rate...] for type purchase.
        # We should definitively split account.voucher object in two and make distinct on_change functions. In the
        # meanwhile, bellow lines must be there because the fields aren't present in the view, what crashes if the
        # onchange returns a value for them
        if ttype == 'sale':
            del (res['value']['line_dr_ids'])
            del (res['value']['pre_line'])
            del (res['value']['payment_rate'])
        elif ttype == 'purchase':
            del (res['value']['line_cr_ids'])
            del (res['value']['pre_line'])
            del (res['value']['payment_rate'])
        return res

    def recompute_voucher_new_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date,
                                    context=None):
        """
        Returns a dict that contains new values and context

        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """

        def _remove_noise_in_o2m():
            """if the line is partially reconciled, then we must pay attention to display it only once and
                in the good o2m.
                This function returns True if the line is considered as noise and should not be displayed
            """
            if line.reconcile_partial_id:
                if currency_id == line.currency_id.id:
                    if line.amount_residual_currency <= 0:
                        return True
                else:
                    if line.amount_residual <= 0:
                        return True
            return False

        if context is None:
            context = {}
        context_multi_currency = context.copy()

        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        line_pool = self.pool.get('account.voucher.line')

        # set default values
        default = {
            'value': {'line_dr_ids': [], 'line_cr_ids': [], 'pre_line': False, },
        }

        # drop existing lines
        line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])]) or False
        if line_ids:
            line_pool.unlink(cr, uid, line_ids)

        if not partner_id or not journal_id:
            return default

        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        currency_id = currency_id or journal.company_id.currency_id.id

        total_credit = 0.0
        total_debit = 0.0
        account_type = None
        if context.get('account_id'):
            account_type = self.pool['account.account'].browse(cr, uid, context['account_id'], context=context).type
        if ttype == 'payment':
            if not account_type:
                account_type = 'payable'
            total_debit = price or 0.0
        else:
            total_credit = price or 0.0
            if not account_type:
                account_type = 'receivable'

        if not context.get('move_line_ids', False):
            ids = move_line_pool.search(cr, uid, [('state', '=', 'valid'), ('account_id.type', '=', account_type),
                                                  ('reconcile_id', '=', False), ('partner_id', '=', partner_id)],
                                        context=context)
        else:
            ids = context['move_line_ids']
        invoice_id = context.get('invoice_id', False)

        invoice_currency = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context).currency_id.id

        company_currency = journal.company_id.currency_id.id
        move_lines_found = []

        # order the lines by most old first
        ids.reverse()
        account_move_lines = move_line_pool.browse(cr, uid, ids, context=context)

        # compute the total debit/credit and look for a matching open amount or invoice
        for line in account_move_lines:

            # Probando comentando esto 15/09
            if _remove_noise_in_o2m():
                continue

            # invoice_currency = line.move_line_id.currency_id and line.move_line_id.currency_id or False
            if invoice_id:
                if line.invoice.id == invoice_id:
                    # if the invoice linked to the voucher line is equal to the invoice_id in context
                    # then we assign the amount on that line, whatever the other voucher lines
                    move_lines_found.append(line.id)
            elif currency_id == company_currency:
                # otherwise treatments is the same but with other field names
                if line.amount_residual == price:
                    # if the amount residual is equal the amount voucher, we assign it to that voucher
                    # line, whatever the other voucher lines
                    move_lines_found.append(line.id)
                    break
                # otherwise we will split the voucher amount on each line (by most old first)
                total_credit += line.credit or 0.0
                total_debit += line.debit or 0.0
            elif currency_id == line.currency_id.id:
                if line.amount_residual_currency == price:
                    move_lines_found.append(line.id)
                    break
                total_credit += line.credit and line.amount_currency or 0.0
                total_debit += line.debit and line.amount_currency or 0.0

        remaining_amount = price
        # voucher line creation
        for line in account_move_lines:
            # Probando comentando esto 15/09
            if _remove_noise_in_o2m():
                continue

            if line.currency_id and currency_id == line.currency_id.id:
                amount_original = abs(line.amount_currency)
                amount_original_move_line = abs(line.amount_currency)
                amount_unreconciled = abs(line.amount_residual_currency)
            else:
                # always use the amount booked in the company currency as the basis of the conversion into the voucher currency
                # cambio aca la forma de calcular los montos y lo restante
                # echaviano, cambio de calculo de amount original
                if line.currency_id and line.amount_currency and invoice_currency != company_currency:
                    amount_original = currency_pool.compute(cr, uid, invoice_currency, company_currency,
                                                            abs(line.amount_currency) or 0.0,
                                                            context=context_multi_currency)
                    amount_original_move_line = currency_pool.compute(cr, uid, company_currency, currency_id,
                                                                      line.credit or line.debit or 0.0,
                                                                      context=context_multi_currency)
                    amount_unreconciled = currency_pool.compute(cr, uid, invoice_currency, company_currency,
                                                                abs(line.amount_residual_currency),
                                                                context=context_multi_currency)
                    # montos y restante, fin
                else:
                    amount_original = currency_pool.compute(cr, uid, company_currency, currency_id,
                                                            line.credit or line.debit or 0.0,
                                                            context=context_multi_currency)
                    amount_original_move_line = currency_pool.compute(cr, uid, company_currency, currency_id,
                                                                      line.credit or line.debit or 0.0,
                                                                      context=context_multi_currency)
                    amount_unreconciled = currency_pool.compute(cr, uid, company_currency, currency_id,
                                                                abs(line.amount_residual),
                                                                context=context_multi_currency)

            line_currency_id = line.currency_id and line.currency_id.id or company_currency
            # Para cuando no hay credito y debito, tener en cuenta el monto en moneda original
            type_credit = line.credit and 'dr' or 'cr'
            if not line.credit and not line.debit and abs(line.amount_currency):
                type_credit = line.amount_currency < 0 and 'dr' or 'cr'
            rs = {
                'name': line.move_id.name,
                'type': type_credit,
                'move_line_id': line.id,
                'account_id': line.account_id.id,
                'amount_original': amount_original,
                'amount_original_move_line': amount_original_move_line,
                'amount': (line.id in move_lines_found) and min(abs(remaining_amount), amount_unreconciled) or 0.0,
                'date_original': line.date,
                'date_due': line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'currency_id': line_currency_id,
            }
            remaining_amount -= rs['amount']
            # in case a corresponding move_line hasn't been found, we now try to assign the voucher amount
            # on existing invoices: we split voucher amount by most old first, but only for lines in the same currency
            if not move_lines_found:
                if currency_id == line_currency_id:
                    if line.credit:
                        amount = min(amount_unreconciled, abs(total_debit))
                        rs['amount'] = amount
                        total_debit -= amount
                    else:
                        amount = min(amount_unreconciled, abs(total_credit))
                        rs['amount'] = amount
                        total_credit -= amount

            # CAMBIO MVARELA - Se compara con funcion is_zero para tolerancia de decimales
            # if rs['amount_unreconciled'] == rs['amount']:
            moneda = currency_pool.browse(cr, uid, currency_id)
            if currency_pool.is_zero(cr, uid, moneda, rs['amount_unreconciled'] - rs['amount']):
                rs['reconcile'] = True

            if rs['type'] == 'cr':
                default['value']['line_cr_ids'].append(rs)
            else:
                default['value']['line_dr_ids'].append(rs)

            if len(default['value']['line_cr_ids']) > 0:
                default['value']['pre_line'] = 1
            elif len(default['value']['line_dr_ids']) > 0:
                default['value']['pre_line'] = 1
            default['value']['writeoff_amount'] = self._compute_writeoff_amount(cr, uid,
                                                                                default['value']['line_dr_ids'],
                                                                                default['value']['line_cr_ids'], price,
                                                                                ttype)
            # default['value']['writeoff_amount'] = 0
        return default

    def action_move_line_create_change_tc(self, cr, uid, ids, context=None):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')

        # Elementos agregados para las modificaciones
        invoice_pool = self.pool.get('account.invoice')
        journal_pool = self.pool.get('account.journal')
        if context.get('invoice_id', False):
            invoice_id = invoice_pool.browse(cr, uid, context['invoice_id'], context=context)

        for voucher in self.browse(cr, uid, ids, context=context):
            local_context = dict(context, force_company=voucher.journal_id.company_id.id)
            if voucher.move_id:
                continue

            invoice_id = voucher.invoice_id or False
            company_currency = self._get_company_currency(cr, uid, voucher.id, context)
            current_currency = self._get_current_currency(cr, uid, voucher.id, context)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(cr, uid, voucher.id, context)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx.update({'date': voucher.date,'date_p':voucher.date})
            # Create the account move record.
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, voucher.id, context=context),
                                       context=context)
            # Get the name of the account_move just created
            name = move_pool.browse(cr, uid, move_id, context=context).name
            # Create the first line of the voucher
            move_line_id = move_line_pool.create(cr, uid, self.first_move_line_get(cr, uid, voucher.id, move_id,
                                                                                   company_currency, current_currency,
                                                                                   local_context), local_context)
            move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
            line_total = move_line_brw.debit - move_line_brw.credit
            rec_list_ids = []
            if voucher.type == 'sale':
                line_total = line_total - self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            elif voucher.type == 'purchase':
                line_total = line_total + self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)

            # foreign_negativo = False
            # Create one move line per voucher line where amount is not 0.0
            if invoice_id:  # and foreign_negativo:
                # 002 - cambio del elemento 3 sin importar la moneda del diario, se crea asiendo por el doble si hubo diferencia
                line_total, rec_list_ids = self.voucher_move_line_create_pay_tc(cr, uid, voucher.id, line_total,
                                                                                move_id, company_currency,
                                                                                current_currency, invoice_id, context)
            else:
                line_total, rec_list_ids = self.voucher_move_line_create(cr, uid, voucher.id, line_total, move_id,
                                                                         company_currency, current_currency, context)

            # Create the writeoff line if needed
            # Cambio elemento 5, Pasar la cuenta de la factura original y no la del cliente
            if invoice_id:
                ml_writeoff = self.writeoff_move_line_get_mod(cr, uid, voucher.id, line_total, move_id, name,
                                                              company_currency, current_currency, invoice_id,
                                                              local_context)
                # if voucher.fix_down_tc: # moneda es distinta
                #     self.create_fix_move_down_tc(cr, uid, voucher.id, line_total, move_id, name, company_currency, current_currency, invoice_id, local_context)
            else:
                ml_writeoff = self.writeoff_move_line_get(cr, uid, voucher.id, line_total, move_id, name,
                                                          company_currency, current_currency, local_context)
            # ml_writeoff = self.writeoff_move_line_get(cr, uid, voucher.id, line_total, move_id, name, company_currency, current_currency, local_context)

            if ml_writeoff:
                move_line_pool.create(cr, uid, ml_writeoff, local_context)
            # We post the voucher.
            self.write(cr, uid, [voucher.id], {
                'move_id': move_id,
                # 'state': 'posted', Gap 267
                'state': 'draft',
                'number': name,
            })

            if voucher.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context={})
            # We automatically reconcile the account move lines.
            reconcile = False
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    res_partner_pool = self.pool.get('res.partner')
                    if not res_partner_pool.check_access_rights(cr, uid, 'write', raise_exception=False):
                        user_id = SUPERUSER_ID
                    else:
                        user_id = uid
                    # if voucher.writeoff_amount_aux < 0.0 and voucher.down_tc and not voucher.writeoff_acc_id:
                    # if voucher.down_tc and voucher.writeoff_amount_aux == 0.0 and not voucher.writeoff_acc_id:
                    # echaviano, cuenta en subida de TC
                    ctx['voucher'] = voucher
                    if voucher.up_tc or voucher.down_tc:
                        # if not voucher.writeoff_acc_aux_id:
                        #     raise osv.except_osv(_('Warning!'), _('You have to provide an account of difference amount for the write off/exchange difference entry.'))
                        writeoff_acc_aux_id = False
                        if voucher.writeoff_acc_id.id and voucher.writeoff_acc_id.id:
                            writeoff_acc_aux_id = voucher.writeoff_acc_id.id
                        elif voucher.writeoff_acc_aux_id and voucher.writeoff_acc_aux_id.id:
                            writeoff_acc_aux_id = voucher.writeoff_acc_aux_id.id
                        reconcile = move_line_pool.reconcile_partial(cr, user_id, rec_ids,
                                                                     writeoff_acc_id=writeoff_acc_aux_id,
                                                                     writeoff_period_id=voucher.period_id.id,
                                                                     writeoff_journal_id=voucher.journal_id.id, context=ctx)
                    else:
                        reconcile = move_line_pool.reconcile_partial(cr, user_id, rec_ids,
                                                                     writeoff_acc_id=voucher.writeoff_acc_id.id,
                                                                     writeoff_period_id=voucher.period_id.id,
                                                                     writeoff_journal_id=voucher.journal_id.id, context=ctx)
        return True

    # Metodo para enviar a crear  el asiento que crea es el en dolares, por el tipo de cambio
    def voucher_move_line_create_pay_tc(self, cr, uid, voucher_id, line_total, move_id, company_currency,
                                        current_currency, invoice_id, context=None):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).

        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        move_obj = self.pool.get('account.move')
        currency_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        tot_line = line_total
        rec_lst_ids = []

        date = self.read(cr, uid, voucher_id, ['date'], context=context)['date']
        ctx = context.copy()
        ctx.update({'date': date})
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
        voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
        ctx.update({
            'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate,
            'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False, })
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')

        for line in voucher.line_ids:
            # chaviano, cambio a ver si funciona
            # if not line.amount and not line.amount_unreconciled and not line.amount_original:
            #     continue
            # create one move line per voucher line where amount is not 0.0
            # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
            if not line.amount and not (
                            line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit,
                                                                    precision_digits=prec) and not float_compare(
                        line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_currency.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
            # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
            # currency rate difference
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise osv.except_osv(_('Wrong voucher line'),
                                         _("The invoice you are willing to pay is not valid anymore."))
                sign = voucher.type in ('payment', 'purchase') and -1 or 1
                # 008- ECHAVIANO; REVISANDO PROBLEMAS CON RECT de PROVEEDOR
                if voucher.invoice_id and line.amount != 0:
                    if voucher.invoice_id.type in (
                            'in_invoice', 'out_refund'):  # fact de proveedor o rectificativa de cliente
                        sign = -1
                    elif voucher.invoice_id.type in ('out_invoice', 'in_refund'):  # de cliente o rect de proveedor
                        sign = 1
                # 008 - Fin
                currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
            else:
                currency_rate_difference = 0.0
            move_line = {
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                # 'name': 'MODDD %s' % line.name or '/',   # echaviano, aca es donde genera los asientos con saldo 0.0
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'currency_id': line.move_line_id and (
                    company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'

            if (line.type == 'dr'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': voucher.tax_id.id,
                })

            if move_line.get('account_tax_id', False):
                tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
                if not (tax_data.base_code_id and tax_data.tax_code_id):
                    raise osv.except_osv(_('No Account Base Code and Account Tax Code!'), _(
                        "You have to configure account base code and account tax code on the '%s' tax!") % (
                                             tax_data.name))

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = False
            if line.move_line_id:
                # We want to set it on the account move line as soon as the original line had a foreign currency
                if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                    # we compute the amount in that foreign currency.
                    if line.move_line_id.currency_id.id == current_currency:
                        # if the voucher and the voucher line share the same currency, there is no computation to do
                        sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                        amount_currency = sign * (line.amount)
                    else:
                        # if the rate is specified on the voucher, it will be used thanks to the special keys in the context
                        # otherwise we use the rates of the system
                        amount_currency = currency_obj.compute(cr, uid, company_currency,
                                                               line.move_line_id.currency_id.id,
                                                               move_line['debit'] - move_line['credit'], context=ctx)
                if line.amount == line.amount_unreconciled:
                    # sign = voucher.type in ('payment', 'purchase') and -1 or 1
                    # foreign_currency_diff = sign * line.move_line_id.amount_residual_currency + amount_currency
                    foreign_currency_diff = (line.move_line_id.amount_residual_currency - abs(amount_currency))
            # echaviano, revisar - para lineas que genera en blanco
            # 004 Lineas en blanco
            rec_ids = []
            if amount_currency != 0.0 or amount != 0.0:
                move_line['amount_currency'] = amount_currency
                voucher_line = move_line_obj.create(cr, uid, move_line)
                rec_ids = [voucher_line, line.move_line_id.id]
            # voucher_line = False
            # rec_ids = [voucher_line, line.move_line_id.id]
            if len(rec_ids) == 0:
                rec_ids = [line.move_line_id.id]
            # cambio para lineas en banco
            # 004 Lineas en blanco Fin

            if not currency_obj.is_zero(cr, uid, voucher.company_id.currency_id, currency_rate_difference):
                # Change difference entry in company currency
                exch_lines = self._get_exchange_lines(cr, uid, line, move_id, currency_rate_difference,
                                                      company_currency, current_currency, context=context)
                # 009-Agregando flag
                exch_lines[0].update({'exchange_line': True})
                exch_lines[1].update({'exchange_line': True})
                new_id = move_line_obj.create(cr, uid, exch_lines[0], context)
                move_line_obj.create(cr, uid, exch_lines[1], context)
                rec_ids.append(new_id)

            # if line.move_line_id and line.move_line_id.currency_id and not currency_obj.is_zero(cr, uid, line.move_line_id.currency_id, foreign_currency_diff):
            if line.move_line_id and line.move_line_id.currency_id and not currency_obj.is_zero(cr, uid,
                                                                                                line.move_line_id.currency_id,
                                                                                                foreign_currency_diff):
                # si no subio el TC

                # Probando comentando aca, 15/09
                # if voucher.total_residual_pay:
                if voucher.writeoff_amount_aux == 0:
                    # Change difference entry in voucher currency
                    move_line_foreign_currency = {
                        'journal_id': line.voucher_id.journal_id.id,
                        'period_id': line.voucher_id.period_id.id,
                        'name': _('change') + ': ' + (line.name or '/'),
                        'account_id': line.account_id.id,
                        'move_id': move_id,
                        'partner_id': line.voucher_id.partner_id.id,
                        'currency_id': line.move_line_id.currency_id.id,
                        'amount_currency': -1 * foreign_currency_diff,
                        'quantity': 1,
                        'credit': 0.0,
                        'debit': 0.0,
                        'date': line.voucher_id.date,
                        # 009- pasando campo
                        'exchange_line': True,
                    }
                    new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context)
                    rec_ids.append(new_id)

            if line.move_line_id.id:
                rec_lst_ids.append(rec_ids)
        return (tot_line, rec_lst_ids)

    def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency,
                                 context=None):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).

        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        if context is None:
            context = {}
        context = dict(context)
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        tot_line = line_total
        rec_lst_ids = []
        rec_lst_voucher_lines = []

        date = self.read(cr, uid, voucher_id, ['date'], context=context)['date']
        ctx = context.copy()
        ctx.update({'date': date})
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
        voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
        ctx.update({
            'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate,
            'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False, })
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        for line in voucher.line_ids:
            # create one move line per voucher line where amount is not 0.0
            # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
            if not line.amount and not (
                    line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit,
                                                            precision_digits=prec) and not float_compare(
                    line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
            # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
            # currency rate difference
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise osv.except_osv(_('Wrong voucher line'),
                                         _("The invoice you are willing to pay is not valid anymore."))
                sign = voucher.type in ('payment', 'purchase') and -1 or 1
                #currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
                currency_rate_difference = sign * (float_round(line.move_line_id.amount_residual, precision_digits=prec) - float_round(amount, precision_digits=prec))
            else:
                currency_rate_difference = 0.0
            move_line = {
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'currency_id': line.move_line_id and (
                company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'

            if (line.type == 'dr'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': voucher.tax_id.id,
                })

            if move_line.get('account_tax_id', False):
                tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
                if not (tax_data.base_code_id and tax_data.tax_code_id):
                    raise osv.except_osv(_('No Account Base Code and Account Tax Code!'), _(
                        "You have to configure account base code and account tax code on the '%s' tax!") % (
                                         tax_data.name))

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = False
            corregido = False
            ajuste_negativo = False
            if line.move_line_id:
                # We want to set it on the account move line as soon as the original line had a foreign currency
                if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                    # we compute the amount in that foreign currency.
                    if line.move_line_id.currency_id.id == current_currency:
                        # if the voucher and the voucher line share the same currency, there is no computation to do
                        # PCARBALLO modificacion del signo del monto.
                        # si tiene monto en debito o en credito, entonces es el caso comun,
                        # y no se modifica el calculo del signo con respecto al estandar.
                        # de lo contrario, chequea si el voucher tiene lineas de credito
                        # o lineas de debito, para modificar el signo en base a ese criterio.
                        # Se declara ademas una variable booleana "corregido", que sirve
                        # para verificar si el codigo ingreso o no a estos casos particulares.
                        # Se utiliza mas adelante para el calculo de la diferencia de cambio.
                        # ECHAVIANO 26/10 ACA ESTA EL PROBLEMA EN EL PAGO DEL AJUSTE > 0
                        if move_line['debit'] or move_line['credit']:
                            sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                            amount_currency = sign * (line.amount)
                        elif voucher.line_dr_ids or voucher.line_cr_ids and line.amount != 0:
                            if voucher.invoice_id and line.amount != 0:
                                if voucher.invoice_id.type in ('in_invoice','out_refund'):  # fact de proveedor o rectificativa de cliente
                                    sign = 1
                                elif voucher.invoice_id.type in ('in_refund'): # rect de proveedor
                                    corregido = True
                                    sign = (line.amount > 0) and -1 or 1
                                    ajuste_negativo = voucher.invoice_id.amount_total < 0 and True or False
                                    # if voucher.invoice_id.residual < 0:
                                    #     sign = (line.amount > 0) and -1 or 1
                                    # else:
                                    #     sign = (line.amount > 0) and 1 or -1
                                elif voucher.invoice_id.type in ('out_invoice'): # de cliente, dividido en un else por si es un caso diferente, puede agregarse en la condicion de arriba
                                    sign = (line.amount > 0) and -1 or 1
                                amount_currency = sign * (line.amount)
                    else:
                        # if the rate is specified on the voucher, it will be used thanks to the special keys in the context
                        # otherwise we use the rates of the system
                        amount_currency = currency_obj.compute(cr, uid, company_currency, line.move_line_id.currency_id.id, move_line['debit']-move_line['credit'], context=ctx)
                if line.amount == line.amount_unreconciled:
                    sign = voucher.type in ('payment', 'purchase') and -1 or 1
                    # PCARBALLO uso de la variable corregido.
                    # Si estamos en los casos particulares anteriormente descritos,
                    # entonces el signo cambia, para evitar que foreign_currency_diff de un valor no nulo.
                    if corregido:
                        sign = sign * -1
                        foreign_currency_diff = sign * line.move_line_id.amount_residual_currency + amount_currency
                    else:
                        foreign_currency_diff = (line.move_line_id.amount_residual_currency - abs(amount_currency))
                    # ECHAVIANO cambio
            # RAGU al momento de la aprobacion el comprobante no tiene apuntes contables.
            elif current_currency and current_currency != company_currency:
                    amount_currency = move_line.get('debit', 0) != 0 and line.amount or abs(line.amount) * -1
                    move_line['currency_id'] = current_currency

            # PCARBALLO eliminar creacion lineas con cero
            rec_ids = []
            context.update({'voucher_line': line})
            if amount_currency != 0 or amount != 0:
                if corregido and ajuste_negativo:
                    amount_currency = amount_currency * -1
                move_line['amount_currency'] = amount_currency
                voucher_line = move_line_obj.create(cr, uid, move_line, context=context)
                rec_ids = [voucher_line, line.move_line_id.id]
            if len(rec_ids) == 0:
                rec_ids = [line.move_line_id.id]
            # PCARBALLO fin eliminar creacion lineas con cero

            if not currency_obj.is_zero(cr, uid, voucher.company_id.currency_id, currency_rate_difference):
                # Change difference entry in company currency
                exch_lines = self._get_exchange_lines(cr, uid, line, move_id, currency_rate_difference, company_currency, current_currency, context=context)
                #009-Agregando flag
                exch_lines[0].update({'exchange_line':True})
                exch_lines[1].update({'exchange_line':True})
                new_id = move_line_obj.create(cr, uid, exch_lines[0],context)
                move_line_obj.create(cr, uid, exch_lines[1], context)
                rec_ids.append(new_id)

            if line.move_line_id and line.move_line_id.currency_id and not currency_obj.is_zero(cr, uid, line.move_line_id.currency_id, foreign_currency_diff):
                # Change difference entry in voucher currency
                move_line_foreign_currency = {
                    'journal_id': line.voucher_id.journal_id.id,
                    'period_id': line.voucher_id.period_id.id,
                    'name': _('change')+': '+(line.name or '/'),
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.voucher_id.partner_id.id,
                    'currency_id': line.move_line_id.currency_id.id,
                    'amount_currency': -1 * foreign_currency_diff,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': line.voucher_id.date,
                    #009- pasando campo en true cuando se genera tipo de cambio
                    'exchange_line': True,
                }
                new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context)
                rec_ids.append(new_id)
            if line.move_line_id.id:
                rec_lst_ids.append(rec_ids)
                rec_lst_voucher_lines.append(line)
        # irabaza => Update context by reference
        #           We need a dictionary, not a frozen dict!
        context.update({'rec_lst_voucher_lines': rec_lst_voucher_lines})
        return (tot_line, rec_lst_ids)
        #002-Fin

    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        """
        Returns a dict that contains new values and context

        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        def _remove_noise_in_o2m():
            """if the line is partially reconciled, then we must pay attention to display it only once and
                in the good o2m.
                This function returns True if the line is considered as noise and should not be displayed
            """
            if line.reconcile_partial_id:
                if currency_id == line.currency_id.id:
                    if line.amount_residual_currency <= 0:
                        return True
                else:
                    if line.amount_residual <= 0:
                        return True
            return False

        if context is None:
            context = {}
        context_multi_currency = context.copy()

        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        line_pool = self.pool.get('account.voucher.line')
        ajuste_redondeo_pool = self.pool.get('grp.ajuste.redondeo')

        #set default values
        default = {
            'value': {'line_dr_ids': [] ,'line_cr_ids': [] ,'pre_line': False,},
        }

        # drop existing lines
        # RAGU temporal comentado
        # move_lines_to_exlude = [x.move_line_id.id for x in line_pool.browse(cr, uid,line_pool.search(cr, uid, [('voucher_id.state','!=','cancel'),('reconcile','=',True)]))]
        line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])])

        for line in line_pool.browse(cr, uid, line_ids, context=context):
            if line.type == 'cr':
                default['value']['line_cr_ids'].append((2, line.id))
            else:
                default['value']['line_dr_ids'].append((2, line.id))
        # #drop existing lines
        # line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])]) or False
        # if line_ids:
        #     line_pool.unlink(cr, uid, line_ids)

        if not partner_id or not journal_id:
            return default

        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        currency_id = currency_id or journal.company_id.currency_id.id
        moneda = journal.currency or journal.company_id.currency_id
        ajuste_ids = ajuste_redondeo_pool.search(cr, 1, [('moneda', '=', moneda.id),('company_id','=',journal.company_id.id)])
        ajuste_obj = ajuste_ids and ajuste_redondeo_pool.browse(cr, 1, ajuste_ids[0]) or False

        total_credit = 0.0
        total_debit = 0.0
        account_type = None
        if context.get('account_id'):
            account_type = self.pool['account.account'].browse(cr, uid, context['account_id'], context=context).type
        if ttype == 'payment':
            if not account_type:
                account_type = 'payable'
            total_debit = price or 0.0
        else:
            total_credit = price or 0.0
            if not account_type:
                account_type = 'receivable'

        if not context.get('move_line_ids', False):
            ids = move_line_pool.search(cr, uid, [('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id)], context=context)
        else:
            ids = context['move_line_ids']
        invoice_id = context.get('invoice_id', False)
        company_currency = journal.company_id.currency_id.id
        move_lines_found = []

        #order the lines by most old first
        ids.reverse()
        account_move_lines = move_line_pool.browse(cr, uid, ids, context=context)
        #compute the total debit/credit and look for a matching open amount or invoice
        for line in account_move_lines:
            if _remove_noise_in_o2m():
                continue

            if invoice_id:
                if line.invoice.id == invoice_id:
                    #if the invoice linked to the voucher line is equal to the invoice_id in context
                    #then we assign the amount on that line, whatever the other voucher lines
                    move_lines_found.append(line.id)
            elif currency_id == company_currency:
                #otherwise treatments is the same but with other field names
                if line.amount_residual == price:
                    #if the amount residual is equal the amount voucher, we assign it to that voucher
                    #line, whatever the other voucher lines
                    move_lines_found.append(line.id)
                    break
                #otherwise we will split the voucher amount on each line (by most old first)
                total_credit += line.credit or 0.0
                total_debit += line.debit or 0.0
            elif currency_id == line.currency_id.id:
                if line.amount_residual_currency == price:
                    move_lines_found.append(line.id)
                    break
                total_credit += line.credit and line.amount_currency or 0.0
                total_debit += line.debit and line.amount_currency or 0.0

        remaining_amount = price
        #voucher line creation
        # RAGU ajustes varios para gestión de pagos
        for line in account_move_lines:
            if _remove_noise_in_o2m():
                continue
            to_currency = currency_id
            from_currency = line.currency_id and line.currency_id.id or company_currency
            if to_currency == from_currency:
                amount_original = abs(line.amount_currency)
                amount_unreconciled = abs(line.amount_residual_currency)
                # amount_unreconciled = abs(line.amount_residual_currency_unround)
            else:
                amount_original = currency_pool.compute(cr, uid, company_currency, to_currency,
                                                        line.debit or line.credit or 0.0,
                                                        context=context_multi_currency)
                amount_unreconciled = currency_pool.compute(cr, uid, from_currency, to_currency,
                                                            abs(line.amount_residual_currency_unround),
                                                            context=context_multi_currency)

                # amount_unreconciled = currency_pool.compute(cr, uid, from_currency, to_currency,
                #                                             abs(line.fixed_amount_currency_unround),
                #                                             context=context_multi_currency)
                # amount_unreconciled = currency_pool.compute(cr, uid, from_currency, to_currency,
                #                                             abs(line.amount_residual_currency),
                #                                             context=context_multi_currency)
            #PCARBALLO : Se agrega control para el caso en que el monto sea cercano a cero.
            line_currency_id = line.currency_id and line.currency_id.id or company_currency
            type_credit = line.credit and 'dr' or 'cr'
            if not line.credit and not line.debit and abs(line.amount_currency):
                #type_credit = line.amount_currency < 0 and 'cr' or 'dr'
                #context.update({'credit_debit_cero':True})
                type_credit = line.amount_currency < 0 and 'dr' or 'cr'
            origin_voucher_id = self.pool.get('account.voucher').search(cr, 1, [('move_id', '=', line.move_id.id)], context=context)

            rs = {
                'name':line.move_id.name,
                'type': type_credit,
                'move_line_id':line.id,
                'account_id':line.account_id.id,
                'amount_original': amount_original,
                'amount_original_move_line': amount_original,
                'amount': (line.id in move_lines_found) and min(abs(remaining_amount), amount_unreconciled) or 0.0,
                # 'amount': amount_unreconciled,
                'date_original':line.date,
                'date_due':line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'currency_id': line_currency_id,
                'origin_voucher_id': origin_voucher_id[0] if origin_voucher_id else False,
                'operating_unit_id': line.operating_unit_id.id,
                'invoice_id':False,
                'supplier_invoice_number':False
            }
            #PCARBALLO
            remaining_amount -= rs['amount']
            #in case a corresponding move_line hasn't been found, we now try to assign the voucher amount
            #on existing invoices: we split voucher amount by most old first, but only for lines in the same currency
            if not move_lines_found:
                if currency_id == line_currency_id:
                    if line.credit:
                        amount = min(amount_unreconciled, abs(total_debit))
                        rs['amount'] = 0
                        total_debit -= amount
                    else:
                        amount = min(amount_unreconciled, abs(total_credit))
                        rs['amount'] = 0   #RAGU las lineas de creditos deben iniciarse con monto 0
                        total_credit -= amount

            # 004-Inicio cambiar esto por un chequeo de diferencia
            # menor que la configurada en ajuste por redondeo
            difference = rs['amount_unreconciled'] - rs['amount']
            if ajuste_obj and rs['amount']:
                if abs(difference) < ajuste_obj.ajuste_redondeo:
                    if difference > 0:
                        rs['amount'] += difference
                    rs['reconcile'] = True
            elif currency_pool.is_zero(cr, uid, moneda, difference): #RAGU si no hay ajuste de redondeo config
                rs['reconcile'] = True
            # 004-Fin

            if rs['type'] == 'cr':
                default['value']['line_cr_ids'].append(rs)
            else:
                default['value']['line_dr_ids'].append(rs)

            if len(default['value']['line_cr_ids']) > 0:
                default['value']['pre_line'] = 1
            elif len(default['value']['line_dr_ids']) > 0:
                default['value']['pre_line'] = 1
            default['value']['writeoff_amount'] = self._compute_writeoff_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)
        return default

    #002-Inicio
    # TODO GAP 247 Spring 4: Cambiando la fecha y periodo a las lineas de los asientos generados
    def first_move_line_get(self, cr, uid, voucher_id, move_id, company_currency, current_currency, context=None):
        '''
        Return a dict to be use to create the first account move line of given voucher.

        :param voucher_id: Id of voucher what we are creating account_move.
        :param move_id: Id of account move where this line will be added.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: mapping between fieldname and value of account move line to create
        :rtype: dict
        '''
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        debit = credit = 0.0
        # TODO: is there any other alternative then the voucher type ??
        # ANSWER: We can have payment and receipt "In Advance".
        # TODO: Make this logic available.
        # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt

        if voucher.type in ('purchase', 'payment'):
            credit = voucher.paid_amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            debit = voucher.paid_amount_in_company_currency
        if debit < 0: credit = -debit; debit = 0.0
        if credit < 0: debit = -credit; credit = 0.0

        #sign = debit - credit < 0 and -1 or 1
        #PCARBALLO si no tiene monto de credito ni debito
        # entonces estamos en el caso de las lineas con decimales
        sign = 1
        if credit or debit:
            sign = debit - credit < 0 and -1 or 1
        elif voucher.invoice_id:
            if voucher.invoice_id.type in ('in_invoice','out_refund'):  # fact de proveedor o rectificativa de cliente
                sign = (voucher.amount > 0) and -1 or 1
                # sign = -1
            elif voucher.invoice_id.type in ('in_refund','out_invoice'): # rect de proveedor y de cliente
                sign = (voucher.amount > 0) and -1 or 1
                # if voucher.invoice_id.residual < 0:
                #     sign = (line.amount > 0) and -1 or 1
                # else:
                #     sign = (line.amount > 0) and 1 or -1
        # ECHAVIANO cambiar los signos cuando no hay credito o debito segun el tipo de factura

        period_id = voucher.period_id.id
        if voucher.entry_date:
            period = self.pool.get('account.period').find(cr, uid, voucher.entry_date, context=context)
            if period:
                period_id = period[0]
        #set the first line of the voucher
        move_line = {
                # 'amount_currency': company_currency <> current_currency and sign * voucher.amount or 0.0,
                'name': voucher.name or '/',
                'debit': debit,
                'credit': credit,
                'account_id': voucher.account_id.id,
                'move_id': move_id,
                'journal_id': voucher.journal_id.id,
                'period_id': period_id,#todo para que tome el periodo del asiento
                'partner_id': voucher.partner_id.id,
                'currency_id': company_currency <> current_currency and  current_currency or False,
                #'amount_currency': company_currency <> current_currency and sign * voucher.amount or 0.0,
                'amount_currency': (sign * abs(voucher.amount)
                    if company_currency != current_currency else 0.0),
                'date': voucher.entry_date,#TODO Spring 4 Cambiando el date de las lineas
                'date_maturity': voucher.date_due

            }
        return move_line
        #002-Fin

    # TODO: GAP 247 Spring 4: Redefiniendo este metodo para coger la fecha asiento como fecha del asiento
    def account_move_get(self, cr, uid, voucher_id, context=None):
        '''
        This method prepare the creation of the account move related to the given voucher.

        :param voucher_id: Id of voucher for which we are creating account_move.
        :return: mapping between fieldname and value of account move to create
        :rtype: dict
        '''
        if context is None:
            context = {}
        seq_obj = self.pool.get('ir.sequence')
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        if voucher.number:
            name = voucher.number
            ## Si existe un movimiento con este name ir agregando /1 luego /2 ...
            pos = name.rfind('/')
            try:
                if pos != -1 and pos > 8 and name[(pos+1):]==str(int(name[(pos+1):])):
                    name = name[:pos]
            except: # ignore
                pass
            m_ids = self.pool.get('account.move').search(cr, uid, [('name','ilike',name)], order='name asc', context=context)
            if m_ids:
                move_name = self.pool.get('account.move').read(cr, uid, m_ids[-1], ['name'], context=context)['name']
                if move_name == name:
                    name += '/1'
                else:
                    pos = move_name.rfind('/')
                    try:
                        if pos != -1:
                            last = int(move_name[(pos+1):])
                            if move_name[(pos+1):]==str(last):
                                name += '/%s' % (last+1)
                    except: # ignore
                        pass
            ##
        elif voucher.journal_id.sequence_id:
            if not voucher.journal_id.sequence_id.active:
                raise osv.except_osv(_('Configuration Error !'),
                    _('Please activate the sequence of selected journal !'))
            c = dict(context)
            c.update({'fiscalyear_id': voucher.period_id.fiscalyear_id.id})
            name = seq_obj.next_by_id(cr, uid, voucher.journal_id.sequence_id.id, context=c)
        else:
            raise osv.except_osv(_('Error!'),
                        _('Please define a sequence on the journal.'))
        if not voucher.reference:
            ref = name.replace('/','')
        else:
            ref = voucher.reference

        date = voucher.date
        period_id = voucher.period_id.id
        if voucher.entry_date:
            date = voucher.entry_date
            period = self.pool.get('account.period').find(cr, uid, date, context=context)
            if period:
                period_id = period[0]

        move = {
            'name': name,
            'journal_id': voucher.journal_id.id,
            'narration': voucher.narration,
            'date': date,
            'ref': ref,
            'period_id': period_id,
        }
        return move


    # TODO RAGU: En caso de decidir usar los _new eliminar este metodo
    def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
        vals = {'value': {}}
        if not journal_id:
            return vals
        # currency_obj = self.pool.get('res.currency')
        if context is None:
            context = {}
        journal_pool = self.pool.get('account.journal')
        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        if ttype in ('sale', 'receipt'):
            account_id = journal.default_debit_account_id
        elif ttype in ('purchase', 'payment'):
            account_id = journal.default_credit_account_id
        else:
            account_id = journal.default_credit_account_id or journal.default_debit_account_id
        tax_id = False
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0].id

        if ttype in ('sale', 'purchase'):
            vals = self.onchange_price(cr, uid, ids, line_ids, tax_id, partner_id, context)
            vals['value'].update({'tax_id':tax_id,'amount': amount})
        # currency_id = False
        if journal.currency:
            currency_id = journal.currency.id
        else:
            currency_id = journal.company_id.currency_id.id

        period_ids = self.pool['account.period'].find(cr, uid, dt=date, context=dict(context, company_id=company_id))
        vals['value'].update({
            'currency_id': currency_id,
            'payment_rate_currency_id': currency_id,
            'period_id': period_ids and period_ids[0] or False
        })
        # RAGU procedimiento reemplazado por conversion de moneda
        #in case we want to register the payment directly from an invoice, it's confusing to allow to switch the journal
        #without seeing that the amount is expressed in the journal currency, and not in the invoice currency. So to avoid
        #this common mistake, we simply reset the amount to 0 if the currency is not the invoice currency.
        if context.get('payment_expected_currency') and currency_id != context.get('payment_expected_currency'):
            if context.get('invoice_id'):
                invoice_id = self.pool.get('account.invoice').browse(cr, uid, context['invoice_id'])
                topay_amount = invoice_id.amount_total - (abs(sum(invoice_id.payment_ids.mapped('fixed_amount_currency_unround'))) or abs(sum(invoice_id.payment_ids.mapped('amount_currency_unround'))))
                # topay_amount = invoice_id.total_pesos_no_round - invoice_id.amount_total_paid
                # topay_amount_no_round = invoice_id.move_id
                # topay_amount_no_round = currency_obj.compute(cr, uid, journal.company_id.currency_id.id, context.get('payment_expected_currency'), topay_amount,round=False)
                # if currency_obj.is_zero(cr, uid, currency_obj.browse(cr,uid,context.get('payment_expected_currency')), topay_amount_no_round-context.get('default_amount') or amount):
                amount = topay_amount
            amount = self.pool.get('res.currency').compute(cr, uid, context.get('payment_expected_currency'),
                                                           currency_id,
                                                           amount)
            vals['value']['amount'] = amount
        elif context.get('default_amount'):
            amount = context['default_amount']
            vals['value']['amount'] = context['default_amount']
        else:
            vals['value']['amount'] = 0
            amount = 0



        if partner_id:
            res = self.onchange_partner_id(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context)
            for key in res.keys():
                vals[key].update(res[key])

            # _amount = 0
            # for line in res['value']['line_cr_ids']:
            #     if isinstance(line, dict):
            #         _amount += line['amount']
            # for line in res['value']['line_dr_ids']:
            #     if isinstance(line, dict):
            #         _amount += line['amount']

            # vals['value']['amount'] = amount
        return vals

grp_facturas_account_voucher()
