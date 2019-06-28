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

class financiamiento_siif(osv.osv):
    _name = "financiamiento.siif"
    _description = u"Financiamiento SIIF"

    def _concatenarFuncion(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            nombre_completo = rec.codigo + ' - ' + rec.descripcion
            result[rec.id] = nombre_completo.strip()
        return result

    _columns = {
        'name': fields.function(_concatenarFuncion, type='char', method=True, string='Nombre', store=True, readonly=True),
        'codigo': fields.char(u'Código', size=2, required=True),
        'descripcion': fields.char(u'Descripción', size=100, required=True),
        'visible_documento': fields.boolean(u'¿Visible en documentos?'),
        'exceptuado_sice': fields.boolean('Exceptuado SICE'),
    }

    _sql_constraints = [
        ('grp_financiamiento_unique', 'unique(codigo)', u"Ya existe un Financiamiento con dicho código. El código debe ser único."),
    ]
financiamiento_siif()


class codigo_sir_siif(osv.osv):
    _name = "codigo.sir.siif"
    _description = u"Codigo sir SIIF"

    def _concatenarFuncion(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            nombre_completo = rec.codigo + ' - ' + rec.descripcion
            result[rec.id] = nombre_completo.strip()
        return result

    _columns = {
        'name': fields.function(_concatenarFuncion, type='char', method=True, string='Nombre', store=True, readonly=True),
        'codigo': fields.char(u'Código SIR', size=18, required=True),
        'descripcion': fields.char(u'Descripción', size=60, required=True),
        'visible_documento': fields.boolean(u'¿Visible en documentos?'),
    }

    _sql_constraints = [
        ('grp_codigo_sir_unique', 'unique(codigo)', u"Ya existe un Código sir con dicho código. El código debe ser único."),
    ]
codigo_sir_siif()

class tipo_documento_siif(osv.osv):
    _name = "tipo.documento.siif"
    _description = u"Tipo de documento SIIF"

    def _concatenarFuncion (self, cr, uid, ids, name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            nombre_completo = rec.codigo + ' - ' + rec.descripcion
            result[rec.id] = nombre_completo.strip()
        return result

    _columns = {
        'name': fields.function(_concatenarFuncion, type='char', method=True, string='Nombre', store=True, readonly=True),
        'codigo': fields.char(u'Código', size=2, required=True),
        'descripcion': fields.char(u'Descripción', size=60, required=True),
        'visible_documento_afectacion': fields.boolean(u'¿Visible en documento de afectación?'),
        'visible_documento_compromiso': fields.boolean(u'¿Visible en documento de compromiso?'),
        'visible_documento_obligacion': fields.boolean(u'¿Visible en documento de obligación?'),
    }

    _sql_constraints = [
        ('grp_tipo_doc_siif_unique', 'unique(codigo)', u"Ya existe un Tipo de documento SIIF con dicho código. El código debe ser único."),
    ]

tipo_documento_siif()


class tipo_ejecucion_siif(osv.osv):
    _name = "tipo.ejecucion.siif"
    _description = "Tipo de ejecucion SIIF"

    def _concatenarFuncion(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            nombre_completo = rec.codigo + ' - ' + rec.descripcion
            result[rec.id] = nombre_completo.strip()
        return result

    _columns = {
        'name': fields.function(_concatenarFuncion, type='char', method=True, string='Nombre', store=True, readonly=True),
        'codigo': fields.char(u'Código', size=2, required=True),
        'descripcion': fields.char(u'Descripción', size=60, required=True),
        'visible_documento': fields.boolean(u'¿Visible en documentos?'),
        'exceptuado_sice': fields.boolean('Exceptuado SICE'),
    }

tipo_ejecucion_siif()


class fondo_rotatorio_siif(osv.osv):
    _name = "fondo.rotatorio.siif"
    _description = u"Fondo Rotatorio SIIF"

    # Se va a buscar al modelo presupuesto si existe alguno que tenga asociado el mismo año fiscal ingresado en el form y verifica que se ingrese el mismo inciso.
    def _check_inciso(self, cr, uid, ids, context=None):
        existe = False
        presupuesto_obj = self.pool.get('presupuesto.presupuesto')
        for obj in self.browse(cr, uid, ids, context=context):
            presupuesto_ids = presupuesto_obj.search(cr, uid, [('fiscal_year', '=', obj.fiscal_year.id)])
            for presupuesto in presupuesto_obj.browse(cr, uid, presupuesto_ids):
                if presupuesto.inciso == obj.inciso.inciso:
                    existe = True
        return existe

    _columns = {
        'name': fields.char(u'Número de fondo rotatorio', size=2, required=True),
        'fiscal_year': fields.many2one('account.fiscalyear', u'Año fiscal', required=True),
        'moneda': fields.char('Moneda', size=2, required=True),
        # 'inciso': fields.char('Inciso', size=2, required=True),
        'financiamiento_id': fields.many2one('financiamiento.siif', 'Financiamiento', required=True),
        # 'ue': fields.char('Unidad ejecutora', size=3, required=True),
        'inciso': fields.many2one('grp.estruc_pres.inciso', 'Inciso', required=True, domain="[('fiscal_year_id','=',fiscal_year)]"),
        'ue': fields.many2one('grp.estruc_pres.ue', 'Unidad ejecutora', required=True, domain="[('fiscal_year_id','=',fiscal_year),('inciso_id','=',inciso)]"),
    }
    _sql_constraints = [
        ('instance_uniq', 'unique(fiscal_year,inciso,ue,financiamiento_id,moneda,name)', u'Error!, La combinación: Año fiscal - Inciso - Unidad ejecutora - Financiamiento - Moneda - Número de fondo rotatorio debe ser única!'),
    ]

    _constraints = [
        (_check_inciso, u'Error!, El valor de inciso debe existir en algún presupuesto', ['fiscal_year', 'inciso'])
    ]

    def onchange_fiscal_year(self, cr, uid, ids):
        return {'value':{'inciso':False}}

    def onchange_inciso(self, cr, uid, ids):
        return {'value':{'ue':False}}

fondo_rotatorio_siif()


class motivo_intervencion_tc(osv.osv):
    _name = "motivo.intervencion.tc"
    _description = u"Motivo de intervención del Tribunal de Cuentas"

    def _concatenarFuncion(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            nombre_completo = rec.codigo + ' - ' + rec.descripcion
            result[rec.id] = nombre_completo.strip()
        return result

    _columns = {
        'name': fields.function(_concatenarFuncion, type='char', method=True, string='Nombre', store=True, readonly=True),
        'codigo': fields.char(u'Código', size=2, required=True),
        'descripcion': fields.char('Motivo', size=100, required=True),
        'impacta_documento': fields.boolean(u'¿Impacta en documentos?'),
    }

motivo_intervencion_tc()
