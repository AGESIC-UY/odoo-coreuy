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
from openerp.tools.translate import _
from datetime import datetime
from openerp.exceptions import except_orm, Warning, ValidationError


# ================================================================
#       Autorización para gastar
# ================================================================
# TODO Spring 7 GAP 442

class grp_compras_apg(models.Model):
    _name = 'grp.compras.apg'
    _inherit = ['grp.compras.apg']

    filtro_sir = fields.Char(string=u'Filtro código SIR', compute='_compute_filtro_sir')

    @api.model
    def create(self, values):
        apg = super(grp_compras_apg, self).create(values)
        if apg.fiscalyear_siif_id and apg.fecha:
            fiscalyear = int(apg.fiscalyear_siif_id.name)
            pedidoyear = datetime.strptime(apg.fecha, "%Y-%m-%d").year
            if fiscalyear > pedidoyear:
                apg.act_apg_en_financiero()
        return apg

    @api.multi
    def write(self, values):
        res = super(grp_compras_apg, self).write(values)
        for apg in self:
            if apg.state == 'nuevo' and (values.get('fiscalyear_siif_id',False) or values.get('fecha',False)) and apg.fiscalyear_siif_id and apg.fecha:
                fiscalyear = int(apg.fiscalyear_siif_id.name)
                pedidoyear = datetime.strptime(apg.fecha, "%Y-%m-%d").year
                if fiscalyear > pedidoyear:
                    apg.act_apg_en_financiero()
        return res

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


    # TODO R LLAVES PRESUPUESTALES
    @api.multi
    def action_llpapg_reload(self):
        ODG = self.env['grp.estruc_pres.odg']
        Auxiliar = self.env['grp.estruc_pres.aux']
        for rec in self:
            rec.llpapg_ids.unlink()
            llpapgs = []
            for line in rec.lprapg_ids:
                if not line.product_id.objeto_gasto:
                    raise ValidationError(_(u'El producto %s no tiene objeto del gasto asociado!') % (line.product_id.name_get()[0][1]))
                odg = ODG.search([('ue_id','=',rec.ue_siif_id.id),('odg','=',line.product_id.objeto_gasto.name)], limit=1)
                if not odg:
                    raise exceptions.ValidationError(_(u'No se ha encontrado el objeto del gasto asociado al producto %s para esta combinación de: UE, Inciso, Año fiscal!') % (line.product_id.name_get()[0][1]))
                auxiliar = Auxiliar.search([('odg_id','=',odg.id),('aux','=',line.product_id.objeto_gasto.auxiliar)], limit=1) if odg else False
                if not auxiliar:
                    raise exceptions.ValidationError(_(u'No se ha encontrado el auxiliar asociado al producto %s para este combinación de: ODG, UE, Inciso, Año fiscal!') % (line.product_id.name_get()[0][1]))
                if auxiliar:
                    new_llpapg = True
                    for llpapg in llpapgs:
                        if llpapg[0] == 0 and llpapg[2] and llpapg[2]['odg_id'] == odg.id and llpapg[2]['auxiliar_id'] == auxiliar.id:
                            new_llpapg = False
                            llpapg['importe'] += line.subtotal
                            break
                    if new_llpapg:
                        llpapgs.append((0,0,{'odg_id':odg.id,'auxiliar_id':auxiliar.id,'importe':line.subtotal}))
            rec.write({'llpapg_ids':llpapgs})

    @api.multi
    @api.depends('inciso_siif_id', 'ue_siif_id', 'siif_financiamiento')
    def _compute_filtro_sir(self):
        for rec in self:
            # Si el financiamiento es 11 filtro solo por financiamiento
            if rec.siif_financiamiento and rec.siif_financiamiento.codigo.zfill(2) == '11':
                rec.filtro_sir = '_____' + rec.siif_financiamiento.codigo.zfill(2) + '__________'
            # Si tiene inciso_siif_id, ue_siif_id y financiamiento != 11, filtro por inciso, ue y financiamiento
            elif rec.inciso_siif_id and rec.ue_siif_id and rec.siif_financiamiento:
                rec.filtro_sir = rec.inciso_siif_id.inciso + rec.ue_siif_id.ue + rec.siif_financiamiento.codigo.zfill(
                    2) + '__________'
            # Si no finaciamiento, o el financiamiento es != 11 y no tiene inciso_siif_id o ue_siif_id, no muestra nada
            else:
                rec.filtro_sir = 'xxxxxxxxxxxxxxx'