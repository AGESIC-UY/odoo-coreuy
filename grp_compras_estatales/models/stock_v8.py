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

from openerp import models, fields, api, _, exceptions
from lxml import etree


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    # TODO GAP 3 Spring 4: Modificando el dominio del location_id
    def list_locations(self):
        prod_obj = self.env['product.product']
        location_ids = []
        for wh in self.env['stock.warehouse'].search(
                [('encargado_ids.id', '=', self._uid)]):
            _loc_domain_dest_ids = [('usage', '!=', 'view')]
            domains = prod_obj.with_context({
                'warehouse': wh.id,
                'compute_child': True
            })._get_domain_locations()
            if domains:
                for _d in domains[0]:
                    if not isinstance(_d, (tuple,)):
                        _loc_domain_dest_ids.append(_d)
                    else:
                        _loc_domain_dest_ids.append(
                            ('parent_left', _d[1], _d[2]))
                location_ids += self.env['stock.location'].search(
                    _loc_domain_dest_ids).ids
        return location_ids

    @api.model
    def get_locations(self):
        return self.list_locations()

    location_ids = fields.Many2many(comodel_name="stock.location",
                                    string="Ubicaciones del encargado",
                                    compute='_compute_locations',
                                    default=get_locations)

    @api.one
    def _compute_locations(self):
        self.location_ids = self.list_locations()

    @api.model
    def default_get(self, fields):
        res = super(StockInventory, self).default_get(fields)
        location_ids = self.get_locations()
        res['location_id'] = location_ids[0] if len(location_ids) else []
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.constrains('date', 'fecha_prev')
    def check_fecha_prevista(self):
        if self.fecha_prev and self.date and self.fecha_prev < self.date:
            raise exceptions.ValidationError(
                u'La fecha prevista debe ser posterior a la fecha de creación')


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.one
    @api.depends('product_id')
    def _compute_show_sr_uom(self):
        self.show_sr_uom = self.line_sr_id and self.line_sr_id.product_id and self.product_id \
                           and self.line_sr_id.product_id.id != self.product_id.id
        if self.show_sr_uom and self._context.get('form_view_ref',
                                                  False) == 'stock.view_move_picking_form':  # from UI
            self.sr_product_uom_qty = self.line_sr_id.cantidad_pendiente
            self.sr_product_uom = self.line_sr_id.uom_id.id

    grp_sice_cod = fields.Integer(string='Código SICE',
                                  related='product_id.grp_sice_cod', readonly=1)
    show_sr_uom = fields.Boolean(compute="_compute_show_sr_uom")
    product_id = fields.Many2one(
        domain="[('type','<>','service'),('no_inventory','=',False)]")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None,
                        toolbar=False, submenu=False):
        if context is None:
            context = {}

        if view_type == 'tree':
            move_ids = self.search(
                ['|', ('location_id.responsable_id', '=', self.env.user.id), (
                    'location_dest_id.responsable_id', '=',
                    self.env.user.id)]).mapped('id')
            action = self.env.ref('stock.action_move_form2')
            action.domain = "[('id', 'in', [" + ','.join(
                map(str, move_ids)) + "])]"

        res = super(StockMove, self).fields_view_get(view_id=view_id,
                                                     view_type=view_type,
                                                     context=context,
                                                     toolbar=toolbar,
                                                     submenu=submenu)
        return res


class StockLocation(models.Model):
    _inherit = 'stock.location'

    operating_unit_ids = fields.Many2many('operating.unit',
                                          string='Unidades ejecutoras')

    @api.model
    def _get_act_window_dict_v8(self, name):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        res = mod_obj.xmlid_to_res_id(name, raise_if_not_found=True)
        result = act_obj.browse(res).read()[0]
        return result


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    product_id = fields.Many2one(
        domain="[('type','<>','service'),('no_inventory','=',False)]")


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None,
                        toolbar=False, submenu=False):
        if context is None:
            context = {}

        if view_type == 'tree':
            quants_ids = self.search(
                [('warehouse_id.encargado_ids', 'in', [self.env.user.id])]).ids
            action = self.env.ref('stock.quantsact')
            action.domain = "[('id', 'in', [" + ','.join(
                map(str, quants_ids)) + "])]"

        res = super(StockQuant, self).fields_view_get(view_id=view_id,
                                                      view_type=view_type,
                                                      context=context,
                                                      toolbar=toolbar,
                                                      submenu=submenu)
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None,
                   orderby=False, lazy=True):
        """Solo se muestran los quant si es encargado del almacén"""
        #Todo Valorar si se realiza por relgas de seguridad
        domain.extend(
            [['warehouse_id.encargado_ids', 'in', [self.env.user.id]]])
        return super(StockQuant, self).read_group(
            domain, fields, groupby, offset=offset,
            limit=limit, orderby=orderby, lazy=lazy
        )

    @api.multi
    @api.depends('location_id')
    def _compute_warehouse_id(self):
        for rec in self:
            rec.warehouse_id = rec.location_id and rec.location_id.get_warehouse(
                rec.location_id) or False

    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Almacén', compute='_compute_warehouse_id',
        store=True
    )
