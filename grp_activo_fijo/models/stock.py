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
from openerp import api, fields as fields2
import time

class stock_transfer_details(osv.TransientModel):
    _inherit = "stock.transfer_details"

    @api.one
    def do_detailed_transfer(self):
        result = super(stock_transfer_details, self).do_detailed_transfer()

        PurchaseOrder = self.env['purchase.order']
        Asset = self.env['account.asset.asset'].sudo()
        MroAsset = self.env['asset.asset'].sudo()
        UbicFisica = self.env['grp.ubicacion.fisica']
        StockMove = self.env['stock.move']
        StockPicking = self.env['stock.picking']
        ctx = dict(self._context or {}, asset_create_move=False)
        picking = self.picking_id
        in_po = False
        if picking.picking_type_id.code == 'incoming' and picking.origin:
            in_po = PurchaseOrder.search([('name','=',picking.origin)], limit=1)
            # Si es una reversión de una reversión de una recepción asociada a una compra
            if not in_po:
                out_pick = StockPicking.search([('name','=',picking.origin)], limit=1)
                if out_pick and out_pick.picking_type_id.code == 'outgoing' and out_pick.origin:
                    in_pick = StockPicking.search([('name','=',out_pick.origin)], limit=1)
                    if in_pick and in_pick.picking_type_id.code == 'incoming' and in_pick.origin:
                        in_po = PurchaseOrder.search([('name','=',in_pick.origin)], limit=1)
        origin_pick = False
        if picking.picking_type_id.code == 'outgoing' and picking.origin:
            origin_pick = StockPicking.search([('name','=',picking.origin)], limit=1)
        out_po = False
        if origin_pick and origin_pick.picking_type_id.code == 'incoming' and origin_pick.origin:
            out_po = PurchaseOrder.search([('name','=',origin_pick.origin)], limit=1)
            if not out_po:
                out_pick = StockPicking.search([('name','=',origin_pick.origin)], limit=1)
                if out_pick and out_pick.picking_type_id.code == 'outgoing' and out_pick.origin:
                    in_pick = StockPicking.search([('name','=',out_pick.origin)], limit=1)
                    if in_pick and in_pick.picking_type_id.code == 'incoming' and in_pick.origin:
                        out_po = PurchaseOrder.search([('name','=',in_pick.origin)], limit=1)
        if in_po or out_po:
            for item in self.item_ids:
                move = StockMove.search([('picking_id','=',picking.id),('product_id','=',item.product_id.id)], limit=1)
                if move.product_id and move.product_id.categ_id and \
                   move.product_id.categ_id.activo_fijo and \
                   move.product_id.type in ['consu','product'] and not move.product_id.no_inventory:
                    if not move.asset_category_id and move.product_id.categ_id.asset_category_id:
                        move.write({'asset_category_id': move.product_id.categ_id.asset_category_id.id })
                    if not move.asset_category_id:
                        raise osv.except_osv('Error', u"Debe configurar la categoría de Activo Fijo en el movimiento.")
                    qty = item.quantity # normalizada a la unidad de medida base
                    if in_po:
                        po_prod_lines = in_po.order_line.filtered(lambda x: x.product_id.id==move.product_id.id)
                        location_dest_id = move.location_dest_id and move.location_dest_id.id or picking.location_dest_id.id  # tomar ubic destino del item o del move?
                        ubic_fisica = location_dest_id and UbicFisica.search([('stock_location_id','=',location_dest_id)], limit=1) or False
                        if not ubic_fisica:
                            raise osv.except_osv('Error', u"No existe ubicación física de Activo Fijo para la ubicación '%s'. Debe configurar una ubicación física con dicha ubicación de almacén." % (move.location_dest_id.complete_name))
                        while qty > 0:
                            purchase_value = sum(po_prod_lines.mapped('price_unit'))
                            if in_po.currency_oc.id != in_po.company_id.currency_id.id:
                                purchase_value = in_po.currency_oc.with_context(date=(in_po.fecha_tipo_cambio_oc or time.strftime('%Y-%m-%d'))).compute(purchase_value, in_po.company_id.currency_id)
                            vals = {
                                'name': move.name,
                                'product_id': move.product_id.id,
                                'invoice_id': False,
                                'operating_unit_id': in_po.operating_unit_id and in_po.operating_unit_id.id or False,
                                'category_id': move.asset_category_id.id,
                                'purchase_date': picking.date and picking.date[:10] or time.strftime('%Y-%m-%d'),
                                'currency_id': in_po.company_id.currency_id.id,
                                'purchase_value': purchase_value,
                                'partner_id': in_po.partner_id.id,
                                'code': picking.name, #*
                                'origin_picking_id': picking.id,
                                'ubicacion_fisica': ubic_fisica.id,
                            }

                            changed_vals = Asset.onchange_category_id(vals['category_id'])
                            vals.update(changed_vals.get('value', {}))
                            vals['purchase_value_date'] = Asset._default_purchase_value_date() # ??
                            asset = Asset.with_context(ctx).create(vals)
                            if move.asset_category_id.open_asset:
                                asset.with_context(ctx).validate()
                            qty -= 1

                        # TODO: hacer esto?
                        if move.asset_category_id.is_asset_mro:
                            MroAsset.with_context(ctx).create({ 'name': move.name })

                    if out_po:
                        location_id = move.location_id and move.location_id.id or picking.location_id.id
                        ubic_fisica = location_id and UbicFisica.search([('stock_location_id','=',location_id)], limit=1) or False
                        if not ubic_fisica:
                            raise osv.except_osv('Error', u"No existe ubicación física de Activo Fijo para la ubicación '%s'. Debe configurar una ubicación física con dicha ubicación de almacén." % (move.location_dest_id.complete_name))
                        domain = [('product_id','=',move.product_id.id),
                                  ('ubicacion_fisica','=',ubic_fisica.id),
                                  ('origin_picking_id','=',origin_pick.id),
                                  ('state','=','draft'),
                                  #('category_id','=',move.asset_category_id.id), # include?
                                 ]
                        assets = Asset.search(domain, order='id', limit=qty)
                        if assets and len(assets)==qty:
                            assets.unlink()
                        else:
                            if not assets:
                                raise osv.except_osv('Error', u"No se encuentran activos fijos en estado Borrador para el producto '%s' en la ubicación física '%s'." % (move.product_id.name, ubic_fisica.nombre_completo))
                            if len(assets) < qty:
                                raise osv.except_osv('Error', u"La cantidad de activos fijos en estado Borrador para el producto '%s' en la ubicación física '%s' es menor a la cantidad que desea devolver." % (move.product_id.name, ubic_fisica.nombre_completo))
                            raise osv.except_osv('Error', u"Debe corregir los datos de los Activos Fijos para el producto '%s' generados en la recepción." % (move.product_id.name))

        return result

class stock_move(osv.osv):
    _inherit = 'stock.move'

    _columns = {
        'asset_category_id': fields.many2one('account.asset.category', string=u"Categoría de activo fijo", states={'done': [('readonly', True)]}),
    }
    is_asset_categ = fields2.Boolean(related="product_id.categ_id.activo_fijo", string=u"Es categoría de activo fijo")

    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False, asset_category_id=False):
        result = super(stock_move, self).onchange_product_id(cr, uid, ids, prod_id=prod_id, loc_id=loc_id, loc_dest_id=loc_dest_id, partner_id=partner_id)
        if prod_id and not asset_category_id:
            product = self.pool.get('product.product').browse(cr, uid, prod_id)
            if product.categ_id and product.categ_id.activo_fijo and product.categ_id.asset_category_id:
                if 'value' not in result:
                    result['value'] = {}
                result['value'].update({
                    'asset_category_id': product.categ_id.asset_category_id.id
                })
        return result

    @api.model
    def create(self, vals):
        if not vals.get('asset_category_id', False) and vals.get('product_id', False):
            product = self.env['product.product'].browse(vals['product_id'])
            if product.categ_id and product.categ_id.activo_fijo and product.categ_id.asset_category_id:
                vals.update({'asset_category_id': product.categ_id.asset_category_id.id })
        return super(stock_move, self).create(vals)
