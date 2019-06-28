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
import time
from datetime import datetime
from openerp.report import report_sxw
from openerp import SUPERUSER_ID
from openerp.osv import osv

import logging
_logger = logging.getLogger(__name__)
# TODO: K SPRING 16 GAP 379_380
class grp_ejecucion_presupuestal_compras(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(grp_ejecucion_presupuestal_compras, self).__init__(cr, uid, name, context=context)

        fecha_reporte = self.formatLang(
            str(datetime.today()), date=True)
        self.pedidos_compras = None
        self.afectaciones = None
        self.adjudicaciones = None
        self.ordenes = None
        self.facturas = None
        self.localcontext.update({
            'time': time,
            'get_tipo': self._get_tipo,
            'get_pedido_compra': self._get_pedido_compra,
            'get_afectaciones': self._get_afectaciones,
            'get_adjudicaciones': self._get_adjudicaciones,
            'get_ordenes': self._get_ordenes,
            'get_facturas': self._get_facturas,
            'fecha_reporte':fecha_reporte,
        })

    # TODO: K SPRING 16 GAP 379_380
    def _get_tipo(self, data):
        return data.get('type')

    # TODO: K SPRING 16 GAP 379_380
    def _get_pedido_compra(self, data):
        if self.pedidos_compras:
            return self.pedidos_compras
        pedido_compra_obj = self.pool.get('grp.pedido.compra')
        if data.get('pedido_compra_id'):
            self.pedidos_compras = pedido_compra_obj.browse(self.cr, self.uid,data['pedido_compra_id'][0])
        else:
            domain = []
            if data.get('fiscalyear_siif_id', False):
                fiscal_year = self.pool['account.fiscalyear'].browse(self.cr, self.uid, data['fiscalyear_siif_id'][0])
                domain.append(('date_start','>=',fiscal_year.date_start))
                domain.append(('date_start','<=',fiscal_year.date_stop))
            pedido_compra_ids = pedido_compra_obj.search(self.cr, self.uid, domain)
            self.pedidos_compras = pedido_compra_obj.browse(self.cr, self.uid, pedido_compra_ids)
        return self.pedidos_compras

    # TODO: K SPRING 16 GAP 379_380
    def _get_afectaciones(self, data):
        if self.afectaciones:
            return self.afectaciones
        pedidos_vals = {}
        for pedido in self._get_pedido_compra(data):
            afectacion_vals = []
            for afectaciones in pedido.apg_ids.mapped('nro_afectacion_siif'):
                afectacion = {
                    'nro_afectacion_siif' : afectaciones
                }
                modif_vals = []
                monto_afectado_fiscalyear = {}
                monto_efectacion = 0
                for modif in pedido.apg_ids.filtered(lambda x: x.nro_afectacion_siif == afectaciones
                                                     ).mapped('modif_log_ids').sorted(key=lambda a:
                                                    (a.apg_id.fiscalyear_siif_id.name, a.fecha)):
                    vals_modif = {
                        'fiscalyear_siif_id' : modif.apg_id.fiscalyear_siif_id.name,
                        'fecha': modif.fecha,
                        'llave': modif.apg_id.inciso_siif_id.inciso + '-' + modif.apg_id.ue_siif_id.ue + '-' +\
                                 modif.objeto_gasto + '-' + modif.auxiliar + '-' + modif.financiamiento + '-' +\
                                 modif.programa + '-' + modif.proyecto + '-' +  modif.moneda + '-' + modif.tipo_credito,
                        'importe': modif.importe,
                    }
                    modif_vals.append(vals_modif)
                    monto_efectacion += modif.importe
                    if monto_afectado_fiscalyear.has_key(modif.apg_id.fiscalyear_siif_id.name):
                        monto_afectado_fiscalyear[modif.apg_id.fiscalyear_siif_id.name] += modif.importe
                    else:
                        monto_afectado_fiscalyear[modif.apg_id.fiscalyear_siif_id.name] = modif.importe
                afectacion['modif_vals'] = modif_vals
                afectacion['monto_afectado_fiscalyear'] = monto_afectado_fiscalyear
                afectacion['monto_efectacion'] = monto_efectacion
                afectacion_vals.append(afectacion)
            pedidos_vals[pedido.name] = afectacion_vals
        self.afectaciones = pedidos_vals
        return self.afectaciones

    # TODO: K SPRING 16 GAP 379_380
    def _get_adjudicaciones(self, data):
        if self.adjudicaciones:
            return self.adjudicaciones
        pedidos_vals = {}
        LISTA_ESTADOS_COT = {
            'draft': 'Borrador',
            'validado': u'Validado',
            'in_approval': u'En aprobación',
            'approved': u'Aprobado',
            'in_authorization': u'En autorización',
            'authorized': u'Autorizado',
            'refused': u'Rechazado ',
            'aprobado_sice': 'Aprobado SICE',
            'cancelado': 'Cancelado',
        }
        adjudicacion_obj = self.pool.get('grp.cotizaciones')
        for pedido in self._get_pedido_compra(data):
            adjudicacion_ids = adjudicacion_obj.search(self.cr, self.uid, [('pedido_compra_id', '=', pedido.id)])
            adjudicaciones = []
            for adjudicacion in adjudicacion_obj.browse(self.cr, self.uid, adjudicacion_ids):
                # proveedores = []
                for proveedor_adj in adjudicacion.sice_page_aceptadas.mapped('proveedor_cot_id'):
                    proveedor = {
                        'name': proveedor_adj.name
                    }
                    lines = []
                    for line in adjudicacion.sice_page_aceptadas.filtered(lambda x: x.proveedor_cot_id == proveedor_adj):
                        line_vals = {
                            'fecha_respuesta': adjudicacion.fecha_respuesta,
                            'currency': line.currency.name,
                            'subtotal': line.subtotal,
                            'state': LISTA_ESTADOS_COT[adjudicacion.state],
                        }
                        lines.append(line_vals)
                    proveedor['lines'] = lines

                    compromisos = []
                    for compromiso in adjudicacion.provider_compromise_ids.filtered(lambda x: x.provider_id == proveedor_adj). \
                                                                        sorted(key=lambda a: (a.fiscalyear_id.name,
                                                                        a.nro_compromiso)):
                        compromiso_vals = {'nro_compromiso': compromiso.nro_compromiso}
                        modifs = []
                        monto_compromiso = 0
                        for modif in compromiso.mapped('modif_compromiso_log_ids'):
                            vals_modif = {
                                'fiscalyear_id': compromiso.fiscalyear_id.name,
                                'fecha': modif.fecha,
                                'llave': compromiso.inciso_siif_id.inciso + '-' + compromiso.ue_siif_id.ue + '-' + \
                                         modif.objeto_gasto + '-' + modif.auxiliar + '-' + modif.financiamiento + '-' + \
                                         modif.programa + '-' + modif.proyecto + '-' + modif.moneda + '-' + modif.tipo_credito,
                                'importe': modif.importe,
                            }
                            modifs.append(vals_modif)
                            monto_compromiso += modif.importe
                        compromiso_vals['modifs'] = modifs
                        compromiso_vals['monto_compromiso'] = monto_compromiso
                        compromisos.append(compromiso_vals)
                    proveedor['compromisos'] = compromisos
                    # proveedores.append(proveedor)
                    adjudicaciones.append(proveedor)
                # adjudicacion_vals = {'proveedores': proveedores}

                # adjudicacion_vals['orders'] = adjudicacion.purchase_order_ids

                # factura_obj = self.pool.get('account.invoice')
                # factura_ids = factura_obj.search(self.cr, self.uid, [('orden_compra_id', 'in', adjudicacion.purchase_order_ids.ids)])
                # facturas = factura_obj.browse(self.cr, self.uid, factura_ids)
                # facturas_list = []
                # monto_obligacion_fiscalyear = {}
                # for factura in facturas.sorted(key=lambda a:(a.partner_id.name, a.orden_compra_id.name)):
                #     modif_vals = []
                #     monto_obligacion = 0
                #     for modif in factura.modif_obligacion_log_ids.sorted(key=lambda a:
                #                                         (a.invoice_id.fiscalyear_siif_id.name, a.siif_sec_obligacion)):
                #         vals_modif = {
                #             'fiscalyear_siif_id':modif.invoice_id.fiscalyear_siif_id.name,
                #             'fecha': modif.fecha,
                #             'llave': modif.invoice_id.inciso_siif_id.inciso + '-' + modif.invoice_id.ue_siif_id.ue + '-' + \
                #                      modif.objeto_gasto + '-' + modif.auxiliar + '-' + modif.financiamiento + '-' + \
                #                      modif.programa + '-' + modif.proyecto + '-' + modif.moneda + '-' + modif.tipo_credito,
                #             'importe': modif.importe,
                #         }
                #         modif_vals.append(vals_modif)
                #         monto_obligacion += modif.importe
                #         if monto_obligacion_fiscalyear.has_key(modif.invoice_id.fiscalyear_siif_id.name):
                #             monto_obligacion_fiscalyear[modif.invoice_id.fiscalyear_siif_id.name] += modif.importe
                #         else:
                #             monto_obligacion_fiscalyear[modif.invoice_id.fiscalyear_siif_id.name] = modif.importe
                #         modif_vals.append(vals_modif)
                #     obligacion = {
                #         'nro_afectacion_siif': factura.nro_obligacion,
                #         'modif_vals': modif_vals,
                #         'monto_obligacion': monto_obligacion
                #     }
                #     factura_vals = {
                #         'name_proveedor': factura.partner_id.name,
                #         'factura_obj': factura,
                #         'obligacion': obligacion
                #     }
                #     facturas_list.append(factura_vals)
                #
                # adjudicacion_vals['facturas'] = facturas_list
                # adjudicacion_vals['monto_obligacion_fiscalyear'] = monto_obligacion_fiscalyear
                # adjudicaciones.append(adjudicacion_vals)

            pedidos_vals[pedido.name] = adjudicaciones
        self.adjudicaciones = pedidos_vals
        return self.adjudicaciones

    # TODO: K SPRING 16 GAP 379_380
    def _get_ordenes(self, data):
        if self.ordenes:
            return self.ordenes
        pedidos_vals = {}
        adjudicacion_obj = self.pool.get('grp.cotizaciones')
        for pedido in self._get_pedido_compra(data):
            adjudicacion_ids = adjudicacion_obj.search(self.cr, self.uid, [('pedido_compra_id', '=', pedido.id)])
            orders = adjudicacion_obj.browse(self.cr, self.uid, adjudicacion_ids).mapped('purchase_order_ids')
            pedidos_vals[pedido.name] = orders
        self.ordenes = pedidos_vals
        return self.ordenes

    # TODO: K SPRING 16 GAP 379_380
    def _get_facturas(self, data):
        if self.facturas:
            return self.facturas
        pedidos_vals = {}
        factura_obj = self.pool.get('account.invoice')
        orders = self._get_ordenes(data)
        for pedido in self._get_pedido_compra(data):
            ordenes_pedido = orders[pedido.name]

            factura_ids = factura_obj.search(self.cr, self.uid,
                                             [('orden_compra_id', 'in', ordenes_pedido.ids)])
            facturas = factura_obj.browse(self.cr, self.uid, factura_ids)
            facturas_list = []
            monto_obligacion_fiscalyear = {}
            for factura in facturas.sorted(key=lambda a: (a.partner_id.name, a.orden_compra_id.name)):
                modif_vals = []
                monto_obligacion = 0
                for modif in factura.modif_obligacion_log_ids.sorted(key=lambda a:
                (a.invoice_id.fiscalyear_siif_id.name, a.siif_sec_obligacion)):
                    vals_modif = {
                        'fiscalyear_siif_id': modif.invoice_id.fiscalyear_siif_id.name,
                        'fecha': modif.fecha,
                        'llave': modif.invoice_id.inciso_siif_id.inciso + '-' + modif.invoice_id.ue_siif_id.ue + '-' + \
                                 modif.objeto_gasto + '-' + modif.auxiliar + '-' + modif.financiamiento + '-' + \
                                 modif.programa + '-' + modif.proyecto + '-' + modif.moneda + '-' + modif.tipo_credito,
                        'importe': modif.importe,
                    }
                    modif_vals.append(vals_modif)
                    monto_obligacion += modif.importe
                    if monto_obligacion_fiscalyear.has_key(modif.invoice_id.fiscalyear_siif_id.name):
                        monto_obligacion_fiscalyear[modif.invoice_id.fiscalyear_siif_id.name] += modif.importe
                    else:
                        monto_obligacion_fiscalyear[modif.invoice_id.fiscalyear_siif_id.name] = modif.importe
                    modif_vals.append(vals_modif)
                obligacion = {
                    'nro_afectacion_siif': factura.nro_obligacion,
                    'modif_vals': modif_vals,
                    'monto_obligacion': monto_obligacion
                }
                factura_vals = {
                    'name_proveedor': factura.partner_id.name,
                    'factura_obj': factura,
                    'obligacion': obligacion
                }
                facturas_list.append(factura_vals)
            value_list = {
                'facturas': facturas_list,
                'monto_obligacion_fiscalyear': monto_obligacion_fiscalyear
            }
            pedidos_vals[pedido.name] = value_list
        self.facturas = pedidos_vals
        return self.facturas
