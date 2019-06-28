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
import logging

_logger = logging.getLogger(__name__)


class grp_estruc_pres_inciso(osv.osv):
    _name = 'grp.estruc_pres.inciso'
    _description = 'Estructura presupuesto - Inciso'
    _rec_name = 'inciso'

    _columns = {
        'fiscal_year_id': fields.many2one('account.fiscalyear', u'Año fiscal'),
        'inciso': fields.char('Inciso', size=2),
    }

class grp_estruc_pres_ue(osv.osv):
    _name = 'grp.estruc_pres.ue'
    _description = 'Estructura presupuesto - Unidad Ejecutora'
    _rec_name = 'ue'

    _columns = {
        'inciso_id': fields.many2one('grp.estruc_pres.inciso', 'Inciso'),
        'ue': fields.char('Unidad ejecutora', size=3),
        'fiscal_year_id': fields.related('inciso_id', 'fiscal_year_id', string=u'Año fiscal', type='many2one', relation='account.fiscalyear', readonly="1"),
    }

class grp_estruc_pres_odg(osv.osv):
    _name = 'grp.estruc_pres.odg'
    _description = 'Estructura presupuesto - Objeto del gasto'
    _rec_name = 'odg'

    _columns = {
        'ue_id': fields.many2one('grp.estruc_pres.ue', 'Unidad ejecutora'),
        'odg': fields.char('Objeto del gasto', size=3),
        'fiscal_year_id': fields.related('ue_id', 'fiscal_year_id', string=u'Año fiscal', type='many2one', relation='account.fiscalyear', readonly="1"),
        'inciso_id': fields.related('ue_id', 'inciso_id', string='Inciso', type='many2one', relation='grp.estruc_pres.inciso', readonly="1"),
    }

class grp_estruc_pres_aux(osv.osv):
    _name = 'grp.estruc_pres.aux'
    _description = 'Estructura presupuesto - Auxiliar'
    _rec_name = 'aux'

    _columns = {
        'odg_id': fields.many2one('grp.estruc_pres.odg', 'Objeto del gasto'),
        'aux': fields.char('Auxiliar', size=3),
        'fiscal_year_id': fields.related('odg_id', 'fiscal_year_id', string=u'Año fiscal', type='many2one', relation='account.fiscalyear', readonly="1"),
        'inciso_id': fields.related('odg_id', 'inciso_id', string='Inciso', type='many2one', relation='grp.estruc_pres.inciso', readonly="1"),
        'ue_id': fields.related('odg_id', 'ue_id', string='Unidad ejecutora', type='many2one', relation='grp.estruc_pres.ue', readonly="1"),
    }

class grp_estruc_pres_ff(osv.osv):
    _name = 'grp.estruc_pres.ff'
    _description = 'Estructura presupuesto - Financiamiento'
    _rec_name = 'ff'

    _columns = {
        'aux_id': fields.many2one('grp.estruc_pres.aux', 'Auxiliar'),
        'ff': fields.char('FF', size=2),
        'fiscal_year_id': fields.related('aux_id', 'fiscal_year_id', string=u'Año fiscal', type='many2one',  relation='account.fiscalyear', readonly="1"),
        'inciso_id': fields.related('aux_id', 'inciso_id', string='Inciso', type='many2one', relation='grp.estruc_pres.inciso', readonly="1"),
        'ue_id': fields.related('aux_id', 'ue_id', string='Unidad ejecutora', type='many2one', relation='grp.estruc_pres.ue', readonly="1"),
        'odg_id': fields.related('aux_id', 'odg_id', string='Objeto del gasto', type='many2one', relation='grp.estruc_pres.odg', readonly="1"),
    }

class grp_estruc_pres_programa(osv.osv):
    _name = 'grp.estruc_pres.programa'
    _description = 'Estructura presupuesto - Programa'
    _rec_name = 'programa'

    _columns = {
        'ff_id': fields.many2one('grp.estruc_pres.ff', 'Financiamiento'),
        'programa': fields.char('Programa', size=3),
        'fiscal_year_id': fields.related('ff_id', 'fiscal_year_id', string=u'Año fiscal', type='many2one', relation='account.fiscalyear', readonly="1"),
        'inciso_id': fields.related('ff_id', 'inciso_id', string='Inciso', type='many2one', relation='grp.estruc_pres.inciso', readonly="1"),
        'ue_id': fields.related('ff_id', 'ue_id', string='Unidad ejecutora', type='many2one', relation='grp.estruc_pres.ue', readonly="1"),
        'odg_id': fields.related('ff_id', 'odg_id', string='Objeto del gasto', type='many2one', relation='grp.estruc_pres.odg', readonly="1"),
        'aux_id': fields.related('ff_id', 'aux_id', string='Auxiliar', type='many2one', relation='grp.estruc_pres.aux', readonly="1"),
    }

class grp_estruc_pres_proyecto(osv.osv):
    _name = 'grp.estruc_pres.proyecto'
    _description = 'Estructura presupuesto - Proyecto'
    _rec_name = 'proyecto'

    _columns = {
        'programa_id': fields.many2one('grp.estruc_pres.programa', 'Programa'),
        'proyecto': fields.char('Proyecto', size=3),
        'fiscal_year_id': fields.related('programa_id', 'fiscal_year_id', string=u'Año fiscal', type='many2one', relation='account.fiscalyear', readonly="1"),
        'inciso_id': fields.related('programa_id', 'inciso_id', string='Inciso', type='many2one', relation='grp.estruc_pres.inciso', readonly="1"),
        'ue_id': fields.related('programa_id', 'ue_id', string='Unidad ejecutora', type='many2one', relation='grp.estruc_pres.ue', readonly="1"),
        'odg_id': fields.related('programa_id', 'odg_id', string='Objeto del gasto', type='many2one', relation='grp.estruc_pres.odg', readonly="1"),
        'aux_id': fields.related('programa_id', 'aux_id', string='Auxiliar', type='many2one', relation='grp.estruc_pres.aux', readonly="1"),
        'ff_id': fields.related('programa_id', 'ff_id', string='Financiamiento', type='many2one', relation='grp.estruc_pres.ff', readonly="1"),
    }

class grp_estruc_pres_moneda(osv.osv):
    _name = 'grp.estruc_pres.moneda'
    _description = 'Estructura presupuesto - Moneda'
    _rec_name = 'moneda'

    _columns = {
        'proyecto_id': fields.many2one('grp.estruc_pres.proyecto', 'Proyecto'),
        'moneda': fields.char('Moneda', size=2),
        'fiscal_year_id': fields.related('proyecto_id', 'fiscal_year_id', string=u'Año fiscal', type='many2one', relation='account.fiscalyear', readonly="1"),
        'inciso_id': fields.related('proyecto_id', 'inciso_id', string='Inciso', type='many2one', relation='grp.estruc_pres.inciso', readonly="1"),
        'ue_id': fields.related('proyecto_id', 'ue_id', string='Unidad ejecutora', type='many2one', relation='grp.estruc_pres.ue', readonly="1"),
        'odg_id': fields.related('proyecto_id', 'odg_id', string='Objeto del gasto', type='many2one', relation='grp.estruc_pres.odg', readonly="1"),
        'aux_id': fields.related('proyecto_id', 'aux_id', string='Auxiliar', type='many2one', relation='grp.estruc_pres.aux', readonly="1"),
        'ff_id': fields.related('proyecto_id', 'ff_id', string='Financiamiento', type='many2one', relation='grp.estruc_pres.ff', readonly="1"),
        'programa_id': fields.related('proyecto_id', 'programa_id', string='Programa', type='many2one', relation='grp.estruc_pres.programa', readonly="1"),
    }

class grp_estruc_pres_tc(osv.osv):
    _name = 'grp.estruc_pres.tc'
    _description = 'Estructura presupuesto - Tipo de credito'
    _rec_name = 'tc'

    _columns = {
        'moneda_id': fields.many2one('grp.estruc_pres.moneda', 'Moneda'),
        'tc': fields.char(u'Tipo de crédito', size=1),
        'fiscal_year_id': fields.related('moneda_id', 'fiscal_year_id', string=u'Año fiscal', type='many2one', relation='account.fiscalyear', readonly="1"),
        'inciso_id': fields.related('moneda_id', 'inciso_id', string='Inciso', type='many2one', relation='grp.estruc_pres.inciso', readonly="1"),
        'ue_id': fields.related('moneda_id', 'ue_id', string='Unidad ejecutora', type='many2one', relation='grp.estruc_pres.ue', readonly="1"),
        'odg_id': fields.related('moneda_id', 'odg_id', string='Objeto del gasto', type='many2one', relation='grp.estruc_pres.odg', readonly="1"),
        'aux_id': fields.related('moneda_id', 'aux_id', string='Auxiliar', type='many2one', relation='grp.estruc_pres.aux', readonly="1"),
        'ff_id': fields.related('moneda_id', 'ff_id', string='Financiamiento', type='many2one', relation='grp.estruc_pres.ff', readonly="1"),
        'programa_id': fields.related('moneda_id', 'programa_id', string='Programa', type='many2one', relation='grp.estruc_pres.programa', readonly="1"),
        'proyecto_id': fields.related('moneda_id', 'proyecto_id', string='Proyecto', type='many2one', relation='grp.estruc_pres.proyecto', readonly="1"),
    }
