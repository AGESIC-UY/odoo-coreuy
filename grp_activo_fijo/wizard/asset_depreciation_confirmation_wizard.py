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
import time
from openerp import SUPERUSER_ID

import logging

_logger = logging.getLogger(__name__)

class grp_asset_depreciation_confirmation_wizard(osv.osv_memory):
    _inherit = 'asset.depreciation.confirmation.wizard'

    def _prepare_deb_move_line(self, cr, uid, ids, lines, asset_categ, debit, operating_unit, context=None):
        return {
                    'name': asset_categ.name,
                    'account_id': asset_categ.account_expense_depreciation_id.id,
                    'debit': debit,
                    'credit': 0.0,
                    'operating_unit_id': operating_unit.id,
        }

    def asset_compute(self, cr, uid, ids, context):
        ass_obj = self.pool.get('account.asset.asset')
        operating_unit_obj = self.pool.get('operating.unit')
        currency_obj = self.pool.get('res.currency')
        data = self.browse(cr, uid, ids, context=context)
        period_id = data[0].period_id.id
        ass_cat_obj = self.pool.get('account.asset.category')
        ass_cat_ids = ass_cat_obj.search(cr, uid, [], context=context)
        operating_unit_ids = operating_unit_obj.search(cr, uid, [], context=context)
        move_objs = self.pool.get('account.move')
        move_list = []
        for categ in ass_cat_obj.browse(cr, uid, ass_cat_ids, context=context):
            for operating_unit in operating_unit_obj.browse(cr, uid, operating_unit_ids, context=context):
                asset_ids = ass_obj.search(cr, uid, [('category_id', '=', categ.id), ('operating_unit_id', '=', operating_unit.id), ('state', 'in', ['open'])])
                # para cada activo de una categoria
                lista = []
                credit = 0.0
                tiene_lineas = []
                depr_line_ids_to_move = []
                for asset in ass_obj.browse(cr, uid, asset_ids, context=context):
                    # para cada linea de depreciacion de cada activo
                    for depr_line in asset.depreciation_line_ids:
                        # Control de lineas de depreciacion de periodos anteriores sin asentar.
                        if depr_line.depreciation_date < data[0].period_id.date_start and not depr_line.move_check:
                            raise osv.except_osv((u'Error!'), (u'Existen líneas de depreciación anteriores sin asentar para el activo: ' + asset.name + u'. Por favor, verifique.'))
                        if (depr_line.depreciation_date >= data[0].period_id.date_start) and (
                            depr_line.depreciation_date <= data[0].period_id.date_stop) and not (depr_line.move_check):
                            tiene_lineas.append(depr_line)
                            credit += depr_line.amount
                            lista.append((0, 0, {
                                'name': asset.name,
                                # 'account_id': move_line.account_id.id,
                                'account_id': asset.category_id.account_depreciation_id.id,
                                # 'debit': move_line.debit,
                                # 'credit': move_line.credit,
                                'debit': 0.0,
                                'credit': depr_line.amount,
                                'operating_unit_id': operating_unit.id,
                                # 001-Inicio
                                'asset_id': asset.id,
                                # 001-Fin
                            }))
                            depr_line_ids_to_move.append(depr_line.id)
                if tiene_lineas and credit:
                    lista.append((0, 0, self._prepare_deb_move_line(cr, uid, ids, tiene_lineas, categ, credit, operating_unit, context=context)))
                    move_data = {}
                    if lista:
                        move_data = {
                            'name': '/',
                            'ref': categ.name + " - " + data[0].period_id.name,
                            'journal_id': categ.journal_id.id,
                            'period_id': period_id,
                            'date': data[0].period_id.date_stop,
                            'to_check': False,
                            'line_id': lista,
                            'operating_unit_id': operating_unit.id,
                        }
                        new_move_id = move_objs.create(cr, uid, move_data, context=context)
                        if new_move_id:
                            move_list.append(new_move_id)
                            write_id = self.pool.get('account.asset.depreciation.line').write(cr, uid,
                                                                                              depr_line_ids_to_move,
                                                                                              {'move_id': new_move_id,
                                                                                               'move_check': True},
                                                                                              context=context)
                #si algun activo tiene que pasar a estado amortizado, hago el cambio de estado
                for asset in ass_obj.browse(cr, uid, asset_ids, context=context):
                    if currency_obj.is_zero(cr, uid, asset.currency_id, asset.value_residual):
                        asset.write({'state': 'close'})

        return {
            'name': _('Created Asset Moves'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': "[('id','in',[" + ','.join(map(str, move_list)) + "])]",
            'type': 'ir.actions.act_window',
        }

    # 001-Inicio PCAR 02 05 2017
    def onchange_cancelar_amortizacion(self, cr, uid, ids, cancelar_amortizacion, period_id=False, context=None):
        res = {}
        if cancelar_amortizacion:
            if period_id:
                period = self.pool.get('account.period').browse(cr, uid, period_id, context=context)
                date = period.date_stop
            else:
                date = time.strftime("%Y-%m-%d")
            res.update(
                {'value':
                    {
                        'fecha_asiento': date,
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

    def action_cancelar_amortizaciones(self, cr, uid, ids, context=None):
        data = self.browse(cr, uid, ids)
        move_objs = self.pool.get('account.move')
        move_line_objs = self.pool.get('account.move.line')
        depr_line_objs = self.pool.get('account.asset.depreciation.line')
        asset_objs = self.pool.get('account.asset.asset')
        operating_unit_obj = self.pool.get('operating.unit')
        # Lista de asientos generados
        move_list = []
        # Lista de asientos cancelados
        cancelled_move_ids = []
        # Busco los asientos de amortizacion correspondientes a ese periodo
        # Solamente se cancelan los asientos asignados a una linea de depreciacion
        operating_unit_ids = operating_unit_obj.search(cr, uid, [], context=context)
        depreciation_ids = depr_line_objs.search(cr, uid, [('asset_id.operating_unit_id','in',operating_unit_ids),('asset_id.state','!=','baja'),('move_id.period_id','=',data[0].period_id.id)], context=context)
        for depreciation_id in depreciation_ids:
            context.update({'cancelled_move_ids': cancelled_move_ids[:]}) #copia de la lista original
            # Como cancela a nivel de move_id, me guardo los move_ids que se cancelaron para no cancelar 2 veces en caso de que mas de una linea pertenezca al mismo move_id
            depreciation_line = depr_line_objs.browse(cr, uid, depreciation_id, context=context)
            if depreciation_line.move_id.id not in cancelled_move_ids:
                cancelled_move_ids.append(depreciation_line.move_id.id)
            depr_line_objs.write(cr, uid, [depreciation_id], {'fecha_asiento': data[0].fecha_asiento}, context=context)
            generated_move_id = depr_line_objs.action_cancelar_amortizacion(cr, uid, [depreciation_id], context=context)
            if generated_move_id:
                move_list.append(generated_move_id)

        return {
            'name': _('Created Asset Moves'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': "[('id','in',[" + ','.join(map(str, move_list)) + "])]",
            'type': 'ir.actions.act_window',
        }

    def action_cancelar_amortizaciones_old(self, cr, uid, ids, context=None):
        data = self.browse(cr, uid, ids)
        move_objs = self.pool.get('account.move')
        move_line_objs = self.pool.get('account.move.line')
        depr_line_objs = self.pool.get('account.asset.depreciation.line')
        asset_objs = self.pool.get('account.asset.asset')
        operating_unit_obj = self.pool.get('operating.unit')
        move_list = []
        # Busco los asientos de amortizacion correspondientes a ese periodo
        # Solamente se cancelan los asientos asignados a una linea de depreciacion
        operating_unit_ids = operating_unit_obj.search(cr, uid, [], context=context)
        depreciation_ids = depr_line_objs.search(cr, uid, [('asset_id.operating_unit_id','in',operating_unit_ids),('move_id.period_id','=',data[0].period_id.id)], context=context)

        # cr.execute("""
        #     SELECT mov.id
        #     FROM account_move mov, account_asset_depreciation_line depr
        #     WHERE mov.period_id = %s AND depr.move_id = mov.id
        # """, [data[0].period_id.id])
        # move_ids = [r[0] for r in cr.fetchall()]

        #obtengo asientos para cancelar
        moves = []
        for depr_line in depr_line_objs.browse(cr, uid, depreciation_ids, context=context):
            if depr_line.move_id not in moves:
                moves.append(depr_line.move_id)
        for mov in moves:

        # for mov in move_objs.browse(cr, uid, move_ids, context=context):
            # Obtener las lineas de depreciacion del asiento para actualizar sus datos mas adelante
            # depr_line_ids = depr_line_objs.search(cr, uid, [('move_id', '=', mov.id)])
            # if depr_line_ids:
            seq_obj = self.pool.get('ir.sequence')
            fy_obj = self.pool.get('account.fiscalyear')
            anio = time.strftime("%Y-%m-%d")[:4]
            fy_id = fy_obj.search(cr, uid, [('name','=',anio)])
            if len(fy_id) > 0:
                fy_id = fy_id[0]
            context.update({'fiscalyear_id': fy_id})
            asset_ids = []
            if mov.line_id and mov.line_id[0].asset_id and mov.line_id[0].asset_id.state not in ['baja'] and mov.date <= data[0].fecha_asiento:
                next_seq = seq_obj.next_by_id(cr, uid, mov.line_id[0].asset_id.category_id.journal_id.sequence_id.id, context=context)
                values = {
                    'name': next_seq,
                    'ref': "Extorno " + mov.ref,
                    'date': data[0].fecha_asiento,
                    'journal_id': mov.line_id[0].asset_id.category_id.journal_id.id,
                    'period_id': data[0].period_id.id,
                    'operating_unit_id': mov.line_id[0].asset_id.operating_unit_id.id,
                }
                new_move_id = move_objs.create(cr, uid, values, context=context)
                move_list.append(new_move_id)
                asset_ids = []
                for line in mov.line_id:
                    # Chequear que no existan amortizaciones posteriores
                    # al periodo seleccionado sin cancelar para cada activo de las lineas de asiento
                    # TODO: pasar a ORM: esta dando error de seguridad
                    if line.asset_id:
                        posteriores_ids = depr_line_objs.search(cr, uid, [('asset_id','=',line.asset_id.id),('move_check','=',True),('depreciation_date','>',data[0].period_id.date_stop)], context=context)

                        # cr.execute("""
                        #     SELECT count(*)
                        #     FROM account_asset_depreciation_line depr, account_period per
                        #     WHERE depr.asset_id = %s AND per.id = %s AND depr.move_check AND
                        #      depr.depreciation_date > per.date_stop
                        # """, [line.asset_id.id, data[0].period_id.id])
                        # num = cr.fetchone()[0]
                        if posteriores_ids:
                            raise osv.except_osv((u'Error!'), (
                                            u'Existen líneas de depreciación de activo posteriores'
                                            u' sin cancelar. Por favor, verifique. '))
                        if line.asset_id.id not in asset_ids:
                            asset_ids.append(line.asset_id.id)
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

                depr_line_objs.write(cr, SUPERUSER_ID, [depr_line.id],
                                     {'move_check': False, 'move_id': False, 'cancelar_amortizacion': False},
                                     context=context)
            # Validacion: si el activo esta amortizado, y cancelo la ultima depreciacion
            # debe cambiar el estado del activo a En ejecucion
            for asset in asset_objs.browse(cr, uid, asset_ids, context=context):
                if asset.state in ['close']:
                    ultima_depr_ids = depr_line_objs.search(cr, uid, [('asset_id', '=', asset.id),
                                                            ('remaining_value', '=', 0),
                                                            ('move_check', '=', False)])
                    if ultima_depr_ids:
                        asset_objs.write(cr, uid, [asset.id], {'state': 'open'}, context=context)

        return {
            'name': _('Created Asset Moves'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': "[('id','in',[" + ','.join(map(str, move_list)) + "])]",
            'type': 'ir.actions.act_window',
        }

grp_asset_depreciation_confirmation_wizard()
# 001-Fin PCAR 02 05 2017

