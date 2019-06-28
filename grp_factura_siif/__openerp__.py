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
    'name': 'GRP Adecuaciones SIIF',
    'version': '1.0',
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'category' : 'Accounting & Finance',
    'images': [],
    'depends': ['grp_compras_estatales','uy_retenciones','facturas_uy',
                'grp_factura_sice','grp_rupe','grp_activo_fijo', 'grp_siif',
                'grp_account','grp_cotizaciones','report_xls'], #TODO: VER DEPENDENCIAS
    'description': """
    Generación de "Obligaciones de proveedores".
    Generación de "Facturas 3 en 1".
""",
    'data': [
        'data/sequence_data.xml',
        'data/siif_grupos_subgrupos_data.xml',
        'data/presupuesto.objeto.gasto.csv',
        'wizard/grp_wizard_enviar_cesion_siif_wizard_view.xml',# TODO: SPRING 8 GAP 115 C
        'views/account_invoice_obligacion_view.xml',
        'views/account_supplier_invoice_view.xml',
        'views/invoice_regularizacion_clearing_view.xml',# TODO: SPRING 8 GAP 236.237 M
        # 'views/account_invoice_workflow.xml',# TODO: SPRING 8 GAP 236.237 M
        'views/retention_creditors_view.xml',
        'views/retentions_view.xml',
        'views/presupuesto_config_view.xml',
        'views/siif_menus.xml',
        'views/grp_afectacion_view.xml',
        'views/grp_compromiso_view.xml',
        'views/grp_compras_apg_view.xml',
        'views/purchase_order_view.xml',
        'views/presupuesto_presupuesto_view.xml',
        'views/presupuesto_linea_view.xml',
        'views/presupuesto_estructura_view.xml',
        'views/presupuesto_combinaciones_validas_view.xml',
        'views/grp_diarios_pagos_config_view.xml',
        'views/grp_facturas_consolidadas_view.xml',
        'views/facturas_priorizadas_view.xml',
        'views/facturas_intervenidas_view.xml',
        'views/facturas_pagas_view.xml',
        'views/facturas_pagas_totalmente_view.xml',
        'views/res_company_view.xml',
        'views/account_voucher_view.xml',
        'views/account_invoice_nota_credito_view.xml',
	    'report/grp_consulta_pago_view.xml', # TODO: SPRING 8 GAP 364 K
        'report/grp_agrupar_suministros_facturas_view.xml',# TODO: SPRING 8 GAP 236.237 M
        'wizard/grp_cotizaciones_comprometer_wizard_view.xml',
        'views/grp_cotizaciones_view.xml',
        'views/grp_cotizaciones_compromiso_view.xml',
        'wizard/grp_fondo_rendido_view.xml',
        'wizard/wizard_integracion_view.xml',
        'wizard/wizard_modif_afectacion_siif_view.xml',
        'wizard/wizard_modif_apg_siif_view.xml',
        'wizard/wizard_modif_compromiso_siif_view.xml',
        'wizard/wizard_modif_cot_compromiso_siif_view.xml',
        'wizard/wizard_modif_oc_siif_view.xml',
        'wizard/wizard_modif_obligacion_siif_view.xml',
        'wizard/grp_account_invoice_refund_view.xml',
        'wizard/wizard_modif_regularizacion_siif_view.xml',# TODO: SPRING 8 GAP 236.237 M
        'wizard/grp_ejecucion_presupuestal_compras_wizard_view.xml',# TODO: K SPRING 16 GAP 379_380
        'security/ir.model.access.csv',
        'security/grp_factura_siif_security.xml',
        # 001-Inicio
        'views/product_template_view.xml',
        # 001-Fin
        'views/retention_list_report_view.xml',
        'views/grp_aprobacion_pagos.xml',
        'views/grp_pedido_compra_view.xml',
        'views/unidad_ejecutora_view.xml',
        'views/grp_obligaciones_siif_presupuesto_view.xml',
        'views/grp_obligacion_correccion_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}

#TODO PENDIENTE PASAR COSAS DE res.partner.bank ver en que addon se incorporan
#TODO depende de integracion_SIIF (ese addon solo tienen los metodos)
#TODO dependencia factura SICE ver campos id_item, id_variacion, etc
#TODO: dependencias campos sice id_item, id_variacion

#TODO: meter estos ACL cuando esten los modelos:
# access_pagas_APG_Responsable SIIF,grp.integracion.pagas_APG Responsable SIIF,model_grp_integracion_pagas,grp_seguridad.grp_compras_apg_Responsable_SIIF,1,0,0,0
# access_pagas_totalmente_Responsable SIIF,grp.integracion.pagas_totalmente_Responsable SIIF,model_grp_integracion_pagas_totalmente,grp_seguridad.grp_compras_apg_Responsable_SIIF,1,0,0,0
