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

from openerp import api, fields, models

class unidadEjecutora(models.Model):
    _name = 'unidad.ejecutora'

    codigo = fields.Integer(u"Código", required=True)
    descripcion = fields.Char(u"Descripción")
    name = fields.Char("Nombre", compute='_compute_name', store=True)
    str_codigo = fields.Char(u"Código char", compute='_compute_name', store=True)

    @api.depends('codigo','descripcion')
    def _compute_name(self):
        for rec in self:
            name= str(rec.codigo)
            rec.str_codigo = str(rec.codigo).zfill(3)
            if rec.descripcion:
                name+= ' - ' + rec.descripcion
            rec.name= name
