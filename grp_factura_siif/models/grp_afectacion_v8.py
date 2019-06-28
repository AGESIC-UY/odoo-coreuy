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

from openerp import api, exceptions, fields, models

class grpAfectacion(models.Model):
    _inherit = 'grp.afectacion'

    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Unidad ejecutora responsable',
        required=True,
        default=lambda self: (self.env['res.users'].operating_unit_default_get(self.env.uid))
    )

    compromisos_count = fields.Integer(compute='_compromisos_count', string="Compromisos")
    filtro_sir = fields.Char(string=u'Filtro código SIR', compute='_compute_filtro_sir')

    def _compromisos_count(self):
        for afectacion in self:
            afectacion.compromisos_count = self.env['grp.compromiso'].search_count([('afectacion_id', '=', afectacion.id)])

    @api.multi
    def view_compromisos(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'grp.compromiso',
            'domain': [('afectacion_id', 'in', self.ids)]
        }

    @api.onchange('inciso_siif_id', 'operating_unit_id')
    def onchange_inciso(self):
        if self.inciso_siif_id and self.operating_unit_id and self.operating_unit_id.unidad_ejecutora:
            unidad_ejecutora = self.env['grp.estruc_pres.ue'].search(
                [('inciso_id', '=', self.inciso_siif_id.id), ('ue', '=', self.operating_unit_id.unidad_ejecutora)], limit=1)
            if unidad_ejecutora:
                self.ue_siif_id = unidad_ejecutora.id
            else:
                self.ue_siif_id = False
        else:
            self.ue_siif_id = False

    @api.multi
    @api.depends('inciso_siif_id','ue_siif_id','siif_financiamiento')
    def _compute_filtro_sir(self):
        for rec in self:
            #Si el financiamiento es 11 filtro solo por financiamiento
            if rec.siif_financiamiento and rec.siif_financiamiento.codigo.zfill(2) == '11':
                rec.filtro_sir = '_____' + rec.siif_financiamiento.codigo.zfill(2) + '__________'
            #Si tiene inciso_siif_id, ue_siif_id y financiamiento != 11, filtro por inciso, ue y financiamiento
            elif rec.inciso_siif_id and rec.ue_siif_id and rec.siif_financiamiento:
                rec.filtro_sir = rec.inciso_siif_id.inciso + rec.ue_siif_id.ue + rec.siif_financiamiento.codigo.zfill(2) + '__________'
            # Si no finaciamiento, o el financiamiento es != 11 y no tiene inciso_siif_id o ue_siif_id, no muestra nada
            else:
                rec.filtro_sir = 'xxxxxxxxxxxxxxx'

