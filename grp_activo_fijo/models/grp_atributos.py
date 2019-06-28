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


class grp_atributos(osv.osv):
    _name = 'grp.atributos'
    _description = 'Atributos de activo fijo'

    _columns = {
        'category_id': fields.many2one('account.asset.category', u'Categoría/Subcategoría', required=True),
        'name': fields.char(u'Atributo', required=True),
        'valor_ids': fields.one2many('grp.valores_atributos', 'atributo_id', 'Valores'),
        'company_related': fields.related('category_id', 'company_id', type='many2one', relation='res.company', string=u"Compañía", readonly=True),
    }

    _sql_constraints = [
        ('grp_atributos', 'unique(name, category_id)', u'Ya existe un atributo con la misma categoría.')]


class grp_valores_atributos(osv.osv):
    _name = 'grp.valores_atributos'
    _description = 'Valores de los atributos de activo fijo'

    _columns = {
        'name': fields.char('Valor', required=True),
        'atributo_id': fields.many2one('grp.atributos', 'Atributo', ondelete='cascade'),
    }
