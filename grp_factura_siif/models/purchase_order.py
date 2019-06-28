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
import openerp.addons.decimal_precision as dp
import datetime
import time
from lxml import etree
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from datetime import datetime
from openerp import netsvc
from suds import WebFault
from suds.client import Client
import math
from presupuesto_estructura import TIPO_DOCUMENTO

import logging

_logger = logging.getLogger(__name__)

class compromiso_oc_anulaciones_siif_log(osv.osv):
    _name = 'compromiso.oc.anulacion.siif.log'
    _description = "Log orden compras anulaciones"
    _columns = {
        'orden_id': fields.many2one('purchase.order', 'Compromiso OC', required=True,ondelete='cascade'),
        'fecha': fields.date('Fecha', required=True),
        'nro_afectacion_siif': fields.integer(u'Nro Afectación SIIF'),
        'nro_compromiso': fields.char(u'Nro Compromiso'),
        'nro_comp_sist_aux': fields.char(u'Nro Compromiso Sistema Aux'),
    }

    _defaults = {
        # 'fecha': lambda *a: time.strftime('%Y-%m-%d'),
        'fecha': fields.date.context_today,
    }
compromiso_oc_anulaciones_siif_log()

class grp_orden_compra(osv.osv):
    _inherit = 'purchase.order'

    def _get_total_llavep(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for po in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for llavep in po.llpapg_ids:
                total += llavep.importe
            res[po.id] = total
        return res

    # Fecha por defecto para año fiscal
    def _get_default_fiscal_year(self, cr, uid, context=None):
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id

        fiscal_year_id = fiscalyear_obj.search(cr, uid,
                                               [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
                                                ('company_id', '=', uid_company_id)], context=context)
        return fiscal_year_id and fiscal_year_id[0] or False

    _columns = {
        'siif_tipo_ejecucion': fields.related('pc_apg_id', 'siif_tipo_ejecucion', type="many2one",
                                              relation="tipo.ejecucion.siif", string=u'Tipo de ejecución',
                                              readonly="1"),
        'siif_concepto_gasto': fields.related('pc_apg_id', 'siif_concepto_gasto', type="many2one",
                                              relation="presupuesto.concepto", string='Concepto del gasto',
                                              readonly="1"),
        'siif_codigo_sir': fields.related('pc_apg_id', 'siif_codigo_sir', type="many2one", relation="codigo.sir.siif",
                                          string=u'Código SIR', readonly="1"),
        'siif_financiamiento': fields.related('pc_apg_id', 'siif_financiamiento', type="many2one",
                                              relation="financiamiento.siif", string='Fuente de financiamiento',
                                              readonly="1"),
        'siif_tipo_documento': fields.many2one('tipo.documento.siif', u'Tipo de documento',
                                               domain=[('visible_documento_compromiso', '=', True)]),
        'siif_nro_fondo_rot': fields.related('pc_apg_id', 'siif_nro_fondo_rot', type="many2one",
                                             relation="fondo.rotatorio.siif", string='Nro doc. fondo rotatorio',
                                             readonly="1"),
        'siif_ult_modif': fields.integer(u'Última modificación'),
        'siif_sec_compromiso': fields.char(u'Secuencial compromiso'),
        'siif_descripcion': fields.text(u"Descripción SIIF", size=100),
        'tipo_ejecucion_codigo_rel': fields.related("siif_tipo_ejecucion", "codigo", type="char",
                                                    string=u'Código tipo ejecución'),
        'fiscalyear_siif_id': fields.many2one('account.fiscalyear', u'Año fiscal'),
        'inciso_siif_id': fields.related('pc_apg_id', 'inciso_siif_id', type='many2one',
                                         relation='grp.estruc_pres.inciso', string=u'Inciso', readonly="1"),
        'ue_siif_id': fields.related('pc_apg_id', 'ue_siif_id', type='many2one', relation='grp.estruc_pres.ue',
                                     string=u'Unidad ejecutora', readonly="1"),
        'nro_comp_sist_aux': fields.char(u'Nro Compromiso Sist. aux'),
        'anulada_siif': fields.boolean('Anulada en SIIF'),
        # Pestaña Llave Presupuestal
        'llpapg_ids': fields.one2many('grp.compras.lineas.llavep', 'order_id', string=u'Líneas presupuesto'),
        'total_llavep': fields.function(_get_total_llavep, string='Total llave presupuestal',
                                        digits_compute=dp.get_precision('Account')),
        'anulacion_siif_log_ids': fields.one2many(
            'compromiso.oc.anulacion.siif.log',
            'orden_id',
            'Log anulaciones'),
    }

    _defaults = {
        'fiscalyear_siif_id': _get_default_fiscal_year,
    }

    def onchange_fiscalyear_siif_id(self, cr, uid, ids, fiscalyear_siif_id):
        vals = {'value': {'inciso_siif_id': False, 'ue_siif_id': False}}
        if not fiscalyear_siif_id:
            return vals
        pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')
        pres_ue_obj = self.pool.get('grp.estruc_pres.ue')
        if fiscalyear_siif_id:
            ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id', '=', fiscalyear_siif_id)])
            if ids_pres_inciso:
                vals['value'].update({'inciso_siif_id': ids_pres_inciso[0]})
                ids_pres_ue = pres_ue_obj.search(cr, uid, [('inciso_id', '=', ids_pres_inciso[0])])
                if ids_pres_ue:
                    vals['value'].update({'ue_siif_id': ids_pres_ue[0]})
        if ids:
            vals['value'].update({'llpapg_ids': []})
        return vals

    def onchange_pedido(self, cr, uid, ids, pedido_compra_id, doc_origen, context=None):
        if context is None:
            context = dict({})
        result = {}
        result.setdefault('value', {})
        result['value'] = {'sice_nro': False, 'pc_apg_id': False, 'page_apg_oc': []}

        # desvincular existentes
        if ids:
            self.write(cr, uid, ids, {'pc_apg_id': False, 'page_apg_oc': [(5,)], 'llpapg_ids': [(5,)]}, context=context)

            pedido = self.browse(cr, uid, ids)
            result['value'].update({'currency_oc': pedido.currency_oc.id or False,
                                    'pricelist_id': pedido.pricelist_id.id or False,
                                    # 'odg_cot': pedido.odg_cot and pedido.odg_cot.id or False,
                                    'partner_id': pedido.partner_id and pedido.partner_id.id or False,
                                    'fecha_tipo_cambio_oc': pedido.fecha_tipo_cambio_oc or False,
                                    'date_order': pedido.date_order or False,
                                    'centro_de_costos': pedido.centro_de_costos and pedido.centro_de_costos.id or False,
                                    'location_id': pedido.location_id and pedido.location_id.id or False})
        order_line_ids = []
        if not pedido_compra_id:
            return result
        pc = self.pool.get('grp.pedido.compra').browse(cr, uid, pedido_compra_id, context=context)

        result['value'].update({'pc_apg_id': False})
        default_apg_ids = []
        if pc.apg_ids:
            for apg in pc.apg_ids:
                if apg.state in ['afectado']:
                    default_apg_ids.append(apg.id)
            if len(default_apg_ids) > 0:
                default_tuple_apg_ids = tuple(default_apg_ids)
                default_apg_id = max(default_tuple_apg_ids)
                result['value'].update({'pc_apg_id': default_apg_id})

        if pc.moneda:
            result['value'].update({'currency_oc': pc.moneda.id})

        result['value'].update({'sice_nro': pc.sice_id_compra, 'pedido_compra_id': pedido_compra_id})

        for linea in pc.lineas_ids:
            descrp = linea.sc_descripcion
            if not descrp:
                descrp = linea.product_id.name
            order_line_ids.append((0, 0, {'product_id': linea.product_id.id,
                                          'name': descrp,
                                          'date_planned': datetime.today().strftime("%Y-%m-%d"),
                                          'product_qty': linea.cantidad_comprar_sice,
                                          'product_uom': linea.uom_id.id,
                                          'price_unit': linea.precio_estimado,
                                          'taxes_id': [(6, 0, [x.id for x in linea.iva])],
                                          'state': 'draft'}))
        result['value'].update({'order_line': order_line_ids})
        return result

    def onchange_pc_apg_id(self, cr, uid, ids, pc_apg_id, pedido_compra_id):
        result = super(grp_orden_compra, self).onchange_pc_apg_id(cr, uid, ids, pc_apg_id, pedido_compra_id)
        if pc_apg_id:
            apg = self.pool.get('grp.compras.apg').browse(cr, uid, pc_apg_id)
            result['value'].update({'fiscalyear_siif_id': apg.fiscalyear_siif_id.id})
            result['value'].update({'inciso_siif_id': apg.inciso_siif_id.id})
            result['value'].update({'ue_siif_id': apg.ue_siif_id.id})
            page_apg_oc = [(5,)]
            for apg_line in self.pool.get('grp.pedido.compra').browse(cr, uid, pedido_compra_id).apg_ids:
                if apg_line.fiscalyear_siif_id.id == apg.fiscalyear_siif_id.id:
                    monto_apg = 0
                    for llp in apg_line.llpapg_ids:
                        monto_apg += llp.importe
                    page_apg_oc.append((0, 0, {'nro_apg': apg_line.id,
                                               'descripcion_apg': apg_line.descripcion,
                                               'monto_apg': monto_apg,
                                               'currency': apg_line.moneda.id,
                                               'fecha_apg': apg_line.fecha,
                                               'nro_afectacion_apg': apg_line.nro_afectacion_siif
                                               }))
            result['value'].update({'page_apg_oc': page_apg_oc})

            if apg.llpapg_ids:
                llavep_data = []

                for llavep in apg.llpapg_ids:  # la seleccionada
                    llavep_data.append((0, 0, {
                        'programa': llavep.programa,
                        'odg': llavep.odg,
                        'auxiliar': llavep.auxiliar,
                        'disponible': llavep.disponible,
                        'proyecto': llavep.proyecto,
                        'fin': llavep.fin,
                        'mon': llavep.mon,
                        'tc': llavep.tc,
                        'importe': llavep.importe,
                        # MVARELA nuevos campos
                        'programa_id': llavep.programa_id.id,
                        'odg_id': llavep.odg_id.id,
                        'auxiliar_id': llavep.auxiliar_id.id,
                        'proyecto_id': llavep.proyecto_id.id,
                        'fin_id': llavep.fin_id.id,
                        'mon_id': llavep.mon_id.id,
                        'tc_id': llavep.tc_id.id,
                    }))
                result['value'].update({'llpapg_ids': llavep_data})
        else:
            result['value'].update({'fiscalyear_siif_id': False})
            result['value'].update({'inciso_siif_id': False})
            result['value'].update({'ue_siif_id': False})
            result['value'].update({'page_apg_oc': [(5,)]})
        return result


    def button_reset_apg_llave(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # desvincular existentes
        if not ids:
            return False

        self.write(cr, uid, ids, {'page_apg_oc': [(5,)], 'llpapg_ids': [(5,)]}, context=context)
        for oc in self.browse(cr, uid, ids, context=context):
            apg_ids = []
            llavep_data = []
            pc = self.pool.get('grp.pedido.compra').browse(cr, uid, oc.pedido_compra_id.id, context=context)
            if pc.apg_ids:
                for apg in pc.apg_ids:
                    if apg.id == oc.pc_apg_id.id:
                        apg_ids.append((0, 0, {
                            'nro_apg': apg.id,
                            'descripcion_apg': apg.descripcion,
                            'monto_apg': apg.monto_divisa,  # puede ser monto pesos  monto
                            'currency': apg.moneda.id,
                            'fecha_apg': apg.fecha,
                            'nro_afectacion_apg': apg.nro_afectacion_siif
                        }))
                # llave presupuestal del primer APG correspondiente al PC
                if pc.apg_ids:
                    for apg in pc.apg_ids:
                        if apg.id == oc.pc_apg_id.id:
                            # for llavep in pc.apg_ids[0].llpapg_ids:  la primera
                            for llavep in apg.llpapg_ids:  # la seleccionada
                                llavep_data.append((0, 0, {
                                    'programa': llavep.programa,
                                    'odg': llavep.odg,
                                    'auxiliar': llavep.auxiliar,
                                    'disponible': llavep.disponible,
                                    'proyecto': llavep.proyecto,
                                    'fin': llavep.fin,
                                    'mon': llavep.mon,
                                    'tc': llavep.tc,
                                    'importe': llavep.importe
                                }))
            if apg_ids or llavep_data:
                self.write(cr, uid, ids, {'page_apg_oc': apg_ids, 'llpapg_ids': llavep_data}, context=context)
        return True

    #TODO: ver si no hay que pasarle mas datos de SIIF que vienen de la OC
    def _prepare_invoice_grp(self, cr, uid, order, line_ids, context=None):
        """Prepare the dict of values to create the new invoice for a
           purchase order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: purchase.order record to invoice
           :param list(int) line_ids: list of invoice line IDs that must be
                                      attached to the invoice
           :return: dict of value to create() the invoice
        """
        if context is None:
            context = {}
        context = dict(context)

        inv_data = super(grp_orden_compra, self)._prepare_invoice_grp(cr, uid, order, line_ids, context=context)

        # adicionando campos numero compromiso y no obligacion desde la OC
        monto_oc = math.floor(order.total_llavep or 0)
        monto_oc = int(monto_oc)
        inv_data.update({'nro_compromiso': order.nro_compromiso or False, 'monto_comprometido': monto_oc or 0, 'currency_id':order.currency_oc.id})

        # adicionando campos no afectacion y monto autorizado desde la primera APG
        if order.pc_apg_id:
            first_apg = order.pc_apg_id
            monto_apg = math.floor(first_apg.total_llavep)
            monto_apg = int(monto_apg)
            # TODO R SPRING X ADICIONANDO CABEZALES SIIF A LA FACTURA A PARTIR DE LA APG
            inv_data.update({'nro_afectacion': first_apg.nro_afectacion_siif or False,
                             'monto_afectado': monto_apg or 0,
                             'siif_tipo_ejecucion':first_apg.siif_tipo_ejecucion.id,
                             'siif_concepto_gasto':first_apg.siif_concepto_gasto.id,
                             'siif_financiamiento':first_apg.siif_financiamiento.id,
                             'siif_codigo_sir':first_apg.siif_codigo_sir.id,
                             'siif_nro_fondo_rot':first_apg.siif_nro_fondo_rot.id,
                             })  # cambiando nro_afectacion 23/10
            # inv.update({'nro_afectacion': first_apg.nro_afectacion_apg or False, 'monto_afectado': monto_apg or 0})

            # # TODO R SPRING X NO LLEVAR LAS LLAVES PRESUPUESTALES POR DEFECTO
            # if order.pc_apg_id.llpapg_ids:
            #     llavep_ids = []
            #     for llavep in order.pc_apg_id.llpapg_ids:
            #         llavep_ids.append((0, 0, {
            #             'programa_id': llavep.programa_id.id,
            #             'odg_id': llavep.odg_id.id,
            #             'auxiliar_id': llavep.auxiliar_id.id,
            #             'disponible': llavep.disponible,
            #             'proyecto_id': llavep.proyecto_id.id,
            #             'fin_id': llavep.fin_id.id,
            #             'mon_id': llavep.mon_id.id,
            #             'tc_id': llavep.tc_id.id,
            #             'importe': llavep.importe
            #         }))
            #     inv_data.update({'llpapg_ids': llavep_ids})

        return inv_data

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or dict({})
        default.update({
            'nro_comp_sist_aux': False,
            'nro_compromiso': False,
            'anulada_siif': False,
            'anulacion_siif_log_ids': False,
        })
        context = context or {}
        context = dict(context)
        context.update({'copy': True})  # Perder el control de estado desafectado cuando se copia
        return super(grp_orden_compra, self).copy(cr, uid, id, default, context=context)

    def oc_impactar_presupuesto(self, cr, uid, ids, context=None):
        estructura_obj = self.pool.get('presupuesto.estructura')
        for oc in self.browse(cr, uid, ids, context=context):
            # Control 1: que la sumatoria de llave no sea la misma que la OC
            if oc.total_llavep != oc.amount_total_base:
                # Mostrar error y salir
                raise osv.except_osv('Error',
                                     'La sumatoria de importes de llaves presupuestales no es igual al monto total de la Orden de Compra.')

            for llave in oc.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(cr, uid, oc.fiscalyear_siif_id.id,
                                                               oc.inciso_siif_id.inciso,
                                                               oc.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                # Control 2: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (oc.fiscalyear_siif_id.code, oc.inciso_siif_id.inciso, oc.ue_siif_id.ue, llave.odg,
                                  llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                    raise osv.except_osv('Error', u'No se encontró estructura con la llave presupuestal asociada a la Orden de Compra: ' + desc_error)

                # Control 3: que no alcance el disponible para el monto de la llave presupuestal
                # if estructura.disponible < llave.importe:
                #    raise osv.except_osv('Error', 'El disponible de la estructura no es suficiente para cubrir el importe de la llave presupuestal.')

                res_comprometer = estructura_obj.comprometer(cr, uid, oc.id, TIPO_DOCUMENTO.ORDEN_COMPRA, llave.importe,
                                                             estructura)
        return True

    def oc_enviar_siif(self, cr, uid, ids, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for oc in self.browse(cr, uid, ids, context):
            if oc.partner_id.tipo_doc_rupe == '':
                raise osv.except_osv((''), (u'El proveedor debe tener configurado tipo y número de documento de RUPE.'))
            if oc.partner_id.nro_doc_rupe == '':
                raise osv.except_osv((''), (u'El proveedor debe tener configurado tipo y número de documento de RUPE.'))

            # se compromete contra el SIIF
            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': oc.fiscalyear_siif_id and oc.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_comp_sist_aux = self.pool.get('ir.sequence').get(cr, uid, 'sec.siif.compromiso', context=context)
            nro_comp_sist_aux = nro_comp_sist_aux[4:]

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if oc.siif_financiamiento.exceptuado_sice or oc.siif_tipo_ejecucion.exceptuado_sice or oc.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in oc.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name', '=', llave_pres.odg),
                                                                         ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise osv.except_osv(('Error'),
                                             (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                             llave_pres.odg, llave_pres.auxiliar))

            xml_oc = generador_xml.gen_xml_oc(cr, uid, orden_compra=oc, llaves_presupuestales=oc.llpapg_ids,
                                                importe=oc.amount_total_base, nro_carga=nro_carga, tipo_doc_grp='02',
                                                nro_modif_grp=0,
                                                tipo_modificacion='A',
                                                enviar_datos_sice=enviar_datos_sice,
                                                nro_comp_sist_aux=nro_comp_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_oc)

            #conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_compromiso', None) is None and movimiento.find(
                        'nro_compromiso').text and movimiento.find('nro_compromiso').text.strip():
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('resultado', None) is None and movimiento.find(
                        'resultado').text and movimiento.find('resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_compromiso', None) is None and movimiento.find(
                        'sec_compromiso').text and movimiento.find('sec_compromiso').text.strip():
                    dicc_modif['siif_sec_compromiso'] = movimiento.find('sec_compromiso').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al comprometer en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_compromiso', False) and dicc_modif.get('nro_compromiso',False).strip() and dicc_modif.get('resultado', False):
                    break

            # error en devolucion de numero de compromiso
            if not dicc_modif.get('nro_compromiso', None):
                raise osv.except_osv(('Error al comprometer en SIIF'),
                                     (descr_error or u'Error en devolución de número de compromiso por el SIIF'))

            dicc_modif['nro_comp_sist_aux'] = nro_comp_sist_aux
            # 004 Pasa a Comprometido = True
            dicc_modif['anulada_siif'] = False
            res_write = self.write(cr, uid, oc.id, dicc_modif, context=context)

            if res_write:
                modif_compromiso_log_obj = self.pool.get('wiz.modif_compromiso_siif_log')
                for llave in oc.llpapg_ids:
                    vals = {
                        'oc_id': oc.id,
                        'tipo': 'A',
                        'fecha': fields.date.context_today(self, cr, uid, context=context),
                        'programa': llave.programa,
                        'proyecto': llave.proyecto,
                        'moneda': llave.mon,
                        'tipo_credito': llave.tc,
                        'financiamiento': llave.fin,
                        'objeto_gasto': llave.odg,
                        'auxiliar': llave.auxiliar,
                        'importe': llave.importe,
                        'siif_sec_compromiso': dicc_modif.get('siif_sec_compromiso', False),
                        'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                    }
                    modif_compromiso_log_obj.create(cr, uid, vals, context=context)
        return True


    def purchase_commit(self, cr, uid, ids, context=None):
        res = super(grp_orden_compra, self).purchase_commit(cr, uid, ids, context=context)

        self.oc_impactar_presupuesto(cr, uid, ids, context=context)

        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        integracion_siif = company.integracion_siif or False
        if not integracion_siif:
            return res
        else:
            return self.oc_enviar_siif(cr, uid, ids, context=context)

    def oc_desafectar_presupuesto(self, cr, uid, ids, context=None):
        estructura_obj = self.pool.get('presupuesto.estructura')
        for oc in self.browse(cr, uid, ids, context=context):
            # #COMENTADO
            # 103- Sacado control de llaver presupuestal al enviar modificacion de compromiso, inc 512, 10/03
            # # Control 1: que la sumatoria de llave no sea la misma que la OC
            # if oc.total_llavep != oc.amount_total_base:
            #     raise osv.except_osv('Error', 'La sumatoria de importes de llaves presupuestales no es igual al monto total de la Orden de Compra.')
            for llave in oc.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(cr, uid, oc.fiscalyear_siif_id.id,
                                                               oc.inciso_siif_id.inciso,
                                                               oc.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                # Control 2: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (oc.fiscalyear_siif_id.code, oc.inciso_siif_id.inciso, oc.ue_siif_id.ue, llave.odg,
                                  llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                    raise osv.except_osv('Error',
                                         u'No se encontró estructura con la llave presupuestal asociada a la Orden de Compra: ' + desc_error)
                # Control 3: que no alcance el disponible para el monto de la llave presupuestal
                # if estructura.disponible < llave.importe:
                #    raise osv.except_osv('Error',
                # 'El disponible de la estructura no es suficiente para cubrir el importe de la llave presupuestal.')
                res_comprometer = estructura_obj.comprometer(cr, uid, oc.id, TIPO_DOCUMENTO.ORDEN_COMPRA,
                                                             -1 * llave.importe, estructura)
        return True


    def oc_desafectar_siif(self, cr, uid, ids, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for oc in self.browse(cr, uid, ids, context):
            if oc.siif_tipo_ejecucion and oc.siif_tipo_ejecucion.codigo == 'P' and not oc.siif_nro_fondo_rot:
                raise osv.except_osv(('Error'),
                                     (u'Si el tipo de ejecución es Fondo Rotatorio, se debe cargar Nro. de Fondo Rotatorio.'))
            if oc.partner_id.tipo_doc_rupe == '':
                raise osv.except_osv((''), (u'El proveedor debe tener configurado tipo y número de documento de RUPE.'))
            if oc.partner_id.nro_doc_rupe == '':
                raise osv.except_osv((''), (u'El proveedor debe tener configurado tipo y número de documento de RUPE.'))

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if oc.siif_financiamiento.exceptuado_sice or oc.siif_tipo_ejecucion.exceptuado_sice or oc.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in oc.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name', '=', llave_pres.odg),
                                                                         ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise osv.except_osv(('Error'),
                                             (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                             llave_pres.odg, llave_pres.auxiliar))

            nro_modif = oc.siif_ult_modif + 1

            # se compromete contra el SIIF
            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': oc.fiscalyear_siif_id and oc.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            monto_anular = 0
            for llave in oc.llpapg_ids:
                monto_anular += llave.importe
            monto_anular *= -1

            # Anular Compromiso ------------------
            xml_anular_oc = generador_xml.gen_xml_oc(cr, uid, orden_compra=oc, llaves_presupuestales=oc.llpapg_ids,
                                                       importe=monto_anular, nro_carga=nro_carga, tipo_doc_grp='02',
                                                       nro_modif_grp=nro_modif, tipo_modificacion='N', es_modif=True,
                                                       motivo="Anulacion de compromiso",
                                                       enviar_datos_sice=enviar_datos_sice,
                                                       nro_comp_sist_aux=oc.nro_comp_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_anular_oc)

            #conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_compromiso', None) is None and movimiento.find(
                        'nro_compromiso').text and movimiento.find('nro_compromiso').text.strip():
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('resultado', None) is None and movimiento.find('resultado').text and movimiento.find(
                        'resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_compromiso', None) is None and movimiento.find(
                        'sec_compromiso').text and movimiento.find('sec_compromiso').text.strip():
                    dicc_modif['siif_sec_compromiso'] = movimiento.find('sec_compromiso').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al comprometer en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_compromiso', False) and dicc_modif.get('nro_compromiso',
                                                                              False).strip() and dicc_modif.get('resultado', False):
                    break

            anulacion_oc_log_obj = self.pool.get('compromiso.oc.anulacion.siif.log')
            # anulacion_siif_log_ids
            vals_history = {
                'orden_id': oc.id,
                'nro_afectacion_siif': oc.nro_afectacion_siif or 0,
                'nro_compromiso': oc.nro_compromiso or 0,
                'nro_comp_sist_aux': oc.nro_comp_sist_aux or False,
            }
            id = anulacion_oc_log_obj.create(cr, uid, vals_history, context=context)
            # Borrando valores
            ids_delete = []
            for idm in oc.modif_compromiso_log_ids:
                ids_delete.append(idm.id)
            if ids_delete:
                self.pool.get('wiz.modif_compromiso_siif_log').unlink(cr, uid, ids_delete)
            # Pasa a Comprometido = True
            dicc_modif.update(
                {'nro_comp_sist_aux': False, 'nro_compromiso': False, 'comprometido': False, 'anulada_siif': True})
            res_write = self.write(cr, uid, oc.id, dicc_modif, context=context)
        return True

    def button_anular_compromiso_oc(self, cr, uid, ids, context=None):
        self.oc_desafectar_presupuesto(cr, uid, ids, context=context)
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        integracion_siif = company.integracion_siif or False
        if not integracion_siif:
            return True
        else:
            return self.oc_desafectar_siif(cr, uid, ids, context=context)


    # MODIFICACION DE COMPROMISO
    def enviar_modificacion_siif(self, cr, uid, id, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        programa = context['programa']
        proyecto = context['proyecto']
        moneda = context['moneda']
        tipo_credito = context['tipo_credito']
        tipo_modificacion = context['tipo_modificacion']
        financiamiento = context['financiamiento']
        objeto_gasto = context['objeto_gasto']
        auxiliar = context['auxiliar']
        importe = context['importe']
        fecha = context['fecha']
        motivo = context['motivo']
        auxiliar_id = context['auxiliar_id']
        fin_id = context['fin_id']
        mon_id = context['mon_id']
        odg_id = context['odg_id']
        programa_id = context['programa_id']
        proyecto_id = context['proyecto_id']
        tc_id = context['tc_id']

        lineas_llavep_obj = self.pool.get('grp.compras.lineas.llavep')
        condicion = []
        condicion.append(('order_id', '=', id))
        condicion.append(('programa', '=', programa))
        condicion.append(('proyecto', '=', proyecto))
        condicion.append(('odg', '=', objeto_gasto))
        condicion.append(('auxiliar', '=', auxiliar))
        condicion.append(('fin', '=', financiamiento))
        condicion.append(('mon', '=', moneda))
        condicion.append(('tc', '=', tipo_credito))
        llavep_id = lineas_llavep_obj.search(cr, uid, condicion, context=context)
        if len(llavep_id) < 1:
            if tipo_modificacion != 'A':
                raise osv.except_osv(('Error'), (u'La llave presupuestal ingresada no se encuentra en la OC.'))
            else:
                vals = {
                    'order_id': id,
                    'fin_id': fin_id,
                    'programa_id': programa_id,
                    'proyecto_id': proyecto_id,
                    'odg_id': odg_id,
                    'auxiliar_id': auxiliar_id,
                    'mon_id': mon_id,
                    'tc_id': tc_id,
                    'importe': 0,
                }
                llavep_id = lineas_llavep_obj.create(cr, uid, vals, context=context)
                llavep_id = [llavep_id]

        llavep = lineas_llavep_obj.browse(cr, uid, llavep_id, context=context)
        llavep = llavep[0]

        # 'purchase.order'
        oc = self.browse(cr, uid, id, context)

        # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
        enviar_datos_sice = False
        if oc.siif_financiamiento.exceptuado_sice or oc.siif_tipo_ejecucion.exceptuado_sice or oc.siif_concepto_gasto.exceptuado_sice:
            enviar_datos_sice = False
        else:
            objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
            objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name', '=', objeto_gasto), ('auxiliar', '=', auxiliar)])
            if len(objeto_gasto_ids) > 0:
                ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                if not ogasto.exceptuado_sice:
                    enviar_datos_sice = True
            else:
                raise osv.except_osv(('Error'),
                                     (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (objeto_gasto, auxiliar))

        # SE AFECTA CONTRA LA ESTRUCTURA LOCAL
        estructura_obj = self.pool.get('presupuesto.estructura')
        estructura = estructura_obj.obtener_estructura(cr, uid, oc.fiscalyear_siif_id.id, oc.inciso_siif_id.inciso,
                                                       oc.ue_siif_id.ue,
                                                       programa, proyecto, moneda, tipo_credito,
                                                       financiamiento, objeto_gasto, auxiliar)

        if estructura is None:
            desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                         (oc.fiscalyear_siif_id.code, oc.inciso_siif_id.inciso, oc.ue_siif_id.ue, objeto_gasto,
                          auxiliar, financiamiento, programa, proyecto, moneda, tipo_credito)
            raise osv.except_osv('Error',
                                 u'No se encontró estructura con la llave presupuestal asociada a la Orden de Compra: ' + desc_error)

        # ** Falta agregar controles **
        res = estructura_obj.comprometer(cr, uid, oc, TIPO_DOCUMENTO.ORDEN_COMPRA, importe, estructura)

        if res['codigo'] == 1:
            # SE COMPROMETE CONTRA SIIF
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            integracion_siif = company.integracion_siif or False
            if not integracion_siif:
                return True

            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': oc.fiscalyear_siif_id and oc.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_modif = oc.siif_ult_modif + 1

            xml_modificar_oc = generador_xml.gen_xml_oc(cr, uid, orden_compra=oc, llaves_presupuestales=[llavep],
                                                          importe=importe,
                                                          nro_carga=nro_carga, tipo_doc_grp='02',
                                                          nro_modif_grp=nro_modif,
                                                          tipo_modificacion=tipo_modificacion, es_modif=True,
                                                          motivo=motivo,
                                                          enviar_datos_sice=enviar_datos_sice,
                                                          nro_comp_sist_aux=oc.nro_comp_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_modificar_oc)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_compromiso', None) is None:
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('resultado', None) is None:
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_compromiso', None) is None:
                    dicc_modif['siif_sec_compromiso'] = movimiento.find('sec_compromiso').text
                if dicc_modif.get('siif_ult_modif', None) is None:
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al comprometer en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_compromiso', False) and dicc_modif.get('nro_compromiso', False).strip()\
                        and dicc_modif.get('resultado', False):
                    break

            res_write_oc = self.write(cr, uid, oc.id, dicc_modif, context=context)

            if res_write_oc:
                # Actualizar importe
                val_modif = {
                    'importe': importe + llavep.importe,
                }
                res_write = lineas_llavep_obj.write(cr, uid, llavep.id, val_modif, context=context)

                if res_write:
                    modif_log_obj = self.pool.get('wiz.modif_compromiso_siif_log')
                    vals = {
                        'oc_id': id,
                        'tipo': tipo_modificacion,
                        'fecha': fecha,
                        'programa': programa,
                        'proyecto': proyecto,
                        'moneda': moneda,
                        'tipo_credito': tipo_credito,
                        'financiamiento': financiamiento,
                        'objeto_gasto': objeto_gasto,
                        'auxiliar': auxiliar,
                        'importe': importe,
                        'siif_sec_compromiso': dicc_modif.get('siif_sec_compromiso', False),
                        'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                    }
                    modif_log_obj.create(cr, uid, vals, context=context)
        return True

    # TODO: GAP 456 SPRING 6
    #TODO MVARELA este metodo no se llama mas, ver de meterlo en el estandar confirm
    # TODO R GAP 456 MODIFICANDO LLAMADA POR CAMBIO DE  FLUJO EN LA OC
    def wkf_confirm_order(self, cr, uid, ids, context=None):
        #RAGU ps07 323
        #MVARELA: solo se controla el compromiso si no es una migracion
        order = self.browse(cr, uid, ids[0], context=context)
        if not order.es_migracion:
            self.check_compromiso(cr, uid, ids, context=context)
        super(grp_orden_compra, self).wkf_confirm_order(cr, uid, ids, context=context)

    def check_compromiso(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            if not (order.doc_origen and order.doc_origen.provider_compromise_ids and order.doc_origen.provider_compromise_ids.filtered(lambda x: x.state == 'committed')):
                raise osv.except_osv(('Error!!'), (
                    u"No se ha identificado ningún compromiso en estado 'Comprometido' para este proveedor que corresponda a la adjudicación!"))
            Total_compromise = 0
            orders_total_amount = 0
            if order.doc_origen and order.doc_origen.provider_compromise_ids:
                year = order.fiscalyear_siif_id
                provider = order.partner_id
                compromise = order.doc_origen.provider_compromise_ids.filtered(lambda x: x.fiscalyear_id.id == year.id
                                                                                         and x.provider_id.id == provider.id)
                if compromise:
                    Total_compromise = sum(map(lambda c: c.total_comprometido, compromise))
                orders = self.search(cr, uid, [('partner_id', '=', provider.id),
                                               ('fiscalyear_siif_id', '=', year.id),
                                               ('doc_origen', '=', order.doc_origen.id),
                                               ('id', '!=', order.id),
                                               ('state', '=', 'confirmed')])
                if orders:
                    orders_total_amount = sum(map(lambda o: o.amount_total_base, self.browse(cr, uid, orders, context=context)))
                if order.amount_total_base + orders_total_amount > Total_compromise:
                    raise osv.except_osv(('Error!!'), (
                        'La orden de Compra no se puede confirmar debido a que el total estimado en pesos supera el monto comprometido.'))

grp_orden_compra()


