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

from openerp.osv import osv
import logging
_logger = logging.getLogger(__name__)


class account_invoice_rendido(osv.osv_memory):

    _name = "account.invoice.rendido"

    def invoice_rendido(self, cr, uid, ids, context=None):
        invoice_obj = self.pool.get('account.invoice')
        if context is None:
            context = {}
        if 'active_ids' in context:
            invoice_ids= context.get('active_ids', [])
            for invoice in invoice_obj.browse(cr, uid, invoice_ids, context=context):
                if invoice.rendido_siif == False:
                    invoice_obj.write(cr, uid, invoice.id, {'rendido_siif': True}, context=context)
        return {'type': 'ir.actions.act_window_close'}

account_invoice_rendido()