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
from openerp import SUPERUSER_ID
from openerp.addons.grp_sice.grp_sice import soap_sice

import logging

_logger = logging.getLogger(__name__)

class grp_orden_compra(osv.osv):
    _inherit = 'purchase.order'

    @soap_sice.orden_compra(request='aprobar')
    def enviar_orden_compra_sice_aprobar(self, cr, uid, ids, context=None):
        if not context.get('idOC', False):
            raise osv.except_osv("Error", "ID de la orden de compra no encontrado")
        return context['idOC']

    @soap_sice.orden_compra(request='alta')
    def enviar_orden_compra_sice_alta(self, cr, uid, ids, context=None):
        # El "cabezal"
        obj = self.browse(cr, uid, ids[0], context=context)
        ordenCompraAlta = {
            'nroOC': int(obj.name.split('-')[3]),
            'fechaOC': obj.date_order[:10],
            'itemsAlta': [],
        }
        if obj.descripcion:
            ordenCompraAlta['observacion'] = obj.descripcion[:500]
        # MVARELA - Se envia el codigo moneda SICE que vino de la adjudicacion.
        if obj.cod_moneda:
            ordenCompraAlta['codMoneda'] = obj.cod_moneda.codMoneda
        else:
            raise osv.except_osv('Error!', u'La órden de compra no tiene asignado el código de moneda SICE.')

        if obj.partner_id.tipo_doc_rupe and obj.partner_id.nro_doc_rupe:
            ordenCompraAlta['proveedor'] = {
                'tipoDocProv': obj.partner_id.tipo_doc_rupe,
                'nroDocProv': obj.partner_id.nro_doc_rupe
            }
        else:
            raise osv.except_osv('Error!', u'El proveedor no tiene configurado los datos de RUPE')
        if obj.pedido_compra_id.sice_id_compra:
            ordenCompraAlta['idCompra'] = obj.pedido_compra_id.sice_id_compra
        else:
            raise osv.except_osv('Error!', u'El pedido de compra no tiene Nro SICE')
        if obj.horario_dir:
            ordenCompraAlta['lugarEntrega'] = obj.horario_dir[:60]
        if obj.plazo_entrega_sel:
            plazo = dict(self.fields_get(cr, uid, allfields=['plazo_entrega_sel'], context=context)['plazo_entrega_sel']['selection'])[obj.plazo_entrega_sel]
            ordenCompraAlta['plazoEntrega'] = plazo
        # Las "líneas"
        for articulo in obj.order_line:
            #control decimales en las cantidades
            if articulo.product_qty != round(articulo.product_qty, 2):
                raise osv.except_osv('Error!', u'SICE sólo acepta 2 decimales en las cantidades')

            itemOC = {
                'idItem': articulo.id_item,
                'idVariacion': articulo.id_variacion,
                'cantidad': round(articulo.product_qty, 2),
                'precioUnitario': round(articulo.precio_sin_iva,4),
                # 'codImpuestos': articulo.taxes_id,
            }

            # cr.execute("select unme_cod, imp_cod from sice_art_serv_obra where cod = %(cod)s",
            #            {'cod': articulo.product_id.grp_sice_cod})
            # res = cr.fetchone()

            if articulo.taxes_id:
                iva = articulo.taxes_id[0].id
                cr.execute("select imp_sice from grp_art_impuestos where cast (imp_grp as float) = %(imp_grp)s",
                           {'imp_grp': iva})
                if cr.rowcount > 0:
                    res = cr.fetchone()
                    tax_id = (res[0][0])
                    # cr.execute(
                    #     "select 1 from sice_art_impuestos where arse_cod = %(art_cod)s and imp_cod = %(imp_sice)s",
                    #     {'art_cod': articulo.product_id.grp_sice_cod, 'imp_sice': tax_id})
                    cr.execute(
                        """select 1 from grp_sice_art_impuesto
                        where articulo_id = (select id from grp_sice_art_serv_obra where cod = %(art_cod)s)
                        and impuesto_id = (select id from grp_sice_impuesto where cod = %(imp_sice)s)""",
                        {'art_cod': articulo.product_id.grp_sice_cod, 'imp_sice': tax_id})
                    if cr.rowcount == 0:
                        raise osv.except_osv('Error!',
                                             u'El impuesto %s no está definido en SICE para el artículo %s.' % (
                                             articulo.taxes_id[0].name, articulo.product_id.name))
                    itemOC['codImpuestos'] = tax_id
                else:
                    raise osv.except_osv('Error!',
                                         u'No existe el mapeo entre impuestos de GRP y SICE para impuesto %s.' % (
                                         articulo.taxes_id[0].name,))
            else:
                #Solo controlo impuesto cuando el monto es mayor a 0
                if round(articulo.precio_sin_iva,4):
                    raise osv.except_osv('Error!',
                                         u'El artículo %s no tiene impuesto definido.' % (articulo.product_id.name,))

            ordenCompraAlta['itemsAlta'].append(itemOC)
        return ordenCompraAlta

    def button_oc_enviar_sice(self, cr, uid, ids, context=None):
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context).company_id
        integracion_sice = company.integracion_sice or False
        if not integracion_sice:
            self.write(cr, uid, ids, {'enviado_sice': True})
            return True

        """
        Crea la compra en SICE mediante la invocación del WS 'alta' de
        la interfaz de SICE.
        """
        # compra
        compra = self.enviar_orden_compra_sice_alta(cr, uid, ids, context=context)
        # Guardamos el número de compra asignado por SICE
        self.write(cr, uid, ids, {'sice_id_oc': compra.idOC, 'sice_nro_oc': compra.nroOC, 'enviado_sice': True})
        ctx = context.copy()
        ctx.update({'idOC': compra.idOC})
        # aprobación
        self.enviar_orden_compra_sice_aprobar(cr, uid, ids, context=ctx)
        return True

    def sice_orden_compra_listar_response(self, cr, uid, ids, response, context=None):
        # import sys
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        # response ==> orden_compra
        # Guardamos el número de orden_compra asignado por SICE
        _logger.info("La respuesta de listar en SICE es: %s", str(response))
        # self.write(cr, uid, ids, {'sice_id_compra': response.idCompra, 'sice_id_estado': response.codEstado,
        #                           'sice_desc_estado': response.descEstado})
        return response

    @soap_sice.orden_compra(request='listar', response='sice_orden_compra_listar_response')
    def sice_orden_compra_listar(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)
        if not obj.pedido_compra_id or not obj.pedido_compra_id.sice_id_compra:
            raise osv.except_osv('Error!', u'La Orden de compra no tiene asociado Pedido de compra o el Pedido de compra no tiene ID SICE.')
        if not obj.partner_id.tipo_doc_rupe or not obj.partner_id.nro_doc_rupe:
            raise osv.except_osv('Error!', u'El proveedor no tiene configurado los datos de RUPE')
        # Parametros de busqueda
        ordenCompraListar = {
            'idCompra': obj.pedido_compra_id.sice_id_compra,
            'codEstado': 2,
            'tipoDocProv': obj.partner_id.tipo_doc_rupe,
            'nroDocProv': obj.partner_id.nro_doc_rupe,
        }
        return ordenCompraListar

    def button_oc_importar_sice(self, cr, uid, ids, context=None):
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context).company_id
        integracion_sice = company.integracion_sice or False
        if not integracion_sice:
            return True
        result = self.sice_orden_compra_listar(cr, uid, ids, context=context)
        if result:
            if len(result) == 1:
                orden_compra = result[0]
                vals = {'sice_id_oc': orden_compra.idOC,
                        'sice_nro_oc': orden_compra.nroOC,
                        'enviado_sice': True}
                self.write(cr, uid, ids, vals, context=context)
                return True
            else:
                ocs = []
                for r in result:
                    ocs.append({'idOC': r.idOC,'nroOC': r.nroOC, 'montoTotal': r.montoTotal, 'descMoneda': r.descMoneda, 'fechaOC': str(r.fechaOC)})
                mod_obj = self.pool.get('ir.model.data')
                res = mod_obj.get_object_reference(cr, uid, 'grp_factura_sice', 'wizard_oc_import_sice')
                res_id = res and res[1] or False
                ctx= dict(context)
                ctx.update({'result': ocs, 'active_model': 'purchase.order', 'active_id':ids[0], 'active_ids': ids})
                return {
                    'name': "Importar OC",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': 'wizard.oc.import_sice',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': ctx,
                }
        else:
            raise osv.except_osv('Error!', u'No se encontró Orden de compra para los datos ingresados.')

class wizard_oc_import_sice(osv.osv_memory):
    _name = 'wizard.oc.import_sice'
    _description = "Importar OC desde SICE"

    def _get_lista_ocs(self, cr, uid, context=None):
        result = context.get('result',False)
        select_list = []
        if not result:
            return (('0','0'))
        for r in result:
            info = "Nro: %s, Fecha: %s, Monto: %s, Moneda: %s" % (r['nroOC'], r['fechaOC'], r['montoTotal'], r['descMoneda'])
            select_list.append((str(r['idOC']), info))
        return select_list

    _columns = {
        'orden_sice': fields.selection(_get_lista_ocs, string='Orden de compra', required=True),
    }

    # Importar OC SICE
    def importar_oc_sice(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        id_oc_sice = False
        nro_oc_sice = False
        for r in context.get('result'):
            if str(r['idOC']) == data['orden_sice']:
                id_oc_sice = r['idOC']
                nro_oc_sice = r['nroOC']
        if id_oc_sice and nro_oc_sice:
            self.pool.get('purchase.order').write(cr, uid, [context.get('active_id')], {'sice_id_oc': id_oc_sice,
                                                                                      'sice_nro_oc': nro_oc_sice,
                                                                                      'enviado_sice': True})
            return True
        else:
            raise osv.except_osv('Error!', u'Error al intentar importar OC desde SICE.')
