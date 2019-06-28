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
import time
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class account_report_daily_invoices(osv.osv_memory):
    _name = "account.report.daily.invoices"
    _description = "Account Invoices Daily Report"

    _columns = {
        'filter_date': fields.date(u"Fecha de ingreso"),
        # 'fecha_format': fields.function(get_fecha, u"Fecha reporte", type='char'),
        'fecha': fields.date(u"Fecha"),
    }
    _defaults = {
        'filter_date': fields.date.context_today, #time.strftime('%Y-%m-%d'),
        'fecha': fields.date.context_today, #time.strftime('%Y-%m-%d'),
    }

    def print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}

        data = self.read(cr, uid, ids)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': 'account.invoice',
             'form': data
            }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.inv.daily.registered',
            'datas': datas,
            }

account_report_daily_invoices()
