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
from openerp import SUPERUSER_ID

class grp_product_category(osv.osv):
    _inherit = 'product.category'

    _columns = {
        'activo_fijo': fields.boolean('Es de activo fijo'),
    }


grp_product_category()


class grp_product_template(osv.osv):
    _inherit = "product.template"

    def _es_inventario(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            es_grupo_inventario = (self.pool.get('res.users').has_group(cr,uid,'grp_seguridad.grp_visibilidad_inventario') and (uid!=SUPERUSER_ID) ) or (uid==SUPERUSER_ID)
            res[rec.id] = es_grupo_inventario
        return res

    def _default_es_inventario(self, cr, uid, context=None):
        return (self.pool.get('res.users').has_group(cr,uid,'grp_seguridad.grp_visibilidad_inventario') and (uid!=SUPERUSER_ID) ) or (uid==SUPERUSER_ID)

    def _es_contabilidad(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            pool_users = self.pool.get('res.users')
            res[rec.id] = pool_users.has_group(cr, uid, 'account.group_account_invoice')
        return res

    def _es_almacenero(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            pool_users = self.pool.get('res.users')
            res[rec.id] = pool_users.has_group(cr, uid, 'grp_seguridad.grp_compras_sr_Encargado_de_almacen')
        return res

    def _es_manager(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            # pool_users = self.pool.get('res.users')
            res[rec.id] = (uid==SUPERUSER_ID)
        return res

    def _es_responsable_sice(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            pool_users = self.pool.get('res.users')
            res[rec.id] = pool_users.has_group(cr, uid, 'grp_seguridad.grp_responsable_sice')
        return res

    def buscar_unidades_ids(self, cr, uid, ids, name, args, context=None):
        result = {}
        prod_uom_object = self.pool.get('product.uom')
        grp_art_sice_obj = self.pool.get("grp.sice_art_serv_obra")
        for rec in self.browse(cr, uid, ids):
            result[rec.id] = False
            if rec.grp_sice_cod > 0:
                articulo_sice_ids = grp_art_sice_obj.search(cr, 1, [('cod', '=', rec.grp_sice_cod)])
                if articulo_sice_ids:
                    articulo_sice_id = articulo_sice_ids[0]
                    articulo_sice = grp_art_sice_obj.browse(cr, 1, articulo_sice_id)
                    unidades_med_sice_ids = [x.id for x in articulo_sice.unidades_med_ids]
                    uom_ids = prod_uom_object.search(cr, 1, [('sice_uom_id', 'in', unidades_med_sice_ids)])
                    if uom_ids:
                        result[rec.id] = uom_ids
            else:
                uom_ids = prod_uom_object.search(cr, uid, [('active', '=', True)], context=context)
                if uom_ids:
                    result[rec.id] = uom_ids
        return result

    def _check_codigo_sice(self, cr, uid, ids):
        ptemplate_obj = self.pool.get('product.template')
        for ptemplate in self.browse(cr, uid, ids):
            if ptemplate.grp_sice_cod and ptemplate.grp_sice_cod > 0:
                id_prod = ptemplate_obj.search(cr, uid, [('grp_sice_cod', '=', ptemplate.grp_sice_cod),
                                                         ('id', '<>', ptemplate.id)])
                if id_prod:
                    return False
        return True

    _columns = {
        'grp_objeto_del_gasto': fields.integer('Objeto del Gasto'),
        'grp_sice_cod': fields.integer('Código SICE'),
        'domain_art_uom_ids': fields.function(buscar_unidades_ids, method=True, type='many2many',
                                              relation='product.uom', string='Lista domain unidades de medida'),
        'es_inventario': fields.function(_es_inventario, type='boolean', string=u'Es inventario?'),
        'es_contabilidad': fields.function(_es_contabilidad, type="boolean", string='Es grupo contabilidad'),
        'es_almacenero': fields.function(_es_almacenero, type="boolean", string='Es grupo almacenero'),
        'es_manager': fields.function(_es_manager, type="boolean", string='Es grupo manager'),
        'es_resp_sice': fields.function(_es_responsable_sice, type="boolean", string="Es grupo responsable SICE"),
        'no_inventory': fields.boolean('No inventariable'),
    }

    _constraints = [
        (_check_codigo_sice, u'Código SICE existente. No puede crear un artículo sice desde la pantalla de productos.',
         ['grp_sice_cod']),
    ]

    _defaults = {
        'cost_method': 'real',
    }

    def onchange_categ_id(self, cr, uid, ids, categ_id):
        context = {}
        if categ_id:
            category_object = self.pool.get('product.category').browse(cr, uid, categ_id, context=context)
            valuation = False
            if category_object and category_object.property_stock_account_input_categ:
                valuation = 'real_time'
            else:
                valuation = 'manual_periodic'
            expense_account = category_object.property_account_expense_categ
            income_account = category_object.property_account_income_categ
            return {'value': {'property_account_expense': expense_account and expense_account.id or False,
                              'property_account_income': income_account and income_account.id or False,
                              'valuation': valuation}}
        return {'value': {'property_account_expense': False, 'property_account_income': False}}

    def onchange_type(self, cr, uid, ids, type):
        res = super(grp_product_template, self).onchange_type(cr, uid, ids, type)
        if not res:
            res = {'value': {}}
        if not res.get('value', False):
            res['value'] = {}
        v = self.pool['product.product'].onchange_type(cr, uid, ids, type)
        res['value'].update(v.get('value', {}))
        return res

grp_product_template()


class grp_compras_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'dummy': fields.boolean('dummy'),
        'nombre_prod_proveedor': fields.char('Nombre producto proveedor'),
        'grp_warehouse': fields.many2one('stock.warehouse', 'Almacén'),
    }

    _defaults = {
        'sale_ok': False,
        'cost_method': 'real',
        'categ_id': None,
        'type': None,
        'uom_id': None,
    }

    def onchange_categ_id(self, cr, uid, ids, categ_id):
        context = {}
        if categ_id:
            category_object = self.pool.get('product.category').browse(cr, uid, categ_id, context=context)
            valuation = False
            if category_object and category_object.property_stock_account_input_categ:
                valuation = 'real_time'
            else:
                valuation = 'manual_periodic'
            expense_account = category_object.property_account_expense_categ
            income_account = category_object.property_account_income_categ
            return {'value': {'property_account_expense': expense_account and expense_account.id or False,
                              'property_account_income': income_account and income_account.id or False,
                              'valuation': valuation}}
        return {'value': {'property_account_expense': False, 'property_account_income': False}}

    def onchange_type(self, cr, uid, ids, type):
        res = super(grp_compras_product, self).onchange_type(cr, uid, ids, type)
        if type != 'consu':
            if not res:
                res = {'value': {}}
            if not res['value']:
                res['value'] = {}
            res['value']['no_inventory'] = False
        return res

    def need_procurement(self, cr, uid, ids, context=None):
        for product in self.browse(cr, uid, ids, context=context):
            if product and \
               product.type != 'service' or not (product.type=='consu' and product.no_inventory):
                return True
        return super(grp_compras_product, self).need_procurement(cr, uid, ids, context=context)

grp_compras_product()
