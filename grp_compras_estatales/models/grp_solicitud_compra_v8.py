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

class grp_solicitud_compra_v8(models.Model):
    _inherit = 'grp.solicitud.compra'
    _name = 'grp.solicitud.compra'


    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        compute='_get_operating_unit',
        string='Unidad ejecutora responsable',
        store=True,
        readonly=True,
    )
    attachment_ids = fields.Many2many(compute='get_attachments_docs',
                                      comodel_name='ir.attachment',
                                      string=u'Documentos asociados')

    @api.multi
    @api.depends('solicitud_recursos_id')
    def get_attachments_docs(self):
        pool_po = self.env['purchase.order']
        pool_invoice = self.env['account.invoice']
        pool_voucher = self.env['account.voucher']
        pool_adj = self.env['grp.cotizaciones']
        pool_apg = self.env['grp.compras.apg']
        pool_sc = self.env['grp.solicitud.compra']
        pool_lpc = self.env['grp.linea.pedido.compra']
        for sc in self:
            domain = False
            lpc_ids = pool_lpc.suspend_security().search([('solicitud_compra_id', '=', sc.id)])
            pc_ids = []
            for line_pc in lpc_ids:
                pc_ids.append(line_pc.pedido_compra_id.id)
            pc_ids = list(set(pc_ids))
            po_ids = pool_po.suspend_security().search([('pedido_compra_id', 'in', pc_ids), ('state', 'not in', ['cancel'])])
            inv_ids = pool_invoice.suspend_security().search([('orden_compra_id', 'in', po_ids.ids),
                                                    ('state', 'not in', ['cancel', 'cancel_siif', 'cancel_sice'])])
            apg_ids = pool_apg.suspend_security().search([('pc_id', 'in', pc_ids), ('state', 'not in', ['anulada'])])
            av_ids = pool_voucher.suspend_security().search([('invoice_id', 'in', inv_ids.ids),('state', 'not in', ['cancel'])])
            adj_ids = pool_adj.suspend_security().search([('pedido_compra_id', 'in', pc_ids), ('state', 'not in', ['cancelado'])])
            domain = ['|','|','|','|','|','|', '|', '&', ('res_id', '=', sc.id), ('res_model', '=', 'grp.solicitud.compra'),
                      '&', ('res_id', 'in', pc_ids), ('res_model', '=', 'grp.pedido.compra'),
                      '&', ('res_id', '=', sc.solicitud_recursos_id.id), ('res_model', '=', 'grp.compras.solicitud.recursos.almacen'),
                      '&', ('res_id', 'in', po_ids.ids), ('res_model', '=', 'purchase.order'),
                      '&', ('res_id', 'in', inv_ids.ids), ('res_model', '=', 'account.invoice'),
                      '&', ('res_id', 'in', av_ids.ids), ('res_model', '=', 'account.voucher'),
                      '&', ('res_id', 'in', adj_ids.ids), ('res_model', '=', 'grp.cotizaciones'),
                      '&', ('res_id', 'in', apg_ids.ids), ('res_model', '=', 'grp.compras.apg'),
                      ]
            docs = self.env['ir.attachment'].search(domain)
            sc.attachment_ids = docs.ids

    @api.multi
    @api.depends('linea_solicitud_recursos_id')
    def _get_operating_unit(self):
        for record in self:
            if record.linea_solicitud_recursos_id and record.linea_solicitud_recursos_id.grp_id:
                solic_rec_almacen = self.env['grp.compras.solicitud.recursos.almacen'].search([('sr_id', '=', record.linea_solicitud_recursos_id.grp_id.id)])
                if solic_rec_almacen:
                    record.operating_unit_id = solic_rec_almacen.operating_unit_id.id
                else:
                    record.operating_unit_id = False
            else:
                record.operating_unit_id = False

    # Se filtran los AF de su operating_unit para los usuarios que tienen el grupo Restringir SC por UE
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.user.has_group('grp_seguridad.grp_compras_SC_UE'):
            if ['operating_unit_id', '=', self.env.user.default_operating_unit_id.id] not in args:
                args.append(['operating_unit_id', '=', self.env.user.default_operating_unit_id.id])
        return super(grp_solicitud_compra_v8, self).search(args, offset, limit, order, count=count)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self.env.user.has_group('grp_seguridad.grp_compras_SC_UE'):
            if ['operating_unit_id', '=', self.env.user.default_operating_unit_id.id] not in domain:
                domain.append(['operating_unit_id', '=', self.env.user.default_operating_unit_id.id])
        return super(grp_solicitud_compra_v8, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                         orderby=orderby, lazy=lazy)

    @api.constrains('fecha_sc', 'pedido_compra_id')
    def check_fecha_sc(self):
        for record in self:
            if record.pedido_compra_id:
                if record.pedido_compra_id.date_start < record.fecha_sc:
                    raise exceptions.ValidationError(u'La fecha de creación de la Solicitud de compra debe ser anterior a'
                                                     u' la fecha de creación del Pedido de compra.')
