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
    'name': 'Contracts Pro',
    'version': '1.0',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'Human Resources',
    'description': 'Contract clauses management, metrics formulas',
    'depends': ['grp_compras_estatales'],
    'images':[
    ],
    'data':[
#                  'security/contracts_pros_pro_security.xml',
#                  'security/ir.model.access.csv',
                  'views/contracts_pro_view.xml',
#                  'data/contracts_pro_data.xml',
                  'report/contracts_pro_report.xml',
                  'report/report_contract_template_basic.xml',
    ],
    'demo': [
    ],
    'test': [],
    'js':[],
    'installable': True,
    'application': True,
    'active': False,
}

