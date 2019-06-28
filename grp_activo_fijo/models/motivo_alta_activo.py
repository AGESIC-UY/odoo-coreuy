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

class MotivoAltaActivo(models.Model):
    _name = "motivo.alta.activo"
    _description = u"Motivos de alta"
    _rec_name = 'motivo_alta'

    motivo_alta = fields.Char(string='Motivo de alta', required=True)
    account_id = fields.Many2one(comodel_name='account.account', string=u'Cuenta contable', required=False)
    journal_id = fields.Many2one(comodel_name='account.journal', string=u'Diario', required=False)
    migracion = fields.Boolean(u'Migración', default=False)
