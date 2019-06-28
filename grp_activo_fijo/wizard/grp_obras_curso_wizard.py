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

from openerp import pooler, api
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)
import time

class GrpObrasCursoEnviarGasto(osv.osv_memory):
    """
    Este wizard es para enviar a gasto una obra en curso
    """

    _name = "grp.obras.curso.enviar.gasto"
    _description = "Envia la obra en curso a gasto"

    _columns = {
        'fecha': fields.date(string=u'Fecha')
    }

    @api.multi
    def enviar_gasto(self):
        data = self.browse(self._ids[0])
        obras_pool = self.env['grp.obras.curso.linea']
        journal_pool = self.env['account.journal']
        period_pool = self.env['account.period']
        sequence_pool = self.env['ir.sequence']
        move_objs = self.env['account.move']
        move_line_objs = self.env['account.move.line']
        data_inv = obras_pool.search([('id', 'in', self._context['active_ids'])])
        monto = 0
        for record in data_inv:
            monto += record.importe
        fy_objs = self.env['account.fiscalyear']
        anio = time.strftime("%Y-%m-%d")[:4]
        fy_id = fy_objs.search([('name', '=', anio)])
        if len(fy_id) > 0:
            fy_id = fy_id[0]
        ctx = self._context.copy()
        ctx = dict(ctx)
        ctx.update({'fiscalyear_id': fy_id})
        journal_obj = journal_pool.search([('name', '=', 'Diario varios')])
        next_seq = sequence_pool.next_by_id(journal_obj.sequence_id.id)
        period_obj = period_pool.search([('date_start', '<=', data[0].fecha),
                            ('date_stop', '>=', data[0].fecha)])
        move = {
            'name': next_seq,
            'ref': "/",
            'date': data[0].fecha,
            'journal_id': journal_obj.id,
            'period_id': period_obj.id,
        }
        new_move_id = move_objs.create(move)
        property_list = []
        property_association = []
        for record in data_inv:
            property_objs = self.env['ir.property']
            ir_property_search_id = property_objs.search([('name', '=', 'property_account_expense'),
                                                         ('res_id', '=',
                                                          'product.template,' +
                                                          str(record.producto_id.product_tmpl_id.id))
                                                         ])
            account_exp_id = int(ir_property_search_id.value_reference.split(",")[1])
            property_association.append((record.id, account_exp_id, record.account_id.id, record.importe))
            if account_exp_id not in property_list:
                property_list.append(account_exp_id)

        for prop in property_list:
            cantidad = 0
            account_id = False
            for assoc in property_association:
                if assoc[1] == prop:
                    cantidad += assoc[3]
                    account_id = assoc[2]
            move_line = {
                'name': '/',
                'ref': '/',
                'move_id': new_move_id.id,
                'account_id': prop,
                'credit': 0.0,
                'debit': cantidad,
                'period_id': period_obj.id,
                'journal_id': journal_obj.id,
            }
            move_line_objs.create(move_line)
            move_line = {
                'name': '/',
                'ref': '/',
                'move_id': new_move_id.id,
                'account_id': account_id,
                'credit': cantidad,
                'debit': 0.0,
                'period_id': period_obj.id,
                'journal_id': journal_obj.id,
            }
            move_line_objs.create(move_line)
        obras_pool.browse(self._context['active_ids']).write({'no_activar': True})
        return {'type': 'ir.actions.act_window_close'}


class GrpObrasCursoActivarExistente(osv.osv_memory):
    """
    Este wizard es para activar la obra a un activo existente.
    """

    _name = "grp.obras.curso.activar.existente"
    _description = "Envia la obra en curso a un activo existente"

    @api.onchange('asset_id')
    def check_change(self):
        if self.asset_id:
            self.asset_category_id = self.asset_id.category_id
            self.asset_category_cpy = self.asset_id.category_id

    def _get_asset_category(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.asset_category_id.id
        return res

    _columns = {
        'fecha': fields.date(string=u'Fecha'),
        'asset_id': fields.many2one('account.asset.asset', string=u'Activo Fijo'),
        'asset_category_id': fields.many2one('account.asset.category', string=u'Categoría de activo'),
        'asset_category_cpy': fields.function(_get_asset_category, method=True, type='many2one',
                                              relation='account.asset.category', string=u'Categoría de activo'),
    }

    @api.multi
    def activar_existente(self):
        data = self.browse(self._ids[0])
        obras_pool = self.env['grp.obras.curso.linea']
        journal_pool = self.env['account.journal']
        period_pool = self.env['account.period']
        sequence_pool = self.env['ir.sequence']
        move_objs = self.env['account.move']
        move_line_objs = self.env['account.move.line']
        account_asset_objs = self.env['account.asset.asset']
        data_inv = obras_pool.search([('id', 'in', self._context['active_ids'])])
        monto = 0
        cuenta = data_inv[0].account_id.id
        for record in data_inv:
            monto += record.importe
        asset = account_asset_objs.search([('id', '=', data[0].asset_id.id)])
        asset.write({'purchase_value': asset.purchase_value + monto})
        # Si esta en ejecucion, recalcular lo que no esta asentado
        if asset.state in ['open']:
            asset.compute_depreciation_board()
        fy_objs = self.env['account.fiscalyear']
        anio = time.strftime("%Y-%m-%d")[:4]
        fy_id = fy_objs.search([('name', '=', anio)])
        if len(fy_id) > 0:
            fy_id = fy_id[0]
        ctx = self._context.copy()
        ctx = dict(ctx)
        ctx.update({'fiscalyear_id': fy_id.id})
        journal_obj = journal_pool.search([('code', '=', 'Vario')])
        next_seq = sequence_pool.with_context(ctx).next_by_id(journal_obj.sequence_id.id)
        period_obj = period_pool.search([('date_start', '<=', data[0].fecha),
                            ('date_stop', '>=', data[0].fecha)])
        move = {
            'name': next_seq,
            'ref': "/",
            'date': data[0].fecha,
            'journal_id': journal_obj.id,
            'period_id': period_obj.id,
        }
        new_move_id = move_objs.create(move)

        move_line = {
            'name': '/',
            'ref': '/',
            'move_id': new_move_id.id,
            # 'account_id': cuenta,
            'account_id': data[0].asset_category_id.account_asset_id.id,
            'credit': 0.0,
            'debit': monto,
            'period_id': period_obj.id,
            'journal_id': journal_obj.id,
            'asset_id': asset.id,
        }
        move_line_objs.create(move_line)

        move_line = {
            'name': '/',
            'ref': '/',
            'move_id': new_move_id.id,
            'account_id': cuenta,
            'credit': monto,
            'debit': 0.0,
            'period_id': period_obj.id,
            'journal_id': journal_obj.id,
            'asset_id': asset.id,
        }
        move_line_objs.create(move_line)
        obras_pool.browse(self._context['active_ids']).write({'activado': True})
        # obras_pool.write(self._context['active_ids'], {'activado': True})
        #  cargar en la relacion many2many la asociacion de activo a account.invoice
        for record in data_inv:
            self._cr.execute("""
                SELECT count(*)
                FROM ass_asset_invoice_rel
                WHERE asset_id = %s AND
                invoice_id = %s
            """, [data[0].asset_id.id, record.factura_id.id])
            res = self._cr.fetchone()
            if res[0] == 0:
                self._cr.execute("""
                    INSERT INTO ass_asset_invoice_rel (asset_id, invoice_id)
                    VALUES (%s, %s)
                """, [data[0].asset_id.id, record.factura_id.id])

        return {'type': 'ir.actions.act_window_close'}


class GrpObrasCursoActivarNuevo(osv.osv_memory):
    """
    Este wizard es para pasar la obra a un activo nuevo.
    """

    _name = "grp.obras.curso.activar.nuevo"
    _description = "Envia la obra en curso a un activo nuevo"

    _columns = {
        'fecha': fields.date(string=u'Fecha'),
        'nombre_activo': fields.char(string=u'Nombre del activo', size=50),
        'asset_category_id': fields.many2one('account.asset.category', string=u'Categoría de activo'),
    }

    @api.multi
    def activar_nuevo(self):
        data = self.browse(self._ids[0])
        obras_pool = self.env['grp.obras.curso.linea']
        journal_pool = self.env['account.journal']
        period_pool = self.env['account.period']
        sequence_pool = self.env['ir.sequence']
        move_objs = self.env['account.move']
        move_line_objs = self.env['account.move.line']
        account_asset_objs = self.env['account.asset.asset']
        data_inv = obras_pool.search([('id', 'in', self._context['active_ids'])])
        monto = 0
        cuenta = data_inv[0].account_id.id
        for record in data_inv:
            monto += record.importe
        vals = {
            'name': data[0].nombre_activo,
            'fecha_alta': data[0].fecha,
            'category_id': data[0].asset_category_id.id,
            'purchase_value': monto,
            'purchase_value_date': time.strftime("%Y-%m-%d"),
        }
        asset_id = account_asset_objs.create(vals)
        asset = account_asset_objs.search([('id', '=', asset_id.id)])
        fy_objs = self.env['account.fiscalyear']
        anio = time.strftime("%Y-%m-%d")[:4]
        fy_id = fy_objs.search([('name', '=', anio)])
        if len(fy_id) > 0:
            fy_id = fy_id[0]
        ctx = self._context.copy()
        ctx = dict(ctx)
        ctx.update({'fiscalyear_id': fy_id.id})
        journal_obj = journal_pool.search([('code', '=', 'Vario')])
        next_seq = sequence_pool.with_context(ctx).next_by_id(journal_obj.sequence_id.id)
        period_obj = period_pool.search([('date_start', '<=', data[0].fecha),
                            ('date_stop', '>=', data[0].fecha)])
        move = {
            'name': next_seq,
            'ref': "/",
            'date': data[0].fecha,
            'journal_id': journal_obj.id,
            'period_id': period_obj.id,
        }
        new_move_id = move_objs.create(move)

        move_line = {
            'name': '/',
            'ref': '/',
            'move_id': new_move_id.id,
            # 'account_id': cuenta,
            'account_id': data[0].asset_category_id.account_asset_id.id,
            'credit': 0.0,
            'debit': monto,
            'period_id': period_obj.id,
            'journal_id': journal_obj.id,
            'asset_id': asset.id,
        }
        move_line_objs.create(move_line)

        move_line = {
            'name': '/',
            'ref': '/',
            'move_id': new_move_id.id,
            'account_id': cuenta,
            'credit': monto,
            'debit': 0.0,
            'period_id': period_obj.id,
            'journal_id': journal_obj.id,
            'asset_id': asset.id,
        }
        move_line_objs.create(move_line)
        obras_pool.browse(self._context['active_ids']).write({'activado': True})
        # obras_pool.write(self._context['active_ids'], {'activado': True})
        #  cargar en la relacion many2many la asociacion de activo a account.invoice
        for record in data_inv:
            self._cr.execute("""
                SELECT count(*)
                FROM ass_asset_invoice_rel
                WHERE asset_id = %s AND
                invoice_id = %s
            """, [asset_id.id, record.factura_id.id])
            res = self._cr.fetchone()
            if res[0] == 0:
                self._cr.execute("""
                    INSERT INTO ass_asset_invoice_rel (asset_id, invoice_id)
                    VALUES (%s, %s)
                """, [asset_id.id, record.factura_id.id])

        return {'type': 'ir.actions.act_window_close'}


