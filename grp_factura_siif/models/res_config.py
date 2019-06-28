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

class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'

    _columns = {
        'integracion_siif': fields.related('company_id', 'integracion_siif',
                                           type='boolean',string=u'Esta compañía tiene integración con SIIF'),
        'exceptuado_sice': fields.related('company_id', 'exceptuado_sice',
                                          type='boolean', string=u'Exceptuado SICE'),
        'unverified_context': fields.related('company_id', 'unverified_context',
                                             type='boolean', string=u'Deshabilitar validación certificado ssl'),
        'siif_concepto_gasto_lng': fields.related('company_id', 'siif_concepto_gasto_lng', type='many2one', relation='presupuesto.concepto', string = 'Concepto del Gasto para LNG'),
        'siif_concepto_gasto_aof': fields.related('company_id', 'siif_concepto_gasto_aof',  type='many2one', relation='presupuesto.concepto', string = 'Concepto del Gasto para AOF'),
        'product_id_lng': fields.related('company_id', 'product_id_lng',  type='many2one', relation='product.product', string ='Producto para LNG'),
        'product_id_aof': fields.related('company_id', 'product_id_aof',  type='many2one', relation='product.product', string ='Producto para AOF'),
        'journal_id_obl_siif': fields.related('company_id', 'journal_id_obl_siif', type='many2one', relation='account.journal', string='Diario para Obligaciones SIIF Alquileres'),
        'journal_id_obl_siif_lic': fields.related('company_id', 'journal_id_obl_siif_lic', type='many2one',
                                              relation='account.journal', string='Diario para Obligaciones SIIF Licencias')
    }

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        res = super(account_config_settings, self).onchange_company_id(cr, uid, ids, company_id, context=context)
        if company_id:
            company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
            res['value'].update({'integracion_siif': company.integracion_siif or False})
            res['value'].update({'exceptuado_sice': company.exceptuado_sice or False})
            res['value'].update({'unverified_context': company.unverified_context or False})
            res['value'].update({'siif_concepto_gasto_lng': company.siif_concepto_gasto_lng.id or False})
            res['value'].update({'siif_concepto_gasto_aof': company.siif_concepto_gasto_aof.id or False})
            res['value'].update({'product_id_lng': company.product_id_lng.id or False})
            res['value'].update({'product_id_aof': company.product_id_aof.id or False})
            res['value'].update({'journal_id_obl_siif': company.journal_id_obl_siif.id or False})
            res['value'].update({'journal_id_obl_siif_lic': company.journal_id_obl_siif_lic.id or False})
        else:
            res['value'].update({'integracion_siif': False})
            res['value'].update({'exceptuado_sice': False})
            res['value'].update({'unverified_context': False})
            res['value'].update({'siif_concepto_gasto_lng': False})
            res['value'].update({'siif_concepto_gasto_aof': False})
            res['value'].update({'product_id_lng': False})
            res['value'].update({'product_id_aof': False})
            res['value'].update({'journal_id_obl_siif': False})
            res['value'].update({'journal_id_obl_siif_lic': False})
        return res

account_config_settings()
