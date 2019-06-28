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
from openerp import api, exceptions
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

class grp_campos_baja_activo(osv.osv_memory):
    """ Campos de Wizard Baja de Activo """

    _name = 'grp.baja_activo'
    _description = 'Baja de activos'

    @api.depends('fecha_baja','amortizacion_form')
    def _compute_amortizacion(self):
        for record in self:
            record.amortizacion = record.amortizacion_form
            if record.fecha_baja and self.env.context.get('active_id', False):
                form = self.env['account.asset.asset'].search([('id','=',self.env.context['active_id'])])
                for line in form.depreciation_line_ids.search([('asset_id','=',form.id),('move_check','=',True)], limit=1, order='depreciation_date DESC'):
                    _date = datetime.strptime(record.fecha_baja, DEFAULT_SERVER_DATE_FORMAT)
                    _depreciation_date = datetime.strptime(line.depreciation_date, DEFAULT_SERVER_DATE_FORMAT)
                    if _depreciation_date < _date:
                        rdelta_days = _date - _depreciation_date
                        record.amortizacion = record.amortizacion * (rdelta_days.days - 1)
                        record.is_valid = True
                        break
                    else:
                        record.is_valid = False
                        raise exceptions.ValidationError(u"La fecha de baja debe ser mayor que la última fecha de depreciación asentada.\n Fecha de baja: %s\n Última fecha de depreciación asentada: %s" % (record.fecha_baja, line.depreciation_date))

    def baja_activo(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context.get('active_id', False):
            row = self.browse(cr, uid, ids[0], context=context)
            asset_obj = self.pool.get('account.asset.asset')
            asset_row = asset_obj.browse(cr, uid, context['active_id'], context=context)
            period_obj = self.pool.get('account.period')
            move_obj = self.pool.get('account.move')
            move_line_obj = self.pool.get('account.move.line')
            currency_obj = self.pool.get('res.currency')

            #Contabilidad
            depreciation_date = row.fecha_baja
            ctx = dict(context, account_period_prefer_normal=True)
            period_ids = period_obj.find(cr, uid, depreciation_date, context=ctx)

            asset_name = "/"
            reference = asset_row.name
            company_currency = asset_row.company_id.currency_id.id
            current_currency = asset_row.currency_id.id
            context.update({'date': depreciation_date})
            amount = currency_obj.compute(cr, uid, current_currency, company_currency, row.amortizacion, context=context)
            sign = (asset_row.category_id.journal_id.type == 'purchase' and 1) or -1
            journal_id = asset_row.category_id.journal_id.id
            partner_id = asset_row.partner_id.id
            if asset_row.state == 'open':
                #Creando asiento y apuntes en la ejecución de dar baja
                move_id_amort = move_obj.create(cr, uid, {
                    'name': asset_name,
                    'date': depreciation_date,
                    'ref': reference,
                    'operating_unit_id':context.get('operating_unit',False),
                    'period_id': period_ids and period_ids[0] or False,
                    'journal_id': asset_row.category_id.journal_id.id,
                }, context=context)
                #Apunte de crédito
                move_line_obj.create(cr, uid, {
                    'name': asset_row.name,
                    'ref': reference,
                    'move_id': move_id_amort,
                    'account_id': asset_row.category_id.account_depreciation_id.id,
                    'debit': 0.0,
                    'credit': amount,
                    'period_id': period_ids and period_ids[0] or False,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency or False,
                    'amount_currency': company_currency != current_currency and - sign * row.amortizacion or 0.0,
                    'date': depreciation_date,
                })
                #Apunte de débito
                move_line_obj.create(cr, uid, {
                    'name': asset_row.category_id.name,
                    'ref': reference,
                    'move_id': move_id_amort,
                    'account_id': asset_row.category_id.account_expense_depreciation_id.id,
                    'credit': 0.0,
                    'debit': amount,
                    'period_id': period_ids and period_ids[0] or False,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency or False,
                    'amount_currency': company_currency != current_currency and sign * _amount or 0.0,
                    'analytic_account_id': asset_row.category_id.account_analytic_id.id,
                    'date': depreciation_date,
                    'asset_id': asset_row.id
                })
            #----------------------------------------------------------------------------------------

            move_id_baja = move_obj.create(cr, uid, {
                'name': asset_name,
                'date': depreciation_date,
                'ref': reference,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': asset_row.category_id.journal_id.id,
                'operating_unit_id': context.get('operating_unit', False)
            }, context=context)

            #Apunte de crédito
            amount_cred = currency_obj.compute(cr, uid, current_currency, company_currency, asset_row.purchase_value, context=context)
            amount_cred_currency = company_currency != current_currency and sign * asset_row.purchase_value or 0.0
            move_line_obj.create(cr, uid, {
                'name': asset_row.name,
                'ref': reference,
                'move_id': move_id_baja,
                'account_id': asset_row.category_id.account_asset_id.id,
                'debit': 0.0,
                'credit': amount_cred,
                'partner_id': partner_id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': amount_cred_currency,
                'date': depreciation_date,
            })

            #Apunte de débito
            amount_deb = currency_obj.compute(cr, uid, current_currency, company_currency, asset_row.amortizacion_ac, context=context) + amount
            amount_deb_currency = company_currency != current_currency and - sign * (asset_row.amortizacion_ac + amount) or 0.0
            move_line_obj.create(cr, uid, {
                'name': asset_row.category_id.name,
                'ref': reference,
                'move_id': move_id_baja,
                'account_id': asset_row.category_id.account_depreciation_id.id,
                'credit': 0.0,
                'debit': amount_deb,
                'partner_id': partner_id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': amount_deb_currency,
                'analytic_account_id': asset_row.category_id.account_analytic_id.id,
                'date': depreciation_date
            })
            #Tercer posible apunte de baja
            if amount_cred > amount_deb:
                amount_deb_ex = currency_obj.compute(cr, uid, current_currency, company_currency, amount_cred - amount_deb, context=context)
                amount_deb_ex_currency = company_currency != current_currency and sign * (amount_cred - amount_deb) or 0.0
                move_line_obj.create(cr, uid, {
                    'name': asset_row.category_id.name,
                    'ref': reference,
                    'move_id': move_id_baja,
                    'account_id': row.motivo_baja.account_id.id,
                    'credit': 0.0,
                    'debit': amount_deb_ex,
                    'period_id': period_ids and period_ids[0] or False,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency or False,
                    'amount_currency': amount_deb_ex_currency,
                    'analytic_account_id': asset_row.category_id.account_analytic_id.id,
                    'date': depreciation_date
                })
            elif amount_cred < amount_deb:
                amount_cred_ex = currency_obj.compute(cr, uid, current_currency, company_currency, amount_deb - amount_cred, context=context)
                amount_cred_ex_currency = company_currency != current_currency and sign * (amount_deb - amount_cred) or 0.0
                move_line_obj.create(cr, uid, {
                    'name': asset_row.category_id.name,
                    'ref': reference,
                    'move_id': move_id_baja,
                    'account_id': row.motivo_baja.account_id.id,
                    'credit': amount_cred_ex,
                    'debit': 0.0,
                    'period_id': period_ids and period_ids[0] or False,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency or False,
                    'amount_currency': amount_cred_ex_currency,
                    'analytic_account_id': asset_row.category_id.account_analytic_id.id,
                    'date': depreciation_date
                })

            self.pool.get('grp.historial_baja_activo').create(cr, uid, {
                'fecha_baja': row.fecha_baja,
                'motivo_baja': row.motivo_baja.id,
                'descripcion_motivo': row.descripcion_motivo,
                'nro_expediente': row.nro_expediente,
                'grp_account_asset_id': asset_row.id,
                'account_move_id': move_id_baja
            }, context=context)

            asset_row.write({
                'fecha_baja': row.fecha_baja,
                'state': 'baja',
                'amortizacion_ac_baja': row.amortizacion,
                'amortizacion_parcial': row.amortizacion
            })
        return True

    _columns = {
        'fecha_baja': fields.date('Fecha de Baja', required=True),
        'motivo_baja': fields.many2one('grp.motivos_baja', 'Motivo', required=True),
        'descripcion_motivo': fields.char(u'Descripción', size=64),
        'nro_expediente': fields.char(u'Nro. de expediente', size=30, required=True),
        'amortizacion_form': fields.float(u'Amortización'),
        'amortizacion': fields.float(u'Amortización', compute='_compute_amortizacion', readonly=True, store=True),
        'is_valid': fields.boolean('Datos correctos', compute='_compute_amortizacion', readonly=True, store=True, default=False)
    }
