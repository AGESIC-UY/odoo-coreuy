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
from openerp import api, exceptions, fields, models, _
from lxml import etree
from openerp.osv.orm import setup_modifiers
import time
from datetime import datetime
from openerp.exceptions import Warning

class grpMSPCotizacion(models.Model):
    _inherit = 'grp.cotizaciones'

    sub_tipo_solicitud = fields.Selection(string=u'Sub-Tipo Solicitud', related='pedido_compra_id.sub_tipo_solicitud',
                                          size=60, readonly=True)
    show_button = fields.Boolean('Mostrar Boton', compute='_compute_show_button')
    se_cargo_datos = fields.Boolean('Mostrar Boton', default=False)

    @api.multi
    @api.depends('sub_tipo_solicitud', 'tipo_compra_cod')
    def _compute_show_button(self):
        for rec in self:
            rec.show_button = False
            if rec.sub_tipo_solicitud in ['compra_uca'] or rec.tipo_compra_cod == 'CD':
                rec.show_button = True

    # TODO: SPRING 6 GAP 204
    def onchage_pedido_compra(self, cr, uid, ids, pedido_compra, context=None):
        value = super(grpMSPCotizacion, self).onchage_pedido_compra(cr, uid, ids, pedido_compra)
        if pedido_compra:
            pedido = self.pool.get('grp.pedido.compra').browse(cr, uid, pedido_compra, context=None)
            if pedido.tipo_compra.idTipoCompra == 'SP':
                values_aceptadas = []
                if ids:
                    # desvincular existentes
                    self.write(cr, uid, ids, {'sice_page_aceptadas': [(5,)]}, context)
                line_number = 0
                for linea in pedido.lineas_ids:
                    # TODO R INCIDENCIA
                    if pedido.sub_tipo_solicitud == 'compra_uca':
                        if len(pedido.compra_uca_ids) > line_number:
                            linea_uca_id = pedido.compra_uca_ids[line_number]
                        else:
                            raise Warning(_('La cantidad de líneas UCA del Pedido de Compra no corresponde con las líneas de la Solicitud de Compra'))
                        line_number += 1
                    # linea_uca_id = linea.pedido_id.compra_uca_ids.filtered(lambda x: x.product_id.id == linea.product_id.id and x.quantity == linea.cantidad_comprar_sice and x.uom_id.id == linea.uom_id.id)
                    values_aceptadas.append((0, 0, {
                        'codigo_articulo': linea.sice_cod_articulo,
                        'product_id': linea.product_id.id,
                        'uom_id': linea.uom_id.id,
                        'cantidad': linea.cantidad_comprar_sice,
                        'precio': linea.precio_estimado,
                        'precio_sice': linea.precio_estimado / (1 + linea.iva[0].amount),
                        'iva': [(6, 0, [line.id for line in linea.iva])],
                        'currency': pedido.moneda.id,
                        'odg': linea.odg,
                        'proveedor_cot_id': linea_uca_id.provider_id.id if pedido.sub_tipo_solicitud == 'compra_uca' and linea_uca_id else False
                    }))
                value['value']['sice_page_aceptadas'] = values_aceptadas
        return value

    # TODO: SPRING 7 GAP 469
    @api.multi
    def cargar_datos_pedido(self):
        if self.pedido_compra_id:
            values_aceptadas = [(5,)]
            for linea in self.pedido_compra_id.lineas_ids:
                proveedor = False
                if self.pedido_compra_id.sub_tipo_solicitud == 'compra_uca':
                    # Si la linea de UCA no tiene linea de PC, entonces
                    # hace la busqueda por solicitud_compra_id
                    # Si la linea de UCA tiene linea de PC, entonces
                    # hace la busqueda por pedido_linea_id
                    uca_list = self.pedido_compra_id.compra_uca_ids.filtered(
                        lambda x: (not x.pedido_linea_id and
                                   x.solicitud_compra_id.id == linea.solicitud_compra_id.id) or
                                  (x.pedido_linea_id and
                                   x.pedido_linea_id.id == linea.id)
                    )
                    if len(uca_list) == 1 and uca_list[0].provider_id:
                        proveedor = uca_list[0].provider_id.id
                values_aceptadas.append((0, 0, {
                    'proveedor_cot_id': proveedor,
                    'codigo_articulo': linea.sice_cod_articulo,
                    'product_id': linea.product_id.id,
                    'uom_id': linea.uom_id.id,
                    'cantidad': linea.cantidad_comprar_sice,
                    'precio': linea.precio_estimado,
                    'iva': [(6, 0, [line.id for line in linea.iva])],
                    'currency': self.pedido_compra_id.moneda.id
                }))
            self.write({'sice_page_aceptadas': values_aceptadas, 'se_cargo_datos': True})
        return self.id


class grp_msp_cotizaciones_lineas_aceptadas(models.Model):
    _name = 'grp.cotizaciones.lineas.aceptadas'
    _inherit = 'grp.cotizaciones.lineas.aceptadas'

    proveedor_cot_id = fields.Many2one('res.partner', 'Proveedor', required=False)
    idTipoCompra = fields.Char('Tipo', related='pedido_cot_id.pedido_compra_id.idTipoCompra', readonly=True)
    sub_tipo_solicitud = fields.Selection(string=u'Sub-Tipo Solicitud',
                                          related='pedido_cot_id.pedido_compra_id.sub_tipo_solicitud', size=60)
