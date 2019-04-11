# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) BrowseInfo (http://browseinfo.in)
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

class account_report_general_ledger(osv.osv_memory):
    _inherit = "account.report.general.ledger"
    _description = "General Ledger Report"
    _columns = {
              'currency_id' : fields.many2one('res.currency', 'Currency'),
    }

    def print_report_excel(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        data['form'].update(self.read(cr, uid, ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby'])[0])
        if not data['form']['fiscalyear_id']:# GTK client problem onchange does not consider in save record
            data['form'].update({'initial_balance': False})
        
        if data['form'].get('currency_id',False):
            data['form']['currency_id'] =  data['form']['currency_id'][0]
        if data['form'].get('period_to',False):
            data['form']['period_to'] =  data['form']['period_to'][0]
        if data['form'].get('period_from',False):
            data['form']['period_from'] =  data['form']['period_from'][0]
        if data['form'].get('used_context',False) and data['form']['used_context'].get('period_to', False):
            data['form']['used_context']['period_to'] =  data['form']['used_context']['period_to'][0]
        if data['form'].get('used_context',False) and data['form']['used_context'].get('period_from',False):
            data['form']['used_context']['period_from'] =  data['form']['used_context']['period_from'][0]
        if data['form'].get('chart_account_id', False):
            data['form']['chart_account_id'] =  data['form']['chart_account_id'][0]
        if data['form'].get('fiscalyear_id', False):
            data['form']['fiscalyear_id'] =  data['form']['fiscalyear_id'][0]
        if data['form'].get('used_context', False) and data['form']['used_context'].get('chart_account_id', False):
            data['form']['used_context']['chart_account_id'] =  data['form']['used_context']['chart_account_id'][0]
        if data['form'].get('used_context', False) and data['form']['used_context'].get('fiscalyear', False):
            data['form']['used_context']['fiscalyear'] =  data['form']['used_context']['fiscalyear'][0]
        if data['form']['landscape']:
            return { 'type': 'ir.actions.report.xml', 'report_name': 'account_general_ledger_excel', 'datas': data}
        return { 'type': 'ir.actions.report.xml', 'report_name': 'account_general_ledger_excel', 'datas': data}
    
    def check_report_excel(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(cr, uid, ids, ['currency_id','date_from',  'date_to',  'fiscalyear_id', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move'])[0]
        used_context = self._build_contexts(cr, uid, ids, data, context=context)
        data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
        data['form']['used_context'] = used_context
        return self.print_report_excel(cr, uid, ids, data, context=context)
account_report_general_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
