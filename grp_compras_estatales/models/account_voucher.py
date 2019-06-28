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

import logging

from openerp.osv import osv, fields

_logger = logging.getLogger(__name__)

class grp_account_voucher(osv.osv):
    _inherit = 'account.voucher'

    # RAGU: reemplazando metodo cancel_voucher para que no elimine asientos. OJO: a partir de ahora se obvia el del core
    def _cancel_voucher(self, cr, uid, ids, context=None):
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        writeoff_move_ids = {} # writeoff_move_id => to_reconcile_account_id
        for voucher in self.browse(cr, uid, ids, context=context):
            # refresh to make sure you don't unlink an already removed move
            voucher.refresh()
            for line in voucher.move_ids:
                # refresh to make sure you don't unreconcile an already unreconciled entry
                line.refresh()
                if line.reconcile_id:
                    # irabaza: Obtener asiento(s) por diferencia de cambio
                    move_lines = []
                    for move_line in line.reconcile_id.line_id:
                        move_lines.append(move_line.id)
                        if move_line.move_id.desajuste and move_line.move_id.id != voucher.move_id.id \
                           and move_line.move_id.id not in writeoff_move_ids.keys():
                            writeoff_move_ids[move_line.move_id.id] = line.account_id.id

                    #move_lines = [move_line.id for move_line in line.reconcile_id.line_id]
                    move_lines.remove(line.id)
                    reconcile_pool.unlink(cr, uid, [line.reconcile_id.id], context=context)
                    if len(move_lines) >= 2:
                        move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto', context=context)
                # irabaza: Eliminar apuntes parcialmente conciliados
                if line.reconcile_partial_id:
                    move_lines = [move_line.id for move_line in line.reconcile_partial_id.line_partial_ids]
                    if line.id in move_lines:
                        move_lines.remove(line.id)
                    reconcile_pool.unlink(cr, uid, [line.reconcile_partial_id.id], context=context)
                    if len(move_lines) >= 2:
                        move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto', context=context)
            ## irabaza: No cancelar el movimiento para evitar tener que validarlo otra vez
            ## debe quedar 'posted' al igual que el asiento de extorno
            #if voucher.move_id:
            #    move_pool.button_cancel(cr, uid, [voucher.move_id.id], context=context)
            #    # move_pool.unlink(cr, uid, [voucher.move_id.id], context=context)
        res = {
            'state': 'cancel',
            'move_id': False,
        }
        self.write(cr, uid, ids, res, context=context)
        return writeoff_move_ids


