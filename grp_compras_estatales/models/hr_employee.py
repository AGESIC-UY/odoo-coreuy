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

from openerp import models, api, exceptions
from openerp.tools.translate import _


class hrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.constrains('department_id', 'user_id')
    def _check_ue_empleado_usuario(self):
        # Si el empleado tiene usuario asociado y el usuario tiene UE,
        # Se controla que coincida con la UE del departamento del empleado
        for employee in self:
            if employee.user_id and employee.user_id.default_operating_unit_id and employee.department_id:
                department = employee.department_id
                if department.operating_unit_id and department.operating_unit_id.id != employee.user_id.default_operating_unit_id.id:
                    raise exceptions.ValidationError(_(u'El usuario está mal configurado.'
                                                       u' La UE del departamento del empleado no se corresponde con la UE del usuario.'
                                                       u' Por favor verifique la UE en el catálogo de usuarios y la UE en el catálogo de departamentos.'
                                                       u' Debe modificar la UE del departamento o la UE del usuario para que ambas coincidan.'))
