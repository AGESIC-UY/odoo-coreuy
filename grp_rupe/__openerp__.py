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
    'name':     u'GRP - RUPE',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'GRP',
    'license':  'AGPL-3',
    'version':  '1.0',
    'description': u"""
Registro Unico de Proveedores del Estado
========================================

* Proveedores
* Cuentas Bancarias
* Datos de comunicación
""",
    "depends" : ['base', 'grp_seguridad'],
    'data': [
        'views/grp_rupe_view.xml',
        'security/ir.model.access.csv',
        'wizard/grp_poblar_staging_rupe_view.xml',
        'wizard/grp_novedades_rupe_view.xml',
        'views/grp_rupe_historico_view.xml',
        'views/grp_rupe_proveedores_view.xml',
        'views/grp_rupe_carga_proveedores_view.xml',

    ],
    'auto_install': False,
    'installable': True,
    'application': True
}
