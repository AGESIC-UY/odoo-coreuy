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
from openerp import netsvc
from openerp import SUPERUSER_ID
import time
import datetime
import logging
import sys, os
_logger = logging.getLogger(__name__)



def _generar_dictkey(lista_linea):
    clave = str(lista_linea.unidadEjecutora).zfill(3) + '|' + \
            str(lista_linea.programa).zfill(3) + '|' + \
            str(lista_linea.proyecto).zfill(3) + '|' + \
            str(lista_linea.moneda).zfill(1) + '|' + \
            str(lista_linea.tipoDeCredito).zfill(1) + '|' + \
            str(lista_linea.financiamiento).zfill(2) + '|' + \
            str(lista_linea.objetoDelGasto).zfill(3) + '|' + \
            str(lista_linea.auxiliar).zfill(3)
    return clave

class presupuesto_presupuesto(osv.osv):
    _name = "presupuesto.presupuesto"
    _description = "Presupuesto"
    _columns = {
        'name': fields.char('Nombre', size=200, required=True),
        'inciso': fields.char('Inciso', size=2, required=True),
        'fiscal_year': fields.many2one('account.fiscalyear', 'Año fiscal', required=True),
        'start_date': fields.date('Fecha de inicio', required=True),
        'end_date': fields.date('Fecha de fin', required=True),
        'active': fields.boolean('Activo'),
        'budget_line_ids': fields.one2many('presupuesto.linea',
                                           'budget_id',
                                           u'Líneas de presupuesto'),
        'note': fields.text('Notas'),
        'create_date': fields.datetime(u'Fecha de creación', readonly=True),
        'unidad_ejecutora_ids': fields.many2many('unidad.ejecutora','presupuesto_ue_rel','pres_id','ue_id', string=u"Unidades ejecutoras",
                                                 help="Si no quiere traer todas las Unidades ejecutoras, seleccione las que corresponden"),
    }

    _defaults = {
        'active': lambda *a: True,
        'inciso': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid,
                                                                             c).company_id.inciso,
    }
    _order = 'name'

    def _check_start_end_dates(self, cr, uid, ids, context=None):
        """ check the start date is before the end date """
        for l in self.browse(cr, uid, ids, context=context):
            if l.end_date < l.start_date:
                return False
        return True

    def unlink(self, cr, uid, ids, context=None):
        """Se eliminan todas las lineas cuando se elimina un presupuesto"""
        budget_lines_obj = self.pool.get('presupuesto.linea')
        lines_ids = budget_lines_obj.search(cr, uid, [('budget_id', 'in', ids)], context=context)
        budget_lines_obj.unlink(cr, uid, lines_ids, context=context)
        return super(presupuesto_presupuesto, self).unlink(cr, uid, ids, context=context)

    def write(self, cr, uid, ids, values, context=None):
        res_presupuesto = super(presupuesto_presupuesto, self).write(cr, uid, ids, values, context=context)
        valores = {}
        if 'inciso' in values:
            valores['linea_proy_inciso'] = values['inciso']

            lineas_obj = self.pool.get('presupuesto.linea')
            id_lineas = lineas_obj.search(cr, uid, [('budget_id', 'in', ids)], context=context)
            if id_lineas is not False:
                estructura_obj = self.pool.get('presupuesto.estructura')
                estructura_ids = estructura_obj.search(cr, uid, [('linea_id', 'in', id_lineas)], context=context)
                if estructura_ids is not False:
                    estructura_obj.write(cr, uid, estructura_ids, valores, context=context)
        return res_presupuesto

    def nombre_fiscal_unico(self, cr, uid, ids, context=None):
        for presupuesto in self.browse(cr, uid, ids, context=context):
            presupuesto_ids = self.search(cr, uid, [('name', '=', presupuesto.name),
                                                    ('fiscal_year', '=', presupuesto.fiscal_year.id)], context=context)
            if len(presupuesto_ids) > 1:
                return False
        return True

    def anio_fiscal_inciso_unico(self, cr, uid, ids, context=None):
        for presupuesto in self.browse(cr, uid, ids, context=context):
            presupuesto_ids = self.search(cr, uid, [('fiscal_year', '=', presupuesto.fiscal_year.id),
                                                    ('inciso', '=', presupuesto.inciso)], context=context)
            if len(presupuesto_ids) > 1:
                return False
        return True

    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear, context=None):
        """Cuando cambia el Año Fiscal, seteo fecha de inicio y fin de periodo"""
        fecha_inicio = self.pool.get('account.fiscalyear').browse(cr, uid, fiscalyear, context).date_start
        fecha_fin = self.pool.get('account.fiscalyear').browse(cr, uid, fiscalyear, context).date_stop
        return {'value': {'start_date': fecha_inicio, 'end_date': fecha_fin}}

    _constraints = [
        (_check_start_end_dates, 'Date Error: The end date is defined before the start date', ['start_date', 'end_date']),
        (nombre_fiscal_unico, u'El nombre de presupuesto debe ser único por año fiscal.', ['fiscal_year', 'name']),
        (anio_fiscal_inciso_unico, u'Debe existir un único presupuesto para la combinación Inciso - Año fiscal.', ['inciso', 'fiscal_year']),
    ]

    def carga_inicial_siif(self, cr, uid, ids, context=None):
        siif_proxy = self.pool.get('siif.proxy')
        if ids:
            presupuesto = self.browse(cr, uid, ids[0])

            ue_codes = []
            if presupuesto.unidad_ejecutora_ids:
                for ue in presupuesto.unidad_ejecutora_ids:
                    if ue.codigo not in ue_codes:
                        ue_codes.append(ue.codigo)

            # ----------------------------------------------------------------------------
            # Se ejecuta la Carga Inicial solo si no hay lineas cargadas en el presupuesto
            # ----------------------------------------------------------------------------
            if len(presupuesto.budget_line_ids) > 0:
                raise osv.except_osv(u'Atención !',
                                     u'No es posible realizar la Carga Inicial de un presupuesto con líneas')

            lista = siif_proxy.carga_inicial(cr, uid, presupuesto.fiscal_year.name, presupuesto.inciso)
            presup_line_obj = self.pool.get('presupuesto.linea')
            objeto_gasto_obj = self.pool.get("presupuesto.objeto.gasto")

            if len(lista) > 0:
                # ---------------------------------------------------------------------------------------
                # Proceso las lineas de presupuestos que retorna la consulta al servicio web CargaInicial
                # ---------------------------------------------------------------------------------------
                for presup in lista:
                    #Si se seleccionaron Unidades Ejecutoras, solo se tienen en cuenta estas, las otras se ignoran
                    if ue_codes and presup.unidadEjecutora not in ue_codes:
                        continue
                    #Solo cargo lineas del inciso del prespuesto (a veces vienen lineas de otros incisos ej: 21)
                    if presup.inciso != int(presupuesto.inciso):
                        continue
                    # ------------------------------------------------------
                    # Validacion: debe existir la combinacion ODG + Auxiliar
                    # ------------------------------------------------------
                    ids_objeto_gasto = objeto_gasto_obj.search(cr, uid,
                                                               [('name', '=', str(presup.objetoDelGasto).zfill(3)),
                                                                ('auxiliar', '=', str(presup.auxiliar).zfill(3))])
                    if len(ids_objeto_gasto) == 0:
                        # _logger.info('ODG: str(presup.objetoDelGasto).zfill(3): %s',str(presup.objetoDelGasto).zfill(3))
                        # _logger.info('Auxiliar: str(presup.auxiliar).zfill(3): %s',str(presup.auxiliar).zfill(3))
                        raise osv.except_osv('Error!', 'No existe la combinacion ODG + Auxiliar: ' + str(
                            presup.objetoDelGasto).zfill(3) + ' ' + str(presup.auxiliar).zfill(3))
                    # ----------------------------
                    # Creo la linea de presupuesto
                    # ----------------------------
                    vals = {}
                    # vals['filtro_anio_fiscal'] = presupuesto.fiscal_year
                    vals['budget_id'] = presupuesto.id
                    vals['ue'] = str(presup.unidadEjecutora).zfill(3)
                    vals['programa'] = str(presup.programa).zfill(3)
                    vals['proyecto'] = str(presup.proyecto).zfill(3)
                    vals['moneda'] = str(presup.moneda).zfill(1)
                    vals['tipo_credito'] = str(presup.tipoDeCredito).zfill(1)
                    vals['financiamiento'] = str(presup.financiamiento).zfill(2)
                    vals['objeto_gasto'] = str(presup.objetoDelGasto).zfill(3)
                    vals['auxiliar'] = str(presup.auxiliar).zfill(3)
                    vals['monto'] = presup.importe
                    vals['ajuste'] = 0
                    line_id = presup_line_obj.create(cr, uid, vals, context)
                    # _logger.info(line_id)
        # MVARELA luego de cargar el presupuesto se actualiza la estructura de combinaciones validas
        self.cargar_combinaciones_validas(cr, uid, ids, context)
        return True

    def refrescar_ajustes_siif(self, cr, uid, ids, context=None):
        """Carga desde SIIF los Ajustes al Presupuesto"""

        _logger.info('INICIO ------------------')

        presup_line_obj = self.pool.get('presupuesto.linea')
        objeto_gasto_obj = self.pool.get("presupuesto.objeto.gasto")
        siif_proxy = self.pool.get('siif.proxy')

        # ----------------------------------------------------------------------------
        # Se ejecuta la Carga de Ajustes para el presupuesto
        # ----------------------------------------------------------------------------
        budget_id = ids[0]
        if budget_id:

            presupuesto = self.browse(cr, uid, ids[0])

            ue_codes = []
            if presupuesto.unidad_ejecutora_ids:
                for ue in presupuesto.unidad_ejecutora_ids:
                    if ue.codigo not in ue_codes:
                        ue_codes.append(ue.codigo)

            fecha_hasta = time.strftime("%Y-%m-%d")
            #el presupuesto ahora se carga en diciembre del año anterior
            #fecha_desde = presupuesto.fiscal_year.date_start
            # anio_actual = time.strftime("%Y")
            # anio_anterior = str(int(anio_actual) -1)
            fecha_desde = '2000-01-01'


            _logger.info('fecha desde: %s', fecha_desde)
            _logger.info('fecha hasta: %s', fecha_hasta)

            lista = siif_proxy.carga_inicial_y_ajuste(cr, uid, presupuesto.fiscal_year.name, presupuesto.inciso, fecha_desde, fecha_hasta)
            ajustes_compensados = {}

            _logger.info('lista: %s', lista)

            if len(lista) > 0:
                for presup in lista:
                    #Si se seleccionaron Unidades Ejecutoras, solo se tienen en cuenta estas, las otras se ignoran
                    if ue_codes and presup.unidadEjecutora not in ue_codes:
                        continue
                    # Solo cargo lineas del inciso del prespuesto (a veces vienen lineas de otros incisos ej: 21)
                    if presup.inciso != int(presupuesto.inciso):
                        continue
                    # ------------------------------------------------------
                    # Validacion: debe existir la combinacion ODG + Auxiliar
                    # ------------------------------------------------------
                    ids_objeto_gasto = objeto_gasto_obj.search(cr, uid,
                                                               [('name', '=', str(presup.objetoDelGasto).zfill(3)),
                                                                ('auxiliar', '=', str(presup.auxiliar).zfill(3))])
                    if len(ids_objeto_gasto) == 0:
                        raise osv.except_osv('Error!', 'No existe la combinacion ODG + Auxiliar: ' + str(
                            presup.objetoDelGasto).zfill(3) + ' ' + str(presup.auxiliar).zfill(3))

                    clave = _generar_dictkey(presup)
                    if clave in ajustes_compensados:
                        ajustes_compensados[clave] = ajustes_compensados[clave] + presup.importe
                    else:
                        ajustes_compensados[clave] = presup.importe

                for key in ajustes_compensados:
                    vals = {}
                    lista_key = key.split('|')
                    condicion = []
                    condicion.append(('budget_id', '=', presupuesto.id))
                    condicion.append(('ue', '=', lista_key[0]))
                    condicion.append(('programa', '=', lista_key[1]))
                    condicion.append(('proyecto', '=', lista_key[2]))
                    condicion.append(('moneda', '=', lista_key[3]))
                    condicion.append(('tipo_credito', '=', lista_key[4]))
                    condicion.append(('financiamiento', '=', lista_key[5]))
                    condicion.append(('objeto_gasto', '=', lista_key[6]))
                    condicion.append(('auxiliar', '=', lista_key[7]))

                    lineas_ids = presup_line_obj.search(cr, uid, condicion, 0, None, None, context)

                    encontre = False
                    for line in presup_line_obj.browse(cr, uid, lineas_ids, context):
                        # ----------------------------------------------------------------------------
                        # Modifico campo ajuste de cada linea del presupuesto
                        # ----------------------------------------------------------------------------
                        encontre = True
                        # ----------------------------------------------------------------------------
                        # En los ajustes viene siempre la Carga Inicial, por lo que entonces para obtener sólo el ajuste,
                        # corresponde calcular la diferencia  con el monto de la carga inicial  de la linea del presupuesto
                        # ----------------------------------------------------------------------------
                        vals['ajuste'] = float(ajustes_compensados[key]) - line.monto
                        line_id = presup_line_obj.write(cr, uid, lineas_ids, vals, context)

                    # ----------------------------------------------------------------------------
                    # Si viene ajuste para linea que no se encuentra en el presupuesto, se agrega la linea al presupuesto
                    # ----------------------------------------------------------------------------
                    if not encontre:
                        vals = {}
                        # vals['filtro_anio_fiscal'] = line.budget_id.fiscal_year.id
                        vals['budget_id'] = presupuesto.id
                        vals['ue'] = lista_key[0]
                        vals['programa'] = lista_key[1]
                        vals['proyecto'] = lista_key[2]
                        vals['moneda'] = lista_key[3]
                        vals['tipo_credito'] = lista_key[4]
                        vals['financiamiento'] = lista_key[5]
                        vals['objeto_gasto'] = lista_key[6]
                        vals['auxiliar'] = lista_key[7]
                        vals['monto'] = 0
                        vals['ajuste'] = ajustes_compensados[key]
                        line_id = presup_line_obj.create(cr, uid, vals, context)
        _logger.info('fin!')
        # MVARELA luego de cargar el presupuesto se actualiza la estructura de combinaciones validas
        self.cargar_combinaciones_validas(cr, uid, ids, context)
        return True

    def cargar_staging_obtener_afe_com_obl_por_ue_siif_button(self, cr, uid, ids, context=None):
        return self.cargar_staging_obtener_afe_com_obl_por_ue_siif(cr, uid, context)

    def cargar_staging_obtener_afe_com_obl_por_ue_siif(self, cr, uid, context=None):
        """Carga desde SIIF obligaciones"""

        grp_obligaciones_siif_presupuesto_obj = self.pool.get('grp.obligaciones.siif.presupuesto')
        grp_log_obligaciones_siif_presupuesto_obj = self.pool.get('grp.log.obligaciones.siif.presupuesto')

        errores_ejecucion = False
        registros_procesados = 0
        datos = ''

        if context is None:
            context = {}
        context=dict(context)

        _logger.info('INICIO cargar_staging_obtener_afe_com_obl_por_ue_siif ------------------')

        siif_proxy = self.pool.get('siif.proxy')


        inciso = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.inciso
        fecha_desde = self.pool.get('ir.config_parameter').get_param(cr, uid, 'grp_factura_siif.CargarStaging.ultima_ejecucion')
        if not fecha_desde:
            fecha_desde = datetime.date.today().strftime("%Y-%m-%d")
        _logger.info("Fecha desde:" + fecha_desde)
        fecha_hasta = fecha_desde
        fiscal_year = datetime.datetime.strptime(fecha_desde, "%Y-%m-%d").year


        _logger.info('fecha desde: %s', fecha_desde)
        _logger.info('fecha hasta: %s', fecha_hasta)

        # Se procesan todos los registros del modelo operating.unit (unidad_ejecutora)

        operating_unit_obj = self.pool.get('operating.unit')

        operating_unit_ids = operating_unit_obj.search(cr, uid, [])
        operating_units = operating_unit_obj.browse(cr, uid, operating_unit_ids,context=context)

        try:

            for operating_unit in operating_units:


                unidad_ejecutora = operating_unit.unidad_ejecutora
                _logger.info('unidad_ejecutora: %s', unidad_ejecutora)

                # Se procesan 2 valores para procesoGenObl LNG y AOF
                genObl = ['LNG', 'AOF']
                for i, procesoGenObl in enumerate(genObl):

                    _logger.info('procesoGenObl: %s', procesoGenObl)
                    lista = siif_proxy.obtener_afe_com_obl_por_ue(cr, uid, fiscal_year, inciso, unidad_ejecutora, fecha_desde,
                                                                  fecha_hasta, procesoGenObl)
                    if len(lista) > 1:
                        _logger.info('Hay datos para procesar')
                        for elem in lista[1]:
                            registros_procesados = registros_procesados + 1
                            #Primero debo verificar si la oblgacion ya esta cargada en la staging o no. pero esto no necesariamente es correcto
                            # 20180301: Se agrega el campo acreedor_por_retencion para identificar las potenciales "obligaciones hermanas" (en lineas de retencion)
                            staging_element = grp_obligaciones_siif_presupuesto_obj.search(cr, uid, [('anio', '=', elem.anio if hasattr(elem, 'anio') else ''),('inciso', '=', elem.inciso if hasattr(elem, 'inciso') else ''),('unidad_ejecutora', '=', elem.unidadEjecutora if hasattr(elem, 'unidadEjecutora') else ''),('nro_doc_afectacion', '=', elem.nroDocAfectacion if hasattr(elem, 'nroDocAfectacion') else ''),('nro_doc_compromiso', '=', elem.nroDocCompromiso if hasattr(elem, 'nroDocCompromiso') else ''),('nro_doc_obligacion', '=', elem.nroDocObligacion if hasattr(elem, 'nroDocObligacion') else ''),('sec_obligacion', '=', elem.secObligacion if hasattr(elem, 'secObligacion') else ''),('grupo', '=', elem.grupo if hasattr(elem, 'grupo') else ''),('acreedor_por_retencion', '=', elem.acreedorPorRetencion if hasattr(elem, 'acreedorPorRetencion') else '')])

                            if not staging_element:
                                vals_staging = {
                                    'anio': elem.anio if hasattr(elem, 'anio') else '',
                                    'inciso': elem.inciso if hasattr(elem, 'inciso') else '',
                                    'unidad_ejecutora': elem.unidadEjecutora if hasattr(elem, 'unidadEjecutora') else '',
                                    'nro_doc_afectacion': elem.nroDocAfectacion if hasattr(elem, 'nroDocAfectacion') else '',
                                    'nro_doc_compromiso': elem.nroDocCompromiso if hasattr(elem, 'nroDocCompromiso') else '',
                                    'nro_doc_obligacion': elem.nroDocObligacion if hasattr(elem, 'nroDocObligacion') else '',
                                    'sec_obligacion': elem.secObligacion if hasattr(elem, 'secObligacion') else '',
                                    'tipo_de_modificacion': elem.tipoModificacion if hasattr(elem, 'tipoModificacion') else '',
                                    'tipo_de_ejecucion': elem.tipoEjecucion if hasattr(elem, 'tipoEjecucion') else '',
                                    'tipo_doc_respaldo': elem.tipoDocRespaldo if hasattr(elem, 'tipoDocRespaldo') else '',
                                    'tipo_programa': elem.tipoPrograma if hasattr(elem, 'tipoPrograma') else '',
                                    'documento_respaldo': elem.documentoRespaldo if hasattr(elem, 'documentoRespaldo') else '',
                                    'fecha_doc_respaldo': elem.fechaDocRespaldo if hasattr(elem, 'fechaDocRespaldo') else '',
                                    'factura_fecha_recepcion': elem.facturaFechaRecepcion if hasattr(elem, 'facturaFechaRecepcion') else '',
                                    'resumen': elem.resumen if hasattr(elem, 'resumen') else '',
                                    'codigo_sir': elem.codigoSir if hasattr(elem, 'codigoSir') else '',
                                    'monto_obligacion': elem.montoObligacion if hasattr(elem, 'montoObligacion') else '',
                                    'monto_retenciones': elem.montoRetenciones if hasattr(elem, 'montoRetenciones') else '',
                                    'liquido_a_pagar': elem.liquidoPagar if hasattr(elem, 'liquidoPagar') else '',
                                    'clase_id': elem.claseId if hasattr(elem, 'claseId') else '',
                                    'ruc': elem.ruc if hasattr(elem, 'ruc') else '',
                                    'banco': elem.banco if hasattr(elem, 'banco') else '',
                                    'agencia': elem.agencia if hasattr(elem, 'agencia') else '',
                                    'cta_corriente': elem.ctaCorriente if hasattr(elem, 'ctaCorriente') else '',
                                    'tipo_cuenta': elem.tipoCuenta if hasattr(elem, 'tipoCuenta') else '',
                                    'moneda_cuenta': elem.monedaCuenta if hasattr(elem, 'monedaCuenta') else '',
                                    'estado_obligacion': elem.estadoObligacion if hasattr(elem, 'estadoObligacion') else '',
                                    'proceso_general_obl': elem.procesoGeneralObl if hasattr(elem, 'procesoGeneralObl') else '',
                                    'programa': elem.programa if hasattr(elem, 'programa') else '',
                                    'proyecto': elem.proyecto if hasattr(elem, 'proyecto') else '',
                                    'objeto_gasto': elem.objetoDelGasto if hasattr(elem, 'objetoDelGasto') else '',
                                    'auxiliar': elem.auxiliar if hasattr(elem, 'auxiliar') else '',
                                    'financiamiento': elem.financiamiento if hasattr(elem, 'financiamiento') else '',
                                    'moneda': elem.moneda if hasattr(elem, 'moneda') else '',
                                    'tipo_credito': elem.tipoDeCredito if hasattr(elem, 'tipoDeCredito') else '',
                                    'monto': elem.monto if hasattr(elem, 'monto') else '',
                                    'grupo': elem.grupo if hasattr(elem, 'grupo') else '',
                                    'acreedor_por_retencion': elem.acreedorPorRetencion if hasattr(elem, 'acreedorPorRetencion') else '',
                                    'monto_retencion': elem.montoRetencion if hasattr(elem, 'montoRetencion') else '',
                                    'tipo_impuesto': elem.tipoImpuesto if hasattr(elem, 'tipoImpuesto') else '',
                                    'monto_calculo': elem.montoCalculo if hasattr(elem, 'montoCalculo') else '',
                                    'state': 'pendant',
                                    'timestamp': datetime.datetime.now(),

                                }

                                staging = grp_obligaciones_siif_presupuesto_obj.create(cr, uid, vals_staging)


        except Exception as e:
            _logger.info('Exception procesar_staging_obtener_afe_com_obl_por_ue_siif ------------------')
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            _logger.info('cargar_staging_obtener_afe_com_obl_por_ue_siif error type=' + str(exc_type))
            _logger.info('cargar_staging_obtener_afe_com_obl_por_ue_siif error file=' + str(fname))
            _logger.info('cargar_staging_obtener_afe_com_obl_por_ue_siif error line=' + str(exc_tb.tb_lineno))
            _logger.info('cargar_staging_obtener_afe_com_obl_por_ue_siif error message=' + str(e.message))

            errores_ejecucion = True

        vals_log = {
            'timestamp': datetime.datetime.now(),
            'tipo_proceso': 'carga',
            'fecha_proceso_carga': datetime.datetime.strptime(fecha_desde, "%Y-%m-%d"),
            'registros_procesados': registros_procesados,
            'errores': errores_ejecucion,
            'texto': datos

        }

        log_element = grp_log_obligaciones_siif_presupuesto_obj.create(cr, uid, vals_log)

        # Si no hay errores, entonces se actualiza el parametro grp_factura_siif.CargarStaging.ultima_ejecucion, incrementandolo en 1 dia
        if not errores_ejecucion:
            self.pool.get('ir.config_parameter').set_param(cr, uid, 'grp_factura_siif.CargarStaging.ultima_ejecucion', (datetime.datetime.strptime(fecha_desde, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))

    def procesar_staging_obtener_afe_com_obl_por_ue_siif_button(self, cr, uid, ids, context=None):
        return self.procesar_staging_obtener_afe_com_obl_por_ue_siif(cr, uid, context)

    def procesar_staging_obtener_afe_com_obl_por_ue_siif(self, cr, uid, context=None):
            """Carga desde SIIF obligaciones"""

            _logger.info('INICIO procesar_staging_obtener_afe_com_obl_por_ue_siif ------------------')
            errores_ejecucion = False
            registros_procesados = 0

            grp_obligaciones_siif_presupuesto_obj = self.pool.get('grp.obligaciones.siif.presupuesto')
            grp_log_obligaciones_siif_presupuesto_obj = self.pool.get('grp.log.obligaciones.siif.presupuesto')

            staging_elements_ids = grp_obligaciones_siif_presupuesto_obj.search(cr, uid, [('state', '=', 'pendant')])
            staging_elements = grp_obligaciones_siif_presupuesto_obj.browse(cr, uid, staging_elements_ids,context=context)
            for elem in staging_elements:
                try:

                        registros_procesados = registros_procesados + 1
                        #ir_model_data_obj = self.pool.get('ir.model.data')
                        invoice_obj = self.pool.get('account.invoice')
                        invoice_line_obj = self.pool.get('account.invoice.line')
                        grp_compras_lineas_llavep_obj = self.pool.get('grp.compras.lineas.llavep')
                        account_global_retention_line_obj = self.pool.get('account.global.retention.line')

                        fiscalyear_obj = self.pool.get('account.fiscalyear')
                        pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')

                        operating_unit_obj = self.pool.get('operating.unit')
                        unidad_ejecutora_obj = self.pool.get('unidad.ejecutora')
                        tipo_ejecucion_siif_obj = self.pool.get('tipo.ejecucion.siif')
                        tipo_documento_siif_obj = self.pool.get('tipo.documento.siif')
                        codigo_sir_siif_obj = self.pool.get('codigo.sir.siif')
                        res_bank_obj = self.pool.get('res.bank')
                        res_partner_bank_obj = self.pool.get('res.partner.bank')
                        res_partner_obj = self.pool.get('res.partner')

                        pres_ue_obj = self.pool.get('grp.estruc_pres.ue')
                        pres_ff_obj = self.pool.get('grp.estruc_pres.ff')
                        pres_programa_obj = self.pool.get('grp.estruc_pres.programa')
                        pres_proyecto_obj = self.pool.get('grp.estruc_pres.proyecto')
                        pres_odg_obj = self.pool.get('grp.estruc_pres.odg')
                        pres_aux_obj = self.pool.get('grp.estruc_pres.aux')
                        pres_moneda_obj = self.pool.get('grp.estruc_pres.moneda')
                        pres_tc_obj = self.pool.get('grp.estruc_pres.tc')

                        financiamiento_siif_obj = self.pool.get('financiamiento.siif')
                        rupe_cuentas_bancarias_obj = self.pool.get('rupe.cuentas.bancarias')
                        res_currency_obj = self.pool.get('res.currency')

                        account_retention_creditors_obj = self.pool.get('account.retention.creditors')
                        account_group_creditors_obj = self.pool.get('account.group.creditors')

                        product_template_obj = self.pool.get('product.template')
                        product_product_obj = self.pool.get('product.product')

                        tipo_documento_siif_obj = self.pool.get('tipo.documento.siif')
                        grp_integracion_intervenidas_obj = self.pool.get('grp.integracion.intervenidas')


                        partner_id = ''
                        beneficiario_siif_id = ''
                        account_id = ''
                        #DDELFINO: 20181210 - Cambio pedido por Alicia B. se cambia tipo_doc_siif por tipo_doc_rupe
                        res_partner = res_partner_obj.search(cr, uid, [('tipo_doc_rupe', '=', elem.clase_id), ('nro_doc_rupe', '=', elem.ruc)])
                        #res_partner = res_partner_obj.search(cr, uid, [('tipo_doc_siif', '=', elem.clase_id), ('nro_doc_rupe', '=', elem.ruc)])
                        if not res_partner:
                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {'texto_error':'No se encuentra partner_id a partir de claseId=%s y ruc=%s' % (str(elem.clase_id), str(elem.ruc)),'state':'error'}, context=context)
                            errores_ejecucion = True
                            continue
                        else:
                            res_partner_data = res_partner_obj.browse(cr, uid, res_partner[0], context=context)
                            partner_id = res_partner_data.id
                            beneficiario_siif_id = partner_id
                            banco_partner_id = ''
                            if res_partner_data.es_inciso:
                                # Banco para el que coincida este número con el campo bic del modelo res.bank
                                banco = res_bank_obj.search(cr, uid, [('bic', '=', str(elem.banco).zfill(3))])
                                if banco:
                                    banco_id = banco[0]
                                    if elem.tipo_cuenta == 'C':
                                        tipoCuenta = 'cuenta corriente'
                                    # El otro caso es tipo_cuenta == 'A' pero no pregunto, salgo por el else
                                    else:
                                        tipoCuenta = 'caja de ahorros'
                                    banco_partner = res_partner_bank_obj.search(cr, uid, [('bank', '=', banco_id), (
                                    'agencia', '=', elem.agencia), ('acc_number', '=', str(elem.cta_corriente).zfill(14)),
                                                                                          ('state', '=', tipoCuenta)])
                                    if banco_partner:
                                        banco_partner_id = banco_partner[0]
                                        rupe_cuenta_bancaria_id = ''
                                        #rupe_cuenta_bancaria_id = banco_partner_id
                                    else:
                                        rupe_cuenta_bancaria_id = ''
                            else:
                                id_rupe = res_partner_data.id_rupe
                                if elem.tipo_cuenta == 'C':
                                    tipoCuenta = 'CC'
                                # El otro caso es tipo_cuenta == 'A' pero no pregunto, salgo por el else
                                else:
                                    tipoCuenta = 'CA'

                                #if elem.moneda_cuenta == 0:
                                #    moneda_id = res_currency_obj.search(cr, uid,[('name', 'in', ['UYU'])])
                                #else:
                                # El otro caso es moneda_cuenta == '1' pero no pregunto, salgo por el else
                                #    moneda_id = res_currency_obj.search(cr, uid,[('name', 'in', ['USD'])])

                                if elem.moneda == 0:
                                    moneda_rupe = 'UYU'
                                else:
                                    moneda_rupe = 'USD'

                                rupe_cuenta_bancaria = rupe_cuentas_bancarias_obj.search(cr, uid, [('cnt_proveedor_prv_id', '=', id_rupe),('codigo_banco', '=', str(elem.banco).zfill(3)),('codigo_sucursal', '=', str(elem.agencia)),('cnt_nro_cuenta', '=', str(elem.cta_corriente)),('codigo_tipo_cuenta', '=', tipoCuenta),('codigo_moneda', '=', moneda_rupe)])
                                if not rupe_cuenta_bancaria:
                                    grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                        'texto_error': 'No se encuentra rupe_cuenta_bancaria_id a partir de cnt_proveedor_prv_id=%s, codigo_banco=%s, codigo_sucursal=%s, cnt_nro_cuenta=%s, codigo_tipo_cuenta=%s, codigo_moneda=%s ' % (
                                        str(id_rupe),str(elem.banco).zfill(3),str(elem.agencia),str(elem.cta_corriente),str(tipoCuenta),str(moneda_rupe)), 'state': 'error'}, context=context)
                                    errores_ejecucion = True
                                    continue
                                else:
                                    banco_partner_id = ''
                                    rupe_cuenta_bancaria_id = rupe_cuenta_bancaria[0]

                            #rupe_cuenta_bancaria_id = rupe_cuenta_bancaria_id if res_partner_data.es_inciso else ''

                            account_id = res_partner_data.property_account_payable.id

                        #TODO: Ver que hacer con el tema de moneda (ver doc)
                        #res_currency_obj.search(cr, uid, [('bic', '=', str(elem.banco).zfill(3))])

                        # base_company = ir_model_data_obj.search(cr, uid, [('name', '=', 'main_company')])
                        # if len(base_company) == 0:
                        #     grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {'texto_error':'No se encuentra \'main_company\' en modelo ir.model_data','state':'error'}, context=context)
                        # else:
                        #     base_company_data = ir_model_data_obj.browse(cr, uid, base_company[0], context=context)
                        #     partner_id = base_company_data.res_id


                        fiscalyear = fiscalyear_obj.search(cr, uid,[('code', '=', elem.anio)], context=context)
                        if not fiscalyear:
                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {'texto_error':'No se encuentra fiscal_year a partir de anio=%s' % (str(elem.anio)),'state':'error'}, context=context)
                            errores_ejecucion = True
                            continue

                        fiscal_year_id = fiscalyear[0]
                        pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id', '=', fiscal_year_id),('inciso', '=', elem.inciso)])

                        if not pres_inciso:
                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {'texto_error':'No se encuentra inciso a partir de fiscal_year_id=%s e inciso=%s' % (str(fiscal_year_id),str(elem.inciso)),'state':'error'}, context=context)
                            errores_ejecucion = True
                            continue

                        inciso_id =  pres_inciso[0]

                        #unidad_ejecutora_id: tomar la que el campo codigo del modelo unidad.ejecutora coincida con lo que viene en este campo
                        unidad_ejecutora_id = ''
                        operating_unit_id = ''

                        unidad_ejecutora = unidad_ejecutora_obj.search(cr, uid, [('codigo', '=', int(elem.unidad_ejecutora))])
                        if unidad_ejecutora:
                            unidad_ejecutora_id = unidad_ejecutora[0]
                            #unidad_ejecutora_data = unidad_ejecutora_obj.browse(cr, uid, unidad_ejecutora_id, context=context)
                            #code_unidad_ejecutora = unidad_ejecutora_data.str_codigo

                            #operating_unit_id: obtener la operating unit que tenga en el campo unidad_ejecutora el mismo valor que el que viene en el servicio
                            operating_unit = operating_unit_obj.search(cr, uid, [('unidad_ejecutora', '=', str(elem.unidad_ejecutora).zfill(3))])
                            #operating_unit = operating_unit_obj.search(cr, uid, [('unidad_ejecutora', '=', code_unidad_ejecutora)])
                            if operating_unit:
                                operating_unit_id = operating_unit[0]


                        # El orden en que se deben obtener es: ODG, AUX, FIN, Programa, Proyecto, Mon, TC
                        ue_siif_id = ''
                        odg_id = ''
                        auxiliar_id = ''
                        fin_id = ''
                        programa_id = ''
                        proyecto_id = ''
                        mon_id = ''
                        tc_id = ''
                        creditor_id = ''
                        group_id = ''
                        obligacion_retencion = False
                        pres_ue = pres_ue_obj.search(cr, uid, [('inciso_id', '=', inciso_id), ('ue', '=', str(elem.unidad_ejecutora).zfill(3))])
                        if not pres_ue:
                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {'texto_error':'No se ha encontrado la unidad ejecutora con valor %s , asociado al inciso %s.' % (str(elem.unidad_ejecutora).zfill(3), inciso_id),'state':'error'}, context=context)
                            errores_ejecucion = True
                            continue
                        else:

                            ue_siif_id = pres_ue[0]
                            odg = pres_odg_obj.search(cr, uid, [('ue_id', '=', ue_siif_id), ('odg', '=', str(elem.objeto_gasto).zfill(3))],limit=1)
                            if not odg:
                                #En este caso debo verificar que no se trate de una "obligacion hermana", para ello verifico el valor del tag grupo
                                #20180301: Con valor grupo distinto de 0 puede haber n (n "obligaciones hermanas" que generan n lineas de retencion)
                                if elem.grupo == 0:
                                    grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                        'texto_error': 'No se ha encontrado el objeto del gasto con valor %s , asociado a la operating_unit %s.' % (str(elem.objeto_gasto), operating_unit_id), 'state':'error'}, context = context)
                                    errores_ejecucion = True
                                    continue
                                else:
                                    #En este caso como viene el dato de grupo entonces se asume que es la "obligacion hermana" y corresponde generar la linea de retencion.
                                    obligacion_retencion = True
                                    group = account_group_creditors_obj.search(cr, uid, [('grupo', '=', elem.grupo)],context=context)
                                    if not group:
                                        grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                            'texto_error': 'No se encuentra el grupo_id a partir de grupo=%s' % (str(elem.grupo)),
                                            'state': 'error'}, context=context)
                                        errores_ejecucion = True
                                        continue

                                    group_id = group[0]
                                    creditor = account_retention_creditors_obj.search(cr, uid, [('acreedor', '=', elem.acreedor_por_retencion)],context=context)
                                    if not creditor:
                                        grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                            'texto_error': 'No se encuentra el creditor_id a partir de acreedor_por_retencion=%s' % (
                                            str(elem.acreedor_por_retencion)),
                                            'state': 'error'}, context=context)
                                        errores_ejecucion = True
                                        continue

                                    creditor_id = creditor[0]
                                    account_ret = account_retention_creditors_obj.browse(cr, uid, creditor_id,context=context)
                                    account_id_ret = account_ret.account_id.id
                                    if not account_id_ret:
                                        grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                            'texto_error': 'No se encuentra el account_id a partir de acreedor_por_retencion=%s' % (
                                                str(elem.acreedor_por_retencion)),
                                            'state': 'error'}, context=context)
                                        errores_ejecucion = True
                                        continue


                            else:
                                odg_id = odg[0]
                                auxiliar = pres_aux_obj.search(cr, uid, [('odg_id', '=', odg_id), ('aux', '=', str(elem.auxiliar).zfill(3))], limit=1) if odg_id else False
                                if not auxiliar:
                                    grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                        'texto_error': 'No se ha encontrado el auxiliar con valor %s , asociado al objeto del gasto %s.' % (str(elem.auxiliar).zfill(3), odg_id), 'state': 'error'},
                                                                                context=context)
                                    errores_ejecucion = True
                                    continue
                                else:
                                    auxiliar_id = auxiliar[0]
                                    financiamiento = pres_ff_obj.search(cr, uid,[('aux_id', '=', auxiliar_id), ('ff', '=', str(elem.financiamiento))])

                                    if not financiamiento:
                                        grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                            'texto_error': 'No se ha encontrado el financiamiento con valor %s , asociado al auxiliar %s.' % (
                                                             str(elem.financiamiento), auxiliar_id), 'state': 'error'},
                                                                                    context=context)
                                        errores_ejecucion = True
                                        continue
                                    else:
                                        fin_id = financiamiento[0]
                                        programa = pres_programa_obj.search(cr, uid, [('ff_id', '=', fin_id), ('programa', '=', str(elem.programa))])

                                        if not programa:
                                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                                'texto_error': 'No se ha encontrado el programa con valor %s , asociado al financiamiento %s.' % (
                                                                     str(elem.programa), fin_id), 'state': 'error'},
                                                                                        context=context)
                                            errores_ejecucion = True
                                            continue
                                        else:
                                            programa_id = programa[0]
                                            proyecto = pres_proyecto_obj.search(cr, uid, [('programa_id', '=', programa_id), ('proyecto', '=', str(elem.proyecto).zfill(3))])

                                            if not proyecto:
                                                grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                                    'texto_error': 'No se ha encontrado el proyecto con valor %s , asociado al programa %s.' % (
                                                                         str(elem.proyecto).zfill(3), programa_id), 'state': 'error'},
                                                                                            context=context)
                                                errores_ejecucion = True
                                                continue
                                            else:
                                                proyecto_id = proyecto[0]
                                                moneda = pres_moneda_obj.search(cr, uid, [('proyecto_id', '=', proyecto_id), ('moneda', '=', str(elem.moneda))])
                                                if not moneda:
                                                    grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                                        'texto_error': 'No se ha encontrado la moneda con valor %s , asociado al proyecto %s.' % (
                                                                             str(elem.moneda), proyecto_id), 'state': 'error'},
                                                                                                context=context)
                                                    errores_ejecucion = True
                                                    continue
                                                else:
                                                    mon_id = moneda[0]
                                                    tipo_credito = pres_tc_obj.search(cr, uid, [('moneda_id', '=', mon_id), ('tc', '=', str(elem.tipo_credito))])
                                                    if not tipo_credito:
                                                        grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id],{'texto_error': 'No se ha encontrado el tipo de credito con valor %s , asociado a la moneda %s.' % (str(elem.tipo_credito), mon_id),'state': 'error'},context=context)
                                                        errores_ejecucion = True
                                                        continue
                                                    else:
                                                        tc_id = tipo_credito[0]

                        #siif_tipo_ejecucion: esto es un catálogo, se debe mapear este valor con el campo codigo del modelo tipo.ejecucion.siif
                        siif_tipo_ejecucion = ''
                        tipo_ejecucion_siif = tipo_ejecucion_siif_obj.search(cr, uid, [('codigo', '=', elem.tipo_de_ejecucion)])
                        if tipo_ejecucion_siif:
                            siif_tipo_ejecucion = tipo_ejecucion_siif[0]

                        #siif_tipo_documento: esto es un catálogo, se debe mapear este valor con el campo codigo del modelo tipo.documento.siif
                        siif_tipo_documento = ''
                        #DDELFINO 20181210 - Elimino esta parte porque se carga con el codigo 99 mas adelante
                        #if (elem.tipo_doc_respaldo != 0):
                        #    tipo_documento_siif = tipo_documento_siif_obj.search(cr, uid, [('codigo', '=', elem.tipo_doc_respaldo)])
                            # TODO: Por ahora le fuerzo un valor (20180411: Ya no se fuerza)
                            #tipo_documento_siif = [10]
                        #    if not tipo_documento_siif:
                        #        grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                        #            'texto_error': 'No se encuentra el tipo documento siif a partir del codigo=%s' % (str(elem.tipo_doc_respaldo)),
                        #            'state': 'error'}, context=context)
                        #        errores_ejecucion = True
                        #        continue

                        #    siif_tipo_documento = tipo_documento_siif[0]

                        #siif_codigo_sir: esto es un catálogo, se debe mapear este valor con el campo codigo del modelo codigo.sir.siif
                        siif_codigo_sir = ''
                        codigo_sir_siif = codigo_sir_siif_obj.search(cr, uid, [('codigo', '=', str(elem.codigo_sir).zfill(17))])
                        # TODO: Por ahora le fuerzo un valor (20180411: Ya no se fuerza)
                        #codigo_sir_siif = [1]
                        if not codigo_sir_siif:
                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                'texto_error': 'No se encuentra el codigo sir siif a partir del codigo=%s' % (str(elem.codigo_sir).zfill(17)),
                                'state': 'error'}, context=context)
                            errores_ejecucion = True
                            continue
                        siif_codigo_sir = codigo_sir_siif[0]

                        #TODO: Validar si esta bien no obtener el valor cuando elem.financiamiento es cero
                        if str(elem.financiamiento)<>'0':
                            siif_financiamiento_id = financiamiento_siif_obj.search(cr, uid, [('codigo', '=', str(elem.financiamiento))])

                            if not siif_financiamiento_id:
                                grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                    'texto_error': 'No se ha encontrado el financiamiento a partir del codigo=%s.' % (
                                        str(elem.financiamiento)), 'state': 'error'},
                                                                            context=context)
                                errores_ejecucion = True
                                continue

                            siif_financiamiento = siif_financiamiento_id[0]



                        #siif_concepto_gasto = 13  # Remuneraciones

                        siif_tipo_documento_aux = tipo_documento_siif_obj.search(cr, uid, [('codigo', '=', 99)])
                        if siif_tipo_documento_aux:
                            siif_tipo_documento = siif_tipo_documento_aux[0]
                        else:
                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                'texto_error': 'No se ha encontrado el tipo de documento 99 - Otro a partir del codigo=%s.' % (
                                    str(99)), 'state': 'error'},context=context)
                            errores_ejecucion = True
                            continue

                        company = self.pool.get('res.users').browse(cr, uid, uid).company_id

                        if (company.journal_id_obl_siif):
                            journal_id_alq = company.journal_id_obl_siif.id
                        else:
                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                'texto_error': 'No se ha configurado Diario para Obligaciones SIIF Alquileres en la solapa integraciones de la compania.',
                                'state': 'error'}, context=context)
                            errores_ejecucion = True
                            continue

                        if (company.journal_id_obl_siif_lic):
                            journal_id_lic = company.journal_id_obl_siif_lic.id
                        else:
                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                'texto_error': 'No se ha configurado Diario para Obligaciones SIIF Licencias en la solapa integraciones de la compania.',
                                'state': 'error'}, context=context)
                            errores_ejecucion = True
                            continue

                        journal_id = ''
                        if (elem.proceso_general_obl == 'LNG'):
                            #self.sudo().env.user.company_id.siif_concepto_gasto_lng
                            journal_id = journal_id_lic
                            if (company.siif_concepto_gasto_lng):
                                siif_concepto_gasto = company.siif_concepto_gasto_lng.id
                            else:
                                grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                    'texto_error': 'No se ha configurado Concepto del Gasto para LNG en la solapa integraciones de la compania.', 'state': 'error'}, context=context)
                                errores_ejecucion = True
                                continue
                            if (company.product_id_lng):
                                product_id = company.product_id_lng.id
                            else:
                                grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                    'texto_error': 'No se ha configurado Producto para LNG en la solapa integraciones de la compania.',
                                    'state': 'error'}, context=context)
                                errores_ejecucion = True
                                continue

                        else:
                            if (elem.proceso_general_obl == 'AOF'):
                                journal_id = journal_id_alq
                                if (company.siif_concepto_gasto_aof):
                                    siif_concepto_gasto = company.siif_concepto_gasto_aof.id
                                else:
                                    grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                        'texto_error': 'No se ha configurado Concepto del Gasto para AOF en la solapa integraciones de la compania.', 'state': 'error'}, context=context)
                                    errores_ejecucion = True
                                    continue
                            if (company.product_id_aof):
                                product_id = company.product_id_aof.id
                            else:
                                grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                                    'texto_error': 'No se ha configurado Producto para AOF en la solapa integraciones de la compania.',
                                    'state': 'error'}, context=context)
                                errores_ejecucion = True
                                continue


                        #Uso la variables something_created para determinar al final del proceso si se creo algun registro en algun modelo, caso contrario se marca en error el registro de la tabla de staginb
                        something_created = False

                        #Puede ser que el cabezal ya exista, si ya procese una "obligacion hermana"
                        invoice_element = invoice_obj.search(cr, uid, [('fiscalyear_siif_id', '=', fiscal_year_id),('inciso_siif_id', '=', inciso_id),('unidad_ejecutora_id', '=', False if unidad_ejecutora_id == '' else unidad_ejecutora_id),('nro_afectacion', '=', elem.nro_doc_afectacion),('nro_compromiso', '=', elem.nro_doc_compromiso),('nro_obligacion', '=', elem.nro_doc_obligacion),('siif_sec_obligacion', '=', str(elem.sec_obligacion))])

                        if not invoice_element:

                            vals_invoice = {
                                'doc_type': '3en1_invoice',
                                'type': 'in_invoice',
                                'obligacion_afe_com_obl_por_ue_siif': True,
                                'fiscalyear_siif_id': fiscal_year_id,
                                'inciso_siif_id': inciso_id,
                                'operating_unit_id': operating_unit_id,
                                'ue_siif_id': ue_siif_id,
                                'unidad_ejecutora_id': unidad_ejecutora_id,
                                'nro_afectacion': elem.nro_doc_afectacion,
                                'nro_compromiso': elem.nro_doc_compromiso,
                                'nro_obligacion': elem.nro_doc_obligacion,
                                'siif_sec_obligacion': str(elem.sec_obligacion),
                                'siif_tipo_ejecucion': siif_tipo_ejecucion,
                                'siif_tipo_documento': siif_tipo_documento,
                                'date_invoice': elem.fecha_doc_respaldo,
                                'entry_date': elem.fecha_doc_respaldo,
                                'date_due' : elem.fecha_doc_respaldo,
                                'siif_descripcion': elem.resumen,
                                'siif_codigo_sir': siif_codigo_sir,
                                'partner_id': partner_id,
                                'beneficiario_siif_id': beneficiario_siif_id,
                                'account_id': account_id,
                                'journal_id': journal_id,
                                'siif_concepto_gasto': siif_concepto_gasto,
                                'siif_financiamiento': siif_financiamiento,
                                'rupe_cuenta_bancaria_id': rupe_cuenta_bancaria_id,
                                'partner_bank_id': banco_partner_id
                            }

                            #DDELFINO: 20181212 - Antes de crear el invoice correspondiente al 3en1 borro el eventual registro en la tabla de staging de intervenidas (grp.integracion.intervenidas)
                            condiciones_integracion_intervenidas = []
                            condiciones_integracion_intervenidas.append(
                                ('nro_doc_afectacion', '=', elem.nro_doc_afectacion))
                            condiciones_integracion_intervenidas.append(
                                ('nro_doc_compromiso', '=', elem.nro_doc_compromiso))
                            condiciones_integracion_intervenidas.append(
                                ('nro_doc_obligacion', '=', elem.nro_doc_obligacion))
                            condiciones_integracion_intervenidas.append(
                                ('anio_fiscal', '=', elem.anio))
                            condiciones_integracion_intervenidas.append(
                                ('unidad_ejecutora', '=',elem.unidad_ejecutora))
                            condiciones_integracion_intervenidas.append(
                                ('inciso', '=', elem.inciso))

                            id_registro = grp_integracion_intervenidas_obj.search(cr, uid,
                                                                                  condiciones_integracion_intervenidas,
                                                                                  context=context)

                            if id_registro:
                                #Debo borrarlo
                                grp_integracion_intervenidas_obj.unlink(cr, uid, id_registro, context=context)

                            invoice = invoice_obj.create(cr, uid, vals_invoice)
                            something_created = True
                        else:
                            invoice = invoice_element[0]
                        # Se crea la llave presupuestal o la retencion

                        if obligacion_retencion:

                            # Por las dudas verifico que no existan lineas de retencion para la factura, con los mismos valores de creditor_id y group_id
                            retencion_element = account_global_retention_line_obj.search(cr, uid, [('invoice_id', '=', invoice), ('creditor_id', '=', creditor_id), ('group_id', '=', group_id)])

                            if not retencion_element:
                                #product_product_data = product_product_obj.browse(cr, uid, product_id, context=context)
                                #product_template_data = product_template_obj.browse(cr, uid, product_product_data.product_tmpl_id.id, context=context)

                                #account_id_ret = product_template_data.property_account_expense.id

                                vals_retenciones_factura = {
                                    'invoice_id': invoice,
                                    'account_id': account_id_ret,
                                    'journal_id': journal_id,
                                    'creditor_id': creditor_id,
                                    'group_id': group_id,
                                    'amount_ret_pesos': elem.monto_retencion,
                                }
                                account_global_retention_line_id = account_global_retention_line_obj.create(cr, uid, vals_retenciones_factura)
                                something_created = True

                        else:
                            # Por las dudas verifico que no existan lineas para la factura, como es una sola linea con buscar por invoice alcanza.
                            invoice_line_element = invoice_line_obj.search(cr, uid, [('invoice_id', '=', invoice)])

                            if not invoice_line_element:
                                product_product_data = product_product_obj.browse(cr, uid, product_id, context=context)
                                product_template_data = product_template_obj.browse(cr, uid, product_product_data.product_tmpl_id.id, context=context)

                                account_id = product_template_data.property_account_expense.id
                                if product_product_data.default_code:
                                    product_name =  '[' + product_product_data.default_code + '] ' +  product_product_data.name_template
                                else:
                                    product_name = '[*] ' + product_product_data.name_template

                                vals_invoice_line = {
                                    'invoice_id': invoice,
                                    'account_id': account_id,
                                    'product_id': product_id,
                                    'name': product_name,
                                    'quantity': 1,
                                    'price_unit': elem.monto,
                                    'price_subtotal': elem.monto,
                                    'monto_moneda_base': elem.monto,
                                }
                                vals_invoice_line_id = invoice_line_obj.create(cr, uid, vals_invoice_line)
                                something_created = True


                            # Por las dudas verifico que no existan llaves presupuestales para la factura, como es una sola linea con buscar por invoice alcanza.
                            llave_presupestal_element = grp_compras_lineas_llavep_obj.search(cr, uid, [('invoice_id', '=', invoice)])

                            if not llave_presupestal_element:
                                vals_llaves_presupuestales_factura = {
                                    'invoice_id': invoice,
                                    'odg_id': odg_id,
                                    'auxiliar_id': auxiliar_id,
                                    'fin_id': fin_id,
                                    'programa_id': programa_id,
                                    'proyecto_id': proyecto_id,
                                    'mon_id': mon_id,
                                    'tc_id': tc_id,
                                    'importe': elem.monto,
                                }
                                llave_presupuestal_line_id = grp_compras_lineas_llavep_obj.create(cr, uid, vals_llaves_presupuestales_factura)
                                something_created = True

                        if something_created:
                            # Se presiona el button_reset_taxes
                            #invoice_data = invoice_obj.browse(cr, uid, invoice, context=context)
                            #invoice_data.button_reset_taxes()

                            #invoice_data.invoice_impactar_presupuesto()

                            #if not invoice_data.move_id:
                            #    wf_service = netsvc.LocalService('workflow')
                            #    wf_service.trg_validate(uid, 'account.invoice', invoice_data.id, 'invoice_open', cr)

                            #    invoice_obj.write(cr, uid, [invoice_data.id], {'state': 'forced'}, context=context)
                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id],{'texto_error': '','state': 'processed', 'factura_grp_id': invoice},context=context)
                        else:
                            grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id],{'texto_error': 'No se pudo insertar ningun registro porque la informacion ya existia en GRP.','state': 'processed'},context=context)

                except Exception as e:
                    _logger.info('Exception procesar_staging_obtener_afe_com_obl_por_ue_siif ------------------')
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    _logger.info('procesar_staging_obtener_afe_com_obl_por_ue_siif error type=' + str(exc_type))
                    _logger.info('procesar_staging_obtener_afe_com_obl_por_ue_siif error file=' + str(fname))
                    _logger.info('procesar_staging_obtener_afe_com_obl_por_ue_siif error line=' + str(exc_tb.tb_lineno))
                    _logger.info('procesar_staging_obtener_afe_com_obl_por_ue_siif error message=' +  str(e.message))
                    grp_obligaciones_siif_presupuesto_obj.write(cr, uid, [elem.id], {
                        'texto_error': 'Error no controlado especificamente, por favor contacte al administrador.', 'state': 'error'}, context=context)
                    errores_ejecucion = True

            vals_log = {
                'timestamp': datetime.datetime.now(),
                'tipo_proceso': 'proceso',
                'registros_procesados': registros_procesados,
                'errores': errores_ejecucion,

            }

            log_element = grp_log_obligaciones_siif_presupuesto_obj.create(cr, uid, vals_log)

    def cargar_combinaciones_validas(self, cr, uid, ids, context={}):
        #MVARELA se pasa el SUPERUSER_ID como uid para no tener que dar permisos de creacion a la estructura
        uid = SUPERUSER_ID
        pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')
        pres_ue_obj = self.pool.get('grp.estruc_pres.ue')
        pres_ff_obj = self.pool.get('grp.estruc_pres.ff')
        pres_programa_obj = self.pool.get('grp.estruc_pres.programa')
        pres_proyecto_obj = self.pool.get('grp.estruc_pres.proyecto')
        pres_odg_obj = self.pool.get('grp.estruc_pres.odg')
        pres_aux_obj = self.pool.get('grp.estruc_pres.aux')
        pres_moneda_obj = self.pool.get('grp.estruc_pres.moneda')
        pres_tc_obj = self.pool.get('grp.estruc_pres.tc')

        for presupuesto in self.browse(cr, uid, ids):
            #cargo tabla inciso, año fiscal
            anio_fiscal = presupuesto.fiscal_year.id
            inciso = presupuesto.inciso
            ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id','=', anio_fiscal),('inciso','=',inciso)])
            if len(ids_pres_inciso) == 0:
                id_pres_inciso = pres_inciso_obj.create(cr, uid, {'fiscal_year_id': anio_fiscal, 'inciso': inciso})
            else:
                id_pres_inciso = ids_pres_inciso[0]
            for linea in presupuesto.budget_line_ids:
                #cargo tabla ue
                ue = linea.ue
                ids_pres_ue = pres_ue_obj.search(cr, uid, [('inciso_id','=', id_pres_inciso),('ue','=',ue)])
                if len(ids_pres_ue) == 0:
                    id_pres_ue = pres_ue_obj.create(cr, uid, {'inciso_id': id_pres_inciso, 'ue': ue})
                else:
                    id_pres_ue = ids_pres_ue[0]

                #cargo tabla objeto del gasto
                odg = linea.objeto_gasto
                ids_pres_odg = pres_odg_obj.search(cr, uid, [('ue_id','=', id_pres_ue),('odg','=',odg)])
                if len(ids_pres_odg) == 0:
                    id_pres_odg = pres_odg_obj.create(cr, uid, {'ue_id': id_pres_ue, 'odg': odg})
                else:
                    id_pres_odg = ids_pres_odg[0]

                #cargo tabla auxiliar
                aux = linea.auxiliar
                ids_pres_aux = pres_aux_obj.search(cr, uid, [('odg_id','=', id_pres_odg),('aux','=',aux)])
                if len(ids_pres_aux) == 0:
                    id_pres_aux = pres_aux_obj.create(cr, uid, {'odg_id': id_pres_odg, 'aux': aux})
                else:
                    id_pres_aux = ids_pres_aux[0]

                #cargo tabla ff
                ff = linea.financiamiento
                ids_pres_ff = pres_ff_obj.search(cr, uid, [('aux_id','=', id_pres_aux),('ff','=',ff)])
                if len(ids_pres_ff) == 0:
                    id_pres_ff = pres_ff_obj.create(cr, uid, {'aux_id': id_pres_aux, 'ff': ff})
                else:
                    id_pres_ff = ids_pres_ff[0]

                #cargo tabla programa
                programa = linea.programa
                ids_pres_programa = pres_programa_obj.search(cr, uid, [('ff_id','=', id_pres_ff),('programa','=',programa)])
                if len(ids_pres_programa) == 0:
                    id_pres_programa = pres_programa_obj.create(cr, uid, {'ff_id': id_pres_ff, 'programa': programa})
                else:
                    id_pres_programa = ids_pres_programa[0]

                #cargo tabla proyecto
                proyecto = linea.proyecto
                ids_pres_proyecto = pres_proyecto_obj.search(cr, uid, [('programa_id','=', id_pres_programa),('proyecto','=',proyecto)])
                if len(ids_pres_proyecto) == 0:
                    id_pres_proyecto = pres_proyecto_obj.create(cr, uid, {'programa_id': id_pres_programa, 'proyecto': proyecto})
                else:
                    id_pres_proyecto = ids_pres_proyecto[0]

                #cargo tabla moneda
                moneda = linea.moneda
                ids_pres_moneda = pres_moneda_obj.search(cr, uid, [('proyecto_id','=', id_pres_proyecto),('moneda','=',moneda)])
                if len(ids_pres_moneda) == 0:
                    id_pres_moneda = pres_moneda_obj.create(cr, uid, {'proyecto_id': id_pres_proyecto, 'moneda': moneda})
                else:
                    id_pres_moneda = ids_pres_moneda[0]

                #cargo tabla tipo credito
                tc = linea.tipo_credito
                ids_pres_tc = pres_tc_obj.search(cr, uid, [('moneda_id','=', id_pres_moneda),('tc','=',tc)])
                if len(ids_pres_tc) == 0:
                    id_pres_tc = pres_tc_obj.create(cr, uid, {'moneda_id': id_pres_moneda, 'tc': tc})
                else:
                    id_pres_tc = ids_pres_tc[0]
        return True

    def cron_refrescar_ajustes_siif(self, cr, uid, context=None):
        #Cron para refrescar los ajuste de SIIF
        #busca todos los presupuestos activos y llama al metodo refrescar_ajustes_siif
        presupuesto_ids = self.search(cr, uid, [], context=context)
        for presupuesto_id in presupuesto_ids:
            self.refrescar_ajustes_siif(cr, uid, [presupuesto_id], context=context)
        return True


presupuesto_presupuesto()
