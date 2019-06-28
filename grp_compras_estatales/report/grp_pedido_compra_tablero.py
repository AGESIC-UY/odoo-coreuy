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
from openerp import models, fields, api, exceptions, _
from openerp import tools


class GrpPedidoCompra(models.Model):
    _name = 'grp.pedido.compra.tablero'
    _auto = False
    _description = u'Pedido de Compra'

    name = fields.Char('Solicitud Recurso')


    sice_id_compra = fields.Integer('Sice ID')
    date_start = fields.Date('Fecha de Solicitud')
    tipo_compra = fields.Many2one('sicec.tipo.compra', string=u'Tipo de Compra')
    sub_tipo_compra = fields.Many2one('sicec.subtipo.compra', string=u'Tipo de Compra')
    description = fields.Char(u'Observaciones')
    operating_unit_id = fields.Many2one('operating.unit', 'Unidad ejecutora')
    state = fields.Selection([("inicio", "Borrador"),
                              ("confirmado", "Validado"),
                              ("en_aprobacion", "En aprobación"),
                              ("aprobado", "Aprobado"),
                              ("en_aut_ordenador", "En autorización Ordenador"),
                              ("aut_ordenador", "Autorizado Ordenador"),
                              ("rechazado", "Rechazado"),
                              ("sice", "SICE"),
                              ("cancelado_sice", "Anulada"),
                              ("cancelado", "Cancelado")], 'Estado')
    user_id = fields.Many2one('res.users', string='Creado por')
    usr_solicitante = fields.Many2one('res.users', string='Solicitado por')
    sicec_uc_id = fields.Many2one('sicec.uc', string='Unidad de compra')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_pedido_compra_tablero')
        cr.execute("""
                CREATE OR replace VIEW grp_pedido_compra_tablero AS (
                   SELECT
	id,
	name,
	sice_id_compra,
	date_start,
	tipo_compra,
	sub_tipo_compra,
	description,
	operating_unit_id,
	state,
	user_id,
	usr_solicitante,
	sicec_uc_id
FROM grp_pedido_compra WHERE id NOT IN
(SELECT DISTINCT pedido_compra_id FROM grp_cotizaciones WHERE pedido_compra_id IS NOT NULL) AND
state IN ('aut_ordenador','sice'))
            """)
