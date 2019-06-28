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

from openerp.osv import osv
from openerp.tools.translate import _

class grp_consolidar_pedidos_compra(osv.osv_memory):
    _name = "grp.consolidar.pedido.compra"
    _description = "Consolida  Solicitudes de Compra"

    def check_estado_solicitudes(self, cr, uid, sc_ids, context=None):
        sc_obj = self.pool.get('grp.solicitud.compra')
        for sc in sc_obj.browse(cr, uid, sc_ids, context=context):
            if sc.state != 'open':
                raise osv.except_osv(('Error!'), (u'La solicitud de compra %s no está en estado Abierto.') % (sc.name,))

            elif sc.pedido_compra_id and sc.pedido_compra_id.state not in ['cancelado', 'cancelado_sice']:
                raise osv.except_osv(('Error!'), (u'La solicitud de compra %s está asociada al pedido de compra %s') % (sc.name,sc.pedido_compra_id.name))
        return True

    def merge_orders(self, cr, uid, ids, context=None):
        sc_ids = context.get('active_ids', [])
        self.check_estado_solicitudes(cr, uid, sc_ids, context=context)
        pedido_id = self.pool.get('grp.pedido.compra').do_merge_sc(cr, uid, sc_ids, context=context)
        return {
            'target': 'current',
            'res_id': pedido_id,
            'name': _('Pedidos de Compra'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'grp.pedido.compra',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

grp_consolidar_pedidos_compra()
