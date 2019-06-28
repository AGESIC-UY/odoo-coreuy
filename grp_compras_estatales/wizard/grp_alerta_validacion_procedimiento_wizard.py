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
import logging

_logger = logging.getLogger(__name__)


class GrpAlertaValidacionProcedimientoWizard(models.TransientModel):
    _name = 'grp.alerta.validacion.procedimiento.wizard'
    _description = u"Alerta de Validación de Procedimiento de Compra"

    @api.multi
    def action_continue(self):
        if 'active_id' in self._context:
            pc_id = self._context.get('active_id')
            for record in self:
                pedido = self.env['grp.pedido.compra'].browse(pc_id)
                pedido.signal_workflow('button_pc_inicio_validado')
                pedido.write({'procedimiento_validado': True})
                self.env['grp.pedido.compra'].send_notification(pedido.id)
        return True
