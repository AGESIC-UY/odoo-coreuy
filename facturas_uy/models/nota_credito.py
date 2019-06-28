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

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp

class notas_credito(osv.osv):
    _name = 'nota.credito'
    _description = 'Nota de credito'
    _columns = {
        # factura_original
        'invoice_id': fields.many2one('account.invoice', string="Factura", readonly=True),
        'nro_nc': fields.char('Nro NC', size=20),
        'fecha_nc': fields.date('Fecha NC'),
        'fecha_vto': fields.date('Fecha Vto'),
        'total_nc': fields.float(string='Total NC', digits_compute=dp.get_precision('Account')),
    }

notas_credito()

