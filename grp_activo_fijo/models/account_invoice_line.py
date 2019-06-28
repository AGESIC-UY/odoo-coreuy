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

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from datetime import datetime, date

class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.depends('account_id')
    def _get_obra_editable(self):
        asset_cat_pool = self.env['account.asset.category']
        for record in self:
            categories = asset_cat_pool.search([('tipo', 'in', ['obc'])])
            editable = False
            for category in categories:
                if category.account_asset_id.id == record.account_id.id:
                    editable = True
            record.obra_editable = editable

    # 001-Inicio
    @api.depends('price_unit', 'quantity')
    def _get_importe_imp_incl(self):
        for rec in self:
            rec.importe_imp_incl = rec.price_unit * rec.quantity
    # 001-Fin

    @api.one
    @api.depends('product_id')
    def _compute_product_stockable(self):
        self.product_stockable = (self.product_id and \
                                  self.product_id.type in ['consu','product'] and \
                                  not self.product_id.no_inventory)

    active_expense = fields.Boolean(string='Activar gasto')
    obra = fields.Many2one(
        comodel_name=u'grp.obras.curso',
        string=u'Obra',
    )
    obra_editable = fields.Boolean(
        compute=_get_obra_editable,
    )
    # 001-Inicio
    importe_imp_incl = fields.Float(
        compute='_get_importe_imp_incl',
        string=u'Importe',
    )
    seleccionar = fields.Boolean(u'Seleccionar')
    # 001-Fin
    product_stockable = fields.Boolean(compute="_compute_product_stockable", string="Es producto almacenable")

    def get_fecha_depreciacion(self, date_from):
        date_conv = datetime.strptime(date_from, "%Y-%m-%d")
        if date_conv.today().month >= 6:
            year_def = date_conv.today().year
            ret = date(year_def, 12, 31)
        else:
            year_def = date_conv.today().year
            ret = date(year_def, 06, 30)
        return ret.strftime('%Y-%m-%d')

    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
                          partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
                          company_id=None):
        res = super(account_invoice_line, self).product_id_change(product, uom_id, qty=0, name=name, type=type,
                                                                  partner_id=partner_id,
                                                                  fposition_id=fposition_id,
                                                                  price_unit=price_unit,
                                                                  currency_id=currency_id,
                                                                  company_id=company_id)
        product = self.env['product.product'].browse(product)
        if product.categ_id.activo_fijo:
            res['value'].update({'asset_category_id': product.categ_id.asset_category_id})
        return res

    @api.model
    def create(self, vals):
        if not vals.get('asset_category_id', False) and vals.get('product_id', False):
            product = self.env['product.product'].browse(vals['product_id'])
            if product.categ_id and product.categ_id.activo_fijo and product.categ_id.asset_category_id:
                vals.update({'asset_category_id': product.categ_id.asset_category_id.id })
        return super(account_invoice_line, self).create(vals)

    # TODO Gap 4 Spring 4: Modificando el purchase value de asset
    def asset_create(self, cr, uid, lines, context=None):
        context = context or {}
        asset_obj = self.pool.get('account.asset.asset')
        # if lines and not asset_obj.search(cr,uid, [('invoice_id','=',lines[0].invoice_id.id)]):
        if lines:
            tipo = 'doc_type' in context and context.get('doc_type', False)
            if lines[0].invoice_id.doc_type in ['3en1_invoice','invoice'] or tipo:

                #RAGU prorrateo ajuste
                prorated_amount = 0
                asset_lines = lines.filtered(lambda x: x.asset_category_id)
                if asset_lines:
                    last_asset_line_id = asset_lines[len(asset_lines)-1].id

                total_cost = sum(map(lambda x: x.quantity * x.price_unit, filter(lambda l: l.asset_category_id, lines)))
                expenses_list = map(lambda x: x.quantity * x.price_unit, filter(lambda l: l.active_expense, lines))
                for line in lines:
                    if line.asset_category_id:
                        quant = line.quantity
                        if not line.product_stockable or \
                           not line.invoice_id.orden_compra_id: # proceso de alta de productos stockables se hace desde stock.picking
                            while quant > 0:
                                vals = {
                                    'name': line.name,
                                    'code': line.invoice_id.number or False,
                                    'category_id': line.asset_category_id.id,
                                    # 'purchase_value': line.price_subtotal,  # echaviano 29/03
                                    'period_id': line.invoice_id.period_id.id,
                                    'partner_id': line.invoice_id.partner_id.id,
                                    'company_id': line.invoice_id.company_id.id,
                                    'currency_id': line.invoice_id.currency_id.id,
                                    'purchase_date': line.invoice_id.date_invoice,
                                    'invoice_id': line.invoice_id.id,
                                    # 'unidades_originales': line.quantity,
                                    # ECHAVIANO, corrigiendo error de creacion de activo desde factura
                                    'purchase_value_date': self.get_fecha_depreciacion(line.invoice_id.date_invoice),
                                    'operating_unit_id': line.invoice_id.operating_unit_id.id,
                                    # 002-Inicio
                                    'product_id': line.product_id.id,
                                    # 002-Fin
                                }
                                # 002- Inicio inc - 536
                                iva_include = False
                                for tax in line.invoice_line_tax_id:
                                    # si es iva incluido
                                    if tax.price_include:
                                        iva_include = True
                                current_cost = iva_include and line.quantity * line.price_unit or line.price_subtotal
                                percent = current_cost / float(total_cost)
                                expense_distrb = sum(map(lambda x: (x*percent) / line.quantity, expenses_list))
                                prorated_amount += round(expense_distrb,2)
                                # RAGU asignando a ultima linea de activo fijo el sobrante de los redondeos de la prorrata
                                if line.id == last_asset_line_id and prorated_amount < sum(expenses_list):
                                    expense_distrb += sum(expenses_list) - prorated_amount

                                vals.update({'purchase_value': expense_distrb + line.price_unit})
                                # 002- Fin inc - 536
                                changed_vals = asset_obj.onchange_category_id(cr, uid, [], vals['category_id'], context=context)
                                vals.update(changed_vals['value'])
                                # Crear un activo fijo por cada unidad de la linea de factura
                                asset_id = asset_obj.create(cr, uid, vals, context=context)
                                if line.asset_category_id.open_asset:
                                    asset_obj.validate(cr, uid, [asset_id], context=context)

                                quant -=1
                        elif line.purchase_line_id:
                            # Actualizar el dato Nro. factura GRP
                            stock_moves = line.purchase_line_id.move_ids | line.purchase_line_id.move_ids.mapped('returned_move_ids')
                            stock_moves = stock_moves.filtered(lambda r: r.state != 'cancel')
                            pickings = stock_moves.mapped('picking_id')
                            if pickings:
                                domain = [('invoice_id','=',False),
                                          ('product_id','=',line.product_id.id),
                                          ('origin_picking_id','in',pickings.ids),
                                         ]
                                asset_ids = asset_obj.search(cr, uid, domain, order='id', limit=quant, context=context)
                                if len(asset_ids) < quant:
                                    raise ValidationError(u'La cantidad del producto %s en la línea de la factura es mayor a la cantidad de bienes disponibles (%s).' % (line.product_id.name, len(asset_ids)))
                                if asset_ids:
                                    asset_obj.write(cr, uid, asset_ids, {'invoice_id': line.invoice_id.id}, context=context)
        return True
