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


class grp_rupe_rubro(osv.osv):
    _name = 'grp.rupe.rubro'
    _description = u'Código y descripción de rubros RUPE'
    _rec_name = 'descripcion'
    _columns = {
        'id_rupe': fields.many2one('res.partner', 'id_rubro', 'Proveedor', readonly=True, invisible=True),
        'codigo': fields.integer(u'Código'),
        'descripcion': fields.char(u'Descripción'),
    }


grp_rupe_rubro()
