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
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class GrpUbicacionFisica(models.Model):
    _name = 'grp.ubicacion.fisica'
    _rec_name = 'nombre_completo'

    @api.depends('ubicacion_fisica','ubicacion_padre','ubicacion_padre.codigo',
                 'ubicacion_padre.ubicacion_padre','ubicacion_padre.ubicacion_padre.codigo', 'codigo')
    def _concatenar(self):
        for rec in self:
            rec.nombre_completo = rec.name_get()[0][1]

    # --------------------------------------------------------------------------------------------
    # Campos relativos a las ubicaciones fisicas
    # --------------------------------------------------------------------------------------------
    nombre_completo = fields.Char(string=u'Nombre completo', compute='_concatenar', store=True)
    ubicacion_fisica = fields.Char(string=u'Ubicación física', size=64)
    ubicacion_padre = fields.Many2one(string=u'Ubicación padre',
                                      comodel_name='grp.ubicacion.fisica')
    # ubicaciones_hijas_ids = fields.One2many(comodel_name="grp.ubicacion.fisica", inverse_name="ubicacion_padre", string="Ubicaciones hijas")
    ubicaciones_hijas_ids = fields.Many2many(comodel_name="grp.ubicacion.fisica",
                                             string=u'Ubicaciones hijas',
                                             relation="ubicaciones_padre_hijos_rel",
                                             column1="padre_id", column2="hijo_id")
    active = fields.Boolean(string=u'Activo', default=True)
    codigo = fields.Char(string=u'Código', size=16)
    is_stock_location = fields.Boolean(string=u'¿Es ubicación de almacén?')
    stock_location_id = fields.Many2one('stock.location', string=u'Ubicación de almacén', domain="[('usage','=','internal')]")

    _sql_constraints = [('unique_loc_id', 'unique(stock_location_id)', u'Ya existe una ubicación física con esta ubicación de almacén.')]

    @api.onchange('is_stock_location')
    def _onchange_is_stock_location(self):
        if not self.is_stock_location:
            self.stock_location_id = False

    @api.multi
    def name_get(self):
        res = []
        for r in self:
            name = r.ubicacion_fisica
            if r.ubicacion_padre:
                if r.codigo:
                    name = r.codigo + ' - ' + r.ubicacion_padre.name_get()[0][1] + ' / ' + name
                else:
                    name = r.ubicacion_padre.name_get()[0][1] + ' / ' + name
            res.append((r.id, name))
        return res

    @api.constrains('ubicaciones_hijas_ids','codigo','ubicacion_fisica','ubicacion_padre')
    def check_codigo(self):
        for record in self:
            if record.ubicaciones_hijas_ids:
                if record.codigo:
                    raise ValidationError(u"La ubicación no es final, no puede tener código")
            else:
                if not record.codigo:
                    raise ValidationError(u"La ubicación es final, debe tener código")

    @api.model
    def create(self, vals):
        rec = super(GrpUbicacionFisica, self).create(vals)
        if vals.get("ubicaciones_hijas_ids"):
            hijos = vals["ubicaciones_hijas_ids"]
            for line in hijos:
                if line[0] == 6:
                    self.browse(line[2]).write({'ubicacion_padre': rec.id})
        return rec

    @api.multi
    def write(self, vals):
        for rec in self:
            if vals.get("ubicaciones_hijas_ids"):
                hijos = vals["ubicaciones_hijas_ids"]
                lista_hijos = []
                for line in hijos:
                    if line[0] == 6:
                        if line[2]:
                            self.browse(line[2]).write({'ubicacion_padre': rec.id})
                            lista_hijos.extend(line[2])
                    elif line[0] == 3:
                        self.browse([line[2]]).write({'ubicacion_padre': False})
                    elif line[0] == 4:
                        self.browse([line[2]]).write({'ubicacion_padre': rec.id})
                for linea in rec.ubicaciones_hijas_ids:
                    if linea.id not in lista_hijos:
                        self.browse([linea.id]).write({'ubicacion_padre': False})
        return super(GrpUbicacionFisica, self).write(vals)

