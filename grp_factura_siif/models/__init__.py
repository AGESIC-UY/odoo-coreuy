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

import res_partner  #TODO quitar esto
import res_company
import res_config
import presupuesto_config
import presupuesto_combinaciones_validas
import grp_catalogos_siif
import grp_llave_presupuestal_siif
import grp_compras_apg
import purchase_order
import grp_afectacion
import grp_compromiso
import grp_cotizaciones
import grp_cotizaciones_v8
import account_invoice
import account_invoice_v8
import account_voucher
import retention_creditors
import account_retention
import account_invoice_summary_ret
import obligacion_anulacion_siif_log
import presupuesto_presupuesto
import presupuesto_linea
import presupuesto_estructura
import grp_diarios_pagos_config
import product_template
import facturas_intervenidas
import facturas_priorizadas
import facturas_pagas
import facturas_pagas_totalmente
import retention_lines_report
import grp_compras_apg_v8
import cesion_embargo
import grp_genera_xml_siif
import invoice_regularizacion_clearing
import grp_afectacion_v8
import grp_pedido_compra_v8
import unidad_ejecutora
import grp_marcar_pendientes_obligaciones_siif_presupuesto
import grp_obligaciones_siif_presupuesto
import grp_obligacion_correccion
import grp_compromiso_v8
