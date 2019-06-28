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

import time, datetime
from dateutil.relativedelta import relativedelta
import re

from openerp.osv import osv, fields
from openerp.osv.orm import Model
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

# vinculo de move line a lineas de retenciones
class account_move_line_ext(osv.osv):
    _inherit = 'account.move.line'
    _columns = {
        'account_ret_line_id': fields.many2one('account.retention.line', 'Retention Line', readonly=True, ondelete='set null', select=2),
    }
account_move_line_ext()

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'retention_journal_id': fields.many2one(
            'account.journal',
            string="Journal",
            domain="[('type', '=', 'bank')]"),
    }
res_company()

class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    _columns = {
        'retention_journal_id': fields.related(
            'company_id', 'retention_journal_id',
            type="many2one",
            relation='account.journal',
            string="Journal",
            domain="[('type', '=', 'bank')]"),
    }
    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        res = super(account_config_settings, self).onchange_company_id(cr, uid, ids, company_id, context=context)
        if company_id:
            company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
            res['value'].update({'retention_journal_id': company.retention_journal_id and company.retention_journal_id.id or False})
        else:
            res['value'].update({'retention_journal_id': False})
        return res

account_config_settings()


#Para las lineas del IRPF
class retention_irpf(osv.osv):

    def _amount_base(self, cr, uid, ids, fields, args, context=None):
        res = {}
        if context is None:
            context = {}
        ctx = context.copy()
        currency_obj = self.pool.get('res.currency')

        for rec in self.browse(cr,uid,ids,context=context):
            moneda = rec.invoice_id.currency_id.id
            moneda_base = rec.invoice_id.company_id.currency_id.id
            base_amount = rec.base_amount or 0.0
            base_amount_pend = rec.base_amount_pend or 0.0
            if moneda != moneda_base:
                # ctx.update({'date': rec.invoice_id.date_invoice or time.strftime('%Y-%m-%d %H:%M:%S')})
                ctx.update({'date': rec.invoice_id.date_invoice or time.strftime('%Y-%m-%d')})
                base_amount = currency_obj.compute(cr, uid, moneda, moneda_base, rec.base_amount, context=ctx)
                base_amount_pend = currency_obj.compute(cr, uid, moneda, moneda_base, rec.base_amount_pend, context=ctx)
            res[rec.id] = {
                #'base_amount_pesos': base_amount,
                'base_amount_pesos': base_amount,
                'base_amount_pend_pesos': base_amount_pend,
            }
        return res

    def _amount_ret_line(self, cr, uid, ids, fields, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = {
                # 'amount_ret_pendiente':0.0,
                'amount_ret':0.0,
            }
            ret = line.retention_id
            monto = 0.0
            if ret:
                if ret.base_compute == 'ret_tax':
                    if line.base_amount_pend>0:
                        monto = line.base_amount_pend * ret.percent / 100
                elif ret.base_compute == 'ret_line_amount':
                    if line.base_amount_pend>0:
                        monto = line.base_amount_pend * ret.percent / 100

            if not line.pendiente:
                res[line.id] = {
                    # 'amount_ret_pendiente':monto,
                    'amount_ret': monto,
                }
        return res

    _name = "account.retention.line.irpf"
    _description = "Invoice Retention Lines IRPF"
    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice Ref', ondelete='cascade', select=True),
        'base_amount': fields.float(u'Monto base cálculo', digits_compute= dp.get_precision('Account'), help=u'Monto base cálculo'), # monto base de calculo, monto sin IVA de las líneas
        'base_amount_pend': fields.float(u'Monto base cálculo', digits_compute= dp.get_precision('Account'), help=u'Monto base cálculo pendiente'), # monto base de calculo, monto sin IVA de las líneas
        'base_amount_pesos':fields.function(_amount_base, multi='fnc_base', string=u'Monto base cálculo pesos', type="float", # monto base calculo pesos
            digits_compute= dp.get_precision('Account'), help="Monto base calculo pesos."),
        'base_amount_pend_pesos': fields.function(_amount_base, multi='fnc_base', string=u'Monto base cálculo pesos', type="float", # monto base calculo pesos
            digits_compute= dp.get_precision('Account'), help="Monto base calculo en pesos."),
        'amount_ret': fields.function(_amount_ret_line, multi='amount', string='Importe a retener', type="float", # monto calculado a retener
            digits_compute= dp.get_precision('Account'), store=True, help="Monto a retener."),
        'move_payment_id': fields.many2one('account.move.line', 'Move Line Payment', readonly=True, select=1, ondelete='set null', help="Link to the payment Line Items."),
        # retenciones, nuevo diseño con many2many   09/04
        'pendiente': fields.boolean('Pendiente'),
        'retention_id': fields.many2one('account.retention', u'Retención', select=True), # Retencion IRPF
        'type': fields.selection([('local', u'Local'), ('externo', u'Pendiente')],'Tipo'), # Remoto si es el calculo de las facturas
        'description': fields.char(u'Descripción', size=64),
        'partner_id': fields.many2one('res.partner','Partner'), #Agregando id de proveedor
    }

    _defaults = {
        'amount_ret': 0.0,
        'base_amount': 0.0,
        'base_amount_pend':0.0,
        'pendiente':True,
        'type': 'local',
    }

    _sql_constraints = [('linea_ret_irpf_pago_uniq', 'unique(invoice_id, move_payment_id)', u'Los pagos deben ser únicos según las líneas de retenciones IRPF.')]

    # para la factura de proveedor, importe negativo para afectacion por el credito
    def move_line_get_credit(self, cr, uid, inv, ref, invoice_id, dif_currency_arr, context=None):
        res = []
        cur_obj         = self.pool.get('res.currency')
        amount_ret      = 0.0
        amount_currency = 0.0
        if context is None:
            context = {}
        context = dict(context)
        # acc_ret_line_ids = account_ret_line_obj.search(cr, uid, [('invoice_id','=',invoice_id),('amount_ret','>',0)], order='id')
        acc_ret_line_ids = self.search(cr, uid, [('invoice_id','=',invoice_id),('amount_ret','>',0)], order='id')
        if acc_ret_line_ids:
            for ret_irpf_line in self.browse(cr, uid, acc_ret_line_ids,context=context):
                if ret_irpf_line.retention_id:
                # retention_related = self.pool['account.retention'].browse(cr, uid, t['retention_id'])
                # product_related = self.pool['product.product'].browse(cr, uid, t['product_id'])
                    t_amount_ret = ret_irpf_line.amount_ret
                    diff_currency_p = dif_currency_arr[0]
                    if diff_currency_p:                         # from  DIVISA    to MN BASE
                        total_currency = cur_obj.compute(cr, uid, dif_currency_arr[1], dif_currency_arr[2], t_amount_ret, context=context)

                    amount = dif_currency_arr[0] and total_currency or ret_irpf_line.amount_ret
                    amount_ret+= -1 * amount or 0.0
                    amount_currency += dif_currency_arr[0] and -1 * t_amount_ret or 0.0
                    # ret_name = re.sub("[<>'\"/;%]","", r_name)
                    ret_name = ''
                    if ret_irpf_line.retention_id.name:
                        ret_name = re.sub("[<>'\"/;]","", ret_irpf_line.retention_id.name)
                    res.append({
                        'type':'retencion',
                        'name': ret_name,
                        'date_maturity': inv.date_due or False,
                        'currency_id':diff_currency_p \
                                    and inv.currency_id.id or False,
                        'amount_currency': diff_currency_p \
                                    and t_amount_ret or False,
                        'ref': ref,
                        'account_id': ret_irpf_line.retention_id.account_id and ret_irpf_line.retention_id.account_id.id,
                        'amount': -1 * amount if inv.type != 'in_refund' else amount,
                        'price': -1 * amount if inv.type != 'in_refund' else amount,
                        # 'amount': -1 * t['amount_ret'],
                    })
        if inv.type == 'in_refund':
            amount_ret *= -1
        return amount_ret, amount_currency, res
retention_irpf()
#Fin de clase para lineas IRPF


# nuevo modelo gestionar retenciones de lineas
# account.retention.line
class account_retention_line(osv.osv):

    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        for line in self.browse(cr, uid, ids):
            subtotal = line.price_unit * line.quantity
            res[line.id] = subtotal
        return res

    def _check_uniq_line_tax(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for line_ret in self.browse(cr, uid, ids):
            lines_ids = self.search(cr, uid, [('line_id', '=', line_ret.line_id.id),('tax_id', '=', line_ret.tax_id.id)], context=context)
            if len(lines_ids)>1:
                return False
        return True

    def _amount_ret_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = 0.0
            for ret in line.retention_line_ret_ids:
                if ret.base_compute == 'ret_tax':
                    if line.base_retax:
                        res[line.id] += line.base_retax * ret.percent / 100
                elif ret.base_compute == 'ret_line_amount':
                    if line.base_ret_line:
                        res[line.id] += line.base_ret_line * ret.percent / 100
                else:
                    res[line.id] += 0.0
        return res

    def _get_payment_lines(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            id = invoice.id
            res[id] = []
            if not invoice.move_id:
                continue
            data_lines = [x for x in invoice.move_id.line_id if x.account_id.id == invoice.account_id.id]
            partial_ids = []
            for line in data_lines:
                ids_line = []
                if line.reconcile_id:
                    ids_line = line.reconcile_id.line_id
                elif line.reconcile_partial_id:
                    ids_line = line.reconcile_partial_id.line_partial_ids
                l = map(lambda x: x.id, ids_line)
                partial_ids.append(line.id)
                res[id] =[x for x in l if x <> line.id and x not in partial_ids]
        return res

    _name = "account.retention.line"
    _description = "Invoice Retention Line"
    _columns = {
        'line_id': fields.many2one('account.invoice.line', 'Invoice Line Ref', ondelete='cascade', select=True),
        'subtotal': fields.function(_amount_line, string='Amount', type="float",
            digits_compute= dp.get_precision('Account'), store=True),
        'base_retax': fields.float('Base impuesto', digits_compute= dp.get_precision('Account')), # base impuesto
        'base_ret_line': fields.float('Base linea', digits_compute= dp.get_precision('Account')), # base linea
        'amount_ret': fields.function(_amount_ret_line, string='Importe a retener', type="float", # monto calculado a retener
            digits_compute= dp.get_precision('Account'), store=True, help="Monto a retener."),
        # nuevo diseño 10/04 pagos de retenciones
        # 'move_payment_id': fields.many2one('account.move.line', 'Move Line Payment', readonly=True, select=1, ondelete='set null', help="Link to the payment Line Items."),
        'move_payment_line': fields.one2many('account.move.line', 'account_ret_line_id', 'Payment Retention Lines', readonly=True, help="Link to the payment Line Items."),
        'tax_id': fields.many2one('account.tax', 'Account Tax'),
        # retenciones, nuevo diseño con many2many   09/04
        # 'retention_id': fields.many2one('account.retention', u'Retención', select=True), # Retencion
        'retention_line_ret_ids': fields.many2many('account.retention', 'account_retention_line_ret', 'account_ret_line_id', 'retention_id', 'Retenciones'),
        # campos agregados grp, comentados por campos siif integracion carolina 003
        'description': fields.char('Description', size=64),
        # Todos son campos related pq no cambian
        'invoice_id': fields.many2one('account.invoice', string='Invoice Ref', ondelete='cascade'),
        # 'invoice_id': fields.related('line_id','invoice_id',type='many2one', relation='account.invoice', string='Invoice Ref', store=True, ondelete='cascade'),
        'product_id': fields.related('line_id','product_id',type='many2one', relation='product.product', string='Product'),
        'price_unit': fields.related('line_id','price_unit',type='float', string='Unit Price'),
        'quantity': fields.related('line_id','quantity',type='float',string='Quantity'),
    }

    _defaults = {
        'base_retax': 0.0,
        'base_ret_line': 0.0,
        'amount_ret': 0.0,
    }

    _sql_constraints = [('linea_retencion_factura_uniq', 'unique(invoice_id, line_id, tax_id)', u'Las líneas de retención deben ser únicas según las líneas de la factura.')]

    _constraints = [(_check_uniq_line_tax,u'Las líneas de retención deben ser únicas por cada línea de factura.',['line_id','tax_id']),]

    # para la factura de proveedor, importe negativo para afectacion por el credito
    def move_line_get_credit(self, cr, uid, inv, ref, invoice_id, dif_currency_arr, context=None):
        if context is None:
            context = {}
        context = dict(context)
        res = []
        # cr.execute('SELECT * FROM account_retention_line WHERE invoice_id=%s and amount_ret > 0', (invoice_id,))
        cur_obj         = self.pool.get('res.currency')
        amount_ret      = 0.0
        amount_currency = 0.0
        def amount_retention(ret, base_retax=0, base_ret_line=0):
            if ret.base_compute == 'ret_tax':
                if base_retax:
                    return base_retax * ret.percent / 100
            elif ret.base_compute == 'ret_line_amount':
                if base_ret_line:
                    return base_ret_line * ret.percent / 100
            return 0.0

        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(cr, uid, 'Account')
        # acc_ret_line_ids = account_ret_line_obj.search(cr, uid, [('invoice_id','=',invoice_id),('amount_ret','>',0)], order='id')
        acc_ret_line_ids = self.search(cr, uid, [('invoice_id','=',invoice_id),('amount_ret','>',0)], order='id')
        if acc_ret_line_ids:
            prec = obj_precision.precision_get(cr, uid, 'Account')
            for retline in self.browse(cr, uid, acc_ret_line_ids,context=context):
                for retention_related in retline.retention_line_ret_ids:
                    # retention_related = self.pool['account.retention'].browse(cr, uid, t['retention_id'])
                    # product_related = self.pool['product.product'].browse(cr, uid, t['product_id'])
                    t_amount_ret = amount_retention(retention_related, retline.base_retax,retline.base_ret_line)
                    # La causa es que el amount de retenciones viene con mas de 3 lugares despues de la coma, hay aspecto de perdida en redondeo
                    diff_currency_p = dif_currency_arr[0]
                    if diff_currency_p:                         # from  DIVISA    to MN BASE
                        total_currency = cur_obj.compute(cr, uid, dif_currency_arr[1], dif_currency_arr[2], t_amount_ret, context=context)

                    amount = dif_currency_arr[0] and total_currency or amount_retention(retention_related, retline.base_retax,retline.base_ret_line)
                    amount_ret += -1 * round(amount,prec) or 0.0
                    amount_currency += dif_currency_arr[0] and -1 * round(t_amount_ret,prec) or 0.0
                    # ret_name = re.sub("[<>'\"/;%]","", r_name)
                    ret_name = ''
                    if retention_related.name:
                        ret_name = re.sub("[<>'\"/;]","", retention_related.name)
                    res.append({
                        'type':'retencion',
                        'name': ret_name,
                        'date_maturity': inv.date_due or False,
                        'currency_id':diff_currency_p \
                                    and inv.currency_id.id or False,
                        'amount_currency': diff_currency_p \
                                    and t_amount_ret or False,
                        'ref': ref,
                        'account_id': retention_related.account_id.id,
                        'amount': -1 * amount if inv.type != 'in_refund' else amount,
                        'price': -1 * amount if inv.type != 'in_refund' else amount,
                    })
                    # amount_ret      = -1 * amount_ret
                    # amount_currency = -1 * amount_currency
        if inv.type == 'in_refund':
            amount_ret *= -1
        return amount_ret, amount_currency, res

account_retention_line()

# retenciones globales, nueva clase
class account_global_retention_line(osv.osv):
    _name = "account.global.retention.line"
    _description = "Invoice Global Retention Line"

    #009- cambio retencion moneda base
    def _amount_ret_base(self, cr, uid, ids, fields, args, context=None):
        res = {}
        if context is None:
            context = {}
        ctx = context.copy()
        currency_obj = self.pool.get('res.currency')
        for rec in self.browse(cr,uid,ids,context=context):
            moneda = rec.invoice_id.currency_id.id
            moneda_base = rec.invoice_id.company_id.currency_id.id
            ret_mb = rec.amount_ret_pesos or 0.0
            if moneda != moneda_base:
                # ctx.update({'date': rec.invoice_id.date_invoice or time.strftime('%Y-%m-%d %H:%M:%S')})
                ctx.update({'date': rec.invoice_id.date_invoice or time.strftime('%Y-%m-%d')})
                # ret_mb = currency_obj.compute(cr, uid, moneda, moneda_base, rec.amount_ret, context=ctx)
                ret_mb = currency_obj.compute(cr, uid, moneda_base, moneda, ret_mb, context=ctx)
            res[rec.id] = {
                #'base_amount_pesos': base_amount,
                'amount_ret': ret_mb,
            }
        return res

    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice Ref', ondelete='cascade', select=True),# si se elimina la factura se elimina el global rete
        'name': fields.char(u'Descripción', size=30),
        # incidencia 009 - Agregar retencion en moneda base
        'amount_ret': fields.function(_amount_ret_base, multi='fnc_base', string=u'Importe', type="float",
                                   digits_compute= dp.get_precision('Account'), help=u"Monto a retener en moneda de factura"),
        'amount_ret_pesos': fields.float('Importe pesos', digits_compute= dp.get_precision('Account'), required=True), # base linea
        # 'amount_ret_pesos':fields.function(_amount_ret_base, multi='fnc_base', string=u'Importe pesos', type="float", # monto base calculo pesos
        #     digits_compute= dp.get_precision('Account'), help="Monto base calculo pesos."),
        'move_payment_id': fields.many2one('account.move.line', 'Move Line Payment', readonly=True, select=1, ondelete='set null', help="Link to the payment Line Items."),
        # 'move_payment_line': fields.one2many('account.move.line', 'account_ret_line_id', 'Payment Retention Lines', readonly=True, help="Link to the payment Line Items."),
        'date': fields.date(u'Fecha de creación', readonly=True), # fecha emision
        # incidencia 122 el campo diario debe ser el mismo de la factura
        'journal_id': fields.related('invoice_id','journal_id',type='many2one',relation='account.journal', readonly=True, string=u'Diario'),
        # 'journal_id': fields.many2one('account.journal', u'Diario'),
        'account_id': fields.many2one('account.account', 'Account', required=True, domain=[('type','=','other')], help=u"La cuenta a la cual se contabilizará la retención."),
    }

    _defaults = {
        'amount_ret': 0.0,
        'date': lambda *a: datetime.date.today().strftime('%Y-%m-%d') #time.strftime('%Y-%m-%d'),
    }



    # Retenciones manuales
    def move_line_get_credit(self, cr, uid, inv, ref, invoice_id, dif_currency_arr, context=None):
        res = []
        cur_obj         = self.pool.get('res.currency')
        amount_ret      = 0.0
        amount_currency = 0.0

        if context is None:
            context = {}
        context = dict(context)
        acc_ret_line_ids = self.search(cr, uid, [('invoice_id','=',invoice_id)], order='id')
        if acc_ret_line_ids:
            for ret_global_line in self.browse(cr, uid, acc_ret_line_ids,context=context):
                if ret_global_line.amount_ret > 0:
                    # retention_related = self.pool['account.retention'].browse(cr, uid, t['retention_id'])
                    # product_related = self.pool['product.product'].browse(cr, uid, t['product_id'])
                    t_amount_ret = ret_global_line.amount_ret
                    diff_currency_p = dif_currency_arr[0]
                    if diff_currency_p:                         # from  DIVISA    to MN BASE
                        total_currency = cur_obj.compute(cr, uid, dif_currency_arr[1], dif_currency_arr[2], t_amount_ret, context=context)

                    amount = dif_currency_arr[0] and total_currency or ret_global_line.amount_ret
                    amount_ret      += -1 * amount or 0.0
                    amount_currency += dif_currency_arr[0] and -1 * t_amount_ret or 0.0
                    # ret_name = re.sub("[<>'\"/;%]","", r_name)
                    ret_name = ''
                    # Debe ser el concatenado de grupo + acreedor
                    #113- inc 08/03 Cambio en el name
                    #if ret_global_line.name:
                    # if ret_global_line.group_id or ret_global_line.creditor_id:
                    #     ret_group = re.sub("[<>'\"/;]","", ret_global_line.group_id.name)
                    #     ret_cred = re.sub("[<>'\"/;]","", ret_global_line.creditor_id.name)
                    #     ret_name = '%s %s' % (ret_group,ret_cred)
                    if ret_global_line.creditor_id:
                        ret_cred = re.sub("[<>'\"/;]","", ret_global_line.creditor_id.name)
                        ret_name = ret_cred
                    #113-Fin cambios
                    res.append({
                        'type':'retencion',
                        'name': ret_name,
                        'date_maturity': inv.date_due or False,
                        'currency_id':diff_currency_p \
                                    and inv.currency_id.id or False,
                        'amount_currency': diff_currency_p \
                                    and t_amount_ret or False,
                        'ref': ref,
                        'account_id': ret_global_line.account_id.id,
                        'amount': -1 * amount if inv.type != 'in_refund' else amount,
                        'price': -1 * amount if inv.type != 'in_refund' else amount,
                        # 'amount': -1 * t['amount_ret'],
                    })
        if inv.type == 'in_refund':
            amount_ret *= -1
        return amount_ret, amount_currency, res

account_global_retention_line()

# modificando y agregando metodos a account.invoice
class account_invoice_ext_ret(Model):
    _inherit = 'account.invoice'

    def button_compute(self, cr, uid, ids, context=None, set_total=True):
        for inv in self.browse(cr, uid, ids, context=context):
            if set_total:
                self.pool.get('account.invoice').write(cr, uid, [inv.id], {'check_total': inv.amount_total})
        return True

    def print_retention(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        ids_r = []
        if ids_r:
            datas = {'ids' : ids_r,
                     'model': 'account.retention'}
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.retention.rlist',
                'model': 'account.retention',
                'datas': datas,
                'nodestroy': True,
                }
        else:
            raise osv.except_osv(_('No Retention Lines!'), _('The selected invoice have not retention lines.'))

    # metodo principal donde se calculan los impuestos y retenciones
    # def _amount_all(self, cr, uid, ids, fields, args, context=None):
    #     res = {}
    #     invoices = self.browse(cr, uid, ids, context=context)
    #     for invoice in invoices:
    #         res[invoice.id] = {
    #             'amount_untaxed': 0.0,
    #             'amount_tax': 0.0,
    #             'amount_total': 0.0,
    #             'amount_subttal_lines_ret':0.0,
    #             'amount_subttal_global_inv_ret':0.0,
    #             'amount_total_retention':0.0
    #         }
    #         for line in invoice.tax_line:
    #             res[invoice.id]['amount_tax'] += line.amount
    #
    #         #Total General
    #         obj_retline = self.pool.get('account.retention.line')
    #         tax_obj = self.pool.get('account.tax')
    #         cur_obj = self.pool.get('res.currency')
    #         cur = invoice.currency_id
    #         company_currency = self.pool['res.company'].browse(cr, uid, invoice.company_id.id).currency_id.id
    #         # Modificacion del metodo original para calcular los datos de las lineas de retenciones
    #         sum_retenciones_lines = 0.0
    #         sum_ret_global_lines = 0.0
    #         for ret_global_line in invoice.invoice_ret_global_line_ids:
    #             sum_ret_global_lines += ret_global_line.amount_ret
    #
    #         for line in invoice.invoice_line:
    #             res[invoice.id]['amount_untaxed'] += line.price_subtotal
    #             for line_tax_id in line.invoice_line_tax_id:
    #                 for tax in tax_obj.compute_all(cr, uid, [line_tax_id], (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, line.product_id, invoice.partner_id)['taxes']:
    #                     amount_ret = 0.0
    #                     val={}
    #                     val['amount'] = tax['amount']
    #                     val['base'] = cur_obj.round(cr, uid, cur, tax['price_unit'] * line['quantity'])
    #
    #                     if invoice.type in ('out_invoice','in_invoice'):
    #                         val['base_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, False, val['amount'] * tax['base_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
    #                         val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, False, val['amount'] * tax['tax_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
    #                     else:
    #                         val['base_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, False, val['amount'] * tax['ref_base_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
    #                         val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, False, val['amount'] * tax['ref_tax_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
    #                         # val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
    #                     base_retax = val['base_amount'] or 0.0
    #                     base_ret_line = val['base'] or 0.0
    #
    #                     rdata = {'line_id':line.id,
    #                                 'tax_id': line_tax_id.id,       # id del impuesto
    #                                 'base_retax': base_retax,       # base calculo impuesto
    #                                 'base_ret_line': base_ret_line, # base calculo linea
    #                                 'amount_ret': amount_ret}
    #                     id_rlines = obj_retline.search(cr, uid, [('line_id', '=', line.id),('tax_id','=',line_tax_id.id)], context=context)
    #                     ret_id = 0
    #                     if id_rlines and id_rlines[0]:
    #                         obj_retline.write(cr, uid, id_rlines[0], rdata, context)
    #                         ret_id = id_rlines[0]
    #                     elif invoice.state == 'draft':
    #                         ret_id = obj_retline.create(cr, uid, rdata, context)
    #                     if ret_id:
    #                         for ret_line in obj_retline.browse(cr,uid,[ret_id],context=context):
    #                             if ret_line.amount_ret:
    #                                 #for tax_line in line.invoice_line_tax_id:
    #                                 sum_retenciones_lines += ret_line.amount_ret
    #                             # if ret_line.retention_id:
    #                             #     sum_retenciones += ret_line.base_retax * ret_line.retention_id.percent / 100
    #
    #         # res[invoice.id]['amount_ret'] = sum_retenciones
    #         res[invoice.id]['amount_subttal_lines_ret'] = sum_retenciones_lines or 0.0
    #         res[invoice.id]['amount_subttal_global_inv_ret'] = sum_ret_global_lines or 0.0
    #         res[invoice.id]['amount_total_retention'] = sum_retenciones_lines + sum_ret_global_lines
    #         ttret = sum_retenciones_lines + sum_ret_global_lines
    #         amount_ttal = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed'] - ttret
    #         # res[invoice.id]['amount_pay']  = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed'] # echaviano 23 feb
    #         res[invoice.id]['amount_total'] = amount_ttal
    #     return res

    # totales para siif. Redondeados 003 Inicio cambios
    def _get_totales_ret(self, cr, uid, ids, fields, args, context=None):
        res = {}
        context = dict(context)
        currency_obj = self.pool.get('res.currency')
        for inv in self.browse(cr,uid,ids,context=context):
            moneda = inv.currency_id and inv.currency_id.id
            moneda_base = inv.company_id.currency_id and inv.company_id.currency_id.id
            ctx = context.copy()

            ret_ttal_base = round(inv.amount_total_retention)
            # amount_ttal_base = round(inv.amount_total)
            tax_ttal_base = round(inv.amount_tax)
            total_nominal = inv.amount_untaxed + inv.amount_tax
            # total_nominal_pesos = total_nominal
            total_liq_pesos = round(inv.amount_total)
            # amount_mbase = inv.amount_total
            change_moneda = True

            if moneda != moneda_base:
                ctx.update({'date': inv.date_invoice or time.strftime('%Y-%m-%d')})
                ctx_nominal = ctx.copy()
                ctx_nominal.update({'date': inv.fecha_tipo_cambio or time.strftime('%Y-%m-%d')}) # cambio en el contexto 19/11
                ctx_nominal.update({'pricelist_type':'presupuesto'})
                amount_ret_mbase = currency_obj.compute(cr, uid, moneda, moneda_base, inv.amount_total_retention, context=ctx) #total retenciones moneda base
                # amount_mbase = currency_obj.compute(cr, uid, moneda, moneda_base, inv.amount_total, context=ctx) #total a pagar moneda base
                amount_tax_mbase = currency_obj.compute(cr, uid, moneda, moneda_base, inv.amount_tax, context=ctx) #total a pagar moneda base
                #amount_tax_mbase = currency_obj.compute(cr, uid, moneda, moneda_base, inv.amount_tax, context=ctx_nominal) #total a pagar moneda base
                #total_nominal_pesos = currency_obj.compute(cr, uid, moneda, moneda_base, total_nominal, context=ctx_nominal) #total a pagar moneda base
                #008 - TC Prespuesto
                rate = 1
                if not inv.tc_presupuesto:
                    ctx2 = context.copy()
                    if inv.fecha_tipo_cambio:
                        ctx2.update({'date': inv.fecha_tipo_cambio})
                    else:
                        ctx2.update({'date': time.strftime('%Y-%m-%d')})
                    currency2 = self.pool.get('res.currency').browse(cr, uid, inv.currency_id.id, context=ctx2)
                    if not currency2:
                        raise osv.except_osv(_('Error !'),
                                             _('No encontrada moneda !'))
                    if currency2 and currency2.rate_silent != 0 and currency2.rate_presupuesto != 0:
                        rate = currency2.rate_presupuesto
                else:
                    rate = inv.tc_presupuesto
                total_liq_pesos = inv.amount_total and round(inv.amount_total) * rate or 0.0
                # total_liq_pesos = currency_obj.compute(cr, uid, moneda, moneda_base, round(inv.amount_total), context=ctx_nominal) #total a pagar moneda base
                #008 - TC Presupuesto editable
                # res[line.id] = currency_obj.compute(cr, uid, moneda, moneda_base, line.monto_divisa, context)
                ret_ttal_base = round(amount_ret_mbase)
                tax_ttal_base = round(amount_tax_mbase)
                change_moneda = False

            # calculos retencion redondeado por summary 17/09
            sum = 0
            for retencion in inv.ret_summary_group_line:
                sum += round(retencion.ret_amount_pesos_round)
            # si la factura es en pesos
            # Caso 1
            liq = sum
            liq_pesos = round(total_liq_pesos)
            if change_moneda:
                # Comprobacion con liquido + retenciones > nominal
                if round(total_liq_pesos + sum) > round(total_nominal):
                    liq = liq - 1
                    liq_pesos = round(total_liq_pesos) - 1

                # Caso 2 - Si total nominal diferentes liquido + retenciones
                if abs(round(total_nominal) - round(total_liq_pesos + liq)) > 0:
                    dd = round(total_nominal) - round(total_liq_pesos + liq)
                    liq = liq + dd
                    liq_pesos = liq_pesos + 1

            # fin cambios
            res[inv.id] = {
                # totales moneda de factura
                # nominal
                'total_nominal_divisa': round(total_nominal) or 0.0,
                'total_nominal_divisa_cpy': total_nominal or 0.0,
                # totales en pesos para SIIF
                # campos de precision 16,0
                #'amount_ttal_liq_pesos': round(total_nominal_pesos - sum),
                'amount_ttal_liq_pesos': liq_pesos,
                'amount_ttal_ret_pesos': sum, # campo a cambiar forma de pago
                'amount_ttal_impuestos_pesos': tax_ttal_base,
                #002-
                'total_reponer':round(inv.amount_total_paid + sum),
                # nominal
                'total_nominal': liq_pesos + sum,
                # 'total_nominal': round(total_liq_pesos + liq), # + sum >> suma
                # campos con presicion segun configuracion
                'amount_ttal_ret': inv.amount_total_retention or 0.0, # campo para mostrar total de retenciones en pestanna retenciones
                'amount_ttal_ret_base': ret_ttal_base, # campo para mostrar total de retenciones en pestanna retenciones en pesos
            }
        return res

    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()

    def _compute_invoice_lines(self, cr, uid, ids, name, args, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            if invoice.invoice_line:
                result[invoice.id] = invoice.invoice_line
        return result

    # si tiene lineas, y quitado es cancilleria
    def _invoice_have_ret_lines(self, cr, uid, ids, field_name, args, context={}):
        result = {}
        for invoice in self.browse(cr, uid, ids, context):
            # si no tiene lineas de retenciones y no esta en estado borrador, no tiene retenciones
            if not invoice.invoice_ret_line_ids and invoice.state not in ('draft','sice'):
                result[invoice.id] = False
            else:
            # de no cumplirse los anteriores, tiene retenciones
                result[invoice.id] = True
        return result

    def action_move_create(self, cr, uid, ids, context=None):
        # check retention before
        if context is None:
            context = {}
        if self.check_invoice_retentions(cr, uid, ids, context):
            res = self.action_move_create_with_retention(cr, uid, ids, context)
        else:
            res = super(account_invoice_ext_ret, self).action_move_create(cr, uid, ids, context)
        return res

    def check_invoice_retentions(self, cr, uid, ids, context):
        for inv in self.browse(cr, uid, ids, context=context):
            if inv.invoice_ret_lines:
                return True
        return False

    def _have_retention(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = any(ret_line.id for ret_line in invoice.invoice_ret_line_ids) or any(ret_line.id for ret_line in invoice.invoice_ret_global_line_ids)
        return res


    HELP_RET_TEXT = _('''Automatic: The system identify to taxs and make the retention document automatic, \
    Manual: The user insert the retention number \
    Group: Use the option to group the system invoices on one retention document.''')

    HELP_RET_TEXT2 = '''Automatico: El sistema identificara los impuestos y creara la retencion automaticamente, \
    Manual: El usuario ingresara el numero de retencion \
    Agrupar: Podra usar la opcion para agrupar facturas del sistema en una sola retencion.'''

    #TC unidad indexada
    def _get_tc_ui_fnc ( self, cr, uid, ids, fieldname, args, context = None ):
        res = {}
        for invoice in self.browse ( cr, uid, ids, context = context ):
            res[invoice.id] = invoice.rate_ui or 1
        return res

    def _search_tc_ui_fnc(self, cr, uid, obj, field_name, args, context=None):
        if not context:
            context= {}
        ids = self.search(cr, uid, [])
        res = []
        datos = self._get_tc_ui_fnc(cr, uid, ids, field_name, args, context=context)
        for arg in args:
            if arg[0] == 'tipo_cambio_ui_fnc':
                for id, tc_fnc in datos.items():
                    if tc_fnc == arg[2]:
                        res.append(id)
        return [('id', 'in', res)]

    def _get_default_rate_ui(self, cr, uid, context=None):
        if context is None:
            context = {}
        period_obj = self.pool.get('account.period')
        ctx = context.copy()

        date_after_month = datetime.date.today() - relativedelta(months=1)
        period_ids = period_obj.find(cr, uid, date_after_month, context=ctx)
        if period_ids:
            period_id = period_ids and period_ids[0]
            p = period_obj.browse(cr, uid, period_id)
            ctx.update({'date': p.date_stop})
        else:
            ctx.update({'date': time.strftime('%Y-%m-%d')})

        currency_obj = self.pool.get('res.currency')
        ui_currency_id = currency_obj.search (cr, uid, [('name','=','UI')])
        if len(ui_currency_id):
            ui_currency_id = ui_currency_id[0]
        else:
            raise osv.except_osv(_('Error!'),
                            _(u'Deberá cargar la moneda Unidad Indexada.'))
        currency = currency_obj.browse(cr, uid, ui_currency_id, context=ctx)
        # incidencia 479
        if currency.rate_silent != 0:
            return currency.rate
        return 1

    def _get_default_date_ui(self, cr, uid, context=None):
        if context is None:
            context = {}
        period_obj = self.pool.get('account.period')
        ctx = context.copy()

        date_after_month = datetime.date.today() - relativedelta(months=1)
        period_ids = period_obj.find(cr, uid, date_after_month, context=ctx)
        if period_ids:
            period_id = period_ids and period_ids[0]
            p = period_obj.browse(cr, uid, period_id)
            return p.date_stop
        return False
    #Fin tipo cambio UI

    _columns = {
        'amount_ttal_ret':fields.function(_get_totales_ret, multi='totales', type='float', digits_compute=dp.get_precision('Account'),
                                          string=u'Total a retener'),
        # cambio de forma de llamar metodos #003 Cambios  todos campos funcional y que no se guardan en base de datos
        'amount_ttal_ret_base':fields.function(_get_totales_ret, multi='totales', type='float', digits_compute=dp.get_precision('Account'), string=u'Total a retener moneda base'),
        #003 Campos para intercambio con siif, cuadro resumen Importes SIIF. + Campos totales nominales definidos en fact proveedores
        'amount_ttal_liq_pesos':fields.function(_get_totales_ret, multi='totales', type='float', digits=(16,0), string=u'Líquido pagable'),
        'amount_ttal_ret_pesos':fields.function(_get_totales_ret, multi='totales', type='float', digits=(16,0), string=u'Total retenciones'),
        'amount_ttal_impuestos_pesos':fields.function(_get_totales_ret, multi='totales', type='float', digits=(16,0), string=u'Impuestos en pesos'),
        # Totales nominal
        'total_reponer':fields.function(_get_totales_ret, multi='totales', type='float', digits=(16,0), string=u'Total a Reponer', help=u'Monto total a reponer. Monto pagado + Retenciones'),
        'total_nominal_divisa_cpy': fields.function(_get_totales_ret, method=True, multi='totales', string='Total nominal', type='float', digits_compute=dp.get_precision('Account')), #total nominal = total - retenciones no se redondea
        'total_nominal_divisa': fields.function(_get_totales_ret, method=True, multi='totales', string='Total nominal', type='float', digits=(16,0)), #total nominal = total - retenciones  round
        'total_nominal': fields.function(_get_totales_ret, method=True, multi='totales', string='Total nominal en pesos', type='float', digits=(16,0)),  #total nominal = total - retenciones  round
        #003 Campos para intercambio con siif, cuadro resumen Importes SIIF
        # 'amount_ttal_ret_base':fields.function(_get_total_ret_base, type='float', digits_compute=dp.get_precision('Account'), string=u'Total a retener moneda base'),
        # se define en factura de proveedor
        # 'company_currency_id': fields.related('company_id','currency_id',  type='many2one', relation='res.currency', string=u'Moneda empresa',store=False, readonly=True),
        'invoice_ret_lines': fields.function(_have_retention, string='Invoice Retention Lines', type='boolean', help="It indicates that an invoice has retention line"),
        'invoice_ret_line_ids': fields.one2many('account.retention.line', 'invoice_id', 'Invoice Retention Lines'), #, readonly=True, states={'sice':[('readonly',False)]}),
        'invoice_ret_global_line_ids': fields.one2many('account.global.retention.line', 'invoice_id', 'Invoice Global Retention Lines'),
        #004 - Retenciones IRPF
        'invoice_ret_irpf_lines': fields.one2many('account.retention.line.irpf', 'invoice_id', u'Retención 7% IRPF'),
        #004 Tipo de cambio unidad indexada
        'fecha_tc_rate_ui': fields.date('Fecha tipo cambio UI'),
        'rate_ui': fields.float(string='TC UI',digits=(10,5),help=u"Tipo de cambio UI."),
        'tipo_cambio_ui_fnc': fields.function(_get_tc_ui_fnc, fnct_search=_search_tc_ui_fnc, string = u'Tipo de cambio UI', type='float', digits=(10,5)),
    }

    _defaults = {
        # 'date_invoice': time.strftime('%Y-%m-%d'),
        'date_invoice': lambda *a: datetime.date.today().strftime('%Y-%m-%d'),
        # 'amount_total_retention':0.0,
        'invoice_ret_lines': False,
        'fecha_tc_rate_ui': _get_default_date_ui,
        'rate_ui': _get_default_rate_ui,
        # self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, c).company_id.es_cancilleria and
    }

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'invoice_ret_line_ids': False,
        })
        return super(account_invoice_ext_ret, self).copy(cr, uid, id, default, context=context)

    # pasar a la nueva api
    # def button_reset_taxes(self, cr, uid, ids, context=None):
    #     if context is None:
    #         context = {}
    #     ctx = context.copy()
    #     summary_ret_obj = self.pool.get('account.invoice.summary.ret')
    #     for id in ids:
    #         cr.execute("DELETE FROM account_invoice_summary_ret WHERE invoice_id=%s", (id,))
    #         partner = self.browse(cr, uid, id, context=ctx).partner_id
    #         if partner.lang:
    #             ctx.update({'lang': partner.lang})
    #         for summ_ret in summary_ret_obj.compute(cr, uid, id, context=ctx).values():
    #             summary_ret_obj.create(cr, uid, summ_ret)
        # return super para hacer el funcionamiento estandar
    #     return super(account_invoice_ext_ret, self).button_reset_taxes(cr, uid, ids, context=context)


    def onchange_fecha_ui(self, cr, uid, ids, date_tc_rate_ui):
        context = {}
        if not date_tc_rate_ui:
            return {'value': {'rate_ui': False}}
        if date_tc_rate_ui:
            context.update({'date': date_tc_rate_ui})
        else:
            context.update({'date': time.strftime('%Y-%m-%d')})

        currency_obj = self.pool.get('res.currency')
        ui_currency_id = currency_obj.search (cr, uid, [('name','=','UI')])
        if len(ui_currency_id):
            ui_currency_id = ui_currency_id[0]
        else:
            raise osv.except_osv(_('Error!'),
                            _(u'Deberá cargar la moneda Unidad Indexada.'))

        currency = currency_obj.browse(cr, uid, ui_currency_id, context=context)
        # incidencia 119 de facturas
        if currency.rate_silent != 0:
            rate = currency.rate
            return {'value': {'rate_ui': rate, 'tipo_cambio_ui_fnc':rate}}
        return {'value': {'rate_ui': False, 'tipo_cambio_ui_fnc':False}}


    # metodo para eliminar lineas de retencion vacias. Se ejecuta cuando se contabiliza la factura
    def action_review_retention_lines(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # in_grp = self.pool.get('res.users').has_group(cr,uid,'grp_compras_estatales.group_grp_mrree_cancilleria')
        # if in_grp:
        ret_line_obj = self.pool.get('account.retention.line')
        obj_global_retline = self.pool.get('account.global.retention.line')
        obj_retline_irpf = self.pool.get('account.retention.line.irpf')
        for obj_inv in self.browse(cr, uid, ids, context=context):
            line_ids = ret_line_obj.search(cr, uid,[('invoice_id','=',obj_inv.id)], context=context)
            delete_ids = []
            for ret_line in ret_line_obj.browse(cr, uid, line_ids, context=context):
                if not ret_line.retention_line_ret_ids:
                    delete_ids.append(ret_line.id)
            if delete_ids:
                cr.execute('delete from account_retention_line where id in %s', (tuple(delete_ids),))
            global_ret_lines_ids = obj_global_retline.search(cr, uid,[('invoice_id','=',obj_inv.id)], context=context)
            delete2_ids = []
            for gbl_ret_line in obj_global_retline.browse(cr, uid, global_ret_lines_ids, context=context):
                if not gbl_ret_line.amount_ret != 0.0:
                    delete2_ids.append(gbl_ret_line.id)
            if delete2_ids:
                cr.execute('delete from account_global_retention_line where id in %s', (tuple(delete2_ids),))
                # if obj_inv.invoice_ret_line_ids == [] and obj_inv.invoice_ret_global_line_ids == []:
                #     self.write(cr, uid, obj_inv.id, {'invoice_ret_lines':False})

            #Eliminando las lineas si no fueron cargadas con retencion

            # Siempre deben ser 2 lineas
            ret_lines_irpf_ids = obj_retline_irpf.search(cr, uid,[('invoice_id','=',obj_inv.id),('retention_id','=',False)], context=context)
            if ret_lines_irpf_ids:
                # Si la linea local no tiene cargada retenciones, no debera
                local_lines_irpf_ids = obj_retline_irpf.search(cr, uid,[('invoice_id','=',obj_inv.id)], context=context)
                if len(local_lines_irpf_ids)>1:
                    raise osv.except_osv(_('Error!'),
                        _(u'Deberá cargar la retención en la línea de IRPF.'))
                delete3_ids = []
                for ret_irpf_line in obj_retline_irpf.browse(cr, uid, ret_lines_irpf_ids, context=context):
                    if not ret_irpf_line.amount_ret > 0.0:
                        delete3_ids.append(ret_irpf_line.id)
                if delete3_ids:
                    cr.execute('delete from account_retention_line_irpf \
                            where id in %s', (tuple(delete3_ids),))
            #Fin para eliminacion de lineas con cero

        return True

account_invoice_ext_ret()
