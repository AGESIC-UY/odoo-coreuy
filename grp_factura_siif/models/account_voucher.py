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
import openerp.addons.decimal_precision as dp
import datetime
from openerp import SUPERUSER_ID

class account_voucher(osv.osv):
    _inherit= "account.voucher"

    def _compute_amount(self, cr, uid, ids, fields, args, context={}):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for voucher in self.browse(cr, uid, ids, context=context):
            res[voucher.id] = {
                'paid_amount_pend_base':0.0,
                'rate_currency':1.0,
            }
            if voucher.invoice_id and voucher.invoice_id.siif_tipo_ejecucion and voucher.invoice_id.siif_tipo_ejecucion.codigo == 'P' and voucher.company_currency_id.id != voucher.invoice_id.currency_id.id:
                context=dict(context)
                context.update({'date': voucher.date or time.strftime('%Y-%m-%d')})
                # CALCULANDO EN MONEDA BASE
                amount_to_pay = cur_obj.compute(cr, uid, voucher.invoice_id.currency_id.id, voucher.company_currency_id.id, voucher.invoice_id.residual, context=context)
                cur = cur_obj.browse(cr, uid, voucher.invoice_id.currency_id.id, context=context) # Buscando el TC en MONEDA EXTRANJERA
                res[voucher.id] = {
                    'paid_amount_pend_base':amount_to_pay,
                    'rate_currency':cur.rate or 1.0,
                }
        return res

    _columns = {
        'company_currency_id': fields.related('company_id','currency_id',  type='many2one', relation='res.currency', string='Moneda empresa',store=False, readonly=True),
        'usd_fondo_rot': fields.boolean('Es fondo rotatorio dolares'),
        'paid_amount_pend_base': fields.function(_compute_amount, type='float', multi='amount', digits_compute=dp.get_precision('Account'),
                                                 string='Total Nominal a Pagar pesos',
                                                 help='El tipo de cambio usado en el pago.'),
        'rate_currency': fields.function(_compute_amount, type='float', multi='amount', string='Tipo de Cambio', digits=(12,6),
                                         help='El tipo de cambio usado en el pago.'),
    }

    # redefiniendo metodo que se implementa en l10n_tipo_cambio_pagos
    def onchange_date_change_tc(self, cr, uid, ids, date, currency_id, payment_rate_currency_id, amount, company_id, rate, partner_id, journal_id, ttype, context=None):
        if context is None:
            context ={}

        currency_obj = self.pool.get('res.currency')
        ctx = context.copy()
        ctx.update({'company_id': company_id, 'account_period_prefer_normal': True})

        # llamada al super, onchange_date_change_tc en l10n
        res = super(account_voucher, self).onchange_date_change_tc(cr, uid, ids, date, currency_id, payment_rate_currency_id, amount, company_id, rate, partner_id, journal_id, ttype, context=context)

        # Voucher Company Currency
        company_currency_id = self.pool.get('res.company').browse(cr, uid, company_id, context=ctx).currency_id.id

        res['value']['company_currency_id']= company_currency_id

        if 'invoice_id' in context and context.get('invoice_id') and context.get('type',False)== 'payment':
            invoice_obj = self.pool.get('account.invoice')
            invoice = invoice_obj.browse(cr, uid, context.get('invoice_id'),context=ctx)
            if invoice.siif_tipo_ejecucion and invoice.siif_tipo_ejecucion.codigo == 'P' and company_currency_id != invoice.currency_id.id:
                ctx.update({'date': date or time.strftime('%Y-%m-%d')})
                amount_to_pay = currency_obj.compute(cr, uid, invoice.currency_id.id, company_currency_id, invoice.residual, context=ctx)
                cur = currency_obj.browse(cr, uid, invoice.currency_id.id, context=ctx)
                res['value'].update({'paid_amount_pend_base': amount_to_pay,
                                     'rate_currency': cur.rate,
                                     })
        return res

    def onchange_amount_change_tc(self, cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update({'date': date})
        currency_obj = self.pool.get('res.currency')

        # Llamada al super, onchange_amount_change_tc en l10n
        res = super(account_voucher, self).onchange_amount_change_tc(cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=context)

        company_currency_id = self.pool.get('res.company').browse(cr, uid, company_id, context=ctx).currency_id.id
        res['value']['usd_fondo_rot']= False
        res['value']['company_currency_id']= company_currency_id
        if 'invoice_id' in context and context.get('invoice_id') and context.get('type',False)== 'payment':
            invoice_obj = self.pool.get('account.invoice')
            invoice = invoice_obj.browse(cr, uid, context.get('invoice_id'),context=ctx)
            if invoice.siif_tipo_ejecucion and invoice.siif_tipo_ejecucion.codigo == 'P' and company_currency_id != invoice.currency_id.id:
                ctx.update({'date': date or time.strftime('%Y-%m-%d')})
                amount_to_pay = currency_obj.compute(cr, uid, invoice.currency_id.id, company_currency_id, invoice.residual, context=ctx)
                cur = currency_obj.browse(cr, uid, invoice.currency_id.id, context=ctx)
                res['value'].update({'paid_amount_pend_base': amount_to_pay,
                                     'rate_currency': cur.rate,
                                     'usd_fondo_rot': True})

        return res

    def onchange_journal_new(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
        if context is None:
            context = {}
        if not journal_id:
            return False
        journal_pool = self.pool.get('account.journal')
        currency_obj = self.pool.get('res.currency')
        journal = journal_pool.browse(cr, uid, journal_id, context=context)

        # Llamada al super, onchange_amount_change_tc en l10n
        res = super(account_voucher, self).onchange_journal_new(cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=context)

        ctx = context.copy()
        ctx = dict(ctx)

        # COMPANY CURRENCY
        company_currency_id = journal.company_id.currency_id.id
        res['value']['usd_fondo_rot']= False
        res['value']['company_currency_id']= company_currency_id

        if 'invoice_id' in context and context.get('invoice_id') and context.get('type',False)== 'payment':
            invoice_obj = self.pool.get('account.invoice')
            invoice = invoice_obj.browse(cr, uid, context.get('invoice_id'),context=ctx)
            if invoice.siif_tipo_ejecucion and invoice.siif_tipo_ejecucion.codigo == 'P' and company_currency_id != invoice.currency_id.id:
                ctx.update({'date': date or datetime.date.today().strftime('%Y-%m-%d')})
                amount_to_pay = currency_obj.compute(cr, uid, invoice.currency_id.id, company_currency_id, invoice.residual, context=ctx)

                cur = currency_obj.browse(cr, uid, invoice.currency_id.id, context=ctx)
                res['value'].update({'paid_amount_pend_base': amount_to_pay,
                                     'rate_currency': cur.rate,
                                     'usd_fondo_rot': True})

        return res

    # RAGU adicionar validacion si es un pago de factura que sea de tipo 3en1 FR
    def _filter_voucher_lines(self, cr, uid, ids, line_ids, journal_id, partner_id, context=None):
        res = super(account_voucher, self)._filter_voucher_lines(cr, uid, ids, line_ids, journal_id, partner_id, context=context)
        move_line_obj = self.pool.get('account.move.line')
        lines_filtered = [(5,)]
        for line in list(filter(lambda x: isinstance(x, dict), res)):
            # Se pasa el superuser por tema de pagos entre operating units
            invoice_id = move_line_obj.browse(cr, SUPERUSER_ID, line['move_line_id'], context=context).invoice or False
            #Cambio para pago de sueldos
            if not invoice_id or invoice_id.type in [u'out_invoice',u'out_refund'] or (invoice_id.siif_tipo_ejecucion.codigo == 'P') or (invoice_id.siif_tipo_ejecucion.codigo == 'N' and invoice_id.siif_concepto_gasto.concepto == '1'):
                lines_filtered.append(line)
        return lines_filtered