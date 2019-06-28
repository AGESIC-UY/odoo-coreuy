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

class presupuesto_linea(osv.osv):
    _name = "presupuesto.linea"
    _description = u"Líneas del presupuesto"

    _order = 'budget_id, ue, programa, proyecto, moneda, tipo_credito, financiamiento, objeto_gasto, auxiliar'

    def _get_total(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = record.monto + record.ajuste
        return res

    _columns = {
        'budget_id': fields.many2one('presupuesto.presupuesto', u'Presupuesto', required=True),
        'ue': fields.char('UE', size=3, required=True),
        'budget_inciso': fields.related('budget_id', 'inciso', type='char', string='Inciso', readonly=True),
        'budget_fiscal_year': fields.related('budget_id', 'fiscal_year', type='many2one',relation='account.fiscalyear',
                                             string=u'Año fiscal', readonly=True),
        'programa': fields.char('Programa', size=3),
        'proyecto': fields.char('Proyecto', size=3),
        'moneda': fields.char('MON', size=2),
        'tipo_credito': fields.char('TC', size=1),
        'financiamiento': fields.char('FF', size=2),
        'objeto_gasto': fields.char('ODG', size=3),
        'auxiliar': fields.char('AUX', size=3),
        'monto': fields.float('Monto inicial', required=True),
        'ajuste': fields.float('Ajuste', required=True),
        'descripcion': fields.char(u'Descripción'),
        'total': fields.function(_get_total, method=True, string=u'Crédito vigente', type='integer'),
    }

    def unlink(self, cr, uid, ids, context=None):
        #Al borrar una linea borro las estructuras que pertenecen a la linea
        estructura_obj = self.pool.get('presupuesto.estructura')
        estructura_ids = estructura_obj.search(cr, uid, [('linea_id', 'in', ids)], context=context)
        estructura_obj.unlink(cr, uid, estructura_ids, context=context)
        return super(presupuesto_linea, self).unlink(cr, uid, ids, context=context)

    def create(self, cr, uid, vals, context=None):
        linea_id = super(presupuesto_linea, self).create(cr, uid, vals, context=context)
        linea = self.browse(cr, uid, linea_id, context=context)
        if linea_id is not False:
            valores={}
            valores['linea_id']= linea_id
            valores['afectado']=0
            valores['comprometido']=0
            valores['obligado']=0
            valores['pagado']=0
            valores['porc_ejecutado']=0
            valores['disponible']=0
            valores['linea_programa']=vals['programa']
            valores['linea_proyecto']=vals['proyecto']
            valores['linea_moneda']=vals['moneda']
            valores['linea_tc']=vals['tipo_credito']
            valores['linea_ff']=vals['financiamiento']
            valores['linea_proy_inciso']=linea.budget_inciso
            valores['linea_ue']=vals['ue']
            valores['linea_og']=vals['objeto_gasto']
            valores['linea_aux']=vals['auxiliar']
            valores['linea_inicial']=vals['monto']
            valores['linea_ajuste']=vals['ajuste']
            valores['linea_planificado']= vals['ajuste'] + vals['monto']
            estructura_obj = self.pool.get('presupuesto.estructura')
            estructura_id = estructura_obj.create(cr, uid, valores, context=context)
        return linea_id

    def write(self, cr, uid, ids, values, context=None):
        valores={}
        if 'programa' in values:
           valores['linea_programa']=values['programa']
        if 'proyecto' in values:
           valores['linea_proyecto']=values['proyecto']
        if 'moneda' in values:
           valores['linea_moneda']=values['moneda']
        if 'tipo_credito' in values:
           valores['linea_tc']=values['tipo_credito']
        if 'financiamiento' in values:
           valores['linea_ff']=values['financiamiento']
        if 'budget_inciso' in values:
           valores['linea_proy_inciso']=values['budget_inciso']
        if 'ue' in values:
           valores['linea_ue']=values['ue']
        if 'objeto_gasto' in values:
           valores['linea_og']=values['objeto_gasto']
        if 'auxiliar' in values:
           valores['linea_aux']=values['auxiliar']
        if 'monto' in values:
           valores['linea_inicial']=values['monto']
        if 'ajuste' in values:
           valores['linea_ajuste']=values['ajuste']
        estructura_obj= self.pool.get('presupuesto.estructura')
        estructura_ids= estructura_obj.search(cr, uid, [('linea_id', 'in', ids)], context=context)
        estructura_obj.write(cr, uid, estructura_ids, valores, context=context)

        return super(presupuesto_linea, self).write(cr, uid, ids, values, context=context)

presupuesto_linea()
