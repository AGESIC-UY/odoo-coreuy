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

import time, datetime
from openerp.osv import osv, fields
from openerp.osv.orm import Model
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp import netsvc
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

#ESTO VIENE DE grp_orden_compras

class account_invoice_extend(osv.osv):
    _inherit = 'account.invoice'

    # # Se define en retenciones pues depende de monto de retenciones
    # def _get_ttal_nominal(self, cr, uid, ids, fields, args, context=None):
    #     res = {}
    #     for inv in self.browse(cr,uid,ids,context=context):
    #         total = inv.amount_untaxed + inv.amount_tax
    #         res[inv.id] = {
    #             'total_nominal_divisa': total and round(total) or 0.0,
    #             'total_nominal_divisa_cpy': total or 0.0,
    #             # 'total_nominal': total and round(total) or 0.0,
    #         }
    #     return res

    # def _get_dif_currency_fnc(self, cr, uid, ids, fieldname, args, context=None):
    #     res = {}
    #     for invoice in self.browse(cr, uid, ids, context=context):
    #         res[invoice.id] = invoice.currency_id.id != invoice.company_currency_id.id and True or False
    #     return res

    _columns = {
        'create_date_date': fields.date(u"Fecha de ingreso"),
        # 'total_nominal_divisa_cpy': fields.function(_get_ttal_nominal, method=True, multi='amount_ttal', string='Total nominal', type='float', digits_compute=dp.get_precision('Account')), #total nominal = total - retenciones no se redondea
        # 'total_nominal_divisa': fields.function(_get_ttal_nominal, method=True, multi='amount_ttal', string='Total nominal', type='float', digits=(16,0)), #total nominal = total - retenciones  round
        # 'total_nominal': fields.function(_get_ttal_nominal, method=True, multi='amount_ttal', string='Total nominal en pesos', type='float', digits=(16,0)),  #total nominal = total - retenciones  round
        # 'diferent_currency': fields.function(_get_dif_currency_fnc, string='Diferencia moneda', type='boolean'),
        'cod_moneda': fields.many2one('sicec.moneda', u'Código moneda SICE'),
    }

    _defaults = {
        'doc_type': 'invoice',
        'create_date_date': lambda *a: datetime.date.today().strftime('%Y-%m-%d'), #time.strftime('%Y-%m-%d'),
    }

    def _get_aux_account_id(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        account_id = company.income_currency_exchange_account_id and company.income_currency_exchange_account_id.id or company.expense_currency_exchange_account_id and company.expense_currency_exchange_account_id.id
        if not account_id:
            raise osv.except_osv(_('Insufficient Configuration!'),_("You should configure the 'The Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        return account_id

    #001 Inicio
    # def invoice_check_oc( self, cr, uid, factura_ids, context = None ):
    #     if context is None:
    #         context = {}
    #     # verificar controles
    #     purchase_order_obj = self.pool.get('purchase.order')
    #     invoice_line_obj = self.pool.get('account.invoice.line')
    #     # read access on purchase.order object is not required
    #     if not purchase_order_obj.check_access_rights(cr, uid, 'read', raise_exception=False):
    #         user_id = SUPERUSER_ID
    #     else:
    #         user_id = uid
    #     po_ids = purchase_order_obj.search(cr, user_id, [('invoice_ids', 'in', factura_ids)], context=context)
    #
    #     order_ids = []
    #     for order in purchase_order_obj.browse(cr, uid, po_ids, context=context):
    #         # Signal purchase order workflow that an invoice has been validated.
    #         order_ids.append(order.id)
    #         for po_line in order.order_line:
    #             line_id = invoice_line_obj.search(cr, user_id, [('invoice_id','in',factura_ids),('product_id','=',po_line.product_id.id)],context=context)
    #             if line_id:
    #                 line_id = line_id or line_id[0]
    #                 line_read = invoice_line_obj.read(cr, user_id,line_id,['quantity'],context=context)
    #                 cantidad_linea = line_read[0]['quantity']
    #                 if po_line.qty_invoiced + cantidad_linea > po_line.product_qty:
    #                     raise osv.except_osv(u'Error!', u'La cantidad a facturar del producto %s supera la cantidad prevista en la orden de compra %s.'% (po_line.product_id.name,po_line.order_id.name))
    #     return order_ids

    def invoice_check_oc(self, cr, uid, factura_ids, context=None):
        if context is None:
            context = {}
        # verificar controles
        purchase_order_obj = self.pool.get('purchase.order')
        # invoice_line_obj = self.pool.get('account.invoice.line')
        # read access on purchase.order object is not required
        if not purchase_order_obj.check_access_rights(cr, uid, 'read', raise_exception=False):
            uid = SUPERUSER_ID
        else:
            uid = uid
        order_ids = []
        for inv in self.browse(cr, uid, factura_ids, context=context):
            if inv.orden_compra_id and inv.orden_compra_id.invoice_method != 'picking':
                order_ids.append(inv.orden_compra_id.id)
                for invoice_line in inv.invoice_line:
                    cant_pendiente = 0.0
                    for order_line in invoice_line.order_lines:
                        cant_pendiente += order_line.qty_pendiente

                    if round(cant_pendiente,3) < round(invoice_line.quantity,3):
                        raise osv.except_osv(u'Error!', u'La cantidad a facturar del producto %s supera la cantidad prevista en la orden de compra %s.' %
                                             ( invoice_line.product_id.name, invoice_line.invoice_id.orden_compra_id and invoice_line.invoice_id.orden_compra_id.name or ''))
        return order_ids

    def invoice_sice_temp(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context=dict(context)

        self.check_amount(cr, uid, ids, context=context)  # RAGU verificar monto en el boton Financiero

        # verificar controles
        order_ids = self.invoice_check_oc(cr, uid, ids, context=context)

        if ids:
            inv = self.browse(cr, uid, ids[0], context)
            tipo = inv.doc_type
            #Si no viene al año fiscal se carga el de la fecha de la factura
            if not context.get('fiscalyear_id', False):
                fiscalyear_obj = self.pool.get('account.fiscalyear')
                uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
                fecha_hoy = inv.date_invoice
                fiscal_year_id = fiscalyear_obj.search(cr, uid,[('date_start', '<=', fecha_hoy),
                                                                ('date_stop', '>=', fecha_hoy),
                                                                ('company_id', '=', uid_company_id)], context=context)
                fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
                context.update({'fiscalyear_id': fiscal_year_id})
        else:
            tipo = 'doc_type' in context and context.get('doc_type',False)
        values = {'state':'sice'}
        if self.check_accounts(cr, uid, ids, context=context):
            self.button_reset_taxes(cr, uid, ids, context) # para incidencia, recalculas impuestos
            if tipo and tipo == 'invoice':
                values['nro_factura_grp'] = self.pool.get('ir.sequence').get(cr, uid, 'sec.factura', context=context)
            self.write(cr, uid, ids, values, context=context)
        return False

    def invoice_sice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context=dict(context)

        # verificar controles
        order_ids = self.invoice_check_oc(cr, uid, ids, context=context)

        if ids:
            inv = self.browse(cr, uid, ids[0], context)
            tipo = inv.doc_type
            #Si no viene al año fiscal se carga el de la fecha de la factura
            if not context.get('fiscalyear_id', False):
                fiscalyear_obj = self.pool.get('account.fiscalyear')
                uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
                fecha_hoy = inv.date_invoice
                fiscal_year_id = fiscalyear_obj.search(cr, uid,[('date_start', '<=', fecha_hoy),
                                                                ('date_stop', '>=', fecha_hoy),
                                                                ('company_id', '=', uid_company_id)], context=context)
                fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
                context.update({'fiscalyear_id': fiscal_year_id})
        else:
            tipo = 'doc_type' in context and context.get('doc_type',False)
        values = {'state': 'sice'}
        if self.check_accounts(cr, uid, ids, context=context):
            self.button_reset_taxes(cr, uid, ids, context) # para incidencia, recalculas impuestos
            if tipo and tipo == 'invoice':
                values['nro_factura_grp'] = self.pool.get('ir.sequence').get(cr, uid, 'sec.factura', context=context)
            self.write(cr, uid, ids, values, context=context)
            return True
        return False

    #001 Fin incidencia, tambien modificado el sice temp
    def action_invoice_cancel_sice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state':'cancel_sice'}, context=context)
        self._log_event(cr, uid, ids, -1.0, 'Cancel SICE')
        return True

    # 004 Incidencia cancelacion del pago
    def button_cancelar_pago(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for inv_id in ids:
            inv_obj = self.browse(cr, uid, inv_id)
            if (inv_obj.doc_type in ['invoice'] and inv_obj.tipo_ejecucion_codigo_rel in ['P']) or\
               (inv_obj.doc_type in ['3en1_invoice', 'vales_caja', 'adelanto_viatico']) or\
               (inv_obj.type in ['in_invoice']):
                if inv_obj.fecha_aprobacion:
                    raise osv.except_osv(_(u'Error!'), _(u'Este documento ya fue aprobado para su pago. Cancele la '
                                                    u'aprobación del pago si desea cancelar la factura.'))
            wf_service.trg_validate(uid, 'account.invoice', inv_id, 'invoice_cancel_paid', cr)
        return True

    def cancel_pagos_factura(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        invoices = self.read(cr, uid, ids, ['id', 'move_id', 'payment_ids'])
        move_ids = []  # ones that we will need to remove
        move_reconciled_ids = []
        move_line_reconc_ids = []
        for i in invoices:
            if i['move_id']:
                move_ids.append(i['move_id'][0])
            if i['payment_ids']:
                # cancel_pago_wiz_obj = self.pool.get('grp.wiz.cancelar.pago')
                pay_ids = account_move_line_obj.browse(cr, uid, i['payment_ids'])
                for move_line in pay_ids:
                    if move_line.reconcile_partial_id and move_line.reconcile_partial_id.line_partial_ids:
                        # self.temp_cancel_pago_parcial(cr, uid, ids, move_line)
                        # self.cancel_voucher_partial_reconcile_paids(cr, uid, move_line, False, context=context)
                        continue
                        # self.button_cancel_pago_parcial(cr, uid, ids, context=context)
                        # raise osv.except_osv(_('Error!'), _('You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))
                    # Aca cambie a ver este if / else
                    else:
                        # si los movimientos asociados al pago estan conciliados, elimino el pago y la conciliacion
                        if move_line.reconcile_id:
                            # canc_wiz = cancel_pago_wiz_obj.search(cr, uid,[('invoice_id','=',i['id'])],limit=1, order='id desc')
                            # canc_wiz_id = canc_wiz and canc_wiz[0] or False
                            # ctx = context.copy()
                            # if canc_wiz:
                            #     wiz_data = cancel_pago_wiz_obj.read(cr, uid, canc_wiz_id ,['writeoff_acc_aux_id','date'])
                            #     writeoff_acc_aux_id = wiz_data and wiz_data['writeoff_acc_aux_id'] and wiz_data['writeoff_acc_aux_id'][0] or False
                            #     date_p = wiz_data['date']
                            #     ctx.update({'write_off_account_id': writeoff_acc_aux_id, 'writeoff_journal_id': move_line.journal_id.id,
                            #                 'writeoff_period_id': move_line.period_id.id, 'date_p': date_p})

                            # Cambio, echaviano 18/02
                            # ctx = context.copy()
                            # writeoff_acc_aux_id = self._get_aux_account_id(cr, uid, context=ctx)
                            # if writeoff_acc_aux_id:
                            #     date_p = time.strftime('%Y-%m-%d'),
                            #     ctx.update({'write_off_account_id': writeoff_acc_aux_id, 'writeoff_journal_id': move_line.journal_id.id,
                            #                 'writeoff_period_id': move_line.period_id.id, 'date_p': date_p})
                            # self.break_delete_paid(cr, uid, move_line, context=ctx)

                            if move_line.move_id.id not in move_reconciled_ids:
                                move_reconciled_ids.append(move_line.move_id.id)
                                move_line_reconc_ids.append(move_line.id)

                # cambios, 18/02
                ctx = context.copy()
                writeoff_acc_aux_id = self._get_aux_account_id(cr, uid, context=ctx)

                # voucher_pool = self.pool.get('account.voucher')
                for move_line_id in move_line_reconc_ids:
                    mline_elem = account_move_line_obj.browse(cr, uid, move_line_id)
                    # for move_id in move_reconciled_ids:
                    #     voucher_ids = voucher_pool.search(cr, uid, [('move_id','=',move_line.move_id.id)])
                    if writeoff_acc_aux_id:
                        date_p = time.strftime('%Y-%m-%d'),
                        ctx.update({'write_off_account_id': writeoff_acc_aux_id,
                                    'writeoff_journal_id': mline_elem.journal_id.id,
                                    'writeoff_period_id': mline_elem.period_id.id, 'date_p': date_p})
                    self.break_delete_paid(cr, uid, mline_elem, context=ctx)

        # 006 - check partial payment aditional - to delete
        moves = account_move_obj.browse(cr, uid, move_ids)
        reconcile_partial_ids = []
        # move_delete_ids = []
        if moves:
            for move in moves:
                for line in move.line_id:
                    if line and line.reconcile_partial_id and line.reconcile_partial_id.id not in reconcile_partial_ids:
                        reconcile_partial_ids.append(line.reconcile_partial_id.id)

        # echaviano, viernes 18/09  posible eliminacion
        if reconcile_partial_ids:
            self.cancel_moves_partial_reconcile_write_off(cr, uid, reconcile_partial_ids, context=ctx)
        # 006 - Fin de eliminacion

        # invoice_state = self.read(cr, uid, ids, ['state'],context=context)[0]['state']
        self.write(cr, uid, ids, {'state': 'open'})
        self._log_event(cr, uid, ids, -1.0, 'Cancel Paid Invoice')
        return True

    def temp_cancel_pago_parcial(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        account_move_line_obj = self.pool.get('account.move.line')
        invoices = self.read(cr, uid, ids, ['id', 'move_id', 'payment_ids'])
        move_ids = []  # ones that we will need to remove
        reconcile_partial_ids = []
        for i in invoices:
            if i['move_id']:
                move_ids.append(i['move_id'][0])
            if i['payment_ids']:
                pay_ids = account_move_line_obj.browse(cr, uid, i['payment_ids'])
                for move_line in pay_ids:
                    if move_line.reconcile_partial_id and move_line.reconcile_partial_id.line_partial_ids:
                        reconcile_partial_ids.append(move_line.reconcile_partial_id.id)
                        self.cancel_voucher_partial_reconcile_paids(cr, uid, move_line, False, context=context)
        # echaviano, posible eliminacion, viernes 18/09
        # if reconcile_partial_ids:
        #     reconcile_partial_ids = list(set(reconcile_partial_ids))
        #     self.cancel_move_write_off(cr, uid, False, reconcile_partial_ids)
        return True

    # 007 Cancelar pagos parciales - Boton
    def button_cancel_pago_parcial(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        account_move_line_obj = self.pool.get('account.move.line')
        invoices = self.read(cr, uid, ids, ['id', 'move_id', 'payment_ids'])
        move_ids = []  # ones that we will need to remove
        reconcile_partial_ids = []
        for i in invoices:
            if i['move_id']:
                move_ids.append(i['move_id'][0])
            if i['payment_ids']:
                pay_ids = account_move_line_obj.browse(cr, uid, i['payment_ids'])
                for move_line in pay_ids:
                    if move_line.reconcile_partial_id and move_line.reconcile_partial_id.line_partial_ids:
                        reconcile_partial_ids.append(move_line.reconcile_partial_id.id)
                        self.cancel_voucher_partial_reconcile_paids(cr, uid, move_line, False, context=context)
        # echaviano, posible eliminacion, viernes 18/09
        if reconcile_partial_ids:
            reconcile_partial_ids = list(set(reconcile_partial_ids))
            self.cancel_move_write_off(cr, uid, False, reconcile_partial_ids)
        return True

    def cancel_voucher_partial_reconcile_paids(self, cr, uid, move_line, reconcile_partial_ids, context=None):
        voucher_pool = self.pool.get('account.voucher')
        # move_line_pool = self.pool.get('account.move.line')
        voucher_ids = voucher_pool.search(cr, uid, [('move_id', '=', move_line.move_id.id)])
        if voucher_ids and len(voucher_ids) >= 1:
            voucher_pool.cancel_voucher(cr, uid, voucher_ids, context=context)
            voucher_pool.unlink(cr, uid, voucher_ids, context)
            return True
        return False

    # 007 Fin - Cancelar pagos parciales

    # metodo auxiliar para eliminar el/los pagos asociados a la factura. Conciliados total
    def break_delete_paid(self, cr, uid, move_line, context=None):
        voucher_pool = self.pool.get('account.voucher')
        move_line_pool = self.pool.get('account.move.line')
        voucher_ids = voucher_pool.search(cr, uid, [('move_id', '=', move_line.move_id.id)])
        # move_write_of_ids = []
        if voucher_ids and len(voucher_ids) == 1:
            try:
                # if voucher_ids:
                move_line_reconcil_ids = []
                reconcile_ids = []
                for voucher in voucher_pool.browse(cr, uid, voucher_ids, context=context):
                    if voucher.move_ids:
                        # for move_id in voucher.move_ids:
                        # move_write_of_ids.append(voucher.move_ids)
                        for line in voucher.move_ids:
                            if line.reconcile_id:
                                reconcile_ids.append(line.reconcile_id.id)
                                move_line_tmp_ids = move_line_pool.search(cr, uid,
                                                                          [('reconcile_id', '=', line.reconcile_id.id)])

                                for mline in move_line_pool.browse(cr, uid, move_line_tmp_ids, context=context):
                                    if mline.move_id and mline.move_id.desajuste and mline.move_id.id not in move_line_reconcil_ids:
                                        move_line_reconcil_ids.append(mline.move_id.id)

                                        # self.cancel_move_write_off(cr, uid, voucher.move_ids)
                voucher_pool.cancel_voucher(cr, uid, voucher_ids, context=context)
                voucher_pool.unlink(cr, uid, voucher_ids, context=context)
                reconcile_ids = list(set(reconcile_ids))
                # echaviano, posible eliminacion 18/09
                self.cancel_move_write_off(cr, uid, move_line_reconcil_ids, reconcile_ids)
            except AttributeError:
                # raise osv.except_osv(_('Error!'),_("Debe eliminar la conciliacion para cancelar la factura!"))
                if reconcile_ids:
                    cr.execute('delete from account_move_reconcile \
                                where id in %s', (tuple(reconcile_ids),))
                    voucher_pool.cancel_voucher(cr, uid, voucher_ids, context=context)
                    voucher_pool.unlink(cr, uid, voucher_ids, context)
                return True
                # try:
                #     voucher_pool.cancel_voucher(cr, uid, voucher_ids, context=context)
                #     voucher_pool.unlink(cr, uid, voucher_ids, context)
                # except Exception as e:
                #     raise osv.except_osv('Error!', u'Debe definir la cuenta auxiliar')
        return True

    # echaviano, viernes 18/09 posible eliminacion
    # 006 - Cancelar los asientos de desajustes con conciliacion parcial - Metodo auxiliar cancelar pagos
    def cancel_moves_partial_reconcile_write_off(self, cr, uid, unlink_reconcile_partial_ids, context=None):
        # account_move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        delete_moves_ids = []

        move_line_tmp_ids = move_line_pool.search(cr, uid,
                                                  [('reconcile_partial_id', 'in', unlink_reconcile_partial_ids)])
        for mline in move_line_pool.browse(cr, uid, move_line_tmp_ids, context=context):
            if mline.move_id and mline.move_id.desajuste and mline.move_id.id not in delete_moves_ids:
                delete_moves_ids.append(mline.move_id.id)
            # reconcile_ids = list(set(reconcile_ids))
            reconcile_ids = list(set(unlink_reconcile_partial_ids))
            self.cancel_move_write_off(cr, uid, delete_moves_ids, reconcile_ids)
        return True

    # echaviano, posible eliminacion. viernes 18/09
    # 005 - Metodo auxiliar cancelar pagos. Desajustes
    def cancel_move_write_off(self, cr, uid, move_ids, unlink_reconcile_ids, context=None):
        account_move_pool = self.pool.get('account.move')
        # for reconcile_id in reconcile_ids:
        # buscar la lineas que tenga reconcilie id, y esten con un move con desajuste
        try:
            if move_ids:
                account_move_pool.button_cancel(cr, uid, move_ids, context=context)
                # cr.execute('UPDATE account_move '\
                #            'SET state=%s '\
                #            'WHERE id IN %s', ('draft', tuple(move_ids),))
                account_move_pool.unlink(cr, uid, move_ids, context=context)
            if unlink_reconcile_ids:
                # cr.execute('DELETE FROM account_move_reconcile WHERE id=%s',(id_reconcile,))
                cr.execute('DELETE FROM account_move_reconcile WHERE id in %s', (tuple(unlink_reconcile_ids),))
                cr.commit()
        except AttributeError:
            return True
        # Agregado excepcion 18/02
        except Exception:
            return True
            # cr.commit()
        return True

    def btn_aprobar(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state': 'approved'}, context=context)
        return True

    def btn_enviar_autorizar(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state': 'in_auth'}, context=context)
        return True

    def btn_autorizar(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state': 'authorized'}, context=context)
        return True

    def btn_obligar(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # verificar que el monto no sea menor o igual a cero
        # todas las facturas pasan por el estado Obligado
        if self.check_amount(cr, uid, ids, context=context):
            self.write(cr, uid, ids, {'state': 'forced'}, context=context)
            return True
        return False

    def btn_cancel_obligacion(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # self.write(cr, uid, ids, {'state':'cancel_siif', 'move_id':False})
        self.write(cr, uid, ids, {'state': 'cancel_siif'})
        self._log_event(cr, uid, ids, -1.0, 'Cancel SIIF')
        return True

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if 'date_invoice' in vals and vals.get('date_invoice', False):  # 003 Incidencia periodo
            period_obj = self.pool.get('account.period')
            ctx = context.copy()
            ctx.update(company_id=vals.get('company_id', False),
                       account_period_prefer_normal=True)
            period_ids = period_obj.find(cr, uid, vals.get('date_invoice'), context=ctx)
            period_id = period_ids and period_ids[0] or False
            vals.update({'period_id': period_id})
        id = super(account_invoice_extend, self).create(cr, uid, vals, context)
        self.button_reset_taxes(cr, uid, [id], context)
        return id


    # 003 Para incidencia de periodo
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if 'date_invoice' in vals and vals.get('date_invoice', False):
            date_invoice = vals.get('date_invoice')

        if isinstance(ids, (int, long)):
            ids = [ids]
        for inv in self.browse(cr, uid, ids, context):
            period_obj = self.pool.get('account.period')
            ctx = context.copy()

            date_invoice = vals.get('date_invoice', False) and date_invoice or inv.date_invoice
            ctx.update(company_id=inv.company_id.id,
                       account_period_prefer_normal=True)
            period_ids = period_obj.find(cr, uid, date_invoice, context=ctx)
            period_id = period_ids and period_ids[0] or False
            vals.update({'period_id': period_id})
        r = super(account_invoice_extend, self).write(cr, uid, ids, vals, context=context)

        if 'reset' not in context:
            c = context.copy()
            c.update({'reset': True})
            self.button_reset_taxes(cr, uid, ids, context=c)
            # super(account_invoice_extend, self).button_reset_taxes(cr, uid, ids, context=c)
        return True


    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'supplier_invoice_number': False,
        })
        return super(account_invoice_extend, self).copy(cr, uid, id, default, context=context)


    def ordenes_compra_tree_view(self, cr, uid, ids, context):
        ordenes_ids = []
        factura = self.browse(cr, uid, ids, context=context)[0]
        if factura.orden_compra_id and factura.orden_compra_id.id:
            ordenes_ids.append(factura.orden_compra_id.id)
        domain = [('id', 'in', ordenes_ids)]

        if ordenes_ids:
            return {
                'name': _(u'Órdenes de Compra'),
                'domain': domain,
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree,form',
                'view_type': 'form',
                'limit': 80,
                'context': {},
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'action_warn',
                'name': _('Aviso'),
                'context': context,
                'params': {
                    'title': _('Aviso'),
                    'text': _(u'No hay órdenes de compra asociada!'),
                    'sticky': True
                }}


    def contratos_tree_view(self, cr, uid, ids, context):
        factura = self.browse(cr, uid, ids[0], context)
        # TODO: L SPRING 12 GAP 499
        contratos_ids = self.pool.get('grp.contrato.proveedores').search(cr, uid, [
            ('nro_adj_id', '=', factura.orden_compra_id.doc_origen.id),
            ('proveedor', '=', factura.orden_compra_id.partner_id.id)])
        # domain = [('id', 'in', contratos_ids)]

        if contratos_ids:
            data_pool = self.pool.get('ir.model.data')
            action_model, action_id = data_pool.get_object_reference(cr, uid, 'grp_contrato_proveedores',
                                                                     'action_contract_proveedores_form')
            if action_model:
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                action['domain'] = "[('id','in', [" + ','.join(map(str, contratos_ids)) + "])]"
            return action
        return

account_invoice_extend()
