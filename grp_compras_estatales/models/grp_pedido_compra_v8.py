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
from openerp import api, exceptions, fields, models
from openerp import SUPERUSER_ID
from openerp.osv.orm import setup_modifiers
from lxml import etree
from openerp.tools.translate import _
from datetime import date


LISTA_ESTADOS = [
    ('inicio', 'Borrador'),
    ('confirmado', 'Validado'),
    ('en_aprobacion', u'En aprobación'),
    ('aprobado', 'Aprobado'),
    ('en_aut_ordenador', 'En autorización Ordenador'),
    ('aut_ordenador', 'Autorizado Ordenador'),
    ('rechazado', 'Rechazado'),
    ('sice', 'SICE'),
    ('cancelado_sice', u'Anulada'),
    ('cancelado', 'Cancelado'),

]


class grpPedidoCompra(models.Model):
    _inherit = 'grp.pedido.compra'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(grpPedidoCompra, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                           context=context,
                                                           toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        if view_type == 'form':
            company_inciso = self.env['res.users'].browse(self._uid).company_id.inciso
            inciso_ids = self.env['sicec.inciso'].search([('idInciso', '=', company_inciso)]).ids
            for field in res['fields']:
                node = doc.xpath("//field[@name='" + field + "']")[0]
                if field == 'sicec_uc_id':
                    res['fields'][field]['domain'] = [('id', 'in',
                                                       self.env['sicec.uc'].search(
                                                           [('idInciso', 'in', inciso_ids)]).ids)]
                # TODO: R Restringiendo usuarios PC Comprador a comprador_asignado
                if field == 'comprador_asignado_id':
                    _model, group_id = self.env['ir.model.data'].get_object_reference('grp_seguridad',
                                                                                      'grp_compras_pc_Comprador')
                    res['fields'][field]['domain'] = [('id', 'in', self.env['res.users'].search([('groups_id', 'in', group_id)]).ids)]
                setup_modifiers(node, res['fields'][field])


        res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def name_get(self):
        """
        Concatenando el nro de ampliacion en caso de ser un PC ampliado
        """
        res = []
        for rec in self:
            title = _("%s - %s") % (rec.name,rec.nro_ampliacion) if rec.ampliacion else _("%s") % (rec.name)
            res.append((rec.id, title))
        return res

    sicec_uc_id = fields.Many2one('sicec.uc', string='Unidad de compra')
    state = fields.Selection(LISTA_ESTADOS, 'Estado', size=60)
    show_button = fields.Boolean(compute='_compute_show_button', string='Mostrar botón Rechazar?')
    show_button_authorize = fields.Boolean(compute='_compute_show_button_authorize', string='Mostrar botón Autorizar?')
    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Unidad ejecutora responsable',
        required=True,
        default=lambda self: (self.env['res.users'].operating_unit_default_get(self.env.uid))
    )
    attachment_ids = fields.Many2many(compute='get_attachments_docs',
                                      comodel_name='ir.attachment',
                                      string=u'Documentos asociados')
    es_migracion = fields.Boolean(u'¿Es migración de años anteriores?', default=False, copy=False)
    nro_de_procedimiento = fields.Integer(u'Nro. de procedimiento', copy=False)
    anio_de_compra = fields.Integer(u'Año de compra', copy=False)
    anio_fiscal = fields.Integer(u'Año fiscal', copy=False)
    nro_de_ampliacion = fields.Integer(u'Nro. de ampliacion', copy=False)

    show_error_message = fields.Boolean(u'Mostrar mensaje de error', compute='_compute_show_error_message')
    inciso_proc_compra = fields.Char(u'Inciso procedimiento compra')
    unidad_ejec_proc_compra = fields.Char(u'Unidad ejecutora procedimiento compra')
    idTipoCompra = fields.Char(related='tipo_compra.idTipoCompra', size=2, string="Tipo de Compra", readonly=True)

    @api.one
    @api.depends('es_migracion','state','apg_ids')
    def _compute_show_error_message(self):
        self.show_error_message = self.es_migracion and self.state == 'sice' and not self.apg_ids

    @api.multi
    @api.depends('lineas_ids')
    def get_attachments_docs(self):
        pool_po = self.env['purchase.order']
        pool_apg = self.env['grp.compras.apg']
        pool_invoice = self.env['account.invoice']
        pool_voucher = self.env['account.voucher']
        pool_adj = self.env['grp.cotizaciones']
        for pc in self:
            domain = False
            solicitudes = []
            srs = []
            for linea in pc.lineas_ids:
                if linea.solicitud_compra_id:
                    solicitudes.append(linea.solicitud_compra_id.id)
                    srs.append(linea.solicitud_compra_id.solicitud_recursos_id.id)
            po_ids = pool_po.suspend_security().search([('pedido_compra_id', '=', pc.id), ('state', 'not in', ['cancel'])])
            apg_ids = pool_apg.suspend_security().search([('pc_id', '=', pc.id), ('state', 'not in', ['anulada'])])
            inv_ids = pool_invoice.suspend_security().search([('orden_compra_id', 'in', po_ids.ids),
                                                    ('state', 'not in', ['cancel', 'cancel_siif', 'cancel_sice'])])
            av_ids = pool_voucher.suspend_security().search([('invoice_id', 'in', inv_ids.ids),('state', 'not in', ['cancel'])])
            adj_ids = pool_adj.suspend_security().search([('pedido_compra_id', '=', pc.id), ('state', 'not in', ['cancelado'])])
            domain = ['|','|','|','|','|','|', '|', '&', ('res_id', '=', pc.id), ('res_model', '=', 'grp.pedido.compra'),
                      '&', ('res_id', 'in', solicitudes), ('res_model', '=', 'grp.solicitud.compra'),
                      '&', ('res_id', 'in', srs), ('res_model', '=', 'grp.compras.solicitud.recursos.almacen'),
                      '&', ('res_id', 'in', po_ids.ids), ('res_model', '=', 'purchase.order'),
                      '&', ('res_id', 'in', apg_ids.ids), ('res_model', '=', 'grp.compras.apg'),
                      '&', ('res_id', 'in', inv_ids.ids), ('res_model', '=', 'account.invoice'),
                      '&', ('res_id', 'in', av_ids.ids), ('res_model', '=', 'account.voucher'),
                      '&', ('res_id', 'in', adj_ids.ids), ('res_model', '=', 'grp.cotizaciones'),
                      ]

            if not domain:
                domain = [('res_id', '=', pc.id), ('res_model', '=', 'grp.pedido.compra')]
            docs = self.env['ir.attachment'].search(domain)
            pc.attachment_ids = docs.ids

    # TODO: R
    comprador_asignado_id = fields.Many2one('res.users', string='Comprador asignado')

    # TODO: GAP 461 SPRINT 6
    note = fields.Char(string='Observaciones sobre Cancelación / Modificación', size=80, readonly=True)
    motive = fields.Selection([('cancel', 'Cancelar Compra'), ('change', 'Modificar Compra')], string='Motivo', readonly=True)

    apg_afectada = fields.Boolean(string=u'APG Afectada')
    renovacion = fields.Boolean(string=u"Renovación", default=False)

    @api.multi
    def _compute_show_button(self):
        for rec in self:
            rec.show_button = (rec.state == 'en_aprobacion' and self.env['res.users'].has_group('grp_seguridad.grp_compras_apg_Jefe_de_compras_2')) \
                              or (rec.state == 'en_aut_ordenador' and self.env['res.users'].has_group(
                'grp_seguridad.grp_compras_apg_Ordenador_del_gasto'))

    @api.one
    @api.depends('operating_unit_id')
    def _compute_show_button_authorize(self):
        self.show_button_authorize = False
        if self.operating_unit_id.id in self.env.user.operating_unit_ids.ids:
            if self.env['res.users'].has_group('grp_seguridad.grp_compras_apg_Ordenador_del_gasto_primario'):
                self.show_button_authorize = True
            elif self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_4la')\
                    or self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_2la')\
                    or self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_la') \
                    or self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_delegado'):
                tocaf_header = self.env['grp.monto.compras'].search([('anio_vigencia', '=', self.date_start[:4])])
                if self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_delegado'):
                    cd = tocaf_header.linea_ids.filtered(lambda x: x.tipo_compra_id.idTipoCompra == 'CD').hasta
                    if cd and self.total_estimado_cpy <= cd:
                        self.show_button_authorize = True
                else:
                    la = tocaf_header.linea_ids.filtered(lambda x: x.tipo_compra_id.idTipoCompra == 'LA').hasta
                    if la and (self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_4la') and self.total_estimado_cpy <= 4 * la)\
                            or (self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_2la') and self.total_estimado_cpy <= 2 * la)\
                            or (self.env['res.users'].has_group('grp_seguridad.grp_compras_ordenador_secundario_la') and self.total_estimado_cpy <= la):
                        self.show_button_authorize = True


    @api.multi
    def act_enviar_aprobar(self):
        self.write({'state': 'en_aprobacion'})
        return True

    @api.multi
    def act_aprobar(self):
        for record in self:
            record.check_aprobar()
        self.write({'state': 'aprobado'})
        return True

    @api.one
    def check_aprobar(self):
        if self.motive == 'change':
            apg_anuladas_siif = self.apg_ids.filtered(lambda x: x.state in ['desafectado','anulada'])
            apg_no_cumplen = self.apg_ids.filtered(lambda x: x.state not in ['desafectado', 'afectado', 'anulada'])
            if len(self.apg_ids) and (not len(apg_anuladas_siif) or len(apg_no_cumplen)):
                raise exceptions.Warning(_(u'El pedido de compra debe tener al menos una APG en estado Anulada o Anulada en SIIF y el resto en estado Afectada'))

    @api.multi
    def act_enviar_autorizar(self):
        for rec in self:
            if rec.tipo_licitacion and not rec.sice_id_compra:
                raise exceptions.Warning(_(u'El pedido de compra es una licitación. Debe enviarlo a SICE.'))
            if rec.ampliacion and not rec.sice_id_compra:
                raise exceptions.Warning(_(u'El pedido de compra es una ampliación. Debe enviarlo a SICE.'))
            rec.check_apg()
            rec.write({'state': 'en_aut_ordenador'})

            Mail = self.pool['mail.mail']
            ir_model_data = self.env['ir.model.data']
            _model, group_id = ir_model_data.get_object_reference('grp_seguridad',
                                                                  'grp_compras_apg_Ordenador_del_gasto')
            users = self.env['res.users'].search([('groups_id', 'in', group_id),('operating_unit_ids','in',rec.operating_unit_id.id)])
            web_base_url = self.pool.get('ir.config_parameter').get_param(self._cr, self._uid, 'web.base.url')

            partner_ids = []
            if users:
                partner_ids = [user.partner_id.id for user in users]

            body = u'''El pedido de compra Nro. <a href="%(web)s/web#id=%(id)s&view_type=form&model=grp.pedido.compra">%(name)s</a> está listo para ser autorizado'''\
                   % {'web':web_base_url,
                      'id': rec.id,
                      'name': rec.name}

            vals = {'state': 'outgoing',
                    'subject': 'Pedido de compra para Autorizar',
                    'body_html': '<pre>%s</pre>' % body,
                    'recipient_ids': [(6, 0, partner_ids)],
                    'email_from': rec.write_uid.email
                    }
            mail_id = self.env['mail.mail'].create(vals).id
            Mail.send(self._cr, self._uid, [mail_id], context=self._context)
        return True

    @api.one
    def check_apg(self):
        #Control APG afectada al enviar a autorizar PC
        apg_afectadas = self.apg_ids.filtered(lambda x: x.state == 'afectado')
        if not len(apg_afectadas):
            raise exceptions.Warning(_(u'El pedido de compra debe tener asociada una APG en estado Afectada.'))

    @api.multi
    def act_autorizar(self):
        self.write({'state': 'aut_ordenador'})
        return True

    # TODO: GAP 340 SPRINT 6
    @api.multi
    def act_rechazar_confirm(self):
        mod_obj = self.env['ir.model.data']
        res = mod_obj.get_object_reference('grp_compras_estatales', 'pedido_compra_refused_wizard_view')
        res_id = res and res[1] or False
        return {
            'name': 'Rechazar',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(res_id, 'form')],
            'view_id': res_id,
            'res_model': 'grp.pedido.compra.refused.wizard',
            'res_id': False,
            'target': 'new',
        }

    @api.multi
    def act_rechazar(self):
        self.write({'state': 'rechazado'})
        return True

    # TODO: GAP 340 SPRINT 6
    @api.one
    def rechazar_pc(self, motive=None, note=None):
        self.write({'motive': motive, 'note': note})
        for apg in self.apg_ids.filtered(lambda x: x.state == 'afectado'):
            ir_model_data = self.env['ir.model.data']
            _model, group_id = ir_model_data.get_object_reference('grp_seguridad', 'grp_compras_apg_Responsable_SIIF')
            users = self.env['res.users'].search([('groups_id', 'in', group_id),('operating_unit_ids','in',apg.operating_unit_id.id)])
            partner_ids = []
            if users:
                partner_ids = [user.partner_id.id for user in users]
            body = u"El Ordenador  del gasto rechazó la compra %s que ya fue afectada. "\
                    u"Revise la APG %s, afectación número %s y anule " \
                    u"dicha afectación"% (self.name, apg.name, apg.nro_afectacion_siif)
            self.message_post(partner_ids=partner_ids,
                              body=body,
                              subtype='mail.mt_comment')
        self.signal_workflow('button_wkf_rechazar')
        return True

    # Se filtran los AF de su operating_unit para los usuarios que tienen el grupo Restringir PC por UE
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.user.has_group('grp_seguridad.grp_compras_SC_UE'):
            if ['operating_unit_id', '=', self.env.user.default_operating_unit_id.id] not in args:
                args.append(['operating_unit_id', '=', self.env.user.default_operating_unit_id.id])
        return super(grpPedidoCompra, self).search(args, offset, limit, order, count=count)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self.env.user.has_group('grp_seguridad.grp_compras_SC_UE'):
            if ['operating_unit_id', '=', self.env.user.default_operating_unit_id.id] not in domain:
                domain.append(['operating_unit_id', '=', self.env.user.default_operating_unit_id.id])
        return super(grpPedidoCompra, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                       orderby=orderby, lazy=lazy)

    @api.constrains('sicec_uc_id','operating_unit_id')
    def _check_unidad_ejecutora(self):
        #Se controla con superuser porque intenta acceder a sicec.ue
        self = self.sudo()
        for record in self:
            if record.sicec_uc_id and record.operating_unit_id:
                ue_operating_unit = int(record.operating_unit_id.unidad_ejecutora)
                ue_uc = record.sicec_uc_id.idUE.idUE
                if ue_operating_unit != ue_uc:
                    raise exceptions.ValidationError(u"El código de la Unidad ejecutora responsable (%s) no coincide con el de la Unidad de compra (%s)." % (ue_operating_unit, ue_uc))

    @api.multi
    def act_enviar_borrador_aprobar(self):
        for rec in self:
            rec.signal_workflow('button_wkf_pedido_compra_aprobar_inicio')
        return True



class grpLineaPedidoCompra(models.Model):
    _inherit = 'grp.linea.pedido.compra'

    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Unidad ejecutora responsable',
        related='solicitud_compra_id.operating_unit_id',
        readonly=True
    )

    @api.multi
    def open_sc(self):
        for linea in self:
            if linea.solicitud_compra_id:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'grp.solicitud.compra',
                    'res_id': linea.solicitud_compra_id.id,
                    'target': 'new',
                    'context': self._context,
                }
