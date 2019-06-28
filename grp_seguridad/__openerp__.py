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
    'name': 'GRP Seguridad',
    'version': '1.0',
    "author" : "Quanam",
    "website" : "www.quanam.com",
    'category' : 'Accounting & Finance',
    'images': [],
    'depends': ['account','sale','base','purchase'],
    'description': """
Seguridad GRP
===========================================
Definición de 12 grupos de seguridad y sus respectivos control de acceso:
-------------------------------------------------------------------------
    * GRP - Asientos de Cierre/Apertura
    * GRP - Auxiliar Contable
    * GRP - Configuracion Contabilidad
    * GRP - Mant.Proveedores
    * GRP - Monedas y Cotizaciones
    * GRP - Visualización Contrato Proveedores
    * GRP - Analista Contable
    * GRP - Cierre de Ejercicio
    * GRP - Consulta Asientos
    * GRP - Informes
    * GRP - Consulta proveedores
    * GRP - Periodos Contables
    """,
    'data': [
         'security/grp_seguridad.xml',
         'security/grp_compras_estatales_security.xml',
         'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}