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

from openerp.osv import fields, osv

class grp_diarios_pagos_config(osv.osv):
    _name = 'grp.diarios.pagos.config'
    _description = 'Configuracion diarios de pagos'

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        res = []
        reads = self.browse(cr, uid, ids, context=context)
        for record in reads:
            name = '%s - %s - %s' % (record.journal_id.name , record.siif_tipo_ejecucion_id.name, record.siif_codigo_sir.codigo or '')
            res.append((record.id, name))
        return res

    _columns = {
        'journal_id': fields.many2one('account.journal', u'Banco',ondelete='cascade', required=1),
        'siif_concepto_gasto_id': fields.many2one('presupuesto.concepto', u'Concepto de Gasto', required=1),
        'siif_tipo_ejecucion_id': fields.many2one('tipo.ejecucion.siif', u'Tipo de Ejecución', required=1),
        'siif_codigo_sir': fields.many2one("codigo.sir.siif", string=u'Código SIR', required=1),
        'company_id': fields.many2one('res.company', u'Compañía',required=1),
    }

    _defaults={
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    _order = "id desc"
    _sql_constraints = [
        ('payment_company_config_uniq', 'unique (journal_id, siif_concepto_gasto_id, siif_tipo_ejecucion_id, siif_codigo_sir, company_id)',
         u'La configuración de Diarios debe ser única por compañía!')
    ]

grp_diarios_pagos_config()