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


# TODO Spring 8 GAP 115:
class GrpEnviarCesionSiifWizard(models.TransientModel):
    _name = 'grp.enviar.cesion.siif.wizard'

    @api.onchange('date')
    def _onchange_date(self):
        if self.date:
            self.period_id = self.env['account.period'].find(self.date)

    @api.model
    def default_get(self, fields):
        res = super(GrpEnviarCesionSiifWizard, self).default_get(fields)
        if self._context.get('active_id', False):
            if self._context.get('active_model', False) == 'account.invoice':
                res['journal_id'] = self.env['account.invoice'].browse(self._context['active_id']).journal_id.id
                res['invoice_id'] = self.env['account.invoice'].browse(self._context['active_id']).id
        return res

    date = fields.Date('Fecha asiento', default=lambda *a: fields.Date.today(), required=True)
    period_id = fields.Many2one('account.period', 'Período', readonly=True)
    journal_id = fields.Many2one('account.journal', 'Diario', readonly=True)
    invoice_id = fields.Many2one('account.invoice', 'Factura')

    @api.multi
    def send_cession(self):
        for rec in self:
            rec.invoice_id._contabilizar_cesiones()
        return True
