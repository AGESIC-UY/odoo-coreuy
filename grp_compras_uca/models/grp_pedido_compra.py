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

import logging
import collections

_logger = logging.getLogger(__name__)

from openerp import api, exceptions, fields, models, osv
from openerp.tools.translate import _
from openerp.exceptions import ValidationError
from collections import Counter

# TODO Spring 6 GAP 334
#Todo GAP 443 Spring 6
SUB_TIPO_SOLICITUD = [
    ('normal', 'Normal'),
    ('compra_uca', 'Compra por UCA'),
]

class grp_msp_pedido_compra(models.Model):
    _inherit = 'grp.pedido.compra'

    sub_tipo_solicitud = fields.Selection(SUB_TIPO_SOLICITUD, 'Sub-Tipo Solicitud', size=60)
    idTipoCompra = fields.Char(related='tipo_compra.idTipoCompra', size=2, string="Tipo de Compra", readonly=True)

    compra_uca_ids = fields.One2many('grp.compras.solicitud.uca', 'pedido_id', 'Compras UCA')
    number_uca = fields.Char(u'Nro.Licitación UCA', size=10)

    @api.onchange('lineas_ids')
    def onchange_lineas_id(self):
        if self.lineas_ids and not self.sub_tipo_solicitud:
            flag = False
            for line in self.lineas_ids:
                if line.solicitud_compra_id.sentencia_ordenanza in ('compra_uca') and not flag:
                    self.sub_tipo_solicitud = line.solicitud_compra_id.sentencia_ordenanza
                    flag = True

    # TODO SPRING 7 GAP 465 R
    def _get_uca_dict(self):
        compra_uca = [(5,)]
        nro_licitaction_uca_list = []
        for solicitud_line in self.lineas_ids:
            nro_licitaction_uca_list.append(solicitud_line.solicitud_compra_id.number_uca)
            compra_uca.append(
                (0, 0, {'product_id': solicitud_line.product_id.id,
                        'quantity': solicitud_line.cantidad_comprar_sice,
                        'price': solicitud_line.monto,
                        'number': solicitud_line.solicitud_compra_id.number,
                        'description': solicitud_line.descripcion,
                        'provider_id': solicitud_line.solicitud_compra_id.provider_id.id,
                        'solicitud_compra_id': solicitud_line.solicitud_compra_id.id,
                        'solicitud_linea_id': False,
                        'pedido_linea_id': solicitud_line.id}))
        nro_licitaction_uca_agrup = Counter(nro_licitaction_uca_list).keys()
        return {'compra_uca': compra_uca,
                'nro_licitaction_uca': nro_licitaction_uca_agrup[0] if len(
                    nro_licitaction_uca_agrup) == 1 else False}

    # PCAR se sobreescribe metodo para incluir el campo sub_tipo_solicitud en la creacion de PC desde la SC
    def _prepare_merge_sc(self, cr, uid, ids, context=None):
        pedido_data = {
            'description': 'Nueva solicitud',
            'lineas_ids': []
        }
        con_error = []
        for line in self.pool.get('grp.solicitud.compra').browse(cr, uid, ids, context=context):
            if line.product_id.id:
                prod = self.pool.get('product.product').browse(cr, uid, line.product_id.id, context=context)
                taxes = []
                for tax in prod.product_tmpl_id.supplier_taxes_id:
                    if tax:
                        taxes.append(tax.id)
                pedido_data['lineas_ids'].append((0, 0, self._prepare_merge_line(cr, uid, ids, line, taxes=taxes, context=context)))
            else:
                con_error.append([line.id, line.name])
            # PCAR 18 08 2017 inicio se agrega campo sub tipo solicitud al crear el pc en MSP
            # toma el valor del campo sentencia_ordenanza
            pedido_data['sub_tipo_solicitud'] = line.sentencia_ordenanza
            # PCAR 18 08 2017 fin
        return pedido_data, con_error

    def do_merge_sc(self, cr, uid, ids, context=None):
        sub_tipo_solicitud = ''
        for line in self.pool.get('grp.solicitud.compra').browse(cr, uid, ids, context=context):
            if line.sentencia_ordenanza and sub_tipo_solicitud == '':
                sub_tipo_solicitud = line.sentencia_ordenanza
            elif line.sentencia_ordenanza and sub_tipo_solicitud != line.sentencia_ordenanza:
                raise exceptions.ValidationError(_(u'No puede consolidar Solicitudes de Compras de diferentes sub-tipos.'))
        return super(grp_msp_pedido_compra, self).do_merge_sc(cr, uid, ids, context=None)

    # TODO Spring 6 GAP 203 R
    @api.multi
    def trans_enviar_autorizar(self):
        for rec in self:
            if rec.sub_tipo_solicitud:
                apg_afectadas = rec.apg_ids.filtered(lambda x: x.state == 'afectado')
                if not len(apg_afectadas):
                    return False
        return True

    @api.multi
    def act_pc_confirmado(self):
        # control para cuando dan validar sin guardar y no cargaron el proveedor UCA
        for pedido in self:
            if pedido.sub_tipo_solicitud == 'compra_uca':
                for uca in self.compra_uca_ids:
                    if not uca.provider_id:
                        raise exceptions.Warning(_(u'Debe cargar el proveedor en la pestaña UCA'))
        return super(grp_msp_pedido_compra, self).act_pc_confirmado()

    # TODO Spring 6 GAP 332
    @api.model
    def create(self, vals):
        new_id = super(grp_msp_pedido_compra, self).create(vals)
        if new_id.sub_tipo_solicitud == 'compra_uca':
            uca_dict = new_id._get_uca_dict()
            dict_to_write = {'compra_uca_ids': uca_dict['compra_uca']}
            if uca_dict['nro_licitaction_uca']:
                dict_to_write.update({'number_uca':uca_dict['nro_licitaction_uca']})
            new_id.write(dict_to_write)
        return new_id

    # TODO SPRING 7 GAP 465 R limpiando UCA en caso de no ser compra_uca
    @api.multi
    def write(self, values):
        if values.get("sub_tipo_solicitud") and values['sub_tipo_solicitud'] != 'compra_uca':
            values['compra_uca_ids'] = [(5,)]
        res = super(grp_msp_pedido_compra, self).write(values)
        if values.get('lineas_ids'):
            for rec in self:
                if rec.sub_tipo_solicitud == 'compra_uca':
                    uca_dict = rec._get_uca_dict()
                    dict_to_write = {'compra_uca_ids': uca_dict['compra_uca']}
                    if uca_dict['nro_licitaction_uca']:
                        dict_to_write.update({'number_uca': uca_dict['nro_licitaction_uca']})
                    rec.write(dict_to_write)
        return res
