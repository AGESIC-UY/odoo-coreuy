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


class grp_integracion_pagas_totalmente_busqueda(osv.osv):
    _name = 'grp.integracion.pagas_totalmente.busqueda'
    _columns = {
        'create_date': fields.datetime(u'Fecha de creación'),
        'anio_fiscal': fields.char(u'Año fiscal', size=4),
        'inciso': fields.integer(u'Inciso', size=3),
        'fecha_desde': fields.date(u'Fecha desde'),
        'fecha_hasta': fields.date(u'Fecha hasta'),
        'facturas_ids': fields.one2many('grp.integracion.pagas_totalmente', 'id_busqueda'),
    }

    _defaults = {
        'anio_fiscal': lambda *a: time.strftime('%Y'),
    }

    # def grp_integracion_pagas_totalmente_buscar(self, cr, uid, ids, context=None):
    #     # consultar ws pagas totalmente y antes de mostrar, asociar los documentos de GRP
    #     account_invoice_obj = self.pool.get('account.invoice')
    #     siif_proxy = self.pool.get('siif.proxy')
    #     data = self.read(cr, uid, ids, [], context=context)
    #     fecha_desde = data[0]['fecha_desde'].replace('-', '')
    #     fecha_hasta = data[0]['fecha_hasta'].replace('-', '')
    #     anio_fiscal = data[0]['anio_fiscal']
    #     inciso = data[0]['inciso']
    #
    #     consulta_res = siif_proxy.obtener_pagas_totalmente(anio_fiscal=anio_fiscal, inciso=inciso,
    #                                        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    #
    #     pagas_totalmente_obj = self.pool.get('grp.integracion.pagas_totalmente')
    #     _logger.info(consulta_res)
    #     for paga in consulta_res[0]:
    #         dict_create_paga = {}
    #         dict_create_paga['id_busqueda'] = ids[0]
    #         dict_create_paga['anio_fiscal'] = paga.anioFiscal
    #         dict_create_paga['clase_id'] = paga.claseId
    #         dict_create_paga['concepto_gasto'] = paga.conceptoDeGasto
    #         dict_create_paga['fecha_enviado'] = paga.fechaEntregaEnviado
    #         dict_create_paga['financiamiento'] = paga.financiamiento
    #         dict_create_paga['inciso'] = paga.inciso
    #         dict_create_paga['num_doc_afectacion'] = paga.nroDocAfectacion
    #         dict_create_paga['num_doc_compromiso'] = paga.nroDocCompromiso
    #         dict_create_paga['num_doc_obligacion'] = paga.nroDocObligacion
    #         dict_create_paga['nro_lote_oblig'] = paga.nroLoteObl
    #         dict_create_paga['ruc'] = paga.ruc
    #         dict_create_paga['tipo_ejecucion'] = paga.tipodeEjecucion
    #         dict_create_paga['unidad_ejecutora'] = paga.unidadEjecutadora
    #
    #         condiciones_factura = []
    #         condiciones_factura.append(('nro_afectacion', '=', paga.nroDocAfectacion))
    #         condiciones_factura.append(('nro_compromiso', '=', paga.nroDocCompromiso))
    #         condiciones_factura.append(('nro_obligacion', '=', paga.nroDocObligacion))
    #         condiciones_factura.append(('date_invoice', 'like', str(paga.anioFiscal) + '%'))
    #
    #         ids_facturas = account_invoice_obj.search(cr, uid, condiciones_factura, context=context)
    #         if len(ids_facturas) > 0:
    #             _logger.info("encontro: %s", ids_facturas)
    #             dict_create_paga['factura_grp_id'] = ids_facturas[0]
    #
    #         pagas_totalmente_obj.create(cr, uid, dict_create_paga, context=context)
    #     return True


grp_integracion_pagas_totalmente_busqueda()


class grp_integracion_pagas_totalmente(osv.osv):
    _name = 'grp.integracion.pagas_totalmente'
    _columns = {
        'id_busqueda': fields.many2one('grp.integracion.pagas_totalmente.busqueda', u'Id Busqueda'),
        'anio_fiscal': fields.integer(u'Año fiscal', readonly=True),
        'clase_id': fields.char(u'Clase ID', readonly=True),
        'concepto_gasto': fields.integer(u'Concepto del gasto', readonly=True),
        'fecha_enviado': fields.date(u'Fecha entrega enviado', readonly=True),
        'financiamiento': fields.integer(u'Financiamiento', readonly=True),
        'inciso': fields.integer(u'Inciso', readonly=True),
        'num_doc_afectacion': fields.integer(u'Número documento afectación', readonly=True),
        'num_doc_compromiso': fields.integer(u'Número documento compromiso', readonly=True),
        'num_doc_obligacion': fields.integer(u'Número documento obligación', readonly=True),
        'nro_lote_oblig': fields.integer(u'Nro de lote obligación', readonly=True),
        'ruc': fields.char(u'Ruc', readonly=True),
        'tipo_ejecucion': fields.char(u'Tipo de ejecución', readonly=True),
        'unidad_ejecutora': fields.integer(u'Unidad ejecutora', readonly=True),
        'factura_grp_id': fields.many2one('account.invoice', u'Nro factura GRP'),
        'state': fields.selection((('pendant', 'Sin procesar'), ('processed', 'Procesado'), ('error', 'Error')), 'Estado', readonly=True),
        'resultado': fields.text(u"Resultado"),
    }

    def actualizar_pagas_totalmente(self, cr, uid, context=None):
        fecha_hasta = fields.date.context_today(self,cr,uid,context=context)
        _logger.info("Ejecutando cron de actualizar facturas pagas totalmente: %s", fecha_hasta)
        presupuesto_obj = self.pool.get("presupuesto.presupuesto")
        fecha_desde = fecha_hasta.split('-')[0] + '-01-01' #1 de enero del año actual
        anio_fiscal = fecha_hasta.split('-')[0]
        mes_ejecucion = int(fecha_hasta[5:7])
        # Se llama 2 veces, una con el año anterior porque en enero/febrero cargan para el anio fiscal anterior
        # ademas se llama por cada inciso del año fiscal. se buscan los presupuestos de ese año y se obtienen los incisos
        if mes_ejecucion <= 3:
            anio_anterior = str(int(anio_fiscal) -1 )
            presupuestos_anio_ant_ids = presupuesto_obj.search(cr, uid, [('fiscal_year.code','=',anio_anterior)], context=context)
            for pres_ant in presupuesto_obj.browse(cr, uid, presupuestos_anio_ant_ids, context=context):
                self.actualizar_pagas_totalmente_aux(cr, uid, anio_anterior, pres_ant.inciso, fecha_desde, fecha_hasta, context)

        presupuestos_anio_actual_ids = presupuesto_obj.search(cr, uid, [('fiscal_year.code', '=', anio_fiscal)], context=context)
        for pres_actual in presupuesto_obj.browse(cr, uid, presupuestos_anio_actual_ids, context=context):
            self.actualizar_pagas_totalmente_aux(cr, uid, anio_fiscal, pres_actual.inciso, fecha_desde, fecha_hasta, context)
        return True


    def failed_paga(self, cr, uid, vals, paga, context=None):
        vals['state'] = 'error'
        vals['resultado'] = u'No se encontró factura en GRP correspondiente a este registro'
        self.create(cr, uid, vals, context=context)


    def success_clearing_intervened(self, cr, uid, vals, clearing, context=None):

        account_invoice_obj = self.pool.get('account.invoice')
        diarios_pagos_conf_obj = self.pool.get('grp.diarios.pagos.config')
        clearing_obj = self.pool.get('regularizacion.clearing')

        vals['resultado'] = 'Procesada, se paga la regularizacion clearing'

        # Se marca Pago de la regularizacion clearing
        clearing_obj.write(cr, uid, [clearing.id], {'papa_tng': True}, context=context)

        # Pago de las facturas de la regularizacion clearing
        condiciones_factura = []
        condiciones_factura.append(('regularizacion_id', '=', clearing.id))
        ids_facturas = account_invoice_obj.search(cr, uid, condiciones_factura, context=context)
        if ids_facturas:
            for factura in account_invoice_obj.browse(cr, uid, ids_facturas, context=context):

                conf_pagos_ids = diarios_pagos_conf_obj.search(cr, uid, [
                    ('siif_concepto_gasto_id', '=', factura.siif_concepto_gasto.id),
                    ('siif_tipo_ejecucion_id', '=', factura.siif_tipo_ejecucion.id),
                    ('siif_codigo_sir', '=', factura.siif_codigo_sir.id),
                    ('company_id', '=', factura.company_id.id)])

                journal_id = False

                if len(conf_pagos_ids) > 0:
                    journl_conf = diarios_pagos_conf_obj.read(cr, uid, conf_pagos_ids[0], ['journal_id'])
                    journal_id = journl_conf['journal_id'][0]

                if not journal_id:
                    raise osv.except_osv(('Error'),
                                         (
                                         u'No se encontró diario configurado para el Tipo de Ejecución %s y Concepto del Gasto %s.',
                                         (factura.siif_tipo_ejecucion.name, factura.siif_concepto_gasto.name)))

                # Llamar a pagar
                account_invoice_obj.automatic_pay_invoice_aux(cr, uid, factura.id, journal_id=journal_id, amount=0.0, date=vals['fecha_enviado'])

        self.create(cr, uid, vals, context=context)


    def actualizar_pagas_totalmente_aux(self, cr, uid, anio_fiscal, inciso, fecha_desde, fecha_hasta, context=None):

        _logger.info("Actualizar facturas pagas totalmente: año fiscal: %s, inciso: %s, fecha_desde: %s, fecha_hasta: %s", anio_fiscal, inciso, fecha_desde, fecha_hasta)
        account_invoice_obj = self.pool.get('account.invoice')
        regularizacion_clearing_obj = self.pool.get('regularizacion.clearing')
        siif_proxy = self.pool.get('siif.proxy')

        #001- Instancia objeto de configuracion
        diarios_pagos_conf_obj = self.pool.get('grp.diarios.pagos.config')

        consulta_res = siif_proxy.obtener_pagas_totalmente(cr, uid, anio_fiscal=anio_fiscal, inciso=inciso,
                                           fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)

        for paga in consulta_res:
            _logger.info(paga)

            condiciones_log = []
            condiciones_log.append(('num_doc_afectacion', '=', paga.nroDocAfectacion))
            condiciones_log.append(('num_doc_compromiso', '=', paga.nroDocCompromiso))
            condiciones_log.append(('num_doc_obligacion', '=', paga.nroDocObligacion))
            condiciones_log.append(('anio_fiscal', '=', paga.anioFiscal))
            condiciones_log.append(('nro_lote_oblig', '=', paga.nroLoteObl))
            condiciones_log.append(('unidad_ejecutora', '=', paga.unidadEjecutadora))
            condiciones_log.append(('inciso', '=', paga.inciso))

            _logger.info("condiciones_log: %s", condiciones_log)

            condiciones_factura = []
            condiciones_factura.append(('nro_afectacion', '=', paga.nroDocAfectacion))
            condiciones_factura.append(('nro_compromiso', '=', paga.nroDocCompromiso))
            condiciones_factura.append(('nro_obligacion', '=', paga.nroDocObligacion))
            condiciones_factura.append(('fiscalyear_siif_id.code', '=', str(paga.anioFiscal)))
            condiciones_factura.append(('ue_siif_id.ue', '=', str(paga.unidadEjecutadora).zfill(3)))
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
                vals['clase_id'] = paga.claseId
                vals['concepto_gasto'] = paga.conceptoDeGasto
                vals['fecha_enviado'] = paga.fechaEntregaEnviado
                vals['financiamiento'] = paga.financiamiento
                vals['inciso'] = paga.inciso
                vals['num_doc_afectacion'] = paga.nroDocAfectacion
                vals['num_doc_compromiso'] = paga.nroDocCompromiso
                vals['num_doc_obligacion'] = paga.nroDocObligacion
                vals['nro_lote_oblig'] = paga.nroLoteObl
                vals['ruc'] = paga.ruc
                vals['tipo_ejecucion'] = paga.tipodeEjecucion
                vals['unidad_ejecutora'] = paga.unidadEjecutadora

                if len(ids_facturas) > 0:
                    _logger.info("encontro: %s", ids_facturas)
                    vals['factura_grp_id'] = ids_facturas[0]
                    factura = account_invoice_obj.browse(cr, uid, ids_facturas[0])

                    if vals['tipo_ejecucion'] == 'P':
                        vals['state'] = 'processed'
                        vals['resultado'] = u'El tipo de ejecucion del documento es P, se marca el flag Obligación Paga por TGN en True'

                        account_invoice_obj.write(cr, uid, factura.id, {'obligacion_paga_tgn':True})

                    elif factura.siif_concepto_gasto.concepto == '1':
                        vals['state'] = 'processed'
                        vals['resultado'] = u'El concepto del gasto es 1 - Remuneraciones, no se hace nada'


                    elif factura.state not in ['forced','open','intervened','prioritized']:
                        vals['state'] = 'error'
                        estado = dict(account_invoice_obj.fields_get(cr, uid, allfields=['state'], context=context)['state']['selection'])[factura.state]
                        vals['resultado'] = 'El documento debe estar en uno de los siguientes estados: Obligado, Abierto, Intervenida, Priorizada. El estado es: ' + estado

                    else:
                        vals['state'] = 'processed'
                        vals['resultado'] = 'Procesada, se paga el documento'
                        # 001-Buscar diario
                        conf_pagos_ids = diarios_pagos_conf_obj.search(cr, uid, [
                            ('siif_concepto_gasto_id', '=', factura.siif_concepto_gasto.id),
                            ('siif_tipo_ejecucion_id', '=', factura.siif_tipo_ejecucion.id),
                            ('siif_codigo_sir', '=', factura.siif_codigo_sir.id),
                            ('company_id', '=', factura.company_id.id)])
                        journal_id = False
                        if len(conf_pagos_ids) > 0:
                            journl_conf = diarios_pagos_conf_obj.read(cr, uid, conf_pagos_ids[0], ['journal_id'])
                            journal_id = journl_conf['journal_id'][0]

                        if not journal_id:
                            raise osv.except_osv('Error',
                                                 u'No se encontró diario configurado para el Tipo de Ejecución %s, Concepto del Gasto %s, Código SIR %s' %
                                                 (factura.siif_tipo_ejecucion.name, factura.siif_concepto_gasto.name, factura.siif_codigo_sir.name))
                        #Llamar a pagar
                        account_invoice_obj.automatic_pay_invoice_aux(cr, uid, factura.id, journal_id=journal_id, amount=0.0, date=vals['fecha_enviado'])

                    self.create(cr, uid, vals, context)

                # Verifico que existe una regularizacion clearing (en estado intervenida) asociada a los datos
                else:
                    clearing_obj = self.pool.get('regularizacion.clearing')
                    condiciones_clearing = []
                    condiciones_clearing.append(('nro_afectacion', '=', paga.nroDocAfectacion))
                    condiciones_clearing.append(('nro_compromiso', '=', paga.nroDocCompromiso))
                    condiciones_clearing.append(('nro_obligacion', '=', paga.nroDocObligacion))
                    condiciones_clearing.append(('fiscalyear_id.code', '=', str(paga.anioFiscal)))
                    condiciones_clearing.append(('ue_siif_id.ue', '=', str(paga.unidadEjecutadora).zfill(3)))
                    condiciones_clearing.append(('inciso_siif_id.inciso', '=', str(paga.inciso).zfill(2)))

                    condiciones_clearing.append(('state', '=', 'intervened'))

                    ids_clearing = clearing_obj.search(cr, uid, condiciones_clearing, context=context)
                    if ids_clearing:
                        vals['clearing_grp_id'] = ids_clearing[0]
                        clearing = clearing_obj.browse(cr, uid, ids_clearing[0], context=context)
                        self.success_clearing_intervened(cr, uid, vals, clearing, context=context)
                    else:
                        # El documento recibido no es ni Factura ni Regularizacion Clearing
                        self.failed_paga(cr, uid, vals, paga, context=context)
        return True

grp_integracion_pagas_totalmente()
