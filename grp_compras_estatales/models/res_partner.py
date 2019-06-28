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
from openerp.osv.expression import get_unaccent_wrapper


class grp_rupe(osv.osv):
    _inherit = 'res.partner'

    _columns = {
        'domicilio_constituido': fields.char("Domicilio constituido", size=128),
        'id_rupe': fields.integer("ID RUPE", size=10),
        'fecha_creacion_rupe': fields.date(u'Fecha creación'),
        'fecha_modif_rupe': fields.date(u'Fecha última modificación'),
        'version_rupe': fields.integer(u'Versión', size=10),
        'estado_rupe': fields.char('Estado RUPE'),

        'tipo_doc_rupe': fields.selection([
            ('R', 'R - RUT'),
            ('CI', 'CI - Cedula de Identidad'),
            ('PS', 'PS - Pasaporte'),
            # MVARELA 31/01/2018: Se agrega tipo T - Propio de Tesoreria
            ('T', 'T - Propio de Tesoreria'),
            ('NIE', 'NIE - Documento Extranjero'),
            ('O', 'O - Otros'),
            ('CFE', u'CFE - Código Fiscal Extranjero'),
        ], 'Tipo documento', select=True),
        'tipo_doc_siif': fields.selection([
            ('R', 'R - RUT'),
            ('C', 'CI - Cedula de Identidad'),
            ('T', u'T - Propio de Tesorería'),
            ('P', 'P - Pasaporte'),
            ('E', 'E - Documento Extranjero'), ], 'Tipo documento SIIF', select=True),

        'nro_doc_rupe': fields.char(u'Nro documento', size=255),
        'id_rubro': fields.many2one('grp.rupe.rubro', 'Rubro'),
        'funcionario': fields.boolean('Funcionario'),
    }
    _sql_constraints = [('nro_doc_rupe_uniq', 'unique(nro_doc_rupe)',
                         u'Número RUT existente. No se pueden crear dos proveedores/clientes con el mismo RUT.')]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):

            self.check_access_rights(cr, uid, 'read')
            where_query = self._where_calc(cr, uid, args, context=context)
            self._apply_ir_rules(cr, uid, where_query, 'read', context=context)
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            unaccent = get_unaccent_wrapper(cr)

            query = """SELECT id
                         FROM res_partner
                      {where} ({nro_doc_rupe} {operator} {percent}
                           OR {display_name} {operator} {percent})
                     ORDER BY {display_name}
                    """.format(where=where_str, operator=operator,
                               display_name=unaccent('display_name'),
                               nro_doc_rupe=unaccent('nro_doc_rupe'),
                               percent=unaccent('%s'))

            where_clause_params += [search_name, search_name]
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            cr.execute(query, where_clause_params)
            ids = map(lambda x: x[0], cr.fetchall())

            if ids:
                return self.name_get(cr, uid, ids, context)
            else:
                return []
        return super(grp_rupe, self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)


grp_rupe()
