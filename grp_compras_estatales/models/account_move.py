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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class account_move(osv.osv):
    _inherit= "account.move"

    _columns = {
        'desajuste': fields.boolean(u'Desajuste'),
        'ref': fields.char('Reference', copy=False, states={'posted':[('readonly',True)]}),
    }

    def button_validate(self, cursor, user, ids, context=None):
        for move in self.browse(cursor, user, ids, context=context):
            if not (move.period_id.date_start <= move.date <= move.period_id.date_stop):
                raise osv.except_osv(_('Error!'), _("La fecha del asiento no coincide con el período contable."))
        return super(account_move, self).button_validate(cursor, user, ids, context)


    _defaults = {
        'desajuste': lambda *a: False
    }

    def post(self, cr, uid, ids, context=None):
        context = dict(context or {})
        invoice = context.get('invoice', False)
        if invoice and invoice.internal_number:
            int_nbr = invoice.internal_number
            ## Si existe un movimiento con este name ir agregando /1 luego /2 ...
            pos = int_nbr.rfind('/')
            try:
                if pos != -1 and pos > 8 and int_nbr[(pos+1):]==str(int(int_nbr[(pos+1):])):
                    int_nbr = int_nbr[:pos]
            except: # ignore
                pass
            m_ids = self.search(cr, uid, [('name','ilike',int_nbr)], order='name asc', context=context)
            if m_ids:
                move_name = self.read(cr, uid, m_ids[-1], ['name'], context=context)['name']
                if move_name == int_nbr:
                    int_nbr += '/1'
                else:
                    pos = move_name.rfind('/')
                    try:
                        if pos != -1:
                            last = int(move_name[(pos+1):])
                            if move_name[(pos+1):]==str(last):
                                int_nbr += '/%s' % (last+1)
                    except: # ignore
                        pass
                setattr(invoice, 'internal_number', int_nbr)
                context.update({'invoice': invoice})
        return super(account_move, self).post(cr, uid, ids, context=context)

account_move()
