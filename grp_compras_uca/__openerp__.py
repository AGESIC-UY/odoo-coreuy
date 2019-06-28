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
    "name": "GRP - Compras Estatales UCA",
    "version": "1.0",
    "author": "Quanam",
    "website": "www.quanam.com",
    "category": "GRP",
    "description": "GRP",
    'depends': ["grp_compras_estatales", "grp_factura_sice", "grp_factura_siif"],
    'data': [
        'security/ir.model.access.csv',
        'views/grp_solicitud_recursos_view.xml',
        'views/grp_solicitud_compra_view.xml',
        'views/grp_pedido_compra_view.xml',
        'wizard/grp_cotizaciones_cargar_datos_wizard_view.xml',
        'views/grp_cotizaciones_view.xml',
        'views/purchase_order_view.xml',
        'views/grp_orden_compra_uca_report.xml',
        'views/grp_account_invoice_view.xml',
    ],
    "installable": True,
    "active": False,
}

