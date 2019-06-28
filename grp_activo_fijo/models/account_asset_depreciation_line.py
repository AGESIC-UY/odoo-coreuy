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
import logging
_logger = logging.getLogger(__name__)
from datetime import date, datetime, timedelta


class account_asset_depreciation_line(osv.osv):
    _inherit = 'account.asset.depreciation.line'

    def _prepare_cred_move_line(self, cr, uid, ids, line, move_id, depreciation_date, period_ids=[], context=None):
        company_currency = line.asset_id.company_id.currency_id.id
        current_currency = line.asset_id.currency_id.id
        currency_obj = self.pool.get('res.currency')
        ctx = context.copy()
        ctx = ctx.update({'date': depreciation_date})
        amount = currency_obj.compute(cr, uid, current_currency, company_currency, line.amount, context=ctx)
        sign = (line.asset_id.category_id.journal_id.type == 'purchase' and 1) or -1
        return {
                'name': line.asset_id.name,
                'ref': line.asset_id.name,
                'move_id': move_id,
                'account_id': line.asset_id.category_id.account_depreciation_id.id,
                'debit': 0.0,
                'credit': amount,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': line.asset_id.category_id.journal_id.id,
                'partner_id': line.asset_id.partner_id.id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
                'date': depreciation_date,
                'asset_id': line.asset_id.id,
                'operating_unit_id': line.asset_id.operating_unit_id.id
        }

    def _prepare_deb_move_line(self, cr, uid, ids, line, move_id, depreciation_date, period_ids=[], context=None):
        company_currency = line.asset_id.company_id.currency_id.id
        current_currency = line.asset_id.currency_id.id
        currency_obj = self.pool.get('res.currency')
        ctx = context.copy()
        ctx = ctx.update({'date': depreciation_date})
        amount = currency_obj.compute(cr, uid, current_currency, company_currency, line.amount, context=ctx)
        sign = (line.asset_id.category_id.journal_id.type == 'purchase' and 1) or -1
        return {
                'name': line.asset_id.category_id.name,
                'ref': line.asset_id.name,
                'move_id': move_id,
                'account_id': line.asset_id.category_id.account_expense_depreciation_id.id,
                'credit': 0.0,
                'debit': amount,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': line.asset_id.category_id.journal_id.id,
                'partner_id': line.asset_id.partner_id.id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': company_currency != current_currency and sign * line.amount or 0.0,
                'analytic_account_id': line.asset_id.category_id.account_analytic_id.id,
                'date': depreciation_date,
                'operating_unit_id': line.asset_id.operating_unit_id.id
        }

    def create_move(self, cr, uid, ids, context=None):
        can_close = False
        if context is None:
            context = {}
        asset_obj = self.pool.get('account.asset.asset')
        period_obj = self.pool.get('account.period')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        created_move_ids = []
        asset_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            depreciation_date = context.get('depreciation_date') or line.depreciation_date or time.strftime('%Y-%m-%d')
            ctx = dict(context, account_period_prefer_normal=True)
            period_ids = period_obj.find(cr, uid, depreciation_date, context=ctx)
            company_currency = line.asset_id.company_id.currency_id.id
            current_currency = line.asset_id.currency_id.id
            context.update({'date': depreciation_date})
            amount = currency_obj.compute(cr, uid, current_currency, company_currency, line.amount, context=context)
            sign = (line.asset_id.category_id.journal_id.type == 'purchase' and 1) or -1
            # asset_name = line.asset_id.name
            # reference = line.name
            asset_name = "/"
            reference = line.asset_id.name
            # PCARBALLO
            per_id = period_ids and period_ids[0] or False
            per_obj = self.pool.get('account.period').browse(cr, uid, per_id, context=context)
            ass_obj = self.pool.get('account.asset.asset').browse(cr, uid, line.asset_id.id, context=context)
            # Control de lineas de depreciacion previas sin asentar
            for depr_line in ass_obj.depreciation_line_ids:
                # si la linea de depreciacion es anterior a la actual
                # y no esta asentada aun, entonces mostrar mensaje de error
                if depr_line.depreciation_date < per_obj.date_start and not depr_line.move_check:
                    raise osv.except_osv((u'Error!'),
                                         (u'Existen líneas de depreciación anteriores sin asentar para este activo.'))
            move_vals = {
                'name': asset_name,
                'date': depreciation_date,
                'ref': reference,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': line.asset_id.category_id.journal_id.id,
                'operating_unit_id': line.asset_id.operating_unit_id.id,
            }
            move_id = move_obj.create(cr, uid, move_vals, context=context)
            journal_id = line.asset_id.category_id.journal_id.id
            partner_id = line.asset_id.partner_id.id

            cred = self._prepare_cred_move_line(cr, uid, ids, line, move_id, depreciation_date, period_ids=period_ids, context=context)
            move_line_obj.create(cr, uid, cred)
            deb = self._prepare_deb_move_line(cr, uid, ids, line, move_id, depreciation_date, period_ids=period_ids, context=context)
            move_line_obj.create(cr, uid, deb)
            self.write(cr, uid, line.id, {'move_id': move_id}, context=context)
            created_move_ids.append(move_id)
            asset_ids.append(line.asset_id.id)
        # we re-evaluate the assets to determine whether we can close them
        asset_ids = list(set(asset_ids))
        for asset in asset_obj.browse(cr, uid, asset_ids, context=context):
            if currency_obj.is_zero(cr, uid, asset.currency_id, asset.value_residual):
                asset.write({'state': 'close'})
        # Si por context se pasa el valor return_action entonces se retorna la acción con el res_id actual.
        if context.get('return_action', False):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Activos',
                'res_model': 'account.asset.asset',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': asset.id
            }
        return created_move_ids

    # 001-Inicio
    def onchange_cancelar_amortizacion(self, cr, uid, ids, cancelar_amortizacion, context=None):
        res = {}
        if cancelar_amortizacion:
            res.update(
                {'value':
                    {
                        'fecha_asiento': time.strftime("%Y-%m-%d"),
                    }
                }
            )
        return res

    _columns = {
        'cancelar_amortizacion': fields.boolean(u'Cancelar amortización'),
        'fecha_asiento': fields.date(u'Fecha de asiento'),
    }

    _defaults = {
        'cancelar_amortizacion': False
    }

    def action_cancelar_amortizacion(self, cr, uid, ids, context=None):
        seq_obj = self.pool.get('ir.sequence')
        fy_obj = self.pool.get('account.fiscalyear')
        move_objs = self.pool.get('account.move')
        move_line_objs = self.pool.get('account.move.line')
        period_obj = self.pool.get('account.period')
        depr_line_objs = self.pool.get('account.asset.depreciation.line')
        asset_objs = self.pool.get('account.asset.asset')
        self_obj = self.browse(cr, uid, ids[0])
        #controles de lineas de depreciacion posteriores para el activo
        cr.execute("""
        SELECT count(*)
        FROM account_asset_depreciation_line depr
        WHERE depr.asset_id = %s AND depr.depreciation_date > %s
        AND depr.move_check
        """, [self_obj.asset_id.id, self_obj.depreciation_date])
        resultado = cr.fetchall()[0]
        if resultado[0] > 0:
            raise osv.except_osv((u'Error!'),
                                 (
                                 u'Existen líneas de depreciación posteriores a esta sin cancelar para el activo: %s. Por favor, verifique.') % (
                                 self_obj.asset_id.name))

        if self_obj.fecha_asiento < self_obj.depreciation_date:
            raise osv.except_osv((u'Error!'),
                                 (u'La fecha de asiento no puede ser anterior a la fecha de depreciación.'))
        #Si el asiento ya fue cancelado no hago nada, lo cancelo otra linea que tambien pertenece al mismo asiento
        #Solo actualizo la info de la linea
        cancelled_move_ids = context.get('cancelled_move_ids', [])
        if not self_obj.move_id.id in cancelled_move_ids:
            anio = time.strftime("%Y-%m-%d")[:4]
            fy_id = fy_obj.search(cr, uid, [('name','=',anio)])
            if len(fy_id) > 0:
                fy_id = fy_id[0]
            context.update({'fiscalyear_id': fy_id})
            next_seq = seq_obj.next_by_id(cr, uid, self_obj.asset_id.category_id.journal_id.sequence_id.id, context=context)
            period_ids = period_obj.find(cr, uid, self_obj.depreciation_date, context=context)
            if len(period_ids) > 0:
                period_ids = period_ids[0]
            values = {
                'name': next_seq,
                'ref': "Extorno " + self_obj.move_id.ref,
                'date': self_obj.fecha_asiento,
                'journal_id': self_obj.asset_id.category_id.journal_id.id,
                'period_id': period_ids,
                'operating_unit_id': self_obj.asset_id.operating_unit_id.id,
            }
            new_move_id = move_objs.create(cr, uid, values, context=context)
            for line in self_obj.move_id.line_id:
                move_line = {
                    'name': line.name,
                    'ref': line.ref,
                    'move_id': new_move_id,
                    'account_id': line.account_id.id,
                    'credit': 0.0 if line.credit else line.debit,
                    'debit': 0.0 if line.debit else line.credit,
                    'period_id': line.period_id.id,
                    'journal_id': line.journal_id.id,
                    'partner_id': line.partner_id.id,
                    'currency_id': line.currency_id.id,
                    'amount_currency': line.amount_currency,
                    'analytic_account_id': line.analytic_account_id.id,
                    'date': line.date,
                    'asset_id': line.asset_id.id,
                    'operating_unit_id': line.asset_id.operating_unit_id.id,
                }
                move_line_objs.create(cr, uid, move_line, context=context)
        else:
            new_move_id = False
        # Limpiar campos
        self.write(cr, uid, [self_obj.id], {'move_check': False, 'move_id': False, 'cancelar_amortizacion': False}, context=context)
        # Validacion: si el activo esta amortizado, y cancelo la ultima depreciacion
        # debe cambiar el estado del activo a En ejecucion
        if self_obj.asset_id.state in ['close']:
            ultima_depr_ids = depr_line_objs.search(cr, uid, [('asset_id', '=', self_obj.asset_id.id),
                                                                ('remaining_value', '=', 0),
                                                                ('move_check', '=', False)])
            if ultima_depr_ids:
                asset_objs.write(cr, uid, [self_obj.asset_id.id], {'state': 'open'}, context=context)
        return new_move_id

account_asset_depreciation_line()
# 001-Fin
