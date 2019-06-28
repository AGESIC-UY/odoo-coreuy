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

import time
from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp

DOC_TYPE_SELECTION = [
    ('opi_invoice',u'Factura OPI'),
    ('obligacion_invoice',u'Obligación'),
    ('pasarela_invoice', u'Pasarela'),
    ('3en1_invoice',u'TresEnUno'),
    ('invoice',u'Factura'),
    ('ajuste_invoice', u'Ajuste Obligación'),
    ]

#Resumen de retenciones
class account_invoice_summary_retention(osv.osv):
    _name = "account.invoice.summary.ret"
    _description = "Invoice Summary Retention"
    _order = 'tipo_retencion desc, iva desc'

    _columns = {
        'invoice_id': fields.many2one('account.invoice', u'Factura', ondelete='cascade', select=True),
        'iva': fields.char(u'IVA', size=32),
        'monto_retencion': fields.float(u'Monto retención', digits_compute= dp.get_precision('Account')),
        'tipo_retencion': fields.selection([
            ('siif','Siif'),
            ('manual','Manual'),
            ],u'Tipo de retención', select=True, readonly=True),
        'doc_type': fields.related('invoice_id','doc_type', type='selection', selection=DOC_TYPE_SELECTION, readonly=True, store=True,string=u"Tipo de Factura"),
        'invoice_ret_line_id': fields.many2one('account.retention.line', 'Invoice Retention Line'),
        'invoice_ret_global_line_id': fields.many2one('account.global.retention.line', 'Invoice Global Retention Line'),
        'base_impuesto': fields.related('invoice_ret_line_id','base_retax',string=u'Impuesto',type='float',help=u'Base Impuesto'), # importe total factura
        'base_linea': fields.related('invoice_ret_line_id','base_ret_line',string=u'Importe sin impuestos',type='float',help=u'Base línea'),
        'group_id': fields.many2one('account.group.creditors','Grupo'), #002 Inicio    'Grupo acreedor'
        'creditor_id': fields.many2one('account.retention.creditors','Acreedor'), #acreedor  'Acreedor'
        # campo para integracion siif, enlace
        'retention_id': fields.many2one('account.retention',string=u'Retención')
    }

    _defaults = {
        'base_impuesto': 0.0,
        'base_linea': 0.0,
    }

    def compute(self, cr, uid, invoice_id, context=None):
        tax_grouped = {}
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        cur = inv.currency_id

        def amount_ret_compute(ret, base_retax=0, base_ret_line=0):
            if ret.base_compute == 'ret_tax':
                if base_retax:
                    return base_retax * ret.percent / 100
            elif ret.base_compute == 'ret_line_amount':
                if base_ret_line:
                    return base_ret_line * ret.percent / 100
            else:
                return 0.0
        # LINEAS DE RETENCIONES
        for retline in inv.invoice_ret_line_ids:
            for retention_related in retline.retention_line_ret_ids:
                t_amount_ret = amount_ret_compute(retention_related, retline.base_retax,retline.base_ret_line)
                val={}
                val['invoice_id'] = inv.id
                val['iva'] = retention_related.name or False
                val['retention_id'] = retention_related.id
                val['monto_retencion'] = t_amount_ret
                val['tipo_retencion'] = 'siif'
                val['invoice_ret_line_id'] = retline.id
                val['group_id'] = retention_related.grupo_acreedor_id and retention_related.grupo_acreedor_id.id or False
                val['creditor_id'] = retention_related.acreedor_id and retention_related.acreedor_id.id or False

                key = (val['invoice_ret_line_id'], retention_related.id)
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['monto_retencion'] += val['monto_retencion']
                    # agrupar por misma retencion en misma linea

        # RETENCION GLOBAL
        for ret_global_line in inv.invoice_ret_global_line_ids:
            val={}
            val['invoice_id'] = inv.id
            val['iva'] = ret_global_line.name or False
            val['monto_retencion'] = ret_global_line.amount_ret
            val['tipo_retencion'] = 'manual'
            val['invoice_ret_global_line_id'] = ret_global_line.id
            val['group_id'] = ret_global_line.group_id and ret_global_line.group_id.id or False
            val['creditor_id'] = ret_global_line.creditor_id and ret_global_line.creditor_id.id or False

            key = (val['invoice_ret_global_line_id'], val['iva'])
            if not key in tax_grouped:
                tax_grouped[key] = val
            else:
                tax_grouped[key]['monto_retencion'] += val['monto_retencion']
                # agrupar por misma retencion en misma linea

        for t in tax_grouped.values():
            if t['monto_retencion']:
                t['monto_retencion'] = cur_obj.round(cr, uid, cur, t['monto_retencion'])
        return tax_grouped

    def move_line_get(self, cr, uid, invoice_id):
        res = []
        cr.execute('SELECT * FROM account_invoice_summary_ret WHERE invoice_id=%s', (invoice_id,))
        for t in cr.dictfetchall():
            if not t['monto_retencion']:
                continue
            res.append({
                'invoice_id':t['invoice_id'],
                'iva': t['iva'],
                'tipo_retencion': t['tipo_retencion'],
                'invoice_ret_line_id': t['invoice_ret_line_id'] or False,
                'invoice_ret_global_line_id': t['invoice_ret_global_line_id'] or False,
                'monto_retencion': t['monto_retencion'] or 0.0,
            })
        return res
account_invoice_summary_retention()


class account_invoice_sum_group_retention(osv.osv):
    _name = "account.invoice.summary.group.ret"
    _description = "Invoice Summary Grouping Retention"
    _order = 'tipo_retencion desc, iva desc'

    def _get_importe_base(self, cr, uid, ids, fields, args, context=None):
        res = {}
        if context is None:
            context = {}
        currency_obj = self.pool.get('res.currency')
        for summary in self.browse(cr,uid,ids,context=context):
            moneda = summary.invoice_id.currency_id.id
            moneda_base = summary.invoice_id.company_id.currency_id.id
            if moneda != moneda_base:
                ctx = context.copy()
                ctx.update({'date': summary.invoice_id.date_invoice or time.strftime('%Y-%m-%d')})
                #ctx.update({'date': summary.invoice_id.fecha_tipo_cambio or time.strftime('%Y-%m-%d'), 'pricelist_type':'presupuesto'})
                monto_retencion_pesos = currency_obj.compute(cr, uid, moneda, moneda_base, summary.monto_retencion_unround, context=ctx)
                base_impuesto_pesos = currency_obj.compute(cr, uid, moneda, moneda_base, summary.base_impuesto, context=ctx)
                base_linea_pesos = currency_obj.compute(cr, uid, moneda, moneda_base, summary.base_linea, context=ctx)

                base_impuesto_pesos_unround = currency_obj.compute(cr, uid, moneda, moneda_base, summary.base_impuesto_unround, context=ctx)
                res[summary.id] = {
                    'monto_retencion_pesos': round(monto_retencion_pesos) or 0.0,
                    'base_impuesto_pesos': round(base_impuesto_pesos),
                    'base_linea_pesos': round(base_linea_pesos),
                    'base_impuesto_pesos_unround': base_impuesto_pesos_unround, #005-sin redondear
                }
            else:
                res[summary.id] = {
                    'monto_retencion_pesos': round(summary.monto_retencion_unround) or 0.0,
                    'base_impuesto_pesos': round(summary.base_impuesto),
                    'base_linea_pesos': round(summary.base_linea),
                    'base_impuesto_pesos_unround': summary.base_impuesto_unround, #005- sin redondear
                }
        return res

    #CORRIGIENDO DECIMALES
    def _get_ret_redond(self, cr, uid, ids, fields, args, context=None):
        res = {}
        if context is None:
            context = {}
        currency_obj = self.pool.get('res.currency')
        for summary in self.browse(cr,uid,ids,context=context):
            moneda = summary.invoice_id.currency_id.id
            moneda_base = summary.invoice_id.company_id.currency_id.id
            ret = 0.0
            if summary.tipo_retencion == 'siif':
                if summary.retention_id and summary.invoice_ret_line_id:
                    # ret = summary.base_impuesto * summary.retention_id.percent / 100
                    if summary.retention_id.base_compute == 'ret_tax':
                        ret = summary.base_impuesto * summary.retention_id.percent / 100.00
                    elif summary.retention_id.base_compute == 'ret_line_amount':
                        ret = summary.base_linea * summary.retention_id.percent / 100.00
                    else:
                        ret = 0.0
                elif not summary.invoice_ret_line_id:
                    ret = summary.monto_retencion_unround
            else:
            #     Manual
                ret = summary.monto_retencion_unround

            # Variante 1
            if moneda != moneda_base:
                # Variante 2
                ret2 = 0.0
                if summary.retention_id and summary.base_impuesto_pesos:
                    ret2 = summary.base_impuesto_pesos * summary.retention_id.percent / 100

                ctx = context.copy()
                ctx.update({'date': summary.invoice_id.date_invoice or time.strftime('%Y-%m-%d')})
                m_pesos = currency_obj.compute(cr, uid, moneda, moneda_base, ret, context=ctx)

                if ret2 > 0 and abs(round(m_pesos) - round(ret2)) > 0:
                    m_pesos = ret2

                res[summary.id] = {
                    'ret_amount_round': round(ret) or 0.0,
                    'ret_amount_pesos_round': round(m_pesos) or 0.0,
                }
            else:
                res[summary.id] = {
                    'ret_amount_round': round(ret) or 0.0,
                    'ret_amount_pesos_round': round(ret) or 0.0,
                }
        return res

    _columns = {
        'invoice_id': fields.many2one('account.invoice', u'Factura', ondelete='cascade', select=True),
        'iva': fields.char(u'IVA', size=32),
        'monto_retencion': fields.float(u'Monto retención', digits=(16,0),help=u'Monto retención redondeado y calculado a partir de base impuesto sin redondear.'),  #  digits_compute= dp.get_precision('Account')),
        'monto_retencion_unround': fields.float(u'Monto retención', digits_compute= dp.get_precision('Account'), help=u'Monto retención sin redondear'),  #  digits_compute= dp.get_precision('Account')),

        'monto_retencion_pesos':fields.function(_get_importe_base, method=True, multi='importe_base', type='float', digits=(16,0), string=u'Monto retención pesos'),
        'tipo_retencion': fields.selection([
            ('siif','Siif'),
            ('manual','Manual'),
            ],u'Tipo de retención', select=True, readonly=True),
        'invoice_ret_line_id': fields.many2one('account.retention.line', 'Invoice Retention Line'),
        'base_impuesto': fields.float(string=u'Impuesto', digits=(16,0),help=u'Base Impuesto'),
        'base_impuesto_pesos':fields.function(_get_importe_base, string=u'Impuesto en UYU', method=True, multi='importe_base', type='float', digits=(16,0)),

        'base_linea': fields.float(string=u'Importe sin impuestos', digits=(16,0),help=u'Base línea'),
        'base_linea_pesos':fields.function(_get_importe_base, string=u'Importe sin impuestos en UYU', method=True, multi='importe_base', type='float', digits=(16,0)),
        'group_id': fields.many2one('account.group.creditors','Grupo'), #002 Inicio    'Grupo acreedor'
        'creditor_id': fields.many2one('account.retention.creditors','Acreedor'), #acreedor  'Acreedor'
        # campo para integracion siif, enlace
        'retention_id': fields.many2one('account.retention',string=u'Retención'),
        #Campos para ver montos de retencion redondeados
        'ret_amount_round':fields.function(_get_ret_redond, string=u'Retención redondeado ME', method=True, multi='ret', type='float', digits=(16,0), help=u'Monto retención redondeado y calculado a partir de base impuesto redondeado.'), # misma funcion que monto_retencion
        'ret_amount_pesos_round':fields.function(_get_ret_redond, string=u'Retención redondeado', method=True, multi='ret', type='float', digits=(16,0),help=u'Monto retención pesos redondeado y calculado a partir de base impuesto redondeado'),
        #Otro calculo de retenciones, rendondeadas
        'base_impuesto_unround': fields.float(string=u'Impuesto Unround', digits_compute= dp.get_precision('Account'),help=u'Base Impuesto Unround'),
        'base_impuesto_pesos_unround':fields.function(_get_importe_base, string=u'Impuesto Unround en UYU', method=True, multi='importe_base', type='float', digits_compute= dp.get_precision('Account'),help=u'Base Impuesto UYU Unround'),
    }

    _defaults = {
        'base_impuesto': 0.0,
        'base_impuesto_unround': 0.0,
        'base_linea': 0.0,
        'monto_retencion_unround': 0.0,
    }

    def compute(self, cr, uid, invoice_id, context=None):
        tax_grouped = {}

        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        def amount_ret_compute(id_ret, base_tax=0.0, base_line_amount=0.0):
            ret = self.pool.get('account.retention').browse(cr, uid, id_ret)
            if ret.base_compute == 'ret_tax':
                return base_tax * ret.percent / 100.00
            elif ret.base_compute == 'ret_line_amount':
                return base_line_amount * ret.percent / 100.00
            else:
                return 0.0
        # LINEAS DE RETENCIONES

        for retline in inv.invoice_ret_line_ids:
            for retention_related in retline.retention_line_ret_ids:
                if retention_related.grupo_acreedor_id and retention_related.grupo_acreedor_id.id \
                        and retention_related.acreedor_id and retention_related.acreedor_id.id:

                    t_amount_ret = amount_ret_compute(retention_related.id, retline.base_retax,retline.base_ret_line)
                    val={}
                    val['invoice_id'] = inv.id
                    val['iva'] = retention_related.name or False
                    val['retention_id'] = retention_related.id or False

                    val['monto_retencion_unround'] = t_amount_ret
                    val['tipo_retencion'] = 'siif'
                    val['invoice_ret_line_id'] = retline.id
                    val['group_id'] = retention_related.grupo_acreedor_id and retention_related.grupo_acreedor_id.id or False
                    val['creditor_id'] = retention_related.acreedor_id and retention_related.acreedor_id.id or False

                    val['base_impuesto'] = retline.base_retax or 0.0
                    val['base_linea'] = retline.base_ret_line or 0.0

                    key = (val['group_id'], val['creditor_id'], val['retention_id'])
                    if not key in tax_grouped:
                        tax_grouped[key] = val
                    else:

                        tax_grouped[key]['monto_retencion_unround'] += val['monto_retencion_unround']
                        tax_grouped[key]['base_impuesto'] += val['base_impuesto']
                        tax_grouped[key]['base_linea'] += val['base_linea']
                        # agrupar por misma retencion en misma linea

        for t in tax_grouped.values():
            t_amount_ret = amount_ret_compute(t['retention_id'], t['base_impuesto'], t['base_linea'])
            t['monto_retencion'] = round(t_amount_ret)
            t['base_impuesto_unround'] = t['base_impuesto'] #005-base impuesto unround
            t['base_impuesto'] = round(t['base_impuesto'])
            t['base_linea'] = round(t['base_linea'])

        # RETENCION GLOBAL
        for ret_global_line in inv.invoice_ret_global_line_ids:
            if ret_global_line.group_id and ret_global_line.group_id.id and ret_global_line.creditor_id \
                    and ret_global_line.creditor_id.id:
                val={}
                val['invoice_id'] = inv.id
                val['iva'] = ret_global_line.name or False
                val['monto_retencion'] = ret_global_line.amount_ret
                val['monto_retencion_unround'] = ret_global_line.amount_ret
                val['tipo_retencion'] = 'manual'
                val['group_id'] = ret_global_line.group_id and ret_global_line.group_id.id or False
                val['creditor_id'] = ret_global_line.creditor_id and ret_global_line.creditor_id.id or False
                val['base_linea'] = 0.0

                key = (val['group_id'], val['creditor_id'], val['iva'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['monto_retencion'] += val['monto_retencion']

        for t in tax_grouped.values():
            t['monto_retencion'] = round(t['monto_retencion'])

        #AGRUPAR RETENCIONES
        #RENTENCION IRPF
        for ret_irpf_line in inv.invoice_ret_irpf_lines:
            # si no se calcula la retencion, no se pasa al resumen
            if not ret_irpf_line.amount_ret or not ret_irpf_line.retention_id:
                continue

            if ret_irpf_line.retention_id.grupo_acreedor_id and ret_irpf_line.retention_id.grupo_acreedor_id.id \
                    and ret_irpf_line.retention_id.acreedor_id and ret_irpf_line.retention_id.acreedor_id.id:
                val={}
                val['invoice_id'] = inv.id
                val['retention_id'] = ret_irpf_line.retention_id and ret_irpf_line.retention_id.id or False
                val['iva'] = ret_irpf_line.retention_id and ret_irpf_line.retention_id.name or False
                val['monto_retencion'] = ret_irpf_line.amount_ret
                val['monto_retencion_unround'] = ret_irpf_line.amount_ret
                val['tipo_retencion'] = 'siif'
                val['group_id'] = ret_irpf_line.retention_id.grupo_acreedor_id and ret_irpf_line.retention_id.grupo_acreedor_id.id or False
                val['creditor_id'] = ret_irpf_line.retention_id.acreedor_id and ret_irpf_line.retention_id.acreedor_id.id or False

                val['base_linea'] = ret_irpf_line.base_amount_pend or 0.0

                key = (val['group_id'], val['creditor_id'], val['retention_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['monto_retencion'] += val['monto_retencion']
                    tax_grouped[key]['monto_retencion_unround'] += val['monto_retencion_unround']
                    tax_grouped[key]['base_linea'] += val['base_linea']
                        # agrupar por misma retencion en misma linea

        for t in tax_grouped.values():
            t['monto_retencion'] = round(t['monto_retencion'])
            t['monto_retencion_unround'] = t['monto_retencion_unround']
            t['base_linea'] = round(t['base_linea'])

        return tax_grouped

    def move_line_get(self, cr, uid, invoice_id):
        res = []
        cr.execute('SELECT * FROM account_invoice_summary_group_ret WHERE invoice_id=%s', (invoice_id,))
        for t in cr.dictfetchall():
            if not t['monto_retencion']:
                continue
            res.append({
                'invoice_id':t['invoice_id'],
                'iva': t['iva'],
                'tipo_retencion': t['tipo_retencion'],
                'invoice_ret_line_id': t['invoice_ret_line_id'] or False,
                'monto_retencion': t['monto_retencion'] or 0.0,
                'monto_retencion_unround': t['monto_retencion_unround'] or 0.0,
                'base_impuesto': t['base_impuesto'] or 0.0,
                'base_impuesto_unround': t['base_impuesto_unround'] or 0.0, #005-agregado campo
                'base_linea': t['base_linea'] or 0.0,
                'group_id': t['group_id'] or 0.0,
                'creditor_id': t['creditor_id'] or 0.0,
                'retention_id': t['retention_id'] or 0.0,
            })
        return res

account_invoice_sum_group_retention()
