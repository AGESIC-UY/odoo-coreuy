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
from openerp import SUPERUSER_ID
from openerp.addons.grp_sice.grp_sice import soap_sice
from openerp.tools.translate import _


# ================================================================
## COTIZACIONES
# ================================================================

class grp_cotizaciones(osv.osv):
    _inherit = 'grp.cotizaciones'

    @soap_sice.adjudicacion(request='aprobar')
    def enviar_act_cot_aprobar_sice(self, cr, uid, ids, context=None):
        if not context.get('sice_numeracion', False):
            raise osv.except_osv('Error', u'Numeración SICE compra no encontrado')
        return context['sice_numeracion']

    #DDELFINO - 20180720 - Se usa para verificar si SICE y GRP tienen la misma informacion
    def verificar_act_cot_sice(self, cr, uid, ids, context=None):

        def get_prov_id(tipo_doc, num_doc):
            """Retorna id del proveedor dado su RUT"""
            partner_ids = self.pool.get("res.partner").search(cr, 1, [('tipo_doc_rupe', '=', tipo_doc),
                                                                      ('nro_doc_rupe', '=', num_doc)])
            if not partner_ids:
                raise osv.except_osv('Error!',
                                     u'El proveedor con tipo de documento %s y número %s no existe en GRP.' % (
                                         tipo_doc, num_doc))
            return partner_ids[0]

        def get_tax_id(imp_cod):
            """Retorna id del impuesto correspondiente al mapeo"""
            sice_impuestos_obj = self.pool.get("grp.art.impuestos")
            impuesto_ids = sice_impuestos_obj.search(cr, 1, [('imp_sice','=',imp_cod)])
            if not impuesto_ids:
                raise osv.except_osv('Error!',
                                     u'No existe mapeo en GRP para el impuesto SICE con código %s.' % (imp_cod))
            tax_id = sice_impuestos_obj.browse(cr, 1, impuesto_ids[0]).imp_grp.id
            return tax_id

        # Obtener el objeto cotizacion
        obj = self.browse(cr, uid, ids[0], context=context)
        # Consulta
        ctx1 = context.copy()
        ctx1.update({'sice_numeracion': obj.sice_numeracion})
        res = self.enviar_consultar_attr_adjudicacion_importar(cr, uid, ids, context=ctx1)
        if res.codEstado == 6:
            raise osv.except_osv('Error!', u'La Adjudicación no está Preparada')
        if res.codEstado == 1:
            raise osv.except_osv('Error!', u'Se esta armando la compra')

        #Lo primero que se verifica es que la cantidad de lineas devueltas por SICE coincida con la cantidad de lineas en GRP
        diferencia = False
        if obj.tipo_compra.idTipoCompra != 'CM' and len(res.items)==len(obj.sice_page_aceptadas):
            for item in res.items:
                coincidencia = False
                # Busco la linea en GRP a partir de IdItem y IdVariacion
                for linea in obj.sice_page_aceptadas:
                    if linea['id_variacion'] == item.idVariacion and linea['id_item'] == item.idItem:
                        #Si la linea es la correcta, entonces verifico el resto de los conceptos
                        #Verifico el proveedor
                        if linea['proveedor_cot_id'].id == get_prov_id(item.proveedor.tipoDocProv, item.proveedor.nroDocProv):
                            # Verifico la cantidad
                            if linea['cantidad'] == item.cantidad:
                                # Verifico el precio sice
                                if linea['precio_sice'] == item.precioUnitario:
                                    # Verifico el producto
                                    if linea['codigo_articulo'] == item.articulo.codArticulo:
                                        # Verifico impuestos
                                        if hasattr(item, 'codImpuestos'):
                                            tax_cod = get_tax_id(item.codImpuestos)
                                            if linea['iva'].id == tax_cod:
                                                coincidencia = True
                                        else:
                                                coincidencia = True
                if not coincidencia:
                    diferencia = True
        else:
            diferencia = True

        if diferencia:
            raise osv.except_osv('Error', u'No es posible aprobar la adjudicación en SICE. No coinciden los datos de la adjudicación en SICE y GRP.')

        return res.codEstado


    #DDELFINO - 20180720 - Se usa para verificar si SICE y GRP tienen la misma informacion
    def verificar_ampliacion_sice(self, cr, uid, ids, pedido_compra, context=None):

        def get_prov_id(tipo_doc, num_doc):
            """Retorna id del proveedor dado su RUT"""
            partner_ids = self.pool.get("res.partner").search(cr, 1, [('tipo_doc_rupe', '=', tipo_doc),
                                                                      ('nro_doc_rupe', '=', num_doc)])
            if not partner_ids:
                raise osv.except_osv('Error!',
                                     u'El proveedor con tipo de documento %s y número %s no existe en GRP.' % (
                                         tipo_doc, num_doc))
            return partner_ids[0]

        def get_tax_id(imp_cod):
            """Retorna id del impuesto correspondiente al mapeo"""
            sice_impuestos_obj = self.pool.get("grp.art.impuestos")
            impuesto_ids = sice_impuestos_obj.search(cr, 1, [('imp_sice','=',imp_cod)])
            if not impuesto_ids:
                raise osv.except_osv('Error!',
                                     u'No existe mapeo en GRP para el impuesto SICE con código %s.' % (imp_cod))
            tax_id = sice_impuestos_obj.browse(cr, 1, impuesto_ids[0]).imp_grp.id
            return tax_id


        # Obtener el objeto cotizacion
        obj = self.browse(cr, uid, ids, context=context)[0]

        if not pedido_compra or not pedido_compra.sice_id_compra:
            raise osv.except_osv('Error!', u'El pedido de compra seleccionado no tiene id de compra de sice.')
        # Consulta
        ctx1 = context.copy()
        ctx1['sice_id_compra'] = pedido_compra.sice_id_compra
        res = self.enviar_consultar_attr_adjudicacion_ampliada(cr, uid, ids, context=ctx1)

        #16 = Ampliación en proceso
        #13 = Ampliación preparada
        if res.codEstado == 16:
            raise osv.except_osv('Error!', u'La Ampliación no está en estado Preparado')

        #Lo primero que se verifica es que la cantidad de lineas devueltas por SICE coincida con la cantidad de lineas en GRP
        diferencia = False
        if obj.tipo_compra.idTipoCompra != 'CM' and len(res.items)==len(obj.sice_page_aceptadas):
            for item in res.items:
                coincidencia = False
                # Busco la linea en GRP a partir de IdItem y IdVariacion
                for linea in obj.sice_page_aceptadas:
                    if linea['id_variacion'] == item.idVariacion and linea['id_item'] == item.idItem:
                        #Si la linea es la correcta, entonces verifico el resto de los conceptos
                        #Verifico el proveedor
                        if linea['proveedor_cot_id'].id == get_prov_id(item.proveedor.tipoDocProv, item.proveedor.nroDocProv):
                            # Verifico la cantidad
                            if linea['cantidad'] == item.cantidad:
                                # Verifico el precio sice
                                if linea['precio_sice'] == item.precioUnitario:
                                    # Verifico el producto
                                    if linea['codigo_articulo'] == item.articulo.codArticulo:
                                        # Verifico impuestos
                                        if hasattr(item, 'codImpuestos'):
                                            tax_cod = get_tax_id(item.codImpuestos)
                                            if linea['iva'].id == tax_cod:
                                                coincidencia = True
                                        else:
                                                coincidencia = True
                if not coincidencia:
                    diferencia = True
        else:
            diferencia = True

        if diferencia:
            raise osv.except_osv('Error', u'No es posible aprobar la adjudicación en SICE. No coinciden los datos de la adjudicación en SICE y GRP.')

        return res.codEstado


    @soap_sice.ampliacion(request='aprobar')
    def enviar_ampliacion_aprobar_sice(self, cr, uid, ids, context=None):
        if not context.get('sice_numeracion', False):
            raise osv.except_osv('Error', u'Numeración SICE compra no encontrado')
        return context['sice_numeracion']


    def act_cot_aprobar_sice(self, cr, uid, ids, context=None):
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context).company_id
        integracion_sice = company.integracion_sice or False
        if not integracion_sice:
            self.write(cr, uid, ids, {'state': 'aprobado_sice'})
            return True
        # Se aprueba la adjudicacion en SICE
        r = self.browse(cr, uid, ids[0], context=context)
        if not r.sice_numeracion:
            raise osv.except_osv('', u'La adjudicación no posee id de compra SICE.')
        ctx1 = context.copy()
        ctx1.update({'sice_numeracion': r.sice_numeracion})
        if r.ampliacion:
            #DDELFINO - 20180820 - Antes de enviar a aprobar se verifica si lo existente en GRP coincide con lo que esta en SICE
            if r.pedido_compra_id:
                cod_estado = self.verificar_ampliacion_sice(cr, uid, ids, r.pedido_compra_id, context=ctx1)
                #Las migraciones solo se envian a probar si el estado SICE es:
                # 16 = Ampliación en proceso
                # 13 = Ampliación preparada
                if not r.es_migracion or cod_estado in [13,16]:
                    self.enviar_ampliacion_aprobar_sice(cr, uid, ids, context=ctx1)  # client.service.aprobar(r.sice_numeracion)
        else:
            #DDELFINO - 20180820 - Antes de enviar a aprobar se verifica si lo existente en GRP coincide con lo que esta en SICE
            cod_estado = self.verificar_act_cot_sice(cr, uid, ids, context=ctx1)
            #Las migraciones solo se envian a aprobar si el estado SICE es:
            # 12 = Adjudicación Preparada
            # 6 = Adjudicación en Proceso
            if not r.es_migracion or cod_estado in [12,6]:
                self.enviar_act_cot_aprobar_sice(cr, uid, ids, context=ctx1)  # client.service.aprobar(r.sice_numeracion)
        self.write(cr, uid, [r.id], {'state': 'aprobado_sice'}, context=context)
        return True

    # Accion para abrir wizard para seleccionar que pedido de compra enviar a SICE
    def button_importar_adjudicacion(self, cr, uid, ids, context=None):

        cot = self.browse(cr, uid, ids, context=context)
        cot = cot[0]

        if cot.ampliacion is True:
            if cot.pedido_compra_id:
                self.action_importar_adjudicacion_ampliada(cr, uid, ids, cot.pedido_compra_id, context)
        elif cot.tipo_compra_cod in ['CM']:
            return self.action_importar_adjudicacion_cm(cr, uid, ids, context=context)
        else:
            self.action_importar_adjudicacion(cr, uid, ids, context)

    @soap_sice.adjudicacion(request='consultar')
    def enviar_consultar_attr_adjudicacion_importar(self, cr, uid, ids, context=None):
        if not context.get('sice_numeracion', False):
            raise osv.except_osv('Error', u'Numeración SICE compra no encontrado')
        return context['sice_numeracion']

    def action_importar_adjudicacion_cm(self, cr, uid, ids, context=None):
        def get_prov_id(tipo_doc, num_doc):
            """Retorna id del proveedor dado su RUT"""
            partner_ids = self.pool.get("res.partner").search(cr, 1, [('tipo_doc_rupe','=',tipo_doc),('nro_doc_rupe','=',num_doc)])
            if not partner_ids:
                raise osv.except_osv('Error!',
                                     u'El proveedor con tipo de documento %s y número %s no existe en GRP.' % (
                                         tipo_doc, num_doc))
            return partner_ids[0]

        def get_tax_id(imp_cod):
            """Retorna id del impuesto correspondiente al mapeo"""
            sice_impuestos_obj = self.pool.get("grp.art.impuestos")
            impuesto_ids = sice_impuestos_obj.search(cr, 1, [('imp_sice','=',imp_cod)])
            if not impuesto_ids:
                raise osv.except_osv('Error!',
                                     u'No existe mapeo en GRP para el impuesto SICE con código %s.' % (imp_cod))
            tax_id = sice_impuestos_obj.browse(cr, 1, impuesto_ids[0]).imp_grp.id
            return tax_id

        def get_currency_id(currency_cod):
            """Retorna id de la moneda correspondiente al mapeo"""
            sice_moneda_obj = self.pool.get("sicec.moneda")
            sice_moneda_ids = sice_moneda_obj.search(cr, 1, [('codMoneda','=',currency_cod)])
            if not sice_moneda_ids:
                raise osv.except_osv('Error!',
                                     u'La moneda de la adjudicación no esta vinculada a una moneda GRP. Para vincular las monedas ir a: Solicitudes - Compras --> Codigueras SICE --> Monedas')
            currency_id = sice_moneda_obj.browse(cr, 1, sice_moneda_ids[0]).currency_id.id
            return currency_id

        def get_uom_id(sice_uom_cod, uom):
            """Retorna id de la unidad de medida"""
            product_uom_obj = self.pool.get("product.uom")
            if uom:
                if uom.sice_uom_id.cod == sice_uom_cod:
                    uom_ids = [uom.id]
                else:
                    uom_ids = product_uom_obj.search(cr, 1, [('sice_uom_id.cod', '=', sice_uom_cod),
                                                             ('category_id', '=', uom.category_id.id)])
            else:
                uom_ids = product_uom_obj.search(cr, 1, [('sice_uom_id.cod', '=', sice_uom_cod)])
            if not uom_ids:
                raise osv.except_osv('Error!',
                                     u'No existe en GRP una UDM con el código %s ' % sice_uom_cod)
            return uom_ids[0]

        def get_odg_prod(sice_prod):
            """Retorna el ODG del articulo según su código SICE"""
            art_sice_obj = self.pool.get("grp.sice_art_serv_obra")
            art_ids = art_sice_obj.search(cr, 1, [('cod', '=', sice_prod)])
            if not art_ids:
                raise osv.except_osv('Error!',
                                     u'No se encontró en GRP el artículo con código %s' % (sice_prod,))
            odg = art_sice_obj.browse(cr, 1, art_ids[0]).odg
            return odg

        # Obtener el objeto cotizacion
        obj = self.browse(cr, uid, ids[0], context=context)
        ctx1 = context.copy()
        ctx1 = dict(ctx1)
        ctx1.update({'sice_numeracion': obj.sice_numeracion})
        res = self.enviar_consultar_attr_adjudicacion_importar(cr, uid, ids, context=ctx1)
        # ¿ Preparada ? (codEstado == 12) (descEstado == 'Adjudicación Preparada')
        # ¿ En Proceso ? (codEstado == 6) (descEstado == 'Adjudicación en Proceso')
        if res.codEstado == 6:
            raise osv.except_osv('Error!', u'La Adjudicación no está Preparada')
        if res.codEstado == 1:
            raise osv.except_osv('Error!', u'Se esta armando la compra')

        # Datos generales
        adjCabezal = {}
        adjCabezal['sice_page_aceptadas'] = []
        if hasattr(res, 'objetoCompra'):
            adjCabezal['sice_descripcion'] = res.objetoCompra

        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')

        # Los artículos
        for item in res.items:
            adjLinea = {}
            adjLinea['proveedor_cot_id'] = get_prov_id(item.proveedor.tipoDocProv, item.proveedor.nroDocProv)
            adjLinea['cantidad'] = item.cantidad
            adjLinea['precio_sice'] = item.precioUnitario  # 009 - Precio devuelto por sice
            if hasattr(item, 'codImpuestos'):
                tax_cod = get_tax_id(item.codImpuestos)
                adjLinea['iva'] = [(4, tax_cod)]
            cod_moneda_sice_ids = self.pool.get('sicec.moneda').search(cr, 1, [('codMoneda', '=', item.codMoneda)])
            if len(cod_moneda_sice_ids) > 0:
                adjLinea['cod_moneda'] = cod_moneda_sice_ids[0]
            else:
                raise osv.except_osv('Error!', u'El código de moneda de la '
                                                 u'adjudicación no esta configurado en GRP')

            if not item.cantidad:
                raise osv.except_osv('Error!', u'La Cantidad en la '
                                                 u'adjudicación SICE no puede ser 0')

            real_price = item.precioUnitario

            # Validar si tiene iva incluido, cambia la forma de calcular el precio
            if 'iva' in adjLinea and adjLinea['iva']:
                # Se calcula para cantidad = 1 asi se obtiene el precio unitario
                iva_ids = get_tax_id(item.codImpuestos)
                if not isinstance(iva_ids, (list, tuple)):
                    iva_ids = [iva_ids]
                if iva_ids:
                    tax_brw = tax_obj.browse(cr, uid, iva_ids)
                    if tax_brw.price_include:
                        real_price = item.precioTotal / item.cantidad

            adjLinea['precio'] = real_price
            adjLinea['precioTotal'] = item.precioTotal

            adjLinea['codigo_articulo'] = item.articulo.codArticulo
            pool_resumen = self.pool.get('grp.resumen.pedido.compra')
            resumen_id = pool_resumen.search(cr, uid, [
                ('pedido_compra_id', '=', obj.pedido_compra_id.id),
                ('product_id.grp_sice_cod', '=', item.articulo.codArticulo),
            ])
            if resumen_id:
                resumen_obj = pool_resumen.browse(cr, uid, resumen_id[0])
                uom_id_pedido = resumen_obj.uom_id
            else:
                uom_id_pedido = False
            adjLinea['seleccionada'] = False
            adjLinea['uom_id'] = get_uom_id(item.articulo.codUnidad, uom_id_pedido)
            adjLinea['currency'] = get_currency_id(item.codMoneda)
            adjLinea['odg'] = get_odg_prod(item.articulo.codArticulo)
            adjLinea['atributos'] = ""

            adjLinea['id_variacion'] = item.idVariacion
            adjLinea['id_item'] = item.idItem
            adjLinea['desc_variacion'] = item.descVariacion

            cod_art = item.articulo.codArticulo
            cod_med_var = False
            cod_pres = False
            cod_med_pres = False
            if 'codMedidaVariante' in item.articulo:
                cod_med_var = item.articulo.codMedidaVariante
            if 'codPresentacion' in item.articulo:
                cod_pres = item.articulo.codPresentacion
            if 'codMedidaPresentacion' in item.articulo:
                cod_med_pres = item.articulo.codMedidaPresentacion
            if 'codDetalleVariante' in item.articulo:
                cod_det_var = item.articulo.codDetalleVariante
            else:
                cod_det_var = False
            if 'codColor' in item.articulo:
                cod_color = item.articulo.codColor
            else:
                cod_color = False

            if not cod_art:
                raise osv.except_osv('Error!', _(u'El artículo importado desde SICE no '
                                                   u'tiene código de artículo.'))
            if not cod_med_var:
                raise osv.except_osv('Error!', _(u'El artículo importado desde SICE no tiene código de '
                                                   u'medida de variante.'))
            if not cod_med_pres:
                raise osv.except_osv('Error!', _(u'El artículo importado desde SICE no tiene código de '
                                                   u'medida de presentación.'))
            if not cod_pres:
                raise osv.except_osv('Error!', _(u'El artículo importado desde SICE no tiene código de '
                                                   u'presentación.'))
            domain = []
            template_id = self.pool.get('product.template').search(cr, uid, [('grp_sice_cod', '=', cod_art)])
            if template_id:
                if len(template_id) > 0:
                    template_id = template_id[0]
                domain.append(('product_tmpl_id', '=', template_id))
            elif not template_id:
                medida_pool = self.pool.get('grp.sice_medida')
                color_pool = self.pool.get('grp.sice_color')
                pres_pool = self.pool.get('grp.sice_presentacion')
                med_var_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_var)])
                med_var_desc = medida_pool.browse(cr, uid, med_var_id).descripcion
                med_pres_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_pres)])
                med_pres_desc = medida_pool.browse(cr, uid, med_pres_id).descripcion
                color_id = color_pool.search(cr, uid, [('cod', '=', cod_color)])
                color_desc = color_pool.browse(cr, uid, color_id).descripcion
                pres_id = pres_pool.search(cr, uid, [('cod', '=', cod_pres)])
                pres_desc = pres_pool.browse(cr, uid, pres_id).descripcion
                raise osv.except_osv('Error!', _(u'El artículo importado desde SICE'
                                                   u' (Código: %s Medida variante:'
                                                   u' %s Presentación: %s Medida presentación: %s Color: %s'
                                                   u' Cód. Detalle de Variante: %s) '
                                                   u'no está creado en '
                                                   u'GRP.') %
                                                 (cod_art, med_var_desc, pres_desc,
                                                  med_pres_desc, color_desc, cod_det_var))
            med_cod_id = self.pool.get('grp.sice_medida').search(cr, uid, [('cod', '=', cod_med_var)])
            pres_id = self.pool.get('grp.sice_presentacion').search(cr, uid, [('cod', '=', cod_pres)])
            med_cod_pres_id = self.pool.get('grp.sice_medida').search(cr, uid, [('cod', '=', cod_med_pres)])
            if med_cod_id:
                if len(med_cod_id) > 0:
                    med_cod_id = med_cod_id[0]
            else:
                med_cod_id = False
            if pres_id:
                if len(pres_id) > 0:
                    pres_id = pres_id[0]
            else:
                pres_id = False
            if med_cod_pres_id:
                if len(med_cod_pres_id) > 0:
                    med_cod_pres_id = med_cod_pres_id[0]
            else:
                med_cod_pres_id = False
            domain.append(('med_cod_id', '=', med_cod_id))
            domain.append(('pres_id', '=', pres_id))
            domain.append(('med_cod_pres_id', '=', med_cod_pres_id))
            det_variante_id = False
            sice_color_id = False
            if cod_det_var:
                det_variante_id = self.pool.get('grp.sice_det_variante').search(cr, uid, [('cod', '=', cod_det_var)])
                if det_variante_id:
                    if len(det_variante_id) > 0:
                        det_variante_id = det_variante_id[0]
                    domain.append(('det_variante_id', '=', det_variante_id))
                else:
                    domain.append(('det_variante_id', '=', False))
            if cod_color:
                sice_color_id = self.env['grp.sice_color'].search(cr, uid, [('cod', '=', cod_color)])
                if sice_color_id:
                    if len(sice_color_id) > 0:
                        sice_color_id = sice_color_id[0]
                    domain.append(('sice_color_id', '=', sice_color_id))
                else:
                    domain.append(('sice_color_id', '=', False))
            product_ids = self.pool.get('product.product').search(cr, uid, domain)
            if product_ids:
                if len(product_ids) > 0:
                    product_ids = product_ids[0]
                adjLinea['product_id'] = product_ids
            else:
                medida_pool = self.pool.get('grp.sice_medida')
                color_pool = self.pool.get('grp.sice_color')
                pres_pool = self.pool.get('grp.sice_presentacion')
                med_var_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_var)])
                med_var_desc = medida_pool.browse(cr, uid, med_var_id).descripcion
                med_pres_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_pres)])
                med_pres_desc = medida_pool.browse(cr, uid, med_pres_id).descripcion
                color_id = color_pool.search(cr, uid, [('cod', '=', cod_color)])
                color_desc = color_pool.browse(cr, uid, color_id).descripcion
                pres_id = pres_pool.search(cr, uid, [('cod', '=', cod_pres)])
                pres_desc = pres_pool.browse(cr, uid, pres_id).descripcion
                raise osv.except_osv('Error!', _(u'El artículo importado desde SICE (Código: '
                                                   u'%s Medida variante:'
                                                   u' %s Presentación: %s Medida presentación: %s Color: %s'
                                                   u' Cód. Detalle de Variante: %s) '
                                                   u'no está creado en '
                                                   u'GRP.') %
                                                 (cod_art, med_var_desc, pres_desc,
                                                  med_pres_desc, color_desc, cod_det_var))
            adjCabezal['sice_page_aceptadas'].append((0, 0, adjLinea))

        ctx = context.copy()
        ctx = dict(ctx)
        ctx.update({'default_adjudicacion_ids': adjCabezal['sice_page_aceptadas']})
        res = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'grp_factura_sice',
                                                             'grp_importar_adjudicacion_cm_wizard_form_view')
        res_id = res and res[1] or False
        return {
            'type': 'ir.actions.act_window',
            'name': u'Importar Adjudicación Convenio Marco',
            'view_mode': 'form',
            'view_id': res_id,
            'res_model': 'grp.importar.adjudicacion.cm.wizard',
            'src_model': "grp.cotizaciones",
            'target': 'new',
            'context': ctx,
        }

    def action_importar_adjudicacion(self, cr, uid, ids, context=None):

        def get_prov_id(tipo_doc, num_doc):
            """Retorna id del proveedor dado su RUT"""
            partner_ids = self.pool.get("res.partner").search(cr, 1, [('tipo_doc_rupe','=',tipo_doc),('nro_doc_rupe','=',num_doc)])
            if not partner_ids:
                raise osv.except_osv('Error!',
                                     u'El proveedor con tipo de documento %s y número %s no existe en GRP.' % (
                                         tipo_doc, num_doc))
            return partner_ids[0]

        def get_tax_id(imp_cod):
            """Retorna id del impuesto correspondiente al mapeo"""
            sice_impuestos_obj = self.pool.get("grp.art.impuestos")
            impuesto_ids = sice_impuestos_obj.search(cr, 1, [('imp_sice','=',imp_cod)])
            if not impuesto_ids:
                raise osv.except_osv('Error!',
                                     u'No existe mapeo en GRP para el impuesto SICE con código %s.' % (imp_cod))
            tax_id = sice_impuestos_obj.browse(cr, 1, impuesto_ids[0]).imp_grp.id
            return tax_id

        def get_currency_id(currency_cod):
            """Retorna id de la moneda correspondiente al mapeo"""
            sice_moneda_obj = self.pool.get("sicec.moneda")
            sice_moneda_ids = sice_moneda_obj.search(cr, 1, [('codMoneda','=',currency_cod)])
            if not sice_moneda_ids:
                raise osv.except_osv('Error!',
                                     u'La moneda de la adjudicación no esta vinculada a una moneda GRP. Para vincular las monedas ir a: Solicitudes - Compras --> Codigueras SICE --> Monedas')
            currency_id = sice_moneda_obj.browse(cr, 1, sice_moneda_ids[0]).currency_id.id
            return currency_id

        def get_uom_id(sice_uom_cod, uom):
            """Retorna id de la unidad de medida"""
            product_uom_obj = self.pool.get("product.uom")
            if uom:
                if uom.sice_uom_id.cod == sice_uom_cod:
                    uom_ids = [uom.id]
                else:
                    uom_ids = product_uom_obj.search(cr, 1, [('sice_uom_id.cod', '=', sice_uom_cod),
                                                             ('category_id', '=', uom.category_id.id)])
            else:
                uom_ids = product_uom_obj.search(cr, 1, [('sice_uom_id.cod', '=', sice_uom_cod)])
            if not uom_ids:
                raise osv.except_osv('Error!',
                                     u'No existe en GRP una UDM con el código %s ' % sice_uom_cod)
            return uom_ids[0]

        def get_odg_prod(sice_prod):
            """Retorna el ODG del articulo según su código SICE"""
            art_sice_obj = self.pool.get("grp.sice_art_serv_obra")
            art_ids = art_sice_obj.search(cr, 1, [('cod', '=', sice_prod)])
            if not art_ids:
                raise osv.except_osv('Error!',
                                     u'No se encontró en GRP el artículo con código %s' % (sice_prod,))
            odg = art_sice_obj.browse(cr, 1, art_ids[0]).odg
            return odg

        # Obtener el objeto cotizacion
        obj = self.browse(cr, uid, ids[0], context=context)
        # Consulta
        ctx1 = context.copy()
        ctx1.update({'sice_numeracion': obj.sice_numeracion})
        res = self.enviar_consultar_attr_adjudicacion_importar(cr, uid, ids, context=ctx1)
        # ¿ Preparada ? (codEstado == 12) (descEstado == 'Adjudicación Preparada')
        # ¿ En Proceso ? (codEstado == 6) (descEstado == 'Adjudicación en Proceso')
        if res.codEstado == 6:
            raise osv.except_osv('Error!', u'La Adjudicación no está Preparada')
        if res.codEstado == 1:
            raise osv.except_osv('Error!', u'Se esta armando la compra')

        # Datos generales
        adjCabezal = {}
        adjCabezal['sice_page_aceptadas'] = []
        if hasattr(res, 'objetoCompra'):
            adjCabezal['sice_descripcion'] = res.objetoCompra

        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')

        # Los artículos
        for item in res.items:
            adjLinea = {}
            adjLinea['proveedor_cot_id'] = get_prov_id(item.proveedor.tipoDocProv, item.proveedor.nroDocProv)
            adjLinea['cantidad'] = item.cantidad
            adjLinea['precio_sice'] = item.precioUnitario  # 009 - Precio devuelto por sice
            if hasattr(item, 'codImpuestos'):
                tax_cod = get_tax_id(item.codImpuestos)
                adjLinea['iva'] = [(4, tax_cod)]
            cod_moneda_sice_ids = self.pool.get('sicec.moneda').search(cr, SUPERUSER_ID,
                                                                       [('codMoneda', '=', item.codMoneda)])
            if len(cod_moneda_sice_ids) > 0:
                adjLinea['cod_moneda'] = cod_moneda_sice_ids[0]
            else:
                raise osv.except_osv('Error!', u'El código de moneda de la adjudicación no esta configurado en GRP')

            if not item.cantidad:
                raise osv.except_osv('Error!', u'La Cantidad en la adjudicación SICE no puede ser 0')

            real_price = item.precioUnitario

            # Validar si tiene iva incluido, cambia la forma de calcular el precio
            if 'iva' in adjLinea and adjLinea['iva']:
                # Se calcula para cantidad = 1 asi se obtiene el precio unitario
                iva_ids = get_tax_id(item.codImpuestos)
                if not isinstance(iva_ids, (list, tuple)):
                    iva_ids = [iva_ids]
                if iva_ids:
                    tax_brw = tax_obj.browse(cr, uid, iva_ids)
                    if tax_brw.price_include:
                        real_price = item.precioTotal / item.cantidad


            adjLinea['precio'] = real_price
            adjLinea['precioTotal'] = item.precioTotal

            adjLinea['codigo_articulo'] = item.articulo.codArticulo
            pool_resumen = self.pool.get('grp.resumen.pedido.compra')
            resumen_id = pool_resumen.search(cr, uid, [
                ('pedido_compra_id', '=', obj.pedido_compra_id.id),
                ('product_id.grp_sice_cod', '=', item.articulo.codArticulo),
            ])
            if resumen_id:
                resumen_obj = pool_resumen.browse(cr, uid, resumen_id[0])
                uom_id_pedido = resumen_obj.uom_id
            else:
                uom_id_pedido = False
            adjLinea['uom_id'] = get_uom_id(item.articulo.codUnidad, uom_id_pedido)
            adjLinea['currency'] = get_currency_id(item.codMoneda)
            adjLinea['odg'] = get_odg_prod(item.articulo.codArticulo)
            adjLinea['atributos'] = ""

            adjLinea['id_variacion'] = item.idVariacion
            adjLinea['id_item'] = item.idItem
            adjLinea['desc_variacion'] = item.descVariacion

            cod_art = item.articulo.codArticulo
            cod_med_var = item.articulo.codMedidaVariante
            cod_pres = item.articulo.codPresentacion
            cod_med_pres = item.articulo.codMedidaPresentacion
            if 'codDetalleVariante' in item.articulo:
                cod_det_var = item.articulo.codDetalleVariante
            else:
                cod_det_var = False
            if 'codColor' in item.articulo:
                cod_color = item.articulo.codColor
            else:
                cod_color = False

            if not cod_art:
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE no '
                                                     u'tiene código de artículo.'))
            if not cod_med_var:
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE no tiene código de '
                                                     u'medida de variante.'))
            if not cod_med_pres:
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE no tiene código de '
                                                     u'medida de presentación.'))
            if not cod_pres:
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE no tiene código de '
                                                     u'presentación.'))
            domain = []
            template_id = self.pool.get('product.template').search(cr, uid, [('grp_sice_cod', '=', cod_art)])
            if len(template_id) > 0 and template_id:
                template_id = template_id[0]
                domain.append(('product_tmpl_id', '=', template_id))
            elif not template_id:
                medida_pool = self.pool.get('grp.sice_medida')
                color_pool = self.pool.get('grp.sice_color')
                pres_pool = self.pool.get('grp.sice_presentacion')
                med_var_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_var)])
                med_var_desc = medida_pool.browse(cr, uid, med_var_id).descripcion
                med_pres_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_pres)])
                med_pres_desc = medida_pool.browse(cr, uid, med_pres_id).descripcion
                color_id = color_pool.search(cr, uid, [('cod', '=', cod_color)])
                color_desc = color_pool.browse(cr, uid, color_id).descripcion
                pres_id = pres_pool.search(cr, uid, [('cod', '=', cod_pres)])
                pres_desc = pres_pool.browse(cr, uid, pres_id).descripcion
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE (Código: %s Medida variante:'
                                                     u' %s Presentación: %s Medida presentación: %s Color: %s'
                                                     u' Cód. Detalle de Variante: %s) '
                                                     u'no está creado en '
                                                     u'GRP.') %
                                     (cod_art, med_var_desc, pres_desc, med_pres_desc, color_desc, cod_det_var))
            med_cod_id = self.pool.get('grp.sice_medida').search(cr, uid, [('cod', '=', cod_med_var)])
            pres_id = self.pool.get('grp.sice_presentacion').search(cr, uid, [('cod', '=', cod_pres)])
            med_cod_pres_id = self.pool.get('grp.sice_medida').search(cr, uid, [('cod', '=', cod_med_pres)])
            domain.append(('med_cod_id', '=', med_cod_id))
            domain.append(('pres_id', '=', pres_id))
            domain.append(('med_cod_pres_id', '=', med_cod_pres_id))
            det_variante_id = False
            sice_color_id = False
            if cod_det_var:
                det_variante_id = self.pool.get('grp.sice_det_variante').search(cr, uid,
                                                                                [('cod', '=', cod_det_var)])
                if det_variante_id:
                    domain.append(('det_variante_id', '=', det_variante_id[0]))
                else:
                    domain.append(('det_variante_id', '=', False))
            if cod_color:
                sice_color_id = self.pool.get('grp.sice_color').search(cr, uid, [('cod', '=', cod_color)])
                if sice_color_id:
                    domain.append(('sice_color_id', '=', sice_color_id[0]))
                else:
                    domain.append(('sice_color_id', '=', False))
            product_ids = self.pool.get('product.product').search(cr, uid, domain)
            if product_ids:
                adjLinea['product_id'] = product_ids[0]
            else:
                medida_pool = self.pool.get('grp.sice_medida')
                color_pool = self.pool.get('grp.sice_color')
                pres_pool = self.pool.get('grp.sice_presentacion')
                med_var_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_var)])
                med_var_desc = medida_pool.browse(cr, uid, med_var_id).descripcion
                med_pres_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_pres)])
                med_pres_desc = medida_pool.browse(cr, uid, med_pres_id).descripcion
                color_id = color_pool.search(cr, uid, [('cod', '=', cod_color)])
                color_desc = color_pool.browse(cr, uid, color_id).descripcion
                pres_id = pres_pool.search(cr, uid, [('cod', '=', cod_pres)])
                pres_desc = pres_pool.browse(cr, uid, pres_id).descripcion
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE (Código: %s Medida variante:'
                                                     u' %s Presentación: %s Medida presentación: %s Color: %s'
                                                     u' Cód. Detalle de Variante: %s) '
                                                     u'no está creado en '
                                                     u'GRP.') %
                                     (cod_art, med_var_desc, pres_desc, med_pres_desc, color_desc, cod_det_var))
            # Agrego la línea
            adjCabezal['sice_page_aceptadas'].append((0, 0, adjLinea))

        ctx = context.copy()
        # Desvinculo previos si existieran
        self.write(cr, uid, ids, {'sice_page_aceptadas': [(5,)]}, context=ctx)

        # Guardamos
        self.write(cr, uid, ids, adjCabezal, context=ctx)

        return True

    @soap_sice.ampliacion(request='consultar')
    def enviar_consultar_attr_adjudicacion_ampliada(self, cr, uid, ids, context=None):
        # pedido_compra.sice_id_compra
        if not context.get('sice_id_compra', False):
            raise osv.except_osv('Error', 'ID SICE compra no encontrado')
        return context['sice_id_compra']

    # Accion para el pedido de compra ampliado en la cotizacion
    def action_importar_adjudicacion_ampliada(self, cr, uid, ids, pedido_compra, context=None):

        def get_prov_id(tipo_doc, num_doc):
            """Retorna id del proveedor dado su RUT"""
            partner_ids = self.pool.get("res.partner").search(cr, 1, [('tipo_doc_rupe','=',tipo_doc),('nro_doc_rupe','=',num_doc)])
            if not partner_ids:
                raise osv.except_osv('Error!',
                                     u'El proveedor con tipo de documento %s y número %s no existe en GRP.' % (
                                         tipo_doc, num_doc))
            return partner_ids[0]

        def get_tax_id(imp_cod):
            """Retorna id del impuesto correspondiente al mapeo"""
            sice_impuestos_obj = self.pool.get("grp.art.impuestos")
            impuesto_ids = sice_impuestos_obj.search(cr, 1, [('imp_sice','=',imp_cod)])
            if not impuesto_ids:
                raise osv.except_osv('Error!',
                                     u'No existe mapeo en GRP para el impuesto SICE con código %s.' % (imp_cod))
            tax_id = sice_impuestos_obj.browse(cr, 1, impuesto_ids[0]).imp_grp.id
            return tax_id

        def get_currency_id(currency_cod):
            """Retorna id de la moneda correspondiente al mapeo"""
            sice_moneda_obj = self.pool.get("sicec.moneda")
            sice_moneda_ids = sice_moneda_obj.search(cr, 1, [('codMoneda','=',currency_cod)])
            if not sice_moneda_ids:
                raise osv.except_osv('Error!',
                                     u'La moneda de la adjudicación no esta vinculada a una moneda GRP. Para vincular las monedas ir a: Solicitudes - Compras --> Codigueras SICE --> Monedas')
            currency_id = sice_moneda_obj.browse(cr, 1, sice_moneda_ids[0]).currency_id.id
            return currency_id

        def get_uom_id(sice_uom_cod, uom):
            """Retorna id de la unidad de medida"""
            product_uom_obj = self.pool.get("product.uom")
            if uom:
                if uom.sice_uom_id.cod == sice_uom_cod:
                    uom_ids = [uom.id]
                else:
                    uom_ids = product_uom_obj.search(cr, 1, [('sice_uom_id.cod', '=', sice_uom_cod),
                                                             ('category_id', '=', uom.category_id.id)])
            else:
                uom_ids = product_uom_obj.search(cr, 1, [('sice_uom_id.cod', '=', sice_uom_cod)])
            if not uom_ids:
                raise osv.except_osv('Error!',
                                     u'No existe en GRP una UDM con el código %s ' % sice_uom_cod)
            return uom_ids[0]

        def get_odg_prod(sice_prod):
            """Retorna el ODG del articulo según su código SICE"""
            art_sice_obj = self.pool.get("grp.sice_art_serv_obra")
            art_ids = art_sice_obj.search(cr, 1, [('cod', '=', sice_prod)])
            if not art_ids:
                raise osv.except_osv('Error!',
                                     u'No se encontró en GRP el artículo con código %s' % (sice_prod,))
            odg = art_sice_obj.browse(cr, 1, art_ids[0]).odg
            return odg

        # Obtener el objeto cotizacion
        obj = self.browse(cr, uid, ids, context=context)[0]

        if not pedido_compra or not pedido_compra.sice_id_compra:
            raise osv.except_osv('Error!', u'El pedido de compra seleccionado no tiene id de compra de sice.')
        # Consulta
        ctx1 = context.copy()
        ctx1['sice_id_compra'] = pedido_compra.sice_id_compra
        res = self.enviar_consultar_attr_adjudicacion_ampliada(cr, uid, ids, context=ctx1)

        #16 = Ampliación en proceso
        #13 = Ampliación preparada
        if res.codEstado == 16:
            raise osv.except_osv('Error!', u'La Ampliación no está en estado Preparada')
        # Datos generales
        adjWrite = {}
        adjWrite['sice_page_aceptadas'] = []
        sice_descripcion = ''
        if hasattr(res, 'objetoCompra'):
            sice_descripcion = res.objetoCompra
        # Los artículos
        for item in res.items:
            adjLinea = {}
            # Descripcion - Objeto de la compra
            adjLinea['sice_descripcion'] = len(sice_descripcion) and sice_descripcion or ''
            adjLinea['proveedor_cot_id'] = get_prov_id(item.proveedor.tipoDocProv, item.proveedor.nroDocProv)
            adjLinea['cantidad'] = item.cantidad

            if hasattr(item, 'codImpuestos'):
                adjLinea['iva'] = [(4, get_tax_id(item.codImpuestos)), ]
            adjLinea['codigo_articulo'] = item.articulo.codArticulo
            pool_resumen = self.pool.get('grp.resumen.pedido.compra')
            pool_prod_prod = self.pool.get('product.product')
            resumen_id = pool_resumen.search(cr, uid, [
                ('pedido_compra_id', '=', obj.pedido_compra_id.id),
                ('product_id.grp_sice_cod', '=', item.articulo.codArticulo),
            ])
            if resumen_id:
                resumen_obj = pool_resumen.browse(cr, uid, resumen_id[0])
                uom_id_pedido = resumen_obj.uom_id
            else:
                uom_id_pedido = False
            adjLinea['uom_id'] = get_uom_id(item.articulo.codUnidad, uom_id_pedido)
            adjLinea['currency'] = get_currency_id(item.codMoneda)
            adjLinea['odg'] = get_odg_prod(item.articulo.codArticulo)
            adjLinea['atributos'] = ""

            adjLinea['id_variacion'] = item.idVariacion
            adjLinea['id_item'] = item.idItem
            adjLinea['desc_variacion'] = item.descVariacion

            # campos adicionales de relacion con la adjudicacion
            adjLinea[
                'pedido_cot_id_5'] = obj.id  # fields.many2one('grp.cotizaciones',u'Adjudicación', ondelete='cascade'),

            cod_moneda_sice_ids = self.pool.get('sicec.moneda').search(cr, SUPERUSER_ID,
                                                                       [('codMoneda', '=', item.codMoneda)])
            if len(cod_moneda_sice_ids) > 0:
                adjLinea['cod_moneda'] = cod_moneda_sice_ids[0]
            else:
                raise osv.except_osv('Error!', u'El código de moneda de la adjudicación no esta configurado en GRP')

            if not item.cantidad or not item.precioUnitario:
                raise osv.except_osv('Error!', u'Cantidad y precio unitario en la adjudicación SICE no pueden ser 0')

            # Modelos a utilizar
            cur_obj = self.pool.get('res.currency')
            tax_obj = self.pool.get('account.tax')

            real_price = item.precioUnitario

            if 'iva' in adjLinea and adjLinea['iva']:
                # Se calcula para cantidad = 1 asi se obtiene el precio unitario
                iva_ids = get_tax_id(item.codImpuestos)
                if not isinstance(iva_ids, (list, tuple)):
                    iva_ids = [iva_ids]
                if iva_ids:
                    tax_brw = tax_obj.browse(cr, uid, iva_ids)
                    if tax_brw.price_include:
                        real_price = item.precioTotal / item.cantidad
            adjLinea['precio'] = real_price
            adjLinea['precioTotal'] = item.precioTotal
            adjLinea['precio_sice'] = item.precioUnitario

            cod_art = item.articulo.codArticulo
            cod_med_var = item.articulo.codMedidaVariante
            cod_pres = item.articulo.codPresentacion
            cod_med_pres = item.articulo.codMedidaPresentacion
            if 'codDetalleVariante' in item.articulo:
                cod_det_var = item.articulo.codDetalleVariante
            else:
                cod_det_var = False
            if 'codColor' in item.articulo:
                cod_color = item.articulo.codColor
            else:
                cod_color = False

            if not cod_art:
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE no '
                                                     u'tiene código de artículo.'))
            if not cod_med_var:
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE no tiene código de '
                                                     u'medida de variante.'))
            if not cod_med_pres:
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE no tiene código de '
                                                     u'medida de presentación.'))
            if not cod_pres:
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE no tiene código de '
                                                     u'presentación.'))
            domain = []
            template_id = self.pool.get('product.template').search(cr, uid, [('grp_sice_cod', '=', cod_art)])
            if len(template_id) > 0 and template_id:
                template_id = template_id[0]
                domain.append(('product_tmpl_id', '=', template_id))
            elif not template_id:
                medida_pool = self.pool.get('grp.sice_medida')
                color_pool = self.pool.get('grp.sice_color')
                pres_pool = self.pool.get('grp.sice_presentacion')
                med_var_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_var)])
                med_var_desc = medida_pool.browse(cr, uid, med_var_id).descripcion
                med_pres_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_pres)])
                med_pres_desc = medida_pool.browse(cr, uid, med_pres_id).descripcion
                color_id = color_pool.search(cr, uid, [('cod', '=', cod_color)])
                color_desc = color_pool.browse(cr, uid, color_id).descripcion
                pres_id = pres_pool.search(cr, uid, [('cod', '=', cod_pres)])
                pres_desc = pres_pool.browse(cr, uid, pres_id).descripcion
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE (Código: %s Medida variante:'
                                                     u' %s Presentación: %s Medida presentación: %s Color: %s'
                                                     u' Cód. Detalle de Variante: %s) '
                                                     u'no está creado en '
                                                     u'GRP.') %
                                     (cod_art, med_var_desc, pres_desc, med_pres_desc, color_desc, cod_det_var))

            med_cod_id = self.pool.get('grp.sice_medida').search(cr, uid, [('cod', '=', cod_med_var)])
            pres_id = self.pool.get('grp.sice_presentacion').search(cr, uid, [('cod', '=', cod_pres)])
            med_cod_pres_id = self.pool.get('grp.sice_medida').search(cr, uid, [('cod', '=', cod_med_pres)])
            domain.append(('med_cod_id', '=', med_cod_id))
            domain.append(('pres_id', '=', pres_id))
            domain.append(('med_cod_pres_id', '=', med_cod_pres_id))
            det_variante_id = False
            sice_color_id = False
            if cod_det_var:
                det_variante_id = self.pool.get('grp.sice_det_variante').search(cr, uid,
                                                                                [('cod', '=', cod_det_var)])
                if det_variante_id:
                    domain.append(('det_variante_id', '=', det_variante_id[0]))
                else:
                    domain.append(('det_variante_id', '=', False))
            if cod_color:
                sice_color_id = self.pool.get('grp.sice_color').search(cr, uid, [('cod', '=', cod_color)])
                if sice_color_id:
                    domain.append(('sice_color_id', '=', sice_color_id[0]))
                else:
                    domain.append(('sice_color_id', '=', False))
            product_ids = self.pool.get('product.product').search(cr, uid, domain)
            if product_ids:
                adjLinea['product_id'] = product_ids[0]
            else:
                medida_pool = self.pool.get('grp.sice_medida')
                color_pool = self.pool.get('grp.sice_color')
                pres_pool = self.pool.get('grp.sice_presentacion')
                med_var_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_var)])
                med_var_desc = medida_pool.browse(cr, uid, med_var_id).descripcion
                med_pres_id = medida_pool.search(cr, uid, [('cod', '=', cod_med_pres)])
                med_pres_desc = medida_pool.browse(cr, uid, med_pres_id).descripcion
                color_id = color_pool.search(cr, uid, [('cod', '=', cod_color)])
                color_desc = color_pool.browse(cr, uid, color_id).descripcion
                pres_id = pres_pool.search(cr, uid, [('cod', '=', cod_pres)])
                pres_desc = pres_pool.browse(cr, uid, pres_id).descripcion
                raise osv.except_osv(_(u'Error!'), _(u'El artículo importado desde SICE (Código: %s Medida variante:'
                                                     u' %s Presentación: %s Medida presentación: %s Color: %s'
                                                     u' Cód. Detalle de Variante: %s) '
                                                     u'no está creado en '
                                                     u'GRP.') %
                                     (cod_art, med_var_desc, pres_desc, med_pres_desc, color_desc, cod_det_var))

            # Agrego la línea
            adjWrite['sice_page_aceptadas'].append((0, 0, adjLinea))

        # Buscar las lineas de ampliacion
        cot_lines_ampliadas = self.pool.get('grp.cotizaciones.lineas.ampliadas')
        ids_lines_ampliadas = cot_lines_ampliadas.search(cr, uid, [('pedido_cot_id_5', '=', obj.id),
                                                                   ('pc_ampliado_id', '=', pedido_compra.id)],
                                                         context=context)
        ctx = context.copy()
        ctx.update({'create': True})  # Incidencia 348
        if len(ids_lines_ampliadas) > 0:
            # Desvinculo previos si existieran
            for id_line in ids_lines_ampliadas:
                self.write(cr, uid, ids, {'lines_ampliacion_ids': [(2, id_line)]}, context=ctx)

        # Actualizamos
        self.write(cr, uid, ids, adjWrite, context=ctx)
        return True

grp_cotizaciones()


