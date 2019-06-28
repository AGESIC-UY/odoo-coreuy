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
from openerp import tools


class TIPO_DOCUMENTO:
    DESCONOCIDO = 0
    APG = 1
    TRES_EN_UNO = 2
    ORDEN_COMPRA = 3
    FACTURA = 4
    AFECTACION = 5
    COMPROMISO = 6
    OBLIGACION = 7
    TRES_EN_UNO_FR = 8
    TRES_EN_UNO_RC = 9

_logger = logging.getLogger(__name__)

class presupuesto_estructura(osv.osv):
    _name = 'presupuesto.estructura'
    _description = 'Estructura presupuesto'

    def get_disponible(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = record.linea_planificado - record.afectado
        return res

    def get_porc_ejec(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            if record.linea_planificado > 0:
                res[record.id] = (record.obligado / record.linea_planificado) * 100
            else:
                res[record.id] = 0
        return res

    _columns = {
        'linea_id': fields.many2one('presupuesto.linea', 'linea id'),
        'linea_proy_fiscal_year': fields.related('linea_id', 'budget_fiscal_year', string='Año fiscal', type='many2one',
                                                 relation='account.fiscalyear', readonly=True,store=True),
        'linea_programa': fields.char('Progr.', size=3, readonly=True),
        'linea_proyecto': fields.char('Proy.', size=3, readonly=True),
        'linea_moneda': fields.char('MON', size=2, readonly=True),
        'linea_tc': fields.char('TC', size=1, readonly=True),
        'linea_ff': fields.char('FF', size=3, readonly=True),
        'linea_proy_inciso': fields.char('Inciso', size=3, readonly=True),
        'linea_ue': fields.char('UE', size=3, readonly=True),
        'linea_og': fields.char('ODG', size=3, readonly=True),
        'linea_aux': fields.char('AUX', size=3, readonly=True),
        'linea_inicial': fields.float('Inicial', readonly=True),
        'linea_ajuste': fields.float('Ajustes', readonly=True),
        'linea_planificado': fields.float('Vigente', readonly=True),
        'afectado': fields.float('Afectado', readonly=True),
        'comprometido': fields.float('Comprometido', readonly=True),
        'obligado': fields.float('Obligado', readonly=True),
        'pagado': fields.float('Pagado', readonly=True),
        'porc_ejecutado': fields.function(get_porc_ejec, method=True, string='%Ejec.', type='integer'),
        'disponible': fields.function(get_disponible, method=True, string='Disponible', type='float'),
        'log': fields.one2many('presupuesto.estructura.linealog', 'id_estructura', 'Ver historial')
    }

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            # name = '%s - %s - %s' % (record.linea_proy_fiscal_year, record.linea_proy_inciso, record.linea_version_ue)
            name = 'Formulario de estructura'
            res.append((record.id, name))
        return res

    def crear_estructura(self, uid, cr, objeto_presupuesto, auxiliar, financiamiento, importe, moneda, odg, programa, proyecto, tipo_credito, unidad_ejecutora):
        # Si existe la estructura con todos los parametros, no hace nada
        estructura = self.obtener_estructura(cr, uid, objeto_presupuesto.anio_fiscal, objeto_presupuesto.inciso,
                                             unidad_ejecutora, programa, proyecto, moneda, tipo_credito, financiamiento,
                                             odg, auxiliar)
        if estructura is not None:
            return True

        # Obtengo presupuesto según inciso (en caso que no exista presupuesto, lo creo)
        # presupuesto_obj = self.pool.get('presupuesto.presupuesto')
        # presupuesto_obj.create()

        # A partir del presupuesto anterior y la UE, busco la version (en caso que no exista la version, la creo)
        # A partir de la version anterior y la llave presupuestal, obtengo la linea (en caso que no exista la estructura, la creo)
        # Al crear la linea, automaticamente se crea la estructura
        # Que hacer en caso que exista la linea? nada? los montos disponibles no vienen en el ws
        pass

    def obtener_estructura(self, cr, uid,  anio_fiscal, inciso, unidad_ejecutora, programa, proyecto, moneda, tipo_credito, financiamiento, objeto_gasto, auxiliar):
        estructura_obj = self.pool.get('presupuesto.estructura')
        filters = []
        filters.append(('linea_proy_fiscal_year', '=', anio_fiscal))
        filters.append(('linea_proy_inciso', '=', inciso))
        filters.append(('linea_ue', '=', unidad_ejecutora))
        filters.append(('linea_programa', '=', programa))
        filters.append(('linea_proyecto', '=', proyecto))
        filters.append(('linea_moneda', '=', moneda))
        filters.append(('linea_tc', '=', tipo_credito))
        filters.append(('linea_ff', '=', financiamiento))
        filters.append(('linea_og', '=', objeto_gasto))
        filters.append(('linea_aux', '=', auxiliar))

        estructura_ids = estructura_obj.search(cr, uid, filters, offset=0, limit=None, order=None, context=None, count=False)
        if len(estructura_ids) > 0:
            estructura = estructura_obj.browse(cr, uid, estructura_ids[0], context=None)
            return estructura
        else:
            fiscalyear_obj = self.pool.get('account.fiscalyear')
            fislcalyear = fiscalyear_obj.browse(cr, uid, anio_fiscal)
            desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                         (fislcalyear.name, inciso, unidad_ejecutora, objeto_gasto, auxiliar, financiamiento, programa,
                          proyecto, moneda, tipo_credito)
            raise osv.except_osv(('Error'), (u'No se encontró estructura con la llave presupuestal asociada: ' + desc_error))

    def afectar(self, cr, uid, id_documento, tipo_documento, monto, estructura):
        estructura_obj = self.pool.get('presupuesto.estructura')
        res = {}
        res['codigo'] = 1
        res['mensaje'] = 'OK'

        vals = {}
        document_ok = False
        if tipo_documento == TIPO_DOCUMENTO.APG:
            tipo_documento_text = 'APG'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.AFECTACION:
            tipo_documento_text = 'AFECTACION'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.TRES_EN_UNO:
            tipo_documento_text = '3EN1'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.TRES_EN_UNO_FR:
            tipo_documento_text = '3EN1_FR'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.TRES_EN_UNO_RC:
            tipo_documento_text = '3EN1_RC'
            document_ok = True

        if document_ok is False:
            res['codigo'] = 3
            res['mensaje'] = u'Tipo de documento no reconocido para la afectación.'
            return res

        vals['afectado'] = estructura.afectado + monto
        write_result = estructura_obj.write(cr, uid, estructura.id, vals, context=None)
        log_result = self._loguear(cr, uid, estructura.id, id_documento, tipo_documento_text, monto_afectado=monto)
        if write_result is False:
            res['codigo'] = 4
            res['mensaje'] = u'No fue posible realizar la modificación.'
            return res
        if log_result is False:
            res['codigo'] = 5
            res['mensaje'] = u'No fue posible ingresar una línea al log.'
            return res

        return res

    def comprometer(self, cr, uid, id_documento, tipo_documento, monto, estructura):
        res = {}
        estructura_obj = self.pool.get('presupuesto.estructura')
        vals = {}
        document_ok = False
        if tipo_documento == TIPO_DOCUMENTO.ORDEN_COMPRA:
            tipo_documento_text = 'ORDEN_DE_COMPRA'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.COMPROMISO:
            tipo_documento_text = 'COMPROMISO'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.TRES_EN_UNO:
            tipo_documento_text = '3EN1'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.TRES_EN_UNO_FR:
            tipo_documento_text = '3EN1_FR'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.TRES_EN_UNO_RC:
            tipo_documento_text = '3EN1_RC'
            document_ok = True

        if document_ok is False:
            res['codigo'] = 3
            res['mensaje'] = 'Tipo de documento no reconocido para el compromiso.'
            return res

        vals['comprometido'] = estructura.comprometido + monto
        write_result = estructura_obj.write(cr, uid, estructura.id, vals, context=None)
        log_result = self._loguear(cr, uid, estructura.id, id_documento, tipo_documento_text,
                                   monto_comprometido=monto)
        if write_result is False:
            res['codigo'] = 4
            res['mensaje'] = 'No fue posible realizar la modificación.'
            return res
        if log_result is False:
            res['codigo'] = 5
            res['mensaje'] = 'No fue posible ingresar una línea al log.'
            return res

        res['codigo'] = 1
        res['mensaje'] = 'OK'
        return res

    def obligar(self, cr, uid, id_documento, tipo_documento, monto, estructura):
        res = {}
        estructura_obj = self.pool.get('presupuesto.estructura')
        vals = {}
        document_ok = False
        if tipo_documento == TIPO_DOCUMENTO.OBLIGACION:
            tipo_documento_text = 'OBLIGACION'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.FACTURA:
            tipo_documento_text = 'FACTURA'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.TRES_EN_UNO:
            tipo_documento_text = '3EN1'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.TRES_EN_UNO_FR:
            tipo_documento_text = '3EN1_FR'
            document_ok = True
        elif tipo_documento == TIPO_DOCUMENTO.TRES_EN_UNO_RC:
            tipo_documento_text = '3EN1_RC'
            document_ok = True

        if document_ok is False:
            res['codigo'] = 3
            res['mensaje'] = 'Tipo de documento no reconocido para la afectación.'
            return res

        vals['obligado'] = estructura.obligado + monto
        write_result = estructura_obj.write(cr, uid, estructura.id, vals, context=None)
        log_result = self._loguear(cr, uid, estructura.id, id_documento, tipo_documento_text,
                                   monto_obligado=monto)
        if write_result is False:
            res['codigo'] = 4
            res['mensaje'] = 'No fue posible realizar la modificación.'
            return res
        if log_result is False:
            res['codigo'] = 5
            res['mensaje'] = 'No fue posible ingresar una línea al log.'
            return res

        res['codigo'] = 1
        res['mensaje'] = 'OK'
        return res

    def _loguear(self, cr, uid, id_estructura, id_documento, tipo_documento, monto_afectado=None, monto_obligado=None,
                 monto_comprometido=None, monto_pagado=None):
        valores_log = {}
        valores_log['id_estructura'] = id_estructura
        valores_log['id_objeto'] = id_documento
        valores_log['tipo_objeto'] = tipo_documento
        if monto_afectado:
            valores_log['monto_afectado'] = monto_afectado
        if monto_obligado:
            valores_log['monto_obligado'] = monto_obligado
        if monto_comprometido:
            valores_log['monto_comprometido'] = monto_comprometido
        if monto_pagado:
            valores_log['monto_pagado'] = monto_pagado
        log_obj = self.pool.get('presupuesto.estructura.linealog')
        id_log = log_obj.create(cr, uid, valores_log, context=None)
        return id_log

    def obtener_tipo_control(self, cr, uid, estructura):
        presupuesto_id = estructura.linea_id.budget_id.id
        cr.execute('select id, tipo_control, presupuesto_id from presupuesto_config where create_date=(select max(create_date) from presupuesto_config where presupuesto_id=%s)',
                   (presupuesto_id,))
        conf = cr.fetchone()
        if conf is None:
            return None
        tipo_control = conf[0]['tipo_control']
        return tipo_control

    def unlink(self, cr, uid, ids, context=None):
        log_obj = self.pool.get('presupuesto.estructura.linealog')
        log_ids = log_obj.search(cr, uid, [('id_estructura', 'in', ids)], context=context)
        log_obj.unlink(cr, uid, log_ids, context=context)
        return super(presupuesto_estructura, self).unlink(cr, uid, ids, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if not isinstance(ids, list):
            ids = [ids, ]
        estructura_obj = self.pool.get('presupuesto.estructura')
        estructura_list = estructura_obj.browse(cr, uid, ids)
        if len(estructura_list) > 0:
            estructura = estructura_list[0]
            if 'linea_ajuste' in values and 'linea_inicial' in values:
                values['linea_planificado'] = values['linea_ajuste'] + values['linea_inicial']
            else:
                if 'linea_inicial' in values:
                    values['linea_planificado'] = estructura.linea_ajuste + values['linea_inicial']
                if 'linea_ajuste' in values:
                    values['linea_planificado'] = estructura.linea_inicial + values['linea_ajuste']
        return super(presupuesto_estructura, self).write(cr, uid, ids, values, context=context)

presupuesto_estructura()

class presupuesto_estructura_linealog(osv.osv):
    _name = 'presupuesto.estructura.linealog'
    _columns = {
        'create_date': fields.datetime('Fecha/Hora'),
        'id_estructura': fields.many2one('presupuesto.estructura', 'id_estructura'),
        'id_objeto': fields.integer('Documento'),
        'tipo_objeto': fields.char('Tipo documento', size=20),
        'monto_afectado': fields.integer('Afectado'),
        'monto_obligado': fields.integer('Obligado'),
        'monto_comprometido': fields.integer('Comprometido'),
        'monto_pagado': fields.integer('Pagado')
    }

class grp_presupuesto_inciso_sql(osv.osv):
    _name = 'grp.presupuesto.inciso_sql'
    _description = 'Vista sql inciso'
    _auto= False

    _columns = {
        'linea_proy_fiscal_year': fields.related('linea_id', 'budget_fiscal_year', string=u'Año fiscal',
                                                 type='many2one',relation='account.fiscalyear', readonly=True),
        'linea_proy_inciso': fields.char('Inciso', size=3, readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr,'grp_presupuesto_inciso_sql')
        cr.execute("""
            CREATE OR REPLACE VIEW grp_presupuesto_inciso_sql AS (
            SELECT DISTINCT row_number() over() as id,  
                   pe.linea_proy_fiscal_year as linea_proy_fiscal_year, 
                   pe.linea_proy_inciso as linea_proy_inciso
            FROM presupuesto_estructura pe
            GROUP BY pe.linea_proy_fiscal_year, pe.linea_proy_inciso
            )
          """)

grp_presupuesto_inciso_sql()

class grp_presupuesto_unidad_ejecutora(osv.osv):
    _name = 'grp.presupuesto.unidad_ejecutora'
    _description = 'Vista sql unidad ejecutora'
    _auto= False

    _columns = {
        'linea_proy_fiscal_year': fields.related('linea_id', 'budget_fiscal_year', string=u'Año fiscal',
                                                 type='many2one',relation='account.fiscalyear', readonly=True),
        'linea_proy_inciso': fields.char('Inciso', size=3, readonly=True),
        'linea_ue': fields.char('UE', size=3, readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr,'grp_presupuesto_unidad_ejecutora')
        cr.execute("""
            CREATE OR REPLACE VIEW grp_presupuesto_unidad_ejecutora AS (
            SELECT DISTINCT row_number() over() as id,  
                   pe.linea_proy_fiscal_year as linea_proy_fiscal_year, 
                   pe.linea_proy_inciso as linea_proy_inciso,
                   pe.linea_ue as linea_ue
            FROM presupuesto_estructura pe
            GROUP BY pe.linea_proy_fiscal_year, pe.linea_proy_inciso,pe.linea_ue
            )
          """)

grp_presupuesto_unidad_ejecutora()

class grp_presupuesto_financiamiento(osv.osv):
    _name = 'grp.presupuesto_financiamiento'
    _description = 'Vista sql financiamiento'
    _auto= False

    _columns = {
        'linea_proy_fiscal_year': fields.related('linea_id', 'budget_fiscal_year', string=u'Año fiscal',
                                                 type='many2one',relation='account.fiscalyear', readonly=True),
        'linea_proy_inciso': fields.char('Inciso', size=3, readonly=True),
        'linea_ue': fields.char('UE', size=3, readonly=True),
        'linea_ff': fields.char('FF', size=3, readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr,'grp_presupuesto_financiamiento')
        cr.execute("""
            CREATE OR REPLACE VIEW grp_presupuesto_financiamiento AS (
            SELECT DISTINCT row_number() over() as id, 
                   pe.linea_proy_fiscal_year as linea_proy_fiscal_year, 
                   pe.linea_proy_inciso as linea_proy_inciso,
                   pe.linea_ue as linea_ue,
                   pe.linea_ff as linea_ff
            FROM presupuesto_estructura pe
            GROUP BY pe.linea_proy_fiscal_year, pe.linea_proy_inciso, pe.linea_ue, pe.linea_ff
            )
          """)

grp_presupuesto_financiamiento()

class grp_presupuesto_programa(osv.osv):
    _name = 'grp.presupuesto_programa'
    _description = 'Vista sql programa'
    _auto= False

    _columns = {
        'linea_proy_fiscal_year': fields.related('linea_id', 'budget_fiscal_year', string=u'Año fiscal',
                                                 type='many2one',relation='account.fiscalyear', readonly=True),
        'linea_proy_inciso': fields.char('Inciso', size=3, readonly=True),
        'linea_ue': fields.char('UE', size=3, readonly=True),
        'linea_ff': fields.char('FF', size=3, readonly=True),
        'linea_programa': fields.char('Programa', size=3, readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr,'grp_presupuesto_programa')
        cr.execute("""
            CREATE OR REPLACE VIEW grp_presupuesto_programa AS (
            SELECT DISTINCT row_number() over() as id, 
                   pe.linea_proy_fiscal_year as linea_proy_fiscal_year, 
                   pe.linea_proy_inciso as linea_proy_inciso,
                   pe.linea_ue as linea_ue,
                   pe.linea_ff as linea_ff,
                   pe.linea_programa as linea_programa
            FROM presupuesto_estructura pe
            GROUP BY pe.linea_proy_fiscal_year, pe.linea_proy_inciso, pe.linea_ue, pe.linea_ff, pe.linea_programa
            )
          """)

grp_presupuesto_programa()

class grp_presupuesto_proyecto(osv.osv):
    _name = 'grp.presupuesto_proyecto'
    _description = 'Vista sql proyecto'
    _auto= False

    _columns = {
        'linea_proy_fiscal_year': fields.related('linea_id', 'budget_fiscal_year', string=u'Año fiscal',
                                                 type='many2one',relation='account.fiscalyear', readonly=True),
        'linea_proy_inciso': fields.char('Inciso', size=3, readonly=True),
        'linea_ue': fields.char('UE', size=3, readonly=True),
        'linea_ff': fields.char('FF', size=3, readonly=True),
        'linea_programa': fields.char('Programa', size=3, readonly=True),
        'linea_proyecto': fields.char('Proyecto', size=3, readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr,'grp_presupuesto_proyecto')
        cr.execute("""
            CREATE OR REPLACE VIEW grp_presupuesto_proyecto AS (
            SELECT DISTINCT row_number() over() as id, 
                   pe.linea_proy_fiscal_year as linea_proy_fiscal_year, 
                   pe.linea_proy_inciso as linea_proy_inciso,
                   pe.linea_ue as linea_ue,
                   pe.linea_ff as linea_ff,
                   pe.linea_programa as linea_programa,
                   pe.linea_proyecto as linea_proyecto
            FROM presupuesto_estructura pe
            GROUP BY pe.linea_proy_fiscal_year, pe.linea_proy_inciso, pe.linea_ue, pe.linea_ff, pe.linea_programa, pe.linea_proyecto
            )
          """)

grp_presupuesto_proyecto()

class grp_presupuesto_odg_sql(osv.osv):
    _name = 'grp.presupuesto_odg_sql'
    _description = 'Vista sql odg'
    _auto= False

    _columns = {
        'linea_proy_fiscal_year': fields.related('linea_id', 'budget_fiscal_year', string=u'Año fiscal',
                                                 type='many2one',relation='account.fiscalyear', readonly=True),
        'linea_proy_inciso': fields.char('Inciso', size=3, readonly=True),
        'linea_ue': fields.char('UE', size=3, readonly=True),
        'linea_ff': fields.char('FF', size=3, readonly=True),
        'linea_programa': fields.char('Programa', size=3, readonly=True),
        'linea_proyecto': fields.char('Proyecto', size=3, readonly=True),
        'linea_og': fields.char('OG', size=3, readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr,'grp_presupuesto_odg_sql')
        cr.execute("""
            CREATE OR REPLACE VIEW grp_presupuesto_odg_sql AS (
            SELECT DISTINCT row_number() over() as id, 
                   pe.linea_proy_fiscal_year, 
                   pe.linea_proy_inciso,
                   pe.linea_ue,
                   pe.linea_ff,
                   pe.linea_programa,
                   pe.linea_proyecto,
                   pe.linea_og
            FROM presupuesto_estructura pe
            GROUP BY pe.linea_proy_fiscal_year, pe.linea_proy_inciso, pe.linea_ue, pe.linea_ff, pe.linea_programa, pe.linea_proyecto, pe.linea_og
            )
          """)

grp_presupuesto_odg_sql()

class grp_presupuesto_auxiliar_sql(osv.osv):
    _name = 'grp.presupuesto_auxiliar_sql'
    _description = 'Vista sql auxiliar'
    _auto= False

    _columns = {
        'linea_proy_fiscal_year': fields.related('linea_id', 'budget_fiscal_year', string=u'Año fiscal',
                                                 type='many2one',relation='account.fiscalyear', readonly=True),
        'linea_proy_inciso': fields.char('Inciso', size=3, readonly=True),
        'linea_ue': fields.char('UE', size=3, readonly=True),
        'linea_ff': fields.char('FF', size=3, readonly=True),
        'linea_programa': fields.char('Programa', size=3, readonly=True),
        'linea_proyecto': fields.char('Proyecto', size=3, readonly=True),
        'linea_og': fields.char('OG', size=3, readonly=True),
        'linea_aux': fields.char('AUX', size=3, readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr,'grp_presupuesto_auxiliar_sql')
        cr.execute("""
            CREATE OR REPLACE VIEW grp_presupuesto_auxiliar_sql AS (
            SELECT DISTINCT row_number() over() as id, 
                   pe.linea_proy_fiscal_year as linea_proy_fiscal_year, 
                   pe.linea_proy_inciso as linea_proy_inciso,
                   pe.linea_ue as linea_ue,
                   pe.linea_ff as linea_ff,
                   pe.linea_programa as linea_programa,
                   pe.linea_proyecto as linea_proyecto,
                   pe.linea_og as linea_og,
                   pe.linea_aux as linea_aux
            FROM presupuesto_estructura pe
            GROUP BY pe.linea_proy_fiscal_year, pe.linea_proy_inciso, pe.linea_ue, pe.linea_ff, pe.linea_programa, pe.linea_proyecto, pe.linea_og, pe.linea_aux
            )
          """)

grp_presupuesto_auxiliar_sql()
