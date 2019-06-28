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


class grp_importar_adjudicacion(osv.osv_memory):
    _name = 'grp.wiz.importar.adjudicacion'
    _description = 'Importar adjudicación'
    _columns = {
        'pedido_compra_origen_id': fields.many2one('grp.pedido.compra', required=1, string=u'Pedido de Compras',
                                                   ondelete='cascade'),
        'pedido_compra_ampliado_id': fields.many2one('grp.pedido.compra', string=u'Pedidos Ampliados',
                                                     ondelete='cascade'),
        'nro_ampliacion': fields.related('pedido_compra_ampliado_id', 'nro_ampliacion', string=u'Nro Ampliacion',
                                         type='integer'),
    }

    def onchange_pedido_ampliado(self, cr, uid, ids, pedido_id, context=None):
        ampliac = False
        if pedido_id:
            pedido = self.pool.get('grp.pedido.compra').browse(cr, uid, pedido_id, context=context)
            if pedido.nro_ampliacion:
                ampliac = pedido.nro_ampliacion
        return {'value': {'nro_ampliacion': ampliac}}

    def button_wzrd_importar_adjudicacion(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        adjudicacion_obj = self.pool.get('grp.cotizaciones')
        wiz = self.browse(cr, uid, ids, context=context)[0]
        ctx = context.copy()
        ctx.update({'create': True})  # Incidencia 348

        if wiz.pedido_compra_ampliado_id and wiz.pedido_compra_ampliado_id.id:
            r = adjudicacion_obj.action_importar_adjudicacion_ampliada(cr, uid, context.get('active_ids', []),
                                                                       wiz.pedido_compra_ampliado_id, context=ctx)
        else:
            r = adjudicacion_obj.action_importar_adjudicacion(cr, uid, context.get('active_ids', []), context=ctx)
        return {'type': 'ir.actions.act_window_close'}


grp_importar_adjudicacion()

