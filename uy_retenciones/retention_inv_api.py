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
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, Warning, RedirectWarning


class account_invoice_line_ext_api(models.Model):
    _inherit = 'account.invoice.line'

    @api.multi
    def write(self, values):
        res = super(account_invoice_line_ext_api, self).write(values)
        tax_ret_lines_del = []
        obj_retline = self.env['account.retention.line']
        for record in self:
            for tax in record.invoice_line_tax_id:
                tax_ret_lines_del.append(tax.id)
            id_rlines = obj_retline.search([('line_id', '=', record.id), ('tax_id', 'not in', tax_ret_lines_del)])
            if id_rlines:
                id_rlines.unlink()
        return res


account_invoice_line_ext_api()


class account_invoice_ext_api(models.Model):
    _inherit = 'account.invoice'

    # OTRS para modificacion de retenciones Inicio
    @api.multi
    def write(self, values):
        obj_retline = self.env['account.retention.line']
        if values.get('invoice_line', False):
            lines = values.get('invoice_line', False)
            tax_ret_lines_del = []
            for line in lines:
                if len(line) > 1 and line[2] and 'invoice_line_tax_id' in line[2] and line[2]['invoice_line_tax_id']:
                    elim = False
                    for tax_modif in line[2]['invoice_line_tax_id']:
                        if tax_modif[0] == 6:
                            tax_ret_lines_del = [x for x in tax_modif[2]]
                            elim = True
                    # delete retencion line tax
                    id_rlines = False
                    if line[1]:  # id_line
                        id_rlines = obj_retline.search(
                            [('line_id', '=', line[1]), ('tax_id', 'not in', tax_ret_lines_del)])
                    if not id_rlines and elim:
                        id_rlines = obj_retline.search([('line_id', '=', line[1])])
                    if id_rlines:
                        id_rlines.unlink()
        return super(account_invoice_ext_api, self).write(values)

    # @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount', 'invoice_line.invoice_line_tax_id')
    def _compute_amount(self):
        for self_obj in self:
            self_obj.amount_untaxed = sum(line_inv.price_subtotal for line_inv in self_obj.invoice_line)
            self_obj.amount_tax = sum(line_inv.amount for line_inv in self_obj.tax_line)

            obj_retline = self.env['account.retention.line']
            obj_retline_irpf = self.env['account.retention.line.irpf']

            ctx = dict(self._context, lang=self_obj.partner_id.lang)
            sum_retenciones_lines = 0.0
            sum_ret_global_lines = 0.0
            irpf_retention_ids = []

            for ret_global_line in self_obj.invoice_ret_global_line_ids:
                sum_ret_global_lines += ret_global_line.amount_ret

            # Retenciones IRPF
            sum_ret_irpf = 0.0
            for ret_irpf_line in self_obj.invoice_ret_irpf_lines:
                sum_ret_irpf += ret_irpf_line.amount_ret

            if self_obj.currency_id:
                retline_irpf_objs = obj_retline_irpf.search([('invoice_id', '=', self_obj.id)]).ids
                currency = self_obj.currency_id.with_context(date=self_obj.date_invoice or fields.Date.context_today(self_obj))
                taxes = False
                for line in self_obj.invoice_line:
                    taxes = line.invoice_line_tax_id.compute_all((line.price_unit * (1 - (line.discount or 0.0) / 100.0)),
                                                                 line.quantity, line.product_id, self_obj.partner_id)['taxes']

                    for tax in taxes:
                        amount_ret = 0.0
                        val = {
                            'invoice_id': self_obj.id,
                            'name': tax['name'],
                            'amount': tax['amount'],
                            'base': currency.round(tax['price_unit'] * line['quantity']),
                        }
                        #MVARELA 01/11/2017: se modifica por problema de signo en notas de credito
                        # if self_obj.type in ('out_invoice', 'in_invoice'):
                        #     val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], currency, round=False)
                        #     val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], currency, round=False)
                        # else:
                        #     val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], currency, round=False)
                        #     val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], currency, round=False)
                        val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], currency, round=False)
                        val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], currency, round=False)

                        # Base calculo retencion IVA
                        base_retax = val and val['tax_amount'] or 0.0
                        base_ret_line = val and val['base'] or 0.0
                        rdata = {
                            'line_id': line.id,
                            'invoice_id': self_obj.id,
                            'tax_id': tax and tax['id'] or False,  # id del impuesto
                            'base_retax': base_retax,  # base calculo impuesto
                            'base_ret_line': base_ret_line,  # base calculo impuesto
                            'amount_ret': amount_ret}

                        id_rlines = obj_retline.search([('line_id', '=', line.id), ('tax_id', '=', tax['id'])])

                        ret_id = 0
                        if id_rlines:
                            # Variante 1
                            ctx['line_id'] = line
                            id_rlines[0].write(rdata)

                            # Variante 3 with context
                            ret_id = id_rlines[0]
                        elif line.id and self_obj.state in ('draft', 'sice', 'authorized'):
                            # TODO SPRING 8 GAP 62.A R
                            retention_ids = self_obj.partner_id.retention_ids.filtered(lambda x: not x.es_irpf_porciento).ids
                            retention_ids.extend(line.product_id.product_tmpl_id.prod_tmpl_ret_ids.filtered(
                                lambda x: not x.es_irpf_porciento).ids)
                            retention_ids = dict.fromkeys(retention_ids).keys()
                            rdata.update({
                                'retention_line_ret_ids': [(6, 0, retention_ids)],
                            })

                            ret_id = obj_retline.create(rdata)
                        if ret_id:
                            if ret_id.amount_ret > 0:
                                sum_retenciones_lines += ret_id.amount_ret
                    # if not retline_irpf_objs:
                    # TODO SPRING 8 GAP 62.A R buscando retenciones  IRPF en los productos
                    irpf_retention_ids = line.product_id.product_tmpl_id.prod_tmpl_ret_ids.filtered(
                        lambda x: x.es_irpf_porciento).ids

                # TODO SPRING 8 GAO 62.A R
                # de no encontrarse IRPF en las lineas de los productos buscar en el partner
                if len(retline_irpf_objs) > 0:
                    retline_irpf_objs = retline_irpf_objs[0]
                if not retline_irpf_objs:
                    if not len(irpf_retention_ids):
                        irpf_retention_ids = self_obj.partner_id.retention_ids.filtered(lambda x: x.es_irpf_porciento).ids
                    self_obj.invoice_ret_irpf_lines.write({'retention_id': irpf_retention_ids[0] if len(irpf_retention_ids) else False})

                self_obj.amount_subttal_lines_ret = sum_retenciones_lines or 0.0
                self_obj.amount_subttal_irpf_ret = sum_ret_irpf or 0.0  # irpf
                self_obj.amount_subttal_global_inv_ret = sum_ret_global_lines or 0.0
                self_obj.amount_total_retention = sum_retenciones_lines + sum_ret_global_lines + sum_ret_irpf
                ttret = sum_retenciones_lines + sum_ret_global_lines + sum_ret_irpf
                amount_ttal = self_obj.amount_tax + self_obj.amount_untaxed - ttret
                self_obj.amount_total = amount_ttal

    @api.model
    def create(self, fields):
        if 'invoice_ret_irpf_lines' in fields and fields['invoice_ret_irpf_lines'] == []:
            partner_id = fields['partner_id']
            pool_prod = self.env['product.product']
            irpf_id = False
            for line in fields['invoice_line']:
                prod_id = line[2]['product_id']
                irpf_retention_ids = pool_prod.browse(prod_id).product_tmpl_id.prod_tmpl_ret_ids.\
                    filtered(lambda x: x.es_irpf_porciento).ids
                if not len(irpf_retention_ids):
                    irpf_retention_ids = self.env['res.partner'].browse(partner_id).retention_ids.\
                        filtered(lambda x: x.es_irpf_porciento).ids
                if irpf_retention_ids and not irpf_id:
                    irpf_id = irpf_retention_ids[0]
            fields['invoice_ret_irpf_lines'].append((0, 0, {'retention_id': irpf_id}))
        return super(account_invoice_ext_api, self).create(fields)

    amount_subttal_lines_ret = fields.Float(string=u'Subtotal retenciones líneas', digits=dp.get_precision('Account'),
                                            store=True, readonly=True, compute='_compute_amount', default=0.0)

    amount_subttal_global_inv_ret = fields.Float(string=u'Subtotal retenciones global',
                                                 digits=dp.get_precision('Account'),
                                                 store=True, readonly=True, compute='_compute_amount', default=0.0)

    amount_total_retention = fields.Float(string=u'Total a retener', digits=dp.get_precision('Account'),
                                          store=True, readonly=True, compute='_compute_amount', default=0.0)
    # Retenciones IRPF
    amount_subttal_irpf_ret = fields.Float(compute='_compute_amount', store=True, digits=dp.get_precision('Account'),
                                           string=u'Subtotal retenciones IRPF', default=0.0)



    @api.multi
    def check_tax_lines(self, compute_taxes):
        self.button_reset_taxes()
        return super(account_invoice_ext_api, self).check_tax_lines(compute_taxes)

    @api.multi
    def button_reset_taxes(self):
        summary_ret_obj = self.pool.get('account.invoice.summary.ret')
        summary_group_ret_obj = self.pool.get('account.invoice.summary.group.ret')
        # summary_ret_obj = self.env['account.invoice.summary.ret']
        # account_invoice_tax = self.env['account.invoice.tax']
        ctx = dict(self._context)
        for invoice in self:
            self._cr.execute("DELETE FROM account_invoice_summary_ret WHERE invoice_id=%s", (invoice.id,))
            self._cr.execute("DELETE FROM account_invoice_summary_group_ret WHERE invoice_id=%s", (invoice.id,))
            self.invalidate_cache()
            partner = invoice.partner_id
            if partner.lang:
                ctx['lang'] = partner.lang

            values_invoice = summary_ret_obj.compute(self._cr, self._uid, invoice.id, ctx)
            values_group_ret = summary_group_ret_obj.compute(self._cr, self._uid, invoice.id, ctx)

            computes = values_invoice.values()
            for summ_ret in computes:
                summary_ret_obj.create(self._cr, self._uid, summ_ret, ctx)

            # Valores del resumen de tabla retenciones por grupo
            computes_group = values_group_ret.values()
            for summ_group_ret in computes_group:
                summary_group_ret_obj.create(self._cr, self._uid, summ_group_ret, ctx)

            # llamada a crear lineas de retencion
            self.irpf_retention_lines()
        # llamada al principal
        return super(account_invoice_ext_api, self).button_reset_taxes()

    @api.multi
    def action_move_create(self):
        if self.check_invoice_retentions():
            return self.action_move_create_with_retention()
        return super(account_invoice_ext_api, self).action_move_create()

    @api.multi
    def check_invoice_retentions(self):
        for inv in self:
            if inv.invoice_ret_lines:
                return True
        return False

    # 004 - Inicio creacion
    @api.multi
    def irpf_retention_lines(self):
        # obj_ret_irpf_line = self.pool.get('account.retention.line.irpf')
        obj_ret_irpf_line = self.env['account.retention.line.irpf']
        # Type = in_invoice  > Factura de proveedor
        state_inv = False
        moneda_base = False

        date_invoice = fields.Date.context_today(self)
        date_ui = fields.Date.context_today(self)

        # 1 - Buscar Facturas que coincidan con criterios de factura actual
        for inv1 in self:
            # Fecha en contexto para factura actual
            # ctx.update({'date': inv1.date_invoice or time.strftime('%Y-%m-%d')})
            date_invoice = inv1.date_invoice or fields.Date.context_today(self)
            # Contexto con fecha del tipo de cambio para UI
            # ctx_ui.update({'date': inv1.fecha_tc_rate_ui})
            date_ui = inv1.fecha_tc_rate_ui
            moneda_base = inv1.company_id and inv1.company_id.currency_id
            state_inv = inv1.state in ('draft', 'sice', 'authorized') and True or False
            # Cuando es fondo rotatorio, cambio 15/01 CAMBIO SE AGREGA A INTEGRACION SIIF
            # if state_inv == True and inv1.tipo_ejecucion_codigo_rel =='P':
            #     state_inv = False
            # facturas_pen_ids = self.search(cr, uid, [('move_id','>',0),('es_cancilleria','=',True),('doc_type','=',inv1.doc_type),('type','=',inv1.type),('partner_id','=',inv1.partner_id.id)])
            facturas_pen_ids = self.search(
                [('id', '!=', inv1.id), ('move_id', '!=', False), ('period_id', '=', inv1.period_id.id),
                 ('doc_type', '=', inv1.doc_type), ('type', '=', inv1.type), ('partner_id', '=', inv1.partner_id.id)])


        # 2 - Se calcula el saldo pendiente segun las facturas devueltas en el periodo
        suma_ret = 0.0
        suma_ret_mon_origen = 0.0
        suma_base = 0.0
        ret_id = False
        # for fact in self.browse(cr, uid, facturas_pen_ids):
        if facturas_pen_ids:
            # for fact in self.browse(facturas_pen_ids):
            for fact in facturas_pen_ids:
                for line_r in fact.invoice_ret_irpf_lines:
                    if line_r.type == 'local' and line_r.retention_id:
                        if not ret_id:
                            ret_id = line_r.retention_id.id
                        suma_ret_mon_origen += round(line_r.base_amount_pend) - round(line_r.base_amount)
                        # La suma se calcula siempre en pesos
                        suma_ret += round(line_r.base_amount_pend_pesos) - round(line_r.base_amount_pesos)
                        suma_base += round(line_r.base_amount_pend_pesos)
                    elif line_r.type == 'externo' and line_r.retention_id:
                        if not ret_id:
                            ret_id = line_r.retention_id.id

        cant_limite = 30000  # 10 000 UI Convertir a pesos
        # Convertir UI A pesos

        # 3 - Validacion de existencia de Unidad Indexada
        # Unidad Indexada
        # currency_obj = self.pool.get('res.currency')
        currency_obj = self.env['res.currency']
        ui_currency_id = currency_obj.search([('name', '=', 'UI')], limit=1)
        if not ui_currency_id:
            raise except_orm(_('Error!'),
                             _(u'Deberá cargar la moneda Unidad Indexada.'))
        # 4 - Conversion de la unidad indexada a pesos para comprobacion de limites
        if ui_currency_id:
            # cant_limite = currency_obj.compute(cr, uid, ui_currency_id, moneda_base, float(10000), context=ctx_ui)
            currency = currency_obj.browse(ui_currency_id.id)
            currency = currency.with_context(date=date_ui)
            cant_limite = currency.compute(float(10000), moneda_base, round=False)
        # PENDIENTE DEFINICION DE CALCULO EN PESOS Y/O DOLARES
        # 5 - Busqueda y validacion de cantidades para creacion de IRPF si corresponde
        for inv in self:

            if inv.invoice_ret_line_ids:
                amount = 0.0
                sum_ret_currency = 0.0
                for line in inv.invoice_ret_line_ids:
                    amount += round(line.base_ret_line)

                amount_base = amount
                # Si factura no es Moneda Base, se convierte a base para la validacion de 10 000
                change_currency = False
                if inv.currency_id != moneda_base:
                    currency_inv = currency_obj.browse(inv.currency_id.id)
                    currency_inv = currency_inv.with_context(date=inv.date_invoice or fields.Date.context_today(self))
                    amount_base = currency_inv.compute(amount, moneda_base)

                    currency_mb = currency_obj.browse(moneda_base.id)
                    currency_mb = currency_mb.with_context(date=inv.date_invoice or fields.Date.context_today(self))

                    sum_ret_currency = currency_mb.compute(suma_ret, inv.currency_id)
                    change_currency = True

                # Si se supera el limite, comparacion en moneda base (UYU)
                # MVARELA: Se suman las bases para ver si se manda, no los pendientes
                # if suma_ret + amount_base > cant_limite:
                if suma_base + amount_base > cant_limite:
                    # Si entra aca, es porque supero el limite, siempre se guarda
                    # amount_local = suma_ret + amount > cant_limite:
                    # 1----- Creando el local
                    # Cantidad pendiente es Falso, pues se pasa del limite de UI  (10 000)
                    data_line = {
                        'invoice_id': inv.id,
                        'base_amount': change_currency and sum_ret_currency + amount or suma_ret + amount_base,
                        'base_amount_pend': change_currency and amount or amount_base,  # ACA ERROR, debe ser cero
                        # 'amount_ret':
                        # 'amount_ret_pendiente':
                        'pendiente': False,
                        # 'retention_id': ,
                        'description': 'Local',
                        'type': 'local',
                        'partner_id': inv.partner_id.id,
                    }
                    id_rlines = obj_ret_irpf_line.search([('invoice_id', '=', inv.id), ('type', '=', 'local')])
                    if id_rlines:
                        # rlines = obj_ret_irpf_line.browse(id_rlines[0])
                        id_rlines.write(data_line)
                        # obj_ret_irpf_line.write(data_line)
                    # elif invoice.state == 'draft': #COMENTADO MVARELA 18-11-2015, se agrega estado SICE
                    elif state_inv:
                        obj_ret_irpf_line.create(data_line)

                    aplica_irpf_local = obj_ret_irpf_line.search([('invoice_id', '=', inv.id), ('type', '=', 'local'), ('retention_id','!=',False)],limit=1)
                    # 2---- Para el externo, las otras facturas
                    if aplica_irpf_local and suma_ret > 0 and suma_ret + amount_base > cant_limite:
                        data_line1 = {
                            'invoice_id': inv.id,
                            'base_amount': 0.0,
                            'base_amount_pend': change_currency and sum_ret_currency or suma_ret,
                            'description': 'Externo',
                            'retention_id': ret_id,
                            'pendiente': False,
                            'type': 'externo',
                            'partner_id': inv.partner_id.id,
                        }
                        id_ext_rlines = obj_ret_irpf_line.search(
                            [('invoice_id', '=', inv.id), ('type', '=', 'externo')])
                        if id_ext_rlines and id_ext_rlines[0]:
                            # ext_rlines = obj_ret_irpf_line.browse(id_ext_rlines[0])
                            id_ext_rlines.write(data_line1)
                        elif state_inv:
                            obj_ret_irpf_line.create(data_line1)

                    # MVARELA 03/08/2016: Se crea la linea con monto negativo cuando retuve de mas
                    elif aplica_irpf_local and suma_ret < 0:
                        data_line1 = {
                            'invoice_id': inv.id,
                            'base_amount': 0.0,
                            'base_amount_pend': change_currency and sum_ret_currency or suma_ret,
                            'description': 'Externo',
                            'retention_id': ret_id,
                            'pendiente': False,
                            'type': 'externo',
                            'partner_id': inv.partner_id.id,
                            # 'suma_redondeo_perdido' : suma_redondeos_pendientes,
                        }
                        id_ext_rlines = obj_ret_irpf_line.search([('invoice_id', '=', inv.id), ('type', '=', 'externo')])
                        if id_ext_rlines and id_ext_rlines[0]:
                            id_ext_rlines.write(data_line1)
                        elif state_inv:
                            obj_ret_irpf_line.create(data_line1)

                else:
                    # 1----- Creando el local y queda pendiente. Siempre en la moneda de la factura
                    data_line = {
                        'invoice_id': inv.id,
                        'base_amount': 0.0,
                        'base_amount_pend': amount,
                        'pendiente': True,
                        # 'retention_id': ret_id,
                        'description': 'Local',
                        'type': 'local',
                        'partner_id': inv.partner_id.id,
                    }
                    id_rlines = obj_ret_irpf_line.search([('invoice_id', '=', inv.id), ('type', '=', 'local')])
                    if id_rlines:
                        # ret_irpf_line = obj_ret_irpf_line.browse(id_rlines[0])
                        id_rlines.write(data_line)
                    elif state_inv:
                        obj_ret_irpf_line.create(data_line)

                    # Eliminando las externas en caso que hayan
                    id_ext_rlines = obj_ret_irpf_line.search([('invoice_id', '=', inv.id), ('type', '=', 'externo')])
                    if id_ext_rlines:
                        for ide in id_ext_rlines:
                            ide.unlink()
                            # obj_ret_irpf_line.unlink(cr, uid, id_ext_rlines[0], context)
        return True

    # 003-Inicio ref facturas
    def get_ref(self, inv):
        ref_move = inv.reference or inv.name
        # 002- 08/03 Pendiente refund. Por ahora solo para facturas de proveedor
        if inv.type in ('in_invoice','in_refund'):
            for inv_line in inv.invoice_line:
                ref_move = inv_line.name
                break
        return ref_move

    @api.multi
    def action_move_create_with_retention(self):
        """Creates invoice related analytics and financial move lines"""

        ait_obj = self.env['account.invoice.tax']  # account_invoice_tax
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise except_orm(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise except_orm(_('No Invoice Lines!'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)
            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice

            company_currency = inv.company_id.currency_id
            # create the analytical lines, one move line per invoice line
            iml = inv._get_analytic_lines()
            # check if taxes are all computed
            compute_taxes = ait_obj.compute(inv.with_context(lang=inv.partner_id.lang))
            inv.check_tax_lines(compute_taxes)

            # I disabled the check_total feature
            if self.env['res.users'].has_group('account.group_supplier_inv_check_total'):
                if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (
                            inv.currency_id.rounding / 2.0):
                    raise except_orm(_('Bad Total!'), _(
                        'Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise except_orm(_('Error!'), _(
                        "Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

            # one move line per tax line
            iml += ait_obj.move_line_get(inv.id)

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = inv.number

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, ref, iml)

            name = inv.supplier_invoice_number or inv.name or '/'
            totlines = []
            if inv.payment_term:
                totlines = inv.with_context(ctx).payment_term.compute(total, date_invoice)[0]

            acc_id = inv.account_id.id

            if totlines:
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'ref': ref,
                    })
            else:
                ctx.update({'date': inv.date_invoice})
                # cambios en contabilizacion, echaviano  -- 17/07
                if inv.type in (
                        'in_invoice', 'in_refund') and inv.amount_total_retention > 0 and inv.invoice_ret_lines:
                    # retenciones de lineas de impuestos
                    obj_retline = self.pool.get('account.retention.line')
                    dif_currency_arr = [diff_currency, inv.currency_id.id, company_currency.id]
                    # aca esta el problema del lunes de cambio de moneda
                    total_ret, total_currency_ret, iml_temp = obj_retline.move_line_get_credit(self._cr, self._uid, inv,
                                                                                               ref, inv.id,
                                                                                               dif_currency_arr,
                                                                                               context=ctx)
                    if total_ret != 0:
                        iml += iml_temp
                        total = total - total_ret
                        total_currency = total_currency - total_currency_ret
                        # retenciones globales
                    obj_global_retline = self.pool.get('account.global.retention.line')
                    dif_currency_arr = [diff_currency, inv.currency_id.id, company_currency.id]
                    total_global_ret, total_currency_globlal_ret, iml_gbl_temp = obj_global_retline.move_line_get_credit(
                        self._cr, self._uid, inv, ref, inv.id, dif_currency_arr, context=ctx)
                    if total_global_ret != 0:
                        iml += iml_gbl_temp
                        total = total - total_global_ret
                        total_currency = total_currency - total_currency_globlal_ret

                    # 004 Retenciones IRPF  03/12
                    # 3- retenciones IRPF
                    obj_siif_retline = self.pool.get('account.retention.line.irpf')
                    dif_currency_arr = [diff_currency, inv.currency_id.id, company_currency.id]
                    total_irpf_ret, total_currency_irpf_ret, iml_irpf_temp = obj_siif_retline.move_line_get_credit(
                        self._cr, self._uid, inv, ref, inv.id, dif_currency_arr, context=ctx)
                    if total_irpf_ret != 0:
                        iml += iml_irpf_temp
                        total = total - total_irpf_ret
                        total_currency = total_currency - total_currency_irpf_ret

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': total,
                        'account_id': acc_id,
                        'date_maturity': inv.date_due or False,
                        'amount_currency': diff_currency \
                                           and total_currency or False,
                        'currency_id': diff_currency \
                                       and inv.currency_id.id or False,
                        'ref': ref
                    })
                    # 004 Retenciones IRPF
                # para las facturas de cliente por ahora no -- fin de modificacion
                # para el resto de las facturas
                else:
                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': total,
                        'account_id': acc_id,
                        'date_maturity': inv.date_due or False,
                        'amount_currency': diff_currency \
                                           and total_currency or False,
                        'currency_id': diff_currency \
                                       and inv.currency_id.id or False,
                        'ref': ref
                    })
            # hasta aqui la modificacion, echaviano'ref': ref

            date = date_invoice

            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)

            line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            if journal.centralisation:
                raise except_orm(_('User Error!'),
                                 _(
                                     'You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            # Modificacion
            line = self.modify_move_canc_lines(line)

            line = inv.finalize_invoice_move_lines(line)

            # Agregado modificacion de ref a nivel cabezal
            # 103-llamada metodo para ref
            ref_move = self.get_ref(inv)
            move_date = inv.date_invoice
            if inv.entry_date:
                move_date = inv.entry_date
            move_vals = {
                # 'ref': inv.reference or inv.name, #Estandar
                'ref': ref_move,
                'line_id': line,
                'journal_id': journal.id,
                'date': move_date,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            ctx['company_id'] = inv.company_id.id
            # period = inv.period_id
            # if not period:
            period = self.env['account.period'].with_context(ctx).find(move_date)[:1]
            if period:
                move_vals['period_id'] = period.id
                for i in line:
                    i[2]['period_id'] = period.id

            ctx['invoice'] = inv
            move = account_move.with_context(ctx).create(move_vals)
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'period_id': period.id,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
        self._log_event()
        return True

    # MOdificacion ceros
    @api.multi
    def modify_move_canc_lines(self, move_lines):
        mov_line = []
        account_id = self.env['account.journal'].browse(self.journal_id.id).default_credit_account_id.id
        amount_currency = 0
        for elem in move_lines:
            if self.type in ('out_refund', 'in_refund'):
                if (not elem[2]['credit'] and not elem[2]['debit'] and self.invoice_line[0].price_subtotal > 0):
                    if account_id == elem[2]['account_id']:
                        amount_currency = abs(elem[2]['amount_currency'])
                    else:
                        amount_currency = -abs(elem[2]['amount_currency'])
                    elem[2].update({'amount_currency': amount_currency})
                elif (not elem[2]['credit'] and not elem[2]['debit'] and self.invoice_line[0].price_subtotal < 0):
                    if account_id == elem[2]['account_id']:
                        amount_currency = -abs(elem[2]['amount_currency'])
                    else:
                        amount_currency = abs(elem[2]['amount_currency'])
                    elem[2].update({'amount_currency': amount_currency})
            elif self.type in ('out_invoice', 'in_invoice'):
                if (not elem[2]['credit'] and not elem[2]['debit']):
                    if account_id == elem[2]['account_id']:
                        amount_currency = -abs(elem[2]['amount_currency'])
                    else:
                        amount_currency = abs(elem[2]['amount_currency'])
                    elem[2].update({'amount_currency': amount_currency})
            mov_line.append((0, 0, elem[2]))
        return mov_line

    #     para los pagos

    # sobreescribiendo el primer metodo 1er metodo
    # integrado al workflow nuevo  2do metodo
    @api.multi
    def action_cancel_paid(self):
        # ctx = dict(self._context)
        # ids = [x.id for x in self]
        if self.check_invoice_retentions():
            self.delete_retention_payments()
        return self.cancel_pagos_factura()
        # return self.cancel_pagos_factura(self._cr, self._uid, ids, ctx)

    # eliminar los asientos de las retenciones en caso de cancelar la factura o devolverla a abierta
    # Para devolverla a abierta hay que modificar el workflow de factura de proveedor
    @api.multi
    def delete_retention_payments(self):
        # para eliminar los pagos de retenciones
        # account_move_obj = self.pool.get('account.move')
        moves = self.env['account.move']
        flag = False
        # for obj_inv in self.browse(cr, uid, ids, context=context):
        for obj_inv in self:
            try:
                if obj_inv.payment_ret_ids:
                    invoices = self.read(['payment_ret_ids'])
                    move_ids = []  # ones that we will need to remove
                    for i in invoices:
                        if i['payment_ret_ids']:
                            # account_move_line_obj = self.pool.get('account.move.line')
                            account_move_line_obj = self.env['account.move.line']
                            # pay_ids = account_move_line_obj.browse(cr, uid, i['payment_ret_ids'])
                            pay_ids = account_move_line_obj.browse(i['payment_ret_ids'])
                            for move_line in pay_ids:
                                # if move_line.move_id and move_line.move_id.id not in move_ids:
                                if move_line.move_id and move_line.move_id not in moves:
                                    # move_ids.append(move_line.move_id.id)
                                    moves += move_line.move_id
                                    move_ids.append(move_line.move_id.id)
                    # if move_ids:
                    if moves:
                        flag = True
                        # second, invalidate the move(s)
                        # account_move_obj.button_cancel(cr, uid, move_ids, context=context)
                        # second, invalidate the move(s)
                        moves.button_cancel()
                        # delete the move
                        # self._cr.execute('DELETE FROM account_move '\
                        #         'WHERE id IN %s', (tuple(move_ids),))
                        self.env.cr.execute("DELETE FROM account_move WHERE id IN %s", (tuple(move_ids),))
                        # account_move_obj.unlink(cr, uid, move_ids, context=context)
            except AttributeError:
                self._log_event(-1.0, "The Invoice don't have a retentions ids.")
                # self._log_event(cr, uid, ids, 1.0, "The Invoice don't have a retentions ids.")
                return True
            except ValueError:
                continue
        if flag:
            self._log_event(-1.0, "Delete Payments Retention in cancel Invoice")
            # self._log_event(cr, uid, ids, -1.0, 'Delete Payments Retention in cancel Invoice')
        return True


account_invoice_ext_api()
