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
from openerp.tools.translate import _
from openerp.addons.grp_sice.grp_sice import soap_sice

import logging
_logger = logging.getLogger(__name__)


class account_invoice(osv.osv):
    _inherit = "account.invoice"

    _columns = {
        'id_compra': fields.integer('Id factura sice', size=9),
        'serie_factura': fields.char('Serie', size=3),
        'sec_factura': fields.integer('Secuencia',size=2),
        'id_factura_sice': fields.integer('ID Factura SICE'),
        'nro_oc': fields.integer(u'Id OC SICE'),
        'descripcion': fields.text(u'Descripción',size=100),
    }

    _defaults = {
        'sec_factura': 0,
    }

    @soap_sice.factura(request='aprobar')
    def enviar_invoice_sice_aprobar(self, cr, uid, ids, context=None):
        if not context.get('idFactura', False):
            raise osv.except_osv("Error", "ID de la factura no encontrado")
        return context['idFactura']

    def prepare_invoice_sice_alta(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)

        facturaAlta = {
            'secFactura': obj.sec_factura,
            'fechaFactura': obj.date_invoice,
            'fechaVencFactura': obj.date_due,
            'proveedor': {
                'tipoDocProv': obj.partner_id.tipo_doc_rupe,
                'nroDocProv': obj.partner_id.nro_doc_rupe
            },
            'itemsAlta': []
        }
        if obj.supplier_invoice_number:
            facturaAlta['nroFactura'] = obj.supplier_invoice_number
        else:
            raise osv.except_osv(_('Error!'), _(u'Por favor ingrese el nro de factura del proveedor.'))
        if obj.serie_factura:
            facturaAlta['serieFactura'] = obj.serie_factura
        else:
            raise osv.except_osv(_('Error!'), _(u'Por favor ingrese la serie de la factura.'))
        if obj.sec_factura > 99:
            raise osv.except_osv(_('Error!'), _(u'El largo máximo de la secuencia de factura es 2.'))
        if not obj.orden_compra_id:
            raise osv.except_osv(_('Error!'), _(u'Por favor ingrese el nro de OC.'))
        elif not obj.orden_compra_id.sice_id_oc:
            raise osv.except_osv(_('Error!'), _(u'Primero debe enviar a SICE la OC asociada a la Factura.'))
        elif not obj.orden_compra_id.pedido_compra_id:
            raise osv.except_osv(_('Error!'), _(u'La OC seleccionada no tiene pedido de compra asociado.'))
        if obj.orden_compra_id.pedido_compra_id.sice_id_compra:
            facturaAlta['idCompra'] = obj.orden_compra_id.pedido_compra_id.sice_id_compra
        else:
            raise osv.except_osv(_('Error!'),
                                 _(u'El pedido de compra asociado a la OC seleccionada no tiene nro SICE.'))

        if obj.cod_moneda:
            facturaAlta['codMoneda'] = obj.cod_moneda.codMoneda
        elif obj.orden_compra_id.cod_moneda:
            facturaAlta['codMoneda'] = obj.orden_compra_id.cod_moneda.codMoneda
        else:
            raise osv.except_osv('Error!', u'La factura y/o la OC no tienen asignado el código de moneda SICE.')

        for articulo in obj.invoice_line:
            # control decimales en las cantidades
            if articulo.quantity != round(articulo.quantity, 2):
                raise osv.except_osv('Error!', u'SICE sólo acepta 2 decimales en las cantidades')

            itemFactura = {
                'idItem': articulo.id_item,
                'idVariacion': articulo.id_variacion,
                'cantidad': round(articulo.quantity, 2),
                'precioUnitario': round(articulo.precio_sin_iva, 4),
                # 'codImpuestos': articulo.invoice_line_tax_id,
                'distUO': 'N',
                'idOC': obj.orden_compra_id.sice_id_oc
            }

            # cr.execute("select unme_cod, imp_cod from sice_art_serv_obra where cod = %(cod)s",
            #            {'cod': articulo.product_id.grp_sice_cod})
            # res = cr.fetchone()

            if articulo.invoice_line_tax_id:
                iva = articulo.invoice_line_tax_id[0].id
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
                                                 articulo.invoice_line_tax_id[0].name, articulo.product_id.name))
                    itemFactura['codImpuestos'] = tax_id
                else:
                    raise osv.except_osv('Error!',
                                         u'No existe el mapeo entre impuestos de GRP y SICE para impuesto %s.' % (
                                             articulo.invoice_line_tax_id[0].name,))
            else:
                #Solo controlo impuesto cuando el monto es mayor a 0
                if round(articulo.precio_sin_iva,4):
                    raise osv.except_osv('Error!',
                                         u'El artículo %s no tiene impuesto definido.' % (articulo.product_id.name,))

            facturaAlta['itemsAlta'].append(itemFactura)
        return facturaAlta

    @soap_sice.factura(request='alta')
    def enviar_invoice_sice_alta(self, cr, uid, ids, context=None):
        facturaAlta = self.prepare_invoice_sice_alta(cr, uid, ids, context=context)
        return facturaAlta

    def invoice_sice(self, cr, uid, ids, context=None):
        retorno = super(account_invoice, self).invoice_sice(cr, uid, ids, context=context)
        if not retorno:
            return False
        """
        Crea la compra en SICE mediante la invocación del WS 'alta' de
        la interfaz de SICE.
        """
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        integracion_sice = company.integracion_sice or False
        if not integracion_sice:
            self.write(cr, uid, ids, {'state': 'sice'})
            return True

        # compra
        compra = self.enviar_invoice_sice_alta(cr, uid, ids, context=context)
        # Guardamos el número de compra asignado por SICE
        self.write(cr, uid, ids, {'id_factura_sice': compra.idFactura, 'state': 'sice'})
        ctx = context.copy()
        ctx.update({'idFactura': compra.idFactura})
        # aprobación
        self.enviar_invoice_sice_aprobar(cr, uid, ids, context=ctx)
        return True

    @soap_sice.factura(request='consultar')
    def invoice_sice_consultar(self, cr, uid, ids, context=None):
        if not context.get('idFactura', False):
            raise osv.except_osv("Error", "ID de la factura no encontrado")
        return context['idFactura']

    @soap_sice.factura(request='cambiar_estado')
    def invoice_sice_cambiar_estado(self, cr, uid, ids, context=None):
        if not context.get('idFactura', False):
            raise osv.except_osv("Error", "ID de la factura no encontrado")
        return context['idFactura']

    @soap_sice.factura(request='eliminar')
    def invoice_sice_eliminar(self, cr, uid, ids, context=None):
        if not context.get('idFactura', False):
            raise osv.except_osv("Error", "ID de la factura no encontrado")
        return context['idFactura']

    def action_invoice_cancel_sice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        result = super(account_invoice, self).action_invoice_cancel_sice(cr, uid, ids, context=context)
        # si la Factura fue enviada a SICE (el campo id_factura_sice no es nulo), se llama a eliminar sice
        for factura in self.browse(cr, uid, ids, context=context):
            if factura.id_factura_sice:
                self.invoice_eliminar_sice(cr, uid, [factura.id], context=context)
        return result

    def invoice_eliminar_sice(self, cr, uid, ids, context=None):
        """
        Elimina la factura en SICE mediante la invocación del WS 'eliminar' de
        la interfaz de SICE.
        Primero se consulta el estado de la Factura con el WS 'consultar'
        Si la Factura esta en estado '1 - Armando factura', se elimina
        Si la factura esta en estado '2 - Factura cerrada', se intenta pasar a estado 1 con la operacion 'cambiarEstado' y luego se elimina
        """

        # Recorro la factura
        for obj in self.browse(cr, uid, ids):
            # El "cabezal"
            if not obj.id_factura_sice:
                raise osv.except_osv('Error!', u'La factura no tiene asignado Id de SICE.')

            ctx = context.copy()
            ctx.update({'idFactura': obj.id_factura_sice})

            # Invocando el método "consultar" del WS
            factura = self.invoice_sice_consultar(cr, uid, ids, context=ctx)
            _logger.info("Datos de la consulta: %s", factura)

            if factura.codEstado == 1:
                # Invocando el método "eliminar" del WS, le paso el id de Factura SICE
                elimino = self.invoice_sice_eliminar(cr, uid, ids, context=ctx)
                _logger.info("Respuesta al eliminar: %s", elimino)
            elif factura.codEstado == 2:
                # Invocando el método "cambiarEstado" del WS, le paso el id de OC SICE
                cambio_estado = self.invoice_sice_cambiar_estado(cr, uid, ids, context=ctx)
                _logger.info("Respuesta al cambiar de estado: %s", cambio_estado)
                # Invocando el método "eliminar" del WS, le paso el id de Factura SICE
                elimino = self.invoice_sice_eliminar(cr, uid, ids, context=ctx)
                _logger.info("Respuesta al eliminar: %s", elimino)
            else:
                raise osv.except_osv('Error!',
                                     u'En este estado no se puede eliminar una Factura: %s' % str(factura.codEstado))

            # Borrarmos la info de SICE en GRP
            self.write(cr, uid, [obj.id], {'id_factura_sice': False}, context=context)

        return True
