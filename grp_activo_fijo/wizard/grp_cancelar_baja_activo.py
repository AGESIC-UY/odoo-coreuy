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
from datetime import date, datetime, timedelta
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import _

class grp_cancelar_baja_activo(osv.osv_memory):
    """ Cancelar la Baja de Activos """
    _name = 'grp.cancelar_baja_activo'
    _description = 'Cancelar baja de activos'

    @api.multi
    def cancelar_baja_activo(self):
        active_id = self._context.get('active_id', False)
        asset_objs = self.env['account.asset.asset']
        seq_obj = self.env['ir.sequence']
        move_objs = self.env['account.move']
        move_line_objs = self.env['account.move.line']
        historial_objs = self.env['grp.historial_baja_activo']
        motivos_objs = self.env['grp.motivos_baja']
        fy_objs = self.env['account.fiscalyear']
        if active_id:
            asset = asset_objs.browse(active_id)
            crear_extorno_parcial = False
            for dep_line in asset.depreciation_line_ids:
                if not dep_line.move_check:
                    date = dep_line.depreciation_date
                    year = datetime.strptime(date, "%Y-%m-%d").date().year
                    fy_obj = self.env['account.fiscalyear'].search([('code', '=', year)])
                    if fy_obj.state in ['done']:
                        raise osv.except_osv(_(u'Error!'), _(u'El ejercicio está cerrado,'
                                                             u' no se puede cancelar la baja del activo.'))
                    else:
                        crear_extorno_parcial = True
            if crear_extorno_parcial:
                # Crear asiento extorno de amortizacion parcial
                historial_sort = historial_objs.search([('grp_account_asset_id', '=', asset.id)],
                                                       order='id DESC')
                hist = historial_sort[0]
                if hist.account_move_id:
                    # Si el periodo del asiento esta cerrado, lanzar error
                    if hist.account_move_id.period_id.state in ['done']:
                        raise osv.except_osv(_(u'Error!'), _(u'El período del asiento de baja está cerrado,'
                                                             u' no se puede cancelar la baja del activo.'))
                    # crear el asiento de extorno de la baja
                    # busco el asiento anterior al de baja de activo
                    # que se corresponde con el asiento de amortizacion parcial a extornar
                    # tiene un numero de secuencia menos que el asiento de baja
                    num = hist.account_move_id.name[-4:]
                    secuencia = ""
                    if num[0] != "0":
                        num = int(num)
                        num -= 1
                        secuencia = str(num)
                    elif num[1] != "0":
                        num = int(num[-3:])
                        num -= 1
                        secuencia = "0" + str(num)
                    elif num[2] != "0":
                        num = int(num[-2:])
                        num -= 1
                        secuencia = "00" + str(num)
                    else:
                        num = int(num[3])
                        num -= 1
                        secuencia = "000" + str(num)
                    secuencia = hist.account_move_id.name[:-4] + secuencia
                    move_partial = move_objs.search([('name', '=', secuencia)])
                    if move_partial:
                        anio = time.strftime("%Y-%m-%d")[:4]
                        fy = fy_objs.search([('name', '=', anio)], limit=1)
                        if fy:
                            fy_id = fy.id
                            ctx = self._context.copy()
                            ctx = dict(ctx)
                            ctx.update({'fiscalyear_id': fy_id})
                        next_seq = seq_obj.with_context(ctx).next_by_id(move_partial.journal_id.sequence_id.id)
                        values = {
                            'name': next_seq,
                            'ref': "Extorno " + move_partial.ref,
                            'date': move_partial.date,
                            'journal_id': move_partial.journal_id.id,
                            'period_id': move_partial.period_id.id,
                            'operating_unit_id': hist.grp_account_asset_id.operating_unit_id.id,
                        }
                        new_move_id = move_objs.create(values)
                        for line in move_partial.line_id:
                            move_line = {
                                'name': line.name,
                                'ref': line.ref,
                                'move_id': new_move_id.id,
                                'account_id': line.account_id.id,
                                'credit': 0.0 if line.credit else asset.amortizacion_parcial,
                                'debit': 0.0 if line.debit else asset.amortizacion_parcial,
                                'period_id': line.period_id.id,
                                'journal_id': line.journal_id.id,
                                'partner_id': line.partner_id.id,
                                'currency_id': line.currency_id.id,
                                'amount_currency': line.amount_currency,
                                'analytic_account_id': line.analytic_account_id.id,
                                'date': line.date,
                                # 'asset_id': asset.id,
                                'operating_unit_id': line.asset_id.operating_unit_id.id,
                            }
                            # De las dos lineas nuevas, solo se muestra en el historial la que tiene
                            # credito (que es la que en la linea original tiene monto no nulo en debito)
                            if line.debit:
                                move_line.update({'asset_id': asset.id})
                            move_line_objs.create(move_line)

            # Ordenar el historial por id en forma descendente, el primero corresponde con la baja que hay que cancelar
            historial_sort = historial_objs.search([('grp_account_asset_id', '=', asset.id)], order='id DESC')
            hist = historial_sort[0]
            if hist.account_move_id:
                # Si el periodo del asiento esta cerrado, lanzar error
                if hist.account_move_id.period_id.state in ['done']:
                    raise osv.except_osv(_(u'Error!'), _(u'El período del asiento de baja está cerrado,'
                                                         u' no se puede cancelar la baja del activo.'))
                # crear el asiento de extorno de la baja
                anio = time.strftime("%Y-%m-%d")[:4]
                fy = fy_objs.search([('name', '=', anio)], limit=1)
                if fy:
                    fy_id = fy.id
                    ctx = self._context.copy()
                    ctx = dict(ctx)
                    ctx.update({'fiscalyear_id': fy_id})
                next_seq = seq_obj.with_context(ctx).next_by_id(hist.account_move_id.journal_id.sequence_id.id)
                values = {
                    'name': next_seq,
                    'ref': "Extorno " + hist.account_move_id.ref,
                    'date': hist.account_move_id.date,
                    'journal_id': hist.account_move_id.journal_id.id,
                    'period_id': hist.account_move_id.period_id.id,
                    'operating_unit_id': hist.grp_account_asset_id.operating_unit_id.id,
                }
                new_move_id = move_objs.create(values)
                for line in hist.account_move_id.line_id:
                    move_line = {
                        'name': line.name,
                        'ref': line.ref,
                        'move_id': new_move_id.id,
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
                        'asset_id': asset.id,
                        'operating_unit_id': line.asset_id.operating_unit_id.id,
                    }
                    move_line_objs.create(move_line)
                # actualizar campo amortizacion_parcial a 0
                asset.write({
                    'amortizacion_parcial': 0,
                    'amortizacion_ac_baja': 0,
                })
                motivo_don = motivos_objs.search([('name', 'in', [u'Cancelación'])])
                historial_data = {
                    'grp_account_asset_id': asset.id,
                    'account_move_id': new_move_id.id,
                    'descripcion_motivo': u"Cancelación",
                    'motivo_baja': motivo_don.id,
                    'fecha_baja': hist.account_move_id.date,
                }
                historial_objs.create(historial_data)
                # si tiene lineas sin amortizar el af pasa a estado en ejecucion
                # sino pasa a Amortizado
                if crear_extorno_parcial:
                    asset.write({'state': 'open'})
                else:
                    asset.write({'state': 'close'})
        return True


