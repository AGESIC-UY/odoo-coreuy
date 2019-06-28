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

import logging

from openerp.osv import fields, osv
from openerp import SUPERUSER_ID
_logger = logging.getLogger(__name__)


class wizard_integracion_pagas_totalmente(osv.osv_memory):
    _name = 'wizard.integracion.pagas.totalmente'
    _columns = {
        'anio_fiscal': fields.many2one('account.fiscalyear', 'Ejercicio fiscal', required=True),
        'inciso': fields.char('Inciso', required=True),
        'fecha_desde': fields.date('Fecha desde', required=True),
        'fecha_hasta': fields.date('Fecha hasta', required=True)
    }

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        res = []
        for emp in self.browse(cr, uid, ids, context=context):
            res.append((emp.id, emp.anio_fiscal.name + ' - ' + emp.inciso))
        return res

    def ejecutar_pagas_totalmente(self, cr, uid, ids, context=None):
        fact_p_obj = self.pool.get('grp.integracion.pagas_totalmente')
        data = self.read(cr, uid, ids, [], context=context)

        fecha_desde = data[0]['fecha_desde']
        fecha_hasta = data[0]['fecha_hasta']
        anio_fiscal = data[0]['anio_fiscal'][1]
        inciso = data[0]['inciso']

        fact_p_obj.actualizar_pagas_totalmente_aux(cr, SUPERUSER_ID, anio_fiscal, inciso, fecha_desde, fecha_hasta, context=context)

        return {
            'name': 'Facturas pagas totalmente',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'grp.integracion.pagas_totalmente',
            'type': 'ir.actions.act_window',
            'context': {},
            'domain': [('anio_fiscal','=',anio_fiscal),('inciso','=',inciso),('fecha_enviado','>=',fecha_desde),('fecha_enviado','<=',fecha_hasta)]
        }


    def ir_a_pagas_totalmente(self, cr, uid, ids, context=None):
        return {
            'name': 'Facturas pagas totalmente',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'grp.integracion.pagas_totalmente',
            'type': 'ir.actions.act_window',
            'context': {},
        }


wizard_integracion_pagas_totalmente()
