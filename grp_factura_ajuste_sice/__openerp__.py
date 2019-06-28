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
    'name': 'GRP Campos para interfaz SICE Y Financiero/Contable',
    'version': '1.0',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'Accounting & Finance',
    'images': [],
    'depends': ['grp_factura_siif', 'grp_contrato_proveedores'],
    'description': """
Modificar la Pantalla de Factura de Proveedor para incluir los campos para la interfaz con SICE y Financiero/Contable.
Se agrega un mensaje de confirmación al validar la factura.
Se modifica la vista tree de facturas de proveedor estándar para los usuarios financiero/contable.
""",
    'data': [
        'views/grp_factura_ajuste_sice_view.xml',
        'views/grp_factura_obligacion_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
