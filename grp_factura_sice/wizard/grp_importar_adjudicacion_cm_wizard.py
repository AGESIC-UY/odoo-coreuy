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

from openerp import fields, models, api, _
from openerp.exceptions import ValidationError
import logging
import openerp.addons.decimal_precision as dp
from lxml import etree

_logger = logging.getLogger(__name__)


class GrpImportarAdjudicacionCMWizard(models.TransientModel):
    _name = 'grp.importar.adjudicacion.cm.wizard'
    _description = u'Adjudicación Convenio Marco'

    adjudicacion_ids = fields.One2many('grp.importar.adjudicacion.cm.wizard.lineas',
                                       'adjudicacion_cm_id',
                                       string=u'Líneas de Adjudicación Convenio Marco')

    @api.multi
    def cargar_datos_adjudicacion(self):
        active_id = self._context.get('active_id', False)
        if active_id:
            for rec in self:
                lineas_seleccionadas = []
                for line in rec.adjudicacion_ids:
                    if line.seleccionado:
                        adj_ids = self._context.get('default_adjudicacion_ids', [])
                        iva = []
                        for line_adj in adj_ids:
                            if line_adj[2].get('iva', False) and line_adj[2]['id_item'] == line.id_item:
                                iva = line_adj[2]['iva']
                                break

                        lineas_seleccionadas.append((0, 0, {
                            'proveedor_cot_id': line.proveedor_cot_id.id,
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'cantidad': line.cantidad,
                            'uom_id': line.uom_id.id,
                            'precio': line.precio,
                            'precio_sice': line.precio_sice,
                            'codigo_impuesto': line.codigo_impuesto,
                            'codigo_articulo': line.codigo_articulo,
                            'currency': line.currency.id,
                            'precioTotal': line.precio_total,
                            'iva': iva,
                            'odg': line.odg,
                            'atributos': line.atributos,
                            'id_variacion': line.id_variacion,
                            'id_item': line.id_item,
                            'desc_variacion': line.desc_variacion,
                            'cod_moneda': line.cod_moneda.id,
                        }))
            self.env['grp.cotizaciones'].browse([active_id]).write({'sice_page_aceptadas': lineas_seleccionadas})
        return True


class GrpImportarAdjudicacionCMWizardLineas(models.TransientModel):
    _name = 'grp.importar.adjudicacion.cm.wizard.lineas'
    _description = u'Líneas de Adjudicación Convenio Marco'

    adjudicacion_cm_id = fields.Many2one('grp.importar.adjudicacion.cm.wizard', u"Adjudicación Convenio Marco")
    seleccionado = fields.Boolean(u"Seleccionado")
    proveedor_cot_id = fields.Many2one('res.partner', 'Proveedor', required=True)
    product_id = fields.Many2one('product.product', u'Producto', ondelete='set null', select=True)
    name = fields.Char(u'Descripción Producto')
    cantidad = fields.Float('Cantidad', required=True)
    uom_id = fields.Many2one('product.uom', 'UdM', required=True)
    precio = fields.Float('Precio Unitario', required=True)
    precio_sice = fields.Float('Precio s/imp', digits_compute=dp.get_precision('Product Price'),
                                help='Precio unitario del producto devuelto por sice en el ws' "Precio s/imp")
    codigo_impuesto = fields.Char(u'Código Impuesto')
    codigo_articulo = fields.Integer(u'Código Artículo')
    currency = fields.Many2one('res.currency', 'Moneda')
    precio_total = fields.Float(string='Precio Total', digits_compute=dp.get_precision('Account'))
    odg = fields.Integer('OdG')
    atributos = fields.Char('Atributos')
    id_variacion = fields.Integer(u'Id Variación ')
    id_item = fields.Integer('Id Item')
    desc_variacion = fields.Char(u'Descripción variación')
    cod_moneda = fields.Many2one('sicec.moneda', u'Código moneda SICE')


