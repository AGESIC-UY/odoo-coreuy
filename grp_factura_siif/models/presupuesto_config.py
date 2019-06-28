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

from openerp.osv import fields, osv, expression
import logging

class presupuesto_config(osv.osv):
    _name = "presupuesto.config"
    _description = "Control Presupuestal"
    _logger = logging.getLogger(_name)

    _columns = {
        'name':fields.char('Nombre', size=50, required=True),
        'presupuesto_id': fields.many2one('presupuesto.presupuesto', 'Presupuesto'),
        'create_date': fields.datetime(u'Fecha de creación', readonly=True),
        'anio_fiscal': fields.related('name','fiscal_year', string=u'Año fiscal', readonly=True),
        'tipo_control': fields.selection((('sin_control','Sin control'),  ('control_total','Control total')), 'Tipo de control'),
    }

presupuesto_config()

class presupuesto_grupo(osv.osv):
    _name = "presupuesto.grupo"
    _description = "Presupuesto grupo"

    _columns = {
        'name':fields.char('Grupo', size=2, required=True),
        'descripcion': fields.char(u'Descripción', required=True),
        'subgrupo_ids': fields.one2many('presupuesto.subgrupo','grupo_id', 'Grilla subgrupos'),
    }
presupuesto_grupo()

class presupuesto_subgrupo(osv.osv):
    _name = "presupuesto.subgrupo"
    _description = "Presupuesto subgrupo"

    _columns = {
        'grupo_id':fields.many2one('presupuesto.grupo', 'Presupuesto grupo'),
        'name':fields.char('Subgrupo', size=2, required=True),
        'descripcion': fields.char(u'Descripción', required=True),
    }
presupuesto_subgrupo()

class presupuesto_concepto(osv.osv):
    _name = "presupuesto.concepto"
    _description = "Presupuesto concepto"

    def _concatenarFuncion (self, cr, uid, ids, name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            nombre_completo = rec.concepto + ' - ' + rec.descripcion
            result[rec.id] = nombre_completo.strip()
        return result

    _columns = {
        'name':fields.function(_concatenarFuncion, type='char', method=True, string='Nombre', store=True, readonly=True),
        'concepto':fields.char('Concepto', size=2, required=True),
        'descripcion': fields.char(u'Descripción', required=True),
        'visible_documento': fields.boolean(u'¿Visible en documentos?'),
        'linea_concepto_ids': fields.one2many('presupuesto.linea.concepto','concepto_id', 'Linea concepto'),
        'exceptuado_sice': fields.boolean('Exceptuado SICE'),
    }
    
    sql_constraints=[('presupuesto_concepto_unique_name','unique(name)','Error, el concepto debe ser unico')]

presupuesto_concepto()

class presupuesto_linea_concepto(osv.osv):
    _name = "presupuesto.linea.concepto"
    _description = u"Presupuesto linea concepto"

    def onchange_grupo(self, cr, uid, ids, grupo_id, context=None):
        value = {}
        if grupo_id:
            obj = self.pool.get('presupuesto.grupo').browse(cr, uid, grupo_id)
            value = {
                'descripcion':obj.descripcion
            }
        else:
            value = {'descripcion':False}
        return {'value': value}

    _columns = {
        'concepto_id':fields.many2one('presupuesto.concepto', 'Presupuesto concepto',ondelete='restrict'),
        'grupo_id':fields.many2one('presupuesto.grupo', 'Grupo',required=True),
        'descripcion': fields.related('grupo_id','descripcion',type='char',string=u'Descripción', readonly="1"),
    }

presupuesto_linea_concepto()

class presupuesto_objeto_gasto(osv.osv):
    _name = "presupuesto.objeto.gasto"
    _description = "ODG"
    _rec_name = 'odg_aux'

    def tiene_combinacion(self, cr, uid, ids, context=None):
        for obj_gasto in self.browse(cr,uid,ids,context=context):
            obj_gasto_ids = self.search(cr, uid, [('name', '=', obj_gasto.name),('grupo_id', '=', obj_gasto.grupo_id.id),('subgrupo_id','=', obj_gasto.subgrupo_id.id), ('auxiliar', '=', obj_gasto.auxiliar)], context=context)
            if len(obj_gasto_ids) >1:
                return False
        return True

    def onchange_grupo(self, cr, uid, ids, grupo_id, context=None):
        value = {}
        domain_ids=[]
        if grupo_id:
            obj = self.pool.get('presupuesto.grupo').browse(cr, uid, grupo_id)
            subgrupo_ids=self.pool.get('presupuesto.subgrupo').search(cr,uid,[('grupo_id','=',obj.id)])
            for id_p in subgrupo_ids:
                domain_ids.append(id_p)
            value = {
                'descripcion_grupo':obj.descripcion,'domain_ids':domain_ids
            }
        else:
            value = {'descripcion_grupo':False,'domain_ids':False}
        return {'value': value}

    def onchange_subgrupo(self, cr, uid, ids, subgrupo_id, context=None):
        value = {}
        domain_ids=[]
        if subgrupo_id:
            obj = self.pool.get('presupuesto.subgrupo').browse(cr, uid, subgrupo_id)

            value = {
                'descripcion_subgrupo':obj.descripcion
            }
        else:
            value = {'descripcion_subgrupo':False}
        return {'value': value}

    def _get_odg_aux(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.auxiliar:
                res[rec.id] = rec.name + ' - ' + rec.auxiliar
            else:
                res[rec.id] = rec.name
        return res

    _columns = {
        'odg_aux': fields.function(_get_odg_aux, method=True, type='char', string=u'Nombre'),
        'grupo_id':fields.many2one('presupuesto.grupo', 'Grupo',required=True),
        'subgrupo_id':fields.many2one('presupuesto.subgrupo', 'Subgrupo', required=True),
        'descripcion_subgrupo': fields.related('subgrupo_id','descripcion',type='char',string=u'Descripción', readonly="1"),
        'descripcion_grupo': fields.related('grupo_id','descripcion',type='char',string=u'Descripción', readonly="1"),
        'descripcion': fields.char(u'Descripción'),
        'auxiliar': fields.char('Auxiliar', size=3,required=True),
        'name': fields.char('ODG', size=3,required=True),
        'exceptuado_sice': fields.boolean('Exceptuado SICE'),
        'domain_ids': fields.many2many('presupuesto.subgrupo', 'grp_presupuesto_rel', 'subgrupo_id', 'group_id', u'Filtro'),
        'objeto_especifico': fields.boolean(u'Objeto específico'),
    }

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('name', operator, name)]
        else:
            domain = ['|', ('name', operator, name), ('auxiliar', operator, name)]
        ids = self.search(cr, user, expression.AND([domain, args]), limit=limit, context=context)
        return self.name_get(cr, user, ids, context=context)

    _constraints = [(tiene_combinacion, u'La combinación de Grupo-Subgrupo-ODG-Auxiliar debe ser única.', ['group_id','name','subgrupo_id','auxiliar'])]

presupuesto_objeto_gasto()

