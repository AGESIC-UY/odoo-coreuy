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

from openerp import models, fields, api
from openerp.exceptions import Warning
from openerp.tools.translate import _
from openerp.addons.grp_sice.grp_sice import soap_sice

import logging
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    ajustar_facturas = fields.Boolean(
        string=u'¿Factura de ajustes?', default=False)
    ajustar_facturas_readonly = fields.Boolean(translate=False, default=False)
    factura_ajuste_id = fields.Many2one(
        comodel_name='account.invoice', string=u'Factura')
    factura_ajuste_ids = fields.One2many(
        comodel_name='account.invoice',
        inverse_name='factura_ajuste_id',
        string=u'Factura que se ajusta')

    @api.onchange('ajustar_facturas')
    def onchange_domain_facturas_o2m(self):
        return {
            'domain': {
                'factura_ajuste_ids': [('orden_compra_id', '=',self.orden_compra_id.id),('ajustar_facturas','=',False),('state','!=','draft')]
            }
        }

    def invoice_check_oc(self, cr, uid, factura_ids, context=None):
        invoices = self.read(cr,uid,factura_ids,{'ajustar_facturas'})
        filtered_factura_ids = []
        for invoice in invoices:
            if not invoice.get('ajustar_facturas',False):
                filtered_factura_ids.append(invoice['id'])
        if filtered_factura_ids:
            return super(AccountInvoice, self).invoice_check_oc(cr,uid,filtered_factura_ids,context=context)
        else:
            return True

    @api.multi
    def cargar_lineas_facturas(self):
        self.mapped('invoice_line').unlink()
        for rec in self:
            if rec.ajustar_facturas and len(rec.factura_ajuste_ids):
                lines = []
                for line in rec.factura_ajuste_ids.mapped('invoice_line'):
                    line.copy({
                        'invoice_id':rec.id,
                        'origen_ajuste_factura_id': line.invoice_id.id,
                        'cantidad_factura': line.quantity,
                        'precio_factura': line.price_subtotal,
                        'invoice_line_tax_id': None,
                        'quantity': 1,
                    })
                    # lines.append((0, 0, {
                    #     'name': line.name,
                    #     'origen_ajuste_factura_id': line.invoice_id.id,
                    #     'nro_factura': line.invoice_id.number,
                    #     'origin': line.origin,
                    #     'invoice_line_tax_id': None,
                    #     'uos_id': line.uos_id.id,
                    #     'product_id': line.product_id.id,
                    #     'account_id': line.account_id.id,
                    #     'price_unit': line.price_unit,
                    #     'price_subtotal': line.price_subtotal,
                    #     'cantidad_factura': line.quantity,
                    #     'precio_factura': line.price_subtotal,
                    #     'quantity': 1,
                    #     'purchase_line_id': line.purchase_line_id.id,
                    #     'id_item': line.id_item,
                    #     'id_variacion': line.id_variacion,
                    #     'desc_variacion': line.desc_variacion,
                    # }))

                # rec.invoice_line = lines

    @soap_sice.factura_ajuste(request='aprobar')
    def enviar_invoice_ajuste_sice_aprobar(self, cr, uid, ids, context=None):
        _logger.info("LOGGER self._context: %s, context: %s", self._context, context)
        if not context.get('idFacturaAjuste', False):
            raise Warning("Error", "ID de la factura de ajuste no encontrado")
        return context.get('idFacturaAjuste', False)

    @soap_sice.factura_ajuste(request='eliminar')
    def invoice_ajuste_sice_eliminar(self, cr, uid, ids, context=None):
        _logger.info("LOGGER self._context: %s, context: %s", self._context, context)
        if not context.get('idFacturaAjuste', False):
            raise Warning("Error", "ID de la factura de ajuste no encontrado")
        return context['idFacturaAjuste']

    @soap_sice.factura_ajuste(request='consultar')
    def invoice_ajuste_sice_consultar(self, cr, uid, ids, context=None):
        _logger.info("LOGGER self._context: %s, context: %s", self._context, context)
        if not context.get('idFacturaAjuste', False):
            raise Warning("Error", "ID de la factura de ajuste no encontrado")
        return context['idFacturaAjuste']

    @soap_sice.factura_ajuste(request='cambiar_estado')
    def invoice_ajuste_sice_cambiar_estado(self, cr, uid, ids, context=None):
        _logger.info("LOGGER self._context: %s, context: %s", self._context, context)
        if not context.get('idFacturaAjuste', False):
            raise Warning("Error", "ID de la factura de ajuste no encontrado")
        return context['idFacturaAjuste']

    @api.one
    def prepare_invoice_ajuste_sice_alta(self):
        facturaAlta = {
            'secFacturaAjuste': self.sec_factura,
            'fechaFacturaAjuste': self.date_invoice,
            'fechaVencFacturaAjuste': self.date_due,
            'proveedor': {
                'tipoDocProv': self.partner_id.tipo_doc_rupe,
                'nroDocProv': self.partner_id.nro_doc_rupe
            },
            'itemsAlta': []
        }
        if self.supplier_invoice_number:
            facturaAlta['nroFacturaAjuste'] = self.supplier_invoice_number
        else:
            raise Warning(
                _('Error!'),
                _(u'Por favor ingrese el nro de factura del proveedor.'))
        if self.serie_factura:
            facturaAlta['serieFacturaAjuste'] = self.serie_factura
        else:
            raise Warning(
                _('Error!'), _(u'Por favor ingrese la serie de la factura.'))
        if self.sec_factura > 99:
            raise Warning(
                _('Error!'),
                _(u'El largo máximo de la secuencia de factura es 2.'))
        if not self.orden_compra_id:
            raise Warning(_('Error!'), _(u'Por favor ingrese el nro de OC.'))
        elif not self.orden_compra_id.sice_id_oc:
            raise Warning(
                _('Error!'),
                _(u'Primero debe enviar a SICE la OC asociada a la Factura.'))
        elif not self.orden_compra_id.pedido_compra_id:
            raise Warning(
                _('Error!'),
                _(u'La OC seleccionada no tiene pedido de compra asociado.'))
        if self.orden_compra_id.pedido_compra_id.sice_id_compra:
            facturaAlta[
                'idCompra'] = self.orden_compra_id.pedido_compra_id.sice_id_compra
        else:
            raise Warning(
                _('Error!'),
                _(u'El pedido de compra asociado a la OC seleccionada no tiene nro SICE.'
                  ))

        if self.cod_moneda:
            facturaAlta['codMoneda'] = self.cod_moneda.codMoneda
        elif self.orden_compra_id.cod_moneda:
            facturaAlta[
                'codMoneda'] = self.orden_compra_id.cod_moneda.codMoneda
        else:
            raise Warning(
                'Error!',
                u'La factura y/o la OC no tienen asignado el código de moneda SICE.'
            )

        for articulo in self.invoice_line:
            # control decimales en las cantidades
            if articulo.quantity != round(articulo.quantity, 2):
                raise Warning('Error!', u'SICE sólo acepta 2 decimales en las cantidades')

            itemFactura = {
                'idFactura': articulo.origen_ajuste_factura_id.id_factura_sice,
                'idItem': articulo.id_item,
                'idVariacion': articulo.id_variacion,
                # 'cantidad': round(articulo.quantity, 2),
                # 'precioUnitario': round(articulo.precio_sin_iva, 4),
                # 'codImpuestos': articulo.invoice_line_tax_id,
                'montoAjuste': round(articulo.monto_moneda_base, 2),
                'idOC': self.orden_compra_id.sice_id_oc
            }

            facturaAlta['itemsAlta'].append(itemFactura)
        return facturaAlta

    @soap_sice.factura_ajuste(request='alta')
    def enviar_invoice_ajuste_sice_alta(self, cr, uid, ids, context=None):
        facturaAltaAjuste = self.prepare_invoice_ajuste_sice_alta()[0]
        return facturaAltaAjuste

    @api.multi
    def factura_ajuste_sice(self):
        # retorno = super(account_invoice_ext_api, self).factura_ajuste_sice()
        # if not retorno:
        #     return False
        """
        Crea la compra en SICE mediante la invocación del WS 'alta' de
        la interfaz de SICE.
        """
        company = self.env.user.company_id
        integracion_sice = company.integracion_sice or False
        if not integracion_sice:
            values = {
                'nro_factura_grp': self.env['ir.sequence'].with_context(
                    {'fiscalyear_id': self.fiscalyear_siif_id.id}).get('sec.factura'),
                'state': 'sice'
            }
            self.write(values)
        else:
            # compra
            compra = self.enviar_invoice_ajuste_sice_alta(
                self._cr, self._uid, self._ids, context=self._context)
            print "***********"
            print compra
            print "***********"
            # Guardamos el número de compra asignado por SICE
            values = {
                'nro_factura_grp': self.env['ir.sequence'].with_context(
                    {'fiscalyear_id': self.fiscalyear_siif_id.id}).get('sec.factura'),
                'state': 'sice',
                'id_factura_sice': compra.idFacturaAjuste
            }
            self.write(values)

            ctx = self._context.copy()
            ctx.update({'idFacturaAjuste': compra.idFacturaAjuste})
            #aprobación
            self.enviar_invoice_ajuste_sice_aprobar(self._cr, self._uid, self._ids, context=ctx)
        return True

    @api.multi
    def invoice_eliminar_sice(self):
        """
        Elimina la factura en SICE mediante la invocación del WS 'eliminar' de
        la interfaz de SICE.
        Primero se consulta el estado de la Factura con el WS 'consultar'
        Si la Factura esta en estado '1 - Armando factura', se elimina
        Si la factura esta en estado '2 - Factura cerrada', se intenta pasar a estado 1 con la operacion 'cambiarEstado' y luego se elimina
        """

        # Recorro la factura
        facturas_ajuste = self.filtered(lambda x: x.ajustar_facturas)
        for obj in facturas_ajuste:
            if not obj.id_factura_sice:
                raise Warning(_('Error!'), _(u'La factura no tiene asignado Id de SICE.'))

            ctx = self._context.copy()
            ctx.update({'idFacturaAjuste': obj.id_factura_sice})

            # Invocando el método "consultar" del WS
            factura = self.invoice_ajuste_sice_consultar(self._cr, self._uid, self._ids, context=ctx)
            _logger.info("Datos de la consulta: %s", factura)

            if factura.codEstado == 1:
                # Invocando el método "eliminar" del WS, le paso el id de Factura SICE
                elimino = self.invoice_ajuste_sice_eliminar(self._cr, self._uid, self._ids, context=ctx)
                _logger.info("Respuesta al eliminar: %s", elimino)
            elif factura.codEstado == 2:
                # Invocando el método "cambiarEstado" del WS, le paso el id de OC SICE
                cambio_estado = self.invoice_ajuste_sice_cambiar_estado(self._cr, self._uid, self._ids, context=ctx)
                _logger.info("Respuesta al cambiar de estado: %s", cambio_estado)
                # Invocando el método "eliminar" del WS, le paso el id de Factura SICE
                elimino = self.invoice_ajuste_sice_eliminar(self._cr, self._uid, self._ids, context=ctx)
                _logger.info("Respuesta al eliminar: %s", elimino)
            else:
                raise Warning(_('Error!'), _(u'En este estado no se puede eliminar una Factura: %s' % str(factura.codEstado)))

        # Borrarmos la info de SICE en GRP
        facturas_ajuste.write({'id_factura_sice': False})

        a = super(AccountInvoice, self.filtered(lambda x: not x.ajustar_facturas)).invoice_eliminar_sice()
        return a


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    ajustar_facturas = fields.Boolean(
        string=u'¿Factura de ajustes?', related='invoice_id.ajustar_facturas', readonly=True)
    origen_ajuste_factura_id = fields.Many2one('account.invoice', string='Factura origen de ajuste')
    origen_ajuste_supplier_invoice_number = fields.Char(string=u'Factura que ajusta', related='origen_ajuste_factura_id.supplier_invoice_number', readonly=True)
    cantidad_factura = fields.Integer(string=u'Cantidad factura', readonly=True)
    precio_factura = fields.Float(string=u'Precio factura', readonly=True)