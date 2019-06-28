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

from openerp import fields, models, api, exceptions, _
from openerp import tools
from openerp.exceptions import ValidationError
import logging
import openerp.addons.decimal_precision as dp
from lxml import etree

class grp_consulta_pago(models.Model):
    _name = 'grp.consulta.pago'
    _auto = False

    pago_id = fields.Many2one('account.voucher',string='Asiento contable')
    pago_line_id = fields.Many2one('account.voucher.line',string='Linea asiento contable')
    fecha = fields.Date(string='Fecha',related='pago_id.date', store=False)
    numero = fields.Char(string=u'Número', related='pago_id.number', store=False)
    referencia = fields.Char(string='Referencia', related='pago_id.reference', store=False)
    no_factura = fields.Char(string=u'N° factura proveedor', compute='_get_no_factura', store=False)
    partner_id = fields.Many2one('res.partner', 'Empresa', related='pago_id.partner_id', store=False)
    source_journal_id = fields.Many2one('account.journal','Diario', related='pago_id.journal_id', store=False)
    total = fields.Float(string='Total', related='pago_line_id.amount', store=False)

    # TODO: SPRING 8 GAP 364 K
    @api.multi
    @api.depends('pago_line_id')
    def _get_no_factura(self):
        for rec in self:
            factura = self.env['account.invoice'].search([('move_id','!=',False),('move_id','=',rec.pago_line_id.move_line_id.move_id.id)])
            if factura:
                rec.no_factura = factura.number


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_consulta_pago')
        cr.execute("""
            create or replace view grp_consulta_pago as (
                SELECT
                    avl.id as id,
                    av.id as pago_id,
                    avl.id as pago_line_id
                    FROM account_voucher as av
                    left join account_voucher_line avl on (avl.voucher_id = av.id)
                    where av.state = 'posted' and av."type" = 'payment' and avl.amount > 0
                    order by id
            )
        """)
