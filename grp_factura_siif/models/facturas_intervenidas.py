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
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc

_logger = logging.getLogger(__name__)


class grp_integracion_intervenidas(osv.osv):
    _name = 'grp.integracion.intervenidas'

    # ASM Se calcula fecha date para usar en vista tree y como filtro desde "Procesar facturas intervenidas"
    def _get_fecha_aprob_date( self, cr, uid, ids, name, args, context = None ):
        res = { }
        for record in self.browse(cr, uid, ids, context = context):
            res[record.id] = datetime.strptime(record.fecha_aprobado[:10], '%Y-%m-%d').date()
        return res

    _columns = {
        'anio_fiscal': fields.integer(u'Año fiscal', readonly=True),
        'clase_id': fields.char('Id clase', readonly=True),
        'concepto_de_gasto': fields.integer('Concepto del gasto', readonly=True),
        'fecha_aprobado': fields.char('Fecha aprobado', readonly=True),
        'financiamiento': fields.integer('Financiamiento', readonly=True),
        'inciso': fields.integer('Inciso', readonly=True),
        'liquido_a_pagar': fields.integer('Liquido a pagar', readonly=True),
        'moneda': fields.integer('Moneda', readonly=True),
        'monto_obligacion': fields.integer('Monto obligacion', readonly=True),
        'monto_retenciones': fields.integer('Monto retenciones', readonly=True),
        'nro_doc_afectacion': fields.integer(u'Número doc. afectación', readonly=True),
        'nro_doc_compromiso': fields.integer(u'Número doc. compromiso', readonly=True),
        'nro_doc_obligacion': fields.integer(u'Número doc. obligación', readonly=True),
        'nro_lote_oblig': fields.integer(u'Número lote obligación', readonly=True),
        'ruc': fields.char('Ruc', readonly=True),
        'sec_obligacion': fields.integer(u'Sec. obligación', readonly=True),
        'tasa_de_cambio': fields.integer('Tasa de cambio', readonly=True),
        'tipo_de_ejecucion': fields.char(u'Tipo de ejecución', readonly=True),
        'tipo_de_modificacion': fields.char(u'Tipo de modificación', readonly=True),
        'unidad_ejecutora': fields.integer('Unidad ejecutora', readonly=True),
        'state': fields.selection((('pendant', 'Sin procesar'), ('processed', 'Procesado'), ('error', 'Error')), 'Estado', readonly=True),
        'resultado': fields.text(u"Resultado"),
        'timestamp': fields.datetime(u'Fecha de creación', readonly=True),
        'timestamp_aprobado': fields.datetime(u'Fecha de aprobación', readonly=True),
        'usuario_aprobador': fields.many2one('res.users', u'Aprobado por', readonly=True),
        'factura_grp_id': fields.many2one('account.invoice', 'Factura GRP intervenida', readonly=True),
        'clearing_grp_id': fields.many2one('regularizacion.clearing', 'Clearing GRP intervenida', readonly=True),
        'fecha_aprobado_date': fields.function(_get_fecha_aprob_date, string='Fecha aprobado', type='date', store=True),

    }

    def actualizar_intervenidas_cron(self, cr, uid, context=None):
        fecha_hasta = fields.date.context_today(self,cr,uid,context=context)
        presupuesto_obj = self.pool.get("presupuesto.presupuesto")
        fecha_desde = fecha_hasta.split('-')[0] + '-01-01' #1 de enero del año actual
        anio_fiscal = fecha_hasta.split('-')[0]
        mes_ejecucion = int(fecha_hasta[5:7])
        # Se llama 2 veces, una con el año anterior porque en enero/febrero cargan para el anio fiscal anterior
        if mes_ejecucion <= 3:
            anio_anterior = str(int(anio_fiscal) - 1)
            presupuestos_anio_ant_ids = presupuesto_obj.search(cr, uid, [('fiscal_year.code','=',anio_anterior)], context=context)
            for pres_ant in presupuesto_obj.browse(cr, uid, presupuestos_anio_ant_ids, context=context):
                self.actualizar_intervenidas(cr, uid, anio_anterior, pres_ant.inciso, fecha_desde, fecha_hasta, context)

        presupuestos_anio_actual_ids = presupuesto_obj.search(cr, uid, [('fiscal_year.code', '=', anio_fiscal)], context=context)
        for pres_actual in presupuesto_obj.browse(cr, uid, presupuestos_anio_actual_ids, context=context):
            self.actualizar_intervenidas(cr, uid, anio_fiscal, pres_actual.inciso, fecha_desde, fecha_hasta, context)
        return True

    def success_invoice_intervened(self, cr, uid, vals, factura, intervenida, context=None):
        #DDELFINO: 20181212 - En caso de que se trate de un 3en1 recibido por la integracion afe_com_obl_por_ue_siif se procede a contabilizar
        if factura.obligacion_afe_com_obl_por_ue_siif:
            invoice_obj = self.pool.get('account.invoice')

            # Se presiona el button_reset_taxes
            invoice_data = invoice_obj.browse(cr, uid, factura.id, context=context)
            invoice_data.button_reset_taxes()

            invoice_data.invoice_impactar_presupuesto()
            # invoice_data.invoice_impactar_presupuesto([invoice], context=context)

            if not invoice_data.move_id:
                wf_service = netsvc.LocalService('workflow')
                wf_service.trg_validate(uid, 'account.invoice', invoice_data.id, 'invoice_open', cr)

                invoice_obj.write(cr, uid, [invoice_data.id], {'state': 'forced'}, context=context)

        if factura.siif_tipo_ejecucion.codigo == 'P':
            if factura.state == 'forced':
                vals['state'] = 'processed'
                vals['resultado'] = 'Procesada'
                factura.write({'state': 'intervened'})
            else:
                vals['state'] = 'error'
                estado = dict(self.pool.get('account.invoice').fields_get(cr, uid, allfields=['state'], context=context)['state']['selection'])[factura.state]
                vals['resultado'] = 'El documento debe estar en estado Obligado. El estado es: %s' % (estado,)
        else:
            if factura.state in ['forced','open']:
                vals['state'] = 'processed'
                vals['resultado'] = 'Procesada'
                factura.write({'state': 'intervened'})
            else:
                vals['state'] = 'error'
                estado = dict(self.pool.get('account.invoice').fields_get(cr, uid, allfields=['state'], context=context)['state']['selection'])[factura.state]
                vals['resultado'] = 'El documento debe estar en estado Obligado o Abierto. El estado es: %s' % (estado,)

        self.create(cr, uid, vals, context=context)

    def failed_intervened(self, cr, uid, vals, intervenida, context=None):
        vals['state'] = 'error'
        vals['resultado'] = u'No se encontró factura en GRP correspondiente a este registro'
        self.create(cr, uid, vals, context=context)

    def success_clearing_intervened(self, cr, uid, vals, clearing, intervenida, context=None):
        if clearing.siif_tipo_ejecucion and clearing.siif_tipo_ejecucion.codigo == 'P':
            if clearing.state == 'forced':
                vals['state'] = 'processed'
                vals['resultado'] = 'Procesada'
                clearing.write({'state': 'intervened'})
            else:
                vals['state'] = 'error'
                estado = dict(self.pool.get('regularizacion.clearing').fields_get(cr, uid, allfields=['state'], context=context)['state']['selection'])[clearing.state]
                vals['resultado'] = 'El documento debe estar en estado Obligado. El estado es: %s' % (estado,)
        else:
            if clearing.state in ['forced','confirm']:
                vals['state'] = 'processed'
                vals['resultado'] = 'Procesada'
                clearing.write({'state': 'intervened'})
            else:
                vals['state'] = 'error'
                estado = dict(self.pool.get('regularizacion.clearing').fields_get(cr, uid, allfields=['state'], context=context)['state']['selection'])[clearing.state]
                vals['resultado'] = 'El documento debe estar en estado Obligado o Confirmado. El estado es: %s' % (estado,)
        self.create(cr, uid, vals, context=context)

    def actualizar_intervenidas(self, cr, uid, anio_fiscal, inciso, fecha_desde, fecha_hasta, context=None):
        _logger.info("Ejecutando cron de actualizar facturas intervenidas: anio_fiscal: %s, inciso: %s, fecha_desde: %s, fecha_hasta: %s", anio_fiscal, inciso, fecha_desde, fecha_hasta)
        account_invoice_obj = self.pool.get('account.invoice')
        siif_proxy = self.pool.get('siif.proxy')
        lista = siif_proxy.obtener_intervenidas(cr, uid, anio_fiscal, inciso, fecha_desde, fecha_hasta)
        _logger.info('resultado intervenidas: %s', lista)
        if len(lista) > 0:
            for intervenida in lista:
                condiciones_log = []
                condiciones_log.append(('nro_doc_afectacion', '=', intervenida.nroDocAfectacion))
                condiciones_log.append(('nro_doc_compromiso', '=', intervenida.nroDocCompromiso))
                condiciones_log.append(('nro_doc_obligacion', '=', intervenida.nroDocObligacion))
                condiciones_log.append(('anio_fiscal', '=', intervenida.anioFiscal))
                condiciones_log.append(('sec_obligacion', '=', intervenida.secObligacion))
                condiciones_log.append(('unidad_ejecutora', '=', intervenida.unidadEjecutora))
                condiciones_log.append(('inciso', '=', intervenida.inciso))

                #TODO: ver de agregar condiciones para no buscar modificaciones
                condiciones_factura = []
                condiciones_factura.append(('nro_afectacion', '=', intervenida.nroDocAfectacion))
                condiciones_factura.append(('nro_compromiso', '=', intervenida.nroDocCompromiso))
                condiciones_factura.append(('nro_obligacion', '=', intervenida.nroDocObligacion))
                condiciones_factura.append(('fiscalyear_siif_id.code', '=', str(intervenida.anioFiscal)))
                condiciones_factura.append(('ue_siif_id.ue', '=', str(intervenida.unidadEjecutora).zfill(3)))
                condiciones_factura.append(('inciso_siif_id.inciso', '=', str(intervenida.inciso).zfill(2)))
                condiciones_factura.append(('doc_type','!=','ajuste_invoice'))

                #Busco en la tabla de log si ya se cargo el registro
                ids_intervenidas = self.search(cr, uid, condiciones_log, context=context)
                #Si no se cargo verifico que existe una factura asociada a los datos
                if not ids_intervenidas:
                    ids_facturas = account_invoice_obj.search(cr, uid, condiciones_factura, context=context)
                    vals = {}
                    vals['anio_fiscal'] = intervenida.anioFiscal
                    vals['clase_id'] = intervenida.claseId
                    vals['concepto_de_gasto'] = intervenida.conceptoDeGasto
                    vals['fecha_aprobado']=intervenida.fechaAprobado
                    vals['financiamiento'] = intervenida.financiamiento
                    vals['inciso'] = intervenida.inciso
                    vals['liquido_a_pagar'] = intervenida.liquidoAPagar
                    vals['moneda'] = intervenida.moneda
                    vals['monto_obligacion'] = intervenida.montoObligacion
                    vals['monto_retenciones'] = intervenida.montoRetenciones
                    vals['nro_doc_afectacion'] = intervenida.nroDocAfectacion
                    vals['nro_doc_compromiso'] = intervenida.nroDocCompromiso
                    vals['nro_doc_obligacion'] = intervenida.nroDocObligacion
                    if hasattr(intervenida,'nroLoteOblig'):
                        vals['nro_lote_oblig'] = intervenida.nroLoteOblig
                    vals['ruc'] = intervenida.ruc
                    vals['sec_obligacion'] = intervenida.secObligacion
                    if hasattr(intervenida, 'tasaDeCambio'):
                        vals['tasa_de_cambio'] = intervenida.tasaDeCambio
                    vals['tipo_de_ejecucion'] = intervenida.tipoDeEjecucion
                    vals['tipo_de_modificacion'] = intervenida.tipoDeModificacion
                    vals['unidad_ejecutora'] = intervenida.unidadEjecutora
                    if ids_facturas:
                        vals['factura_grp_id'] = ids_facturas[0]
                        factura = account_invoice_obj.browse(cr, uid, ids_facturas[0], context=context)
                        self.success_invoice_intervened(cr, uid, vals, factura, intervenida, context=context)
                    else:
                        clearing_obj = self.pool.get('regularizacion.clearing')
                        condiciones_clearing = []
                        condiciones_clearing.append(('nro_afectacion', '=', intervenida.nroDocAfectacion))
                        condiciones_clearing.append(('nro_compromiso', '=', intervenida.nroDocCompromiso))
                        condiciones_clearing.append(('nro_obligacion', '=', intervenida.nroDocObligacion))
                        condiciones_clearing.append(('fiscalyear_id.code', '=', str(intervenida.anioFiscal)))
                        condiciones_clearing.append(('ue_siif_id.ue', '=', str(intervenida.unidadEjecutora).zfill(3)))
                        condiciones_clearing.append(('inciso_siif_id.inciso', '=', str(intervenida.inciso).zfill(2)))

                        ids_clearing = clearing_obj.search(cr, uid, condiciones_clearing, context=context)
                        if ids_clearing:
                            vals['clearing_grp_id'] = ids_clearing[0]
                            clearing = clearing_obj.browse(cr, uid, ids_clearing[0], context=context)
                            self.success_clearing_intervened(cr, uid, vals, clearing, intervenida, context=context)
                        else:
                            self.failed_intervened(cr, uid, vals, intervenida, context=context)
        return True


