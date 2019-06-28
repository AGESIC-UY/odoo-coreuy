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

from openerp import fields, models, api, exceptions, _
import openerp.addons.decimal_precision as dp
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

# TODO: K SPRING 16 GAP 379_380
class GrpEjecucionPresupuestalComprasWizard(models.TransientModel):
    _name = 'grp.ejecucion.presupuestal.compras.wizard'

    fiscalyear_siif_id = fields.Many2one('account.fiscalyear', u'Año fiscal')
    pedido_compra_id = fields.Many2one('grp.pedido.compra', 'Pedido de compra')
    type = fields.Selection([('doc_asociados', u'Con documentos asociados'),
                             ('imp_asociados', u'Con imputaciones asociadas'),
                             ('ambos', 'Ambos')],
                             string="Tipo", required=True, default='ambos')

    # TODO: K SPRING 16 GAP 379_380
    def procesar_datos_xls(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}

        data = self.read(cr, uid, ids)[0]

        datas = {
             'ids': [],
             'model': 'grp.ejecucion.presupuestal.compras.wizard',
             'form': data
            }

        return {'type': 'ir.actions.report.xml',
                    'report_name': 'grp_factura_siif.grp_ejecucion_presupuestal_compras_xls',
                    'datas': datas}




