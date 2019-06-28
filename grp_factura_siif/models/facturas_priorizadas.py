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
from datetime import datetime

_logger = logging.getLogger(__name__)


class grp_integracion_priorizadas(osv.osv):
    _name = 'grp.integracion.priorizadas'

    # MVAR Se calcula fecha date para usar en vista tree y como filtro desde "Procesar facturas priorizadas"
    def _get_fecha_aprob_date( self, cr, uid, ids, name, args, context = None ):
        res = { }
        for record in self.browse(cr, uid, ids, context = context):
            res[record.id] = datetime.strptime(record.fecha_confirmado[:10], '%Y-%m-%d').date()
        return res

    _columns = {
        'anio_fiscal': fields.integer(u'Año fiscal', readonly=True),
        'anio_priorizacion': fields.integer(u'Año fiscal', readonly=True),
        'clase_id': fields.char(u'Id clase', readonly=True),
        'concepto_de_gasto': fields.integer(u'Concepto del gasto', readonly=True),
        'fecha_confirmado': fields.char(u'Fecha aprobado', readonly=True),
        'inciso': fields.integer(u'Inciso', readonly=True),
        'mes_priorizacion': fields.integer(u'Liquido a pagar', readonly=True),
        'moneda': fields.integer(u'Moneda', readonly=True),
        'monto_pagado': fields.integer(u'Monto obligacion', readonly=True),
        'monto_priorizado': fields.integer(u'Monto priorizado', readonly=True),
        'nro_doc_afectacion': fields.integer(u'Número doc. afectación', readonly=True),
        'nro_doc_compromiso': fields.integer(u'Número doc. compromiso', readonly=True),
        'nro_doc_obligacion': fields.integer(u'Número doc. obligación', readonly=True),
        'nro_lote_oblig': fields.integer(u'Número lote obligación', readonly=True),
        'ruc': fields.char(u'Ruc', readonly=True),
        'sec_priorizacion': fields.integer(u'Sec. priorización', readonly=True),
        'unidad_ejecutora': fields.integer(u'Unidad ejecutora', readonly=True),
        'state': fields.selection((('pendant', 'Sin procesar'), ('processed', 'Procesado'), ('error', 'Error')), 'Estado', readonly=True),
        'resultado': fields.text(u"Resultado"),
        'timestamp': fields.datetime(u'Fecha de creación', readonly=True),
        'timestamp_aprobado': fields.datetime(u'Fecha de aprobación', readonly=True),
        'usuario_aprobador': fields.many2one('res.users', u'Aprobado por', readonly=True),
        'factura_grp_id': fields.many2one('account.invoice', 'Factura GRP priorizada', readonly=True),
        'fecha_aprobado_date': fields.function(_get_fecha_aprob_date, string='Fecha aprobado', type='date', store=True),
    }

    def actualizar_priorizadas_cron(self, cr, uid, context=None):
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
                self.actualizar_priorizadas(cr, uid, anio_anterior, pres_ant.inciso, fecha_desde, fecha_hasta, context)

        presupuestos_anio_actual_ids = presupuesto_obj.search(cr, uid, [('fiscal_year.code', '=', anio_fiscal)], context=context)
        for pres_actual in presupuesto_obj.browse(cr, uid, presupuestos_anio_actual_ids, context=context):
            self.actualizar_priorizadas(cr, uid, anio_fiscal, pres_actual.inciso, fecha_desde, fecha_hasta, context)
        return True

    def success_invoice_prioritized(self, cr, uid, vals, factura, priorizada, context=None):
        if factura.state not in ['forced','open','intervened']:
            vals['state'] = 'error'
            estado = dict(self.pool.get('account.invoice').fields_get(cr, uid, allfields=['state'], context=context)['state']['selection'])[factura.state]
            vals['resultado'] = 'La factura debe estar en estado Obligado, Abierto o Intervenido. El estado es: %s' % (estado,)
        else:
            vals['state'] = 'processed'
            vals['resultado'] = 'Fatura procesada con un monto priorizado de %s.' % (str(priorizada.montoPriorizado),)
            self.pool.get('grp.account.invoice.prioritized.line').create(cr, uid, {
                'factura_grp_id': factura.id,
                'fecha_confirmado': priorizada.fechaConfirmado,
                'monto_priorizado': priorizada.montoPriorizado,
                'ruc': priorizada.ruc
            }, context=context)
            _amount = 0
            for inv_p in factura.inv_prioritized_line:
                _amount += inv_p.monto_priorizado
            if _amount > 0 and _amount >= factura.amount_ttal_liq_pesos:
                vals['resultado'] = 'Factura procesada con un monto priorizado de %s. Se pasa a Priorizada.' % (str(priorizada.montoPriorizado),)
                factura.write({'state': 'prioritized'})
        #Create Log
        self.create(cr, uid, vals, context=context)

    def failed_prioritized(self, cr, uid, vals, priorizada, context=None):
        vals['state'] = 'error'
        vals['resultado'] = 'No se encontro factura en GRP correspondiente a este registro'
        self.create(cr, uid, vals, context=context)

    #TODO: no se esta llamando a este metodo
    def success_clearing_prioritized(self, cr, uid, vals, clearing, priorizada, context=None):
        if clearing.siif_tipo_ejecucion and clearing.siif_tipo_ejecucion.codigo == 'P':
            if clearing.state == 'forced':
                vals['state'] = 'processed'
                vals['resultado'] = 'Procesada'
                clearing.write({'state': 'prioritized'})
            else:
                vals['state'] = 'error'
                estado = dict(self.pool.get('regularizacion.clearing').fields_get(cr, uid, allfields=['state'], context=context)['state']['selection'])[clearing.state]
                vals['resultado'] = 'El documento debe estar en estado Obligado. El estado es: %s' % (estado,)
        else:
            if clearing.state in ['forced','confirm']:
                vals['state'] = 'processed'
                vals['resultado'] = 'Procesada'
                clearing.write({'state': 'prioritized'})
            else:
                vals['state'] = 'error'
                estado = dict(self.pool.get('regularizacion.clearing').fields_get(cr, uid, allfields=['state'], context=context)['state']['selection'])[clearing.state]
                vals['resultado'] = 'El documento debe estar en estado Obligado o Confirmado. El estado es: %s' % (estado,)
        self.create(cr, uid, vals, context=context)

    def actualizar_priorizadas(self, cr, uid, anio_fiscal, inciso, fecha_desde, fecha_hasta, context=None):
        _logger.info("Ejecutando cron de actualizar facturas priorizadas: anio_fiscal: %s, inciso: %s, fecha_desde: %s, fecha_hasta: %s", anio_fiscal, inciso, fecha_desde, fecha_hasta)

        account_invoice_obj = self.pool.get('account.invoice')
        siif_proxy = self.pool.get('siif.proxy')
        lista = siif_proxy.obtener_priorizadas(cr, uid, anio_fiscal, inciso, fecha_desde, fecha_hasta)
        _logger.info('resultado priorizadas: %s', lista)
        if len(lista) > 0:
            for priorizada in lista:
                condiciones_log = []
                condiciones_log.append(('nro_doc_afectacion', '=', priorizada.nroDocAfectacion))
                condiciones_log.append(('nro_doc_compromiso', '=', priorizada.nroDocCompromiso))
                condiciones_log.append(('nro_doc_obligacion', '=', priorizada.nroDocObligacion))
                condiciones_log.append(('anio_fiscal', '=', priorizada.anioFiscal))
                condiciones_log.append(('sec_priorizacion', '=', priorizada.secDePriorizacion))
                condiciones_log.append(('ruc', '=', priorizada.ruc))
                condiciones_log.append(('unidad_ejecutora', '=', priorizada.unidadEjecutora))
                condiciones_log.append(('inciso', '=', priorizada.inciso))

                condiciones_factura = []
                condiciones_factura.append(('nro_afectacion', '=', priorizada.nroDocAfectacion))
                condiciones_factura.append(('nro_compromiso', '=', priorizada.nroDocCompromiso))
                condiciones_factura.append(('nro_obligacion', '=', priorizada.nroDocObligacion))
                condiciones_factura.append(('fiscalyear_siif_id.code', '=', str(priorizada.anioFiscal)))
                condiciones_factura.append(('ue_siif_id.ue', '=', str(priorizada.unidadEjecutora).zfill(3)))
                condiciones_factura.append(('inciso_siif_id.inciso', '=', str(priorizada.inciso).zfill(2)))
                condiciones_factura.append(('doc_type','!=','ajuste_invoice'))

                #Busco en la tabla de log si ya se cargo el registro
                ids_priorizadas = self.search(cr, uid, condiciones_log, context=context)
                #Si no se cargo verifico que existe una factura asociada a los datos
                if not ids_priorizadas:
                    ids_facturas = account_invoice_obj.search(cr, uid, condiciones_factura, context=context)
                    vals = {}
                    vals['anio_fiscal'] = priorizada.anioFiscal
                    vals['anio_priorizacion'] = priorizada.anioPriorizacion
                    vals['clase_id'] = priorizada.claseId
                    vals['concepto_de_gasto'] = priorizada.conceptoDeGasto
                    vals['fecha_confirmado']=priorizada.fechaConfirmado
                    vals['inciso'] = priorizada.inciso
                    vals['mes_priorizacion'] = priorizada.mesDePriorizacion
                    vals['moneda'] = priorizada.moneda
                    if hasattr(priorizada,'montoPagado'):
                        vals['monto_pagado'] = priorizada.montoPagado
                    vals['monto_priorizado'] = priorizada.montoPriorizado
                    vals['nro_doc_afectacion'] = priorizada.nroDocAfectacion
                    vals['nro_doc_compromiso'] = priorizada.nroDocCompromiso
                    vals['nro_doc_obligacion'] = priorizada.nroDocObligacion
                    vals['nro_lote_oblig'] = priorizada.nroLoteOblig
                    vals['ruc'] = priorizada.ruc
                    vals['sec_priorizacion'] = priorizada.secDePriorizacion
                    vals['unidad_ejecutora'] = priorizada.unidadEjecutora
                    if ids_facturas:
                        vals['factura_grp_id'] = ids_facturas[0]
                        factura = account_invoice_obj.browse(cr, uid, ids_facturas[0], context=context)
                        self.success_invoice_prioritized(cr, uid, vals, factura, priorizada, context=context)
                    #TODO: confirmar que no es necesario buscar regularizacion clearing, no busca ni llama a la funcion (success_clearing_prioritized)
                    else:
                        self.failed_prioritized(cr, uid, vals, priorizada, context=context)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
