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

from openerp import models, fields

class AccountConfigSettings(models.Model):
    _inherit = 'account.config.settings'

    cuenta_a_cobrar_me = fields.Many2one(
        related='company_id.cuenta_a_cobrar_me',
        string=u'Cuenta a cobrar M/E'
    )

    cuenta_a_pagar_me = fields.Many2one(
        related='company_id.cuenta_a_pagar_me',
        string=u'Cuenta a pagar M/E'
    )

    income_rounding_adjust_account_id = fields.Many2one(
        related='company_id.income_rounding_adjust_account_id',
        string=u'Ingresos por Ajuste por redondeo',
        domain="[('type','=','other')]"
    )

    expense_rounding_adjust_account_id = fields.Many2one(
        related='company_id.expense_rounding_adjust_account_id',
        string=u'Pérdida por Ajuste por redondeo',
        domain="[('type','=','other')]"
    )

