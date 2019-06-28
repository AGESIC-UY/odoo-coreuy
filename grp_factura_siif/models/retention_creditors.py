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

import datetime
from openerp.osv import osv, fields
from openerp.tools.translate import _

# Acreedores de retenciones
class group_creditors(osv.osv):

    _name = "account.group.creditors"
    _description = "Grupo de acreedores"
    _rec_name = 'name'
    _order = "id desc"

    #001 Inicio
    def _concatenarFuncion(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            nombre_completo = str(rec.grupo) + ' - ' + rec.descripcion
            result[rec.id] = nombre_completo.strip()
        return result

    _columns = {
        'grupo': fields.integer(u'Grupo', size=2, required=True),
        'descripcion': fields.char(u'Descripción', size=128,required=True),
        'name': fields.function(_concatenarFuncion, type='char', method=True, string='Nombre', store=True, readonly=True),
    }

class account_retention_creditors(osv.osv):
    _name = "account.retention.creditors"
    _description = "Acreedores de retenciones"
    _order = "id desc"
    _rec_name = 'nombre_completo'

    def _concatenarFuncion(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            nombre_completo = rec.acreedor + ' - ' + rec.name
            result[rec.id] = nombre_completo.strip()
        return result

    _columns = {
        'name': fields.char(u'Descripción',size=128,required=True),
        'acreedor': fields.char(u'Acreedor por retención',size=3),
        'clase': fields.char(u'Clase',size=3),
        'ruc': fields.char(u'RUC',size=11),
        'operacion': fields.char(u'Operación',size=128),
        'banco': fields.integer(u'Banco',size=10),
        'agencia': fields.integer(u'Agencia',size=10),
        'tipo_cuenta': fields.selection([('C', u'Cuenta corriente'), ('A', u'Caja de ahorros')],string=u'Tipo de cuenta', select=True),
        'fecha_vigencia': fields.date(u'Fecha vigencia',required=True),
        'cuenta_corriente':fields.char('Cuenta corriente', size=256),
        'bank_id':fields.many2one('res.bank', string='Banco'),
        'currency_id':fields.many2one('res.currency', string='Moneda'),
        'group_id':fields.many2one('account.group.creditors', string=u'Descripción', required=True),
        'codigo_grupo':fields.related('group_id','grupo',type='integer',string=u'Grupo'),
        'nombre_completo': fields.function(_concatenarFuncion, type='char', method=True, string=u'Nombre', store=True, readonly=True),
        'account_id': fields.many2one('account.account', string='Cuenta contable', domain=[('type','!=','view')]),
        }

    _defaults = {
        'fecha_vigencia': lambda *a: (datetime.datetime.now() + datetime.timedelta(365)).strftime("%Y-%m-%d")
        }

    _sql_constraints = [
        ('unique_creditor_group', 'unique(group_id,acreedor)', _(u'El acreedor por grupo debe ser único.')),
        ]

account_retention_creditors()
