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

{
    'name': 'Retenciones Uruguay',
    'version': '1.0',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category' : 'Accounting & Finance',
    'images': [],
    'depends': ['account_accountant', 'account_voucher','facturas_uy'],
    'description': """
Cálculo de Retenciones
""",
    'data': ['views/retention_workflow.xml',
             'views/retention_view.xml',
             'views/retention_invoice_view.xml',
             'views/retention_product_view.xml',
             'views/res_partner_view.xml',
             'security/ir.model.access.csv',
    ],
    'installable': True,
    'active': False,
}