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

import time
import xlwt
from datetime import datetime
from openerp.report import report_sxw
from openerp.addons.report_xls.report_xls import report_xls
from .grp_ejecucion_presupuestal_compras import grp_ejecucion_presupuestal_compras
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)
# TODO: K SPRING 16 GAP 379_380
class grp_ejecucion_presupuestal_compras_xls(report_xls):
    column_sizes = [35, 17, 30, 17, 17, 17, 17]

    def __init__(self, name, table, rml=False, parser=False, header=True,
                 store=False):
        super(grp_ejecucion_presupuestal_compras_xls, self).__init__(
            name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles
        # header

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        pedido_estados = dict(self.pool.get('grp.pedido.compra')._fields['state'].selection)
        p_names = []
        pedidos_compra = _p['get_pedido_compra'](data['form'])
        if not pedidos_compra:
            ws = wb.add_sheet("Hoja1")
        for pedido in pedidos_compra:
            report_name = "DAC Pedido" + '-' + str(pedido.name) + '%s'%(pedido.name in p_names and '(%s)'%(p_names.count(pedido.name)+1) or '')
            p_names.append(pedido.name)
            ws = wb.add_sheet(report_name[:31])
            ws.panes_frozen = True
            ws.remove_splits = True
            ws.portrait = 1  # Landscape
            ws.fit_width_to_pages = 1
            row_pos = 1

            # set print header/footer
            ws.header_str = self.xls_headers['standard']
            ws.footer_str = self.xls_footers['standard']

            # Title
            cell_style = xlwt.easyxf(_xs['xls_title']+_xs['center']+_xs['underline'])
            c_specs = [
                ('report_name', 6, 0, 'text', _('EJECUCIÓN DE PRESUPUESTAL/DOCUMENTOS ASOCIADOS DE COMPRAS')),
            ]

            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cell_style, set_column_size=False)

            cell_style_right = xlwt.easyxf(_xs['bold'] + _xs['right'])
            c_specs = [
                ('espacio', 1, 35, 'text', None),
                ('espacio_1', 1, 17, 'text', None),
                ('espacio_2', 1, 30, 'text', None),
                ('espacio_3', 1, 17, 'text', None),
                ('espacio_4', 1, 17, 'text', None),
                ('fecha', 1, 17, 'text', 'Fecha del reporte'),
                ('report_fecha', 1, 17, 'text', _p['fecha_reporte']),
            ]

            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cell_style_right, set_column_size=True)

            row_pos += 1


            # ------HEADER------#
            cabezal_cell_format = _xs['bold'] + _xs['borders_all']
            cell_format = _xs['borders_all']
            cell_style = xlwt.easyxf(cell_format)
            cell_style_left = xlwt.easyxf(cell_format + _xs['left'])
            cabezal_cell_style_lef = xlwt.easyxf(cabezal_cell_format + _xs['left'])
            header_string = [u'Número procedimiento de compras', 'Concepto de la compra', 'Fecha',
                             'Estado Pedido de Compras', 'Monto estimado']
            header_str = ['name', 'description', 'date_start', 'state', 'total_estimado_cpy']
            header_data =[pedido.name, pedido.description and pedido.description or '',
                          pedido.date_start, pedido_estados.get(pedido.state, ''), pedido.total_estimado_cpy]
            i= 0
            for value in header_data:
                c_specs = [
                    (header_str[i], 1, 35, 'text', header_string[i]),
                    header_str[i] != 'total_estimado_cpy' and (header_str[i] + '_value', 1, 0, 'text', value) or
                    (header_str[i] + '_value', 1, 17, 'number', value),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cabezal_cell_style_lef, set_column_size=True)
                i += 1

            row_pos += 1
            row_pos += 1
            tipo = _p['get_tipo'](data['form'])
            if tipo in ('doc_asociados', 'ambos'):
                cell_style_aut = xlwt.easyxf(_xs['bold'] + _xs['center'] + _xs['underline'])
                c_specs = [('fecha', 2, 0, 'text', 'AUTORIZACIONES PARA GASTAR'),]

                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style_aut, set_column_size=False)

                c_specs = [
                    ('numer', 1, self.column_sizes[0], 'text', _('Nro. APG')),
                    ('fecha', 1, self.column_sizes[1], 'text', _('Fecha APG')),
                    ('monto', 1, self.column_sizes[2], 'text', _('Monto a afectar (pesos)')),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                for apg in pedido.apg_ids.sorted(key=lambda a: a.fecha):
                    c_specs = [
                        ('numer', 1, self.column_sizes[0], 'text', apg.name),
                        ('fecha', 1, self.column_sizes[1], 'text', apg.fecha),
                        ('monto', 1, self.column_sizes[2], 'number', apg.moneda.name == 'UYU' and apg.monto_divisa
                                                                    or apg.monto_fnc),
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_left)
                row_pos += 1
                row_pos += 1

            if tipo in ('imp_asociados', 'ambos'):

                afectaciones = _p['get_afectaciones'](data['form'])[pedido.name]
                cell_style_aut = xlwt.easyxf(_xs['bold'] + _xs['left'] + _xs['underline'])
                c_specs = [('fecha', 1, 35, 'text', 'AFECTACIONES'), ]

                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style_aut, set_column_size=True)

                for afectacion in afectaciones:
                    cell_style_aut = xlwt.easyxf(_xs['bold'] + _xs['left'] + _xs['underline'])
                    c_specs = [('fecha', 1, 0, 'text', 'Nro. Afectación: ' + str(afectacion['nro_afectacion_siif']))]

                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_aut, set_column_size=False)

                    c_specs = [
                        ('anno', 1, self.column_sizes[0], 'text', _(u'Año Fiscal')),
                        ('fecha', 1, self.column_sizes[1], 'text', _('Fecha')),
                        ('llave', 1, self.column_sizes[2], 'text', _('Llave Presupuestal')),
                        ('monto', 1, self.column_sizes[3], 'text', _('Monto afectado')),
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                    for modif in afectacion['modif_vals']:
                        c_specs = [
                            ('anno', 1, self.column_sizes[0], 'text', modif['fiscalyear_siif_id']),
                            ('fecha', 1, self.column_sizes[1], 'text', modif['fecha']),
                            ('llave', 1, self.column_sizes[2], 'text', modif['llave']),
                            ('monto', 1, self.column_sizes[3], 'number', modif['importe']),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cell_style_left)

                    row_pos += 1
                    c_specs = [
                        ('anno', 1, self.column_sizes[0], 'text', ''),
                        ('fecha', 1, self.column_sizes[1], 'text',''),
                        ('llave', 1, self.column_sizes[2], 'text', _(u'Monto afectación:')),
                        ('monto', 1, self.column_sizes[3], 'number',afectacion['monto_efectacion']),
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                    for key,value in afectacion['monto_afectado_fiscalyear'].items():
                        row_pos += 1
                        c_specs = [
                            ('anno', 1, self.column_sizes[0], 'text', ''),
                            ('fecha', 1, self.column_sizes[1], 'text', ''),
                            ('llave', 1, self.column_sizes[2], 'text', _(u'Monto Total Afectado ') + key + ':'),
                            ('monto', 1, self.column_sizes[3], 'number', value),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                row_pos += 1
                row_pos += 1

            adjudicaciones = _p['get_adjudicaciones'](data['form'])[pedido.name]
            if adjudicaciones:
                if tipo in ('doc_asociados', 'ambos'):
                    cell_style_aut = xlwt.easyxf(_xs['bold'] + _xs['left'] + _xs['underline'])
                    c_specs = [('fecha', 1, 35, 'text', 'ADJUDICACIONES'), ]

                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_aut, set_column_size=True)

                for proveedor in adjudicaciones:
                    # for proveedor in adjudicacion['proveedores']:
                    if tipo in ('doc_asociados', 'ambos') or (tipo =='imp_asociados' and proveedor.get('compromisos', False)):
                        cell_style_aut = xlwt.easyxf(_xs['bold'] + _xs['left'] + _xs['underline'])
                        c_specs = [('fecha', 1, 0, 'text', 'Proveedor: ' + str(proveedor['name']))]

                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cell_style_aut, set_column_size=False)

                    if tipo in ('doc_asociados', 'ambos'):
                        c_specs = [
                            ('fecha_respuesta', 1, self.column_sizes[0], 'text', _(u'Año Fiscal')),
                            ('currency', 1, self.column_sizes[1], 'text', _('Moneda')),
                            ('subtotal', 1, self.column_sizes[2], 'text', _('Monto adjudicado')),
                            ('state', 1, self.column_sizes[3], 'text', _('Estado Adjudicación')),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                        for line in proveedor['lines']:
                            c_specs = [
                                ('fecha_respuesta', 1, self.column_sizes[0], 'text', line['fecha_respuesta']),
                                ('currency', 1, self.column_sizes[1], 'text', line['currency']),
                                ('subtotal', 1, self.column_sizes[2], 'number', line['subtotal']),
                                ('state', 1, self.column_sizes[3], 'text', line['state']),
                            ]
                            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                            row_pos = self.xls_write_row(
                                ws, row_pos, row_data, row_style=cell_style_left)
                            row_pos += 1

                    if tipo in ('imp_asociados', 'ambos'):
                        if proveedor.get('compromisos', False):
                            row_pos += 1
                            for compromiso in proveedor['compromisos']:
                                cell_style_aut = xlwt.easyxf(_xs['bold'] + _xs['left'] + _xs['underline'])
                                c_specs = [('fecha', 1, 0, 'text', 'Nro. Compromiso: ' + str(compromiso['nro_compromiso']))]

                                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                                row_pos = self.xls_write_row(
                                    ws, row_pos, row_data, row_style=cell_style_aut, set_column_size=False)

                                c_specs = [
                                    ('anno', 1, self.column_sizes[0], 'text', _(u'Año Fiscal')),
                                    ('fecha', 1, self.column_sizes[1], 'text', _('Fecha')),
                                    ('llave', 1, self.column_sizes[2], 'text', _('Llave Presupuestal')),
                                    ('monto', 1, self.column_sizes[3], 'text', _('Monto afectado')),
                                ]
                                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                                row_pos = self.xls_write_row(
                                    ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                                for modif in compromiso['modifs']:
                                    c_specs = [
                                        ('anno', 1, self.column_sizes[0], 'text', modif['fiscalyear_id']),
                                        ('fecha', 1, self.column_sizes[1], 'text', modif['fecha']),
                                        ('llave', 1, self.column_sizes[2], 'text', modif['llave']),
                                        ('monto', 1, self.column_sizes[3], 'number', modif['importe']),
                                    ]
                                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                                    row_pos = self.xls_write_row(
                                        ws, row_pos, row_data, row_style=cell_style_left)

                                row_pos += 1
                                c_specs = [
                                    ('anno', 1, self.column_sizes[0], 'text', ''),
                                    ('fecha', 1, self.column_sizes[1], 'text', ''),
                                    ('llave', 1, self.column_sizes[2], 'text', _(u'Monto compromiso:')),
                                    ('monto', 1, self.column_sizes[3], 'number', compromiso['monto_compromiso']),
                                ]
                                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                                row_pos = self.xls_write_row(
                                    ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                row_pos += 1
                row_pos += 1

            if tipo in ('doc_asociados', 'ambos'):
                ordenes = _p['get_ordenes'](data['form'])[pedido.name]
                if ordenes:
                # if adjudicacion.get('orders', False):
                    cell_style_aut = xlwt.easyxf(_xs['bold'] + _xs['left'] + _xs['underline'])
                    c_specs = [('fecha', 1, 35, 'text', u'ÓRDENES DE COMPRA'), ]

                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_aut, set_column_size=True)

                    c_specs = [
                        ('partner_id', 1, self.column_sizes[0], 'text', _('Proveedor')),
                        ('name', 1, self.column_sizes[1], 'text', _(u'Nro. OC')),
                        ('descripcion', 1, self.column_sizes[2], 'text', _(u'Descripción')),
                        ('date_order', 1, self.column_sizes[3], 'text', _('Fecha OC')),
                        ('currency_oc', 1, self.column_sizes[4], 'text', _('Moneda')),
                        ('amount_total', 1, self.column_sizes[5], 'text', _('Monto')),
                        ('state', 1, self.column_sizes[6], 'text', _('Estado OC')),
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                    STATE_SELECTION = {
                        'draft': 'PC en borrador',
                        'sent': 'RFQ Sent',
                        'bid': 'Lícitacion recibida',
                        'confirmed': 'OC Confirmado',
                        'approved': 'Compra confirmada',
                        'except_picking': u'Excepción de envío',
                        'except_invoice': u'Excepción de factura',
                        'done': u'OC Cerrada',
                        'closed': 'Realizado',
                        'cancel': 'Cancelado',
                    }
                    for order in ordenes:
                        c_specs = [
                            ('partner_id', 1, self.column_sizes[0], 'text', order.partner_id.name),
                            ('name', 1, self.column_sizes[1], 'text', order.name),
                            ('descripcion', 1, self.column_sizes[2], 'text', order.descripcion),
                            ('date_order', 1, self.column_sizes[3], 'text', order.date_order),
                            ('currency_oc', 1, self.column_sizes[4], 'text', order.currency_oc.name),
                            ('amount_total', 1, self.column_sizes[5], 'number', order.amount_total),
                            ('state', 1, self.column_sizes[6], 'text', STATE_SELECTION[order.state])
                        ]

                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cell_style_left)
                    row_pos += 1
                    row_pos += 1

            facturas = _p['get_facturas'](data['form'])[pedido.name]
            LISTA_ESTADOS_FACTURA = {
                'draft': 'Borrador',
                'proforma': 'Pro-forma',
                'proforma2': 'Pro-forma',
                'sice': u'Confirmado/a',
                'cancel_sice': u'Anulado SICE',
                'in_approved': u'En Aprobación',
                'approved': u'Aprobado',
                'in_auth': u'En Autorización',
                'authorized': u'Autorizado',
                'open': 'Abierto/a',
                'intervened': u'Intervenido/a',
                'prioritized': u'Priorizado/a',
                'cancel_siif': u'Anulado SIIF',
                'paid': 'Pagado/a',
                'forced': 'Obligado/a',
                'cancel': 'Cancelado/a',
            }
            if facturas['facturas']:
            # if adjudicacion.get('facturas', False):
                if tipo in ('doc_asociados', 'ambos'):
                    cell_style_aut = xlwt.easyxf(_xs['bold'] + _xs['left'] + _xs['underline'])
                    c_specs = [('fecha', 1, 35, 'text', 'FACTURAS'), ]

                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_aut, set_column_size=True)

                for factura in facturas['facturas']:
                    cell_style_aut = xlwt.easyxf(_xs['bold'] + _xs['left'] + _xs['underline'])
                    c_specs = [('fecha', 1, 0, 'text', 'Proveedor: ' + factura['name_proveedor'])]

                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_aut, set_column_size=False)
                    if tipo in ('doc_asociados', 'ambos'):
                        c_specs = [
                            ('date_invoice', 1, self.column_sizes[0], 'text', _('Fecha Factura')),
                            ('siif_descripcion', 1, self.column_sizes[1], 'text', _(u'Descripción SIIF')),
                            ('order_compra_id', 1, self.column_sizes[2], 'text', _(u'Nro. OC')),
                            ('currency_id', 1, self.column_sizes[3], 'text', _('Moneda')),
                            ('amount_total', 1, self.column_sizes[4], 'text', _('Monto')),
                            ('state ', 1, self.column_sizes[5], 'text', _('Estado Factura')),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                        c_specs = [
                            ('date_invoice', 1, self.column_sizes[0], 'text', factura['factura_obj'].date_invoice),
                            ('siif_descripcion', 1, self.column_sizes[1], 'text', factura['factura_obj'].siif_descripcion),
                            ('order_compra_id', 1, self.column_sizes[2], 'text', factura['factura_obj'].orden_compra_id.name),
                            ('currency_id', 1, self.column_sizes[3], 'text', factura['factura_obj'].currency_id.name),
                            ('amount_total', 1, self.column_sizes[4], 'number', factura['factura_obj'].amount_total),
                            ('state ', 1, self.column_sizes[5], 'text', LISTA_ESTADOS_FACTURA[factura['factura_obj'].state]),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cell_style_left)
                        row_pos += 1

                    if tipo in ('imp_asociados', 'ambos'):
                        row_pos += 1

                        cell_style_aut = xlwt.easyxf(_xs['bold'] + _xs['left'] + _xs['underline'])
                        c_specs = [
                            ('fecha', 1, 0, 'text', 'Nro. Obligación: ' + str(factura['obligacion']['nro_afectacion_siif']))]

                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cell_style_aut, set_column_size=False)

                        c_specs = [
                            ('anno', 1, self.column_sizes[0], 'text', _(u'Año Fiscal')),
                            ('fecha', 1, self.column_sizes[1], 'text', _('Fecha')),
                            ('llave', 1, self.column_sizes[2], 'text', _('Llave Presupuestal')),
                            ('monto', 1, self.column_sizes[3], 'text', _('Monto obligado')),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                        for modif in factura['obligacion']['modif_vals']:
                            c_specs = [
                                ('anno', 1, self.column_sizes[0], 'text', modif['fiscalyear_siif_id']),
                                ('fecha', 1, self.column_sizes[1], 'text', modif['fecha']),
                                ('llave', 1, self.column_sizes[2], 'text', modif['llave']),
                                ('monto', 1, self.column_sizes[3], 'number', modif['importe']),
                            ]
                            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                            row_pos = self.xls_write_row(
                                ws, row_pos, row_data, row_style=cell_style_left)

                        row_pos += 1
                        c_specs = [
                            ('anno', 1, self.column_sizes[0], 'text', ''),
                            ('fecha', 1, self.column_sizes[1], 'text', ''),
                            ('llave', 1, self.column_sizes[2], 'text', _(u'Monto obligación::')),
                            ('monto', 1, self.column_sizes[3], 'number', factura['obligacion']['monto_obligacion']),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                if tipo in ('imp_asociados', 'ambos'):
                    for key, value in facturas['monto_obligacion_fiscalyear'].items():
                        row_pos += 1
                        c_specs = [
                            ('anno', 1, self.column_sizes[0], 'text', ''),
                            ('fecha', 1, self.column_sizes[1], 'text', ''),
                            ('llave', 1, self.column_sizes[2], 'text', _(u'Monto Total Obligado ') + key + ':'),
                            ('monto', 1, self.column_sizes[3], 'number', value),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                row_pos += 1
                row_pos += 1


grp_ejecucion_presupuestal_compras_xls('report.grp_factura_siif.grp_ejecucion_presupuestal_compras_xls', 'grp.ejecucion.presupuestal.compras.wizard',
                    parser=grp_ejecucion_presupuestal_compras)
