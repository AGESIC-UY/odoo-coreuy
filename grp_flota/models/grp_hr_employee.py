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

import openerp
from openerp import models, fields, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.multi
    def write(self, vals):
        for rec in self:
            chofer_obj = self.env['grp.fleet.chofer']
            chofer = chofer_obj.search([('employee_id', '=', rec.id)])
            if chofer:
                values = {}
                if 'work_email' in vals:
                    values.update({'email': vals['work_email']})
                if 'work_phone' in vals:
                    values.update({'phone': vals['work_phone']})
                if 'identification_id' in vals:
                    values.update({'ci': vals['identification_id']})
                if values:
                    chofer.write(values)
        return super(HrEmployee, self).write(vals)

