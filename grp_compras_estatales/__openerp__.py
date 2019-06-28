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
    "name": "GRP - Compras Estatales",
    "version": "1.0",
    "author": "Quanam",
    "website": "www.quanam.com",
    "category": "GRP",
    "description": '''GRP
    Cambios en Facturas:
    * Definición de estados y campos para facturas
    * Modificar la pantalla de facturas rectificativas(de Ajuste)
    * Gestión de tipo de cambio en Factura
    * Reporte listado de facturas por día
    * Lista de control de acceso
Modificaciones al workflow de las facturas:
===========================================
* Definición de estados y campos para facturas
* Modificar la pantalla de facturas rectificativas(de Ajuste)
* Nuevo botón para pagos
''',
    'depends': ["account", "account_cancel", "stock", "stock_account", "purchase", "hr", "account_asset", "grp_calculo_tipo_cambio",
                "grp_seguridad", "facturas_uy", "account_auto_fy_sequence", "auth_ldap", "uy_retenciones",
                "operating_unit", "account_operating_unit", "grp_catalogo_articulos_sice", "purchase_analytic_plans", 'account_reversal',
                'base_suspend_security', 'web_m2x_options', 'readonly_fields'],
    'data': [
        'data/sequence_data.xml',
        'security/grp_compras_estatales_planif_security.xml',
        'security/grp_compras_estatales_security.xml',
        'security/ir.model.access.csv',
        'views/account_config_settings_view.xml',
        'views/account_move_line_view.xml',
        'views/grp_compras_estatales_sequence.xml',
        'views/grp_compras_estatales_workflow.xml',
        'views/hr_employee_view.xml',
        'views/product_view.xml',
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
        'views/res_bank_view.xml',
        'views/res_partner_bank_view.xml',
        'views/stock_view.xml',
        'views/templates.xml',
        'views/grp_web_form.xml',
        'views/grp_compras_estatales_view.xml',
        'views/grp_monto_aprobacion_view.xml',
        'views/grp_codigueras_sice_view.xml',
        'views/purchase_order_view.xml',
        'views/grp_solicitud_recursos_view.xml',
        'views/grp_solicitud_compra_view.xml',
        'views/grp_rupe_view.xml',
        'views/stock_quant_view.xml',
        'wizard/grp_pedido_compra_refused_view.xml',
        'wizard/grp_alerta_validacion_procedimiento_wizard.xml',
        'views/grp_pedido_compra_view.xml',
        'views/grp_compras_apg_view.xml',
        'wizard/grp_cotizaciones_refused_view.xml',
        'views/grp_cotizaciones_view.xml',
        'views/account_invoice_view.xml',
        'views/account_invoice_workflow.xml',
        'views/grp_fecha_planificada_view.xml',
        'views/hr_department_view.xml',
        'views/grp_provision_aguinaldo_view.xml',
        'views/operating_unit_view.xml',
        'views/account_voucher_view.xml',
        'workflow/purchase_workflow.xml',
        'wizard/grp_consolidar_pedidos_compra_view.xml',
        'wizard/grp_solicitar_compra_wizard_view.xml',
        'wizard/grp_adj_crear_oc_wizard_view.xml',
        'wizard/grp_poblar_codigueras_sice_view.xml',
        'wizard/account_report_daily_invoices_view.xml',
        'report/grp_stock_report.xml',
        'report/grp_paid_consult.xml',# TODO: SPRING 10 GAP 549 L
        'views/grp_adjudicaciones_autorizado_tablero_view.xml',
        'views/grp_pc_autorizado_tablero_view.xml',
        'views/grp_listado_sr_tablero_view.xml',
        'data/update_analytic_entries_cron_job.xml',
    ],
    "installable": True,
    "active": False,
}

#TODO: Revisar WKF de orden compras
