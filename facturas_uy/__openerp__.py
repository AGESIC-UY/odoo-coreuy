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
    "name": "Facturas UY",
    "version": "1.0",
    "author": "Quanam",
    "website": "www.quanam.com",
    "category": "GRP",
    "description":
"""
Ajustes para facturas y pagos:
==============================

Funcionalidades sobre las facturas:
=========================================
* Modificar la pantalla de facturas rectificativas(de Ajuste)
* Gestión de tipo de cambio en Factura


Los ajustes para tipo de cambios incluyen:
==========================================
* Al bajar el tipo de cambio, se debe crear asiento de desajuste
* Utilizar siempre la cuenta de acreedores seleccionada
* Corregir pago cruzado para cuando TC sube
* Corregir creación de líneas en blanco
* Corregir cancelaciones de pagos con diferencias de TC
* Recibir pagos parciales/totales asociados a facturas

""",
    'depends': ['account','account_voucher','account_voucher_operating_unit'], #TODO: currency_rate_enhanced ??? lo tenia factura_rate que esta incluido aca
    'data': ['views/account_bank_statement_view.xml',
             'views/account_voucher_sales_purchase_view.xml',
             'views/account_invoice_view.xml',
             'views/account_invoice_workflow.xml',
             'views/account_voucher_view.xml',
             'views/account_voucher_workflow.xml',
             'wizard/wiz_crear_pago_view.xml',
             # 001-Inicio
             'views/res_config_view.xml',
             'views/res_partner_view.xml',
             # 001-Fin
             'views/grp_ajuste_redondeo_view.xml',
             'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
