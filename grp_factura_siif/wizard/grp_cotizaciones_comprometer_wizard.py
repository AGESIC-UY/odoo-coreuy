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

from openerp import fields, models, api, _
from openerp.exceptions import ValidationError
import logging
import openerp.addons.decimal_precision as dp
from lxml import etree

_logger = logging.getLogger(__name__)


# TODO Spring 6 GAP 126
class grpCotizacionesComprometerWizard(models.TransientModel):
    _name = 'grp.cotizaciones.comprometer.wizard'

    @api.onchange('fiscalyear_id', 'provider_id')
    def _onchange_fiscalyear_provider(self):
        if self.fiscalyear_id and self.provider_id:
            self.estimate_fiscalyear = self.cot_id.estimate_ids.filtered(
                lambda
                    x: x.fiscalyear_id.id == self.fiscalyear_id.id and x.provider_id.id == self.provider_id.id).total_amount
        self.apg_id = False
        cot_obj = self.cot_id
        domain = {
            'apg_id': [('id', 'in', [obj.id for obj in cot_obj.pedido_compra_id.apg_ids.filtered(
                lambda record: record.state in ['afectado', 'en_financiero'])]),
                       ('fiscalyear_siif_id', '=', self.fiscalyear_id.id)]
        }
        return {'domain': domain}

    @api.model
    def default_get(self, fields):
        res = super(grpCotizacionesComprometerWizard, self).default_get(fields)
        if self._context.get('cot_id', False):
            res['cot_id'] = self._context.get('cot_id', False)
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(grpCotizacionesComprometerWizard, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                            context=context,
                                                                            toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        if self._context.has_key('cot_id'):
            cot_id = self._context.get('cot_id')
            grpCoreCotizacion = self.env['grp.cotizaciones'].search([('id', '=', cot_id)])
            for field in res['fields']:
                if field == 'fiscalyear_id':
                    res['fields'][field]['domain'] = [
                        ('id', 'in', [obj.fiscalyear_id.id for obj in grpCoreCotizacion.estimate_ids])]
                if field == 'provider_id':
                    res['fields'][field]['domain'] = [
                        ('id', 'in', [obj.provider_id.id for obj in grpCoreCotizacion.provider_ids])]
            res['arch'] = etree.tostring(doc)
        return res

    cot_id = fields.Many2one('grp.cotizaciones', 'Cotización')
    fiscalyear_id = fields.Many2one('account.fiscalyear', 'Año fiscal', required=True)
    provider_id = fields.Many2one('res.partner', 'Proveedor', required=True)
    apg_id = fields.Many2one('grp.compras.apg', 'APG', required=True)
    estimate_fiscalyear = fields.Float(digits_compute=dp.get_precision('Account'), string='Estimado por año fiscal')
    estimate_fiscalyear_temp = fields.Float(string='Estimado por año fiscal', compute='_compute_estimate_fiscalyear_temp')
    amount_compromise = fields.Float(digits_compute=dp.get_precision('Account'), string='Saldo a comprometer',
                                     compute='_compute_amount_compromise', store=True)

    @api.constrains('amount_compromise')
    def _check_compromise(self):
        if self.amount_compromise <= 0:
            raise ValidationError(_(u'No se puede crear otro compromiso. No queda saldo a comprometer para este año fiscal!'))

    @api.multi
    @api.depends('estimate_fiscalyear')
    def _compute_estimate_fiscalyear_temp(self):
        for rec in self:
            rec.estimate_fiscalyear_temp = rec.estimate_fiscalyear

    @api.multi
    def _get_amount_compromise(self):
        self.ensure_one()
        estimate_fiscalyear = self.cot_id.estimate_ids.filtered(lambda x: x.fiscalyear_id.id == self.fiscalyear_id.id and x.provider_id.id == self.provider_id.id).total_amount
        estimate_fiscalyear = round(estimate_fiscalyear)
        real_compromise = self.env['grp.cotizaciones.compromiso.proveedor'].search(
            [('provider_id', '=', self.provider_id.id),
             ('fiscalyear_id', '=', self.fiscalyear_id.id),
             ('cot_id', '=', self.cot_id.id),
             ('state', '=', 'committed')])
        return estimate_fiscalyear - sum(real_compromise.mapped('total_comprometido'))

    @api.multi
    @api.depends('fiscalyear_id', 'provider_id', 'estimate_fiscalyear')
    def _compute_amount_compromise(self):
        for rec in self:
            if rec.fiscalyear_id and rec.provider_id:
                real_compromise = self.env['grp.cotizaciones.compromiso.proveedor'].search(
                    [('provider_id', '=', rec.provider_id.id),
                     ('fiscalyear_id', '=', rec.fiscalyear_id.id),
                     ('cot_id','=',rec.cot_id.id),
                     ('state', '=', 'committed')])
                _amount_compromise = rec.estimate_fiscalyear - sum(real_compromise.mapped('total_comprometido'))
            else:
                _amount_compromise = 0
            rec.amount_compromise = _amount_compromise


    @api.multi
    def confirm_compromise(self):
        compromise_obj = self.env['grp.cotizaciones.compromiso.proveedor']
        ids_lis = []
        for rec in self:
            llpapg_ids = []
            for llave_presupuestal_id in rec.apg_id.llpapg_ids:
                llpapg_ids.append((0,0,{
                    'odg_id':llave_presupuestal_id.odg_id.id,
                    'auxiliar_id':llave_presupuestal_id.auxiliar_id.id,
                    'fin_id':llave_presupuestal_id.fin_id.id,
                    'programa_id':llave_presupuestal_id.programa_id.id,
                    'proyecto_id':llave_presupuestal_id.proyecto_id.id,
                    'mon_id':llave_presupuestal_id.mon_id.id,
                    'tc_id':llave_presupuestal_id.tc_id.id,
                    'disponible':llave_presupuestal_id.disponible,
                    'importe':llave_presupuestal_id.importe,
                }))

            obj = compromise_obj.create({
                'cot_id': rec.cot_id.id,
                'provider_id': rec.provider_id.id,
                'fiscalyear_id': rec.fiscalyear_id.id,
                'inciso_siif_id': rec.apg_id.inciso_siif_id.id,
                'ue_siif_id': rec.apg_id.ue_siif_id.id,
                'apg_id': rec.apg_id.id,
                'llpapg_ids':llpapg_ids,
                'pc_id': rec.apg_id.pc_id.id,
                'total_number_comp':rec._get_amount_compromise(),
                'siif_descripcion': rec.apg_id.siif_descripcion,
                'name': self.env['ir.sequence'].with_context(fiscalyear_id=rec.fiscalyear_id.id).get(
                    'grp.cotizaciones.compromiso.siif') or '/'
            })
            ids_lis.append(obj.id)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'grp.cotizaciones.compromiso.proveedor',
            'res_id': ids_lis[0] if len(ids_lis) else False,
            'target': 'current',
        }
