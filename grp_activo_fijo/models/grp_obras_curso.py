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

from openerp import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class GrpObrasCurso(models.Model):
    _name = 'grp.obras.curso'
    _description = 'GRP Obras en Curso'
    _rec_name = 'obra_en_curso'

    obra_en_curso = fields.Char(
        string=u'Obra en curso',
        required=True,
        size=60
    )

    active = fields.Boolean(
        string=u'Activo',
        default=True
    )


class GrpObrasCursoLinea(models.Model):
    _name = 'grp.obras.curso.linea'
    _description = 'GRP Lineas de Obras en Curso'

    descripcion = fields.Text(
        string=u'Descripción',
    )
    producto_id = fields.Many2one(
        comodel_name=u'product.product',
        string=u'Producto'
    )
    factura_id = fields.Many2one(
        comodel_name=u'account.invoice',
        string=u'Factura id'
    )
    factura_ref = fields.Char(
        string=u'Factura'
    )
    obra_en_curso = fields.Many2one(
        comodel_name=u'grp.obras.curso',
        string=u'Obra en curso',ondelete = 'restrict'
    )
    importe = fields.Float(
        string=u'Importe'
    )
    estado_factura = fields.Selection([
        ('draft', 'Borrador'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        ('sice', u'SICE'),
        ('cancel_sice', u'Anulado SICE'),
        ('in_approved', u'En Aprobación'),
        ('approved', u'Aprobado'),
        ('in_auth', u'En Autorización'),
        ('authorized', u'Autorizado'),
        ('open', 'Abierto'),
        ('intervened', u'Intervenida'),
        ('prioritized', u'Priorizada'),
        ('cancel_siif', u'Anulado SIIF'),
        ('paid', 'Pagado'),
        ('forced', u'Obligado'),
        ('cancel', 'Cancelado'),
    ],
        string=u'Estado factura'
    )
    activado = fields.Boolean(
        string=u'Activado'
    )
    no_activar = fields.Boolean(
        string=u'No activar'
    )
    categoria_activo_id = fields.Many2one(
        comodel_name=u'account.asset.category',
        string=u'Categoría de activo'
    )
    account_id = fields.Many2one(
        comodel_name=u'account.account',
        string=u'Cuenta contable'
    )


