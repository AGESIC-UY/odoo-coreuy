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


class grp_provision_aguinaldo(models.Model):
    _name = 'grp.provision.aguinaldo'

    incoming_account_id = fields.Many2one('account.account', 'Cuenta Sueldo', required=True)
    bonus_account_id = fields.Many2one('account.account', 'Cuenta Aguinaldo', required=True)
    provision_account_id = fields.Many2one('account.account', 'Cuenta Provisión de Aguinaldo', required=True)
    active = fields.Boolean('Activo', default=True)

    _sql_constraints = [('incoming_account_id_uniq', 'unique(incoming_account_id)',
                         u'La cuenta de sueldo no puede ser seleccionada más de una vez.')]
