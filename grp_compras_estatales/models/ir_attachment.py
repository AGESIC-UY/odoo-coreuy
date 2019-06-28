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

class ir_attachment(osv.osv):

    _inherit = 'ir.attachment'

    def _name_get_resname(self, cr, uid, ids, object, method, context):
        data = {}
        for attachment in self.browse(cr, uid, ids, context=context):
            model_object = attachment.res_model
            res_id = attachment.res_id
            if model_object and res_id:
                model_pool = self.pool[model_object]
                res = model_pool.name_get(cr,uid,[res_id],context)
                res_name = res and res[0][1] or None
                data[attachment.id] = res_name or False
            else:
                data[attachment.id] = False
        return data

    def _name_get_resname_computed(self, cr, uid, ids, object, method, context):
        data = {}
        for attachment in self.browse(cr, uid, ids, context=context):
            model_object = attachment.res_model
            res_id = attachment.res_id
            if model_object and res_id:
                model_pool = self.pool[model_object]
                res = model_pool.name_get(cr,uid,[res_id],context)
                res_name = res and res[0][1] or None
                data[attachment.id] = res_name or False
            else:
                data[attachment.id] = False
        return data

    _columns = {
        'res_name': fields.function(_name_get_resname, type='char', string='Resource Name', store=True),
        'res_name_computed': fields.function(_name_get_resname_computed, type='char', string='Resource Name Computed', store=False),
    }

ir_attachment()