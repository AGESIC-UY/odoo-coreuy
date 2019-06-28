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

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.exceptions import except_orm, Warning

_logger = logging.getLogger(__name__)


class wiz_modificacion_cot_compromiso_siif(osv.osv_memory):
    _name = 'wiz.modificacion_cot_compromiso_siif'
    _description = u"Wizard modificación de compromiso SIIF"
    _columns = {
        'cot_compromiso_id': fields.integer('Cot compromiso id'),
        'tipo': fields.selection(
            (('A', u'A - Aumento'),
             ('R', u'R - Reducción')),
             # ('C', u'C - Corrección'),
             # ('N', u'N - Anulación'),
             # ('D', u'D - Devolución')),
            'Tipo', required=True),
        'fecha': fields.date('Fecha', required=True),
        'ue_id': fields.many2one('grp.estruc_pres.ue', 'Unidad ejecutora'),
        'odg_id': fields.many2one('grp.estruc_pres.odg', 'ODG', required=True),
        'auxiliar_id': fields.many2one('grp.estruc_pres.aux', 'Auxiliar', required=True),
        'fin_id': fields.many2one('grp.estruc_pres.ff', 'Fin', required=True),
        'programa_id': fields.many2one('grp.estruc_pres.programa', 'Programa', required=True),
        'proyecto_id': fields.many2one('grp.estruc_pres.proyecto', 'Proyecto', required=True),
        'mon_id': fields.many2one('grp.estruc_pres.moneda', 'Mon', required=True),
        'tc_id': fields.many2one('grp.estruc_pres.tc', 'TC', required=True),

        'importe': fields.integer('Importe', required=True),
        'motivo': fields.char('Motivo', required=True),

        'financiamiento': fields.related('fin_id', 'ff', type='char', string='Fin related', store=True, readonly=True),
        'programa': fields.related('programa_id', 'programa', type='char', string='Programa related', store=True,
                                   readonly=True),
        'proyecto': fields.related('proyecto_id', 'proyecto', type='char', string='Proyecto related', store=True,
                                   readonly=True),
        'objeto_gasto': fields.related('odg_id', 'odg', type='char', string='ODG related', store=True, readonly=True),
        'auxiliar': fields.related('auxiliar_id', 'aux', type='char', string='Auxiliar related', store=True,
                                   readonly=True),
        'moneda': fields.related('mon_id', 'moneda', type='char', string='Mon related', store=True, readonly=True),
        'tipo_credito': fields.related('tc_id', 'tc', type='char', string='TC related', store=True, readonly=True),
    }

    _defaults = {
        'fecha': fields.date.context_today,
    }

    #Consumir SIIF aca
    def send_modif(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        cot_compromiso_obj = self.pool.get("grp.cotizaciones.compromiso.proveedor")

        ctx = dict(context)
        ctx.update({
            'es_modif': True,
            'cot_compromiso_id': data['cot_compromiso_id'],
            'tipo_modificacion': data['tipo'],
            'fecha': data['fecha'],
            'programa': data['programa'],
            'proyecto': data['proyecto'],
            'moneda': data['moneda'],
            'tipo_credito': data['tipo_credito'],
            'financiamiento': data['financiamiento'],
            'objeto_gasto': data['objeto_gasto'],
            'auxiliar': data['auxiliar'],
            'importe': data['importe'] if data['tipo']=='A' else data['importe']*-1,
            'motivo': data['motivo'],
            'auxiliar_id': data['auxiliar_id'][0],
            'fin_id': data['fin_id'][0],
            'mon_id': data['mon_id'][0],
            'odg_id': data['odg_id'][0],
            'programa_id': data['programa_id'][0],
            'proyecto_id': data['proyecto_id'][0],
            'tc_id': data['tc_id'][0],
        })

        return cot_compromiso_obj.enviar_modificacion_siif(cr, uid, id=data['cot_compromiso_id'], context=ctx)





