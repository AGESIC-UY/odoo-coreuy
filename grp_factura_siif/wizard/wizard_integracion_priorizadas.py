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

class wizard_integracion_priorizadas(osv.osv_memory):
    _name = 'wizard.integracion.priorizadas'
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


    def ejecutar_priorizadas(self, cr, uid, ids, context=None):
        fact_p_obj = self.pool.get('grp.integracion.priorizadas')
        data = self.read(cr, uid, ids, [], context=context)

        fecha_desde = data[0]['fecha_desde']
        fecha_hasta = data[0]['fecha_hasta']
        anio_fiscal = data[0]['anio_fiscal'][1]
        inciso = data[0]['inciso']

        fact_p_obj.actualizar_priorizadas(cr, SUPERUSER_ID, anio_fiscal, inciso, fecha_desde, fecha_hasta,
                                           context=context)

        return {
            'name': 'Facturas priorizadas',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'grp.integracion.priorizadas',
            # 'search_view_id': res_id,
            'type': 'ir.actions.act_window',  # 'priority':'1',
            'context': {},
            'domain': [('anio_fiscal', '=', anio_fiscal), ('inciso', '=', inciso),
                       ('fecha_aprobado_date', '>=', fecha_desde),
                       ('fecha_aprobado_date', '<=', fecha_hasta)]
        }

    def ir_a_priorizadas(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif', 'view_grp_integracion_priorizadas')
        res_id = res and res[1] or False
        return {
            'name': 'Facturas priorizadas',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'grp.integracion.priorizadas',
            'search_view_id': res_id,  # 'search_default_filter_pendants': 1,
            'type': 'ir.actions.act_window',
            'context': {'search_default_filter_pendants': 1},
        }

wizard_integracion_priorizadas()
