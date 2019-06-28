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
from datetime import *
from openerp.tools.translate import _

ESTADO_INVENTARIO =[
    ('borrador', 'Borrador'),
    ('enproceso', 'En Proceso'),
    ('validado', 'Validado')
]

class grp_account_asset_inventory(osv.osv):
    _name = 'grp.account_asset_inventory'
    _description = 'Inventario de AF'
    _rec_name = 'referencia'

    def onchange_inventario_de(self, cr, uid, ids, inventario_de, context=None):
        result = {}
        if inventario_de == 'todos':
            result['value'] = {'categoria_id': False}
        return result

    _columns = {
        'referencia': fields.char("Referencia de inventario", size=60, required=True),
        'ubicacion_id': fields.many2one("hr.department", string=u"Ubicación inventariada", required=True),
        'categoria_id': fields.many2one("account.asset.category", string=u"Categoría de activo"),
        'company_id': fields.many2one("res.company", string=u"Compañía", required=True),
        'activo_ids': fields.one2many("grp.account_asset_inventory_line", 'inventario_id', string="Activos"),
        'activo_no_inv_ids': fields.one2many("grp.af_no_inventariado", 'inventario_id', string="Activos sin inventariar"),
        'inventario_de': fields.selection([('todos', 'Todos los activos'), ('categoria', u'Categoría de activo')],
                                          string="Inventario de", required=True),
        'fecha_inventario': fields.datetime("Fecha de inventario", readonly=True),
        'fecha_validacion': fields.datetime(u"Fecha de validación", readonly=True),
        'state': fields.selection(ESTADO_INVENTARIO, string="Estado")
    }

    _defaults = {
            'inventario_de': 'todos',
            'state': 'borrador',
            'fecha_inventario': datetime.now(),
            'company_id': lambda s, cr, uid, c: s.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

    def get_activos_line(self, cr, uid, id, ubicacion_id, categoria_id):
        asset_obj = self.pool.get('account.asset.asset')
        line_obj = self.pool.get('grp.account_asset_inventory_line')
        op = '=' if categoria_id else '!='
        asset_ids = asset_obj.search(cr, uid, [('state', '!=', 'baja'),
                                               ('department_id', 'child_of', ubicacion_id),
                                               ('category_id', op, categoria_id)])
        for obj in asset_obj.browse(cr, uid, asset_ids):
            line_obj.create(cr, uid, {
                'no_activo': obj.numero_activo,
                'activo_id': obj.id,
                'inventario_id': id
            })

    def iniciar_inventario(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids):
            self.write(cr, uid, obj.id, {'state': 'enproceso'})
            self.get_activos_line(cr, uid, obj.id, obj.ubicacion_id.id, obj.categoria_id.id)
        return True

    def validar(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids):
            self.write(cr, uid, obj.id, {'state': 'validado', 'fecha_validacion': datetime.now()})
        return True

    def cancelar(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids):
            self.write(cr, uid, obj.id, {'state': 'borrador', 'activo_ids': [(5,)]})

        return True

    def unlink(self, cr, uid, ids, context=None):
        inventory = self.browse(cr, uid, ids)
        for inv in inventory:
            if inv.state != 'borrador':
                raise osv.except_osv(u'Acción inválida!',
                                     u'No se puede eliminar un registro si este se encuentra en un estado distinto de Borrador.')

        return super(grp_account_asset_inventory, self).unlink(cr, uid, ids, context=context)


RESULTADO_RECUENTO =[
    ('correcto', 'Correcto'),
    ('sobrante', 'Sobrante'),
    ('faltante', 'Faltante')
]

class grp_account_asset_inventory_line(osv.osv):
    _name = 'grp.account_asset_inventory_line'

    def mapp_asset_inventory(self, cr, uid, ids, context=None):
        self_ids = self.pool.get('grp.account_asset_inventory_line').search(cr, uid, [('inventario_id', 'in', ids)])
        return self_ids

    _columns = {
        'no_activo': fields.char("No de activo", readonly=True),
        'activo_id': fields.many2one("account.asset.asset", string="Activo", readonly=True),
        'inventario_id': fields.many2one("grp.account_asset_inventory", string="Inventario"),
        'recuento': fields.selection(RESULTADO_RECUENTO, string="Resultado recuento"),
        'comentario': fields.char("Comentarios", size=60),
        'fecha_inventario': fields.related('inventario_id', 'fecha_inventario', string='Fecha de inventario', type='datetime'),
        'state': fields.related('inventario_id', 'state', type='selection', selection=ESTADO_INVENTARIO,string='Estado',
                                store={
                                    'grp.account_asset_inventory_line': (lambda self, cr, uid, ids, context: ids, [], 10),
                                    'grp.account_asset_inventory': (mapp_asset_inventory, ['state'], 50),
                                }),
        'ubicacion_id': fields.related('inventario_id', 'ubicacion_id', string=u"Ubicación inventariada", type='many2one', relation='hr.department'),
    }

    _defaults = {
    }

class grp_af_no_inventariado(osv.osv):
    _name = 'grp.af_no_inventariado'

    def mapp_asset_inventory(self, cr, uid, ids, context=None):
        self_ids = self.pool.get('grp.account_asset_inventory_line').search(cr, uid, [('inventario_id', 'in', ids)])
        return self_ids

    _columns = {
        'activo_id': fields.many2one("account.asset.asset", string="Activo"),
        'no_activo': fields.related('activo_id', 'numero_activo', string="No de activo", type="char", readonly=True),
        'comentario': fields.char("Comentarios", size=100),
        'inventario_id': fields.many2one("grp.account_asset_inventory", string="Inventario"),
    }