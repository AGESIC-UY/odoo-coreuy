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

from openerp import models, fields, api, _ ,exceptions
import openerp.addons.decimal_precision as dp
import time
from openerp.exceptions import except_orm, Warning, RedirectWarning
import itertools

class account_invoice_ext_api(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    _order = "id desc"

    # @api.one
    # def _get_responsable_siif_editable(self):
    #     res = {}
    #     # in_grp = self.env['res.users'].has_group('grp_seguridad.grp_compras_apg_Responsable_SIIF')
    #     in_grp = self.env.user.has_group('grp_seguridad.grp_compras_apg_Responsable_SIIF')
    #     self.responsable_siif_editable = in_grp and self.state in ('sice')

    @api.one
    @api.constrains('date_invoice','date_due','entry_date')
    def _check_fechas(self):

        # if self.date_invoice and self.date_due and self.type and (self.date_invoice > self.date_due) and (self.type != 'in_refund'):
        if self.date_invoice and self.date_due and self.type and (self.date_invoice > self.date_due) and (self.type == 'in_invoice'):
            raise exceptions.ValidationError('La fecha de vencimiento no puede ser menor a la fecha de factura')

        # if self.entry_date and self.date_due and self.type and (self.entry_date > self.date_due) and (self.type != 'in_refund'):
        if self.entry_date and self.date_due and self.type and (self.entry_date > self.date_due) and (self.type == 'in_invoice'):
            raise exceptions.ValidationError('La fecha de vencimiento no puede ser menor a la fecha de asiento')

        if self.date_invoice and self.entry_date and (self.date_invoice > self.entry_date):
            raise exceptions.ValidationError('La fecha de asiento no puede ser menor a la fecha de factura')

    @api.multi
    @api.depends('currency_id','company_currency_id')
    def _get_dif_currency_fnc(self):
        for invoice in self:
            invoice.diferent_currency = invoice.currency_id.id != self.env.user.company_id.currency_id.id and True or False

    # modificacion ap_01 de lineas a cabezal - Pasado a nueva API
    orden_compra_id = fields.Many2one('purchase.order', string=u'Nº OC', store=True, ondelete='restrict')

    tipo_de_cambio = fields.Float(string='Tipo de cambio', store=True, digits=(10, 5))

    notas_credito_ids = fields.One2many('account.invoice','factura_original', string=u'Notas de crédito')

    # responsable_siif_editable = fields.Boolean(compute='_get_responsable_siif_editable',string='Responsable Siif editable')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        # ('confirmed',u'Confirmado/a'),
        # 001-Inicio
        ('sice', u'Confirmada'),
        # 001-Fin
        ('cancel_sice', u'Anulado SICE'),
        # Nuevos estados para la OPI
        ('in_approved', u'En Aprobación'),
        ('approved', u'Aprobado'),
        ('in_auth', u'En Autorización'),  # in authorization
        ('authorized', u'Autorizado'),
        # estandar
        ('open', 'Open'),  # estandar-cambiano orden 24/09
        ('intervened', u'Intervenida'), # agregado
        ('prioritized', u'Priorizada'), # agregado
        ('cancel_siif', u'Anulado SIIF'), # agregado
        # Anular Obligacion = a estado Anulado SIIF  ('cancel_forced',u'Anulado Obligación')
        # estandar
        ('paid', 'Paid'),  # estandar
        ('forced', u'Obligado'),  # agregado
        ('cancel', 'Cancelled'),  # estandar
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' when invoice is in Pro-forma status,invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user create invoice,a invoice number is generated.Its in open status till user does not pay invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

    @api.multi
    @api.depends('orden_compra_id')
    def get_attachments_docs(self):
        pool_po = self.env['purchase.order']
        pool_invoice = self.env['account.invoice']
        pool_voucher = self.env['account.voucher']
        pool_adj = self.env['grp.cotizaciones']
        for inv in self:
            domain = False
            solicitudes = []
            srs = []
            if inv.orden_compra_id:
                for linea in inv.orden_compra_id.pedido_compra_id.lineas_ids:
                    if linea.solicitud_compra_id:
                        solicitudes.append(linea.solicitud_compra_id.id)
                        srs.append(linea.solicitud_compra_id.solicitud_recursos_id.id)
                po_ids = pool_po.suspend_security().search([('pedido_compra_id', '=', inv.orden_compra_id.pedido_compra_id.id), ('state', 'not in', ['cancel'])])
                inv_ids = pool_invoice.suspend_security().search([('orden_compra_id', 'in', po_ids.ids), ('state', 'not in', ['cancel', 'cancel_siif', 'cancel_sice'])])
                av_ids = pool_voucher.suspend_security().search([('invoice_id', 'in', inv_ids.ids),('state', 'not in', ['cancel'])])
                adj_ids = pool_adj.suspend_security().search([('pedido_compra_id', '=', inv.orden_compra_id.pedido_compra_id.id), ('state', 'not in', ['cancelado'])])
                # if len(solicitudes):
                domain = ['|','|','|','|','|','|', '|', '&', ('res_id', '=', inv.id), ('res_model', '=', 'account.invoice'),
                          '&', ('res_id', '=', inv.orden_compra_id.pedido_compra_id.id), ('res_model', '=', 'grp.pedido.compra'),
                          '&', ('res_id', 'in', solicitudes), ('res_model', '=', 'grp.solicitud.compra'),
                          '&', ('res_id', 'in', srs), ('res_model', '=', 'grp.compras.solicitud.recursos.almacen'),
                          '&', ('res_id', 'in', po_ids.ids), ('res_model', '=', 'purchase.order'),
                          '&', ('res_id', 'in', inv_ids.ids), ('res_model', '=', 'grp.compras.apg'),
                          '&', ('res_id', 'in', av_ids.ids), ('res_model', '=', 'account.voucher'),
                          '&', ('res_id', 'in', adj_ids.ids), ('res_model', '=', 'grp.cotizaciones'),
                          ]

            if not domain:
                domain = [('res_id', '=', inv.id), ('res_model', '=', 'account.invoice')]
            docs = self.env['ir.attachment'].search(domain)
            inv.attachment_ids = docs.ids

    attachment_ids = fields.Many2many(compute='get_attachments_docs',
                                      comodel_name='ir.attachment',
                                      string=u'Documentos asociados')
    nro_factura_grp = fields.Char(size=64, string=u'Número Factura', readonly=True)

    doc_type = fields.Selection([
        ('opi_invoice', u'Factura OPI'),
        ('obligacion_invoice', u'Obligación'),
        ('pasarela_invoice', u'Pasarela'),
        ('3en1_invoice', u'TresEnUno'),
        ('ajuste_invoice', u'Ajuste Obligación'),
        ('invoice', u'Factura')
    ], string=u'Tipo Documento', index=True, readonly=True, select=True, change_default=True, track_visibility='always')

    # Redefiniendo campo para limitar tamaño a 8 caracteres que requiere siif
    supplier_invoice_number = fields.Char(string='Supplier Invoice Number', size=8,
        help="The reference of this invoice as provided by the supplier.",
        readonly=True, states={'draft': [('readonly', False)]})

    diferent_currency = fields.Boolean('Diferencia moneda', compute='_get_dif_currency_fnc')


    @api.model
    def prepare_voucher_data(self, invoice, journal, date, amount):
        voucher_data = super(account_invoice_ext_api, self).prepare_voucher_data(invoice, journal, date, amount)
        voucher_data.update({'operating_unit_id': invoice.operating_unit_id.id})
        return voucher_data

    @api.multi
    def name_get(self):
        # Se pasa el superuser por tema de pagos entre operating units
        self = self.sudo()
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Supplier Invoice'),
            'out_refund': _('Refund'),
            'in_refund': _('Ajuste de obligación'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s %s" % (inv.nro_factura_grp or TYPES[inv.type], inv.name or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('nro_factura_grp', operator, name)] + args, limit=limit)
            if not recs:
                recs = self.search([('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if self._context.get('active_model', '') in ['account.invoice'] and self._context.get('active_ids', False) and self._context['active_ids']:
            # invoice = self.pool.get(context['active_model']).read(cr, uid, context['active_ids'], ['doc_type'])[0]
            # invoice = self.read(['doc_type'])
            invoice = self.env['account.invoice'].browse(self._context['active_ids'])
            if view_type == 'form':
                if self._context.get('type') and self._context['type'] in ('in_invoice', 'in_refund'):
                    if invoice['doc_type']== 'invoice':
                        view_id = self.env['ir.ui.view'].search([('name','=','account.invoice.supplier.form')])[0].id
                    elif invoice['doc_type']== 'obligacion_invoice':
                        view_id = self.env['ir.ui.view'].search([('name','=','account.invoice.supplier.form.obligacion')])[0].id
                    elif invoice['doc_type']== '3en1_invoice':
                        view_id = self.env['ir.ui.view'].search([('name','=','account.invoice.supplier.form.obligacion')])[0].id
                    else:
                        view_id = self.env['ir.ui.view'].search([('name','=','account.invoice.supplier.form')])[0].id
        res = super(account_invoice_ext_api, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return res

    #TODO: Ver de mojorar esta funcion
    @api.multi
    def onchange_orden_compra(self, orden_compra_id=False):
        # context = dict({})
        ctx = dict(self._context)
        # result = {}
        # result.setdefault('value', dict({}))

        if not orden_compra_id:
            return {'value': {
                'origin': False,
                'invoice_line': False,
            }}

        # Inicializando
        result = {'value': {
            'origin': False,
            'operating_unit_id':orden_compra_id.operating_unit_id.id,
            # 'beneficiario_siif_id': False,
            'invoice_line': False,
        }}

        lines = []

        if orden_compra_id:
            orden = self.env['purchase.order'].browse(orden_compra_id)

        # orden = orden_obj.browse(cr, uid, orden_compra_id, context=context)
        if orden:
            result['value'].update({ 'origin': orden.name or False,})
            result['value'].update({'cod_moneda': orden.cod_moneda.id or False,})
            # Cambios 11/05
            if orden.order_line:
                for line in orden.order_line:
                    a = False
                    if line.product_id:
                        # res = self.pool.get('product.product').browse(cr, uid, line.product_id.id, context=context)
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
                    }))
                result['value'].update({'invoice_line': lines})
            result['value'].update({
                'orden_compra_id': orden_compra_id,
                'operating_unit_id': orden.operating_unit_id.id
            })
            # res['value'].update({'nro_afectacion': apg.nro_afectacion_siif  or False, 'monto_afectado': apg.monto_divisa or 0.0})
            return result

    # integrado al workflow nuevo  1er metodo
    @api.multi
    def action_cancel_paid(self):
        ctx = dict(self._context)
        ids = [x.id for x in self]
        return self.cancel_pagos_factura()
        # return True

    @api.multi
    def onchange_journal_id(self, journal_id=False):
        if self and self.state not in ('draft') and journal_id:
            values = {'value': {'journal_id': journal_id}}
            return values
        return super(account_invoice_ext_api, self).onchange_journal_id(journal_id)

    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default.update({'nro_factura_grp': False})
        return super(account_invoice_ext_api, self).copy(default)

    @api.multi
    def _remove_move_reconcile(self):
        for invoice in self:
            for line in invoice.move_id.line_id:
                # refresh to make sure you don't unreconcile an already unreconciled entry
                line.refresh()
                if line.reconcile_id:
                    move_lines = self.env['account.move.line']
                    for move_line in line.reconcile_id.line_id:
                        if move_line.id == line.id:
                            continue
                        move_lines |= move_line
                    line.reconcile_id.unlink()
                    if len(move_lines) >= 2:
                        move_lines.reconcile_partial('auto')
                if line.reconcile_partial_id:
                    move_lines = self.env['account.move.line']
                    for move_line in line.reconcile_partial_id.line_partial_ids:
                        if move_line.id == line.id:
                            continue
                        move_lines |= move_line
                    line.reconcile_partial_id.unlink()
                    if len(move_lines) >= 2:
                        move_lines.reconcile_partial('auto')
        return True

    @api.multi
    def action_cancel(self):
        AccountMoveLine = self.env['account.move.line']
        period_id = self.env['account.period'].find(fields.Date.today()).id
        for inv in self:
            if inv.payment_ids:
                for move_line in inv.payment_ids:
                    if move_line.reconcile_partial_id.line_partial_ids:
                        raise exceptions.ValidationError(_('You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))

            if inv.move_id:
                if not inv.move_id.journal_id.update_posted:
                    raise exceptions.ValidationError(_('You cannot modify a posted entry of this journal.\nFirst you should set the journal to allow cancelling entries.'))
                # irabaza: Invalidate the move(s)
                # Do not delete moves, instead we must unreconcile move lines
                lines = AccountMoveLine.search([('move_id', '=', inv.move_id.id)])
                inv._remove_move_reconcile()
                if inv.move_id.reversal_id:
                    # Reversal move have been already created
                    reversal_move_ids = [ inv.move_id.reversal_id.id ]
                else:
                    # Create reverse entries
                    reversal_move_ids = inv.move_id.create_reversals(fields.Date.today(), reversal_period_id=period_id)
                reversal_lines = AccountMoveLine.search([('move_id', 'in', reversal_move_ids)])
                # Reconcile entries
                lines2rec = AccountMoveLine.browse()
                for line in itertools.chain(lines, reversal_lines):
                    if line.account_id.id == inv.account_id.id:
                        lines2rec += line
                if lines2rec:
                    lines2rec.reconcile('manual', writeoff_journal_id=inv.journal_id.id, writeoff_period_id=period_id)

                # RAGU: RECONCILE RETENTIONS
                retentions_accounts = []
                for retention_line in inv.invoice_ret_global_line_ids:
                    retentions_accounts.append(retention_line.account_id.id)
                for retention_line in inv.invoice_ret_line_ids:
                    retentions_accounts.extend([x.account_id.id for x in retention_line.retention_line_ret_ids])
                for retention_line in inv.invoice_ret_irpf_lines:
                    retentions_accounts.append(retention_line.retention_id.account_id.id)

                lines_union_reversal_lines = lines + reversal_lines
                for retentions_account in set(retentions_accounts):
                    lines2rec = lines_union_reversal_lines.filtered(lambda x: x.account_id.id == retentions_account)
                    if lines2rec:
                        lines2rec.reconcile('manual', writeoff_journal_id=inv.journal_id.id, writeoff_period_id=period_id)

        # Set the invoices as cancelled and detach the move ids
        self.write({'state': 'cancel', 'move_id': False})
        self._log_event(-1.0, 'Cancel Invoice')
        return True

class account_invoice_line_ext_api(models.Model):
    _inherit = "account.invoice.line"
    _name = "account.invoice.line"

    @api.one
    @api.depends('price_unit','discount','invoice_line_tax_id','quantity',
                 'price_subtotal','invoice_id.date_invoice','invoice_id.currency_id','invoice_id.company_id','invoice_id.partner_id')
    def _calcularmontobase(self):
        if self.invoice_id.state == 'draft':
            if self.invoice_id.currency_id and self.invoice_id.company_id.currency_id and self.invoice_id.currency_id.id != self.invoice_id.company_id.currency_id.id:
                ctx = dict(self._context, lang=self.invoice_id.partner_id.lang)
                ctx.update({'date': self.invoice_id.date_invoice or time.strftime('%Y-%m-%d')})
                self.monto_moneda_base = self.invoice_id.currency_id.with_context(ctx).compute(self.price_subtotal,self.invoice_id.company_id.currency_id)
            else:
                self.monto_moneda_base = self.price_subtotal
        else:
            if isinstance(self.id, int):
                _sql = """SELECT monto_moneda_base FROM account_invoice_line WHERE id = %s LIMIT 1""" % (self.id)
                self._cr.execute(_sql)
                _dict = self._cr.dictfetchall()
                self.monto_moneda_base = _dict[0]['monto_moneda_base']
            # else:
            #     self.monto_moneda_base = self.price_subtotal

    # 102 - Onchange carga
    @api.one
    @api.depends('product_id')
    def _es_activo_fijo(self):
        self.product_es_activo_fijo = self.product_id.categ_id.activo_fijo

    monto_moneda_base = fields.Float(string='Monto moneda base', digits=dp.get_precision('Account'), store=True, compute='_calcularmontobase', default=0.0)

    # 102 - Onchange carga - Nuevo Campo
    product_es_activo_fijo = fields.Boolean(string='Es activo fijo', store=True, compute='_es_activo_fijo')

    # 003 Incidencia 170, solo 2 decimales en campo cantidad - Original precision(Product Unit of Measure)
    # quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product Price'), required=True, default=1)
    #para enviar a SICE, precio unitario sin IVA
    precio_sin_iva = fields.Float('Precio sin IVA', digits_compute=(16,4),
                                  compute='_compute_precio_sin_iva')
    invoice_state = fields.Selection(string="Invoice state", related='invoice_id.state', readonly=1)

    @api.depends('price_unit', 'invoice_line_tax_id','price_subtotal')
    def _compute_precio_sin_iva(self):
        for line in self:
            # taxes = line.invoice_line_tax_id.compute_all(line.price_unit, 1, product=line.product_id,
            #                                   partner=line.invoice_id.partner_id)
            # line.precio_sin_iva = taxes['total']
            res = round(line.price_subtotal / line.quantity, 4)
            line.precio_sin_iva = res

    # 102 - Onchange carga - Nuevo Metodo
    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
                          partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
                          company_id=None):
        res = super(account_invoice_line_ext_api, self).product_id_change(product, uom_id, qty=0, name=name, type=type,
                                                                          partner_id=partner_id, fposition_id=fposition_id,
                                                                          price_unit=price_unit, currency_id=currency_id,
                                                                          company_id=company_id)

        context = self._context
        company_id = company_id if company_id is not None else context.get('company_id', False)
        self = self.with_context(company_id=company_id, force_company=company_id)

        if not partner_id:
            raise except_orm(_('No Partner Defined!'), _("You must first select a partner!"))
        if not product:
            if type in ('in_invoice', 'in_refund'):
                return {'value': {}, 'domain': {'product_uom': []}}
            else:
                return {'value': {'price_unit': 0.0}, 'domain': {'product_uom': []}}

        part = self.env['res.partner'].browse(partner_id)
        if part.lang:
            self = self.with_context(lang=part.lang)
        product = self.env['product.product'].browse(product)

        res['value'].update({'product_es_activo_fijo': product.categ_id.activo_fijo})
        return res

class account_invoice_tax_ext_api(models.Model):
    _inherit = "account.invoice.tax"

    @api.one
    @api.depends('amount','invoice_id.date_invoice','invoice_id.currency_id','invoice_id.company_id','invoice_id.partner_id')
    def _calcularimpuestomoneda(self):
        if self.invoice_id.currency_id and self.invoice_id.company_id.currency_id and self.invoice_id.currency_id.id != self.invoice_id.company_id.currency_id.id:
            ctx = dict(self._context, lang=self.invoice_id.partner_id.lang)
            ctx.update({'date': self.invoice_id.date_invoice or time.strftime('%Y-%m-%d')})
            self.impuesto_moneda_base = self.invoice_id.currency_id.with_context(ctx).compute(self.amount, self.invoice_id.company_id.currency_id)
        else:
            self.impuesto_moneda_base = self.amount

    impuesto_moneda_base = fields.Float(compute='_calcularimpuestomoneda', string='Impuesto moneda base', default=0.0)

class AccountInvoiceLineInherited(models.Model):
    _inherit = 'account.invoice.line'

    order_lines = fields.Many2many(comodel_name='purchase.order.line', relation='purchase_order_line_invoice_rel',
                                   column1='invoice_id', column2='order_line_id', string=u'Order Lines',
                                   readonly=True, copy=False)

