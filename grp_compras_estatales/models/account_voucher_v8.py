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
import itertools


class grp_account_voucher(models.Model):
    _inherit = 'account.voucher'

    tipo_cambio = fields.Float(string=u'Tipo de cambio', compute='_compute_tipo_cambio', readonly=True)

    invoice_ids = fields.Many2many(comodel_name='account.invoice', string=u'Facturas', readonly=True,
                                   compute='_get_invoice_ids', store=False)
    # TODO: SPRING 8 GAP 364 K incidecia
    nro_documento = fields.Char(string=u'Nro. Documento', compute='_compute_nro_documento', store=False)

    attachment_ids = fields.Many2many(compute='get_attachments_docs',
                                      comodel_name='ir.attachment',
                                      string=u'Documentos asociados')

    @api.multi
    @api.depends('invoice_id')
    def get_attachments_docs(self):
        pool_po = self.env['purchase.order']
        pool_invoice = self.env['account.invoice']
        pool_voucher = self.env['account.voucher']
        pool_adj = self.env['grp.cotizaciones']
        for voucher in self:
            domain = False
            solicitudes = []
            srs = []

            if voucher.invoice_id and voucher.invoice_id.orden_compra_id:
                for linea in voucher.invoice_id.orden_compra_id.pedido_compra_id.lineas_ids:
                    if linea.solicitud_compra_id:
                        solicitudes.append(linea.solicitud_compra_id.id)
                        srs.append(linea.solicitud_compra_id.solicitud_recursos_id.id)
                po_ids = pool_po.suspend_security().search([('pedido_compra_id', '=', voucher.invoice_id.orden_compra_id.pedido_compra_id.id), ('state', 'not in', ['cancel'])])
                inv_ids = pool_invoice.suspend_security().search([('orden_compra_id', 'in', po_ids.ids),
                                                        ('state', 'not in', ['cancel', 'cancel_siif', 'cancel_sice'])])
                av_ids = pool_voucher.suspend_security().search([('invoice_id', 'in', inv_ids.ids),('state', 'not in', ['cancel'])])
                adj_ids = pool_adj.suspend_security().search([('pedido_compra_id', '=', voucher.invoice_id.orden_compra_id.pedido_compra_id.id), ('state', 'not in', ['cancelado'])])
                domain = ['|','|','|','|','|','|', '|', '&', ('res_id', '=', voucher.id), ('res_model', '=', 'account.voucher'),
                          '&', ('res_id', '=', voucher.invoice_id.orden_compra_id.pedido_compra_id.id), ('res_model', '=', 'grp.pedido.compra'),
                          '&', ('res_id', 'in', solicitudes), ('res_model', '=', 'grp.solicitud.compra'),
                          '&', ('res_id', 'in', srs), ('res_model', '=', 'grp.compras.solicitud.recursos.almacen'),
                          '&', ('res_id', 'in', po_ids.ids), ('res_model', '=', 'purchase.order'),
                          '&', ('res_id', 'in', inv_ids.ids), ('res_model', '=', 'grp.compras.apg'),
                          '&', ('res_id', '=', voucher.invoice_id.id), ('res_model', '=', 'account.invoice'),
                          '&', ('res_id', 'in', adj_ids.ids), ('res_model', '=', 'grp.cotizaciones'),
                          ]

            if not domain:
                domain = [('res_id', '=', voucher.id), ('res_model', '=', 'account.voucher')]
            docs = self.env['ir.attachment'].search(domain)
            voucher.attachment_ids = docs.ids

    # TODO: SPRING 8 GAP 364 K
    @api.multi
    @api.depends('line_ids')
    def _get_invoice_ids(self):
        for rec in self:
            facturas_list = []
            for line in rec.mapped(lambda x: x.line_ids).filtered(lambda x: x.amount > 0):
                facturas = self.env['account.invoice'].search(
                    [('move_id', '!=', False), ('move_id', '=', line.move_line_id.move_id.id)])
                if facturas:
                    for factura in facturas:
                        facturas_list.append((4, factura.id, False))
            rec.invoice_ids = len(facturas_list) > 0 and facturas_list or False

    def _get_nro_documento(self):
        self.ensure_one()
        documentos = []
        for line in self.line_ids.filtered(lambda x: x.amount > 0):
            documentos.append(line.supplier_invoice_number)
        return documentos

    # TODO: SPRING 8 GAP 364 K incidencia
    @api.multi
    @api.depends('line_ids')
    def _compute_nro_documento(self):
        for rec in self:
            rec.nro_documento = ', '.join(filter(None, rec._get_nro_documento()))

    @api.multi
    @api.depends('currency_id')
    def _compute_tipo_cambio(self):
        for row in self:
            row.tipo_cambio = row.currency_id.rate

    #Actualizo la operating_unit_id cada vez que se modifica el diario
    #Se agrega este metodo aca porque esta en account_voucher_operating_unit y no entra en la dependecia de facturas_uy
    def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
        to_return = super(grp_account_voucher, self).onchange_journal(cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=context)
        if to_return and journal_id:
            operating_unit_id = self.pool.get('account.journal').browse(cr, uid, journal_id).operating_unit_id.id
            to_return['value'].update({
                'operating_unit_id': operating_unit_id,
            })
        return to_return

    @api.multi
    def cancel_voucher(self):
        AccountMoveLine = self.env['account.move.line']
        AccountMove = self.env['account.move']
        period_id = self.env['account.period'].find(fields.Date.today()).id
        for rec in self:
            # RAGU cancelando comprobantes que dieron origen
            # el flujo normal es cancelar, ante solicitud se pasa a contabilizado manualmente
            # rec.line_ids.filtered(lambda x: x.amount != 0 and x.origin_voucher_id.state == 'pagado').origin_voucher_id.cancel_voucher()
            rec.line_ids.filtered(lambda x: x.amount != 0 and x.origin_voucher_id.state == 'pagado').mapped('origin_voucher_id').write({'state':'posted'})
            move = rec.move_id
            writeoff_move_ids = rec._cancel_voucher()
            if move:
                lines = AccountMoveLine.search([('move_id', '=', move.id)])
                if move.reversal_id:
                    reversal_move_ids = [ move.reversal_id.id ]
                else:
                    reversal_move_ids = move.create_reversals(fields.Date.today(), reversal_period_id=period_id)
                reversal_lines = AccountMoveLine.search([('move_id', 'in', reversal_move_ids)])
                # Reconcile entries
                lines2rec = AccountMoveLine.browse()
                # Tomar la cuenta del cabezal del voucher cuando el registro es:
                # - OPI
                # - Adelantos y reintegros
                # - Devolución de viáticos
                # - Anticipo de fondos
                # - Devolución de Anticipo de fondos
                # - Vales de caja
                # - Recibo de ventas
                # - Pagos de clientes: RAGU=>SE EXONERA PAGOS DE CLIENTES PUES NO USA CUENTA DEL CABEZAL PARA EXTORNAR.
                if rec.opi or \
                   (rec.journal_id.type in ['purchase'] and rec.type=='payment' and (rec.solicitud_viatico_id or rec.rendicion_viaticos_id)) or \
                   (rec.journal_id.type in ['sale','sale_refund'] and rec.type=='sale' and rec.solicitud_viatico_id) or \
                   (rec.journal_id.type in ['purchase'] and rec.type=='payment' and (rec.solicitud_anticipos_id or rec.rendicion_anticipos_id)) or \
                   (rec.journal_id.type in ['sale','sale_refund'] and rec.type=='sale' and rec.rendicion_anticipos_id) or \
                   (rec.invoice_id and self.env['grp.vale.caja'].search_count([('aprobacion_pago_id', '=', rec.invoice_id.id)])) or \
                   (rec.journal_id.type in ['sale','sale_refund'] and rec.type=='sale' and not rec.solicitud_viatico_id):
                   # (rec.journal_id.type in ['bank','cash'] and rec.type=='receipt'):
                    acc_id = rec.account_id.id
                else:
                    acc_id = False
                company = rec.company_id or self.env.user.company_id
                for line in itertools.chain(lines, reversal_lines):
                    if not acc_id and line.account_id.id != rec.account_id.id \
                       and line.partner_id and line.partner_id.id == rec.partner_id.id \
                       and line.account_id.id not in [ company.income_rounding_adjust_account_id and company.income_rounding_adjust_account_id.id or -1,
                                                       company.expense_rounding_adjust_account_id and company.expense_rounding_adjust_account_id.id or -1,
                                                       company.inter_ou_clearing_account_id and company.inter_ou_clearing_account_id.id or -1 ]:
                        acc_id = line.account_id.id
                    if acc_id and line.account_id.id == acc_id:
                        lines2rec += line
                if lines2rec:
                    lines2rec.reconcile('manual', writeoff_acc_id=rec.writeoff_acc_id and rec.writeoff_acc_id.id or False, writeoff_journal_id = rec.journal_id.id, writeoff_period_id=period_id)
                # Crear extorno de asiento(s) por diferencia de cambio
                for move_id, to_reconcile_account_id in writeoff_move_ids.items():
                    writeoff_move = AccountMove.browse(move_id)
                    if writeoff_move.reversal_id:
                        writeoff_reversal_move_ids = [ writeoff_move.reversal_id.id ]
                    else:
                        writeoff_reversal_move_ids = writeoff_move.create_reversals(fields.Date.today(), reversal_period_id=period_id)
                    writeoff_lines2rec = AccountMoveLine.search([('move_id', '=', move_id),('account_id','=',to_reconcile_account_id)])
                    writeoff_reversal_lines2rec = AccountMoveLine.search([('move_id', 'in', writeoff_reversal_move_ids),('account_id','=',to_reconcile_account_id)])
                    # Reconcile entries
                    lines2rec = writeoff_lines2rec + writeoff_reversal_lines2rec
                    lines2rec.reconcile('manual', writeoff_acc_id=rec.writeoff_acc_id and rec.writeoff_acc_id.id or False, writeoff_journal_id = rec.journal_id.id, writeoff_period_id=period_id)
        return True

class grp_account_voucher_line(models.Model):
    _inherit= 'account.voucher.line'

    invoice_id = fields.Many2one('account.invoice', u'Nro. Factura GRP', readonly=True,
                                          compute='_get_invoice_id', multi='_get_invoice_id', store=False)
    supplier_invoice_number = fields.Char(string=u'Nro. de documento',
                                          compute='_get_invoice_id', multi='_get_invoice_id', store=False)
    supplier_invoice_number2 = fields.Char(string=u'Nro. de documento 2',
                                          compute='_get_invoice_id', multi='_get_invoice_id')

    # TODO: SPRING 8 GAP 364 K
    # RAGU adicionando origen a las lineas del voucher y UE
    def _get_origin_dict(self):
        self = self.sudo()
        invoice_id = self.env['account.invoice'].search([('move_id', '!=', False), ('move_id', '=', self.move_line_id.move_id.id)])
        if invoice_id:
            _view_id = False
            _module_name = False
            if invoice_id.type in (u'in_invoice', u'in_refund') and invoice_id.supplier_invoice_number:
                invoice_number = invoice_id.supplier_invoice_number
            elif invoice_id.type in (u'out_invoice'):
                _view_id = u'invoice_form'
                _module_name = u'account'
                invoice_number = invoice_id.number
            else:
                if invoice_id.nro_factura_grp:
                    invoice_number = invoice_id.nro_factura_grp
                elif invoice_id.name_get():
                    invoice_number = invoice_id.name_get()[0][1]
                else:
                    invoice_number = False
            _related_model = self.invoice_id._name
            _related_id = self.invoice_id.id
            _related_document = invoice_number
            _invoice_id = invoice_id.id
            _supplier_invoice_number = invoice_id.nro_afectacion_fnc and '%s Nro Afect: %s' % (invoice_number, invoice_id.nro_afectacion_fnc) or invoice_number
            _nro_afectacion = invoice_id.nro_afectacion_fnc
        else:
            _related_model = self.move_line_id.move_id._name
            _related_id = self.move_line_id.move_id.id
            _view_id = False
            _module_name = False
            if self.move_line_id:
                _related_document = self.move_line_id.move_id.name_get()[0][1]
                _supplier_invoice_number = self.move_line_id.move_id.name_get()[0][1]
            elif self._context.get('move_line_id'):
                _related_document = self._context.get('move_line_id').move_id.name_get()[0][1]
                _supplier_invoice_number = self._context.get('move_line_id').move_id.name_get()[0][1]
            else:
                _related_document = False
                _supplier_invoice_number = False
            _nro_afectacion = 0
            _invoice_id = False

        return {'related_document': _related_document,
                'related_model': _related_model,
                'related_id': _related_id,
                'module_name': _module_name,
                'view_id': _view_id,
                'invoice_id':_invoice_id,
                'supplier_invoice_number': _supplier_invoice_number,
                'nro_afectacion': _nro_afectacion
                }

    @api.multi
    def _get_invoice_id(self):
        for rec in self.filtered(lambda x:x.move_line_id):  # TODO: SPRING 8 GAP 364 K incidencia
            vals = rec.with_context({'move_line_id':rec.move_line_id})._get_origin_dict()
            rec.invoice_id = vals.get('invoice_id')
            rec.supplier_invoice_number = vals.get('supplier_invoice_number')
            rec.supplier_invoice_number2 = vals.get('supplier_invoice_number2')

    @api.multi
    def action_link_related_document(self):
        self.ensure_one()
        _related_info_dict = self._get_origin_dict()
        dict_toreturn = {
            'type': 'ir.actions.act_window',
            'res_model': _related_info_dict['related_model'],
            'display_name': 'Documento relacionado',
            'view_type': 'form',
            'name': 'Documento relacionado',
            'target': 'current',
            'view_mode': 'form',
            'res_id': _related_info_dict['related_id']
        }

        if _related_info_dict.get('view_id') and _related_info_dict['view_id']:
            res = self.env['ir.model.data'].get_object_reference(_related_info_dict['module_name'],
                                                                 _related_info_dict['view_id'])
            res_id = res and res[1] or False
            dict_toreturn.update({
                'view_id': res_id
            })
        return dict_toreturn
