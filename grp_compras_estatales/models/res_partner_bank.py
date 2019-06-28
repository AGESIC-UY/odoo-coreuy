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

TIPOS_CUENTAS = [('caja de ahorros',u'Caja de ahorros'),
                 ('cuenta corriente','Cuenta corriente')]

class grp_alta_cuentas_bancarias(osv.osv):
    _inherit= "res.partner.bank"

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['agencia','acc_number','descripcion_cuenta'], context=context)
        res = []
        for record in reads:
            res.append((record['id'],('%s-%s-%s') % (record['agencia'],record['acc_number'],record['descripcion_cuenta'] or '')))
        return res

    _columns={
        'state': fields.selection(TIPOS_CUENTAS, 'Tipo de cuenta', required=True,
            change_default=True),
        'agencia': fields.char('Agencia'),
        'descripcion_cuenta': fields.char(string=u'Descripción de cuenta', size=150),
    }


grp_alta_cuentas_bancarias()