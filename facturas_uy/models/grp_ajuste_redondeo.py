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

class GrpAjusteRedondeo(models.Model):
    _name = 'grp.ajuste.redondeo'
    _description = 'Ajuste por Redondeo'
    _rec_name = 'moneda'

    moneda = fields.Many2one('res.currency', string=u'Moneda', required=True)
    ajuste_redondeo = fields.Float(string=u'Ajuste por redondeo', required=True)
    active = fields.Boolean('Activo', default=True)
    company_id = fields.Many2one('res.company', string=u'Compañía', required=True,
                                 default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('currency_uniq', 'unique(moneda,company_id)', u'Moneda debe ser única por compañía.'),
        ('diff_amount_check', 'check(ajuste_redondeo>0)', u'Ajuste por redondeo debe ser mayor que cero.'),
    ]
