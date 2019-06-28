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
import re
import openerp.addons.decimal_precision as dp
import time
from decimal import Decimal, ROUND_HALF_DOWN
from openerp import SUPERUSER_ID

class account_invoice_ret_paid(osv.osv):

    def _compute_ret_lines(self, cr, uid, ids, name, args, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            result[invoice.id] = []
            if not invoice.invoice_ret_lines or not invoice.state == 'paid':
                continue
            lines = []
            if invoice.invoice_ret_lines:
                # retenciones de lineas 13/04
                for m in invoice.invoice_ret_line_ids:
                    # lines.append(m.move_payment_id.id)
                    for move_line in m.move_payment_line:
                        lines.append(move_line.id)
                # globales 13/04
                for m2 in invoice.invoice_ret_global_line_ids:
                    # lines.append(m.move_payment_id.id)
                    if m2.move_payment_id:
                        lines.append(m2.move_payment_id.id)
                #004 retenciones irpf 04/12
                for m3 in invoice.invoice_ret_irpf_lines:
                    # lines.append(m.move_payment_id.id)
                    # corrgiendo errores 04/12
                    if m3.move_payment_id:
                        lines.append(m3.move_payment_id.id)
            result[invoice.id]= lines
        return result

    # Variante 1
    # def _get_total_payment_amount_old(self,cr,uid,ids,fieldname,args,context=None):
    #     res = {}
    #     ids = [ids] if not isinstance(ids,list) else ids
    #     for id in ids:
    #         i = self.read(cr, uid, id, ['payment_ids'])
    #         total_paid = 0.0
    #         if i['payment_ids']:
    #             account_move_line_obj = self.pool.get('account.move.line')
    #             # payment_ids = i['payment_ids'].sort()
    #             payment_ids = sorted(i['payment_ids'], key=int, reverse=True)
    #             pay_ids = account_move_line_obj.browse(cr, uid, payment_ids)
    #             # Cambiado forma de calculo de suma - solo creditos
    #             for move_line in pay_ids:
    #                 if move_line.reconcile_partial_id.line_partial_ids:
    #                     continue
    #                 if not move_line.exchange_line:
    #                     total_paid += move_line.debit
    #         res[id] = total_paid
    #     return res

    # Variante 2 - Buscando el move
    def _get_total_payment_amount(self,cr,uid,ids,fieldname,args,context=None):
        res = {}
        ids = [ids] if not isinstance(ids,list) else ids
        for id in ids:
            i = self.read(cr, uid, [id], ['payment_ids'])[0]
            total_paid = 0.0
            if i['payment_ids']:
                account_move_line_obj = self.pool.get('account.move.line')
                account_move_obj = self.pool.get('account.move')
                # payment_ids = i['payment_ids'].sort()
                payment_ids = sorted(i['payment_ids'], key=int, reverse=True)
                pay_ids = account_move_line_obj.browse(cr, uid, payment_ids)
                move_ids = []
                # Cambiado forma de calculo de suma - solo creditos
                for move_line in pay_ids:
                    if move_line.move_id.id not in move_ids:
                        move_ids.append(move_line.move_id.id)
                if len(move_ids):
                    for move in account_move_obj.browse(cr, uid, move_ids):
                        for move_line2 in move.line_id:
                            if not move_line2.exchange_line:
                                # total_paid += move_line.debit
                                # Cambiado a sumar el credito pq en realidad es lo que se saca del banco 31/03
                                total_paid += move_line2.credit
            res[id] = total_paid
        return res

    _inherit = 'account.invoice'
    _columns = {
        'payment_ret_ids': fields.function(_compute_ret_lines, method=True, relation='account.move.line', type="many2many", string='Retention Payments'),
        #002 - Inicio
        'amount_total_paid': fields.function(_get_total_payment_amount, string='Monto total pagado', digits_compute=dp.get_precision('Account')),
    }

    def find_move_line_related_payment(self, cr, uid, id, context=None):
        i = self.read(cr, uid, [id], ['move_id', 'payment_ids'])[0]
        move_ids = [] # ones that we will need to remove
        if i['move_id']:
            move_ids.append(i['move_id'][0])
        if i['payment_ids']:
            account_move_line_obj = self.pool.get('account.move.line')
            # payment_ids = i['payment_ids'].sort()
            payment_ids = sorted(i['payment_ids'], key=int, reverse=True)
            pay_ids = account_move_line_obj.browse(cr, uid, payment_ids)
            for move_line in pay_ids:
                if move_line.reconcile_partial_id and move_line.reconcile_partial_id.line_partial_ids:
                    return False
                else:
                    # si los movimientos asociados al pago estan conciliados, elimino el pago y la conciliacion
                    if move_line.reconcile_id:
                        return move_line
        return False

    #001 - Devolver cantidad en pagos
    def get_payment_amount(self, cr, uid, id, context=None):
        i = self.read(cr, uid, [id], ['move_id', 'payment_ids'])[0]
        move_ids = [] # ones that we will need to remove
        total_paid = 0.0
        if i['move_id']:
            move_ids.append(i['move_id'][0])
        if i['payment_ids']:
            account_move_line_obj = self.pool.get('account.move.line')
            # payment_ids = i['payment_ids'].sort()
            payment_ids = sorted(i['payment_ids'], key=int, reverse=True)
            pay_ids = account_move_line_obj.browse(cr, uid, payment_ids)
            for move_line in pay_ids:
                if move_line.reconcile_partial_id.line_partial_ids:
                        raise osv.except_osv(_('Error!'), _('You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))
                if not move_line.exchange_line:
                    total_paid += move_line.debit

        return total_paid
    #001 - End total cantidad pago

    # despues que se paga la retencion, se crea el asiento de retenciones contra caja/banco
    # pagando la retencion, se crea el asiento correspondiente a las retenciones
    def action_move_retention_create(self, cr, uid, ids, context=None):
        '''
        Create retention moves for each item
        Se tiene en cuenta el multicurrency, chaviano
        '''
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        period_obj = self.pool.get('account.period')
        move_line_pool = self.pool.get('account.move.line')

        move_ids = []
        for invoice in self.browse(cr, uid, ids, context=context):
            # comprobacion si es fondo rotatorio en Integracion SIIF
            # es fondo rotatorio, continuar ----

            # comprobacion, si no hay retenciones, no hacer nada
            if not invoice.amount_total_retention > 0 or not invoice.invoice_ret_lines:
                continue
            #14/10 buscar diario, cuenta y periodo
            company = invoice.company_id
            journal_retention_id = company.retention_journal_id
            if not journal_retention_id:
                raise osv.except_osv(_('Insufficient Configuration!'),_("You should configure the 'Retention Journal' in the accounting settings, "
                                                                        "to manage automatically the booking of accounting entries related to retention payments."))
                # raise osv.except_osv(_('Insufficient Configuration!'),_("You must con Debe configurar el diario para retenciones."))

            ctx = dict(context, account_period_prefer_normal=True)
            period_ids = period_obj.find(cr, uid, invoice.date_invoice, context=ctx)
            period_id = period_ids and period_ids[0] or False
            if not period_id:
                raise osv.except_osv(_('Error!'),_("No period found for the invoice date %s." % (invoice.date_invoice,)))
                # raise osv.except_osv(_('Error!'),_("No hay período definido para la fecha de la factura %s." % (invoice.date_invoice,)))
            period = period_obj.browse(cr, uid, period_id)
            data_pay_ret = {'journal_retention_id': journal_retention_id, 'account_id': journal_retention_id.default_credit_account_id or journal_retention_id.default_debit_account_id,
                            'period_id': period, 'date': invoice.date_invoice}
            if not invoice.payment_ids:
                raise osv.except_osv(_('Error!'),_("No payments found for the selected invoice."))
                # raise osv.except_osv(_('Error!'),_("No hay pagos asociados a la factura seleccionada."))
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx.update({'date': invoice.date_invoice})

            company_currency = self.pool['res.company'].browse(cr, uid, invoice.company_id.id).currency_id.id

            # find the payments
            pay_move_line = self.find_move_line_related_payment(cr, uid, invoice.id, context=context)
            # modificacion para test de bug en exterior
            if pay_move_line and invoice.amount_total_retention > 0 and invoice.invoice_ret_lines:
                # Create the account move record.
                # data_record = self.account_move_create(cr, uid, pay_move_line, data_pay_ret, context=context)
                # if data_record:
                move_id = move_pool.create(cr, uid, self.account_move_create(cr, uid, pay_move_line, data_pay_ret, context=context), context=context)
                # Get the name of the account_move just created
                name = move_pool.browse(cr, uid, move_id, context=context).name
                ref = move_pool.browse(cr, uid, move_id, context=context).ref

                # Original -- Buscar si hay diferencia de moneda de pago en la moneda base cambio 18/08
                # diff_currency_p = pay_move_line.journal_id.currency and pay_move_line.journal_id.currency.id <> company_currency
                # payment_currency = pay_move_line.journal_id.currency and pay_move_line.journal_id.currency.id or False
                # Cambio 15/10
                # Buscar si hay diferencia de moneda de pago en la moneda base cambio 15/10
                diff_currency_p = journal_retention_id.currency and journal_retention_id.currency.id <> company_currency and True or False
                payment_currency = journal_retention_id.currency and journal_retention_id.currency.id or False

                # Buscar si hay diferencia de moneda de la factura con moneda base  18/08
                diff_currency_inv = invoice.currency_id.id <> company_currency or False

                # Buscar diferencia de factura y pago
                diff_currency_pay = payment_currency and invoice.currency_id.id <> payment_currency

                # Create the first line of the order.
                # Al debito porque es el pago de proveedor  18/08, cambiado a debito
                                   # DIF CAMBIO PAGO-BASE, MONEDA FACTURA ,   MONEDA PAGO ,   MONEDA COMPAÑIA   DIF CAMBIO FACT-BASE   DIF CAMBIO PAGO-FACT
                dif_currency_arr = [diff_currency_p, invoice.currency_id.id, payment_currency, company_currency, diff_currency_inv, diff_currency_pay]
                move_line_id = move_line_pool.create(cr, uid, self.first_move_line_get_ret(cr,uid, pay_move_line, data_pay_ret, move_id, invoice.amount_total_retention, dif_currency_arr, context), context)
                move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
                line_total = move_line_brw.debit - move_line_brw.credit
                                  # DIF CAMBIO FACT  , MONEDA FACTURA,   MONEDA COMPAÑIA
                dif_currency_arr2 = [diff_currency_inv, invoice.currency_id.id, company_currency]
                # Create one moves lines per credit to amount total
                # Buscar las lineas de retenciones
                line_total, amount_currency, credit_ret_lines = self.move_lines_get_credit(cr, uid, invoice, ref, dif_currency_arr2, context)
                # Crear los move.lines a partir de la informacion de los datos de las retenciones
                rec_moves_lines_ids = self.create_second_moves(cr, uid, line_total, credit_ret_lines, move_id, pay_move_line, data_pay_ret, context)
                move_pool.post(cr, uid, [move_id], context=ctx)
                move_ids.append(move_id)
        if move_ids:
            self._log_event(cr, uid, ids, 1.0, _("Retention Paid Move Line Create."))
        return True

    def account_move_create(self, cr, uid, pay_move_line, data_pay_ret,context=None):
        '''
        Este metodo crea el move para el pago de las retenciones.
        '''
        seq_obj = self.pool.get('ir.sequence')
        if data_pay_ret['journal_retention_id'].sequence_id:
            if not data_pay_ret['journal_retention_id'].sequence_id.active:
                raise osv.except_osv(_('Configuration Error !'),_('Please activate the sequence of selected journal !'))
            c = dict(context)
            c.update({'fiscalyear_id': data_pay_ret['period_id'].fiscalyear_id.id})
            name = seq_obj.next_by_id(cr, uid, data_pay_ret['journal_retention_id'].sequence_id.id, context=c)
        else:
            raise osv.except_osv(_('Error!'),_('Please define a sequence on the journal.'))
        if name:
            # ref = name.replace('(<[^>]+/>)','')
            # ref = name.replace('/','')
            ref = re.sub("[<>'\"/;]","", name)
        else:
            ref = pay_move_line.ref
        move = {
            'name':str(name),
            'journal_id': data_pay_ret['journal_retention_id'].id,
            # 'date': data_pay_ret['date'],
            # 'period_id': data_pay_ret['period_id'].id,
            'date': pay_move_line.date,
            'ref': ref,
            'period_id': pay_move_line.period_id.id,
        }
        return move

    # Cambio de este metodo completamente 18/08, ademas cambio del signo, era el credito y se pasa al debito
    def first_move_line_get_ret(self, cr, uid, pay_move_line, data_pay_ret, move_id, debit_total_ret, dif_currency_arr, context=None):
        cur_obj = self.pool.get('res.currency')
        # DIF CAMBIO PAGO-BASE,    MONEDA FACTURA  ,  MONEDA PAGO  ,  MONEDA COMPAÑIA,   DIF CAMBIO FACT-BASE,   DIF CAMBIO PAGO-FACT
        # dif_currency_arr[0]      [1]                [2]              [3]                 [4]               [5]
        ctx = context.copy()
        ctx.update({'date': data_pay_ret['date']})
        # ctx.update({'date': pay_move_line.date})
        sign = -1 # (-) Al credito, (+) Al debito
        # MONEDA Factura es DIVISA
        if dif_currency_arr[4]:
            # DIF CAMBIO   ,  MONEDA FACTURA   ,   MONEDA PAGO  ,  MONEDA COMPAÑIA
            amount_currency = cur_obj.compute(cr, uid, dif_currency_arr[1], dif_currency_arr[3], debit_total_ret, context=ctx)
            # si tiene diferencia de cambio, tomara el calculado, sino tomara el que viene
            credit = dif_currency_arr[4] and amount_currency or debit_total_ret
            debit = 0.0  # cambiado 15/10 al credito el valor
            #set the first line of the pay
            if dif_currency_arr[5]:
                move_line = {
                    'name': pay_move_line.name or '/',
                    'debit': debit,
                    'credit': credit,
                    'account_id': data_pay_ret['journal_retention_id'].default_credit_account_id.id or False,  # cuenta de gasto
                    # 'account_id': pay_move_line.journal_id.default_credit_account_id.id or False,  # cuenta de gasto
                    # 'account_id': pay_move_line.account_id.id or False,  # cuenta de gasto
                    'move_id': move_id,
                    'journal_id': data_pay_ret['journal_retention_id'].id,
                    # 'journal_id': pay_move_line.journal_id.id,
                    'period_id': pay_move_line.period_id.id,
                    'partner_id': pay_move_line.partner_id.id,
                    'price': 1,  # price es informacion del producto, es opcional
                    # 'amount_currency': dif_currency_arr[4] \
                    #             and debit_total_ret or False, # es positivo
                    # 'currency_id': dif_currency_arr[4] \
                    #             and dif_currency_arr[1] or False,
                    'date': pay_move_line.date_created,
                    'date_maturity': pay_move_line.date_created
                    }
            elif dif_currency_arr[0]:
                move_line = {
                        'name': pay_move_line.name or '/',
                        'debit': debit,
                        'credit': credit,
                        'account_id': data_pay_ret['journal_retention_id'].default_credit_account_id.id or False,  # cuenta de gasto
                        # 'account_id': pay_move_line.journal_id.default_credit_account_id.id or False,  # cuenta de gasto
                        # 'account_id': pay_move_line.account_id.id or False,  # cuenta de gasto
                        'move_id': move_id,
                        'journal_id': data_pay_ret['journal_retention_id'].id,
                        # 'journal_id': pay_move_line.journal_id.id,
                        'period_id': pay_move_line.period_id.id,
                        'partner_id': pay_move_line.partner_id.id,
                        'price': 1,  # price es informacion del producto, es opcional
                        'amount_currency': dif_currency_arr[4] \
                                    and sign * debit_total_ret or False, # positivo o negativo segun el signo
                        'currency_id': dif_currency_arr[4] \
                                    and dif_currency_arr[1] or False,
                        'date': pay_move_line.date_created,
                        'date_maturity': pay_move_line.date_created
                }
            else: # cambio para que cuando el diario es en pesos no agregue el currency 31/10
                move_line = {
                        'name': pay_move_line.name or '/',
                        'debit': debit,
                        'credit': credit,
                        'account_id': data_pay_ret['journal_retention_id'].default_credit_account_id.id or False,  # cuenta de gasto del diario de banco
                        'move_id': move_id,
                        'journal_id': data_pay_ret['journal_retention_id'].id,
                        'period_id': pay_move_line.period_id.id,
                        'partner_id': pay_move_line.partner_id.id,
                        'price': 1,  # price es informacion del producto, es opcional
                        'amount_currency': False, # positivo o negativo segun el signo
                        'currency_id': False,
                        'date': pay_move_line.date_created,
                        'date_maturity': pay_move_line.date_created
                }
        # MONEDA pago DIVISA Y MONEDA FACTURA ES BASE, convertir a DIVISA
        elif dif_currency_arr[0]:
            # DIF CAMBIO   ,  MONEDA FACTURA   ,   MONEDA PAGO  ,  MONEDA COMPAÑIA
            amount_currency = cur_obj.compute(cr, uid, dif_currency_arr[1], dif_currency_arr[2], debit_total_ret, context=context)
            sign = 1 and dif_currency_arr[5] or -1
            # si tiene diferencia de cambio, tomara el calculado, sino tomara el que viene
            # credit = amount_currency or credit_total
            #set the first line of the pay
            move_line = {
                    'name': pay_move_line.name or '/',
                    'debit': 0.0, # cambio de debito y credito
                    'credit': debit_total_ret,
                    'account_id': data_pay_ret['journal_retention_id'].default_credit_account_id.id or False,  # cuenta de gasto
                    # 'account_id': pay_move_line.journal_id.default_credit_account_id.id or False,  # cuenta de gasto
                    # 'account_id': pay_move_line.account_id.id or False,  # cuenta de gasto
                    'move_id': move_id,
                    # 'journal_id': pay_move_line.journal_id.id,
                    'journal_id': data_pay_ret['journal_retention_id'].id,
                    'period_id': pay_move_line.period_id.id,
                    'partner_id': pay_move_line.partner_id.id,
                    'price': 1,  # price es informacion del producto, es opcional
                    'amount_currency': dif_currency_arr[0] \
                                and sign * amount_currency or False,
                    'currency_id': dif_currency_arr[0] \
                                and dif_currency_arr[2] or False,
                    'date': pay_move_line.date_created,
                    'date_maturity': pay_move_line.date_created
                }
        else:
            # TODO es moneda base
            #set the first line of the pay
            move_line = {
                    'name': pay_move_line.name or '/',
                    'debit': 0.0, # cambio al debito
                    'credit': debit_total_ret,
                    'account_id': data_pay_ret['journal_retention_id'].default_credit_account_id.id or False,  # cuenta de gasto
                    # 'account_id': pay_move_line.journal_id.default_credit_account_id.id or False,  # cuenta de gasto
                    # 'account_id': pay_move_line.account_id.id or False,  # cuenta de gasto
                    'move_id': move_id,
                    'journal_id': data_pay_ret['journal_retention_id'].id,
                    # 'journal_id': pay_move_line.journal_id.id,
                    'period_id': pay_move_line.period_id.id,
                    'partner_id': pay_move_line.partner_id.id,
                    # 'price': 1,  # price es informacion del producto, es opcional
                    'amount_currency': False,
                    'currency_id': False,
                    'date': pay_move_line.date_created,
                    'date_maturity': pay_move_line.date_created
                }
        return move_line

    #01- para cuando se paga la factura de proveedor, importe positivo para afectacion por el debito old
    #02- para cuando se paga la factura de proveedor, importe negativo para afectacion por al credito, se cambia 20/08
    #03- para cuando se paga la factura de proveedor, importe positivo para afectacion por al debido, se cambia 15/10
    # def move_lines_get_credit(self, cr, uid, inv, ref, dif_currency_arr, pay_move_line, context=None):
    def move_lines_get_credit(self, cr, uid, inv, ref, dif_currency_arr, context=None):
        res = []
        account_ret_line_obj = self.pool.get('account.retention.line')
        account_global_ret_line_obj = self.pool.get('account.global.retention.line')
        #004 Retenciones IRPF
        obj_siif_retline = self.pool.get('account.retention.line.irpf')
        cur_obj         = self.pool.get('res.currency')
        amount_ret      = 0.0
        amount_currency = 0.0
        invoice_id = inv.id
        ctx = context.copy()
        # ctx.update({'date': pay_move_line.date}) # cambio 14/10 fecha de pago del dia de la factura
        ctx.update({'date': inv.date_invoice})
        sign = 1 #Inicializacion de signo, el pago de retencion siempre es positivo, va al credito
        #En la factura, la retencion va a debito, por tanto debe ser negativo el amount_currency   -1   15/10
        acc_ret_line_ids = account_ret_line_obj.search(cr, uid, [('invoice_id','=',invoice_id),('amount_ret','>',0)], order='id')
        if acc_ret_line_ids:
            def amount_retention_calc(ret, base_retax=0, base_ret_line=0):
                        if ret.base_compute == 'ret_tax':
                            if base_retax:
                                return base_retax * ret.percent / 100
                        elif ret.base_compute == 'ret_line_amount':
                            if base_ret_line:
                                return base_ret_line * ret.percent / 100
                        else:
                            return 0.0
            for retline in account_ret_line_obj.browse(cr, uid, acc_ret_line_ids,context=context):
                for retention_related in retline.retention_line_ret_ids:
                    t_amount_ret = amount_retention_calc(retention_related, retline.base_retax,retline.base_ret_line)
                    diff_currency_p = dif_currency_arr[0]
                    if diff_currency_p:                         # from  DIVISA    to MN BASE
                        total_currency = cur_obj.compute(cr, uid, dif_currency_arr[1], dif_currency_arr[2], t_amount_ret, context=ctx)

                    debit = dif_currency_arr[0] and total_currency or amount_retention_calc(retention_related, retline.base_retax,retline.base_ret_line)

                    ret_name = ''
                    if retention_related.name:
                        ret_name = re.sub("[<>'\"/;]","", retention_related.name)
                    amount_ret      += debit or 0.0
                    amount_currency += dif_currency_arr[0] and t_amount_ret or 0.0

                    res.append({
                        'type':'retencion',
                        'name': '%s-%s'%(_('Payment'), ret_name),
                        'date_maturity': inv.date_due or False,
                        'currency_id':diff_currency_p \
                                    and inv.currency_id.id or False,
                        'amount_currency': diff_currency_p \
                                    and sign * t_amount_ret or False,  # cambio de signo
                        'ref': ref,
                        'account_id': retention_related.account_id.id,
                        'amount': debit,
                        'ret_line_id': retline.id,
                        'price': 1
                    })

        # add 13/04 payment to global retention
        # acc_gbl_ret_line_ids = account_global_ret_line_obj.search(cr, uid, [('invoice_id','=',invoice_id),('amount_ret','>',0)], order='id')
        acc_gbl_ret_line_ids = account_global_ret_line_obj.search(cr, uid, [('invoice_id','=',invoice_id)], order='id')
        if acc_gbl_ret_line_ids:
            for ret_global_line in account_global_ret_line_obj.browse(cr, uid, acc_gbl_ret_line_ids,context=context):
                if ret_global_line.amount_ret > 0:
                    t_amount_ret = ret_global_line.amount_ret
                    diff_currency_p = dif_currency_arr[0]
                    if diff_currency_p:                         # from  DIVISA    to MN BASE
                        total_currency = cur_obj.compute(cr, uid, dif_currency_arr[1], dif_currency_arr[2], t_amount_ret, context=ctx)

                    debit = dif_currency_arr[0] and total_currency or ret_global_line.amount_ret
                    ret_name = ''
                    if ret_global_line.name:
                        ret_name = re.sub("[<>'\"/;]","", ret_global_line.name)
                    amount_ret      += debit or 0.0
                    amount_currency += dif_currency_arr[0] and t_amount_ret or 0.0

                    res.append({
                        'type':'retencion',
                        'name': '%s-%s'%(_('Payment'), ret_name),
                        'date_maturity': inv.date_due or False,
                        'currency_id':diff_currency_p \
                                    and inv.currency_id.id or False,
                        'amount_currency': diff_currency_p \
                                    and sign * t_amount_ret or False, # signo * monto
                        'ref': ref,
                        'account_id': ret_global_line.account_id.id,
                        'amount': debit,
                        'ret_gbl_line_id': ret_global_line.id,
                        'price': 1
                    })
        #004 Retenciones IRPF 04/12
        acc_ret_line_irpf_ids = obj_siif_retline.search(cr, uid, [('invoice_id','=',invoice_id),('amount_ret','>',0)], order='id')
        if acc_ret_line_irpf_ids:
            for line_ret_irpf in obj_siif_retline.browse(cr, uid, acc_ret_line_irpf_ids, context=context):
                t_amount_ret = line_ret_irpf.amount_ret
                diff_currency_p = dif_currency_arr[0]
                if diff_currency_p:                         # from  DIVISA    to MN BASE
                    total_currency = cur_obj.compute(cr, uid, dif_currency_arr[1], dif_currency_arr[2], t_amount_ret, context=ctx)

                debit = dif_currency_arr[0] and total_currency or line_ret_irpf.amount_ret
                ret_name = ''
                if line_ret_irpf.retention_id.name:
                    ret_name = re.sub("[<>'\"/;]","", line_ret_irpf.retention_id.name)
                amount_ret      += debit or 0.0
                amount_currency += dif_currency_arr[0] and t_amount_ret or 0.0

                res.append({
                    'type':'retencion',
                    'name': '%s-%s'%(_('Payment'), ret_name),
                    'date_maturity': inv.date_due or False,
                    'currency_id':diff_currency_p \
                                and inv.currency_id.id or False,
                    'amount_currency': diff_currency_p \
                                and sign * t_amount_ret or False, # signo * monto
                    'ref': ref,
                    'account_id': line_ret_irpf.retention_id.account_id.id,
                    'amount': debit,
                    'ret_irpf_line_id': line_ret_irpf.id,
                    'price': 1
                })

        return amount_ret, amount_currency, res

    # para crear las lineas de las retenciones a partir de los datos
    def create_second_moves(self, cr, uid, line_total, lines_record, move_id, pay_move_line, data_pay_ret, context=None):
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        # ret_line_obj = self.pool.get('account.retention.line')
        ret_global_line_obj = self.pool.get('account.global.retention.line')
        ret_irpf_line_obj = self.pool.get('account.retention.line.irpf') #004 Retencion IRPF
        rec_moves_lines = []
        for rec in lines_record:
            move_line = {
                    # 'journal_id': pay_move_line.journal_id.id,
                    'journal_id': data_pay_ret['journal_retention_id'].id,
                    'period_id': pay_move_line.period_id.id,
                    'name': rec['name'] or '/',
                    'account_id': rec['account_id'],
                    'move_id': move_id,
                    'partner_id': pay_move_line.partner_id.id,
                    'analytic_account_id': False,
                    'quantity': 1,
                    # 'credit': rec['amount'], # el cambio, ahora al credito 08
                    'debit': rec['amount'], # el cambio, ahora al credito 15/10
                    'credit': 0.0,
                    'amount_currency': rec['amount_currency'] or False,
                    'currency_id': rec['currency_id'] or False,
                    'date': pay_move_line.date_created,
                    'account_ret_line_id': 'ret_line_id' in rec and rec['ret_line_id'] or False
                }
            ret_line = move_line_obj.create(cr, uid, move_line)
            if 'ret_gbl_line_id' in rec and rec['ret_gbl_line_id']:
                ret_global_line_obj.write(cr, uid, rec['ret_gbl_line_id'], {'move_payment_id': ret_line}) # link
            #004 Retencion IRPF 7%
            if 'ret_irpf_line_id' in rec and rec['ret_irpf_line_id']:
                ret_irpf_line_obj.write(cr, uid, rec['ret_irpf_line_id'], {'move_payment_id': ret_line}) # link
                # ret_global_line_obj.write(cr, uid, rec['ret_gbl_line_id'], {'move_payment_id': (4,ret_line)}) # link
            # ret_line_obj.write(cr, uid, rec['ret_line_id'], {'move_payment_id': ret_line})
            rec_moves_lines.append(ret_line)
        return rec_moves_lines

    # se sobreescribe en la herencia de la nueva api
    # # sobreescribiendo el primer metodo 1er metodo
    # # integrado al workflow nuevo  2do metodo
    # def action_cancel_paid(self, cr, uid, ids, context=None):
    #     if context is None:
    #         context = {}
    #     # integrado al workflow nuevo, cancel pagos retenciones  1er metodo
    #     # si tiene retenciones,eliminar las retenciones
    #     if self.check_invoice_retentions():
    #         self.delete_retention_payments(cr, uid, ids, context=context)
    #     return self.cancel_pagos_factura(cr, uid, ids, context=context)

    # # eliminar los asientos de las retenciones en caso de cancelar la factura o devolverla a abierta
    # # Para devolverla a abierta hay que modificar el workflow de factura de proveedor
    # def delete_retention_payments(self, cr, uid, ids, context=None):
    #     if context is None:
    #         context = {}
    #     # para eliminar los pagos de retenciones
    #     account_move_obj = self.pool.get('account.move')
    #     flag = False
    #     for obj_inv in self.browse(cr, uid, ids, context=context):
    #         try:
    #             if obj_inv.payment_ret_ids:
    #                 invoices = self.read(cr, uid, ids, ['payment_ret_ids'])
    #                 move_ids = [] # ones that we will need to remove
    #                 for i in invoices:
    #                     if i['payment_ret_ids']:
    #                         account_move_line_obj = self.pool.get('account.move.line')
    #                         pay_ids = account_move_line_obj.browse(cr, uid, i['payment_ret_ids'])
    #                         for move_line in pay_ids:
    #                             if move_line.move_id and move_line.move_id.id not in move_ids:
    #                                 move_ids.append(move_line.move_id.id)
    #                 if move_ids:
    #                     flag = True
    #                     # second, invalidate the move(s)
    #                     account_move_obj.button_cancel(cr, uid, move_ids, context=context)
    #                     # delete the move
    #                     cr.execute('DELETE FROM account_move '\
    #                             'WHERE id IN %s', (tuple(move_ids),))
    #                     # account_move_obj.unlink(cr, uid, move_ids, context=context)
    #         except AttributeError:
    #             self._log_event(cr, uid, ids, 1.0, "The Invoice don't have a retentions ids.")
    #             return True
    #         except ValueError:
    #             continue
    #     if flag:
    #         self._log_event(cr, uid, ids, -1.0, 'Delete Payments Retention in cancel Invoice')
    #     return True