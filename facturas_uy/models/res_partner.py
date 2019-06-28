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

from openerp import models, fields, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def default_cuenta_a_cobrar_me(self):
        cuenta_a_cobrar = self.env.user.company_id.cuenta_a_cobrar_me and self.env.user.company_id.cuenta_a_cobrar_me.id or self.env['res.partner']
        return cuenta_a_cobrar

    @api.model
    def default_cuenta_a_pagar_me(self):
        cuenta_a_pagar = self.env.user.company_id.cuenta_a_pagar_me and self.env.user.company_id.cuenta_a_pagar_me.id or self.env['res.partner']
        return cuenta_a_pagar

    cuenta_a_cobrar_me = fields.Many2one('account.account',
        string=u'Cuenta a cobrar M/E',
        default=default_cuenta_a_cobrar_me
    )

    cuenta_a_pagar_me = fields.Many2one('account.account',
        string=u'Cuenta a pagar M/E',
        default=default_cuenta_a_pagar_me
    )
