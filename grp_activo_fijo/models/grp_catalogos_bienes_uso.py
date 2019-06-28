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

class grp_cat_obras_arte(osv.osv):
    _name = "grp.cat_obras_arte"
    _description = u"Categorías de obras de arte"
    _order = 'name'

    _columns = {
        'name': fields.char(u'Categoría de obra de arte', size=50, required=True, select="1"),
    }

    _sql_constraints = [
        ('grp_cat_obras_arte', 'unique(name)', u'Ya existe una categoría de obras de arte del mismo tipo.')]


class grp_gen_obras_arte(osv.osv):
    _name = "grp.gen_obras_arte"
    _description = u"Géneros de obras de arte"
    _order = 'name'

    _columns = {
        'name': fields.char(u'Género de obra de arte', size=50, required=True, select="1"),
    }

    _sql_constraints = [('grp_gen_obras_arte', 'unique(name)', u'Ya existe un género de obras de arte del mismo tipo.')]


class grp_forma_obras_arte(osv.osv):
    _name = "grp.forma_obras_arte"
    _description = u"Formas de obras de arte"
    _order = 'name'

    _columns = {
        'name': fields.char('Forma de obra de arte', size=50, required=True, select="1"),
    }

    _sql_constraints = [
        ('grp_forma_obras_arte', 'unique(name)', u'Ya existe una forma de obra de arte del mismo tipo.')]


class grp_etiquetas_obras_arte(osv.osv):
    _name = "grp.etiquetas_obras_arte"
    _description = u"Etiquetas Técnicas de obras de arte"
    _order = 'name'

    _columns = {
        'name': fields.char(u'Técnica de obra de arte', size=50, required=True, select="1"),
    }

    _sql_constraints = [
        ('grp_etiquetas_obras_arte', 'unique(name)', u'Ya existe una técnica de obras de arte del mismo tipo.')]


class grp_tipos_bien_informatica(osv.osv):
    _name = "grp.tipos_bien_informatica"
    _description = u"Tipos de bien de informática"
    _order = 'name'

    _columns = {
        'name': fields.char(u'Tipo de bien informática', size=50, required=True, select="1"),
    }

    _sql_constraints = [('grp_tipos_bien_informatica', 'unique(name)',
                         u'Ya existe un tipo de bien de informática con el mismo nombre.')]


class grp_tipos_impresoras(osv.osv):
    _name = "grp.tipos_impresoras"
    _description = u"Tipos de impresoras"
    _order = 'name'

    _columns = {
        'name': fields.char('Tipo de impresora', size=50, required=True, select="1"),
    }

    _sql_constraints = [
        ('grp_tipos_impresoras', 'unique(name)', u'Ya existe un tipo de impresora con el mismo nombre.')]


class grp_motivos_baja(osv.osv):
    _name = "grp.motivos_baja"
    _description = u"Motivos de baja"
    _order = 'name'

    _columns = {
        'name': fields.char('Motivo de baja', size=50, required=True, select="1"),
        'account_id': fields.many2one('account.account', string="Cuenta contable", domain=[('type','!=','view')])
    }

    _sql_constraints = [('grp_motivos_baja', 'unique(name)', u'Ya existe un motivo de baja con el mismo nombre.')]
