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

import xlwt
from datetime import datetime
from openerp.osv import osv
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell
from openerp.tools.translate import _
from openerp.addons.account_financial_report_webkit_xls.report.general_ledger_xls \
    import general_ledger_xls
from .general_ledger import GeneralLedgerWebkitExt
from utils import compute_amounts_in_currency


_column_sizes = [
    ('date', 12),
    ('period', 12),
    ('move', 20),
    ('journal', 12),
    ('account_code', 12),
    ('partner', 20),
    ('label', 30),
    ('ref', 30),
    ('counterpart', 30),
    ('debit', 15),
    ('credit', 15),
    ('cumul_bal', 15),
    ('curr_debit', 15),
    ('curr_credit', 15),
    ('curr_cumul_bal', 15),
    ('curr_bal', 15),
    ('curr_code', 15),
]

report_xls.date_format = 'DD/MM/YYYY'

class general_ledger_xls_ext(general_ledger_xls):
    column_sizes = [x[1] for x in _column_sizes]

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        context = {'lang': (_p.get('lang') or 'en_US')}

        ws = wb.add_sheet(_p.report_name[:31])
        ws.panes_frozen = True
        ws.remove_splits = True
        ws.portrait = 0  # Landscape
        ws.fit_width_to_pages = 1
        row_pos = 0

        # set print header/footer
        ws.header_str = self.xls_headers['standard']
        ws.footer_str = self.xls_footers['standard']

        # cf. account_report_general_ledger.mako
        initial_balance_text = {'initial_balance': _('Computed'),
                                'opening_balance': _('Opening Entries'),
                                False: _('No')}

        # Title
        cell_style = xlwt.easyxf(_xs['xls_title'])
        report_name = ' - '.join([_p.report_name.upper(),
                                 _p.company.partner_id.name,
                                 _p.company.currency_id.name])
        c_specs = [
            ('report_name', 1, 0, 'text', report_name),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style)

        # write empty row to define column sizes
        c_sizes = self.column_sizes
        c_specs = [('empty%s' % i, 1, c_sizes[i], 'text', None)
                   for i in range(0, len(c_sizes))]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, set_column_size=True)

        # Alternative Currency
        base_currency_id = _p.company.currency_id.id
        currency_obj = self.pool.get('res.currency')
        alt_curr_ids = currency_obj.search(self.cr, self.uid, [('alt_currency','=',True)])
        alt_curr_id = alt_curr_ids and alt_curr_ids[0] or False
        usd_curr_ids = currency_obj.search(self.cr, self.uid, [('name','=','USD')])
        usd_curr_id = usd_curr_ids and usd_curr_ids[0] or False
        display_curr_columns = data.get('form',{}).get('display_curr_columns', False) and \
                                (alt_curr_id and base_currency_id != alt_curr_id or False) or False
        ## Alternative currency rate options
        context.update({
            'curr_rate_option': data.get('form',{}).get('curr_rate_option', False),
            'curr_rate_date': data.get('form',{}).get('curr_rate_date', False),
            'curr_rate': data.get('form',{}).get('curr_rate', False),
        })

        # Header Table
        cell_format = _xs['bold'] + _xs['fill_blue'] + _xs['borders_all']
        cell_style = xlwt.easyxf(cell_format)
        cell_style_center = xlwt.easyxf(cell_format + _xs['center'])
        c_specs = [
            ('coa', 2, 0, 'text', _('Chart of Account')),
            ('fy', 1, 0, 'text', _('Fiscal Year')),
            ('df', 3, 0, 'text', _p.filter_form(data) ==
             'filter_date' and _('Dates Filter') or _('Periods Filter')),
            ('af', 2, 0, 'text', _('Accounts Filter')),
            ('tm', 1, 0, 'text', _('Target Moves')),
            ('ib', 1, 0, 'text', _('Initial Balance')),
        ]
        if data.get('form',{}).get('filter_partner_ids', False):
            c_specs += [('partf', 2, 0, 'text', _('Partners Filter'))]
        if data.get('form',{}).get('filter_operating_unit_ids', False):
            c_specs += [('ouf', 2, 0, 'text', _('Operating Units Filter'))]
        if display_curr_columns:
            c_specs += [('altc', 2, 0, 'text', _('Alt. Currency'))]
            c_specs += [('altcro', 2, 0, 'text', _('Alt. Curr. Rate Option'))]

        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style_center)

        cell_format = _xs['borders_all']
        cell_style = xlwt.easyxf(cell_format)
        cell_style_center = xlwt.easyxf(cell_format + _xs['center'])
        c_specs = [
            ('coa', 2, 0, 'text', _p.chart_account.name),
            ('fy', 1, 0, 'text', _p.fiscalyear.name if _p.fiscalyear else '-'),
        ]
        df = _('From') + ': '
        if _p.filter_form(data) == 'filter_date':
            df += _p.start_date if _p.start_date else u''
        else:
            df += _p.start_period.name if _p.start_period else u''
        df += ' ' + _('To') + ': '
        if _p.filter_form(data) == 'filter_date':
            df += _p.stop_date if _p.stop_date else u''
        else:
            df += _p.stop_period.name if _p.stop_period else u''
        c_specs += [
            ('df', 3, 0, 'text', df),
            ('af', 2, 0, 'text', _p.accounts(data) and ', '.join(
                [account.code for account in _p.accounts(data)]) or _('All')),
            ('tm', 1, 0, 'text', _p.display_target_move(data)),
            ('ib', 1, 0, 'text', initial_balance_text[
             _p.initial_balance_mode]),
        ]
        # if data.get('form',{}).get('filter_location_ids', False):
        #     c_specs += [('locf', 2, 0, 'text', ', '.join(data['form']['filter_location_names']) )]
        if data.get('form',{}).get('filter_partner_ids', False):
            c_specs += [('partf', 2, 0, 'text', ', '.join(data['form']['filter_partner_names']) )]
        if data.get('form',{}).get('filter_operating_unit_ids', False):
            c_specs += [('ouf', 2, 0, 'text', ', '.join(data['form']['filter_operating_unit_names']) )]
        if display_curr_columns:
            c_specs += [('altc', 2, 0, 'text', currency_obj.read(self.cr, self.uid, alt_curr_id, ['name'])['name'] )]
            rate_option = _("Transaction Date")
            if data.get('form',{}).get('curr_rate_option', False)=='set_date':
                rate_option = _("Custom Date: ") + data.get('form',{}).get('curr_rate_date', '')
            elif data.get('form',{}).get('curr_rate_option', False)=='set_curr_rate':
                rate_option = _("Currency Rate: ") + str(data.get('form',{}).get('curr_rate', 0.0))
            c_specs += [('altcro', 2, 0, 'text', rate_option )]

        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style_center)
        ws.set_horz_split_pos(row_pos)
        row_pos += 1

        # Column Title Row
        cell_format = _xs['bold']
        c_title_cell_style = xlwt.easyxf(cell_format)

        # Column Header Row
        cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        c_hdr_cell_style = xlwt.easyxf(cell_format)
        c_hdr_cell_style_right = xlwt.easyxf(cell_format + _xs['right'])
        c_hdr_cell_style_center = xlwt.easyxf(cell_format + _xs['center'])
        c_hdr_cell_style_decimal = xlwt.easyxf(
            cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        # Column Initial Balance Row
        cell_format = _xs['italic'] + _xs['borders_all']
        c_init_cell_style = xlwt.easyxf(cell_format)
        c_init_cell_style_decimal = xlwt.easyxf(
            cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        c_specs = [
            ('date', 1, 0, 'text', _('Date'), None, c_hdr_cell_style),
            ('period', 1, 0, 'text', _('Period'), None, c_hdr_cell_style),
            ('move', 1, 0, 'text', _('Entry'), None, c_hdr_cell_style),
            ('journal', 1, 0, 'text', _('Journal'), None, c_hdr_cell_style),
            ('account_code', 1, 0, 'text',
             _('Account'), None, c_hdr_cell_style),
            ('partner', 1, 0, 'text', _('Customer'), None, c_hdr_cell_style),
        ]
        # if data.get('form',{}).get('filter_location_ids', False):
        #     c_specs += [('location', 1, 0, 'text', _('Location'), None, c_hdr_cell_style)]
        c_specs += [
            ('label', 1, 0, 'text', _('Label'), None, c_hdr_cell_style),
            ('ref', 1, 0, 'text', _('Reference'), None, c_hdr_cell_style),
            ('counterpart', 1, 0, 'text',
             _('Counterpart'), None, c_hdr_cell_style),
            ('debit', 1, 0, 'text', _('Debit'), None, c_hdr_cell_style_right),
            ('credit', 1, 0, 'text', _('Credit'),
             None, c_hdr_cell_style_right),
            ('cumul_bal', 1, 0, 'text', _('Cumul. Bal.'),
             None, c_hdr_cell_style_right),
        ]
        if display_curr_columns:
            c_specs += [
                ('curr_debit', 1, 0, 'text', _('Curr. Debit'),
                 None, c_hdr_cell_style_right),
                ('curr_credit', 1, 0, 'text', _('Curr. Credit'),
                 None, c_hdr_cell_style_right),
                ('curr_cumul_bal', 1, 0, 'text', _('Curr. Cumul. Bal.'),
                 None, c_hdr_cell_style_right),
            ]
        if _p.amount_currency(data):
            c_specs += [
                ('curr_bal', 1, 0, 'text', _('Curr. Bal.'),
                 None, c_hdr_cell_style_right),
                ('curr_code', 1, 0, 'text', _('Curr.'),
                 None, c_hdr_cell_style_center),
            ]
        c_specs += [
            ('move_ref', 1, 0, 'text', _('Move Ref.'),
             None, c_hdr_cell_style)
        ]
        c_hdr_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])

        # cell styles for ledger lines
        ll_cell_format = _xs['borders_all']
        ll_cell_style = xlwt.easyxf(ll_cell_format)
        ll_cell_style_center = xlwt.easyxf(ll_cell_format + _xs['center'])
        ll_cell_style_date = xlwt.easyxf(
            ll_cell_format + _xs['left'],
            num_format_str=report_xls.date_format)
        ll_cell_style_decimal = xlwt.easyxf(
            ll_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        account_voucher_obj = self.pool.get('account.voucher')
        invoice_obj = self.pool.get('account.invoice')
        cnt = 0
        ## Excel 2003 Límite Número de filas => 65.536
        rows_qty = sum([ len(v) for v in _p['ledger_lines'].values() ])
        if rows_qty > 65535:
            raise osv.except_osv(u'Advertencia', u'Excel (*.xls) no permite más de 65 mil filas, por favor agregue filtros para reducir la cantidad de registros.')
        ##
        for account in objects:

            display_initial_balance = _p['init_balance'][account.id]
            #display_initial_balance = _p['init_balance'][account.id] and \
            #    (_p['init_balance'][account.id].get(
            #        'debit', 0.0) != 0.0 or
            #        _p['init_balance'][account.id].get('credit', 0.0)
            #        != 0.0)
            display_ledger_lines = _p['ledger_lines'][account.id]

            if _p.display_account_raw(data) == 'all' or \
                    (display_ledger_lines or display_initial_balance):
                ###
                cnt += 1
                cumul_debit = 0.0
                cumul_credit = 0.0
                cumul_balance = 0.0
                cumul_balance_curr = 0.0
                if display_curr_columns:
                    cumul_alt_curr_balance = 0.0
                c_specs = [
                    ('acc_title', 10, 0, 'text',
                     ' - '.join([account.code, account.name])),
                ]
                row_data = self.xls_row_template(
                    c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, c_title_cell_style)
                row_pos = self.xls_write_row(ws, row_pos, c_hdr_data)
                row_start = row_pos

                if display_initial_balance:
                    init_balance = _p['init_balance'][account.id]
                    cumul_debit = init_balance.get('debit') or 0.0
                    cumul_credit = init_balance.get('credit') or 0.0
                    cumul_balance = init_balance.get('init_balance') or 0.0
                    cumul_balance_curr = init_balance.get(
                        'init_balance_currency') or 0.0
                    c_specs = [('empty%s' % x, 1, 0, 'text', None)
                               for x in range(6)]
                    c_specs += [
                        ('init_bal', 1, 0, 'text', _('Initial Balance')),
                        ('ref', 1, 0, 'text', None),
                        ('counterpart', 1, 0, 'text', None),
                        ('debit', 1, 0, 'number', cumul_debit,
                         None, c_init_cell_style_decimal),
                        ('credit', 1, 0, 'number', cumul_credit,
                         None, c_init_cell_style_decimal),
                        ('cumul_bal', 1, 0, 'number', cumul_balance,
                         None, c_init_cell_style_decimal),
                    ]
                    if display_curr_columns:
                        if context.get('curr_rate_option')=='trans_date' and alt_curr_id==usd_curr_id:
                            curr_cumul_debit = init_balance.get('usd_debit') or 0.0
                            curr_cumul_credit = init_balance.get('usd_credit') or 0.0
                            cumul_alt_curr_balance = init_balance.get('usd_init_balance') or 0.0
                        else:
                            curr_cumul_debit = compute_amounts_in_currency(self, self.cr, self.uid, cumul_debit, base_currency_id, alt_curr_id, context=context)
                            curr_cumul_credit = compute_amounts_in_currency(self, self.cr, self.uid, cumul_credit, base_currency_id, alt_curr_id, context=context)
                            cumul_alt_curr_balance = compute_amounts_in_currency(self, self.cr, self.uid, cumul_balance, base_currency_id, alt_curr_id, context=context)
                        c_specs += [
                            ('curr_debit', 1, 0, 'number', curr_cumul_debit,
                             None, c_init_cell_style_decimal),
                            ('curr_credit', 1, 0, 'number', curr_cumul_credit,
                             None, c_init_cell_style_decimal),
                            ('curr_cumul_bal', 1, 0, 'number', cumul_alt_curr_balance,
                             None, c_init_cell_style_decimal),
                        ]
                    if _p.amount_currency(data):
                        c_specs += [
                            ('curr_bal', 1, 0, 'number', cumul_balance_curr,
                             None, c_init_cell_style_decimal),
                            ('curr_code', 1, 0, 'text', None),
                        ]
                    row_data = self.xls_row_template(
                        c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, c_init_cell_style)

                for line in _p['ledger_lines'][account.id]:

                    cumul_debit += line.get('debit') or 0.0
                    cumul_credit += line.get('credit') or 0.0
                    cumul_balance_curr += line.get('amount_currency') or 0.0
                    cumul_balance += line.get('balance') or 0.0
                    label_elements = [ line.get('lname') or '' ]
                    ref_elements = []
                    # Origin of this Journal Item
                    move_id = line.get('move_id', False)
                    if line.get('invoice_id', False): # Check for invoice
                        if line.get('invoice_type', False) == 'out_invoice':
                            ref_elements.append(
                            "%s" % (u"Factura Cliente " + (line.get('invoice_number') or '')))
                        elif line.get('invoice_type', False) == 'out_refund':
                            ref_elements.append(
                            "%s" % (u"Nota de Crédito Cliente " + (line.get('invoice_number') or '')))
                        else:
                            s_inv_nbr = invoice_obj.read(self.cr, self.uid, [line['invoice_id']], ['supplier_invoice_number'])[0]['supplier_invoice_number']
                            if line.get('invoice_type', False) == 'in_invoice':
                                ref_elements.append(
                                "%s" % (u"Factura Proveedor " + (s_inv_nbr and s_inv_nbr or (line.get('invoice_number') or ''))))
                            elif line.get('invoice_type', False) == 'in_refund':
                                ref_elements.append(
                                "%s" % (u"Nota de Crédito Proveedor " + (s_inv_nbr and s_inv_nbr or (line.get('invoice_number') or ''))))
                    else: # Check for voucher
                        if move_id:
                            voucher_ids = account_voucher_obj.search(self.cr, self.uid, [('move_id','=',move_id)])
                            if voucher_ids:
                                voucher = account_voucher_obj.browse(self.cr, self.uid, voucher_ids[0])
                                if voucher.journal_id.type in ['bank','cash'] and voucher.type=='receipt':
                                    ref_elements.append(u"Pago Cliente %s" % (voucher.number or voucher.reference))
                                if voucher.journal_id.type in ['bank','cash'] and voucher.type=='payment':
                                    ref_elements.append(u"Pago Proveedor %s" % (voucher.number or voucher.reference))
                                if voucher.journal_id.type in ['sale','sale_refund'] and voucher.type=='sale':
                                    ref_elements.append(u"Recibo de venta %s" % (voucher.number or voucher.reference))
                                if voucher.journal_id.type in ['purchase','purchase_refund'] and voucher.type=='purchase':
                                    ref_elements.append(u"Recibo de compra %s" % (voucher.number or voucher.reference))

                    if not ref_elements and line.get('lref', False):
                        ref_elements.append("%s" % (line['lref']))

                    label = ' '.join(label_elements)
                    reference = ' '.join(ref_elements)

                    if line.get('ldate'):
                        c_specs = [
                            ('ldate', 1, 0, 'date', datetime.strptime(
                                line['ldate'], '%Y-%m-%d'), None,
                             ll_cell_style_date),
                        ]
                    else:
                        c_specs = [
                            ('ldate', 1, 0, 'text', None),
                        ]
                    c_specs += [
                        ('period', 1, 0, 'text',
                         line.get('period_code') or ''),
                        ('move', 1, 0, 'text', line.get('move_name') or ''),
                        ('journal', 1, 0, 'text', line.get('jcode') or ''),
                        ('account_code', 1, 0, 'text', account.code),
                        ('partner', 1, 0, 'text',
                         line.get('partner_name') or ''),
                        ('label', 1, 0, 'text', label),
                        ('ref', 1, 0, 'text', reference),
                        ('counterpart', 1, 0, 'text',
                         line.get('counterparts') or ''),
                        ('debit', 1, 0, 'number', line.get('debit', 0.0),
                         None, ll_cell_style_decimal),
                        ('credit', 1, 0, 'number', line.get('credit', 0.0),
                         None, ll_cell_style_decimal),
                        ('cumul_bal', 1, 0, 'number', cumul_balance,
                         None, ll_cell_style_decimal),
                    ]
                    if display_curr_columns:

                        curr_debit = line.get('curr_debit', 0.0)
                        curr_credit = line.get('curr_credit', 0.0)
                        #is_change_diff = account_move_line_obj.read(self.cr, self.uid, line['id'], ['change_diff'])['change_diff']
                        #curr_debit = 0.0
                        #curr_credit = 0.0
                        #if line.get('debit', 0.0) and line.get('currency_id', False)==alt_curr_id:
                        #    curr_debit = line.get('amount_currency') < 0 and -line.get('amount_currency') or (line.get('amount_currency') or 0.0)
                        #else:
                        #    if not is_change_diff:
                        #        curr_debit = compute_amounts_in_currency(self, self.cr, self.uid, line.get('debit', 0.0), base_currency_id, alt_curr_id, date=line.get('ldate', False), context=context)
                        #if line.get('credit', 0.0) and line.get('currency_id', False)==alt_curr_id:
                        #    curr_credit = line.get('amount_currency') < 0 and -line.get('amount_currency') or (line.get('amount_currency') or 0.0)
                        #else:
                        #    if not is_change_diff:
                        #        curr_credit = compute_amounts_in_currency(self, self.cr, self.uid, line.get('credit', 0.0), base_currency_id, alt_curr_id, date=line.get('ldate', False), context=context)
                        cumul_alt_curr_balance += curr_debit - curr_credit
                        c_specs += [
                            ('curr_debit', 1, 0, 'number', curr_debit,
                             None, ll_cell_style_decimal),
                            ('curr_credit', 1, 0, 'number', curr_credit,
                             None, ll_cell_style_decimal),
                            ('curr_cumul_bal', 1, 0, 'number', cumul_alt_curr_balance,
                             None, ll_cell_style_decimal),
                        ]
                    if _p.amount_currency(data):
                        c_specs += [
                            ('curr_bal', 1, 0, 'number', line.get(
                                'amount_currency') or 0.0, None,
                             ll_cell_style_decimal),
                            ('curr_code', 1, 0, 'text', line.get(
                                'currency_code') or '', None,
                             ll_cell_style_center),
                        ]
                    if move_id:
                        move_ref = account_move_obj.browse(self.cr, self.uid, move_id).ref or ''
                    else:
                        move_ref = ''
                    c_specs += [('move_ref', 1, 0, 'text', move_ref, None)]
                    row_data = self.xls_row_template(
                        c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, ll_cell_style)

                debit_start = rowcol_to_cell(row_start, 9)
                debit_end = rowcol_to_cell(row_pos - 1, 9)
                debit_formula = 'SUM(' + debit_start + ':' + debit_end + ')'
                credit_start = rowcol_to_cell(row_start, 10)
                credit_end = rowcol_to_cell(row_pos - 1, 10)
                credit_formula = 'SUM(' + credit_start + ':' + credit_end + ')'
                balance_debit = rowcol_to_cell(row_pos, 9)
                balance_credit = rowcol_to_cell(row_pos, 10)
                balance_formula = balance_debit + '-' + balance_credit
                c_specs = [
                    ('acc_title', 7, 0, 'text',
                     ' - '.join([account.code, account.name])),
                    ('cum_bal', 2, 0, 'text',
                     _('Cumulated Balance on Account'),
                     None, c_hdr_cell_style_right),
                    ('debit', 1, 0, 'number', None,
                     debit_formula, c_hdr_cell_style_decimal),
                    ('credit', 1, 0, 'number', None,
                     credit_formula, c_hdr_cell_style_decimal),
                    ('balance', 1, 0, 'number', None,
                     balance_formula, c_hdr_cell_style_decimal),
                ]
                if display_curr_columns:
                    curr_debit_start = rowcol_to_cell(row_start, 12)
                    curr_debit_end = rowcol_to_cell(row_pos - 1, 12)
                    curr_debit_formula = 'SUM(' + curr_debit_start + ':' + curr_debit_end + ')'
                    curr_credit_start = rowcol_to_cell(row_start, 13)
                    curr_credit_end = rowcol_to_cell(row_pos - 1, 13)
                    curr_credit_formula = 'SUM(' + curr_credit_start + ':' + curr_credit_end + ')'
                    curr_balance_debit = rowcol_to_cell(row_pos, 12)
                    curr_balance_credit = rowcol_to_cell(row_pos, 13)
                    curr_balance_formula = curr_balance_debit + '-' + curr_balance_credit
                    c_specs += [
                        ('curr_debit', 1, 0, 'number', None,
                         curr_debit_formula, c_hdr_cell_style_decimal),
                        ('curr_credit', 1, 0, 'number', None,
                         curr_credit_formula, c_hdr_cell_style_decimal),
                        ('curr_balance', 1, 0, 'number', None,
                         curr_balance_formula, c_hdr_cell_style_decimal),
                    ]

                if _p.amount_currency(data):
                    if account.currency_id:
                        c_specs += [('curr_bal', 1, 0, 'number',
                                     cumul_balance_curr, None,
                                     c_hdr_cell_style_decimal)]
                    else:
                        c_specs += [('curr_bal', 1, 0, 'text', None)]
                    c_specs += [('curr_code', 1, 0, 'text', None)]
                row_data = self.xls_row_template(
                    c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, c_hdr_cell_style)
                row_pos += 1

general_ledger_xls_ext( 'report.account.account_report_general_ledger_xls_ext',
                        'account.account',
                        parser=GeneralLedgerWebkitExt)