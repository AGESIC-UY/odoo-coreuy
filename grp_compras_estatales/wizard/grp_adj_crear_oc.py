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

from openerp import netsvc

from openerp.osv import fields, osv
from openerp import SUPERUSER_ID


class grp_crear_oc_wiz(osv.osv_memory):
    _name = 'grp.wiz.crear.oc'
    _description = 'Wizard crear oc'
    _columns = {
        'pedido_compra_adjudicacion_id': fields.many2one('grp.pedido.compra', required=1, string=u'Pedido de Compras'),
        'pedido_compra_ampliado_id': fields.many2one('grp.pedido.compra', string=u'Pedido Ampliado'),
        'nro_ampliacion': fields.related('pedido_compra_ampliado_id', 'nro_ampliacion', string=u'N° Ampliación',
                                         type='char'),
    }

    def on_change_pedido_ampliado(self, cr, uid, ids, pedido_compra_ampliado_id):
        context = {}
        result = {}
        result.setdefault('value', {})
        result['value'] = {'nro_ampliacion': False}
        pedido_compra_obj = self.pool.get('grp.pedido.compra')
        pedido_compra_id = pedido_compra_obj.browse(cr, uid, pedido_compra_ampliado_id, context=context)
        if pedido_compra_id:
            result['value'].update({'nro_ampliacion': pedido_compra_id.nro_ampliacion or False})
        return result

    def button_wzrd_crear_ampliacion_oc(self, cr, uid, ids, context=None):
        adjudicacion_obj = self.pool.get('grp.cotizaciones')
        wiz = self.browse(cr, uid, ids, context=context)[0]
        if wiz.pedido_compra_ampliado_id and wiz.pedido_compra_ampliado_id.id:
            return adjudicacion_obj.button_Crear_OC_adjudicacion_ampliada(cr, uid, context.get('active_ids', []),
                                                                          wiz.pedido_compra_ampliado_id,
                                                                          context=context)
        return adjudicacion_obj.button_Crear_OC(cr, uid, context.get('active_ids', []), context=context)


grp_crear_oc_wiz()

