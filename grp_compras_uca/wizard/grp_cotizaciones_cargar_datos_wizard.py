
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


class grpCotizacionesCargarDatosWizard(models.TransientModel):
    _name = 'grp.cotizaciones.cargar.datos.wizard'

    @api.multi
    def merge_orders(self):
        cotizacion_id = self.env['grp.cotizaciones'].browse(self._context.get('active_ids', [])).cargar_datos_pedido()

        return {
            'target': 'current',
            'res_id': cotizacion_id,
            'name': _('Pedidos de Compra'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'grp.cotizaciones',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

