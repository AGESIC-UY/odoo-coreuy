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
from openerp.tools.translate import _
from openerp.osv import osv, fields

_logger = logging.getLogger(__name__)

# TODO: SPRING 8 GAP 236.237 M
class wiz_modificacion_regularizacion_siif(osv.osv_memory):
    _name = 'wiz.modificacion_regularizacion_siif'
    _description = "Wizard modificacion de regularizacion clearing SIIF"
    _columns = {
        'regularizacion_id': fields.integer('regularizacion id', invisible=False),
        'tipo': fields.selection(
            (('A', 'A - Aumento'),
             ('R', u'R - Reducción')),
             # ('C', u'C - Corrección'),
             # ('N', u'N - Anulación'),
             # ('D', u'D - Devolución')),
            'Tipo', required=True),
        'fecha': fields.date('Fecha', required=True),
        'importe': fields.integer('Importe', required=True),
        'motivo': fields.char('Motivo', required=True),
        'financiamiento': fields.related('fin_id', 'ff', type='char', string='Fin related', store=True, readonly=True),
        'programa': fields.related('programa_id', 'programa', type='char', string='Programa related', store=True, readonly=True),
        'proyecto': fields.related('proyecto_id', 'proyecto', type='char', string='Proyecto related', store=True, readonly=True),
        'objeto_gasto': fields.related('odg_id', 'odg', type='char', string='ODG related', store=True, readonly=True),
        'auxiliar': fields.related('auxiliar_id', 'aux', type='char', string='Auxiliar related', store=True, readonly=True),
        'moneda': fields.related('mon_id', 'moneda', type='char', string='Mon related', store=True, readonly=True),
        'tipo_credito': fields.related('tc_id', 'tc', type='char', string='TC related', store=True, readonly=True),
        'ue_id': fields.many2one('grp.estruc_pres.ue', 'Unidad ejecutora'),
        'fin_id': fields.many2one ('grp.estruc_pres.ff', 'Fin', required=True),
        'programa_id': fields.many2one ('grp.estruc_pres.programa', 'Programa', required=True),
        'proyecto_id': fields.many2one ('grp.estruc_pres.proyecto', 'Proyecto', required=True),
        'odg_id': fields.many2one ('grp.estruc_pres.odg', 'ODG', required=True),
        'auxiliar_id': fields.many2one ('grp.estruc_pres.aux', 'Auxiliar', required=True),
        'mon_id': fields.many2one ('grp.estruc_pres.moneda', 'Mon', required=True),
        'tc_id': fields.many2one ('grp.estruc_pres.tc', 'TC', required=True),}

    _defaults = {
        'fecha': fields.date.context_today,
    }

    #Consumir SIIF aca
    def send_modif(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        regularizacion_obj = self.pool.get("regularizacion.clearing")

        ctx = dict(context)
        ctx.update({
            'es_modif': True,
            'regularizacion_id': data['regularizacion_id'],
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
        })
        raise Warning(_('Integración con SIIF'))
        # return regularizacion_obj.enviar_modificacion_siif(cr, uid, id=data['regularizacion_id'], context=ctx)

wiz_modificacion_regularizacion_siif()

class ws_modif_regularizacion_siif_log(osv.osv):
    _name = 'wiz.modif_regularizacion_siif_log'
    _description = "Log de modificaciones de regularizacion SIIF"
    _columns = {
        'regularizacion_id': fields.many2one('regularizacion.clearing', 'regularizacion clearing', required=True),
        'tipo': fields.selection(
            (('A', 'A - Aumento'),
             ('R', u'R - Reducción'),
             # ('C', u'C - Corrección'),
             ('N', u'N - Anulación')),
             # ('D', u'D - Devolución')),
             'Tipo'),
        'fecha': fields.date('Fecha', required=True),
        'importe': fields.float('Importe', required=True),
        'programa': fields.char('Programa', size=3, required=True),
        'proyecto': fields.char('Proyecto', size=3, required=True),
        'moneda': fields.char('MON', size=2, required=True),
        'tipo_credito': fields.char('TC', size=1, required=True),
        'financiamiento': fields.char('FF', size=2, required=True),
        'objeto_gasto': fields.char('ODG', size=3, required=True),
        'auxiliar': fields.char('AUX', size=3, required=True),
        'siif_sec_obligacion': fields.char(u'Secuencial obligación'),
        'siif_ult_modif': fields.integer(u'Última modificación'),
    }
ws_modif_regularizacion_siif_log()

class regularizacion_clearing_ext(osv.osv):
    _inherit = 'regularizacion.clearing'

    _columns={
        'modif_regularizacion_log_ids': fields.one2many(
            'wiz.modif_regularizacion_siif_log',
            'regularizacion_id',
            'Log'),
    }

    def abrir_wizard_modif_obligacion_siif(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif', 'view_wizard_modif_regularizacion_siif')
        res_id = res and res[1] or False
        ue_id = self.browse(cr, uid, ids[0]).ue_siif_id.id or False

        ctx = dict(context)
        ctx.update({
            'default_regularizacion_id': ids[0],
            'default_ue_id': ue_id
        })
        return {
            'name': "Modificaciones",  # Name You want to display on wizard
            'view_mode': 'form',
            'view_id': res_id,
            'view_type': 'form',
            'res_model': 'wiz.modificacion_regularizacion_siif',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'modif_regularizacion_log_ids': False,
        })
        return super(regularizacion_clearing_ext, self).copy(cr, uid, id, default, context=context)

regularizacion_clearing_ext()



