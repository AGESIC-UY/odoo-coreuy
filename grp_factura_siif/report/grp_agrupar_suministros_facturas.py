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

from openerp import fields, models, api, exceptions, _
from openerp import tools
from openerp.exceptions import ValidationError
import logging
import openerp.addons.decimal_precision as dp
from lxml import etree

LISTA_ESTADOS = [
    ('draft', 'Draft'),
    ('proforma', 'Pro-forma'),
    ('proforma2', 'Pro-forma'),
    ('sice', u'Confirmada'),
    ('cancel_sice', u'Anulado SICE'),
    ('in_approved', u'En Aprobación'),
    ('approved', u'Aprobado'),
    ('in_auth', u'En Autorización'),
    ('authorized', u'Autorizado'),
    ('open', 'Open'),
    ('intervened', u'Intervenida'),
    ('prioritized', u'Priorizada'),
    ('cancel_siif', u'Anulado SIIF'),
    ('paid', 'Paid'),
    ('forced', u'Obligado'),
    ('cancel', 'Cancelled'),
]

class GrpAgruparSuministrosFacturas(models.Model):
    _name = 'grp.agrupar.suministros.facturas'
    _auto = False

    invoice_id = fields.Many2one('account.invoice', 'Factura de Proveedor')
    partner_id = fields.Many2one('res.partner', string=u'Proveedor')
    date_invoice = fields.Date(string=u'Fecha factura', related='invoice_id.date_invoice')
    supplier_invoice_number = fields.Char(string=u'Nro factura proveedor',
                                          related='invoice_id.supplier_invoice_number')
    date_due = fields.Date(string=u'Fecha vencimiento', related='invoice_id.date_due')
    total_nominal = fields.Float(string=u'Total nominal en pesos', related='invoice_id.total_nominal')
    siif_concepto_gasto = fields.Many2one('presupuesto.concepto', string=u'Concepto del gasto')
    operating_unit_id = fields.Many2one('operating.unit', string=u'Unidad ejecutora')
    state = fields.Selection(LISTA_ESTADOS, related='invoice_id.state', string='Estado')
    in_regulation_clearing = fields.Boolean(string='En regularización clearing', related='invoice_id.in_regulation_clearing')
    currency_id = fields.Many2one('res.currency', string=u'Divisa', related='invoice_id.currency_id')
    nro_obligacion = fields.Integer(u'Nº obligación', related='invoice_id.nro_obligacion')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_agrupar_suministros_facturas')
        cr.execute("""
            create or replace view grp_agrupar_suministros_facturas as (
            (select
                row_number() over() as id,
                f.id as invoice_id,
                f.partner_id as partner_id,
                f.siif_concepto_gasto as siif_concepto_gasto,
                f.operating_unit_id as operating_unit_id
            from
                account_invoice f
                left join tipo_ejecucion_siif t on (f.siif_tipo_ejecucion = t.id)
                where f.state = 'open' and f.type = 'in_invoice' and f.doc_type in ('3en1_invoice','invoice')
                and f.in_regulation_clearing = False and t.codigo = 'R'))
        """)

    @api.multi
    def get_invoice(self):
        mod_obj = self.env['ir.model.data']
        for rec in self:
            if rec.invoice_id:
                res = mod_obj.get_object_reference('account', 'invoice_supplier_form')
                return {
                    'name': 'Factura de Proveedores',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_id': [res and res[1] or False],
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'res_id': rec.invoice_id.id,
                    'target': 'new',
                    'nodestroy': True,
                }

    def create_regularizacion(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        suministros = self.browse(cr, uid, ids, context)
        invoices = suministros.mapped('invoice_id')
        if len(ids) > 1:
            suministros.ckeck_suministros()

        operating_unit = suministros.mapped('operating_unit_id')
        fiscal_year_id = self.pool['account.fiscalyear'].find(cr, uid, dt=fields.Date.today())
        inciso_company = self.pool['res.users'].browse(cr, uid, uid).company_id.inciso
        inciso_siif_llp_id = self.pool['grp.estruc_pres.inciso'].search(cr, uid, [('fiscal_year_id', '=', fiscal_year_id),
                                                                                  ('inciso', '=', inciso_company)])
        ue_siif_llp_id = False
        if len(inciso_siif_llp_id) > 0:
            inciso_siif_llp_id = inciso_siif_llp_id[0]
            ue_ids = self.pool.get('grp.estruc_pres.ue').search(cr, uid, [('inciso_id', '=', inciso_siif_llp_id),
                                                                          ('ue', '=', operating_unit.unidad_ejecutora)], order='id desc', limit=1)
            ue_siif_llp_id = ue_ids and ue_ids[0] or False

        regularizacion = self.pool.get('regularizacion.clearing')
        vals = {
            'state': 'draft',
            'partner_id': suministros.mapped('partner_id').id,
            'beneficiario_siif_id': suministros.mapped('partner_id').id,
            'siif_concepto_gasto': suministros.mapped('siif_concepto_gasto').id,
            'operating_unit_id': operating_unit.id,
            'fiscalyear_id': fiscal_year_id,
            'inciso_siif_id': inciso_siif_llp_id,
            'ue_siif_id': ue_siif_llp_id,
        }
        regularizacion_id = regularizacion.create(cr, uid, vals, context)
        vals = {'account_invoice_ids': [(4, x) for x in invoices.ids]}
        llpapg_ids = invoices.mapped('llpapg_ids')
        llpapg_data = []
        if llpapg_ids:
            for llpapg in llpapg_ids:
                if not self.check_llpapg(llpapg_data, llpapg):
                    llpapg_data.append((0, 0, {
                        'disponible': llpapg.disponible,
                        'importe': llpapg.importe,
                        'programa_id': llpapg.programa_id.id,
                        'odg_id': llpapg.odg_id.id,
                        'auxiliar_id': llpapg.auxiliar_id.id,
                        'proyecto_id': llpapg.proyecto_id.id,
                        'fin_id': llpapg.fin_id.id,
                        'mon_id': llpapg.mon_id.id,
                        'tc_id': llpapg.tc_id.id,
                    }))
            vals['llpapg_ids'] = llpapg_data
        regularizacion.write(cr, uid, [regularizacion_id], vals, context)
        for invoice in invoices:
            invoice.write({'in_regulation_clearing': True, 'regularizacion_id': regularizacion_id})

        value = {
            'name': _('Regularización clearing'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'regularizacion.clearing',
            'type': 'ir.actions.act_window',
            'res_id': regularizacion_id,
            'target': 'current',
        }
        return value

    def check_llpapg(self,llpapg_data, llpapg):
        if len(llpapg_data):
            for line in llpapg_data:
                if line[2]['fin_id'] == llpapg.fin_id.id and line[2]['mon_id'] == llpapg.mon_id.id and \
                    line[2]['odg_id'] == llpapg.odg_id.id and line[2]['programa_id'] == llpapg.programa_id.id and \
                    line[2]['proyecto_id'] == llpapg.proyecto_id.id and line[2]['tc_id'] == llpapg.tc_id.id:
                    line[2]['importe']= line[2]['importe'] + llpapg.importe
                    return True
        return False



    def ckeck_suministros(self):
        if len(self.mapped('partner_id').ids) > 1 or len(self.mapped('siif_concepto_gasto').ids) > 1 or \
                        len(self.mapped('operating_unit_id').ids) > 1:
            raise exceptions.ValidationError(
                _(u'Todas las facturas a agrupar deben tener el mismo Proveedor, Unidad ejecutora y Concepto del gasto.'))


