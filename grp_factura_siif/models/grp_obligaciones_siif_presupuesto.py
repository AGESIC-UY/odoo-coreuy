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

_logger = logging.getLogger(__name__)


class grp_obligaciones_siif_presupuesto(osv.osv):
    _name = 'grp.obligaciones.siif.presupuesto'

    _columns = {
        'anio': fields.integer(u'Año fiscal', readonly=True),
        'inciso': fields.integer('Inciso', readonly=True),
        'unidad_ejecutora': fields.integer('Unidad ejecutora', readonly=True),
        'nro_doc_afectacion': fields.integer(u'Número doc. afectación', readonly=True),
        'nro_doc_compromiso': fields.integer(u'Número doc. compromiso', readonly=True),
        'nro_doc_obligacion': fields.integer(u'Número doc. obligación', readonly=True),
        'sec_obligacion': fields.integer(u'Sec. obligación', readonly=True),
        'tipo_de_modificacion': fields.char(u'Tipo de modificación', readonly=True),
        'tipo_de_ejecucion': fields.char(u'Tipo de ejecución', readonly=True),
        'tipo_doc_respaldo': fields.integer('Tipo de documento de respaldo', readonly=True),
        'tipo_programa': fields.char('Tipo de programa', readonly=True),
        'documento_respaldo': fields.char('Documento de respaldo', readonly=True),
        'fecha_doc_respaldo': fields.date('Fecha de documento de respaldo', readonly=True),
        'factura_fecha_recepcion': fields.date(u'Fecha de recepción de factura', readonly=True),
        'resumen': fields.char('Resumen', readonly=True),
        'codigo_sir': fields.char(u'Código sir', readonly=True),
        'monto_obligacion': fields.float(u'Monto obligación', readonly=True),
        'monto_retenciones': fields.float('Monto retenciones', readonly=True),
        'liquido_a_pagar': fields.float('Liquido a pagar', readonly=True),
        'clase_id': fields.char('Identificador de clase', readonly=True),
        'ruc': fields.char('Ruc', readonly=True),
        'banco': fields.integer('Banco', readonly=True),
        'agencia': fields.integer('Agencia', readonly=True),
        'cta_corriente': fields.char('Cuenta corriente', readonly=True),
        'tipo_cuenta': fields.char('Tipo de cuenta', readonly=True),
        'moneda_cuenta': fields.integer('Moneda de cuenta', readonly=True),
        'estado_obligacion': fields.char(u'Estado de la obligación', readonly=True),
        'proceso_general_obl': fields.char('Proceso general obl', readonly=True),
        'programa': fields.integer(u'Programa', readonly=True),
        'proyecto': fields.integer(u'Proyecto', readonly=True),
        'objeto_gasto': fields.integer(u'Objeto del gasto', readonly=True),
        'auxiliar': fields.integer(u'Auxiliar', readonly=True),
        'financiamiento': fields.integer('Financiamiento', readonly=True),
        'moneda': fields.integer('Moneda', readonly=True),
        'tipo_credito': fields.integer(u'Tipo de crédito', readonly=True),
        'monto': fields.float(u'Monto', readonly=True),
        'grupo': fields.integer('Grupo', readonly=True),
        'acreedor_por_retencion': fields.integer(u'Acreedor por retención', readonly=True),
        'monto_retencion': fields.float(u'Monto retención', readonly=True),
        'tipo_impuesto': fields.integer('Tipo de impuesto', readonly=True),
        'monto_calculo': fields.float(u'Monto cálculo', readonly=True),
        'state': fields.selection((('pendant', 'Sin procesar'), ('processed', 'Procesado'), ('error', 'Error')), 'Estado', readonly=True),
        'texto_error': fields.char('Texto del error', readonly=True),
        'timestamp': fields.datetime(u'Fecha de creación', readonly=True),
        'factura_grp_id': fields.many2one('account.invoice', '3en1', readonly=True),
    }

class grp_log_obligaciones_siif_presupuesto(osv.osv):
    _name = 'grp.log.obligaciones.siif.presupuesto'

    _columns = {
        'timestamp': fields.datetime(u'Fecha de ejecución', readonly=True),
        'tipo_proceso': fields.selection((('carga', 'Carga Staging'), ('proceso', 'Proceso Staging')), 'Tipo de proceso', readonly=True),
        'fecha_proceso_carga': fields.datetime(u'Fecha de proceso de carga', readonly=True),
        'registros_procesados': fields.integer('Registros procesados', readonly=True),
        'errores': fields.boolean('Errores', default=True),
        'texto': fields.char('Texto informativo', readonly=True),
    }

