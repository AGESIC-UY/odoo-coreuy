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
import time
from openerp import netsvc, api, fields as fields_new_api
from lxml import etree
from presupuesto_estructura import TIPO_DOCUMENTO
from openerp.exceptions import ValidationError
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)


class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(account_invoice, self).fields_view_get(cr = cr, uid=uid, view_id=view_id, view_type=view_type,
                                                                            toolbar=toolbar, submenu=submenu,context=context)
        if res.get('toolbar', False) and context.get('listado_doc_pagar'):
            res['toolbar']['action'] = []
            res['toolbar']['print'] = []
        return res

    def _get_default_fiscal_year(self, cr, uid, context=None):
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id

        fiscal_year_id = fiscalyear_obj.search(cr, uid,
                                               [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
                                                ('company_id', '=', uid_company_id)], context=context)
        return fiscal_year_id and fiscal_year_id[0] or False

    def _get_default_inciso(self, cr, uid, context=None):
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')

        fecha_hoy = time.strftime('%Y-%m-%d')
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        uid_company_id = company_id.id

        fiscal_year_id = fiscalyear_obj.search(cr, uid,
                                               [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
                                                ('company_id', '=', uid_company_id)], context=context)
        fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
        ids_pres_inciso = []  # inicializado por error en default
        if fiscal_year_id:
            ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id', '=', fiscal_year_id),('inciso','=',company_id.inciso)])
        return len(ids_pres_inciso) == 1 and ids_pres_inciso[0] or False

    def _get_default_ue(self, cr, uid, context=None):
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')
        pres_ue_obj = self.pool.get('grp.estruc_pres.ue')

        fecha_hoy = time.strftime('%Y-%m-%d')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = user.company_id
        uid_company_id = company_id.id

        fiscal_year_id = fiscalyear_obj.search(cr, uid,
                                               [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
                                                ('company_id', '=', uid_company_id)], context=context)
        fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
        ids_pres_ue = []
        if fiscal_year_id:
            ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id', '=', fiscal_year_id),('inciso','=',company_id.inciso)])
            if len(ids_pres_inciso) == 1:
                ids_pres_ue = pres_ue_obj.search(cr, uid, [('inciso_id', '=', ids_pres_inciso[0]),
                                                           ('ue', '=', user.default_operating_unit_id.unidad_ejecutora)])
        return len(ids_pres_ue) == 1 and ids_pres_ue[0] or False

    def _get_campos_fnc(self, cr, uid, ids, fields, args, context=None):
        res = {}
        for inv in self.browse(cr, uid, ids, context=context):
            res[inv.id] = {
                'nro_afectacion_fnc': inv.nro_afectacion,
                'monto_afectado_fnc': inv.monto_afectado,
                'nro_compromiso_fnc': inv.nro_compromiso,
                'monto_comprometido_fnc': inv.monto_comprometido,
            }
        return res


    def _get_total_llavep(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for llavep in invoice.llpapg_ids:
                total += llavep.importe
            res[invoice.id] = total
        return res

    # TODO SPRING 8 GAP 235 R si es el action de fr poner por defecto tipo_efecucion_siif en P - Fondo Rotatorio
    @api.model
    def _get_default_siif_tipo_ejecucion(self):
        tipo_ejecucion_siif_fr_id = False
        if self._context.get('apply_default_fr'):
            tipo_ejecucion_siif_fr_ids = self.env['tipo.ejecucion.siif'].search([('codigo','=','P')])
            if tipo_ejecucion_siif_fr_ids:
                tipo_ejecucion_siif_fr_id = tipo_ejecucion_siif_fr_ids[0]
                return tipo_ejecucion_siif_fr_id.id
        return tipo_ejecucion_siif_fr_id


    _columns = {
        'fiscalyear_siif_id': fields.many2one('account.fiscalyear', u'Año fiscal'),
        # 'etapa_del_gasto': fields.selection([('obligacion', u'Obligación'), ('3en1', u'3 en 1'),
        #                                      ], string=u'Etapa del gasto', help=u'Tipo de Etapa del Gasto'),

        'cesion_bank_id': fields.many2one('res.partner.bank', u'Cuenta beneficiario cesión'),
        'monto_cedido_embargado': fields.integer("Monto cedido/embargado"),
        'tc_presupuesto': fields.float('Tipo de cambio presupuesto', digits=(10, 5),
                                       help=u"Tipo de cambio presupuesto divisa de factura."),
        'fecha_tipo_cambio': fields.date('Fecha de tipo de cambio'),
        'rendido_siif': fields.boolean(size=64, string=u'Rendido SIIF'),

        'nro_afectacion': fields.integer(u'Nº afectación', size=6),  # size=12),
        'monto_afectado': fields.integer(u'Monto autorizado'),
        'nro_obligacion': fields.integer(u'Nº obligación', size=3),  # size=12),
        'nro_compromiso': fields.integer(u'Nº compromiso', size=3),  # size=12),
        'monto_comprometido': fields.integer('Monto comprometido'),

        'resultado': fields.char('Resultado SIIF'),
        'comentario_siif': fields.text(u'Comentario SIIF', size=250),
        'descripcion': fields.text(u'Descripción', size=100),

        'tipo_de_cambio': fields.float('Tipo de cambio', digits=(10, 5)),

        'nro_afectacion_fnc': fields.function(_get_campos_fnc, string=u'Nro afectación', type='integer',
                                              multi='campos'),
        'monto_afectado_fnc': fields.function(_get_campos_fnc, string=u'Monto autorizado', type='integer',
                                              multi='campos'),
        'nro_compromiso_fnc': fields.function(_get_campos_fnc, string=u'Nro compromiso', type='integer',
                                              multi='campos'),
        'monto_comprometido_fnc': fields.function(_get_campos_fnc, string='Monto comprometido', type='integer',
                                                  multi='campos'),
        'compromiso_id': fields.many2one('grp.compromiso', 'Nro Compromiso'),
        'afectacion_id': fields.related('compromiso_id', 'afectacion_id', type="many2one", relation="grp.afectacion",
                                        readonly="1", string=u'Nro Afectación SIIF'),
        'siif_concepto_gasto': fields.many2one("presupuesto.concepto", string='Concepto del gasto'),
        'siif_codigo_sir': fields.many2one("codigo.sir.siif", string=u'Código SIR'),
        'siif_financiamiento': fields.many2one("financiamiento.siif", string='Fuente de financiamiento'),
        'siif_tipo_documento': fields.many2one('tipo.documento.siif', u'Tipo documento SIIF',
                                               domain=[('visible_documento_obligacion', '=', True)]),
        'siif_nro_fondo_rot': fields.many2one("fondo.rotatorio.siif", string='Nro doc. fondo rotatorio'),
        'siif_ult_modif': fields.integer(u'Última modificación'),
        'siif_sec_obligacion': fields.char(u'Secuencial obligación'),
        'siif_descripcion': fields.text(u"Descripción SIIF", size=100),
        # 'tipo_ejecucion_codigo_rel': fields.related("siif_tipo_ejecucion", "codigo", type="char",
        #                                             string=u'Código tipo ejecución', readonly=True),

        'inciso_siif_id': fields.many2one('grp.estruc_pres.inciso', 'Inciso'),
        'ue_siif_id': fields.many2one('grp.estruc_pres.ue', 'Unidad ejecutora'),

        'nro_obl_sist_aux': fields.char(u'Nro Obligación Sist. Aux'),

        'anulacion_siif_log_ids': fields.one2many(
            'obligacion.anulacion.siif.log',
            'invoice_id',
            'Log anulaciones'),
        'llpapg_ids': fields.one2many('grp.compras.lineas.llavep', 'invoice_id', string=u'Líneas presupuesto'),
        'total_llavep': fields.function(_get_total_llavep, string='Total llave presupuestal', type='float',
                                        digits=(16, 0)),

        'obligacion_paga_tgn': fields.boolean(string=u'Obligación Paga por TGN', help=u'Obligación paga por TGN'),
        #RETENCIONES
        'ret_summary_line': fields.one2many('account.invoice.summary.ret', 'invoice_id', 'Summary Retention Lines'),
        'ret_summary_group_line': fields.one2many('account.invoice.summary.group.ret', 'invoice_id', 'Summary Group Retention Lines'),

        # Notas de crédito
        'nro_afectacion_original': fields.related('factura_original', 'nro_afectacion_fnc', type='integer', string=u'Nro afectación', readonly=True),
        'nro_compromiso_original': fields.related('factura_original', 'nro_compromiso_fnc', type='integer', string=u'Nro compromiso', readonly=True),
        'nro_obligacion_original': fields.related('factura_original', 'nro_obligacion', type='integer', string=u'Nro obligación', readonly=True),
        'monto_afectado_original': fields.related('factura_original', 'monto_afectado_fnc', type='integer', string=u'Monto autorizado', readonly=True),
        'monto_comprometido_original': fields.related('factura_original', 'monto_comprometido_fnc', type='integer', string=u'Monto comprometido', readonly=True),
        'concepto_siif_concepto_gasto': fields.related('siif_concepto_gasto', 'concepto', type='char', string=u'Código del concepto del gasto', readonly=True),

        'obligacion_afe_com_obl_por_ue_siif': fields.boolean(string=u'Obligación por UE SIIF', help=u'Obligación por UE SIIF'),

        'obligacion_original_borrada': fields.boolean(string=u"Obligación original borrada", default=False, copy=False),
    }

    _defaults = {
        'fiscalyear_siif_id': _get_default_fiscal_year,
        'fecha_tipo_cambio': fields.date.context_today,
        'diferent_currency': False,
        'inciso_siif_id': _get_default_inciso,
        'ue_siif_id': _get_default_ue,
        'obligacion_paga_tgn': False,
        'obligacion_afe_com_obl_por_ue_siif': False,
        # 'siif_tipo_ejecucion':_get_default_siif_tipo_ejecucion # TODO SPRING 8 GAP 235 R si es el action de fr poner por defecto tipo_efecucion_siif en P - Fondo Rotatorio
    }

    siif_tipo_ejecucion = fields_new_api.Many2one("tipo.ejecucion.siif",
                                          string=u'Tipo de ejecución',
                                          default=_get_default_siif_tipo_ejecucion)
    tipo_ejecucion_codigo_rel = fields_new_api.Char(related="siif_tipo_ejecucion.codigo",
                                            string=u'Código tipo ejecución',
                                            readonly=True)

    def onchange_fiscalyear_siif_id(self, cr, uid, ids, fiscalyear_siif_id,compromiso_id=False):
        vals = {}
        if ids:
            invoice = self.browse(cr, uid, ids[0])
            if not compromiso_id and (invoice.doc_type in ['obligacion_invoice','3en1_invoice'] or invoice.siif_tipo_ejecucion.codigo == 'P'):
                vals.update({'value':{'inciso_siif_id': False, 'ue_siif_id': False}})
                if not fiscalyear_siif_id:
                    return vals
                pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')
                pres_ue_obj = self.pool.get('grp.estruc_pres.ue')
                if fiscalyear_siif_id:
                    user = self.pool.get('res.users').browse(cr, uid, uid)
                    ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id','=', fiscalyear_siif_id),('inciso','=',user.company_id.inciso)])
                    if len(ids_pres_inciso) == 1:
                        vals['value'].update({'inciso_siif_id': ids_pres_inciso[0]})
                        ids_pres_ue = pres_ue_obj.search(cr, uid, [('inciso_id','=', ids_pres_inciso[0]),
                                                                   ('ue', '=', user.default_operating_unit_id.unidad_ejecutora)])
                        if len(ids_pres_ue) == 1:
                            vals['value'].update({'ue_siif_id': ids_pres_ue[0]})
                vals['value'].update({'llpapg_ids':[]})
        return vals

    def onchange_beneficiario_cesion_id(self, cr, uid, ids, beneficiario_cesion_id):
        result = {}
        result.setdefault('value', {})
        result['value'].update({'cesion_rupe_cta_bnc_id': False})
        if beneficiario_cesion_id:
            partner = self.pool.get('res.partner').browse(cr, uid, beneficiario_cesion_id)
            result['value'].update({'id_rupe_cesion_benef': partner.id_rupe or ''})
        return result

    def onchange_compromiso_id(self, cr, uid, ids, compromiso_id, context=None):
        result = {}
        result.setdefault('value', {})
        # 105 - Incidencia
        if context.get('doc_type', False) == '3en1_invoice':
            return result

        # desvincular existentes
        if ids:
            self.write(cr, uid, ids, {'llpapg_ids': [(5,)]}, context=context)
        if compromiso_id:
            compromiso = self.pool.get('grp.compromiso').browse(cr, uid, compromiso_id, context=None)
            result['value'].update({'fiscalyear_siif_id': compromiso.fiscalyear_siif_id.id})
            result['value'].update({'inciso_siif_id': compromiso.inciso_siif_id.id})
            result['value'].update({'ue_siif_id': compromiso.ue_siif_id.id})
            result['value'].update({'partner_id': compromiso.partner_id.id})
            if compromiso.currency_oc:
                result['value'].update({'currency_id': compromiso.currency_oc.id})
            result['value'].update({'siif_tipo_ejecucion': compromiso.siif_tipo_ejecucion.id,
                                    'siif_concepto_gasto': compromiso.siif_concepto_gasto.id,
                                    'siif_codigo_sir': compromiso.siif_codigo_sir.id,
                                    'siif_financiamiento': compromiso.siif_financiamiento.id,
                                    'siif_nro_fondo_rot': compromiso.siif_nro_fondo_rot.id,
                                    'tipo_ejecucion_codigo_rel': compromiso.tipo_ejecucion_codigo_rel,
                                    })
            result['value'].update({'nro_afectacion': compromiso.nro_afectacion_siif,
                                    'monto_afectado': compromiso.monto_afectado,
                                    'nro_compromiso': compromiso.nro_compromiso,
                                    'monto_comprometido': compromiso.monto_a_comprometer,
                                    'nro_afectacion_fnc': compromiso.nro_afectacion_siif,
                                    'monto_afectado_fnc': compromiso.monto_afectado,
                                    'nro_compromiso_fnc': compromiso.nro_compromiso,
                                    'monto_comprometido_fnc': compromiso.monto_a_comprometer,
                                    'operating_unit_id': compromiso.operating_unit_id.id
                                    })
            llavep_ids = []
            # llavep_ids.append(5)
            if compromiso.llpapg_ids:
                for llave in compromiso.llpapg_ids:
                    llavep_ids.append((0, 0, {
                        'disponible': llave.disponible,
                        'importe': llave.importe,
                        # MVARELA nuevos campos
                        'programa_id': llave.programa_id.id,
                        'odg_id': llave.odg_id.id,
                        'auxiliar_id': llave.auxiliar_id.id,
                        'proyecto_id': llave.proyecto_id.id,
                        'fin_id': llave.fin_id.id,
                        'mon_id': llave.mon_id.id,
                        'tc_id': llave.tc_id.id,
                    }))
                result['value'].update({'llpapg_ids': llavep_ids})
                # result['value'].update({'currency_id': compromiso.moneda and compromiso.moneda.id or False,'nro_afectacion': compromiso.nro_afectacion_siif or False,'monto_autorizado': compromiso.monto_divisa or 0})
        else:
            result['value'].update({'fiscalyear_siif_id': False})
            result['value'].update({'inciso_siif_id': False})
            result['value'].update({'ue_siif_id': False})
            result['value'].update({'siif_tipo_ejecucion': False,
                                    'siif_concepto_gasto': False,
                                    'siif_codigo_sir': False,
                                    'siif_financiamiento': False,
                                    'siif_nro_fondo_rot': False,
                                    'tipo_ejecucion_codigo_rel': False,
                                    'partner_id': False,
                                    })
        return result

    def on_change_apg(self, cr, uid, ids, apg_id, context=None):
        if ids:
            self.write(cr, uid, ids, {'llpapg_ids': [(5,)], 'invoice_line': [(5,)]}, context=context)
        result = {}
        result.setdefault('value', {})
        result['value'] = {'origin': False, 'nro_afectacion': False, 'monto_afectado': 0.0, 'invoice_line': [],
                           'llpapg_ids': []}
        if apg_id:
            apg = self.pool.get('grp.compras.apg').browse(cr, uid, apg_id, context=None)
            llavep_ids = []
            if apg.llpapg_ids:
                for llave in apg.llpapg_ids:
                    llavep_ids.append(({
                        'disponible': llave.disponible,
                        'importe': llave.importe,
                        # MVARELA nuevos campos
                        'programa_id': llave.programa_id.id,
                        'odg_id': llave.odg_id.id,
                        'auxiliar_id': llave.auxiliar_id.id,
                        'proyecto_id': llave.proyecto_id.id,
                        'fin_id': llave.fin_id.id,
                        'mon_id': llave.mon_id.id,
                        'tc_id': llave.tc_id.id,
                    }))
                result['value'].update({'llpapg_ids': llavep_ids})
            lines = []
            if apg.lprapg_ids:
                for line_resumen in apg.lprapg_ids:
                    res = self.pool.get('product.product').browse(cr, uid, line_resumen.product_id.id, context=context)
                    a = res.property_account_expense.id
                    if not a:
                        a = res.categ_id.property_account_expense_categ.id
                    lines.append((0, 0, {
                        'name': line_resumen.product_id.name,
                        'origin': line_resumen.apg_id.name,
                        'invoice_line_tax_id': [(6, 0, [x.id for x in line_resumen.iva])],
                        'uos_id': line_resumen.uom_id.id,
                        'product_id': line_resumen.product_id.id,
                        'account_id': a,
                        'price_unit': line_resumen.precio_estimado,
                        'price_subtotal': line_resumen.subtotal_divisa,
                        'quantity': line_resumen.cantidad_a_comprar,
                    }))
                result['value'].update({'invoice_line': lines})
            result['value'].update({'descripcion': apg.descripcion or ''})
            result['value'].update({'origin': apg.name, 'nro_afectacion': apg.nro_afectacion_siif or False})
            result['value'].update(
                {'fiscalyear_siif_id': apg.fiscalyear_siif_id and apg.fiscalyear_siif_id.id or False})
            result['value'].update({'inciso_siif_id': apg.inciso_siif_id.id})
            result['value'].update({'ue_siif_id': apg.ue_siif_id.id})
            result['value'].update({'currency_id': apg.moneda.id})
        return result

    def onchange_tipo_ejecucion(self, cr, uid, ids, siif_tipo_ejecucion_id):
        result = {}
        if siif_tipo_ejecucion_id:
            tipo_ejecucion_obj = self.pool.get('tipo.ejecucion.siif')
            tipo_ejecucion = tipo_ejecucion_obj.browse(cr, uid, siif_tipo_ejecucion_id)
            result['value'] = {'tipo_ejecucion_codigo_rel': tipo_ejecucion.codigo}
            #MVARELA Si es Clearing borro el codigo sir, ya que no se manda
            if tipo_ejecucion.codigo == 'R':
                result['value']['siif_codigo_sir'] = False
        else:
            result['value'] = {'tipo_ejecucion_codigo_rel': False}
        return result

    #TODO: Revisar valores hardcoded
    def onchange_siif_financiamiento(self, cr, uid, ids, siif_financiamiento_id):
        vals = {'value':{} }
        if not siif_financiamiento_id:
            return vals
        financiamiento_obj = self.pool.get('financiamiento.siif')
        codigo_sir_obj = self.pool.get('codigo.sir.siif')
        financ = financiamiento_obj.browse(cr, uid, siif_financiamiento_id)
        vals['value'].update({'siif_codigo_sir': False})
        if financ.codigo == '11':
            cod_sir_id = codigo_sir_obj.search(cr, uid, [('codigo','=','05004111520028920'),('visible_documento','=',True)])
            cod_sir_id = cod_sir_id and cod_sir_id[0] or False
            vals['value'].update({'siif_codigo_sir': cod_sir_id})
        return vals

    def open_factura_grp(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        for factura in self.browse(cr, uid, ids, context=context):
            context['default_type'] = 'in_invoice'
            context['type'] = 'in_invoice'
            context['journal_type'] = 'purchase'
            if factura.doc_type == 'invoice':
                res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
                return {
                    'name': 'Factura de Proveedores',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_id': [res and res[1] or False],
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'res_id': factura.id,
                    'target': 'new',
                    'nodestroy': True,
                    'context': "{}",
                }
            if factura.doc_type == 'obligacion_invoice':
                res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif', 'view_account_form_obligacion')
                return {
                    'name': u'Obligación',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_id': [res and res[1] or False],
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'res_id': factura.id,
                    'target': 'new',
                    'nodestroy': True,
                    'context': "{}",
                }
            if factura.doc_type == '3en1_invoice':
                res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif', 'view_account_form_obligacion')
                return {
                    'name': u'3 en 1',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_id': [res and res[1] or False],
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'res_id': factura.id,
                    'target': 'new',
                    'nodestroy': True,
                    'context': "{'doc_type':'3en1_invoice'}",
                }

    # Crear el numero cuando se contabiliza en caso de no tener numero
    def action_move_create(self, cr, uid, ids, context=None):
        # send super create retentions
        if context is None:
            context = {}
        context=dict(context)
        res = super(account_invoice, self).action_move_create(cr, uid, ids, context)
        invoices = self.browse(cr, uid, ids, context=context)
        for inv in invoices:
            if inv.doc_type in ('obligacion_invoice','3en1_invoice') and not inv.nro_factura_grp:
                values = {}
                #MVARELA se agrega el año fiscal para la secuencia
                context.update({'fiscalyear_id': inv.fiscalyear_siif_id and inv.fiscalyear_siif_id.id or False})
                if inv.doc_type == 'obligacion_invoice':
                    values['nro_factura_grp'] = self.pool.get('ir.sequence').get(cr, uid, 'sec.obligacion',context=context)
                elif inv.doc_type == '3en1_invoice':
                    values['nro_factura_grp'] = self.pool.get('ir.sequence').get(cr, uid, 'sec.3en1',context=context)
                if values.get('nro_factura_grp',False):
                    self.write(cr, uid, inv.id, values, context=context)

            if inv.type in ('in_invoice'):
                for inv_line in inv.invoice_line:
                    name_first_line = inv_line.name
                    break
                ref_move = inv.doc_type == 'invoice' and ('%s %s'%(inv.serie_factura,inv.supplier_invoice_number)) or name_first_line
                self.pool.get('account.move').write(cr, uid, inv.move_id.id,{'ref': ref_move})

        return res

    # Si es fondo rotatorio no se generan los asientos de pago de las retenciones
    def action_move_retention_create(self, cr, uid, ids, context=None):
        '''
        Create retention moves for each item
        Se tiene en cuenta el multicurrency, chaviano
        '''
        # Comprobar si habria que pasar algun flag para las retenciones a cargar en el reporte
        for invoice in self.browse(cr, uid, ids, context=context):
            if invoice.siif_tipo_ejecucion and invoice.siif_tipo_ejecucion.codigo == 'P':
                continue
        if not any(context):
            super(account_invoice, self).action_move_retention_create(cr, uid, [invoice.id],
                                                                      context={'invoice_id': invoice})
        else:
            extended_context = context.copy()
            extended_context['invoice_id'] = invoice
            super(account_invoice, self).action_move_retention_create(cr, uid, [invoice.id], extended_context)
        return True

    def invoice_pay_adjustment(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'facturas_uy',
                                                                             'view_vendor_receipt_dialog_tc_up_form')
        inv = self.browse(cr, uid, ids[0], context=context)

        usd_fondo_rot = False
        if inv.siif_tipo_ejecucion and inv.siif_tipo_ejecucion.codigo == 'P' and inv.currency_id.id != inv.company_id.currency_id.id:
            usd_fondo_rot = True

        return {
            'name': _("Pay Invoice"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'payment_expected_currency': inv.currency_id.id,
                'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id,
                'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,

                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'default_type': inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
                'default_usd_fondo_rot': usd_fondo_rot,
                'usd_fondo_rot': usd_fondo_rot,
                'reference': inv.supplier_invoice_number,
                'default_reference': inv.supplier_invoice_number,
                'default_comment': 'Diferencia de Cambio',
            }
        }

    def invoice_sice_temp(self, cr, uid, ids, context=None):
        #TODO: ver que hacia el metodo button_reset_pc_llave_invoice que no esta definido
        #self.button_reset_pc_llave_invoice(cr, uid, ids, context=context)
        if context is None:
            context = {}
        for inv in self.browse(cr, uid, ids, context=context):
            # Se agrega el año fiscal para la secuencia
            context.update({'fiscalyear_id': inv.fiscalyear_siif_id.id})
            if not inv.supplier_invoice_number:
                raise osv.except_osv(_('Error!'),_(u'Por favor ingrese el nro de factura del proveedor.'))
            if not inv.serie_factura:
                raise osv.except_osv(_('Error!'),_(u'Por favor ingrese la serie de la factura.'))
        return super(account_invoice, self).invoice_sice_temp(cr, uid, ids, context=context)

    def invoice_sice(self, cr, uid, ids, context=None):
        self.check_amount(cr, uid, ids, context=context) #RAGU verificar monto en el boton SICE
        if context is None:
            context = {}
        for inv in self.browse(cr, uid, ids, context=context):
            # Se agrega el año fiscal para la secuencia
            context.update({'fiscalyear_id': inv.fiscalyear_siif_id.id})
        return super(account_invoice, self).invoice_sice(cr, uid, ids, context=context)

    def invoice_impactar_presupuesto(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context = dict(context)
        estructura_obj = self.pool.get('presupuesto.estructura')
        tipo = 'doc_type' in context and context.get('doc_type', False)
        for invoice in self.browse(cr, uid, ids, context=context):
            if tipo and not invoice.nro_factura_grp:
                values = {}
                # Se agrega el año fiscal para la secuencia
                context.update({'fiscalyear_id': invoice.fiscalyear_siif_id and invoice.fiscalyear_siif_id.id or False})
                if tipo == 'obligacion_invoice':
                    values['nro_factura_grp'] = self.pool.get('ir.sequence').get(cr, uid, 'sec.obligacion', context=context)
                elif tipo == '3en1_invoice':
                    values['nro_factura_grp'] = self.pool.get('ir.sequence').get(cr, uid, 'sec.3en1', context=context)
                if values.get('nro_factura_grp', False):
                    self.write(cr, uid, ids, values, context=context)

            # Se obliga en el presupuesto
            # Control 1: que la sumatoria de llave sea igual al totoal a reponer
            if invoice.diferent_currency and invoice.siif_tipo_ejecucion.codigo == 'P':
                if invoice.total_llavep <> invoice.total_reponer:
                    raise osv.except_osv(('Error'), ('La sumatoria de importes de llaves presupuestales no es igual al total a reponer.'))
            else:
                if invoice.total_llavep <> invoice.total_nominal:
                    raise osv.except_osv(('Error'), ('La sumatoria de importes de llaves presupuestales no es igual al monto de la factura.'))

            for llave in invoice.llpapg_ids:

                estructura = estructura_obj.obtener_estructura(cr, uid, invoice.fiscalyear_siif_id.id,
                                                               invoice.inciso_siif_id.inciso,
                                                               invoice.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto,
                                                               llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)

                # Control 2: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                        (invoice.fiscalyear_siif_id.code, invoice.inciso_siif_id.inciso, invoice.ue_siif_id.ue,
                         llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                    raise osv.except_osv(('Error'), (u'No se encontró estructura con la llave presupuestal asociada a la factura: ' + desc_error))

                # Control 3: que no alcance el disponible para el monto de la llave presupuestal
                # TODO: MVARELA, se comenta pero se deberia hacer el control con el campo Objeto específico
                # if fact.doc_type=='3en1_invoice' and estructura.disponible < llave.importe:
                #     raise osv.except_osv(('Error'), (
                #         'El disponible de la estructura no es suficiente para cubrir el importe de la llave presupuestal.'))

                #Se cambia el importe a negativo si es reduccion o devolucion al credito
                if invoice.tipo_nota_credito in ('R', 'D'):
                    importe = -llave.importe
                else:
                    importe = llave.importe

                # Se obliga en el presupuesto, si es 3en1 se afecta, compromete y obliga
                if invoice.doc_type == '3en1_invoice' or (invoice.doc_type == 'ajuste_invoice' and invoice.factura_original.doc_type == '3en1_invoice'):
                    res_af = estructura_obj.afectar(cr, uid, invoice.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                    importe,
                                                    estructura)
                    res_comp = estructura_obj.comprometer(cr, uid, invoice.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                          importe,
                                                          estructura)
                    res_obligar = estructura_obj.obligar(cr, uid, invoice.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                         importe,
                                                         estructura)
                else:
                    res_obligar = estructura_obj.obligar(cr, uid, invoice.id, TIPO_DOCUMENTO.FACTURA,
                                                         importe,
                                                         estructura)
        return True

    def invoice_enviar_siif(self, cr, uid, ids, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for factura in self.browse(cr, uid, ids, context):
            if factura.nro_obligacion:
                raise osv.except_osv("Error", "Este documento ya ha sido enviado a SIIF. Por favor, actualice el navegador.")
            if not factura.beneficiario_siif_id.tipo_doc_rupe and not factura.beneficiario_siif_id.es_inciso_default:
                raise osv.except_osv((''), (u'El beneficiario debe tener configurado tipo y número de documento de RUPE.'))
            if not factura.beneficiario_siif_id.nro_doc_rupe and not factura.beneficiario_siif_id.es_inciso_default:
                raise osv.except_osv((''), (u'El beneficiario debe tener configurado tipo y número de documento de RUPE.'))
            if factura.siif_tipo_documento.codigo == '22': #22 - Factura
                if not factura.serie_factura:
                    raise osv.except_osv((''), (u'La factura debe tener configurado serie y/o secuencia.'))
                if not factura.supplier_invoice_number:
                    raise osv.except_osv((''), (u'La factura debe tener configurado el nro de factura del proveedor.'))
                # Validacion factura de proveedor
                if not factura.siif_tipo_ejecucion.codigo == 'R':
                    if len(factura.supplier_invoice_number) > 8:
                        raise osv.except_osv(_('Error!'),
                                             _(u'El campo Nro. Factura Proveedor no debe ser mayor a 8 caracteres.'))

            tipo_doc_grp = '03'
            if factura.doc_type == '3en1_invoice':
                tipo_doc_grp = '04'
            if factura.doc_type == 'obligacion_invoice':
                tipo_doc_grp = '05'
            if factura.doc_type == 'opi_invoice':
                tipo_doc_grp = '05'

            # retenciones: Lista de retenciones a enviar (cada elemento es un diciconario)
            # ret_creditor_id: diccionario que guarda en que posicion de la lista se encuetra la retencion para el acreedor (se agrupan por acreedor)
            retenciones = []
            ret_creditor_id = {}
            for retencion in factura.ret_summary_group_line:
                if retencion.ret_amount_pesos_round > 0:
                    if retencion.tipo_retencion == 'siif':
                        if retencion.retention_id.base_compute == 'ret_tax':
                            base_imp = retencion.base_impuesto_pesos
                            base_imp_mon_ext = retencion.base_impuesto
                        else:
                            base_imp = retencion.base_linea_pesos
                            base_imp_mon_ext = retencion.base_linea
                        ret = {
                            'grupo': retencion.group_id.grupo,
                            'acreedor': retencion.creditor_id.acreedor,
                            'monto': retencion.ret_amount_pesos_round,
                            'base_impuesto': base_imp,
                            'es_manual': False,
                        }
                        if factura.currency_id.name != 'UYU':
                            ret['base_impuesto_mont_ext'] = base_imp_mon_ext
                    else:
                        ret = {
                            'grupo': retencion.group_id.grupo,
                            'acreedor': retencion.creditor_id.acreedor,
                            'monto': retencion.ret_amount_pesos_round,
                            'base_impuesto': retencion.ret_amount_pesos_round,
                            'es_manual': True,
                        }
                    # si todavia no se cargo una retencion para el acreedor la inserto en la lista y actualizo el diccionario
                    if retencion.creditor_id.id not in ret_creditor_id:
                        ret_creditor_id[retencion.creditor_id.id] = len(retenciones)
                        retenciones.append(ret)
                    # si ya se cargo una retencion para el acreedor actualizo los valores monto y base impuesto sumando los nuevos valores
                    else:
                        retenciones[ret_creditor_id[retencion.creditor_id.id]]['monto'] += ret['monto']
                        retenciones[ret_creditor_id[retencion.creditor_id.id]]['base_impuesto'] += ret['base_impuesto']

            # Control de no enviar llave presupuestal vacia
            if len(factura.llpapg_ids) == 0:
                raise osv.except_osv(('Error'),
                                     (u'Debe cargar al menos una llave presupuestal.'))

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if factura.siif_financiamiento.exceptuado_sice or factura.siif_tipo_ejecucion.exceptuado_sice or factura.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in factura.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name', '=', llave_pres.odg),
                                                                         ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise osv.except_osv(('Error'),
                                             (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                             llave_pres.odg, llave_pres.auxiliar))

            # se obliga contra el SIIF

            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': factura.fiscalyear_siif_id and factura.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_obl_sist_aux = self.pool.get('ir.sequence').get(cr, uid, 'sec.siif.obligacion', context=context)
            nro_obl_sist_aux = nro_obl_sist_aux[4:]

            xml_obligacion = generador_xml.gen_xml_obligacion(cr, uid, factura=factura, llaves_presupuestales=factura.llpapg_ids,
                                              importe=factura.amount_ttal_liq_pesos, nro_carga=nro_carga, tipo_doc_grp=tipo_doc_grp,
                                              nro_modif_grp=0,
                                              tipo_modificacion='A',
                                              retenciones=retenciones,
                                              enviar_datos_sice=enviar_datos_sice,
                                              nro_obl_sist_aux=nro_obl_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_obligacion)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_afectacion', None) is None and movimiento.find(
                        'nro_afectacion').text and movimiento.find('nro_afectacion').text.strip():
                    dicc_modif['nro_afectacion'] = movimiento.find('nro_afectacion').text
                if dicc_modif.get('nro_compromiso', None) is None and movimiento.find(
                        'nro_compromiso').text and movimiento.find('nro_compromiso').text.strip():
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('nro_obligacion', None) is None and movimiento.find(
                        'nro_obligacion').text and movimiento.find('nro_obligacion').text.strip():
                    dicc_modif['nro_obligacion'] = movimiento.find('nro_obligacion').text
                if dicc_modif.get('resultado', None) is None and movimiento.find(
                        'resultado').text and movimiento.find('resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_obligacion', None) is None and movimiento.find(
                        'sec_obligacion').text and movimiento.find('sec_obligacion').text.strip():
                    dicc_modif['siif_sec_obligacion'] = movimiento.find('sec_obligacion').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al obligar en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_obligacion', None) and dicc_modif.get('nro_compromiso', None) \
                        and dicc_modif.get('nro_afectacion', None) and dicc_modif.get('resultado', None):
                    break

            # error en devolucion de numero de obligacion
            if not dicc_modif.get('nro_obligacion', None):
                raise osv.except_osv(('Error al obligar en SIIF'),
                                     (descr_error or u'Error en devolución de número de obligación por el SIIF'))

            # Enviar factura como 3 en 1, actualizar Monto Autorizado y Comprometido, condicion de factura y etapa del gasto = 3en1
            if factura.doc_type == '3en1_invoice':
                dicc_modif['monto_afectado'] = factura.total_nominal
                dicc_modif['monto_comprometido'] = factura.total_nominal
                # Cambios para cuando factura en USD y es fondo rotatorio
                if factura.siif_tipo_ejecucion.codigo == 'P' and factura.currency_id.id != factura.company_id.currency_id.id:
                    dicc_modif['monto_afectado'] = int(round(factura.total_reponer, 0))
                    dicc_modif['monto_comprometido'] = int(round(factura.total_reponer, 0))

            dicc_modif['nro_obl_sist_aux'] = nro_obl_sist_aux

            # Es fondo rotatorio - cambiar flag rendido para OPI, Obligacion y 3en1
            if factura.tipo_ejecucion_codigo_rel == 'P' and factura.doc_type != 'invoice':
                dicc_modif['rendido_siif'] = True

            res_write_factura = self.write(cr, uid, [factura.id], dicc_modif, context=context)

            if res_write_factura:
                modif_obligacion_log_obj = self.pool.get('wiz.modif_obligacion_siif_log')
                for llave in factura.llpapg_ids:
                    vals = {
                        'invoice_id': factura.id,
                        'tipo': 'A',
                        'fecha': fields.date.context_today(self, cr, uid, context=context),
                        'programa': llave.programa,
                        'proyecto': llave.proyecto,
                        'moneda': llave.mon,
                        'tipo_credito': llave.tc,
                        'financiamiento': llave.fin,
                        'objeto_gasto': llave.odg,
                        'auxiliar': llave.auxiliar,
                        'importe': llave.importe,
                        'siif_sec_obligacion': dicc_modif.get('siif_sec_obligacion', False),
                        'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                    }
                    modif_obligacion_log_obj.create(cr, uid, vals, context=context)
        return True

    def btn_obligar(self, cr, uid, ids, context=None):
        ctx_check_ajuste = dict(context)
        ctx_check_ajuste.update({'metodo': 'obligar'})
        self.check_ajuste_consolidado(cr, uid, ids, context=ctx_check_ajuste)
        res = super(account_invoice, self).btn_obligar(cr, uid, ids, context=context)

        self.invoice_impactar_presupuesto(cr, uid, ids, context=context)

        # Se valida antes de enviar a SIIF por si da error
        # Se valida la factura si no es fondo rotatorio
        for factura in self.browse(cr, uid, ids, context=context):
            doc_type = context.get('type', False)
            if doc_type in ['in_invoice']:
                if factura.state in ['sice'] and factura.tipo_ejecucion_codigo_rel not in ['P', 'R']\
                   and not factura.compromiso_proveedor_id:
                    raise osv.except_osv(u'El campo Compromiso proveedor es requerido.'
                                         u' Por favor, ingrese valor para el campo.')
                if factura.state in ['sice'] and factura.tipo_ejecucion_codigo_rel not in ['P']\
                   and not factura.siif_tipo_documento:
                    raise osv.except_osv(u'El campo Tipo de documento es requerido.'
                                         u' Por favor, ingrese valor para el campo.')
                if factura.state in ['sice'] and factura.tipo_ejecucion_codigo_rel not in ['P', 'R']\
                   and not factura.siif_descripcion:
                    raise osv.except_osv(u'El campo Descripcion SIIF es requerido.'
                                         u' Por favor, ingrese valor para el campo.')
            if factura.tipo_ejecucion_codigo_rel != 'P':
                if not factura.move_id:
                    wf_service = netsvc.LocalService('workflow')
                    wf_service.trg_validate(uid, 'account.invoice', factura.id, 'invoice_open', cr)
                else:
                    self.write(cr, uid, [factura.id], {'state': 'open'}, context=context)

        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        integracion_siif = company.integracion_siif or False
        if not integracion_siif:
            return True
        else:
            return self.invoice_enviar_siif(cr, uid, ids, context=context)

    def invoice_cancel_presupuesto(self, cr, uid, ids, context=None):
        estructura_obj = self.pool.get('presupuesto.estructura')
        for invoice in self.browse(cr, uid, ids, context=context):

            # # Control 1: que la sumatoria de llave no sea la misma que el total nominal de la factura
            # if invoice.total_llavep <> invoice.total_nominal:
            #     raise osv.except_osv('Error', 'La sumatoria de importes de llaves presupuestales no es igual al monto de la factura.')

            for llave in invoice.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(cr, uid, invoice.fiscalyear_siif_id.id,
                                                               invoice.inciso_siif_id.inciso,
                                                               invoice.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                # Control 2: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (invoice.fiscalyear_siif_id.code, invoice.inciso_siif_id.inciso, invoice.ue_siif_id.ue,
                                  llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                    raise osv.except_osv(('Error'), (u'No se encontró estructura con la llave presupuestal asociada a la factura: ' + desc_error))

                # Control 3: que no alcance el disponible para el monto de la llave presupuestal
                # TODO: MVARELA, se comenta pero se deberia hacer el control con el campo Objeto específico
                # if invoice.doc_type=='3en1_invoice' and estructura.disponible < llave.importe:
                #     raise osv.except_osv(('Error'), (
                #         'El disponible de la estructura no es suficiente para cubrir el importe de la llave presupuestal.'))
                # Mostrar error y salir del for

                #Se cambia el importe a negativo si es reduccion o devolucion al credito
                if invoice.tipo_nota_credito in ('R', 'D'):
                    importe = -llave.importe
                else:
                    importe = llave.importe

                # Se obliga en el presupuesto (* -1), si es 3en1 se afecta, compromete y obliga
                if invoice.doc_type == '3en1_invoice' or (invoice.doc_type == 'ajuste_invoice' and invoice.factura_original.doc_type == '3en1_invoice'):
                    res_af = estructura_obj.afectar(cr, uid, invoice.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                    -1 * importe, estructura)
                    res_comp = estructura_obj.comprometer(cr, uid, invoice.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                          -1 * importe, estructura)
                    res_obligar = estructura_obj.obligar(cr, uid, invoice.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                         -1 * importe, estructura)
                else:
                    res_obligar = estructura_obj.obligar(cr, uid, invoice.id, TIPO_DOCUMENTO.FACTURA,
                                                         -1 * importe, estructura)
        return True

    def invoice_cancel_siif(self, cr, uid, ids, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for invoice in self.browse(cr, uid, ids, context):
            # se afecta contra el SIIF
            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': invoice.fiscalyear_siif_id and invoice.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            monto_desobligar = 0
            for llave in invoice.llpapg_ids:
                monto_desobligar += llave.importe
            monto_desobligar *= -1

            nro_modif_grp = invoice.siif_ult_modif + 1

            tipo_doc_grp = '03'
            if invoice.doc_type == '3en1_invoice':
                tipo_doc_grp = '04'
            if invoice.doc_type == 'obligacion_invoice':
                tipo_doc_grp = '05'
            if invoice.doc_type == 'opi_invoice':
                tipo_doc_grp = '05'
            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if invoice.siif_financiamiento.exceptuado_sice or invoice.siif_tipo_ejecucion.exceptuado_sice or invoice.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in invoice.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name', '=', llave_pres.odg),
                                                                         ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise osv.except_osv(('Error'),
                                             (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                             llave_pres.odg, llave_pres.auxiliar))
            # TODO: Estos campos no se si estan bien, retenciones vacio
            retenciones = []

            xml_cancel_obligacion = generador_xml.gen_xml_obligacion(cr, uid, factura=invoice,
                                                              llaves_presupuestales=invoice.llpapg_ids,
                                                              importe=monto_desobligar,
                                                              nro_carga=nro_carga, tipo_doc_grp=tipo_doc_grp,
                                                              nro_modif_grp=nro_modif_grp,
                                                              tipo_modificacion='N', es_modif=True,
                                                              motivo="Anulacion Obligacion",
                                                              retenciones=retenciones,
                                                              enviar_datos_sice=enviar_datos_sice,
                                                              nro_obl_sist_aux=invoice.nro_obl_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_cancel_obligacion)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_obligacion', None) is None and movimiento.find(
                        'nro_obligacion').text and movimiento.find('nro_obligacion').text.strip():
                    dicc_modif['nro_obligacion'] = movimiento.find('nro_obligacion').text
                if dicc_modif.get('resultado', None) is None and movimiento.find('resultado').text and movimiento.find(
                        'resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_obligacion', None) is None and movimiento.find(
                        'sec_obligacion').text and movimiento.find('sec_obligacion').text.strip():
                    dicc_modif['siif_sec_obligacion'] = movimiento.find('sec_obligacion').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv((u'Error al anular obligación en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_obligacion', None) and dicc_modif.get('resultado', None):
                    break

            # Historico
            anulacion_inv_log_obj = self.pool.get('obligacion.anulacion.siif.log')
            # anulacion_siif_log_ids
            vals_history = {
                'invoice_id': invoice.id,
                'nro_afectacion_siif': invoice.nro_afectacion or 0,
                'nro_compromiso': invoice.nro_compromiso or 0,
                'nro_obligacion': invoice.nro_obligacion or 0,
                'nro_obl_sist_aux': invoice.nro_obl_sist_aux or False,
            }
            id = anulacion_inv_log_obj.create(cr, uid, vals_history, context=context)


            dicc_modif.update({'nro_obl_sist_aux': False, 'nro_obligacion': False, 'state': 'cancel_siif'})

            # Por cada fila en Detalle Presupuestal, agrego la misma fila en Historico de Detalle Presupuestal con importe negativo
            for llavep in invoice.llpapg_ids:
                vals_history_detalle_pres = {
                    'tipo': 'N',
                    'invoice_id': llavep.invoice_id.id,
                    'odg': llavep.odg,
                    'auxiliar': llavep.auxiliar,
                    'fin': llavep.fin,
                    'programa': llavep.programa,
                    'proyecto': llavep.proyecto,
                    'mon': llavep.mon,
                    'tc': llavep.tc,
                    'importe': -llavep.importe
                }
            modif_obligacion_obj = self.pool.get('wiz.modif_obligacion_siif_log')
            id = modif_obligacion_obj.create(cr, uid, vals_history_detalle_pres, context=context)

            # Es fondo rotatorio - cambiar flag rendido para OPI, Obligacion y 3en1  en cancelacion
            if invoice.tipo_ejecucion_codigo_rel == 'P' and invoice.doc_type != 'invoice':
                dicc_modif['rendido_siif'] = False
            res_write = self.write(cr, uid, invoice.id, dicc_modif, context=context)

            # Actualizo estado de ajustes a Anulado SIIF
            ajuste_obj = self.pool.get('account.invoice')
            ajuste_obj_ids = ajuste_obj.search( cr, uid, [('factura_original','=', invoice.id)])
            if len(ajuste_obj_ids) > 0:
                ajuste_obj.write(cr, uid, ajuste_obj_ids, {'state': 'cancel_siif'}, context=context)

        return True

    def btn_cancel_obligacion(self, cr, uid, ids, context=None):
        res = super(account_invoice, self).btn_cancel_obligacion(cr, uid, ids, context=context)

        self.invoice_cancel_presupuesto(cr, uid, ids, context=context)

        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        integracion_siif = company.integracion_siif or False
        if not integracion_siif:
            return True
        else:
            return self.invoice_cancel_siif(cr, uid, ids, context=context)

    def invoice_borrar_siif(self, cr, uid, ids, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for invoice in self.browse(cr, uid, ids, context):
            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': invoice.fiscalyear_siif_id and invoice.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            # SE OBLIGA CONTRA SIIF
            nro_modif_grp = invoice.siif_ult_modif
            tipo_doc_grp = '03'
            if invoice.doc_type == '3en1_invoice':
                tipo_doc_grp = '04'
            if invoice.doc_type == 'obligacion_invoice':
                tipo_doc_grp = '05'
            if invoice.doc_type == 'opi_invoice':
                tipo_doc_grp = '05'

            enviar_datos_sice = False
            if invoice.siif_financiamiento.exceptuado_sice or invoice.siif_tipo_ejecucion.exceptuado_sice or invoice.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in invoice.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name', '=', llave_pres.odg),
                                                                         ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise osv.except_osv(('Error'),
                                             (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                             llave_pres.odg, llave_pres.auxiliar))

            xml_borrar_obligacion = generador_xml.gen_xml_borrado_obligacion(cr, uid, factura=invoice, nro_carga=nro_carga,
                                                                             tipo_doc_grp=tipo_doc_grp, nro_modif_grp=nro_modif_grp,
                                                                             nro_obl_sist_aux=invoice.nro_obl_sist_aux)
            resultado_siif = siif_proxy.put_solic(cr, uid, xml_borrar_obligacion)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            for movimiento in xml_root.findall('movimiento'):
                if movimiento.find('resultado').text == 'B':
                    dicc_modif['nro_obligacion'] = False
                    dicc_modif['siif_sec_obligacion'] = False
                    dicc_modif['siif_ult_modif'] = False
                    dicc_modif['nro_obl_sist_aux'] = False
                    # Historico
                    anulacion_inv_log_obj = self.pool.get('obligacion.anulacion.siif.log')
                    # anulacion_siif_log_ids
                    vals_history = {
                        'invoice_id': invoice.id,
                        'nro_afectacion_siif': invoice.nro_afectacion or 0,
                        'nro_compromiso': invoice.nro_compromiso or 0,
                        'nro_obligacion': invoice.nro_obligacion or 0,
                        'nro_obl_sist_aux': invoice.nro_obl_sist_aux or False,
                    }
                    id = anulacion_inv_log_obj.create(cr, uid, vals_history, context=context)
                    # Borrando valores
                    ids_delete = []
                    for idm in invoice.modif_obligacion_log_ids:
                        ids_delete.append(idm.id)
                    if ids_delete:
                        self.pool.get('wiz.modif_obligacion_siif_log').unlink(cr, uid, ids_delete)
                    # Si es fondo rotatorio se cambia el estado a 'paid'
                    if invoice.tipo_ejecucion_codigo_rel == 'P':
                        if invoice.doc_type != 'invoice':
                            dicc_modif['rendido_siif'] = False

                    res_write = self.write(cr, uid, invoice.id, dicc_modif, context=context)

                else:
                    descr_error = movimiento.find('comentario').text
                    raise osv.except_osv((u'Error al intentar borrar obligación en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))

            return True

    # Si se envio una obligacion consolidadda desde un ajuste
    # solo se permite borrar la obligacion desde el ajuste
    def check_ajuste_consolidado(self, cr, uid, ids, context=None):
        for invoice in self.browse(cr, uid, ids, context=context):
            ajuste_ids = self.search(cr, uid, [('factura_original', '=', invoice.id),
                                               ('obligacion_original_borrada', '=', True)], limit=1, context=context)
            if ajuste_ids:
                ajuste = self.browse(cr, uid, ajuste_ids[0], context=context)
                metodo = context.get('metodo', False)
                if metodo == 'obligar':
                    raise osv.except_osv(('Error'),
                                         (u'Esta obligación tiene asociado el Ajuste/NC: %s. Debe eliminarlo antes de obligar el documento original u obligar el consolidado desde el Ajuste/NC') % (
                                             ajuste.nro_factura_grp or ajuste.display_name,))
                else:
                    raise osv.except_osv(('Error'),
                                         (u'La obligación se envió consolidada con la nota de crédito(Ajuste de obligación): %s. Debe borrar la obligación desde el Ajuste de obligación') % (
                                             ajuste.nro_factura_grp or ajuste.display_name,))
        return True

    def btn_borrar_obligacion(self, cr, uid, ids, context=None):
        ctx_check_ajuste = dict(context)
        ctx_check_ajuste.update({'metodo': 'borrar'})
        self.check_ajuste_consolidado(cr, uid, ids, context=ctx_check_ajuste)
        self.invoice_cancel_presupuesto(cr, uid, ids, context=context)
        for invoice in self.browse(cr, uid, ids, context=context):
            #Se hace el cambio de estado antes de enviar SIIF, porque puede dar error en caso de extorno de asientos
            if invoice.tipo_ejecucion_codigo_rel == 'P':
                self.write(cr, uid, [invoice.id], {'state': 'paid'}, context=context)
            else:
                wf_service = netsvc.LocalService('workflow')
                wf_service.trg_validate(uid, 'account.invoice', invoice.id, 'invoice_cancel', cr)
                self.action_cancel_draft(cr, uid, [invoice.id])
                state = 'draft'
                if invoice.doc_type in ('obligacion_invoice', '3en1_invoice'):  # Obligacion y 3en1
                    state = 'draft'
                elif invoice.doc_type == 'invoice':  # Factura de Proveedor
                    state = 'sice'
                self.write(cr, uid, [invoice.id], {'state': state}, context=context)
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        integracion_siif = company.integracion_siif or False
        if not integracion_siif:
            return True
        else:
            return self.invoice_borrar_siif(cr, uid, ids, context=context)

    def btn_borrar_obligacion_original(self, cr, uid, ids, context=None):
        for nc in self.browse(cr, uid, ids, context=context):
            res = self.btn_borrar_obligacion(cr, uid, [nc.factura_original.id], context=context)
            self.write(cr, uid, [nc.id], {'obligacion_original_borrada': True}, context=context)
            return res

    def btn_obligar_consolidado(self, cr, uid, ids, context=None):

        for nota_credito in self.browse(cr, uid, ids, context=context):
            if nota_credito.factura_original.nro_obligacion:
                raise osv.except_osv(('Error'),
                                     (u'El documento origen no puede estar Obligado.'))
            # se impacta en el presupuesto la factura original y la nota de credito
            self.invoice_impactar_presupuesto(cr, uid, [nota_credito.factura_original.id], context=context)
            self.invoice_impactar_presupuesto(cr, uid, [nota_credito.id], context=context)
            #se contabiliza la nota de credito
            if not nota_credito.move_id:
                wf_service = netsvc.LocalService('workflow')
                wf_service.trg_validate(uid, 'account.invoice', nota_credito.id, 'invoice_open', cr)
            if not nota_credito.factura_original.move_id:
                wf_service = netsvc.LocalService('workflow')
                wf_service.trg_validate(uid, 'account.invoice', nota_credito.factura_original.id, 'invoice_open', cr)
            else:
                self.write(cr, uid, [nota_credito.factura_original.id], {'state': 'open'}, context=context)

            # Control de no enviar llave presupuestal vacia
            if len(nota_credito.llpapg_ids) == 0:
                raise osv.except_osv(('Error'),
                                     (u'Debe cargar al menos una llave presupuestal.'))
            # se obliga el consolidado entre la nota de credito y la factura original
            self.enviar_consolidado_siif(cr, uid, [nota_credito.id], context=context)
            # se actualizan campos correspondientes en la nota de credito
            # se actualizan campos correspondientes en la factura original
        return True

    def enviar_consolidado_siif(self, cr, uid, ids, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for nota_credito in self.browse(cr, uid, ids, context=context):
            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if nota_credito.factura_original.siif_financiamiento.exceptuado_sice or nota_credito.factura_original.siif_tipo_ejecucion.exceptuado_sice or nota_credito.factura_original.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in nota_credito.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name', '=', llave_pres.odg),
                                                                         ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise osv.except_osv(('Error'),
                                             (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                                 llave_pres.odg, llave_pres.auxiliar))

                for llave_orig in nota_credito.factura_original.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name', '=', llave_orig.odg),
                                                                         ('auxiliar', '=', llave_orig.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise osv.except_osv(('Error'),
                                             (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                                 llave_orig.odg, llave_orig.auxiliar))

            # Tipo de documento: Modificación de obligacion
            # Por mas que sea una obigacion nueva, quin lo manda a SIIF es el ajuste
            # Se envia como tipo ajuste para que el borrar desde el ajuste se mantengan los tipos
            if nota_credito.factura_original.doc_type == '3en1_invoice':
                tipo_doc_grp = '14'
            else:
                tipo_doc_grp = '13'

            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': nota_credito.factura_original.fiscalyear_siif_id and nota_credito.factura_original.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_obl_sist_aux = self.pool.get('ir.sequence').get(cr, uid, 'sec.siif.obligacion', context=context)
            nro_obl_sist_aux = nro_obl_sist_aux[4:]

            # retenciones: Lista de retenciones a enviar (cada elemento es un diciconario)
            # ret_creditor_id: diccionario que guarda en que posicion de la lista se encuetra la retencion para el acreedor (se agrupan por acreedor)
            # son las retenciones consolidadas entre factura y nota de credito
            retenciones = []
            ret_creditor_id = {}
            for retencion in nota_credito.factura_original.ret_summary_group_line:
                if retencion.ret_amount_pesos_round > 0:
                    if retencion.tipo_retencion == 'siif':
                        if retencion.retention_id.base_compute == 'ret_tax':
                            base_imp = retencion.base_impuesto_pesos
                            base_imp_mon_ext = retencion.base_impuesto
                        else:
                            base_imp = retencion.base_linea_pesos
                            base_imp_mon_ext = retencion.base_linea
                        ret = {
                            'grupo': retencion.group_id.grupo,
                            'acreedor': retencion.creditor_id.acreedor,
                            'monto': retencion.ret_amount_pesos_round,
                            'base_impuesto': base_imp,
                            'es_manual': False,
                        }
                        if nota_credito.factura_original.currency_id.name != 'UYU':
                            ret['base_impuesto_mont_ext'] = base_imp_mon_ext
                    else:
                        ret = {
                            'grupo': retencion.group_id.grupo,
                            'acreedor': retencion.creditor_id.acreedor,
                            'monto': retencion.ret_amount_pesos_round,
                            'base_impuesto': retencion.ret_amount_pesos_round,
                            'es_manual': True,
                        }
                    # si todavia no se cargo una retencion para el acreedor la inserto en la lista y actualizo el diccionario
                    if retencion.creditor_id.id not in ret_creditor_id:
                        ret_creditor_id[retencion.creditor_id.id] = len(retenciones)
                        retenciones.append(ret)
                    # si ya se cargo una retencion para el acreedor actualizo los valores monto y base impuesto sumando los nuevos valores
                    else:
                        retenciones[ret_creditor_id[retencion.creditor_id.id]]['monto'] += ret['monto']
                        retenciones[ret_creditor_id[retencion.creditor_id.id]]['base_impuesto'] += ret['base_impuesto']

            for retencion in nota_credito.ret_summary_group_line:
                if retencion.ret_amount_pesos_round != 0:
                    if retencion.tipo_retencion == 'siif':
                        if retencion.retention_id.base_compute == 'ret_tax':
                            base_imp = retencion.base_impuesto_pesos
                            base_imp_mon_ext = retencion.base_impuesto
                        else:
                            base_imp = retencion.base_linea_pesos
                            base_imp_mon_ext = retencion.base_linea
                        ret = {
                            'grupo': retencion.group_id.grupo,
                            'acreedor': retencion.creditor_id.acreedor,
                            'monto': -retencion.ret_amount_pesos_round,
                            'base_impuesto': -base_imp,
                            'es_manual': False,
                        }
                        if nota_credito.currency_id.name != 'UYU':
                            ret['base_impuesto_mont_ext'] = -base_imp_mon_ext
                    else:
                        ret = {
                            'grupo': retencion.group_id.grupo,
                            'acreedor': retencion.creditor_id.acreedor,
                            'monto': -retencion.ret_amount_pesos_round,
                            'base_impuesto': -retencion.ret_amount_pesos_round,
                            'es_manual': True,
                        }
                    # si todavia no se cargo una retencion para el acreedor la inserto en la lista y actualizo el diccionario
                    if retencion.creditor_id.id not in ret_creditor_id:
                        ret_creditor_id[retencion.creditor_id.id] = len(retenciones)
                        retenciones.append(ret)
                    # si ya se cargo una retencion para el acreedor actualizo los valores monto y base impuesto sumando los nuevos valores
                    else:
                        retenciones[ret_creditor_id[retencion.creditor_id.id]]['monto'] += ret['monto']
                        retenciones[ret_creditor_id[retencion.creditor_id.id]]['base_impuesto'] += ret['base_impuesto']

            llaves = []
            for llave_orig in nota_credito.factura_original.llpapg_ids:
                llave = {
                    'programa': llave_orig.programa,
                    'proyecto': llave_orig.proyecto,
                    'objeto_gasto': llave_orig.odg,
                    'auxiliar': llave_orig.auxiliar,
                    'financiamiento': llave_orig.fin,
                    'moneda': llave_orig.mon,
                    'tipo_credito': llave_orig.tc,
                    'importe': llave_orig.importe,
                }
                llaves.append(llave)

            for llave_nc in nota_credito.llpapg_ids:
                if nota_credito.tipo_nota_credito in ('R', 'D'):
                    monto_llave = -llave_nc.importe
                else:
                    monto_llave = llave_nc.importe
                llave = {
                    'programa': llave_nc.programa,
                    'proyecto': llave_nc.proyecto,
                    'objeto_gasto': llave_nc.odg,
                    'auxiliar': llave_nc.auxiliar,
                    'financiamiento': llave_nc.fin,
                    'moneda': llave_nc.mon,
                    'tipo_credito': llave_nc.tc,
                    'importe': monto_llave,
                }

                encontro = False
                for llave_fact in llaves:
                    if llave_fact['programa'] == llave['programa']  and llave_fact['proyecto'] == llave['proyecto'] and llave_fact['objeto_gasto'] == llave['objeto_gasto'] \
                            and llave_fact['auxiliar'] == llave['auxiliar'] and llave_fact['financiamiento'] == llave['financiamiento'] \
                            and llave_fact['moneda'] == llave['moneda'] and llave_fact['tipo_credito'] == llave['tipo_credito']:
                        encontro = True
                        llave_fact['importe'] = llave_fact['importe'] + llave['importe']
                if not encontro:
                    llaves.append(llave)



            xml_obligacion = generador_xml.gen_xml_obligacion_consolidado(cr, uid, nota_credito=nota_credito,
                                                                          llaves_presupuestales=llaves,
                                                                          nro_carga=nro_carga,
                                                                          tipo_doc_grp=tipo_doc_grp,
                                                                          nro_modif_grp=0,
                                                                          tipo_modificacion='A',
                                                                          retenciones=retenciones,
                                                                          enviar_datos_sice=enviar_datos_sice,
                                                                          nro_obl_sist_aux=nro_obl_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_obligacion)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_afectacion', None) is None and movimiento.find(
                        'nro_afectacion').text and movimiento.find('nro_afectacion').text.strip():
                    dicc_modif['nro_afectacion'] = movimiento.find('nro_afectacion').text
                if dicc_modif.get('nro_compromiso', None) is None and movimiento.find(
                        'nro_compromiso').text and movimiento.find('nro_compromiso').text.strip():
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('nro_obligacion', None) is None and movimiento.find(
                        'nro_obligacion').text and movimiento.find('nro_obligacion').text.strip():
                    dicc_modif['nro_obligacion'] = movimiento.find('nro_obligacion').text
                if dicc_modif.get('resultado', None) is None and movimiento.find(
                        'resultado').text and movimiento.find('resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_obligacion', None) is None and movimiento.find(
                        'sec_obligacion').text and movimiento.find('sec_obligacion').text.strip():
                    dicc_modif['siif_sec_obligacion'] = movimiento.find('sec_obligacion').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al obligar en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_obligacion', None) and dicc_modif.get('nro_compromiso', None) \
                        and dicc_modif.get('nro_afectacion', None) and dicc_modif.get('resultado', None):
                    break

            # error en devolucion de numero de obligacion
            if not dicc_modif.get('nro_obligacion', None):
                raise osv.except_osv(('Error al obligar en SIIF'),
                                     (descr_error or u'Error en devolución de número de obligación por el SIIF'))

            # Enviar factura como 3 en 1, actualizar Monto Autorizado y Comprometido, condicion de factura y etapa del gasto = 3en1
            if nota_credito.factura_original.doc_type == '3en1_invoice':
                total_nominal = nota_credito.factura_original.total_nominal
                if nota_credito.tipo_nota_credito in ('R', 'D'):
                    total_nominal -= nota_credito.total_nominal
                else:
                    total_nominal += nota_credito.total_nominal
                dicc_modif['monto_afectado'] = total_nominal
                dicc_modif['monto_comprometido'] = total_nominal


            dicc_modif['nro_obl_sist_aux'] = nro_obl_sist_aux

            #guardo la info d ela obligacion en la factura original
            self.write(cr, uid, [nota_credito.factura_original.id], dicc_modif, context=context)

            #guardo la info de secuencia el la nota de credito
            dicc_nc = {
                'siif_sec_obligacion': dicc_modif['siif_sec_obligacion'],
                'siif_ult_modif': dicc_modif['siif_ult_modif']
            }
            self.write(cr, uid, [nota_credito.id], dicc_nc, context=context)

            #Escribo en el log de la factura original, el consolidado de las llaves
            modif_obligacion_log_obj = self.pool.get('wiz.modif_obligacion_siif_log')
            for llave in llaves:
                if llave['importe']:
                    vals = {
                        'invoice_id': nota_credito.factura_original.id,
                        'tipo': 'A',
                        'fecha': fields.date.context_today(self, cr, uid, context=context),
                        'programa': llave['programa'],
                        'proyecto': llave['proyecto'],
                        'moneda': llave['moneda'],
                        'tipo_credito': llave['tipo_credito'],
                        'financiamiento': llave['financiamiento'],
                        'objeto_gasto': llave['objeto_gasto'],
                        'auxiliar': llave['auxiliar'],
                        'importe': llave['importe'],
                        'siif_sec_obligacion': dicc_modif.get('siif_sec_obligacion', False),
                        'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                    }
                    modif_obligacion_log_obj.create(cr, uid, vals, context=context)

            #escribo en el log de la nota de credito las llaves de la nota de credito
            for llave in nota_credito.llpapg_ids:
                # Nota de Credito
                vals = {
                    'invoice_id': nota_credito.id,
                    'tipo': nota_credito.tipo_nota_credito,
                    'fecha': fields.date.context_today(self, cr, uid, context=context),
                    'programa': llave.programa,
                    'proyecto': llave.proyecto,
                    'moneda': llave.mon,
                    'tipo_credito': llave.tc,
                    'financiamiento': llave.fin,
                    'objeto_gasto': llave.odg,
                    'auxiliar': llave.auxiliar,
                    'importe': llave.importe if nota_credito.tipo_nota_credito not in ('R', 'D') else -llave.importe,
                    'siif_sec_obligacion': dicc_modif.get('siif_sec_obligacion', False),
                    'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                }
                modif_obligacion_log_obj.create(cr, uid, vals, context=context)

                # Importe de llave presupuestal original, actualizo montos
                condicion = []
                condicion.append(('invoice_id', '=', nota_credito.factura_original.id))
                condicion.append(('odg', '=', llave.odg))
                condicion.append(('auxiliar', '=', llave.auxiliar))
                condicion.append(('fin', '=', llave.fin))
                condicion.append(('programa', '=', llave.programa))
                condicion.append(('proyecto', '=', llave.proyecto))
                condicion.append(('mon', '=', llave.mon))
                condicion.append(('tc', '=', llave.tc))

                lineas_llavep_obj = self.pool.get('grp.compras.lineas.llavep')
                llavep_id = lineas_llavep_obj.search(cr, uid, condicion, context=context)

                if len(llavep_id) < 1:
                    if nota_credito.tipo_nota_credito != 'A':
                        raise osv.except_osv(('Error'),
                                             (u'La llave presupuestal buscada no se encuentra en la factura.'))
                    else:
                        vals = {
                            'invoice_id': nota_credito.factura_original.id,
                            'fin_id': llave.fin_id.id,
                            'programa_id': llave.programa_id.id,
                            'proyecto_id': llave.proyecto_id.id,
                            'odg_id': llave.odg_id.id,
                            'auxiliar_id': llave.auxiliar_id.id,
                            'mon_id': llave.mon_id.id,
                            'tc_id': llave.tc_id.id,
                            'importe': 0,
                        }
                        llavep_id = lineas_llavep_obj.create(cr, uid, vals, context=context)
                        llavep_id = [llavep_id]

                llavep = lineas_llavep_obj.browse(cr, uid, llavep_id, context=context)
                llavep = llavep[0]

                dicc_modif = {}
                if nota_credito.tipo_nota_credito in ('R', 'D'):
                    dicc_modif['importe'] = llavep.importe - llave.importe
                else:
                    dicc_modif['importe'] = llavep.importe + llave.importe

                lineas_llavep_obj.write(cr, uid, [llavep.id], dicc_modif, context=context)

            return True



    def btn_enviar_modif_siif(self, cr, uid, ids, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')

        # impactar el presupuesto
        self.invoice_impactar_presupuesto(cr, uid, ids, context=context)

        #controles previos
        for nota_credito in self.browse(cr, uid, ids, context):

            # for linea in nota_credito.invoice_line:
            #     # Control: Monto de cada línea vs tipo de nota de crédito
            #     if nota_credito.tipo_nota_credito == 'R':
            #         if linea.price_subtotal < 0:
            #             raise ValidationError(_(u'Tipo de Nota de Crédito es Reducción pero existe una línea con monto de ajuste de aumento'))
            #     elif nota_credito.tipo_nota_credito == 'D':
            #         if linea.price_subtotal < 0:
            #             raise ValidationError(_(u'Tipo de Nota de Crédito es Devolución al crédito pero existe una línea con monto de ajuste de aumento'))
            #     elif nota_credito.tipo_nota_credito == 'A':
            #         if linea.price_subtotal > 0:
            #             raise ValidationError(_(
            #                     u'Tipo de Nota de Crédito es Aumento pero existe una línea con monto de ajuste de reducción'))

            #contabilizar la nota de credito
            if not nota_credito.move_id:
                wf_service = netsvc.LocalService('workflow')
                wf_service.trg_validate(uid, 'account.invoice', nota_credito.id, 'invoice_open', cr)

            # Para el caso de los ajustes de obligacion con monto cero, crear una aprobacion de pagos
            if nota_credito.doc_type in ['ajuste_invoice'] and nota_credito.amount_total == 0:
                self.pago_guardar(cr, uid, ids, nota_credito, u'Financiamiento de Créditos Presupuestales', context=context)


            # Control de no enviar llave presupuestal vacia
            if len(nota_credito.llpapg_ids) == 0:
                raise osv.except_osv(('Error'),
                                     (u'Debe cargar al menos una llave presupuestal.'))

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if nota_credito.factura_original.siif_financiamiento.exceptuado_sice or nota_credito.factura_original.siif_tipo_ejecucion.exceptuado_sice or nota_credito.factura_original.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in nota_credito.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name', '=', llave_pres.odg),
                                                                         ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise osv.except_osv(('Error'),
                                             (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                             llave_pres.odg, llave_pres.auxiliar))

            # Tipo de documento: Modificación de obligacion
            if nota_credito.factura_original.doc_type == '3en1_invoice':
                tipo_doc_grp = '14'
            else:
                tipo_doc_grp = '13'

            nro_modif_grp = nota_credito.factura_original.siif_ult_modif + 1

            # Envio a SIIF
            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': nota_credito.fiscalyear_siif_id and nota_credito.fiscalyear_siif_id.id or False})

            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]

            # retenciones: Lista de retenciones a enviar (cada elemento es un diciconario)
            # ret_creditor_id: diccionario que guarda en que posicion de la lista se encuetra la retencion para el acreedor (se agrupan por acreedor)
            retenciones = []
            ret_creditor_id = {}
            for retencion in nota_credito.ret_summary_group_line:
                if retencion.ret_amount_pesos_round != 0:
                    if retencion.tipo_retencion == 'siif':
                        if retencion.retention_id.base_compute == 'ret_tax':
                            base_imp = retencion.base_impuesto_pesos
                            base_imp_mon_ext = retencion.base_impuesto
                        else:
                            base_imp = retencion.base_linea_pesos
                            base_imp_mon_ext = retencion.base_linea
                        ret = {
                            'grupo': retencion.group_id.grupo,
                            'acreedor': retencion.creditor_id.acreedor,
                            'monto': retencion.ret_amount_pesos_round,
                            'base_impuesto': base_imp,
                            'es_manual': False,
                        }
                        if nota_credito.currency_id.name != 'UYU':
                            ret['base_impuesto_mont_ext'] = base_imp_mon_ext
                    else:
                        ret = {
                            'grupo': retencion.group_id.grupo,
                            'acreedor': retencion.creditor_id.acreedor,
                            'monto': retencion.ret_amount_pesos_round,
                            'base_impuesto': retencion.ret_amount_pesos_round,
                            'es_manual': True,
                        }
                    # si todavia no se cargo una retencion para el acreedor la inserto en la lista y actualizo el diccionario
                    if retencion.creditor_id.id not in ret_creditor_id:
                        ret_creditor_id[retencion.creditor_id.id] = len(retenciones)
                        retenciones.append(ret)
                    # si ya se cargo una retencion para el acreedor actualizo los valores monto y base impuesto sumando los nuevos valores
                    else:
                        retenciones[ret_creditor_id[retencion.creditor_id.id]]['monto'] += ret['monto']
                        retenciones[ret_creditor_id[retencion.creditor_id.id]]['base_impuesto'] += ret[
                            'base_impuesto']

            xml_obligacion = generador_xml.gen_xml_obligacion_modif(cr, uid, factura=nota_credito,
                                                                    llaves_presupuestales=nota_credito.llpapg_ids,
                                                                    importe=nota_credito.amount_ttal_liq_pesos,
                                                                    nro_carga=nro_carga, tipo_doc_grp=tipo_doc_grp,
                                                                    nro_modif_grp=nro_modif_grp,
                                                                    tipo_modificacion=nota_credito.tipo_nota_credito,
                                                                    retenciones=retenciones,
                                                                    enviar_datos_sice=enviar_datos_sice,
                                                                    nro_obl_sist_aux=nota_credito.factura_original.nro_obl_sist_aux)

            # _logger.info('xml_obligacion: %s', xml_obligacion)
            # return True

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_obligacion)

            # _logger.info('RESULTADO: %s', resultado_siif)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)


            # Actualizar datos en nc
            # ------------------------
            dicc_modif = {}
            descr_error = ''
            nro_obligacion_devuelto = False

            for movimiento in xml_root.findall('movimiento'):

                if movimiento.find('nro_obligacion').text and movimiento.find('nro_obligacion').text.strip():
                    nro_obligacion_devuelto = True

                if dicc_modif.get('resultado', None) is None and movimiento.find(
                        'resultado').text and movimiento.find('resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text

                if dicc_modif.get('siif_sec_obligacion', None) is None and movimiento.find(
                        'sec_obligacion').text and movimiento.find('sec_obligacion').text.strip():
                    dicc_modif['siif_sec_obligacion'] = movimiento.find('sec_obligacion').text

                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text

                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text

                # Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al obligar en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))


            # error en devolucion de numero de obligacion
            if not nro_obligacion_devuelto:
                raise osv.except_osv(('Error al obligar en SIIF'),
                                     (descr_error or u'Error en devolución de número de obligación por el SIIF'))

            res_write_nota_credito = self.write(cr, uid, [nota_credito.id], dicc_modif, context=context)

            # Agregar log en historico de llave presupuestal de nota de credito
            # -----------------------------------------------------------------
            if res_write_nota_credito:
                modif_obligacion_log_obj = self.pool.get('wiz.modif_obligacion_siif_log')
                for llave in nota_credito.llpapg_ids:

                    # Nota de Credito
                    vals = {
                        'invoice_id': nota_credito.id,
                        'tipo': nota_credito.tipo_nota_credito,
                        'fecha': fields.date.context_today(self, cr, uid, context=context),
                        'programa': llave.programa,
                        'proyecto': llave.proyecto,
                        'moneda': llave.mon,
                        'tipo_credito': llave.tc,
                        'financiamiento': llave.fin,
                        'objeto_gasto': llave.odg,
                        'auxiliar': llave.auxiliar,
                        'importe': llave.importe if nota_credito.tipo_nota_credito not in ('R','D') else -llave.importe,
                        'siif_sec_obligacion': dicc_modif.get('siif_sec_obligacion', False),
                        'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                    }
                    modif_obligacion_log_obj.create(cr, uid, vals, context=context)

                    # Factura original
                    vals = {
                        'invoice_id': nota_credito.factura_original.id,
                        'tipo': nota_credito.tipo_nota_credito,
                        'fecha': fields.date.context_today(self, cr, uid, context=context),
                        'programa': llave.programa,
                        'proyecto': llave.proyecto,
                        'moneda': llave.mon,
                        'tipo_credito': llave.tc,
                        'financiamiento': llave.fin,
                        'objeto_gasto': llave.odg,
                        'auxiliar': llave.auxiliar,
                        'importe': llave.importe if nota_credito.tipo_nota_credito not in ('R','D') else -llave.importe,
                        'siif_sec_obligacion': dicc_modif.get('siif_sec_obligacion', False),
                        'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                    }
                    modif_obligacion_log_obj.create(cr, uid, vals, context=context)


                    # Actualizar datos en factura original
                    # --------------------------------------
                    # Número de última modificación
                    invoice_obj = self.pool.get('account.invoice')
                    res_write_invoice = invoice_obj.write(cr, uid, [nota_credito.factura_original.id], dicc_modif, context=context)

                    # Importe de llave presupuestal
                    condicion = []
                    condicion.append(('invoice_id', '=', nota_credito.factura_original.id))
                    condicion.append(('odg', '=', llave.odg))
                    condicion.append(('auxiliar', '=', llave.auxiliar))
                    condicion.append(('fin', '=', llave.fin))
                    condicion.append(('programa', '=', llave.programa))
                    condicion.append(('proyecto', '=', llave.proyecto))
                    condicion.append(('mon', '=', llave.mon))
                    condicion.append(('tc', '=', llave.tc))

                    lineas_llavep_obj = self.pool.get('grp.compras.lineas.llavep')
                    llavep_id = lineas_llavep_obj.search(cr, uid, condicion, context=context)

                    if len(llavep_id) < 1:
                        if nota_credito.tipo_nota_credito != 'A':
                            raise osv.except_osv(('Error'),
                                                 (u'La llave presupuestal buscada no se encuentra en la factura.'))
                        else:
                            vals = {
                                'invoice_id': nota_credito.factura_original.id,
                                'fin_id': llave.fin_id.id,
                                'programa_id': llave.programa_id.id,
                                'proyecto_id': llave.proyecto_id.id,
                                'odg_id': llave.odg_id.id,
                                'auxiliar_id': llave.auxiliar_id.id,
                                'mon_id': llave.mon_id.id,
                                'tc_id': llave.tc_id.id,
                                'importe': 0,
                            }
                            llavep_id = lineas_llavep_obj.create(cr, uid, vals, context=context)
                            llavep_id = [llavep_id]

                    llavep = lineas_llavep_obj.browse(cr, uid, llavep_id, context=context)
                    llavep = llavep[0]

                    dicc_modif = {}
                    if nota_credito.tipo_nota_credito in ('R','D'):
                        dicc_modif['importe'] = llavep.importe - llave.importe
                    else:
                        dicc_modif['importe'] = llavep.importe + llave.importe

                    res_write_invoice = lineas_llavep_obj.write(cr, uid, [llavep.id], dicc_modif, context=context)

        return True

    def pago_guardar(self, cr, uid, ids, invoice, journal_name, context=None):
        invoice_obj = self.pool.get('account.invoice')
        journal_obj = self.pool.get('account.journal')
        if not invoice.pago_aprobado:
            journal_id = journal_obj.search(cr, uid, [('name', '=', journal_name)])
            if len(journal_id) > 0:
                journal_id = journal_id[0]
            fecha_aprobacion = datetime.now().strftime('%Y-%m-%d')
            invoice_obj.write(cr, uid, [invoice.id], {
                'pago_aprobado': True,
                'cuenta_bancaria_id': journal_id,
                'fecha_aprobacion': fecha_aprobacion
            })
        elif invoice.pago_aprobado:
            raise osv.except_osv((u'Error !!'),
                                 (u'El pago ya se encuentra aprobado.'))
        return True

    def btn_borrar_modif_obligacion(self, cr, uid, ids, context=None):
        for invoice in self.browse(cr, uid, ids, context=context):
            wf_service = netsvc.LocalService('workflow')
            wf_service.trg_validate(uid, 'account.invoice', invoice.id, 'invoice_cancel', cr)
            self.action_cancel_draft(cr, uid, [invoice.id])
            #Para poder borrar la factura en estado borrador
            self.write(cr, uid, [invoice.id], {'internal_number': False}, context=context)
            #Si es consolidada cancelo el presupuesto de la factura original (esta mantiene el neto)
            if invoice.obligacion_original_borrada and invoice.factura_original:
                #Cancelo presupuesto y contabilidad de factura original
                #Vuelvo a estado sice o draft dependiendo del tipo
                self.invoice_cancel_presupuesto(cr, uid, [invoice.factura_original.id], context=context)
                wf_service.trg_validate(uid, 'account.invoice', invoice.factura_original.id, 'invoice_cancel', cr)
                self.action_cancel_draft(cr, uid, [invoice.factura_original.id])
                state = 'draft'
                if invoice.factura_original.doc_type in ('obligacion_invoice', '3en1_invoice'):  # Obligacion y 3en1
                    state = 'draft'
                elif invoice.factura_original.doc_type == 'invoice':  # Factura de Proveedor
                    state = 'sice'
                self.write(cr, uid, [invoice.factura_original.id], {'state': state}, context=context)
            # Si no es consolidada cancelo el presupuesto del ajuste
            else:
                self.invoice_cancel_presupuesto(cr, uid, [invoice.id], context=context)
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        integracion_siif = company.integracion_siif or False
        if not integracion_siif:
            return True
        else:
            return self.invoice_borrar_modif_siif(cr, uid, ids, context=context)

    def invoice_borrar_modif_siif(self, cr, uid, ids, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for invoice in self.browse(cr, uid, ids, context):
            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': invoice.fiscalyear_siif_id and invoice.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            # SE OBLIGA CONTRA SIIF
            nro_modif_grp = invoice.siif_ult_modif
            # Tipo de documento: Modificación de obligacion
            if invoice.factura_original.doc_type == '3en1_invoice':
                tipo_doc_grp = '14'
            else:
                tipo_doc_grp = '13'

            xml_borrar_obligacion = generador_xml.gen_xml_borrado_modif_obligacion(cr, uid, factura=invoice,
                                                                             factura_original=invoice.factura_original,
                                                                             nro_carga=nro_carga,
                                                                             tipo_doc_grp=tipo_doc_grp,
                                                                             nro_modif_grp=nro_modif_grp,
                                                                             nro_obl_sist_aux=invoice.factura_original.nro_obl_sist_aux)
            resultado_siif = siif_proxy.put_solic(cr, uid, xml_borrar_obligacion)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            for movimiento in xml_root.findall('movimiento'):
                if movimiento.find('resultado').text == 'B':
                    dicc_modif['nro_obligacion'] = False
                    dicc_modif['siif_sec_obligacion'] = False
                    dicc_modif['siif_ult_modif'] = False
                    dicc_modif['nro_obl_sist_aux'] = False
                    # Historico
                    anulacion_inv_log_obj = self.pool.get('obligacion.anulacion.siif.log')
                    # anulacion_siif_log_ids
                    vals_history = {
                        'invoice_id': invoice.id,
                        'nro_afectacion_siif': invoice.nro_afectacion or 0,
                        'nro_compromiso': invoice.nro_compromiso or 0,
                        'nro_obligacion': invoice.nro_obligacion or 0,
                        'nro_obl_sist_aux': invoice.nro_obl_sist_aux or False,
                    }
                    id = anulacion_inv_log_obj.create(cr, uid, vals_history, context=context)
                    # Borrando valores
                    ids_delete = []
                    for idm in invoice.modif_obligacion_log_ids:
                        ids_delete.append(idm.id)
                    #borro logs de llave de factura original que se crearon a partir de esta modificacion
                    for log_orig in invoice.factura_original.modif_obligacion_log_ids:
                        if log_orig.siif_ult_modif and log_orig.siif_ult_modif == invoice.siif_ult_modif:
                            ids_delete.append(log_orig.id)
                    if ids_delete:
                        self.pool.get('wiz.modif_obligacion_siif_log').unlink(cr, uid, ids_delete)
                    # Si es fondo rotatorio se cambia el estado a 'paid'
                    if invoice.tipo_ejecucion_codigo_rel == 'P':
                        if invoice.doc_type != 'invoice':
                            dicc_modif['rendido_siif'] = False

                    #Si borre desde un consolidado, borro los valores de la factura original
                    #Y desmarco flag obligacion_original_borrada en el ajuste
                    if invoice.obligacion_original_borrada:
                        dicc_modif.update({'obligacion_original_borrada': False})
                        vals_original = {'nro_obligacion': False,
                                         'siif_sec_obligacion': False,
                                         'siif_ult_modif': False,
                                         'nro_obl_sist_aux': False,
                                         }
                        self.write(cr, uid, [invoice.factura_original.id], vals_original, context=context)

                    self.write(cr, uid, [invoice.id], dicc_modif, context=context)

                else:
                    descr_error = movimiento.find('comentario').text
                    raise osv.except_osv((u'Error al intentar borrar obligación en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))

            #INICIO - actualizo las llaves de la factura original
            for llave in invoice.llpapg_ids:
                condicion = []
                condicion.append(('invoice_id', '=', invoice.factura_original.id))
                condicion.append(('odg', '=', llave.odg))
                condicion.append(('auxiliar', '=', llave.auxiliar))
                condicion.append(('fin', '=', llave.fin))
                condicion.append(('programa', '=', llave.programa))
                condicion.append(('proyecto', '=', llave.proyecto))
                condicion.append(('mon', '=', llave.mon))
                condicion.append(('tc', '=', llave.tc))
                lineas_llavep_obj = self.pool.get('grp.compras.lineas.llavep')
                llavep_id = lineas_llavep_obj.search(cr, uid, condicion, limit=1, context=context)
                if llavep_id:
                    llavep = lineas_llavep_obj.browse(cr, uid, llavep_id[0], context=context)
                    if invoice.tipo_nota_credito in ('R', 'D'):
                        importe_llave = llavep.importe + llave.importe
                    else:
                        importe_llave = llavep.importe - llave.importe
                    lineas_llavep_obj.write(cr, uid, [llavep.id], {'importe':importe_llave}, context=context)
                else:
                    _logger.info(u"Borrando modif Obligación, no se encontró llave asociada a factura original")
            #FIN - actualizo las llaves de la factura original

            return True

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'nro_afectacion': False,
            'monto_afectado': False,
            'nro_obligacion': False,
            'nro_compromiso': False,
            'resultado': False,
            'comentario_siif': False,
            'monto_comprometido': False,
            'anulacion_siif_log_ids': False,
            'nro_obl_sist_aux': False,
            'siif_ult_modif': False,
            'siif_sec_obligacion': False,
            'monto_comprometido': 0,
            'cesion_embargo': False,
        })
        return super(account_invoice, self).copy(cr, uid, id, default, context=context)

account_invoice()
