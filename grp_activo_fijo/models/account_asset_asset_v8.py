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

class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'

    tipo_categoria = fields.Selection(related='category_id.tipo', string=u'Tipo de Categoría', store=True, readonly=True)

    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Unidad ejecutora responsable',
        required=True,
        default=lambda self: (self.env['res.users'].operating_unit_default_get(self.env.uid))
    )

    poliza_ids = fields.One2many(
        comodel_name='account.asset.asset.poliza.seguro',
        inverse_name='asset_id',
        string=u'Póliza de Seguro'
    )

    amortizacion_parcial = fields.Float(
        string=u'Amortización Parcial'
    )

    invoice_ids = fields.Many2many(
        comodel_name='account.invoice',
        relation='ass_asset_invoice_rel',
        column1='asset_id',
        column2='invoice_id',
        string=u'Facturas relacionadas')
    motivo_alta_id = fields.Many2one(comodel_name='motivo.alta.activo', string=u'Motivo de alta')
    move_id = fields.Many2one(comodel_name='account.move', string=u'Asiento Alta Activo Fijo', readonly=True)

    af_revision = fields.Boolean(related='company_id.revision_af_required', readonly=True)
    ubicacion_fisica = fields.Many2one('grp.ubicacion.fisica', string=u'Ubicación física')
    origin_picking_id = fields.Many2one('stock.picking', string=u"Recepción OC asociada", readonly=True)

    #Se filtran los AF de su operating_unit para los usuarios que tienen el grupo Restringir AF por UE
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.user.has_group('grp_activo_fijo.grp_af_restringir_ue'):
            if ['operating_unit_id', '=', self.env.user.default_operating_unit_id.id] not in args:
                args.append(['operating_unit_id', '=', self.env.user.default_operating_unit_id.id])
        return super(AccountAssetAsset, self).search(args, offset, limit, order, count=count)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self.env.user.has_group('grp_activo_fijo.grp_af_restringir_ue'):
            if ['operating_unit_id', '=', self.env.user.default_operating_unit_id.id] not in domain:
                domain.append(['operating_unit_id', '=', self.env.user.default_operating_unit_id.id])
        return super(AccountAssetAsset, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            nombre = ""
            if rec.state in ['draft', 'baja']:
                nombre = rec.name if rec.name else ""
            else:
                nombre = ""
                if rec.name:
                    nombre += rec.name
                    if rec.numero_activo:
                        nombre += " " + rec.numero_activo
                elif rec.numero_activo:
                    nombre += rec.numero_activo
            result.append((rec.id, nombre))
        return result

    @api.multi
    def set_to_check(self):
        self.write({'state': 'check'})
        for rec in self:
            _model, group_id = self.env['ir.model.data'].get_object_reference('grp_activo_fijo','grp_af_responsable_financiero')
            users = self.env['res.users'].search([('groups_id', 'in', group_id),('operating_unit_ids','in',rec.operating_unit_id.id)])
            partner_ids = []
            if users:
                partner_ids = [user.partner_id.id for user in users]

            self.message_post(partner_ids=partner_ids,
                              body="Se ha creado un activo fijo, favor de revisar la información del activo fijo "
                                   "para que el mismo pueda ser dado de alta en el sistema",subtype='mail.mt_comment')
        return True

    @api.multi
    def set_to_draft1(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def validate(self):
        if not self.invoice_id and self.motivo_alta_id and not self.motivo_alta_id.migracion:
            period_id = self.env['account.period'].search(
                [('date_start', '<=', self.fecha_alta), ('date_stop', '>=', self.fecha_alta)], limit=1)
            if period_id and period_id.state != 'done':
                if self.purchase_value > 0:
                    mv_id = self.env['account.move'].create({
                        'name': '/',
                        'journal_id': self.motivo_alta_id.journal_id.id,
                        'date': self.fecha_alta,
                        'period_id': period_id.id,
                        'state': 'posted' if self.motivo_alta_id.journal_id.entry_posted is True else 'draft',
                        'line_id': [
                            (0, 0, {
                                'name': '/',
                                'account_id': self.category_id.account_asset_id.id,
                                'debit': self.purchase_value,
                            }),
                            (0, 0, {
                                'name': '/',
                                'account_id': self.motivo_alta_id.account_id.id,
                                'credit': self.purchase_value,
                            }),
                        ]
                    })
                    self.write({'move_id': mv_id.id})
                else:
                    raise exceptions.ValidationError(_(u'El costo de adquisición debe ser mayor que cero'))
            else:
                raise exceptions.ValidationError(_(u'La Fecha de alta no puede ser de un periodo cerrado'))
        res = super(AccountAssetAsset, self).validate()
        return res

    @api.multi
    def update_historial_resp(self, user_changed=False):
        """Actualiza el campo historial_resp del Activo Fijo
        :parameter user_changed boolean si esta en True (Usuario cambiado) manda un correo al user_id del Activo"""
        for activo in self:
            valores = {
                'department_id': activo.department_id.id,
                'user_id': activo.user_id.id,
                'estado_responsable': 'EP',
                'hist_resp_id': activo.id,
            }
            if user_changed:
                # Si se modificó el responsable:
                self.env['grp.historial_responsable'].create(valores)
                if activo.state == 'open' and activo.estado_responsable == 'EP':
                    if activo.user_id:
                        body = "Tiene un activo asignado para aceptar."
                        self.message_post(type="notification",
                                          subtype='mt_comment', body=body,
                                          partner_ids=[
                                              activo.user_id.partner_id.id])
            else:
                # Si se modificó el departamento
                valores.update({'estado_responsable': 'AC'})
                self.env['grp.historial_responsable'].create(valores)

    @api.model
    def create(self, vals):
        asset = super(AccountAssetAsset, self).create(vals)
        if self._context.get('asset_create_move', True) and vals.get('ubicacion_fisica', False):
            asset.update_inventory()
        if vals.get('user_id', False) or vals.get('department_id', False):
            asset.update_historial_resp(user_changed=vals.get('user_id', False))
        return asset

    @api.multi
    def write(self, vals):
        update_inventory = self._context.get('asset_create_move', True) and 'ubicacion_fisica' in vals
        if update_inventory:
            ubic_f_dict = {}
            for row in self:
                ubic_f_dict[row.id] = row.ubicacion_fisica or False
        result = super(AccountAssetAsset, self).write(vals)
        if update_inventory:
            for row in self:
                row.update_inventory(ubic_f_dict[row.id])
        return result

    @api.multi
    def update_inventory(self, ubicacion_fisica_ant=False):
        StockMove = self.env['stock.move'].sudo()
        StockPicking = self.env['stock.picking'].sudo()
        StockLocation = self.env['stock.location'].sudo()
        for asset in self.filtered(lambda x: x.product_id and x.product_id.type in ('product','consu') and not x.product_id.no_inventory):
            restrict_lot_id = False
            if self._context.get('restrict_lot_ids', False):
                restrict_lot_id = self._context.get('restrict_lot_ids').get(asset.id, False)

            vals = {'product_id': asset.product_id.id,
                    'price_unit': asset.value_residual,
                    'restrict_lot_id': restrict_lot_id}
            onchange_prod = StockMove.onchange_product_id(prod_id=asset.product_id.id)
            vals.update(onchange_prod.get('value', {}))
            vals['product_uom_qty'] = 1.0
            onchange_qty = StockMove.onchange_quantity(vals.get('product_id'), vals.get('product_uom_qty', False), vals.get('product_uom', False), vals.get('product_uos', False))
            vals.update(onchange_qty.get('value', {}))

            location_src = False
            location_dest = False
            if (not ubicacion_fisica_ant or not ubicacion_fisica_ant.stock_location_id) \
               and asset.ubicacion_fisica.stock_location_id:
                location_dest = asset.ubicacion_fisica.stock_location_id
                warehouse_id = StockLocation.get_warehouse(location_dest)
                stock_picking_type = self.env['stock.picking.type'].search([('warehouse_id','=',warehouse_id),('code','=','incoming')], limit=1)
                if stock_picking_type and stock_picking_type.default_location_src_id:
                    location_src = stock_picking_type.default_location_src_id
                else:
                    warehouse = self.env['stock.warehouse'].browse(warehouse_id)
                    location_src = StockLocation.search([('id','child_of',[warehouse.view_location_id.id]),('usage','=','supplier')], limit=1)
            if ubicacion_fisica_ant and ubicacion_fisica_ant.stock_location_id and \
               (not asset.ubicacion_fisica or not asset.ubicacion_fisica.stock_location_id):
                location_src = ubicacion_fisica_ant.stock_location_id
                warehouse_id = StockLocation.get_warehouse(location_src)
                stock_picking_type = self.env['stock.picking.type'].search([('warehouse_id','=',warehouse_id),('code','=','outgoing')], limit=1)
                if stock_picking_type and stock_picking_type.default_location_dest_id:
                    location_dest = stock_picking_type.default_location_dest_id
                else:
                    warehouse = self.env['stock.warehouse'].browse(warehouse_id)
                    location_dest = StockLocation.search([('id','child_of',[warehouse.view_location_id.id]),('usage','=','customer')], limit=1)
            if ubicacion_fisica_ant and ubicacion_fisica_ant.stock_location_id and \
               asset.ubicacion_fisica.stock_location_id:
                location_src = ubicacion_fisica_ant.stock_location_id
                location_dest = asset.ubicacion_fisica.stock_location_id
                warehouse_id = StockLocation.get_warehouse(location_dest)
                stock_picking_type = self.env['stock.picking.type'].search([('warehouse_id','=',warehouse_id),('code','=','internal')], limit=1)

            if location_src and location_dest:
                vals.update({
                    'picking_type_id': stock_picking_type.id,
                    'location_id': location_src.id,
                    'location_dest_id': location_dest.id,
                })
                picking_vals = {
                    'picking_type_id': stock_picking_type.id,
                    'location_id': location_src.id,
                    'location_dest_id': location_dest.id,
                    'origin': u'AF %s' % (asset.name),
                    'move_lines': [(0, 0, vals)],
                }
                # Si viene doc_origin por context, se carga en picking_vals
                if self._context.get('doc_origin', False):
                    picking_vals.update({'doc_origin': self._context['doc_origin']})
                picking = StockPicking.create(picking_vals)
                picking.action_confirm()
                picking.action_assign()
                picking.action_done()

        return True

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('numero_activo', operator, name)] + args, limit=limit)
        return recs.name_get()


class AccountAssetAssetPolizaSeguro(models.Model):
    _name = 'account.asset.asset.poliza.seguro'

    asset_id = fields.Many2one(
        comodel_name='account.asset.asset',
        string='Activo Fijo'
    )

    nro_poliza = fields.Char(
        size=40,
        string=u'Nro. póliza',
        required=True
    )

    fecha_vencimiento = fields.Date(
        string=u'Fecha de vencimiento',
        required=True
    )

    descripcion = fields.Text(string=u'Descripción')

    @api.one
    @api.constrains('descripcion')
    def _check_descripcion(self):
        if self.descripcion and len(self.descripcion) > 500:
            raise exceptions.ValidationError(u'Se superó el máximo permitido de caracteres para la descripción de la póliza de seguro (500)')

class GrpComprasSolicitudRecursosLineSrAf(models.Model):
    _inherit = 'grp.compras.solicitud.recursos.line.sr.af'

    ubicacion_fisica = fields.Many2one('grp.ubicacion.fisica', string=u'Ubicación física')
