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


class GrpCesionEmbargo(models.Model):
    _name = 'grp.cesion.embargo'
    _description = 'Cesion Embargo'

    @api.one
    @api.depends('cesion_partner_id')
    def _get_cesion_beneficiario(self):
        self.id_rupe_cesion_benef = self.cesion_partner_id and self.cesion_partner_id.id_rupe or False

    tipo_ces_emb = fields.Selection([('C', u'Cesión'), ('E', u'Embargo')
                                     ], string=u'Tipo', help=u'Tipo de cesión o embargo según código SIIF')
    cesion_partner_id = fields.Many2one("res.partner", u"Cedido/Embargado")
    cesion_rupe_cta_bnc_id = fields.Many2one('rupe.cuentas.bancarias', u'Cuenta RUPE beneficiario cesión')
    cesion_res_partner_bank_id = fields.Many2one('res.partner.bank', string=u'Cuenta GRP beneficiario cesión')

    monto_cedido_embargado = fields.Integer("Monto cedido/embargado")
    invoice_id = fields.Many2one('account.invoice', string="Factura", readonly=True)
    descrp_cedido_embargado = fields.Char(size=50, string=u"Cedido/Embargado a")
    id_rupe_cesion_benef = fields.Integer(compute='_get_cesion_beneficiario', string='ID RUPE Beneficiario')
    cesion_es_inciso = fields.Boolean(related='cesion_partner_id.es_inciso', string=u"¿Beneficiario SIIF únicamente?", readonly=True)
    cesion_es_inciso_default = fields.Boolean(related='cesion_partner_id.es_inciso_default', string=u"Es el inciso por defecto", readonly=True)
    unidad_ejecutora_id = fields.Many2one('unidad.ejecutora', string=u"Documento Beneficiario SIIF")

    # TODO Spring 8 GAP 115 C
    asentado = fields.Boolean(string='Asentado', compute='_compute_asentado', default=False)
    # entornado = fields.Boolean(string='Entornado', default=False, compute='_compute_asentado', multi="asiento")
    account_move_name = fields.Char(string="Asiento Contable", readonly=True)

    @api.multi
    def onchange_beneficiario_cesion_id(self, beneficiario_cesion_id):
        result = {}
        result.setdefault('value', {})
        result['value'].update({'cesion_rupe_cta_bnc_id': False, 'cesion_res_partner_bank_id': False, 'unidad_ejecutora_id': False})
        if beneficiario_cesion_id:
            partner = self.env['res.partner'].browse(beneficiario_cesion_id)
            result['value'].update({'id_rupe_cesion_benef': partner.id_rupe or ''})
        return result

    # TODO Spring 8 GAP 115 C
    # TODO R Spring 8 GAP 115 CI
    @api.multi
    @api.depends('account_move_name')
    def _compute_asentado(self):
        for rec in self:
            if rec.account_move_name and rec.account_move_name != '/':
                move = self.env['account.move'].search([('name', '=', rec.account_move_name)])
                rec.asentado = move.state == 'posted' and move.reversal_id.id is False
            else:
                rec.asentado = False

    # TODO Spring 8 GAP 115 C: metodo para crear asiento entornado
    @api.multi
    def crear_extorno(self):
        move_obj = self.env['account.move']
        reversed_move_ids = []
        for rec in self:
            move = move_obj.search([('name', '=', rec.account_move_name)])
            if move:
                if rec.invoice_id and rec.invoice_id.payment_ids:
                    for move_line in rec.invoice_id.payment_ids:
                        if move_line.reconcile_partial_id.line_partial_ids:
                            for line_partial in move_line.reconcile_partial_id.line_partial_ids:
                                if line_partial.id in move.mapped('line_id').ids:
                                    raise exceptions.ValidationError(u'No puede extornar un asiento que tiene una conciliación parcial. Primero debe romper la conciliación.')
                period_id = self.env['account.period'].find(fields.Date.today()).id
                reversed_move_ids.extend(move.create_reversals(
                    fields.Date.today(),
                    reversal_period_id=period_id,
                ))

        move_obj.browse(reversed_move_ids).write({'ref': _(u'Extorno de cesión')})
        self.write({'account_move_name': False})

    # TODO Spring 8 GAP 115 C: Codigo para controlar que no se puedan eliminar cesiones asentadas
    @api.multi
    def unlink(self):
        if len(self.filtered('asentado')):
            raise exceptions.ValidationError(u"No se puede eliminar cesiones asentadas!")
        return super(GrpCesionEmbargo, self).unlink()
