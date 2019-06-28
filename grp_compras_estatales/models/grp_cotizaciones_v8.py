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
from openerp import api, fields, models, exceptions, _
from lxml import etree
from datetime import date

# TODO: GAP 125 SPRINT 6
LISTA_ESTADOS_COT = [
    ('draft', 'Borrador'),
    ('validado', u'Validado'),
    ('in_approval', u'En aprobación'),
    ('approved', u'Aprobado'),
    ('in_authorization', u'En autorización'),
    ('authorized', u'Autorizado'),
    ('refused', u'Rechazado '),
    ('aprobado_sice', 'Aprobado SICE'),
    ('cancelado', 'Cancelado'),
]


class grpCoreCotizacion(models.Model):
    _inherit = 'grp.cotizaciones'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(grpCoreCotizacion, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                                                             context=context,
                                                             toolbar=toolbar, submenu=submenu)
        user_allow = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_pc_Comprador')
        doc = etree.XML(res['arch'])
        if view_type == 'form':
            if not user_allow:
                for node_form in doc.xpath("//form"):
                    node_form.set("create", 'false')
        if view_type == 'tree' and not user_allow:
            for node_tree in doc.xpath("//tree"):
                node_tree.set("create", 'false')

        res['arch'] = etree.tostring(doc)
        return res

    operating_unit_id = fields.Many2one(comodel_name='operating.unit', string='Unidad ejecutora responsable',
                                        related='pedido_compra_id.operating_unit_id', readonly=True, store=True)
    state = fields.Selection(LISTA_ESTADOS_COT, 'Estado', size=86, readonly=True, default='draft',
                             track_visibility='onchange')
    tipo_compra_cod = fields.Char(string=u"Tipo de Compra", related='tipo_compra.idTipoCompra', readonly=True)
    note = fields.Char(u'Observaciones sobre Cancelación / Modificación', size=80, readonly=True)
    motive = fields.Selection([('cancel', 'Cancelar Adjudicación'),
                               ('change', 'Modificar Adjudicación')], u'Motivo', readonly=True)
    allow_authorized = fields.Boolean('Permitir Autorizar', compute='_compute_authorized')
    allow_edit = fields.Boolean('Permitir Editar', compute='_compute_allow_edit')
    pedido_compra_domain_ids = fields.Many2many('grp.pedido.compra',string='Dominio dinámico para pedido de compra', compute='_compute_pedido_compra_domain_ids')
    attachment_ids = fields.Many2many(compute='get_attachments_docs',
                                      comodel_name='ir.attachment',
                                      string=u'Documentos asociados')
    es_migracion = fields.Boolean(u'Es migración?', related='pedido_compra_id.es_migracion', readonly=True)

    @api.multi
    @api.depends('pedido_compra_id')
    def get_attachments_docs(self):
        pool_po = self.env['purchase.order']
        pool_invoice = self.env['account.invoice']
        pool_voucher = self.env['account.voucher']
        pool_apg = self.env['grp.compras.apg']
        for adj in self:
            domain = False
            solicitudes = []
            srs = []
            for linea in adj.pedido_compra_id.lineas_ids:
                if linea.solicitud_compra_id:
                    solicitudes.append(linea.solicitud_compra_id.id)
                    srs.append(linea.solicitud_compra_id.solicitud_recursos_id.id)
            po_ids = pool_po.suspend_security().search([('pedido_compra_id', '=', adj.pedido_compra_id.id), ('state', 'not in', ['cancel'])])
            inv_ids = pool_invoice.suspend_security().search([('orden_compra_id', 'in', po_ids.ids),
                                                    ('state', 'not in', ['cancel', 'cancel_siif', 'cancel_sice'])])
            apg_ids = pool_apg.suspend_security().search([('pc_id', '=', adj.pedido_compra_id.id), ('state', 'not in', ['anulada'])])
            av_ids = pool_voucher.suspend_security().search([('invoice_id', 'in', inv_ids.ids),('state', 'not in', ['cancel'])])
            domain = ['|','|','|','|','|','|', '|', '&', ('res_id', '=', adj.id), ('res_model', '=', 'grp.cotizaciones'),
                      '&', ('res_id', '=', adj.pedido_compra_id.id), ('res_model', '=', 'grp.pedido.compra'),
                      '&', ('res_id', 'in', solicitudes), ('res_model', '=', 'grp.solicitud.compra'),
                      '&', ('res_id', 'in', srs), ('res_model', '=', 'grp.compras.solicitud.recursos.almacen'),
                      '&', ('res_id', 'in', apg_ids.ids), ('res_model', '=', 'grp.compras.apg'),
                      '&', ('res_id', 'in', po_ids.ids), ('res_model', '=', 'purchase.order'),
                      '&', ('res_id', 'in', inv_ids.ids), ('res_model', '=', 'account.invoice'),
                      '&', ('res_id', 'in', av_ids.ids), ('res_model', '=', 'account.voucher'),
                      ]

            if not domain:
                domain = [('res_id', '=', adj.id), ('res_model', '=', 'grp.cotizaciones')]
            docs = self.env['ir.attachment'].search(domain)
            adj.attachment_ids = docs.ids

    @api.multi
    def cotizaciones_in_approval(self):
        return self.write({'state': 'in_approval'})

    @api.multi
    def cotizaciones_approved(self):
        if self.es_migracion:
            return self.write({'state': 'authorized'})
        else:
            return self.write({'state': 'approved'})

    @api.multi
    def cotizaciones_refused(self):
        return self.write({'state': 'refused'})

    @api.multi
    def cotizaciones_authorized(self):
        return self.write({'state': 'authorized'})


    @api.multi
    def cotizaciones_in_authorization(self):
        web_base_url = self.pool.get('ir.config_parameter').get_param(self._cr, self._uid, 'web.base.url')

        body = u'''La Adjudicación <a href="%(web)s/web#id=%(id_adj)s&view_type=form&model=grp.cotizaciones">%(adjudicacion)s</a> correspondiente al pedido de compra <a href="%(web)s/web#id=%(pedido_id)s&view_type=form&model=grp.pedido.compra">%(pedido_compra)s</a> está lista para ser autorizada.'''\
        % {'web':web_base_url,
           'adjudicacion': self.name,
           'id_adj': self.id,
           'pedido_compra': self.pedido_compra_id.name,
           'pedido_id':self.pedido_compra_id.id,}



        self.sent_alert_mail('Adjudicación para autorizar', self.write_uid.email, body)

        return self.write({'state': 'in_authorization'})


    def sent_alert_mail(self, _subject, _from, _body):
        Mail = self.pool['mail.mail']

        ir_model_data = self.env['ir.model.data']
        _model, group_id = ir_model_data.get_object_reference('grp_seguridad',
                                                              'grp_compras_apg_Ordenador_del_gasto')
        users = self.env['res.users'].search([('groups_id', 'in', group_id),('operating_unit_ids','in',self.operating_unit_id.id)])
        partner_ids = []
        if users:
            partner_ids = [user.partner_id.id for user in users]


        vals = {
            'subject': _subject,
            'body_html': '<pre>%s</pre>' % _body,
            'recipient_ids': [(6, 0, partner_ids)],
            'email_from': _from
        }
        mail_id = self.env['mail.mail'].create(vals).id
        Mail.send(self._cr, self._uid, [mail_id], context=self._context)

    @api.multi
    def compromenter(self):
        return True

    @api.one
    @api.depends('operating_unit_id','state','fecha_respuesta')
    def _compute_authorized(self):
        self.allow_authorized = False
        if self.state == 'in_authorization' and self.operating_unit_id.id in self.env.user.operating_unit_ids.ids:
            if self.env['res.users'].has_group('grp_seguridad.grp_compras_apg_Ordenador_del_gasto_primario'):
                self.allow_authorized = True
            elif self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_4la')\
                    or self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_2la')\
                    or self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_la') \
                    or self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_delegado'):
                tocaf_header = self.env['grp.monto.compras'].search([('anio_vigencia', '=', self.fecha_respuesta[:4])])
                if self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_delegado'):
                    cd = tocaf_header.linea_ids.filtered(lambda x: x.tipo_compra_id.idTipoCompra == 'CD').hasta
                    if cd and self.total_estimado <= cd:
                        self.allow_authorized = True
                else:
                    la = tocaf_header.linea_ids.filtered(lambda x: x.tipo_compra_id.idTipoCompra == 'LA').hasta
                    if la and (self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_4la') and self.total_estimado <= 4 * la)\
                            or (self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_2la') and self.total_estimado <= 2 * la)\
                            or (self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_la') and self.total_estimado <= la):
                        self.allow_authorized = True

    @api.multi
    @api.depends('state')
    def _compute_allow_edit(self):
        for rec in self:
            rec.allow_edit = False
            if self.env['res.users'].has_group('grp_seguridad.grp_compras_pc_Comprador') and rec.state in ['draft',
                                                                                                           'validado']:
                rec.allow_edit = True
            if self.env['res.users'].has_group('grp_seguridad.grp_compras_apg_Jefe_de_compras_2') and rec.state in [
                'in_approval', 'approved']:
                rec.allow_edit = True
            if self.env['res.users'].has_group('grp_seguridad.grp_compras_apg_Ordenador_del_gasto') and rec.state == 'in_authorization':
                rec.allow_edit = True

            if self.env['res.users'].has_group('grp_seguridad.grp_compras_apg_Responsable_SIIF') and rec.state == 'authorized':
                rec.allow_edit = True

    @api.depends('ampliacion','nro_adjudicacion_original_id')
    def _compute_pedido_compra_domain_ids(self):
        for record in self:
            if record.ampliacion and record.nro_adjudicacion_original_id:
                ids = self.env['grp.pedido.compra'].search([('apg_ids', '!=', False), ('ampliacion', '=', True),
                                                            '|',
                                                            ('nro_adj', '=', record.nro_adjudicacion_original_id.id),
                                                            ('nro_adj.nro_adjudicacion_original_id', '=', record.nro_adjudicacion_original_id.id)]).ids
            else:
                ids = self.env['grp.pedido.compra'].search([('apg_ids','!=',False)]).ids
            record.pedido_compra_domain_ids = ids

    @api.constrains('state', 'pedido_compra_id')
    def _check_adjudicacion_estado_pc(self):
        for rec in self:
            if rec.pedido_compra_id:
                adj_obj = self.env['grp.cotizaciones'].search([('id', '<>', rec.id),
                                                              ('state', 'not in', ['cancelado', 'refused']),
                                                              ('pedido_compra_id', '=', rec.pedido_compra_id.id)])
                if len(adj_obj) > 0:
                    raise exceptions.ValidationError(u'Ya existe otra Adjudicación '
                                                     u'sin cancelar para el pedido de compra: %s'
                                                     % rec.pedido_compra_id.name)
        return True

class GrpCoreCotizacionesLineasAceptadas(models.Model):
    _inherit = 'grp.cotizaciones.lineas.aceptadas'

    order_linea_ids = fields.One2many('purchase.order.line', 'cotizaciones_linea_id', string=u'Línea de orden de compra')
    cantidad_pendiente_oc = fields.Float(string=u'Cantidad pendiente OC', compute='_compute_cantidad_pendiente_oc')

    @api.multi
    def _compute_cantidad_pendiente_oc(self):
        for rec in self:
            oc = sum(rec.order_linea_ids.filtered(lambda x: x.order_id.state in ['confirmed','done','closed', 'except_picking', 'except_invoice']).mapped('product_qty'))
            rec.cantidad_pendiente_oc = rec.cantidad - oc

    @api.constrains('pedido_cot_id', 'proveedor_cot_id', 'product_id')
    def _check_proveedor_pc_estado(self):
        for rec in self:
            if rec.pedido_cot_id and rec.pedido_cot_id.pedido_compra_id:
                adj_obj = self.env['grp.cotizaciones'].search([('id', '<>', rec.pedido_cot_id.id),
                                                              ('state', 'not in', ['cancelado', 'refused']),
                                                              ('pedido_compra_id', '=',
                                                               rec.pedido_cot_id.pedido_compra_id.id),
                                                              # ('proveedor_id', '=', rec.proveedor_cot_id.id),
                                                              ])
                if len(adj_obj) > 0:
                    adj_lineas = self.search([('id', '<>', rec.id),
                                             ('product_id', '=', rec.product_id.id),
                                             ('proveedor_cot_id', '=', rec.proveedor_cot_id.id),
                                             ('pedido_cot_id', 'in', adj_obj.ids)])
                    if len(adj_lineas) > 0:
                        raise exceptions.ValidationError(u'Ya existe otra Adjudicación '
                                                     u'sin cancelar para el pedido de compra: %s'
                                                     u' el proveedor: %s y el producto: %s'
                                                     % (rec.pedido_cot_id.pedido_compra_id.name,
                                                        rec.proveedor_cot_id.name, rec.product_id.name))


