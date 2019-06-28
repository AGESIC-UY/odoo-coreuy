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
    'name': 'GRP Activo Fijo',
    'version': '1.0',
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'category': 'Accounting & Finance',
    'images': [],
    'depends': ['account_asset', 'hr', 'grp_compras_estatales', 'operating_unit', 'grp_catalogos', 'report'], #TODO: Hay dependencia de factura_sice. VER!!!
    'description': """
GRP Activo Fijo
""",
    'demo': [],
    'test': [],
    'data': [
        'data/grp_catalogos_bienes_uso_data.xml',
        'security/grp_activo_fijo_security.xml',
        'security/ir.model.access.csv',
        'views/grp_catalogos_bienes_uso_view.xml',
        'views/account_asset_category_view.xml',
        'views/grp_atributos_view.xml',
        'wizard/grp_cancelar_baja_activo_view.xml',
        'views/product_category_view.xml',
        'views/grp_account_asset_inventory_view.xml',
        'views/account_invoice_view.xml',
        'wizard/grp_campos_baja_activo_view.xml',
        'views/account_asset_asset_view.xml',
        'report/asset_qr_report.xml',
        'report/reporte_listado_af_view.xml',
        'views/reporte_listado_af_tmpl.xml',
        'views/grp_jerarquizacion_activos.xml',
        'wizard/wizard_asset_compute_view.xml',
        'views/grp_obras_curso_view.xml',
        'wizard/grp_obras_curso_wizard.xml',
        'views/grp_aplicar_costos_extra_view.xml',
        'views/res_company_view.xml',
        'views/motivo_alta_activo.xml',
        'views/grp_ubicacion_fisica_view.xml',
        'views/stock_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
