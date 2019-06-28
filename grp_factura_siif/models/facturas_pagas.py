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
import time
from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)


class grp_integracion_pagas_busqueda(osv.osv):
    _name = 'grp.integracion.pagas.busqueda'
    _columns = {
        'create_date': fields.datetime(u'Fecha de creación'),
        'anio_fiscal': fields.char(u'Año fiscal', size=4),
        'inciso': fields.integer(u'Inciso', size=3),
        'fecha_desde': fields.date(u'Fecha desde'),
        'fecha_hasta': fields.date(u'Fecha hasta'),
        'facturas_ids': fields.one2many('grp.integracion.pagas', 'id_busqueda'),
    }

    _defaults = {
        'anio_fiscal': lambda *a: time.strftime('%Y'),
    }

    # def grp_integracion_pagas_buscar(self, cr, uid, ids, context=None):
    #     # consultar ws pagas y antes de mostrar, asociar los documentos de GRP
    #     account_invoice_obj = self.pool.get('account.invoice')
    #     siif_proxy = self.pool.get('siif.proxy')
    #     data = self.read(cr, uid, ids, [], context=context)
    #     fecha_desde = data[0]['fecha_desde'].replace('-', '')
    #     fecha_hasta = data[0]['fecha_hasta'].replace('-', '')
    #     anio_fiscal = data[0]['anio_fiscal']
    #     inciso = data[0]['inciso']
    #
    #     consulta_res = siif_proxy.obtener_pagas(anio_fiscal=anio_fiscal, inciso=inciso,
    #                                        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    #
    #     pagas_obj = self.pool.get('grp.integracion.pagas')
    #     _logger.info(consulta_res)
    #     for paga in consulta_res[0]:
    #         dict_create_paga = {}
    #         dict_create_paga['id_busqueda'] = ids[0]
    #         dict_create_paga['anio_fiscal'] = paga.anioFiscal
    #         dict_create_paga['auxiliar'] = paga.auxiliar
    #         dict_create_paga['fecha_aprobado'] = paga.fechaAprobado
    #         dict_create_paga['financiamiento'] = paga.financiamiento
    #         dict_create_paga['importe'] = paga.importe
    #         dict_create_paga['inciso'] = paga.inciso
    #         dict_create_paga['moneda'] = paga.moneda
    #         dict_create_paga['num_doc_afectacion'] = paga.nroDocAfectacion
    #         dict_create_paga['num_doc_compromiso'] = paga.nroDocCompromiso
    #         dict_create_paga['num_doc_obligacion'] = paga.nroDocObligacion
    #         dict_create_paga['objeto_gasto'] = paga.objetoDelGasto
    #         dict_create_paga['programa'] = paga.programa
    #         dict_create_paga['proyecto'] = paga.proyecto
    #         dict_create_paga['tipo_credito'] = paga.tipoDeCredito
    #         dict_create_paga['unidad_ejecutora'] = paga.unidadEjecutora
    #
    #         condiciones_factura = []
    #         condiciones_factura.append(('nro_afectacion', '=', paga.nroDocAfectacion))
    #         condiciones_factura.append(('nro_compromiso', '=', paga.nroDocCompromiso))
    #         condiciones_factura.append(('nro_obligacion', '=', paga.nroDocObligacion))
    #         #TODO: Revisar directo contra el año fiscal, aplicar tambien en otros servicios
    #         condiciones_factura.append(('date_invoice', 'like', str(paga.anioFiscal) + '%'))
    #
    #         ids_facturas = account_invoice_obj.search(cr, uid, condiciones_factura, context=context)
    #         if len(ids_facturas) > 0:
    #             _logger.info("encontro: %s", ids_facturas)
    #             dict_create_paga['factura_grp_id'] = ids_facturas[0]
    #
    #
    #         pagas_obj.create(cr, uid, dict_create_paga, context=context)
    #     return True


grp_integracion_pagas_busqueda()


class grp_integracion_pagas(osv.osv):
    _name = 'grp.integracion.pagas'
    _columns = {
        'id_busqueda': fields.many2one('grp.integracion.pagas.busqueda', u'Id Busqueda'),
        'anio_fiscal': fields.integer(u'Año fiscal', readonly=True),
        'auxiliar': fields.integer(u'Auxiliar', readonly=True),
        'fecha_aprobado': fields.date(u'Fecha aprobado', readonly=True),
        'financiamiento': fields.integer(u'Financiamiento', readonly=True),
        'importe': fields.integer(u'Importe', readonly=True),
        'inciso': fields.integer(u'Inciso', readonly=True),
        'moneda': fields.integer(u'Moneda', readonly=True),
        'num_doc_afectacion': fields.integer(u'Número documento afectación', readonly=True),
        'num_doc_compromiso': fields.integer(u'Número documento compromiso', readonly=True),
        'num_doc_obligacion': fields.integer(u'Número documento obligación', readonly=True),
        'objeto_gasto': fields.integer(u'Objeto del gasto', readonly=True),
        'programa': fields.integer(u'Programa', readonly=True),
        'proyecto': fields.integer(u'Proyecto', readonly=True),
        'tipo_credito': fields.integer(u'Tipo de crédito', readonly=True),
        'unidad_ejecutora': fields.integer(u'Unidad ejecutora', readonly=True),
        'factura_grp_id': fields.many2one('account.invoice', u'Nro factura GRP'),
        'state': fields.selection((('pendant', 'Sin procesar'), ('processed', 'Procesado'), ('error', 'Error')), 'Estado', readonly=True),
        'resultado': fields.text(u"Resultado"),
    }

    def actualizar_pagas(self, cr, uid, context=None):
        fecha_hoy = fields.date.context_today(self,cr,uid,context=context)
        _logger.info("Ejecutando cron de actualizar facturas pagas: %s", fecha_hoy)
        presupuesto_obj = self.pool.get("presupuesto.presupuesto")

        fecha_desde = fecha_hoy.split('-')[0] + '0101' #1 de enero del año actual
        fecha_hasta = fecha_hoy.replace('-', '')
        anio_fiscal = fecha_hoy.split('-')[0]
        mes_ejecucion = int(fecha_hoy[5:7])
        #Se llama 2 veces, una con el año anterior porque en enero/febrero cargan para el anio fiscal anterior
        # ademas se llama por cada inciso del año fiscal. se buscan los presupuestos de ese año y se obtienen los incisos
        if mes_ejecucion <= 3:
            anio_anterior = str(int(anio_fiscal) - 1)
            presupuestos_anio_ant_ids = presupuesto_obj.search(cr, uid, [('fiscal_year.code','=',anio_anterior)], context=context)
            for pres_ant in presupuesto_obj.browse(cr, uid, presupuestos_anio_ant_ids, context=context):
                self.actualizar_pagas_aux(cr, uid, anio_anterior, pres_ant.inciso, fecha_desde, fecha_hasta, context)

        presupuestos_anio_actual_ids = presupuesto_obj.search(cr, uid, [('fiscal_year.code', '=', anio_fiscal)], context=context)
        for pres_actual in presupuesto_obj.browse(cr, uid, presupuestos_anio_actual_ids, context=context):
            self.actualizar_pagas_aux(cr, uid, anio_fiscal, pres_actual.inciso, fecha_desde, fecha_hasta, context)
        return True

    def actualizar_pagas_aux(self, cr, uid, anio_fiscal, inciso, fecha_desde, fecha_hasta, context=None):

        _logger.info("Actualizar facturas pagas: %s", fecha_hasta)
        account_invoice_obj = self.pool.get('account.invoice')
        siif_proxy = self.pool.get('siif.proxy')

        diarios_pagos_conf_obj = self.pool.get('grp.diarios.pagos.config')

        consulta_res = siif_proxy.obtener_pagas(cr, uid, anio_fiscal=anio_fiscal, inciso=inciso,
                                           fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)

        for paga in consulta_res[0]:
            _logger.info(paga)

            condiciones_log = []
            condiciones_log.append(('num_doc_afectacion', '=', paga.nroDocAfectacion))
            condiciones_log.append(('num_doc_compromiso', '=', paga.nroDocCompromiso))
            condiciones_log.append(('num_doc_obligacion', '=', paga.nroDocObligacion))
            condiciones_log.append(('anio_fiscal', '=', paga.anioFiscal))
            #se comparan todos los campos, hay que ver que pasa si mandan 2 veces lo mismo
            condiciones_log.append(('auxiliar', '=', paga.auxiliar))
            condiciones_log.append(('fecha_aprobado', '=', paga.fechaAprobado))
            condiciones_log.append(('financiamiento', '=', paga.financiamiento))
            condiciones_log.append(('importe', '=', paga.importe))
            condiciones_log.append(('inciso', '=', paga.inciso))
            condiciones_log.append(('moneda', '=', paga.moneda))
            condiciones_log.append(('objeto_gasto', '=', paga.objetoDelGasto))
            condiciones_log.append(('programa', '=', paga.programa))
            condiciones_log.append(('proyecto', '=', paga.proyecto))
            condiciones_log.append(('tipo_credito', '=', paga.tipoDeCredito))
            condiciones_log.append(('unidad_ejecutora', '=', paga.unidadEjecutora))

            _logger.info("condiciones_log: %s", condiciones_log)

            condiciones_factura = []
            condiciones_factura.append(('nro_afectacion', '=', paga.nroDocAfectacion))
            condiciones_factura.append(('nro_compromiso', '=', paga.nroDocCompromiso))
            condiciones_factura.append(('nro_obligacion', '=', paga.nroDocObligacion))
            condiciones_factura.append(('fiscalyear_siif_id.code', '=', str(paga.anioFiscal)))
            condiciones_factura.append(('ue_siif_id.ue', '=', str(paga.unidadEjecutora).zfill(3)))
            condiciones_factura.append(('inciso_siif_id.inciso', '=', str(paga.inciso).zfill(2)))
            condiciones_factura.append(('doc_type','!=','ajuste_invoice'))

            _logger.info("condiciones_factura: %s", condiciones_factura)

            #Busco en la tabla de log si ya se cargo el registro
            ids_pagas = self.search(cr, uid, condiciones_log, context=context)
            if len(ids_pagas) > 0:
                _logger.info("este registro ya fue ingresado")
            #Si no se cargo verifico que existe una factura asociada a los datos
            else:
                ids_facturas = account_invoice_obj.search(cr, uid, condiciones_factura, context=context)
                vals = {}
                vals['anio_fiscal'] = paga.anioFiscal
                vals['auxiliar'] = paga.auxiliar
                vals['fecha_aprobado'] = paga.fechaAprobado
                vals['financiamiento'] = paga.financiamiento
                vals['importe'] = paga.importe
                vals['inciso'] = paga.inciso
                vals['moneda'] = paga.moneda
                vals['num_doc_afectacion'] = paga.nroDocAfectacion
                vals['num_doc_compromiso'] = paga.nroDocCompromiso
                vals['num_doc_obligacion'] = paga.nroDocObligacion
                vals['objeto_gasto'] = paga.objetoDelGasto
                vals['programa'] = paga.programa
                vals['proyecto'] = paga.proyecto
                vals['tipo_credito'] = paga.tipoDeCredito
                vals['unidad_ejecutora'] = paga.unidadEjecutora

                if len(ids_facturas) > 0:
                    _logger.info("encontro: %s", ids_facturas)
                    vals['factura_grp_id'] = ids_facturas[0]
                    factura = account_invoice_obj.browse(cr, uid, ids_facturas[0])

                    #001-Buscar diario
                    conf_pagos_ids = diarios_pagos_conf_obj.search(cr, uid, [('siif_concepto_gasto_id','=',factura.siif_concepto_gasto.id),
                                                                             ('siif_tipo_ejecucion_id','=',factura.siif_tipo_ejecucion.id),
                                                                             ('siif_codigo_sir', '=', factura.siif_codigo_sir.id),
                                                                             ('company_id','=',factura.company_id.id)])
                    journal_id = False
                    if len(conf_pagos_ids) > 0:
                        journl_conf = diarios_pagos_conf_obj.read(cr, uid, conf_pagos_ids[0],['journal_id'])
                        journal_id = journl_conf['journal_id']

                    if not journal_id:
                        raise osv.except_osv(('Error'),
                                     (u'No se encontró diario configurado para el Tipo de Ejecución %s y Concepto del Gasto %s.', (factura.siif_tipo_ejecucion.name,factura.siif_concepto_gasto.name)))

                    if factura.siif_tipo_ejecucion.codigo == 'P':
                        vals['state'] = 'processed'
                        vals['resultado'] = 'El tipo de ejecucion del documento es P, no se hace nada'
                    elif factura.state not in ['forced','open','intervened','prioritized']:
                        vals['state'] = 'error'
                        estado = dict(account_invoice_obj.fields_get(cr, uid, allfields=['state'], context=context)['state']['selection'])[factura.state]
                        vals['resultado'] = 'La documento debe estar en uno de los siguientes etados: Obligado, Abierto, Intervenida, Priorizada. El estado es: ' + estado
                    else:
                        vals['state'] = 'processed'
                        vals['resultado'] = 'Procesada, se paga el documento'
                        #Llamar a pagar
                        account_invoice_obj.automatic_pay_invoice_aux(cr, uid, factura.id, journal_id=journal_id, amount=vals['importe'], date=vals['fecha_enviado'])

                    self.create(cr, uid, vals, context)

                else:
                    _logger.info("no existe factura para los datos del registro")
                    vals['state'] = 'error'
                    vals['resultado'] = 'No se encontro factura en GRP correspondiente a este registro'
                    self.create(cr, uid, vals, context)

        return True


grp_integracion_pagas()