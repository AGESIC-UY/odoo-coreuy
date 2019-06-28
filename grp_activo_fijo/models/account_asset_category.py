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

TIPO_CATEGORIA = [
    ('inf', u'Informática'),
    ('inm', 'Inmuebles'),
    ('lab', 'Laboratorio'),
    ('veh', u'Vehículos'),
    ('obc', 'Obras en curso'),
    ('art', 'Obras de arte'),
]

class grp_detalle_categoria_activo(osv.osv):
    _inherit = 'account.asset.category'

    def _category_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _order = 'name'

    _columns = {
        'codigo': fields.integer(u"Código categoría"),
        'parent_id': fields.many2one("account.asset.category", string=u"Categoría padre"),
        'complete_name': fields.function(_category_name_get_fnc, type="char", string='Nombre completo'),
        'tipo': fields.selection(TIPO_CATEGORIA, "Tipo"),
        'categoria_ue_notificacion_ids': fields.one2many("grp.categoria_ue_notificacion", 'asset_category_id', string=u"Notificación"),
    }

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def onchange_parent_id(self, cr, uid, ids, parent_id, context=None):
        if parent_id:
            codigo = self.browse(cr, uid, parent_id, context=context).codigo
            return {'value': {'codigo': codigo}}
        return True

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from account_asset_category where id IN %s', (tuple(ids),))
            ids = filter(None, map(lambda x: x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, u'Error! No se pueden crear categorías recursivas.', ['parent_id'])
    ]

class grp_categoria_ue_notificacion(osv.osv):
    _name = 'grp.categoria_ue_notificacion'

    _columns = {
        'asset_category_id': fields.many2one("account.asset.category", string=u"Categoría de activo fijo"),
        'operating_unit_id': fields.many2one("operating.unit", string="Unidad Ejecutora"),
        'group_id': fields.many2one("res.groups", string="Grupo a notificar"),
    }