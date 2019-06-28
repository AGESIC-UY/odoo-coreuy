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

class res_company(osv.osv):
    _inherit = 'res.company'

    _columns = {
        'integracion_siif': fields.boolean(u'Integración SIIF'), # campo para integracion SIIF
        'exceptuado_sice': fields.boolean(u'Exceptuado SICE'), # campo para integracion SIIF
        'unverified_context': fields.boolean(u'Deshabilitar validación certificado ssl'),  # campo para integracion SIIF
        'siif_concepto_gasto_lng': fields.many2one("presupuesto.concepto", 'Concepto del Gasto para LNG'),
        'siif_concepto_gasto_aof': fields.many2one("presupuesto.concepto", 'Concepto del Gasto para AOF'),
        'product_id_lng': fields.many2one("product.product", 'Producto para LNG'),
        'product_id_aof': fields.many2one("product.product", 'Producto para AOF'),
        'journal_id_obl_siif': fields.many2one("account.journal", 'Diario para Obligaciones SIIF Alquileres'),
        'journal_id_obl_siif_lic': fields.many2one("account.journal", 'Diario para Obligaciones SIIF Licencias')
    }

    _defaults = {
        'exceptuado_sice': False,
        'integracion_siif': False,
        'unverified_context': False,
    }

res_company()
