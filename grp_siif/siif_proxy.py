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

from lxml import etree
from openerp import models, api
from openerp.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class siif_proxy(models.AbstractModel):
    _name = 'siif.proxy'
    _inherit = 'siif.proxy.factory'

    @api.model
    def priorizadas(self, anioFiscal, inciso, fecha_desde, fecha_hasta):
        """
        @param anioFiscal: Integer
        @param inciso: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: getPriorizadas')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('priorizadasRequest')
            params['anioFiscal'] = anioFiscal
            params['inciso'] = inciso
            params['fechaDesde'] = fecha_desde
            params['fechaHasta'] = fecha_hasta
            # Invocación del servicio
            res = self.proxy.service.getPriorizadas(params)
            if res.codResultado == 0 and 'lineas' in res:
                return res.lineas
            else:
                return []
                # raise ValidationError('Error al intentar obtener priorizaciones')
        else:
            # Se formatean las fechas porque se envian con el formato yyyymmdd
            fecha_desde = fecha_desde[0:4] + fecha_desde[5:7] + fecha_desde[8:10]
            fecha_hasta = fecha_hasta[0:4] + fecha_hasta[5:7] + fecha_hasta[8:10]
            res = self.proxy.service.getPriorizadas(anioFiscal, inciso, fecha_desde, fecha_hasta)
            if res.codResultado == 0 and 'arrLineasPriorizadas' in res:
                return res.arrLineasPriorizadas
            else:
                return []
                # raise ValidationError('Error al intentar obtener priorizaciones')

    @api.model
    def obtener_priorizadas(self, anio_fiscal, inciso, fecha_desde, fecha_hasta):
        """
        @param anioFiscal: Integer
        @param inciso: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        return self.priorizadas(anio_fiscal, inciso, fecha_desde, fecha_hasta)

    @api.model
    def intervenidas(self, anioFiscal, inciso, fecha_desde, fecha_hasta):
        """
        @param anioFiscal: Integer
        @param inciso: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: getIntervenidas')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('intervenidasRequest')
            params['anioFiscal'] = anioFiscal
            params['inciso'] = inciso
            params['fechaDesde'] = fecha_desde
            params['fechaHasta'] = fecha_hasta
            # Invocación del servicio
            res = self.proxy.service.getIntervenidas(params)
            if res.codResultado == 0 and 'lineas' in res:
                return res.lineas
            else:
                return []
                # raise ValidationError('Error al intentar obtener intervenciones')
        else:
            # Se formatean las fechas porque se envian con el formato yyyymmdd
            fecha_desde = fecha_desde[0:4] + fecha_desde[5:7] + fecha_desde[8:10]
            fecha_hasta = fecha_hasta[0:4] + fecha_hasta[5:7] + fecha_hasta[8:10]
            res = self.proxy.service.getIntervenidas(anioFiscal, inciso, fecha_desde, fecha_hasta)
            if res.codResultado == 0 and 'arrLineasIntervenidas' in res:
                return res.arrLineasIntervenidas
            else:
                return []
                # raise ValidationError('Error al intentar obtener intervenciones')

    @api.model
    def obtener_intervenidas(self, anio_fiscal, inciso, fecha_desde, fecha_hasta):
        """
        @param anioFiscal: Integer
        @param inciso: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        return self.intervenidas(anio_fiscal, inciso, fecha_desde, fecha_hasta)

    @api.model
    def facturas_pagas(self, anioFiscal, inciso, fecha_desde_yyyymmdd, fecha_hasta_yyyymmdd):
        """
        @param anioFiscal: Integer
        @param inciso: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=True)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: getFacturasPagas')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('facturasPagasRequest')
            params['anioFiscal'] = anioFiscal
            params['inciso'] = inciso
            params['fechaDesde'] = fecha_desde_yyyymmdd
            params['fechaHasta'] = fecha_hasta_yyyymmdd
            # Invocación del servicio
            return self.proxy.service.getFacturasPagas(params)
        else:
            return self.proxy.service.getFacturasPagas(anioFiscal, inciso, fecha_desde_yyyymmdd, fecha_hasta_yyyymmdd)

    @api.model
    def obtener_pagas(self, anio_fiscal, inciso, fecha_desde, fecha_hasta):
        """
        @param anioFiscal: Integer
        @param inciso: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        return self.facturas_pagas(anio_fiscal, inciso, fecha_desde, fecha_hasta)

    @api.model
    def facturas_pagas_totalmente(self, anioFiscal, inciso, fecha_desde, fecha_hasta):
        """
        @param anioFiscal: Integer
        @param inciso: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: getFacturasPagasTotalmente')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('facturasPagasTotalmenteRequest')
            params['anioFiscal'] = anioFiscal
            params['inciso'] = inciso
            params['fechaDesde'] = fecha_desde
            params['fechaHasta'] = fecha_hasta
            # Invocación del servicio
            res = self.proxy.service.getFacturasPagasTotalmente(params)
            if res.codResultado == 0 and 'lineas' in res:
                return res.lineas
            else:
                return []
        else:
            # Se formatean las fechas porque se envian con el formato yyyymmdd
            fecha_desde = fecha_desde[0:4] + fecha_desde[5:7] + fecha_desde[8:10]
            fecha_hasta = fecha_hasta[0:4] + fecha_hasta[5:7] + fecha_hasta[8:10]
            res = self.proxy.service.getFacturasPagasTotalmente(anioFiscal, inciso, fecha_desde, fecha_hasta)
            if res.codResultado == 0 and 'arrLineasFacturasPagasTotalmente' in res:
                return res.arrLineasFacturasPagasTotalmente
            else:
                return []
                # raise ValidationError('Error al intentar obtener intervenciones')

    @api.model
    def obtener_pagas_totalmente(self, anio_fiscal, inciso, fecha_desde, fecha_hasta):
        """
        @param anioFiscal: Integer
        @param inciso: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        return self.facturas_pagas_totalmente(anio_fiscal, inciso, fecha_desde, fecha_hasta)

    @api.model
    def carga_inicial(self, presupuesto_anio, presupuesto_inciso):
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, raise_exception=True, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: getCargaInicial')
            return False
        #Si es con el webservice pge
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('cargaInicialRequest')
            params['anioFiscal'] = presupuesto_anio
            params['inciso'] = presupuesto_inciso
            res = self.proxy.service.getCargaInicial(params) #lista
            if res.codResultado == 0 and 'lineas' in res:
                return res.lineas
            else:
                return []
                # raise ValidationError('Error al intentar obtener carga inicial del presupuesto')
        else:
            res = self.proxy.service.getCargaInicial(presupuesto_anio, presupuesto_inciso) #lista
            if res.codResultado == 0 and 'arrLineas' in res:
                return res.arrLineas
            else:
                return []
                # raise ValidationError('Error al intentar obtener carga inicial del presupuesto')

    @api.model
    def carga_inicial_y_ajuste(self, presupuesto_anio, presupuesto_inciso, fecha_desde, fecha_hasta):
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, raise_exception=True, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: getCargaInicialYAjustes')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('cargaInicialYAjustesRequest')
            params['anioFiscal'] = presupuesto_anio
            params['inciso'] = presupuesto_inciso
            params['fechaDesde'] = fecha_desde
            params['fechaHasta'] = fecha_hasta
            # Invocación del servicio
            res = self.proxy.service.getCargaInicialYAjustes(params) #lista
            if res.codResultado == 0 and 'lineas' in res:
                return res.lineas
            else:
                return []
                # raise ValidationError('Error al intentar obtener carga inicial del presupuesto')
        else:
            #Se formatean las fechas porque se envian con el formato yyyymmdd
            fecha_desde = fecha_desde[0:4] + fecha_desde[5:7] + fecha_desde[8:10]
            fecha_hasta = fecha_hasta[0:4] + fecha_hasta[5:7] + fecha_hasta[8:10]
            res = self.proxy.service.getCargaInicialYAjustes(presupuesto_anio, presupuesto_inciso, fecha_desde, fecha_hasta) #lista
            if res.codResultado == 0 and 'arrLineasCIyAjustes' in res:
                return res.arrLineasCIyAjustes
            else:
                return []
                # raise ValidationError('Error al intentar obtener carga inicial del presupuesto')

    @api.model
    def conciliacion(self, anioFiscal, inciso, fecha_desde_yyyymmdd, fecha_hasta_yyyymmdd, tipo):
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: getConciliacion')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('conciliacionRequest')
            params['anioFiscal'] = anioFiscal
            params['inciso'] = inciso
            params['fechaDesde'] = fecha_desde_yyyymmdd
            params['fechaHasta'] = fecha_hasta_yyyymmdd
            params['tipo'] = tipo
            # Invocación del servicio
            return self.proxy.service.getConciliacion(params)
        else:
            return self.proxy.service.getConciliacion(anioFiscal, inciso, fecha_desde_yyyymmdd, fecha_hasta_yyyymmdd, tipo)

    @api.model
    def conciliacion_ctas_financieras(self, codigosIrDesde, codigosIrHasta, financiamiento, inciso, unidadEjecutora, fecha_desde_yyyymmdd, fecha_hasta_yyyymmdd):
        """
        @param codigosIrDesde: Integer
        @param codigosIrHasta: Integer
        @param financiamiento: Integer
        @param inciso: Integer
        @param unidadEjecutora: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: getConciliacionCtasFinancieras')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('conciliacionCtasFinancierasRequest')
            params['codigosIrDesde'] = codigosIrDesde
            params['codigosIrHasta'] = codigosIrHasta
            params['financiamiento'] = financiamiento
            params['inciso'] = inciso
            params['unidadEjecutora'] = unidadEjecutora
            params['fechaDesde'] = fecha_desde_yyyymmdd
            params['fechaHasta'] = fecha_hasta_yyyymmdd
            # Invocación del servicio
            return self.proxy.service.getConciliacionCtasFinancieras(params)
        else:
            return self.proxy.service.getConciliacionCtasFinancieras(codigosIrDesde, codigosIrHasta, financiamiento, inciso, unidadEjecutora, fecha_desde_yyyymmdd, fecha_hasta_yyyymmdd)

    @api.model
    def modificaciones_presupuestales(self, anioFiscal, inciso, fecha_desde_yyyymmdd, fecha_hasta_yyyymmdd):
        """
        @param anioFiscal: Integer
        @param inciso: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: getModificacionesPresupuestales')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('modificacionesPresupuestalesRequest')
            params['anioFiscal'] = anioFiscal
            params['inciso'] = inciso
            params['fechaDesde'] = fecha_desde_yyyymmdd
            params['fechaHasta'] = fecha_hasta_yyyymmdd
            # Invocación del servicio
            return self.proxy.service.getModificacionesPresupuestales(params)
        else:
            return self.proxy.service.getModificacionesPresupuestales(anioFiscal, inciso, fecha_desde_yyyymmdd, fecha_hasta_yyyymmdd)

    @api.model
    def solic_status(self, solicXML):
        """
        @param solicXML: String. Opcional
        """
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=True)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: getSolicStatus')
            return False
        return self.proxy.service.getSolicStatus(solicXML) #res

    @api.model
    def estado_solicitud(self, solicXML):
        """
        @param solicXML: String. Opcional
        """
        return self.solic_status(solicXML)

    @api.model
    def obtener_afe_com_obl_por_ue(self, anio, inciso, unidadEjecutora, fecha_desde_yyyymmdd, fecha_hasta_yyyymmdd, procesoGenObl):
        """
        @param anio: Integer
        @param inciso: Integer
        @param unidadEjecutora: Integer
        @param fechaDesde: Date (yyyymmdd)
        @param fechaHasta: Date (yyyymmdd)
        """
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: obtenerAfeComOblPorUE')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('afeComOblPorUERequest')
            params['anio'] = anio
            params['inciso'] = inciso
            params['unidadEjecutora'] = unidadEjecutora
            params['fechaDesde'] = fecha_desde_yyyymmdd
            params['fechaHasta'] = fecha_hasta_yyyymmdd
            params['procesoGenObl'] = procesoGenObl
            # Invocación del servicio
            return self.proxy.service.obtenerAfeComOblPorUE(params)
        else:
            return self.proxy.service.obtenerAfeComOblPorUE(anio, inciso, unidadEjecutora, fecha_desde_yyyymmdd, fecha_hasta_yyyymmdd, procesoGenObl)

    @api.model
    def obtener_cuentas_bancarias_por_benef(self, claseId, ruc):
        """
        @param claseId: Char
        @param ruc: Char
        """
        self.get_proxy(retornaXML=False, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: obtenerCuentasBancariasPorBenef')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('beneficiarioRequest')
            params['claseId'] = claseId
            params['ruc'] = ruc
            # Invocación del servicio
            return self.proxy.service.obtenerCuentasBancariasPorBenef(params)
        else:
            return self.proxy.service.obtenerCuentasBancariasPorBenef(claseId, ruc)

    @api.model
    def obtener_motivo_interv_obligacion(self, anio, inciso, unidadEjecutora, nroDocAfectacion, nroDocCompromiso, nroDocObligacion, secObligacion):
        """
        @param anio: Integer
        @param inciso: Integer
        @param unidadEjecutora: Integer
        @param nroDocAfectacion: Integer
        @param nroDocCompromiso: Integer
        @param nroDocObligacion: Integer
        @param secObligacion: Integer
        """
        self.get_proxy(retornaXML=False, raise_exception=True, check_wsdl=False)
        # Establecer la conexión con SIIF
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: obtenerMotivoIntervObligacion')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('obligacionRequest')
            params['anio'] = anio
            params['inciso'] = inciso
            params['unidadEjecutora'] = unidadEjecutora
            params['nroDocAfectacion'] = nroDocAfectacion
            params['nroDocCompromiso'] = nroDocCompromiso
            params['nroDocObligacion'] = nroDocObligacion
            params['secObligacion'] = secObligacion
            # Invocación del servicio
            return self.proxy.service.obtenerMotivoIntervObligacion(params)
        else:
            return self.proxy.service.obtenerMotivoIntervObligacion(anio, inciso, unidadEjecutora, nroDocAfectacion, nroDocCompromiso, nroDocObligacion, secObligacion)

    @api.model
    def get_intervenciones(self, anio, inciso, ue, doc_afectacion, doc_compromiso, doc_obligacion, sec_obligacion):
        """
        @param anio: Integer
        @param inciso: Integer
        @param ue: Integer
        @param doc_afectacion: Integer
        @param doc_compromiso: Integer
        @param doc_obligacion: Integer
        @param sec_obligacion: Integer
        """
        return self.obtener_motivo_interv_obligacion(anio, inciso, ue, doc_afectacion, doc_compromiso, doc_obligacion, sec_obligacion)

    @api.model
    def obtener_nro_lote_obligacion(self, anio, inciso, unidadEjecutora, nroDocAfectacion, nroDocCompromiso, nroDocObligacion, secObligacion):
        """
        @param anio: Integer
        @param inciso: Integer
        @param unidadEjecutora: Integer
        @param nroDocAfectacion: Integer
        @param nroDocCompromiso: Integer
        @param nroDocObligacion: Integer
        @param secObligacion: Integer
        """
        self.get_proxy(retornaXML=False, raise_exception=True, check_wsdl=False)
        # Establecer la conexión con SIIF
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: obtenerNroLoteObligacion')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('obligacionRequest')
            params['anio'] = anio
            params['inciso'] = inciso
            params['unidadEjecutora'] = unidadEjecutora
            params['nroDocAfectacion'] = nroDocAfectacion
            params['nroDocCompromiso'] = nroDocCompromiso
            params['nroDocObligacion'] = nroDocObligacion
            params['secObligacion'] = secObligacion
            # Invocación del servicio
            return self.proxy.service.obtenerNroLoteObligacion(params)
        else:
            return self.proxy.service.obtenerNroLoteObligacion(anio, inciso, unidadEjecutora, nroDocAfectacion, nroDocCompromiso, nroDocObligacion, secObligacion)

    @api.model
    def obtener_pagos_entregados_por_obl(self, anio, inciso, unidadEjecutora, nroDocAfectacion, nroDocCompromiso, nroDocObligacion, secObligacion):
        """
        @param anio: Integer
        @param inciso: Integer
        @param unidadEjecutora: Integer
        @param nroDocAfectacion: Integer
        @param nroDocCompromiso: Integer
        @param nroDocObligacion: Integer
        @param secObligacion: Integer
        """
        self.get_proxy(retornaXML=False, raise_exception=True, check_wsdl=False)
        # Establecer la conexión con SIIF
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: obtenerPagosEntregadosPorObl')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('obligacionRequest')
            params['anio'] = anio
            params['inciso'] = inciso
            params['unidadEjecutora'] = unidadEjecutora
            params['nroDocAfectacion'] = nroDocAfectacion
            params['nroDocCompromiso'] = nroDocCompromiso
            params['nroDocObligacion'] = nroDocObligacion
            params['secObligacion'] = secObligacion
            # Invocación del servicio
            return self.proxy.service.obtenerPagosEntregadosPorObl(params)
        else:
            return self.proxy.service.obtenerPagosEntregadosPorObl(anio, inciso, unidadEjecutora, nroDocAfectacion, nroDocCompromiso, nroDocObligacion, secObligacion)

    @api.model
    def obtener_tasa_cambio_por_moneda(self, moneda, fecha):
        """
        @param moneda: Integer
        @param fecha: Date
        """
        self.get_proxy(retornaXML=False, raise_exception=True, check_wsdl=False)
        # Establecer la conexión con SIIF
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: obtenerTasaCambioPorMoneda')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('tasaCambioRequest')
            params['moneda'] = moneda
            params['fecha'] = fecha
            # Invocación del servicio
            return self.proxy.service.obtenerTasaCambioPorMoneda(params)
        else:
            return self.proxy.service.obtenerTasaCambioPorMoneda(moneda, fecha)

    @api.model
    def priorizar(self, anio, inciso, unidadEjecutora, nroDocAfectacion, nroDocCompromiso, nroDocObligacion, secObligacion, anioPriorizacion, mesPriorizacion, claseId, ruc, tipoPriorizacion, montoPriorizado):
        """
        @param anio: Integer
        @param inciso: Integer
        @param unidadEjecutora: Integer
        @param nroDocAfectacion: Integer
        @param nroDocCompromiso: Integer
        @param nroDocObligacion: Integer
        @param secObligacion: Integer
        @param anioPriorizacion: Integer
        @param mesPriorizacion: Integer
        @param claseId: Char
        @param ruc: Char
        @param tipoPriorizacion: Tipo
        @param montoPriorizado: Float
        """
        self.get_proxy(retornaXML=False, raise_exception=True, check_wsdl=False)
        # Establecer la conexión con SIIF
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: priorizar')
            return False
        if not self.local_wsdl:
            # Construcción del parámetro request
            params = self.proxy.factory.create('priorizacionRequest')
            params['anio'] = anio
            params['inciso'] = inciso
            params['unidadEjecutora'] = unidadEjecutora
            params['nroDocAfectacion'] = nroDocAfectacion
            params['nroDocCompromiso'] = nroDocCompromiso
            params['nroDocObligacion'] = nroDocObligacion
            params['secObligacion'] = secObligacion
            params['anioPriorizacion'] = anioPriorizacion
            params['mesPriorizacion'] = mesPriorizacion
            params['ruc'] = ruc
            params['tipoPriorizacion'] = tipoPriorizacion
            params['montoPriorizado'] = montoPriorizado
            return self.proxy.service.priorizar(params)
        else:
            return self.proxy.service.priorizar(anio, inciso, unidadEjecutora, nroDocAfectacion, nroDocCompromiso, nroDocObligacion, secObligacion, anioPriorizacion, mesPriorizacion, claseId, ruc, tipoPriorizacion, montoPriorizado)

    @api.model
    def put_solic(self, xmlData):
        self.get_proxy(retornaXML=True, unverified_context=self.sudo().env.user.company_id.unverified_context, check_wsdl=False)
        if not self.proxy:
            _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio. No se hace la llamada a: putSolic')
            return False
        _logger.info("lo que envia a SIIF es: %s", xmlData)
        res = self.proxy.service.putSolic(xmlData)
        self.validar_resultado(res)
        return res

    #MVARELA 19-01-2015: Nueva validacion generica del resultado que devuelve SIIF
    @api.model
    def validar_resultado(self, resultado):
        _logger.info("el resultado es: %s", str(resultado))
        if not resultado or len(resultado.strip()) == 0:
            raise ValidationError('No se obtuvo respuesta del SIIF, vuelva a intentarlo.')

        xml_root = etree.fromstring(resultado)

        str_xml_list = xml_root.xpath("//*[local-name()='return']")
        if len(str_xml_list) == 0:
            raise ValidationError('No se obtuvo respuesta del SIIF, vuelva a intentarlo.')

        str_xml = str_xml_list[0].text

        if str_xml.find('?>') != -1:
            str_xml = str_xml.split('?>')[1]
        xml_root = etree.fromstring(str_xml)

        #Si el resultado es error, lo muestro en la aplicacion
        if xml_root.tag == "msgErrorWS":
            raise ValidationError('Error al enviar a SIIF\n %s' % (xml_root.find('comentario').text or 'Error no especificado por el SIIF',))

        for error_ws in xml_root.findall('msgErrorWS'):
            raise ValidationError('Error al enviar a SIIF\n %s' % (error_ws.find('comentario').text or 'Error no especificado por el SIIF',))

        descr_error = ''
        error = False
        for movimiento in xml_root.findall('movimiento'):
            if movimiento.find('resultado').text == 'E' or (movimiento.find('resultado').text and len(movimiento.find('resultado').text) > 5 and  movimiento.find('resultado').text[-1] == 'E'):
                error = True
                if movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    if not descr_error:
                        descr_error +=  movimiento.find('comentario').text
                    else:
                        descr_error += ", " + movimiento.find('comentario').text
        if error:
            raise ValidationError('Error al enviar a SIIF\n %s' % (descr_error or 'Error no especificado por el SIIF',))
        else:
            return True

    # Servicios web SIIF a través de Conector PGE
    # -------------------------------------------------------------------------------------------------------------
    # def conectar_siif(self, cr, uid, retornaXML=False):
    #     """
    #     Establece la conexión con el WS y crea el objeto SOAP cliente de dicha conexión.
    #     """
    #     # Obtener la URL de parámetros del sistema
    #     url_siif = self.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.siif')

    #     if not url_siif:
    #         raise osv.except_osv('Error!',
    #                              u'No se encuentra configurada la ruta del WSDL para consumir los servicios SiiF')
    #     # Establecer la conexión
    #     try:
    #         self.client = Client(url_siif, cache=None, retxml=retornaXML)
    #         _logger.info("Client SiiF: %s", self.client)
    #     except Exception as e:
    #         return False
    #     return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
