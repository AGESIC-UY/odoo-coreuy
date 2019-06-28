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
import datetime

LISTA_ROLES = [
    ('odg_p', 'Ordenador del Gasto Primario'),
    ('odg_s', 'Ordenador del Gasto Secundario'),
]

LISTA_TIPO_TRANS = [
    ('apg', u'Autorización para Gastar'),
    ('odc', u'Órden de compra')
]


## LINEAS DE GASTOS DE MONTOS DE APROBACIÓN - HIJO
class grp_linea_monto_aprob(osv.osv):
    _name = 'grp.linea.monto.aprob'
    _description = 'Lineas de monto de aprobacion'

    _columns = {
        'monto_aprob_id': fields.many2one('grp.monto.aprobacion', ondelete='cascade'),
        'desde': fields.float('Monto Desde'),
        'hasta': fields.float('Monto Hasta'),
        'rol_id': fields.selection(LISTA_ROLES, 'Rol', readonly=True),
        'tipo_trans': fields.selection(LISTA_TIPO_TRANS, u'Tipo de Transacción', readonly=True),
    }


grp_linea_monto_aprob()


##MONTO DE APROBACIÓN - PADRE
class grp_monto_aprobacion(osv.osv):
    _name = 'grp.monto.aprobacion'
    _description = 'Lineas de monto de aprobacion'

    def _get_fecha_inicio(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=context):
            res[lines.id] = datetime.date(lines.anio_vigencia, 1, 1).strftime("%Y-%m-%d %H:%M:%S")
        return res

    def _get_fecha_fin(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=context):
            res[lines.id] = datetime.date(lines.anio_vigencia, 12, 31).strftime("%Y-%m-%d %H:%M:%S")
        return res

    _columns = {
        'anio_vigencia': fields.selection(
            [(num, str(num)) for num in range((datetime.datetime.now().year) - 5, (datetime.datetime.now().year) + 5)],
            u'Año de Vigencia', required=True),
        'activo_aprob': fields.boolean('Activo', readonly=True),
        'fecha_inicio': fields.function(_get_fecha_inicio, type='date', string='Fecha Inicio', store=False),
        'fecha_fin': fields.function(_get_fecha_fin, type='date', string='Fecha Fin', store=False),
        'linea_ids': fields.one2many('grp.linea.monto.aprob', 'monto_aprob_id'),
    }

    def onchange_anio_vigencia(self, cr, uid, ids, anio_vigencia, context=None):
        value = {'fecha_inicio': '', 'fecha_fin': ''}
        if anio_vigencia:
            inicio = datetime.date(anio_vigencia, 1, 1).strftime("%Y-%m-%d %H:%M:%S")
            fin = datetime.date(anio_vigencia, 12, 31).strftime("%Y-%m-%d %H:%M:%S")
            value = {'fecha_inicio': inicio, 'fecha_fin': fin}
        return {'value': value}

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['fecha_inicio', 'fecha_fin'], context=context)
        res = []
        for record in reads:
            res.append((record['id'], str(record['fecha_inicio']) + u' - ' + unicode(record['fecha_fin'])))
        return res

    def button_activar(self, cr, uid, ids, context=None):
        if not ids:
            return False
        # ids siempre es una lista de un solo elemento (PC)
        activo = self.browse(cr, uid, ids, context=context)[0]
        a_inactivar = self.search(cr, uid, [('activo_aprob', '=', True), ('anio_vigencia', '=', activo.anio_vigencia)],
                                  context=context)
        for ain in a_inactivar:
            self.write(cr, uid, [ain], {'activo_aprob': False}, context=context)
        return self.write(cr, uid, ids, {'activo_aprob': True}, context=context)

    def _get_default_lines(self, cr, uid, context=None):
        lines = []
        for trans in LISTA_TIPO_TRANS:
            for rol in LISTA_ROLES:
                lines.append((0, 0, {
                    'rol_id': rol[0],
                    'tipo_trans': trans[0]
                }))
        return lines

    _defaults = {
        'fecha_inicio': datetime.date(datetime.date.today().year, 1, 1).strftime("%Y-%m-%d %H:%M:%S"),
        'fecha_fin': datetime.date(datetime.date.today().year, 12, 31).strftime("%Y-%m-%d %H:%M:%S"),
        'linea_ids': _get_default_lines,
        'anio_vigencia': datetime.datetime.now().year,
        'activo_aprob': False
    }

    """ TODO
    def write(self,cr,uid,ids,values,context=None):
        if values.get('activo_aprob',False)
            """


grp_monto_aprobacion()


## LINEAS DE GASTOS DE MONTOS DE APROBACIÓN
class grp_linea_monto_comp(osv.osv):
    _name = 'grp.linea.monto.compra'
    _description = u'Lienas de monto de compra'

    _columns = {
        'monto_compra_id': fields.many2one('grp.monto.compras'),
        'desde': fields.float('Monto Desde'),
        'hasta': fields.float('Monto Hasta'),
        'tipo_compra_id': fields.many2one('sicec.tipo.compra', 'Tipo de compra', required=True),
    }

    _sql_constraints = [('codigo_partida_unico', 'unique(monto_compra_id,tipo_compra_id)',
                         u'Líneas repetidas. Debe haber a lo sumo un registro por tipo de compra para cada periodo')]


grp_linea_monto_comp()


## MONTO DE COMPRAS
class grp_monto_compras(osv.osv):
    _name = 'grp.monto.compras'
    _description = 'Monto de compras'

    def _get_fecha_inicio(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=context):
            res[lines.id] = datetime.date(lines.anio_vigencia, 1, 1).strftime("%Y-%m-%d %H:%M:%S")
        return res

    def _get_fecha_fin(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=context):
            res[lines.id] = datetime.date(lines.anio_vigencia, 12, 31).strftime("%Y-%m-%d %H:%M:%S")
        return res

    _columns = {
        'anio_vigencia': fields.selection(
            [(num, str(num)) for num in range((datetime.datetime.now().year) - 5, (datetime.datetime.now().year) + 5)],
            u'Año de Vigencia', required=True),
        'fecha_inicio': fields.function(_get_fecha_inicio, type='date', string='Fecha Inicio', store=False),
        'fecha_fin': fields.function(_get_fecha_fin, type='date', string='Fecha Fin', store=False),
        'activo_compras': fields.boolean(u'Activo', readonly=True),
        'linea_ids': fields.one2many('grp.linea.monto.compra', 'monto_compra_id', u'Linea de monto'),
    }
    _defaults = {
        'fecha_inicio': datetime.date(datetime.date.today().year, 1, 1).strftime("%Y-%m-%d %H:%M:%S"),
        'fecha_fin': datetime.date(datetime.date.today().year, 12, 31).strftime("%Y-%m-%d %H:%M:%S"),
        'anio_vigencia': datetime.datetime.now().year,
        'activo_compras': False
    }

    def onchange_anio_vigencia(self, cr, uid, ids, anio_vigencia, context=None):
        value = {'fecha_inicio': '', 'fecha_fin': ''}
        if anio_vigencia:
            inicio = datetime.date(anio_vigencia, 1, 1).strftime("%Y-%m-%d %H:%M:%S")
            fin = datetime.date(anio_vigencia, 12, 31).strftime("%Y-%m-%d %H:%M:%S")
            value = {'fecha_inicio': inicio, 'fecha_fin': fin}
        return {'value': value}

    def button_activar(self, cr, uid, ids, context=None):
        if not ids:
            return False
        # ids siempre es una lista de un solo elemento (PC)
        activo = self.browse(cr, uid, ids, context=context)[0]
        a_inactivar = self.search(cr, uid,
                                  [('activo_compras', '=', True), ('anio_vigencia', '=', activo.anio_vigencia)],
                                  context=context)
        for ain in a_inactivar:
            self.write(cr, uid, [ain], {'activo_compras': False}, context=context)
        return self.write(cr, uid, ids, {'activo_compras': True}, context=context)


grp_monto_compras()
