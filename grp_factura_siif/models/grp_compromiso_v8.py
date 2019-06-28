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

class grpCompromiso(models.Model):
    _inherit = 'grp.compromiso'

    obligaciones_count = fields.Integer(compute='_obligaciones_count', string="Obligaciones")
    filtro_sir = fields.Char(string=u'Filtro código SIR', compute='_compute_filtro_sir')


    def _obligaciones_count(self):
        for compromiso in self:
            compromiso.obligaciones_count = self.env['account.invoice'].search_count([('compromiso_id', '=', compromiso.id)])

    @api.multi
    def view_obligaciones(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'domain': [('compromiso_id', 'in', self.ids)]
        }

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
