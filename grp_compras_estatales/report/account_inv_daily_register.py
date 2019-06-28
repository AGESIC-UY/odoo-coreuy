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
from datetime import datetime
from openerp.report import report_sxw
from openerp import SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)

class account_daily_registered(report_sxw.rml_parse):
    _name = 'report.account.inv.daily.registered'

    def __init__(self, cr, uid, name, context=None):
        super(account_daily_registered, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'get_lines': self.get_lines,
            'time': time,
            'get_today_date': self.get_today_date,
            'get_ingreso_date': self.get_ingreso_date,
        })

    def get_today_date(self, data):
        DayL = ['Lunes','Martes',u'Miércoles','Jueves','Viernes',u'Sábado','Domingo']
        MonthL = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
        ds_date =  datetime.strptime(data['fecha'], '%Y-%m-%d') #004 Inicio, cambio de llamada al mes
        string_date = ("%s, %s de %s de %s") % (DayL[ds_date.weekday()], ds_date.day, MonthL[ds_date.month-1], ds_date.year)
        return string_date

    def get_ingreso_date(self, data):
        return data['filter_date'] or ''

    def get_lines(self, data):
        lines = []
        filter_date = 'filter_date' in data and data['filter_date'] or time.strftime('%Y-%m-%d')
        company_id = self.pool.get('res.users').browse(self.cr, SUPERUSER_ID, self.uid).company_id.id
        ids2 = self.pool.get('account.invoice').search(self.cr, self.uid,[('create_date_date','=',filter_date),('type','=','in_invoice'),('state','!=','draft'),('company_id','=',company_id),('doc_type','=','invoice')], order='nro_factura_grp asc')

        if ids2:
            for invoice in self.pool.get('account.invoice').browse(self.cr, SUPERUSER_ID, ids2):
                vals = {
                    'orden_compra': invoice.orden_compra_id.name or '',
                    'proveedor': invoice.partner_id.name or '',
                    'number': invoice.number or '', #Number
                    'invoice_number': invoice.supplier_invoice_number or '', #003 Inicio, mostrar numero de factura
                    'date_invoice': invoice.date_invoice and datetime.strptime(invoice.date_invoice,"%Y-%m-%d") or '',
                    'currency_base': invoice.company_id.currency_id,
                    'currency_id': invoice.currency_id,
                    'nro_interno': invoice.nro_factura_grp or ''
                }
                vals['amount_pesos'] = invoice.currency_id.id == invoice.company_currency_id.id and invoice.amount_total or 0
                vals['amount_divisa'] = invoice.currency_id.id != invoice.company_currency_id.id and invoice.amount_total or 0
                lines.append(vals)
        return lines

report_sxw.report_sxw('report.account.inv.daily.registered', 'account.invoice', 'addons/grp_compras_estatales/report/account_inv_daily_register.rml', parser=account_daily_registered, header=False)