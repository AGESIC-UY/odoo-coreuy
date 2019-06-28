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
from openerp import api

class account_retention(osv.osv):

    _inherit = 'account.retention'

    _columns = {
        'grupo_acreedor_id': fields.many2one('account.group.creditors','Grupo acreedor'),
        'acreedor_id': fields.many2one('account.retention.creditors','Acreedor'),
    }

    def action_validate(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids):
            number = ('%s - %s - %s') % (rec.acreedor_id.name,rec.grupo_acreedor_id.descripcion,rec.name)
            context.update({'number': number})
            super(account_retention, self).action_validate(cr, uid, [rec.id], context=None)
        return True

account_retention()

class account_global_retention_line(osv.osv):
    _inherit = "account.global.retention.line"

    _columns = {
        'group_id': fields.many2one('account.group.creditors','Grupo acreedor'),
        'creditor_id': fields.many2one('account.retention.creditors', 'Acreedor'),
    }

    def onchange_group_id(self, cr, uid, ids, group_id):
        return {'value': {'creditor_id': False}}

    @api.onchange('creditor_id')
    def _onchange_creditor_id(self):
        if self.creditor_id and self.creditor_id.account_id:
            self.account_id = self.creditor_id.account_id

account_global_retention_line()

