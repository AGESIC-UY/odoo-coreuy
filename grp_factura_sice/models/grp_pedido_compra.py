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

_logger = logging.getLogger(__name__)

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp.addons.grp_sice.grp_sice import soap_sice

class grp_pedido_compra(osv.osv):
    _inherit = 'grp.pedido.compra'

    def sice_compra_alta_response(self, cr, uid, ids, response, context=None):
        # import sys
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        # response ==> compra
        # Guardamos el número de compra asignado por SICE
        self.write(cr, uid, ids, {'sice_id_compra': response.idCompra, 'sice_id_estado': response.codEstado,
                                  'sice_desc_estado': response.descEstado})
        return True

    @soap_sice.compra(request='alta', response='sice_compra_alta_response')
    def enviar_sice_compra_alta(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)

        if not obj.sicec_uc_id:
            raise osv.except_osv(_('Error!'), _(u'Por favor ingrese la unidad de compra.'))
        if not obj.sub_tipo_compra:
            raise osv.except_osv(_('Error!'), _(u'Por favor ingrese el subtipo de compra.'))
        # Cabezal
        compraAlta = {
            'idInciso': int(obj.sicec_uc_id.idInciso.idInciso),
            'idUE': int(obj.sicec_uc_id.idUE.idUE),
            'idUC': int(obj.sicec_uc_id.idUC),
            'idTipoCompra': obj.tipo_compra.idTipoCompra,
            'idSubtipoCompra': obj.sub_tipo_compra.idSubtipoCompra,
            'fondosRotatorios': 'N',
            'nroCompra': int(obj.name.split('-')[3]),
            'anioCompra': int(obj.date_start[0:4]),
            'anioFiscal': int(obj.date_start[0:4]),
            'itemsCompra': []
        }
        # Lines
        nroSecuencia = 0
        for articulo in obj.resumen_pedido_compra_ids:
            itemCompra = {}
            nroSecuencia += 1
            itemCompra['nroItem'] = nroSecuencia
            itemCompra['cantidad'] = round(articulo.cantidad_a_comprar,2)
            itemCompra['precioUnitario'] = round(articulo.precio_pesos_sin_iva,4)
            itemCompra['articulo'] = {}
            if articulo.product_id.grp_sice_cod > 0:
                itemCompra['articulo']['codArticulo'] = articulo.product_id.grp_sice_cod
                # Se agregan los campos para mandar a SICE correspondientes a valores de atributos
                # de dimension SICE
                if articulo.product_id.med_cod_id:
                    itemCompra['articulo']['codMedidaVariante'] = articulo.product_id.med_cod_id.cod
                if articulo.product_id.pres_id:
                    itemCompra['articulo']['codPresentacion'] = articulo.product_id.pres_id.cod
                    pres_obj = self.pool.get('grp.sice_presentacion').browse(cr, uid, articulo.product_id.pres_id.id)
                    codigo = pres_obj.unme_cod
                    itemCompra['articulo']['codUnidadPresentacion'] = codigo
                if articulo.product_id.med_cod_pres_id:
                    itemCompra['articulo']['codMedidaPresentacion'] = articulo.product_id.med_cod_pres_id.cod
                if articulo.product_id.det_variante_id:
                    itemCompra['articulo']['codDetalleVariante'] = articulo.product_id.det_variante_id.cod
                if articulo.product_id.sice_color_id:
                    itemCompra['articulo']['codColor'] = articulo.product_id.sice_color_id.cod
                # 001-Fin
            else:
                raise osv.except_osv(_('Error!'), _(u'El producto seleccionado no tiene código SICE.'))

            # cr.execute("select unme_cod, imp_cod from sice_art_serv_obra where cod = %(cod)s",
            #            {'cod': articulo.product_id.grp_sice_cod})
            # res = cr.fetchone()
            if not articulo.uom_id.cod_udm:
                raise osv.except_osv('Error!', u'La unidad de medida del artículo %s no es correcta.' % (
                articulo.product_id.name,))
            itemCompra['articulo']['codUnidad'] = articulo.uom_id.cod_udm
            if articulo.iva:
                iva = articulo.iva[0].id
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
                                             articulo.iva[0].name, articulo.product_id.name))
                    itemCompra['codImpuestos'] = tax_id
                else:
                    raise osv.except_osv('Error!',
                                         u'No existe el mapeo entre impuestos de GRP y SICE para impuesto %s.' % (
                                         articulo.iva[0].name,))
            else:
                raise osv.except_osv('Error!',
                                     u'El artículo %s no tiene impuesto definido.' % (articulo.product_id.name,))
            compraAlta['itemsCompra'].append(itemCompra)
        return compraAlta

    def sice_ampliacion_alta_response(self, cr, uid, ids, response, context=None):
        # import sys
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        # response ==> ampliacion
        # Guardamos el número de compra asignado por SICE
        self.write(cr, uid, ids, {'sice_id_compra': response.idCompra, 'sice_id_estado': response.codEstado,
                                  'nro_ampliacion': response.nroAmpliacion, 'sice_desc_estado': response.descEstado})
        return True

    @soap_sice.ampliacion(request='alta', response='sice_ampliacion_alta_response')
    def enviar_sice_pedido_ampliado_alta(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)
        if not obj.tipo_de_resolucion:
            raise osv.except_osv(_('Error!'), _(u'Debe definir el tipo de resolución a enviar a SICE.'))
        ampliacion_compraAlta = {
            'codEstado': 13,
            'tipoAmpliacion': 'A' if not obj.renovacion else 'R',
            'esReiteracion': 'N',
            'idTipoResolucion': obj.tipo_de_resolucion and int(obj.tipo_de_resolucion) or False,
            'formaPago': obj.forma_pago_amp or '' if obj.tipo_licitacion else '',
            'condicionesEntrega': obj.cond_pago_amp or '' if obj.tipo_licitacion else '',
            'fondosRotatorios': 'N',
            'idCompraOrig': obj.pc_origen_ampliacion_id.sice_id_compra,
            'fechaResolucion': obj.date_start,
            'items': []
        }

        for articulo in obj.resumen_pedido_compra_ids:
            itemCompra = {
                'cantidad': round(articulo.cantidad_a_comprar,2),
                'idItem': articulo.id_item,
                'idVariacion': articulo.id_variacion,
                'precioUnitario': round(articulo.precio_sin_iva,4),
                'proveedor': {
                    'nroDocProv': articulo.nroDocProv,
                    'tipoDocProv': articulo.tipoDocProv
                }
            }
            # cr.execute("select unme_cod, imp_cod from sice_art_serv_obra where cod = %(cod)s",
            #            {'cod': articulo.product_id.grp_sice_cod})
            # res = cr.fetchone()
            if articulo.iva:
                iva = articulo.iva[0].id
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
                                             articulo.iva[0].name, articulo.product_id.name))
                    itemCompra['codImpuestos'] = tax_id
                else:
                    raise osv.except_osv('Error!',
                                         u'No existe el mapeo entre impuestos de GRP y SICE para impuesto %s.' % (
                                         articulo.iva[0].name,))
            else:
                raise osv.except_osv('Error!',
                                     u'El artículo %s no tiene impuesto definido.' % (articulo.product_id.name,))
            ampliacion_compraAlta['items'].append(itemCompra)
        return ampliacion_compraAlta

    def act_pc_sice(self, cr, uid, ids, context=None):
        super(grp_pedido_compra, self).act_pc_sice(cr, uid, ids, context=context)
        pc = self.browse(cr, uid, ids)[0]
        if pc.es_migracion:
            if pc.anio_de_compra and pc.date_start and pc.anio_de_compra != int(pc.date_start[0:4]):
                raise osv.except_osv('Error!', u'La fecha de creación de la compra en SICE y GRP no coinciden')
            if not pc.total_estimado:
                raise osv.except_osv('Error!', u"La importación del pedido de compras no incluye datos sobre el producto, cantidad y precio estimado. Por favor ingresar estos datos")
            return self.importar_compra_sice(cr, uid, ids, context=context)
        #cuando es licitacion o ampliacion no se envia a SICE porque ya se envio antes
        #se controla tambien que no tenga id_sice para enviar
        if not pc.tipo_licitacion and not pc.ampliacion and not pc.sice_id_compra:
            return self.button_enviar_sice(cr, uid, ids, context=context)
        return True

    def button_enviar_sice(self, cr, uid, ids, context=None):
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context).company_id
        integracion_sice = company.integracion_sice or False
        if not integracion_sice:
            return True
        # llamada a integracion con sice para pedido de compra ampliado
        pc = self.browse(cr, uid, ids)[0]
        if pc.ampliacion and pc.pc_origen_ampliacion_id and pc.pc_origen_ampliacion_id.id:
            return self.enviar_sice_pedido_ampliado_alta(cr, uid, ids, context=context)
        return self.enviar_sice_compra_alta(cr, uid, ids, context=context)

    def button_enviar_sice_ampliacion(self, cr, uid, ids, context=None):
        return self.enviar_sice_pedido_ampliado_alta(cr, uid, ids, context=context)


    def sice_compra_buscar_response(self, cr, uid, ids, response, context=None):
        # import sys
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        # response ==> compra
        # Guardamos el número de compra asignado por SICE
        _logger.info("La respuesta de buscar en SICE es: %s", str(response))
        # self.write(cr, uid, ids, {'sice_id_compra': response.idCompra, 'sice_id_estado': response.codEstado,
        #                           'sice_desc_estado': response.descEstado})
        return response

    @soap_sice.compra(request='buscar', response='sice_compra_buscar_response')
    def sice_compra_buscar(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)
        if obj.tipo_compra.idTipoCompra != 'CM' and not obj.sicec_uc_id:
            raise osv.except_osv(_('Error!'), _(u'Por favor ingrese la unidad de compra.'))
        # Parametros de busqueda
        compraBuscar = {
            # 'idInciso': int(obj.sicec_uc_id.idInciso.idInciso),
            # 'idUE': int(obj.sicec_uc_id.idUE.idUE),
            # 'idUC': int(obj.sicec_uc_id.idUC),
            'idTipoCompra': obj.tipo_compra.idTipoCompra,
            'nroCompra': obj.nro_de_procedimiento,
            'anioCompra': obj.anio_de_compra,
            'anioFiscal': obj.anio_fiscal,
            'nroAmpliacion': obj.nro_de_ampliacion,
        }
        return compraBuscar

    def importar_compra_sice(self, cr, uid, ids, context=None):
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context).company_id
        integracion_sice = company.integracion_sice or False
        if not integracion_sice:
            return True
        result = self.sice_compra_buscar(cr, uid, ids, context=context)
        if result:
            compra_importar = False
            pedido = self.browse(cr, uid, ids[0], context=context)
            for compra in result:
                if (pedido.tipo_compra.idTipoCompra == compra.idTipoCompra == 'CM') or (compra.idUC == pedido.sicec_uc_id.idUC and compra.idUE == int(pedido.operating_unit_id.code)):
                    compra_importar = compra
            if compra_importar:
                name = "%(anio)s-%(inciso)s-%(tipo_compra)s-%(nro_compra)s" % {'anio': compra_importar.anioCompra,
                                                                               'inciso': company.inciso,
                                                                               'tipo_compra': compra_importar.idTipoCompra,
                                                                               'nro_compra': str(compra_importar.nroCompra).zfill(5)}
                vals = {'sice_id_compra': compra_importar.idCompra, 'name': name}
                if compra_importar.nroAmpliacion:
                    vals.update({'ampliacion': True, 'nro_ampliacion': compra_importar.nroAmpliacion})
                self.write(cr, uid, ids, vals, context=context)
                return True
            else:
                raise osv.except_osv(_('Error!'), _(u'Se encontraron compras para los datos ingresados, pero no coinciden la Unidad ejecutora y/o Unidad de compra: %s') % (result,))
        else:
            raise osv.except_osv(_('Error!'), _(u'No se encontró compra para los datos ingresados'))

grp_pedido_compra()