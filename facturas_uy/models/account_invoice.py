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
import openerp.addons.decimal_precision as dp
import time
from openerp import api
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_invoice_ext(osv.osv):
    _inherit = "account.invoice"

    @api.depends('currency_rate')
    def _get_tipo_de_cambio_fnc(self):
        for invoice in self:
            invoice.tipo_de_cambio_fnc = invoice.currency_rate

    _columns = {
        'currency_rate': fields.float('rate', digits_compute=dp.get_precision('Account'),help=u"Tipo de cambio de divisa de la factura."),
        'tipo_de_cambio_fnc': fields.float('Tipo de cambio', digits=(10,5), compute='_get_tipo_de_cambio_fnc', readonly=True),
        'fecha_tipo_cambio': fields.date('Fecha de tipo de cambio'), #agregando para compatibilidad
        'factura_original': fields.many2one('account.invoice', string="Factura Original", readonly=True),
        # 001-campo ap Link desde NC a Factura y Vice versa
        'nota_credito_ids': fields.one2many('nota.credito', 'invoice_id', u'Notas de crédito'),
        'company_currency_id': fields.related('company_id', 'currency_id', type='many2one', relation='res.currency', string=u'Moneda empresa', readonly=True),
        'entry_date': fields.date(u'Fecha asiento', readonly=True, select=True, states={'draft': [('readonly', False)]},
                                  help=u"Fecha efectiva para entradas contables.", copy=False),

    }
    _defaults = {
        'currency_rate': 1,
        'entry_date': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def check_accounts(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            if invoice.journal_id.currency.id != invoice.company_id.currency_id.id:
                if invoice.journal_id.currency.id != invoice.account_id.currency_id.id:
                    if invoice.type not in ('out_refund', 'in_refund'):
                        raise osv.except_osv('ValidateError!',
                                             u'The selected account of your Journal Entry forces to provide a secondary currency. '
                                             u'You should remove the secondary currency on the account or select a multi-currency view on the journal.')
        return True

    def _prepare_refund(self, cr, uid, invoice, date=None, period_id=None, description=None, journal_id=None,
                        context=None):
        res = super(account_invoice_ext, self)._prepare_refund(cr, uid, invoice, date, period_id, description, journal_id,
                                                            context)
        res['factura_original'] = invoice.id
        return res

    def check_amount(self, cr, uid, ids, context=None):
        return True

    # 001- Inicio
    # Se sobreescribe onchange sobre el campo partner_id para agregar el parametro currency_id
    # Si currency_id no coincide con la moneda base de la compania, se carga en el campo account_id
    # el valor del campo cuenta a pagar M/E que se definio en la form de Proveedores.
    def onchange_date_currency_id(self, cr, uid, ids, currency_id, date_invoice, partner_id, fecha_tipo_cambio=None):
        context = {}
        res = {'value': {}}
        context = dict(context)
        if not currency_id:
            return {'value': {'tipo_de_cambio': False}}
        if date_invoice:
            context.update({'date': date_invoice})
            res['value'].update({'entry_date': date_invoice})
        else:
            context.update({'date': time.strftime('%Y-%m-%d')})
        currency = self.pool.get('res.currency').browse(cr, uid, currency_id, context=context)
        # PCAR 27 04 2017 Inicio Esto es lo que se agrega respecto al estandar
        # RAGU Si moneda igual a la de la compania cargar la cuenta a pagar de lo contrario la cuenta a pagar M/E
        if partner_id:
            company = self.pool.get('res.users').browse(cr, uid, uid).company_id
            if company.currency_id.id != currency_id:
                cuenta_a_pagar_id = self.pool.get('res.partner').browse(cr, uid, partner_id).cuenta_a_pagar_me
            else:
                cuenta_a_pagar_id = self.pool.get('res.partner').browse(cr, uid, partner_id).property_account_payable
            res['value'].update({'account_id': cuenta_a_pagar_id.id if cuenta_a_pagar_id else False})
        # incidencia 119 de facturas
        if currency.rate_silent != 0:
            rate = currency.rate
            res['value'].update({'currency_rate': rate})
        else:
            res['value'].update({'currency_rate': False})
        return res

    def onchange_journal_id_new(self, cr, uid, ids, journal_id, partner_id, currency_id):
        res = super(account_invoice_ext, self).onchange_journal_id(cr, uid, ids, journal_id)
        if journal_id:
            journal_currency = self.pool.get('account.journal').browse(cr, uid, journal_id).currency
            if partner_id:
                company = self.pool.get('res.users').browse(cr, uid, uid).company_id
                if journal_currency.id and company.currency_id.id != journal_currency.id:
                    cuenta_a_cobrar_id = self.pool.get('res.partner').browse(cr, uid, partner_id).cuenta_a_cobrar_me
                else:
                    cuenta_a_cobrar_id = self.pool.get('res.partner').browse(cr, uid, partner_id).property_account_receivable
                res['value'].update({'account_id': cuenta_a_cobrar_id.id if cuenta_a_cobrar_id else False})
        return res

    def action_move_create(self, cr, uid, ids, context=None):
        res = super(account_invoice_ext, self).action_move_create(cr, uid, ids, context)
        self.update_invoice_rate(cr, uid, ids, context=context)
        return res

    def update_invoice_rate(self, cr, uid, ids, context):
        currency_obj = self.pool.get('res.currency')
        if not context:
            context= {}
        context = dict(context)
        ctx = context.copy()
        for inv in self.browse(cr, uid, ids, context=context):
            company_currency = self.pool['res.company'].browse(cr, uid, inv.company_id.id).currency_id.id
            if inv.currency_id.id <> company_currency:
                if inv.date_invoice:
                    ctx.update({'date': inv.date_invoice})
                else:
                    ctx.update({'date': time.strftime('%Y-%m-%d')})
                if inv.currency_id:
                    currency_rate = currency_obj.browse(cr, uid, inv.currency_id.id, context=ctx).rate
                    self.write(cr, uid, [inv.id], {'currency_rate': currency_rate }, context=ctx)

    def create(self, cr, uid, values, context = None):
        if not context:
            context= {}
        ctx = context.copy()
        if values.get('currency_id',False):
            currency_obj = self.pool.get('res.currency')
            ctx.update({'date': time.strftime('%Y-%m-%d')})
            if values.get('date_invoice',False):
                ctx.update({'date': values.get('date_invoice')})
            currency = currency_obj.browse(cr, uid, values.get('currency_id'), context=ctx)
            if currency.rate_silent != 0:
                currency_rate = currency.rate
                values.update({'currency_rate': currency_rate})
        return super(account_invoice_ext, self).create(cr, uid, values, context = context)

    def write(self, cr, uid, ids, values, context = None):
        if not context:
            context= {}
        ctx = context.copy()
        # TODO SPRING 5 Correccion de potencial error en el addons recibido
        # TODO: Se modifico esta linea de codigo ya que al tener una relacion One2may con account.invoice
        # TODO: entra 2 veces a este metodo y la segunda vez ids = [] por lo que da error a la hora de hacer un browse
        # inv = self.browse(cr, uid, ids[0])
        # date_invoice = inv.date_invoice
        if 'date_invoice' in values and values.get('date_invoice',False) and len(ids):
            inv = self.browse(cr, uid, ids[0])
            currency_id = 'currency_id' in values and values.get('currency_id',False) or inv.currency_id.id
            date_invoice = values.get('date_invoice')
            currency_obj = self.pool.get('res.currency')
            ctx.update({'date': date_invoice})
            currency = currency_obj.browse(cr, uid, currency_id, context=ctx)
            if currency.rate_silent != 0:
                currency_rate = currency.rate
                values.update({'currency_rate': currency_rate})
        res = super(account_invoice_ext, self).write(cr, uid, ids, values, context=context)
        return res


    def invoice_pay_adjustment(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'facturas_uy',
                                                                             'view_vendor_receipt_dialog_tc_up_form')
        # dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')

        inv = self.browse(cr, uid, ids[0], context=context)
        return {
            'name': _("Pay Invoice"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'payment_expected_currency': inv.currency_id.id,
                'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id,
                'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                'default_reference': inv.name,
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'default_type': inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment'
            }
        }


    # METODOS PARA PAGOS AUTOMATICOS
    def _compute_writeoff_amount(self, cr, uid, line_dr_ids, line_cr_ids, amount, type):
        debit = credit = 0.0
        sign = type == 'payment' and -1 or 1
        for l in line_dr_ids:
            if isinstance(l, dict):
                debit += l['amount']
        for l in line_cr_ids:
            if isinstance(l, dict):
                credit += l['amount']
        return amount - sign * (credit - debit)

    def recompute_automatic_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date,
                                          context=None):
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
            'value': {'line_dr_ids': [], 'line_cr_ids': [], 'pre_line': False,},
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
            # ids = []
            ids = move_line_pool.search(cr, uid, [('state', '=', 'valid'), ('account_id.type', '=', account_type),
                                                  ('reconcile_id', '=', False), ('partner_id', '=', partner_id)],
                                        context=context)
        else:
            ids = context['move_line_ids']
        invoice_id = context.get('invoice_id', False)
        company_currency = journal.company_id.currency_id.id
        move_lines_found = []

        # order the lines by most old first
        ids.reverse()
        account_move_lines = move_line_pool.browse(cr, uid, ids, context=context)

        # compute the total debit/credit and look for a matching open amount or invoice
        for line in account_move_lines:
            if _remove_noise_in_o2m():
                continue

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

            if _remove_noise_in_o2m():
                continue

            if line.currency_id and currency_id == line.currency_id.id:
                amount_original = abs(line.amount_currency)
                amount_unreconciled = abs(line.amount_residual_currency)
            else:
                # always use the amount booked in the company currency as the basis of the conversion into the voucher currency
                amount_original = currency_pool.compute(cr, uid, company_currency, currency_id,
                                                        line.credit or line.debit or 0.0, context=context_multi_currency)
                amount_unreconciled = currency_pool.compute(cr, uid, company_currency, currency_id,
                                                            abs(line.amount_residual), context=context_multi_currency)
            line_currency_id = line.currency_id and line.currency_id.id or company_currency
            rs = {
                'name': line.move_id.name,
                'type': line.credit and 'dr' or 'cr',
                'move_line_id': line.id,
                'account_id': line.account_id.id,
                'amount_original': amount_original,
                'amount_original_move_line': amount_original,
                'amount': (line.id in move_lines_found) and min(abs(remaining_amount), amount_unreconciled) or 0.0,
                'date_original': line.date,
                'date_due': line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'currency_id': line_currency_id,
                'operating_unit_id': line.operating_unit_id.id,
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
            default['value']['writeoff_amount'] = self._compute_writeoff_amount(cr, uid, default['value']['line_dr_ids'],
                                                                                default['value']['line_cr_ids'], price,
                                                                                ttype)
        return default


    def automatic_pay_invoice(self, cr, uid, ids, context=None):
        # llamando al wizard
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'facturas_uy', 'view_crear_pago_wizard')
        res_id = res and res[1] or False

        inv = self.browse(cr, uid, ids, context=context)
        inv = inv[0]
        ctx = dict(context)
        ctx.update({
            'default_date': inv.date_invoice or time.strftime('%Y-%m-%d'),
            'default_partner_id': inv.partner_id.id,
            # 'default_invoice_id': ids[0],
            # active_id
        })
        return {
            'name': "Crear pago",  # Name You want to display on wizard
            'view_mode': 'form',
            'view_id': res_id,
            'view_type': 'form',
            'res_model': 'wiz_crear_pago',  # With . Example sale.order
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    def prepare_voucher_data(self, cr, uid, invoice, journal, date, amount, context=None):
        account = invoice.type in ('out_invoice', 'out_refund') and journal.default_debit_account_id or journal.default_credit_account_id
        period_id = self.pool.get('account.period').find(cr, uid, dt=date, context=context)
        period_id = period_id[0] or False
        partner_id = self.pool.get('res.partner')._find_accounting_partner(invoice.partner_id).id,
        voucher_data = {
            'partner_id': partner_id,
            'amount': abs(amount),
            'journal_id': journal.id,
            'period_id': period_id,
            'date': date,
            'entry_date': date,
            'account_id': account.id,
            'type': invoice.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
            'reference': invoice.name,
        }
        return voucher_data

    def automatic_pay_invoice_aux(self, cr, uid, ids, journal_id=False, amount=0.0, date=None, context=None):
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        if not journal_id:
            raise osv.except_osv(_('Error!'), _('Debe enviar el diario a pagar'))
            # journal_id = 2013

        voucher_obj = self.pool.get('account.voucher')
        journal_obj = self.pool.get('account.journal')
        journal = journal_obj.browse(cr, uid, journal_id, context=context)

        for invoice in self.browse(cr, uid, ids, context):
            # if invoice.state not in ('open'):
            # Control para si ya se contabilizo
            if not invoice.move_id:
                continue

            company_currency = self.pool.get('res.company').browse(cr, uid, invoice.company_id.id,
                                                                   context=context).currency_id
            journal_currency = journal.currency and journal.currency.id or company_currency.id

            # Para el pago total, no enviar monto asi se paga el monto total del residual
            if not amount:
                amount = invoice.residual or 0.0
                # amount_inv_in_company_currency = 0.0
                inv_currency = invoice.currency_id.id or False
                if journal_currency != inv_currency and inv_currency != company_currency.id:
                    ctx = dict(context, account_period_prefer_normal=True)
                    if context.get('date_voucher_rei', False):
                        ctx.update({'date': context['date_voucher_rei']})
                    else:
                        ctx.update({'date': date})
                    amount = self.pool.get('res.currency').compute(cr, uid, invoice.currency_id.id, company_currency.id,
                                                                   amount, True, context=ctx)
                    # else:
                    #     amount_inv_in_company_currency = amount
                    # amount = amount_inv_in_company_currency
                    # amount = invoice.residual or 0.0
            if not amount:
                raise osv.except_osv(_('Error!'), _("No se puede pagar una factura con monto cero."))

            if not date:
                date = invoice.date_invoice
            # move = invoice.move_id

            #se crea metodo para preparar los datos, para que otros puedan heredar
            voucher_data = self.prepare_voucher_data(cr, uid, invoice, journal, date, amount, context=None)

            #DDELFINO: Se agrega journal_id al context de modo que _get_payment_rate_currency (de account_voucher.py base) lo tome y devuelva journal.currency.id en lugar de company_id.currency_id.id
            ctx1 = dict(context, journal_id=journal.id)

            voucher_id = voucher_obj.create(cr, uid, voucher_data, context=ctx1)
            # _logger.debug('test')
            # _logger.debug(voucher_id)

            # llamada a creacion de voucher lines en compute
            #DDELFINO: Se arregla codigo para que funcione tanto para factura provedores y factura clientes
            #ttype = 'payment'
            ttype = invoice.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment'
            price = amount
            currency_id = journal_currency  # va la moneda del diario o de la compañia
            c = context.copy()
            #DDELFINO: Se arregla codigo para que funcione tanto para factura provedores y factura clientes
            #c.update({'invoice_id': invoice.id, 'type': 'payment'})
            c.update({'invoice_id': invoice.id, 'type': ttype})
            res = self.recompute_automatic_voucher_lines(cr, uid, [voucher_id], voucher_data['partner_id'], journal.id, price, currency_id,
                                                         ttype, date, context=c)

            values = res['value']

            writeoff_amount = 0.0
            if 'writeoff_amount' in values:
                writeoff_amount = values['writeoff_amount'] or 0.0

            line_ids = []
            # According to invoice type
            if invoice.type in ('out_invoice', 'out_refund'):
                lines = 'line_cr_ids' in values and values['line_cr_ids'] or False
                if lines:
                    for line_data in lines:
                        line_data.update({'voucher_id': voucher_id})
                        line_id = self.pool.get('account.voucher.line').create(cr, uid, line_data, context=context)
                        line_ids.append(line_id)
            else:
                # para las facturas de proveedor
                lines = 'line_dr_ids' in values and values['line_dr_ids'] or False
                if lines:
                    for line_data in lines:
                        line_data.update({'voucher_id': voucher_id})
                        line_id = self.pool.get('account.voucher.line').create(cr, uid, line_data, context=context)
                        line_ids.append(line_id)

            # voucher_new = voucher_obj.browse(cr, uid, voucher_id, context=c)
            tax_id = False
            # res_onchange = voucher_obj.onchange_journal_new(cr, uid, [voucher_id], journal.id, line_ids, tax_id, partner_id, date, amount, ttype, invoice.company_id.id, context=c)
            res_onchange = voucher_obj.onchange_journal_new(cr, uid, [voucher_id], journal.id, line_ids, tax_id, False,
                                                            date, amount, ttype, invoice.company_id.id, context=c)
            self.pool.get('account.voucher').browse(cr, uid, voucher_id).line_ids.filtered(lambda a: a.amount != 0).amount = amount
            rval = res_onchange['value']

            keys_vals = {'down_tc', 'paid_amount_in_company_currency', 'payment_rate', 'payment_rate_currency_id',
                         'pre_line', 'up_tc', 'writeoff_amount_aux'}
            values_update = {'writeoff_amount': writeoff_amount}
            # # for key in keys_vals.keys():
            for key in keys_vals:
                if key in rval:
                    values_update.update({key: rval[key]})
                    # values_update[key].update(rval[key])
            voucher_obj.write(cr, uid, [voucher_id], values_update, context=c)

            # Llamada al metodo de pago modificado para variaciones del tipo de cambio
            # self.pool.get('account.voucher').button_proforma_voucher(cr, uid, [voucher_id], context=context)
            new_context = dict(context)
            new_context.update({'validar': True, 'date_p': date})
            self.pool.get('account.voucher').button_proforma_auxiliary_voucher(cr, uid, [voucher_id], context=new_context)
        return True