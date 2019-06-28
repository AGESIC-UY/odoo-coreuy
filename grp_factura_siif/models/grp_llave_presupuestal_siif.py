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
from openerp.tools.translate import _


# ================================================================
#    Líneas de llave presupuestal en documentos de:
# APG
# OC
# Factura (Factura comun, obligacion y 3en1)
# Afectacion
# Compromiso
# ================================================================

class grp_compras_lineas_llavep(osv.osv):
    _name = 'grp.compras.lineas.llavep'
    _description = 'Lineas de llave presupuestal'

    def _check_linea_llavep_programa(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.programa:
                if not llp.programa.isdigit():
                    return False
        return True

    def _check_linea_llavep_odg(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.odg:
                if not llp.odg.isdigit():
                    return False
        return True

    def _check_linea_llavep_auxiliar(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.auxiliar:
                if not llp.auxiliar.isdigit():
                    return False
        return True

    def _check_linea_llavep_disponible(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.disponible:
                if not llp.disponible.isdigit():
                    return False
        return True

    def _check_linea_llavep_proyecto(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.proyecto:
                if not llp.proyecto.isdigit():
                    return False
        return True

    def _check_linea_llavep_fin(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.fin:
                if not llp.fin.isdigit():
                    return False
        return True

    def _check_linea_llavep_mon(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.mon:
                if not llp.mon.isdigit():
                    return False
        return True

    def _check_linea_llavep_tc(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.tc:
                if not llp.tc.isdigit():
                    return False
        return True

    _columns = {
        #many2one relacionados a los documentos correspondientes
        'apg_id': fields.many2one('grp.compras.apg', u'Autorización para gastar', ondelete='cascade'),
        'order_id': fields.many2one('purchase.order', u'Orden de compra', ondelete='cascade'),
        'invoice_id': fields.many2one('account.invoice', u'Factura', ondelete='cascade'),
        'afectacion_id': fields.many2one('grp.afectacion', u'Afectación', ondelete='cascade'),
        'compromiso_id': fields.many2one('grp.compromiso', u'Compromiso', ondelete='cascade'),
        #Campos de la estructura
        'odg_id': fields.many2one('grp.estruc_pres.odg', 'ODG', required=True),
        'auxiliar_id': fields.many2one('grp.estruc_pres.aux', 'Auxiliar', required=True),
        'fin_id': fields.many2one('grp.estruc_pres.ff', 'Fin', required=False),
        'programa_id': fields.many2one('grp.estruc_pres.programa', 'Programa', required=False),
        'proyecto_id': fields.many2one('grp.estruc_pres.proyecto', 'Proyecto', required=False),
        'mon_id': fields.many2one('grp.estruc_pres.moneda', 'Mon', required=False),
        'tc_id': fields.many2one('grp.estruc_pres.tc', 'TC', required=False),
        # Campos related
        'odg': fields.related('odg_id', 'odg', type='char', string='ODG related', store=True, readonly=True),
        'auxiliar': fields.related('auxiliar_id', 'aux', type='char', string='Auxiliar related', store=True, readonly=True),
        'fin': fields.related('fin_id', 'ff', type='char', string='Fin related', store=True, readonly=True),
        'programa': fields.related('programa_id', 'programa', type='char', string='Programa related', store=True, readonly=True),
        'proyecto': fields.related('proyecto_id', 'proyecto', type='char', string='Proyecto related', store=True, readonly=True),
        'mon': fields.related('mon_id', 'moneda', type='char', string='Mon related', store=True, readonly=True),
        'tc': fields.related('tc_id', 'tc', type='char', string='TC related', store=True, readonly=True),
        #montos
        'disponible': fields.char('Disponible', size=3),  # de 8 a 3 #TODO: VER, CHAR Y DE 3?
        'importe': fields.integer('Importe'),

    }

    # 001 - On_change llaves presupuestal
    def onchange_objeto_del_gasto(self, cr, uid, ids, odg_id, context=None):
        auxiliar_id = False
        if odg_id:
            auxiliar_ids = self.pool.get('grp.estruc_pres.aux').search(cr, uid, [('odg_id', '=', odg_id)])
            if len(auxiliar_ids) == 1:
                auxiliar_id = auxiliar_ids[0]
        return {'value': {
            'auxiliar_id': auxiliar_id,
            'fin_id': False,
            'programa_id': False,
            'proyecto_id': False,
            'mon_id': False,
            'tc_id': False,
        }}

    def onchange_auxiliar(self, cr, uid, ids, auxiliar_id, context=None):
        fin_id = False
        if auxiliar_id:
            fin_ids = self.pool.get('grp.estruc_pres.ff').search(cr, uid, [('aux_id', '=', auxiliar_id)])
            if len(fin_ids) == 1:
                fin_id = fin_ids[0]
        return {'value': {
            'fin_id': fin_id,
            'programa_id': False,
            'proyecto_id': False,
            'mon_id': False,
            'tc_id': False
        }}

    def onchange_fuente_de_financiamiento(self, cr, uid, ids, fin_id, context=None):
        programa_id = False
        if fin_id:
            programa_ids = self.pool.get('grp.estruc_pres.programa').search(cr, uid, [('ff_id', '=', fin_id)])
            if len(programa_ids) == 1:
                programa_id = programa_ids[0]
        return {'value': {
            'programa_id': programa_id,
            'proyecto_id': False,
            'mon_id': False,
            'tc_id': False,
        }}

    def onchange_programa(self, cr, uid, ids, programa_id, context=None):
        proyecto_id = False
        if programa_id:
            proyecto_ids = self.pool.get('grp.estruc_pres.proyecto').search(cr, uid,[('programa_id', '=', programa_id)])
            if len(proyecto_ids) == 1:
                proyecto_id = proyecto_ids[0]
        return {'value': {
            'proyecto_id': proyecto_id,
            'mon_id': False,
            'tc_id': False,
        }}

    def onchange_proyecto(self, cr, uid, ids, proyecto_id, context=None):
        mon_id = False
        if proyecto_id:
            mon_ids = self.pool.get('grp.estruc_pres.moneda').search(cr, uid, [('proyecto_id', '=', proyecto_id)])
            if len(mon_ids) == 1:
                mon_id = mon_ids[0]
        return {'value': {
            'mon_id': mon_id,
            'tc_id': False,
        }}

    def onchange_moneda(self, cr, uid, ids, mon_id, context=None):
        tc_id = False
        if mon_id:
            tc_ids = self.pool.get('grp.estruc_pres.tc').search(cr, uid, [('moneda_id', '=', mon_id)])
            if len(tc_ids) == 1:
                tc_id = tc_ids[0]
        return {'value': {
            'tc_id': tc_id
        }}

    def _check_llavep_unica(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            lineas_duplicadas = self.search(cr, uid, [('afectacion_id', '=', line.afectacion_id.id),
                                                      ('apg_id', '=', line.apg_id.id),
                                                      ('auxiliar_id', '=', line.auxiliar_id.id),
                                                      ('compromiso_id', '=', line.compromiso_id.id),
                                                      ('fin_id', '=', line.fin_id.id),
                                                      ('invoice_id', '=', line.invoice_id.id),
                                                      ('mon_id', '=', line.mon_id.id),
                                                      ('odg_id', '=', line.odg_id.id),
                                                      ('order_id', '=', line.order_id.id),
                                                      ('programa_id', '=', line.programa_id.id),
                                                      ('proyecto_id', '=', line.proyecto_id.id),
                                                      ('tc_id', '=', line.tc_id.id),
                                                      ('id', 'not in', ids)
                                                      ], context=context)
            if lineas_duplicadas:
                raise osv.except_osv(
                    _(u'Línea duplicada'),
                    _(u'No se pueden ingresar 2 líneas iguales para el mismo registro.'))
        return True


    _constraints = [
        (_check_llavep_unica, u'Línea duplicada',
         ['afectacion_id', 'apg_id', 'auxiliar_id', 'compromiso_id', 'fin_id', 'invoice_id', 'mon_id', 'odg_id',
          'order_id', 'programa_id', 'proyecto_id', 'tc_id']),
        (_check_linea_llavep_programa, u'Campo no es numérico', ['programa']),
        (_check_linea_llavep_odg, u'Campo no es numérico', ['odg']),
        (_check_linea_llavep_auxiliar, u'Campo no es numérico', ['auxiliar']),
        (_check_linea_llavep_disponible, u'Campo no es numérico', ['disponible']),
        (_check_linea_llavep_proyecto, u'Campo no es numérico', ['proyecto']),
        (_check_linea_llavep_fin, u'Campo no es numérico', ['fin']),
        (_check_linea_llavep_mon, u'Campo no es numérico', ['mon']),
        (_check_linea_llavep_tc, u'Campo no es numérico', ['tc']),
    ]


grp_compras_lineas_llavep()
