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
import openerp.addons.decimal_precision as dp
import time
from openerp.exceptions import Warning
from openerp.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class account_invoice_ext_api(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    @api.one
    @api.depends('beneficiario_siif_id')
    def _get_rupe_beneficiario(self):
        self.id_rupe_benef = self.beneficiario_siif_id and self.beneficiario_siif_id.id_rupe or False

    @api.one
    @api.depends('beneficiario_siif_id')
    def _get_es_inciso_default_beneficiario(self):
        self.benef_es_inciso_default = self.beneficiario_siif_id and self.beneficiario_siif_id.es_inciso_default or False

    @api.one
    @api.depends('beneficiario_siif_id')
    def _get_es_inciso_beneficiario(self):
        self.benef_es_inciso = self.beneficiario_siif_id and self.beneficiario_siif_id.es_inciso or False

    # @api.one
    # def _get_responsable_siif_editable(self):
    #     res = {}
    #     in_grp = self.env.user.has_group('grp_seguridad.grp_compras_apg_Responsable_SIIF')
    #     self.responsable_siif_editable = self.state in (
    #         'sice', 'paid') and self.tipo_ejecucion_codigo_rel == 'P' and in_grp

    # TODO SPRING 8 GAP 60 L: Calculando el campo Total priorizado
    @api.one
    @api.depends('inv_prioritized_line')
    def _get_prioritize_total(self):
        pr_sum = 0.0
        if isinstance(self.id, (int, long)):
            for line in self.inv_prioritized_line:
                pr_sum += line.monto_priorizado
            self.prioritize_total = pr_sum

    # TODO Spring 8 GAP 115 C
    @api.one
    def _compute_mostrar_boton_enviar(self):
        self.mostrar_boton_enviar = False
        if self.state in ['open', 'prioritized', 'intervened']:
            self.mostrar_boton_enviar = len(self.cesion_ids.filtered(lambda x: not x.account_move_name)) != 0

    @api.depends('tc_presupuesto')
    def _get_tc_pres_fnc(self):
        for invoice in self:
            invoice.tc_presupuesto_fnc = invoice.tc_presupuesto
            invoice.tc_presupuesto_fnc_res = invoice.tc_presupuesto

    @api.one
    @api.depends('partner_id')
    def _compute_beneficiario_val_ids(self):
        #Busco el partner que tenga el flag es_inciso_default = True
        inciso_default = self.env['res.partner'].search([('es_inciso_default', '=', True)])
        benef_val_ids = inciso_default.ids
        if self.partner_id and self.partner_id.id not in benef_val_ids:
            benef_val_ids.append(self.partner_id.id)
        self.domain_beneficiario_ids = [(6, 0, benef_val_ids)]

    # responsable_siif_editable = fields.Boolean(compute='_get_responsable_siif_editable',
    #                                            string='Responsable Siif editable')
    beneficiario_siif_id = fields.Many2one('res.partner', string=u'Beneficiario SIIF', store=True, ondelete='restrict',
                                           copy=False)
    domain_beneficiario_ids = fields.Many2many('res.partner', compute="_compute_beneficiario_val_ids", string='Lista domain beneficiarios')
    # SIIF cuenta bancaria datos que se obligan en SIIF
    id_rupe_benef = fields.Integer(compute='_get_rupe_beneficiario', string='ID RUPE Beneficiario', store=True)
    benef_es_inciso_default = fields.Boolean(compute='_get_es_inciso_default_beneficiario',
                                             string='Es inciso por defecto', store=True)
    benef_es_inciso = fields.Boolean(compute='_get_es_inciso_beneficiario', string=u'¿Beneficiario SIIF únicamente?', store=True)
    rupe_cuenta_bancaria_id = fields.Many2one('rupe.cuentas.bancarias', string='Cuenta Bancaria RUPE', store=True)
    res_partner_bank_id = fields.Many2one('res.partner.bank', string='Cuenta Bancaria', store=True)
    cesion_ids = fields.One2many('grp.cesion.embargo', 'invoice_id', u'Cesion/Embargo IDs')
    cesion_embargo = fields.Boolean(u"Cesión/Embargo")

    intervenido_con_observ = fields.Boolean(u"Intervenido con observaciones")
    observacion_ids = fields.One2many('grp.observacion.tc', 'invoice_id', u'Observación')

    in_regulation_clearing = fields.Boolean(string=u'En regularización clearing',
                                            default=False)  # TODO: SPRING 8 GAP 236.237 M
    regularizacion_id = fields.Many2one('regularizacion.clearing',
                                        u'Documento Agrupador Suministros')  # TODO: SPRING 8 GAP 236.237 M
    prioritize_total = fields.Float(string=u'Total priorizado',
                                    compute='_get_prioritize_total')  # TODO SPRING 8 GAP 60 L: Agregando campo Total priorizado
    oo_difference_change_id = fields.Many2one('account.invoice',
                                              string=u'Obligación origen diferencia de cambio')  # TODO SPRING 8 GAP 61 L
    # TODO Spring 8 GAP 115 C
    mostrar_boton_enviar = fields.Boolean(u"Mostrar Botón", compute='_compute_mostrar_boton_enviar')
    # TODO R Spring 8 GAP 117
    tipo_ejecucion_alert = fields.Boolean(u"Mostar alerta tipo de ejecución", compute='_compute_tipo_ejecucion_alert')
    show_warning = fields.Boolean(u"Mostar alerta tipo de ejecución", default=True)

    # TODO R Spring 9 GAP 65
    tipo_nota_credito = fields.Selection([('A', u'A - Aumento'), ('R', u'R - Reducción'), ('D', u'D - Devolución al crédito')], u'Tipo modificación', required=False)

    compromiso_proveedor_id = fields.Many2one('grp.cotizaciones.compromiso.proveedor', string='Compromiso proveedor')
    #Priorizaciones
    inv_prioritized_line = fields.One2many('grp.account.invoice.prioritized.line','factura_grp_id',string='Priorizaciones')
    # ajuste_obligacion = fields.Boolean(string=u"Es ajuste obligación", default=False)

    tc_presupuesto_fnc = fields.Float('Tipo de cambio presupuesto', digits=(10, 5), compute='_get_tc_pres_fnc')
    #Se repite solo porque en el formulario se muestra en 2 lugares direferentes
    tc_presupuesto_fnc_res = fields.Float('Tipo de cambio presupuesto', digits=(10, 5), compute='_get_tc_pres_fnc')
    unidad_ejecutora_id = fields.Many2one('unidad.ejecutora', string=u"Documento Beneficiario SIIF")

    # RAGU enlazar asientos de provision aguinaldo
    aguinaldo_move_ids = fields.Many2many('account.move','account_invoice_move_aguinaldo_rel', 'invoice_id', 'move_id', string=u"Asientos de provisión")

    filtro_sir = fields.Char(string=u'Filtro código SIR', compute='_compute_filtro_sir')

    inciso_doc_optgn = fields.Char("Inciso documento de OPTGN", size=2)
    unidad_ejec_doc_optgn = fields.Char("Unidad ejecutora documento de OPTGN", size=3)
    nro_doc_optgn = fields.Char("Nro. documento de OPTGN", size=6)
    ano_doc_respaldo = fields.Char(u"Año de documento respaldo", size=4)

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

    @api.one
    @api.constrains('inciso_doc_optgn', 'unidad_ejec_doc_optgn', 'nro_doc_optgn', 'ano_doc_respaldo')
    def _check_optgn_digits(self):
        if self.inciso_doc_optgn and not self.inciso_doc_optgn.isdigit():
            raise ValidationError(_(u'El Inciso documento de OPTGN debe ser numérico!'))
        if self.unidad_ejec_doc_optgn and not self.unidad_ejec_doc_optgn.isdigit():
            raise ValidationError(_(u'La Unidad ejecutora documento de OPTGN debe ser numérico!'))
        if self.nro_doc_optgn and not self.nro_doc_optgn.isdigit():
            raise ValidationError(_(u'El Nro. documento de OPTGN debe ser numérico!'))
        if self.ano_doc_respaldo and not self.ano_doc_respaldo.isdigit():
            raise ValidationError(_(u'El Año de documento respaldo debe ser numérico!'))

    @api.one
    @api.constrains('supplier_invoice_number')
    def _check_number_digits(self):
        if self.supplier_invoice_number and not self.supplier_invoice_number.isdigit():
            raise ValidationError(_(u'El Nº de factura del proveedor debe ser numérico!'))

    # @api.one
    # @api.constrains('state')
    # def _check_amounts(self):
    #     if self.state == 'prioritized' and self.prioritize_total != self.amount_ttal_liq_pesos:
    #         raise ValidationError(_(u'No puede cambiar de estado porque el Total priorizado no es igual a Líquido pagable!'))

    # # TODO R Spring 9 GAP 65 chequeando total contra tipo_nota_credito en las notas de credito
    # @api.one
    # @api.constrains('tipo_nota_credito')
    # def _check_tipo_nota_credito(self):
    #     if self.type == 'in_refund' and self.tipo_nota_credito and ((self.tipo_nota_credito == 'A' and self.amount_total >= 0) or (self.tipo_nota_credito == 'R' and self.amount_total <= 0)):
    #         raise ValidationError(_(u'No coincide el Monto Total con el Tipo de Nota de Crédito seleccionado!'))

    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False, payment_term=False, partner_bank_id=False,
                            company_id=False):
        result = super(account_invoice_ext_api, self).onchange_partner_id(type, partner_id, date_invoice, payment_term,
                                                                          partner_bank_id, company_id)
        result['value'].update({'beneficiario_siif_id': False, 'domain_beneficiario_ids': False})
        domain_ids = []
        part_ids = self.env['res.partner'].search([('es_inciso_default', '=', True)])
        if part_ids:
            for idp in part_ids:
                domain_ids.append(idp.id)
        if partner_id:
            domain_ids.append(partner_id)

        if domain_ids:
            result['value'].update({'domain_beneficiario_ids': [(6, 0, [x for x in domain_ids])]})
        return result

    @api.multi
    def onchange_beneficiario_siif_id(self, beneficiario_siif_id):
        result = {}
        # return result
        result.setdefault('value', {})
        if not beneficiario_siif_id:
            result['value'].update(
                {'rupe_cuenta_bancaria_id': False, 'res_partner_bank_id': False, 'benef_es_inciso_default': False,
                 'benef_es_inciso': False})
            return result
        partner = self.env['res.partner'].browse(beneficiario_siif_id)

        result['value'].update(
            {'id_rupe_benef': partner.id_rupe or '', 'benef_es_inciso_default': partner.es_inciso_default or False,
             'benef_es_inciso': partner.es_inciso or False})
        return result

    def get_tc_presupuesto_rate(self, currency_id, fecha):
        if not currency_id:
            _rate = 0
        else:
            ctx = self.env.context.copy()
            if fecha:
                ctx.update({'date': fecha})
            else:
                ctx.update({'date': time.strftime('%Y-%m-%d')})
            currency = self.env['res.currency'].with_context(ctx).browse(currency_id)
            if currency.rate_silent != 0 and currency.rate_presupuesto != 0:
                _rate = currency.rate_presupuesto
            else:
                _rate = 0
        return _rate


    @api.multi
    def onchange_date_currency_id(self, currency_id, date_invoice, partner_id, fecha_tipo_cambio=False):
        result = super(account_invoice_ext_api, self).onchange_date_currency_id(currency_id=currency_id, date_invoice=date_invoice, partner_id=partner_id, fecha_tipo_cambio=fecha_tipo_cambio)
        result['value'].update({
            'fecha_tipo_cambio': date_invoice,
            'tc_presupuesto': self.get_tc_presupuesto_rate(currency_id, fecha_tipo_cambio)
        })
        return result

    @api.multi
    def onchange_tc_date(self, currency_id, fecha_tipo_cambio):
        return {'value': {'tc_presupuesto': self.get_tc_presupuesto_rate(currency_id, fecha_tipo_cambio)}}

    @api.multi
    def onchange_orden_compra(self, orden_compra_id=False):
        result = {'value': {
            'origin': False,
            'invoice_line': False,
        }}
        if not orden_compra_id:
            return result
        else:
            lines = []
            orden = self.env['purchase.order'].browse(orden_compra_id)
            result['value'].update({'origin': orden.name or False,})
            result['value'].update({'cod_moneda': orden.cod_moneda.id or False,})
            result['value'].update({'partner_id': orden.partner_id.id or False,})
            result['value'].update({'operating_unit_id': orden.operating_unit_id.id})

            if orden.order_line:
                for line in orden.order_line:
                    a = False
                    if line.product_id:

                        res = self.env['product.product'].browse(line.product_id.id)
                        a = res and res.property_account_expense and res.property_account_expense.id or False
                        if not a:
                            a = res and res.categ_id and res.categ_id.property_account_expense_categ and res.categ_id.property_account_expense_categ.id
                    lines.append(({
                        'name': line.name,
                        'origin': line.order_id.name,
                        'invoice_line_tax_id': [(6, 0, [x.id for x in line.taxes_id])],
                        'uos_id': line.product_uom.id,
                        'product_id': line.product_id.id,
                        'account_id': a,
                        'price_unit': line.price_unit,
                        'price_subtotal': line.price_subtotal,
                        'quantity': line.product_qty,
                        'purchase_line_id': line.id,
                        'id_item': line.id_item,
                        'id_variacion': line.id_variacion,
                        'desc_variacion': line.desc_variacion,
                    }))
                result['value'].update({'invoice_line': lines})
            return result

    @api.one
    def get_ref(self, inv):
        ref_move = inv.reference or inv.name

        if inv.type in ('in_invoice'):
            for inv_line in inv.invoice_line:
                name_first_line = inv_line.name
                break
            # Serie y Nro factura de proveedor (para el caso de las facturas de proveedores). Debe aparecer como "A 1234"
            if inv.doc_type == 'invoice':
                ref_move = ('%s %s' % (inv.serie_factura, inv.supplier_invoice_number))
            # Para el caso de 3en1 y Obligación, debe mostrar la descripción de la primera línea de la factura
            elif inv.doc_type in ('3en1_invoice', 'obligacion_invoice'):
                ref_move = name_first_line
                # 002-Fin modificacion
        return ref_move


    @api.one
    @api.constrains('cesion_ids', 'invoice_line', 'state')
    def _check_monto_cedido(self):
        if self.state not in ['draft','proforma','proforma2','sice'] and self.cesion_embargo and len(self.cesion_ids) == 0:
            raise exceptions.ValidationError(_(u'Se debe ingresar al menos un cesión o embargo.'))

        cesion_ttal = 0

        lines = self.cesion_ids
        for line in lines:
            cesion_ttal += line.monto_cedido_embargado

        if len(self.cesion_ids) and self.amount_ttal_liq_pesos < cesion_ttal:
            raise exceptions.ValidationError(_(u'El monto cedido/embargado es mayor al liquido pagable.'))

    @api.onchange('tipo_nota_credito')
    def onchange_tipo_nota_credito(self):
        if self.tipo_nota_credito:
            if self.tipo_nota_credito == 'R':
                self.type = 'in_refund'
            elif self.tipo_nota_credito == 'A':
                self.type = 'in_invoice'

    @api.onchange('cesion_embargo')
    def onchange_cesion(self):
        if not self.cesion_embargo and len(self.cesion_ids) > 0:
            self.cesion_ids = [(5,)]

    @api.onchange('inciso_siif_id', 'operating_unit_id', 'compromiso_id', 'doc_type')
    def onchange_inciso(self):
        if self.doc_type in ['obligacion_invoice']:
            if self.compromiso_id:
                self.ue_siif_id = self.compromiso_id.ue_siif_id.id
            else:
                self.ue_siif_id = False
        elif self.doc_type in ['invoice'] and self.compromiso_proveedor_id:
            if not self.ue_siif_id:
                self.ue_siif_id = self.compromiso_proveedor_id.ue_siif_id.id
        elif self.inciso_siif_id and self.operating_unit_id and self.operating_unit_id.unidad_ejecutora:
            unidad_ejecutora = self.env['grp.estruc_pres.ue'].search([('inciso_id','=',self.inciso_siif_id.id),('ue','=',self.operating_unit_id.unidad_ejecutora)], limit=1)
            if unidad_ejecutora:
                self.ue_siif_id = unidad_ejecutora.id
            else:
                self.ue_siif_id = False
        else:
            self.ue_siif_id = False

    @api.onchange('operating_unit_id')
    def onchange_operating_unit(self):
        if self.operating_unit_id and self.operating_unit_id.unidad_ejecutora:
            unidad_ejecutora = self.env["unidad.ejecutora"].search(
                [('codigo', '=', int(self.operating_unit_id.unidad_ejecutora))])
            if unidad_ejecutora:
                self.unidad_ejecutora_id = unidad_ejecutora.id

    # TODO Spring 8 GAP 115 C
    def _contabilizar_cesiones(self):
        self.ensure_one()
        if self.cesion_embargo:
            domain = [('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())]
            if self.env.user.company_id and self.env.user.company_id.id:
                domain.append(('company_id', '=', self.env.user.company_id.id))
            fiscal_year_id = self.env['account.fiscalyear'].search(domain)
            AccountMove = cesion_moves = self.env['account.move']
            period_id = self.env['account.period'].find(fields.Date.today()).id
            for line in self.cesion_ids.filtered(lambda x: not x.account_move_name):
                debit_move_line = {
                    'name': 'Cesión',
                    'partner_id': self.partner_id.id,
                    'account_id': self.account_id.id,
                    'credit': 0.0,
                    'debit': line.monto_cedido_embargado * self.tipo_de_cambio_fnc,
                    'period_id': period_id,
                    'journal_id': self.journal_id.id,
                    'amount':line.monto_cedido_embargado
                }
                credit_move_line = {
                    'name': 'Cesión',
                    'partner_id': line.cesion_partner_id.id,
                    'account_id': self.account_id.id,
                    'debit': 0.0,
                    'credit': line.monto_cedido_embargado * self.tipo_de_cambio_fnc,
                    'period_id': period_id,
                    'journal_id': self.journal_id.id,
                    'amount': line.monto_cedido_embargado * -1
                }
                move = {
                    'ref': self.nro_factura_grp,
                    'journal_id': self.journal_id.id,
                    'date': fields.Date.today(),
                    'period_id': period_id,
                    'name': self.env['ir.sequence'].with_context(fiscalyear_id=fiscal_year_id.id).next_by_id(self.journal_id.sequence_id.id),
                    'line_id': [(0, 0, debit_move_line), (0, 0, credit_move_line)]
                }
                move = AccountMove.create(move)
                move.button_validate()
                cesion_moves |= move
                line.write({'account_move_name': move.name})

            lines2rec = self.move_id.mapped('line_id').filtered(lambda x: x.account_id.id==self.account_id.id)
            lines2rec |= cesion_moves.mapped('line_id').filtered(lambda x: x.partner_id.id==self.partner_id.id)
            if len(lines2rec) >= 2:
                lines2rec.reconcile_partial()
        return True

    # TODO Spring 8 GAP 115 C
    def _divisa_line(self, monto, positive=True):
        self.ensure_one()
        amount = monto * self.tipo_de_cambio_fnc
        return {
            'amount_currency': amount if positive else amount * -1,
            'currency_id': self.currency_id.id,
        }

    # TODO R Spring 8 GAP 117
    @api.multi
    @api.depends('state','doc_type','siif_tipo_ejecucion','compromiso_id')
    def _compute_tipo_ejecucion_alert(self):
        for rec in self:
            rec.tipo_ejecucion_alert = False if rec._verificar_tipo_ejecucion() else True

    @api.one
    def do_not_show_warning(self):
        self.write({'show_warning':False})

    @api.multi
    def btn_obligar(self):
        # Agregar control sobre campos Compromiso proveedor, Tipo de Documento, y Descripcion Siif
        # solo para pantalla de Factura de Proveedor.
        for inv in self:
            if self.env.user.company_id.integracion_siif and inv.nro_obligacion:
                raise exceptions.ValidationError("Este documento ya ha sido enviado a SIIF. Por favor, actualice el navegador.")
            if inv.type in ['in_invoice'] and inv.doc_type in ['invoice'] and inv.siif_tipo_ejecucion\
               and inv.siif_tipo_ejecucion.codigo not in ['P']:
                if not inv.compromiso_proveedor_id or not inv.siif_tipo_documento or not inv.siif_descripcion:
                    raise exceptions.ValidationError(u'Los campos Compromiso proveedor, '
                                                     u'Tipo documento SIIF y Descripción SIIF'
                                                     u' son obligatorios.')
            res = super(account_invoice_ext_api, inv).btn_obligar()
            inv._contabilizar_cesiones()  # TODO Spring 8 GAP 115 C
        return res

    # TODO SPRING 8 GAP 224 R
    def _set_bonus_provision(self):
        AccountMove = self.env['account.move']
        for rec in self:
            period = self.env['account.period'].search([('date_start', '<=', rec.entry_date),
                                                           ('date_stop', '>=', rec.entry_date)], limit=1)
            period_id = period.id
            aguinaldo_moves = []
            for provision_aguinaldo in self.env['grp.provision.aguinaldo'].search([]):
                lines = rec.invoice_line.filtered(
                    lambda x: x.account_id.id == provision_aguinaldo.incoming_account_id.id)
                if lines:
                    monto = sum(map(lambda x: x.monto_moneda_base, lines))

                    credit_move_line = {
                        'name': '/',
                        'account_id': provision_aguinaldo.provision_account_id.id,
                        'debit': 0.0,
                        'credit': monto / 12,
                        'ref': '/',
                        'period_id': period_id,
                        'journal_id': rec.journal_id.id,
                    }
                    debit_move_line = {
                        'name': '/',
                        'account_id': provision_aguinaldo.bonus_account_id.id,
                        'credit': 0.0,
                        'debit': monto / 12,
                        'ref': '/',
                        'period_id': period_id,
                        'journal_id': rec.journal_id.id,
                    }
                    move = {
                        'ref': "Provisión de aguinaldo",
                        'journal_id': rec.journal_id.id,
                        'date': rec.entry_date,
                        'period_id': period_id,
                        'name': self.env['ir.sequence'].with_context(fiscalyear_id=period.fiscalyear_id.id).next_by_id(rec.journal_id.sequence_id.id),
                        'line_id': [(0, 0, debit_move_line), (0, 0, credit_move_line)]
                    }
                    aguinaldo_move_id = AccountMove.create(move)
                    aguinaldo_moves.append(aguinaldo_move_id.id)
            rec.write({'aguinaldo_move_ids':[(6,0,aguinaldo_moves)]})
        return True

    # TODO SPRING 8 GAP 224 R
    def _set_bonus(self):
        AccountMove = self.env['account.move']
        provision_aguinaldo = self.env['grp.provision.aguinaldo'].search([], limit=1) or False
        if provision_aguinaldo:
            for rec in self:
                period = self.env['account.period'].search([('date_start', '<=', rec.entry_date),
                                                               ('date_stop', '>=', rec.entry_date)], limit=1)
                period_id = period.id
                lines = self.invoice_line.filtered(
                    lambda x: x.account_id.id == provision_aguinaldo.bonus_account_id.id)
                if lines:
                    monto = sum(map(lambda x: x.monto_moneda_base, lines))

                    credit_move_line = {
                        'name': '/',
                        'account_id': provision_aguinaldo.bonus_account_id.id,
                        'debit': 0.0,
                        'credit': monto,
                        'ref': '/',
                        'period_id': period_id,
                        'journal_id': rec.journal_id.id,
                    }
                    debit_move_line = {
                        'name': '/',
                        'account_id': provision_aguinaldo.provision_account_id.id,
                        'credit': 0.0,
                        'debit': monto,
                        'ref': '/',
                        'period_id': period_id,
                        'journal_id': rec.journal_id.id,
                    }
                    move = {
                        'ref': "Aguinaldo",
                        'journal_id': rec.journal_id.id,
                        'date': rec.entry_date,
                        'period_id': period_id,
                        'name': self.env['ir.sequence'].with_context(fiscalyear_id=period.fiscalyear_id.id).next_by_id(rec.journal_id.sequence_id.id),
                        'line_id': [(0, 0, debit_move_line), (0, 0, credit_move_line)]
                    }
                    AccountMove.create(move)
        return True

    # TODO SPRING 8 GAP 224 R
    @api.multi
    def action_move_create(self):
        res = super(account_invoice_ext_api, self).action_move_create()
        invoices = self.filtered(
            lambda x: x.siif_tipo_ejecucion.codigo == 'N' and x.siif_concepto_gasto.concepto == '1')
        # AGUINALDOS
        invoices._set_bonus_provision()
        invoices._set_bonus()
        return res

    # TODO Spring 8 GAP 115 C
    @api.multi
    def invoice_validate(self):
        for factura in self:
            if factura.doc_type in ['in_invoice']:
                if factura.state in ['sice'] and factura.tipo_ejecucion_codigo_rel not in ['P', 'R']\
                   and not factura.compromiso_proveedor_id:
                    raise exceptions.ValidationError(u'El campo Compromiso proveedor es requerido.'
                                                     u' Por favor, ingrese valor para el campo.')
                if factura.state in ['sice'] and factura.tipo_ejecucion_codigo_rel not in ['P']\
                   and not factura.siif_tipo_documento:
                    raise exceptions.ValidationError(u'El campo Tipo de documento es requerido.'
                                                     u' Por favor, ingrese valor para el campo.')
                if factura.state in ['sice'] and factura.tipo_ejecucion_codigo_rel not in ['P', 'R']\
                   and not factura.siif_descripcion:
                    raise exceptions.ValidationError(u'El campo Descripcion SIIF es requerido.'
                                                     u' Por favor, ingrese valor para el campo.')
        self.check_llavep() #MVAR: se mueve control (antes estaba en la condicion de wkf)
        res = super(account_invoice_ext_api, self).invoice_validate()
        self._contabilizar_cesiones()
        return res

    # TODO Spring 8 GAP 117 C
    # TODO R Spring 8 GAP 117 CI
    def _verificar_tipo_ejecucion(self):
        self.ensure_one()
        if self.state == 'draft' and self.doc_type in ['obligacion_invoice', 'invoice']:
            siif_tipo_ejecucion = self.siif_tipo_ejecucion.id if self.siif_tipo_ejecucion else False
            if self.compromiso_id and self.compromiso_id.siif_tipo_ejecucion:
                tipo_ejecucion_rel = self.compromiso_id.siif_tipo_ejecucion.id
            elif self.orden_compra_id and self.orden_compra_id.siif_tipo_ejecucion:
                tipo_ejecucion_rel = self.orden_compra_id.siif_tipo_ejecucion.id
            else:
                tipo_ejecucion_rel = False
            if tipo_ejecucion_rel != siif_tipo_ejecucion:
                return False
        return True

    # TODO SPRING 8 GAP 236.237 M
    @api.multi
    def check_llavep(self):
        for rec in self:
            if rec.siif_tipo_ejecucion.codigo == 'R':
                if rec.total_llavep <> rec.total_nominal:
                    raise exceptions.ValidationError(
                        _(u'La sumatoria de importes de llaves presupuestales no es igual al monto de la factura.'))
        return True

    # TODO SPRING 10 GAP 493 C
    def crear_extorno(self):
        moves = self.move_id + self.aguinaldo_move_ids
        if moves:
            period_id = self.env['account.period'].find(fields.Date.today()).id
            moves.create_reversals(
                fields.Date.today(),
                reversal_period_id=period_id,
            )
        self.cesion_ids.crear_extorno()

    # TODO SPRING 8 GAP 236.237 M
    @api.multi
    def action_cancel(self):
        for inv in self:
            if (inv.doc_type in ['invoice'] and inv.tipo_ejecucion_codigo_rel in ['P']) or\
               (inv.doc_type in ['3en1_invoice', 'vales_caja', 'adelanto_viatico']) or\
               (inv.type in ['in_invoice']):
                if inv.fecha_aprobacion:
                    raise exceptions.ValidationError(u'Este documento ya fue aprobado para su pago.'
                                                                u' Cancele la aprobación del pago si '
                                                                u'desea cancelar la factura.')
            if inv.in_regulation_clearing:
                raise exceptions.ValidationError(
                    _(u'Este documento está en un documento Regularización clearing. No es posible cancelarlo.'))
            inv.cesion_ids.crear_extorno()
        return super(account_invoice_ext_api, self).action_cancel()

    # TODO SPRING 10 GAP 493 C
    @api.multi
    def btn_borrar_obligacion(self):
        for rec in self:
            if rec.state == 'open' and rec.tipo_ejecucion_codigo_rel != 'P':
                rec.crear_extorno()
        return super(account_invoice_ext_api, self).btn_borrar_obligacion()

    # TODO SPRING 10 GAP 493 C
    @api.multi
    def btn_cancel_obligacion(self):
        for rec in self:
            if rec.state == 'open' and rec.tipo_ejecucion_codigo_rel != 'P':
                rec.crear_extorno()
        return super(account_invoice_ext_api, self).btn_cancel_obligacion()

    # TODO SPRING 8 GAP 236.237 M
    @api.multi
    def get_invoice(self):
        mod_obj = self.env['ir.model.data']
        for rec in self:
            if rec.doc_type == 'invoice':
                res = mod_obj.get_object_reference('account', 'invoice_supplier_form')
                return {
                    'name': 'Factura de Proveedores',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_id': [res and res[1] or False],
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'res_id': rec.id,
                    'target': 'new',
                    'nodestroy': True,
                    'context': "{}",
                }

    def _get_llpapgs_compromiso_proveedor(self):
        llpapg_data = []
        for llavep in self.compromiso_proveedor_id.llpapg_ids:
            llpapg_data.append((0, 0, {
                'programa': llavep.programa,
                'odg': llavep.odg,
                'auxiliar': llavep.auxiliar,
                'disponible': llavep.disponible,
                'proyecto': llavep.proyecto,
                'fin': llavep.fin,
                'mon': llavep.mon,
                'tc': llavep.tc,
                'importe': llavep.importe,
                'programa_id': llavep.programa_id.id,
                'odg_id': llavep.odg_id.id,
                'auxiliar_id': llavep.auxiliar_id.id,
                'proyecto_id': llavep.proyecto_id.id,
                'fin_id': llavep.fin_id.id,
                'mon_id': llavep.mon_id.id,
                'tc_id': llavep.tc_id.id,
            }))
        return llpapg_data

    @api.onchange('compromiso_proveedor_id')
    def _onchange_compromiso_proveedor_id(self):
        if self.compromiso_proveedor_id:
            self.nro_compromiso = self.compromiso_proveedor_id.nro_compromiso
            self.monto_comprometido = self.compromiso_proveedor_id.total_comprometido
            self.nro_afectacion = self.compromiso_proveedor_id.nro_afectacion_siif
            self.monto_afectado = self.compromiso_proveedor_id.apg_id.total_estimado
            self.fiscalyear_siif_id = self.compromiso_proveedor_id.fiscalyear_id.id
            self.inciso_siif_id = self.compromiso_proveedor_id.inciso_siif_id.id
            self.ue_siif_id = self.compromiso_proveedor_id.ue_siif_id.id
            llaves = self._get_llpapgs_compromiso_proveedor()
            llaves2 = llaves3 = self.env["grp.compras.lineas.llavep"]
            for llave in llaves:
                llaves2 |= llaves3.new(llave[2])
            self.llpapg_ids = llaves2


    @api.multi
    def action_llpapg_reload(self):
        for rec in self:
            rec.llpapg_ids.unlink()
            llpapg_data = []
            if rec.compromiso_proveedor_id:
                llpapg_data.extend(rec._get_llpapgs_compromiso_proveedor())
            elif rec.orden_compra_id.pc_apg_id:
                for llavep in rec.orden_compra_id.pc_apg_id.llpapg_ids:
                    llpapg_data.append((0, 0, {
                        'programa': llavep.programa,
                        'odg': llavep.odg,
                        'auxiliar': llavep.auxiliar,
                        'disponible': llavep.disponible,
                        'proyecto': llavep.proyecto,
                        'fin': llavep.fin,
                        'mon': llavep.mon,
                        'tc': llavep.tc,
                        'importe': llavep.importe,
                        'programa_id': llavep.programa_id.id,
                        'odg_id': llavep.odg_id.id,
                        'auxiliar_id': llavep.auxiliar_id.id,
                        'proyecto_id': llavep.proyecto_id.id,
                        'fin_id': llavep.fin_id.id,
                        'mon_id': llavep.mon_id.id,
                        'tc_id': llavep.tc_id.id,
                    }))
            elif rec.siif_tipo_ejecucion.codigo == 'P':
                rec.action_llpapg_reload_3en1()
            rec.llpapg_ids = llpapg_data

    # TODO R LLAVES PRESUPUESTALES
    @api.multi
    def action_llpapg_reload_3en1(self):
        ODG = self.env['grp.estruc_pres.odg']
        Auxiliar = self.env['grp.estruc_pres.aux']
        for rec in self:
            llpapgs = [(5,)]
            for line in rec.invoice_line.filtered(lambda x: x.product_id.id):
                if not line.product_id.objeto_gasto:
                    raise ValidationError(_(u'El producto %s no tiene objeto del gasto asociado!') % (
                    line.product_id.name_get()[0][1]))
                odg = ODG.search(
                    [('ue_id', '=', rec.ue_siif_id.id), ('odg', '=', line.product_id.objeto_gasto.name)], limit=1)
                if not odg:
                    raise exceptions.ValidationError(_(
                        u'No se ha encontrado el objeto del gasto asociado al producto %s para esta combinación de: UE, Inciso, Año fiscal!') % (
                                                     line.product_id.name_get()[0][1]))
                auxiliar = Auxiliar.search(
                    [('odg_id', '=', odg.id), ('aux', '=', line.product_id.objeto_gasto.auxiliar)],
                    limit=1) if odg else False
                if not auxiliar:
                    raise exceptions.ValidationError(_(
                        u'No se ha encontrado el auxiliar asociado al producto %s para este combinación de: ODG, UE, Inciso, Año fiscal!') % (
                                                     line.product_id.name_get()[0][1]))
                if auxiliar:
                    new_llpapg = True
                    for llpapg in llpapgs:
                        if llpapg[0] == 0 and llpapg[2] and llpapg[2]['odg_id'] == odg.id and llpapg[2][
                            'auxiliar_id'] == auxiliar.id:
                            new_llpapg = False
                            # llpapg[2]['importe'] += line.monto_moneda_base
                            llpapg[2]['importe'] += line.price_unit * line.quantity
                            break
                    if new_llpapg:
                        llpapgs.append(
                            (0, 0, {'odg_id': odg.id, 'auxiliar_id': auxiliar.id, 'importe': line.price_unit * line.quantity}))
            #Se redondea al final
            company_currency = rec.company_id.currency_id
            invoice_currency = rec.currency_id
            for llave in llpapgs:
                if len(llave) == 3 and 'importe' in llave[2]:
                    llave[2]['importe'] = invoice_currency.with_context(date=rec.date_invoice).compute(llave[2]['importe'], company_currency)
            rec.write({'llpapg_ids': llpapgs})


    @api.multi
    def btn_observ_tribunal(self):
        siif_proxy = self.env['siif.proxy']
        motivo_intervencion = self.env['motivo.intervencion.tc']
        observacion = self.env['grp.observacion.tc']

        for rec in self:
            # _logger.info('rec.state: %s', rec.state)
            # _logger.info('rec.fiscalyear_siif_id: %s', rec.fiscalyear_siif_id.name)
            # _logger.info('rec.nro_afectacion_fnc: %s', rec.nro_afectacion_fnc)
            # _logger.info('rec.nro_compromiso_fnc: %s', rec.nro_compromiso_fnc)
            # _logger.info('rec.nro_obligacion: %s', rec.nro_obligacion)
            # _logger.info('rec.inciso_siif_id: %s', rec.inciso_siif_id.inciso)
            # _logger.info('rec.ue_siif_id: %s', rec.ue_siif_id.ue)

            intervencion = siif_proxy.get_intervenciones(rec.fiscalyear_siif_id.name, rec.inciso_siif_id.inciso, rec.ue_siif_id.ue, rec.nro_afectacion_fnc, rec.nro_compromiso_fnc, rec.nro_obligacion, 0)
            # intervencion = siif_proxy.get_intervenciones('2017', '12', '001', '297', '1', '1', '0')
            # _logger.info('intervencion: %s', intervencion)

            if intervencion.resultado == 1:

                # _logger.info('intervencion.motivoDeIntervencion: %s', intervencion.motivoDeIntervencion)
                # _logger.info('intervencion.descripcionMotivoIntervencion: %s',
                #              intervencion.descripcionMotivoIntervencion)
                # _logger.info('intervencion.observacionInterv: %s', intervencion.observacionInterv)

                motivo = motivo_intervencion.search([('codigo', '=', intervencion.motivoDeIntervencion)])
                if not motivo:
                    raise exceptions.ValidationError(_(
                        u'No se ha encontrado motivo de intervención en el catálogo de Motivo Intervenciones para el código %s retornado por SIIF') % (
                        intervencion.motivoDeIntervencion))
                else:
                    if motivo.impacta_documento:
                        # Crear registro en grilla de Observaciones
                        obs = {
                            'invoice_id': self.id,
                            'motivo_intervencion_id': motivo.id,
                            # 'observacion': intervencion.observacionInterv,
                        }
                        obs = observacion.create(obs)

                        # Marcar campo 'Intervenido con Observaciones'
                        self.write({'intervenido_con_observ': True})
                    else:
                        # Desmarcar campo 'Intervenido con Observaciones'
                        if rec.intervenido_con_observ:
                            self.write({'intervenido_con_observ': False})

    @api.constrains('partner_id', 'sec_factura', 'serie_factura', 'supplier_invoice_number')
    def _check_numeros_factura(self):
        for invoice in self:
            if invoice.serie_factura and \
               invoice.supplier_invoice_number:
                domain = [
                    ('id', '<>', invoice.id),
                    ('state', 'not in', ['cancel', 'cancel_siif', 'cancel_sice']),
                    ('partner_id', '=', invoice.partner_id.id),
                    ('serie_factura', '=', invoice.serie_factura),
                    ('supplier_invoice_number', '=', invoice.supplier_invoice_number)
                ]
                if invoice.sec_factura:
                    domain.append(('sec_factura', '=', invoice.sec_factura))
                else:
                    # El operador in parece no funcionar para los enteros cuando se lo compara contra False
                    # domain.append(('sec_factura', 'in', [0, False]))
                    domain.append('|')
                    domain.append(('sec_factura', '=', 0))
                    domain.append(('sec_factura', '=', False))
                invoices = self.search(domain)
                if len(invoices) > 0:
                    raise exceptions.ValidationError(_(u'Existe otra factura con la misma combinación de '
                                                       u'Proveedor, Secuencia, Serie y Nro. de Factura de Proveedor.'))
        return True

    @api.one
    def copy(self, default=None):
        if default is None:
            default = {}
        default.update({
            'sec_factura': False,
            'serie_factura': False
        })
        return super(account_invoice_ext_api, self).copy(default=default)

class grp_account_invoice_prioritized_line(models.Model):
    _name = 'grp.account.invoice.prioritized.line'

    factura_grp_id = fields.Many2one('account.invoice', 'Factura GRP priorizada', readonly=True)
    fecha_confirmado = fields.Date('Fecha', readonly=True)
    monto_priorizado = fields.Integer('Monto', readonly=True)
    ruc = fields.Char('Ruc', readonly=True)


class grp_observacion_tc(models.Model):
    _name = 'grp.observacion.tc'

    invoice_id = fields.Many2one('account.invoice', string='Factura GRP')
    motivo_intervencion_id = fields.Many2one('motivo.intervencion.tc', string='Motivo')
    descripcion = fields.Char(related='motivo_intervencion_id.descripcion')
    observacion = fields.Char(string=u'Observación', size=100)

    _sql_constraints = [
        ('observacion_unique', 'unique(invoice_id,motivo_intervencion_id,observacion)', u'Ya existe una intervención con la misma observación')
    ]
