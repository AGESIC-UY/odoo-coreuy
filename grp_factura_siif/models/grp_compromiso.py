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
from lxml import etree

import logging
_logger = logging.getLogger(__name__)

class modif_compromiso_compromiso_siif_log(osv.osv):

    _name = 'modif.compromiso.comp.siif.log'
    _description = "Log de modificaciones de compromiso 2 SIIF"

    _columns = {
        'compromiso_id': fields.many2one('grp.compromiso', 'Compromiso', required=True),
        'tipo': fields.selection(
            (('A', u'A - Aumento'),
             ('R', u'R - Reducción')),
             # ('C', u'C - Corrección'),
             # ('N', u'N - Anulación'),
             # ('D', u'D - Devolución')),
             'Tipo'),
        'fecha': fields.date('Fecha', required=True),
        'importe': fields.float('Importe', required=True),
        'programa': fields.char('Programa', size=3, required=True),
        'proyecto': fields.char('Proyecto', size=3, required=True),
        'moneda': fields.char('MON', size=2, required=True),
        'tipo_credito': fields.char('TC', size=1, required=True),
        'financiamiento': fields.char('FF', size=2, required=True),
        'objeto_gasto': fields.char('ODG', size=3, required=True),
        'auxiliar': fields.char('AUX', size=3, required=True),
        'siif_sec_compromiso': fields.char(u'Secuencial compromiso'),
        'siif_ult_modif': fields.integer(u'Última modificación'),
    }

modif_compromiso_compromiso_siif_log()

class compromiso_anulaciones_siif_log(osv.osv):

    _name = 'compromiso.anulacion.siif.log'
    _description = "Log compromiso anulaciones"

    _columns = {
        'compromiso_id': fields.many2one('grp.compromiso', 'Compromiso', required=True, ondelete='cascade'),
        'fecha': fields.date('Fecha', required=True),
        'nro_afectacion_siif': fields.integer(u'Nro Afectación SIIF'),
        'nro_compromiso': fields.char(u'Nro Compromiso', size=6),
        'nro_comp_sist_aux': fields.char(u'Nro Compromiso Sistema Aux', size=6),
    }

    _defaults = {
        'fecha': fields.date.context_today,
    }

compromiso_anulaciones_siif_log()

class grp_compromiso(osv.osv):

    _name = "grp.compromiso"
    _description = "GRP Compromiso Siif"
    _order = 'date desc, id desc'

    STATE_SELECTION = [
        ('draft','Borrador'),
        ('comprometido','Comprometido'),
        ('cancel','Anulado'),
        ('anulada_siif','Anulada en SIIF')
    ]

    def _get_importes_llavep( self, cr, uid, ids, fieldname, args, context = None ):
        res = { }
        for compromiso in self.browse ( cr, uid, ids, context = context ):
            total = 0
            for llavep in compromiso.llpapg_ids:
                total += llavep.importe
            res[compromiso.id] = total
        return res

    def _get_monto_afectado_apg( self, cr, uid, ids, fieldname, args, context = None ):
        res = { }
        for compromiso in self.browse ( cr, uid, ids, context = context ):
            total = 0
            if compromiso.tipo_afectacion == 'apg' and compromiso.apg_id.id:
                for llavep in compromiso.apg_id.llpapg_ids:
                    total += llavep.importe
            elif compromiso.tipo_afectacion == 'afectacion' and compromiso.afectacion_id.id:
                for llavep in compromiso.afectacion_id.llpapg_ids:
                    total += llavep.importe
            res[compromiso.id] = total
        return res

    def _get_datos_afectacion(self, cr, uid, ids, name, args, context=None):
        res = {}
        for compromiso in self.browse(cr, uid, ids, context=context):
            if compromiso.tipo_afectacion == 'apg' and compromiso.apg_id.id:
                res[compromiso.id] = {
                    'siif_tipo_ejecucion': compromiso.apg_id.siif_tipo_ejecucion.id,
                    'siif_concepto_gasto': compromiso.apg_id.siif_concepto_gasto.id,
                    'siif_codigo_sir': compromiso.apg_id.siif_codigo_sir.id,
                    'siif_financiamiento': compromiso.apg_id.siif_financiamiento.id,
                    'siif_nro_fondo_rot': compromiso.apg_id.siif_nro_fondo_rot.id,
                    'nro_afectacion_siif': compromiso.apg_id.nro_afectacion_siif,
                    'fiscalyear_siif_id': compromiso.apg_id.fiscalyear_siif_id.id,
                    'inciso_siif_id': compromiso.apg_id.inciso_siif_id.id,
                    'ue_siif_id': compromiso.apg_id.ue_siif_id.id,
                    'operating_unit_id': compromiso.apg_id.operating_unit_id.id,
                }
            elif compromiso.tipo_afectacion == 'afectacion' and compromiso.afectacion_id.id:
                res[compromiso.id] = {
                    'siif_tipo_ejecucion': compromiso.afectacion_id.siif_tipo_ejecucion.id,
                    'siif_concepto_gasto': compromiso.afectacion_id.siif_concepto_gasto.id,
                    'siif_codigo_sir': compromiso.afectacion_id.siif_codigo_sir.id,
                    'siif_financiamiento': compromiso.afectacion_id.siif_financiamiento.id,
                    'siif_nro_fondo_rot': compromiso.afectacion_id.siif_nro_fondo_rot.id,
                    'nro_afectacion_siif': compromiso.afectacion_id.nro_afectacion,
                    'fiscalyear_siif_id': compromiso.afectacion_id.fiscalyear_siif_id.id,
                    'inciso_siif_id': compromiso.afectacion_id.inciso_siif_id.id,
                    'ue_siif_id': compromiso.afectacion_id.ue_siif_id.id,
                    'operating_unit_id': compromiso.afectacion_id.operating_unit_id.id,
                }
            else:
                res[compromiso.id] = {
                    'siif_tipo_ejecucion': False,
                    'siif_concepto_gasto': False,
                    'siif_codigo_sir': False,
                    'siif_financiamiento': False,
                    'siif_nro_fondo_rot': False,
                    'nro_afectacion_siif': 0,
                    'fiscalyear_siif_id': False,
                    'inciso_siif_id': False,
                    'ue_siif_id': False,
                    'operating_unit_id': False,
                }
        return res

    def _get_es_inciso_default(self, cr, uid, ids, name, args, context=None):
        res = {}
        for compromiso in self.browse(cr, uid, ids, context=context):
            res[compromiso.id] = compromiso.partner_id and compromiso.partner_id.es_inciso_default or False
        return res

    _columns = {
        'name': fields.char('Nro. Compromiso', size=64, required=True, select=True, help=u"Número único, se calcula automáticamente cuando el compromiso es creado."),
        'partner_id':fields.many2one('res.partner', 'Beneficiario', required=True),
        'state': fields.selection(STATE_SELECTION, 'Estado', size=86, readonly=True),
        'descripcion':fields.char(u'Descripción',size=300),
        'date':fields.date('Fecha', required=True, select=True),
        'pedido_compra_id':fields.related('apg_id','pc_id',type="many2one",relation='grp.pedido.compra',string=u'Pedido de Compra'),
        'tipo_afectacion': fields.selection([('apg','APG'),('afectacion',u'Afectación')], u'Tipo afectación', required=True),
        'apg_id': fields.many2one('grp.compras.apg','Nro. de APG'),
        'afectacion_id': fields.many2one('grp.afectacion',u'Afectación'),
        'currency_oc':fields.many2one('res.currency','Moneda'),
        'fecha_tipo_cambio':fields.date('Fecha de tipo de cambio'),
        'company_id': fields.many2one('res.company',u'Compañía'),
        'monto_autorizado_apg': fields.integer('Monto a autorizar divisa'), # en moneda de la apg
        'monto_afectado': fields.function(_get_monto_afectado_apg, string='Monto afectado', type='integer'), # suma de los importes de la llave presupuestal de la APG asociada
        'monto_a_comprometer': fields.function(_get_importes_llavep, string='Monto a comprometer',type='integer'),# suma de los importes de la llave presupuestal del compromiso
        'nro_compromiso': fields.integer('Nro. Compromiso SIIF'),
        'siif_tipo_ejecucion': fields.function(_get_datos_afectacion, method=True, type='many2one', relation="tipo.ejecucion.siif", string=u'Tipo de ejecución', multi="datos_afectacion"),
        'siif_concepto_gasto': fields.function(_get_datos_afectacion, method=True, type='many2one', relation="presupuesto.concepto", string='Concepto del gasto', multi="datos_afectacion"),
        'siif_codigo_sir': fields.function(_get_datos_afectacion, method=True, type='many2one', relation="codigo.sir.siif", string=u'Código SIR', multi="datos_afectacion"),
        'siif_financiamiento': fields.function(_get_datos_afectacion, method=True, type='many2one', relation="financiamiento.siif", string='Fuente de financiamiento', multi="datos_afectacion"),
        'siif_tipo_documento': fields.many2one('tipo.documento.siif', u'Tipo de documento', domain=[('visible_documento_compromiso','=',True)]),
        'siif_nro_fondo_rot': fields.function(_get_datos_afectacion, method=True, type='many2one', relation="fondo.rotatorio.siif", string='Nro doc. fondo rotatorio', multi="datos_afectacion"),
        'siif_ult_modif': fields.integer(u'Última modificación'),
        'siif_sec_compromiso': fields.char(u'Secuencial compromiso'),
        'siif_descripcion': fields.text(u"Descripción SIIF", size=100),
        'tipo_ejecucion_codigo_rel': fields.related("siif_tipo_ejecucion", "codigo", type="char", string=u'Código tipo ejecución'),
        'nro_afectacion_siif': fields.function(_get_datos_afectacion, method=True, type='integer', string=u'Nro Afectación SIIF', multi="datos_afectacion"),
        'company_currency_id': fields.related('company_id','currency_id',  type='many2one', relation='res.currency', string='Moneda empresa',store=False, readonly=True),
        # Pestaña Llave Presupuestal
        'llpapg_ids' : fields.one2many ('grp.compras.lineas.llavep', 'compromiso_id', string = u'Líneas presupuesto' ), # , ondelete = 'cascade' ),
        'modif_compromiso_log_ids': fields.one2many(
            'modif.compromiso.comp.siif.log',
            'compromiso_id',
            'Log'),
        'anulacion_siif_log_ids': fields.one2many(
            'compromiso.anulacion.siif.log',
            'compromiso_id',
            'Log anulaciones'),
        'fiscalyear_siif_id': fields.function(_get_datos_afectacion, method=True, type='many2one', relation='account.fiscalyear', string=u'Año fiscal', multi="datos_afectacion"),
        'inciso_siif_id': fields.function(_get_datos_afectacion, method=True, type='many2one', relation='grp.estruc_pres.inciso', string=u'Inciso', multi="datos_afectacion"),
        'ue_siif_id': fields.function(_get_datos_afectacion, method=True, type='many2one', relation='grp.estruc_pres.ue', string=u'Unidad ejecutora', multi="datos_afectacion"),
        'nro_comp_sist_aux': fields.char(u'Nro Compromiso Sist. aux'),
        'operating_unit_id': fields.function(_get_datos_afectacion, method=True, type='many2one', relation='operating.unit', string=u'Unidad ejecutora responsable', multi="datos_afectacion"),
        'unidad_ejecutora_id': fields.many2one('unidad.ejecutora', string=u"Documento Beneficiario SIIF"),
        'benef_es_inciso_default': fields.function(_get_es_inciso_default, method=True, type='boolean', string='Es inciso por defecto', store=True),

    }

    _defaults = {
        'date': fields.date.context_today,
        'fecha_tipo_cambio': fields.date.context_today,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'grp.compromiso', context=c),
        'state': 'draft',
        'name': lambda obj, cr, uid, context: '/',
        'tipo_afectacion': 'afectacion',
    }

    _sql_constraints = [
        ('name_compromiso_uniq', 'unique(name, company_id)', u'Referencia de compromiso debe ser único por Compañía!'),
    ]

    def create(self, cr, uid, vals, context=None):
        #CAMBIOS SECUENCIAS 30/12
        if context is None:
            context = {}
        context=dict(context)
        tipo_afect = vals.get('tipo_afectacion',False)
        if tipo_afect == 'apg' and vals.get('apg_id',False):
            apg = self.pool.get('grp.compras.apg').browse(cr, uid, vals.get('apg_id',False))
            context.update({'fiscalyear_id':apg.fiscalyear_siif_id and apg.fiscalyear_siif_id.id or False})

        elif tipo_afect == 'afectacion' and vals.get('afectacion_id',False):
            afect = self.pool.get('grp.afectacion').browse(cr, uid, vals.get('afectacion_id',False))
            context.update({'fiscalyear_id':afect.fiscalyear_siif_id and afect.fiscalyear_siif_id.id or False})

        if vals.get('name','/')=='/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'grp.compromiso',context=context) or '/'
        order = super(grp_compromiso, self).create(cr, uid, vals, context=context)
        return order

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'nro_comp_sist_aux': False,
            'modif_compromiso_log_ids': False,
            'anulacion_siif_log_ids': False,
            'name': '/',
            'nro_compromiso': False,
            'siif_ult_modif': False,
            'siif_sec_compromiso': False,
        })
        return super(grp_compromiso, self).copy(cr, uid, id, default, context=context)

    def onchange_apg_id(self,cr,uid,ids,apg_id, tipo_afectacion, context=None):
        if ids:
            self.write(cr, uid, ids, {'llpapg_ids':[(5,)]}, context=context)
        result = {}
        result.setdefault('value', {})
        result['value'] = {'moneda': False, 'nro_afectacion_siif':False, 'monto_autorizado_apg':0, 'llpapg_ids':[]}

        if apg_id:
            apg = self.pool.get('grp.compras.apg').browse(cr, uid, apg_id, context=None)
            result['value'].update({'fiscalyear_siif_id': apg.fiscalyear_siif_id.id})
            result['value'].update({'inciso_siif_id': apg.inciso_siif_id.id})
            result['value'].update({'ue_siif_id': apg.ue_siif_id.id})

            result['value'].update({'siif_tipo_ejecucion': apg.siif_tipo_ejecucion.id})
            result['value'].update({'siif_concepto_gasto': apg.siif_concepto_gasto.id})
            result['value'].update({'siif_codigo_sir': apg.siif_codigo_sir.id})
            result['value'].update({'siif_financiamiento': apg.siif_financiamiento.id})
            result['value'].update({'siif_nro_fondo_rot': apg.siif_nro_fondo_rot.id})
            result['value'].update({'tipo_ejecucion_codigo_rel': apg.tipo_ejecucion_codigo_rel})
            result['value'].update({'operating_unit_id': apg.operating_unit_id.id})
            if apg.operating_unit_id and apg.operating_unit_id.unidad_ejecutora:
                unidad_ejecutora_ids = self.pool.get('unidad.ejecutora').search(cr, uid, [('codigo', '=', int(apg.operating_unit_id.unidad_ejecutora))], limit=1)
                if unidad_ejecutora_ids:
                    result['value'].update({'unidad_ejecutora_id': unidad_ejecutora_ids[0]})
            total= 0
            for llavep in apg.llpapg_ids:
                total += llavep.importe
            result['value'].update({'monto_afectado': total})

            llavep_ids = []
            if apg.llpapg_ids:
                for llave in apg.llpapg_ids:
                    llavep_ids.append((0,0,{
                        'programa' : llave.programa,
                        'odg' : llave.odg,
                        'auxiliar' : llave.auxiliar,
                        'disponible' :llave.disponible,
                        'proyecto' :llave.proyecto,
                        'fin' : llave.fin,
                        'mon' : llave.mon,
                        'tc' : llave.tc,
                        'importe' : llave.importe,
                        #MVARELA nuevos campos
                        'programa_id' : llave.programa_id.id,
                        'odg_id' : llave.odg_id.id,
                        'auxiliar_id' : llave.auxiliar_id.id,
                        'proyecto_id' :llave.proyecto_id.id,
                        'fin_id' : llave.fin_id.id,
                        'mon_id' : llave.mon_id.id,
                        'tc_id' : llave.tc_id.id,
                        }))
                    # cambios echaviano llave presupuestal
                    # llavep_ids.append(llave.id)
                result['value'].update({'llpapg_ids': llavep_ids})
            result['value'].update({'currency_oc': apg.moneda and apg.moneda.id or False,'nro_afectacion_siif': apg.nro_afectacion_siif or False,'monto_autorizado_apg': apg.monto_divisa or 0})
        else:
            result['value'].update({'fiscalyear_siif_id': False})
            result['value'].update({'inciso_siif_id': False})
            result['value'].update({'ue_siif_id': False})

            result['value'].update({'siif_tipo_ejecucion': False})
            result['value'].update({'siif_concepto_gasto': False})
            result['value'].update({'siif_codigo_sir': False})
            result['value'].update({'siif_financiamiento': False})
            result['value'].update({'siif_nro_fondo_rot': False})
            result['value'].update({'tipo_ejecucion_codigo_rel': False})
            result['value'].update({'monto_afectado': 0})
            result['value'].update({'operating_unit_id': False})
        return result

    def onchange_afectacion_id(self,cr,uid,ids,afectacion_id, tipo_afectacion, context=None):
        if ids:
            self.write(cr, uid, ids, {'llpapg_ids':[(5,)]}, context=context)
        result = {}
        result.setdefault('value', {})
        result['value'] = {'moneda': False, 'nro_afectacion_siif':False, 'monto_autorizado_apg':0, 'llpapg_ids':[]}

        if afectacion_id and tipo_afectacion == 'afectacion':
            afectacion = self.pool.get('grp.afectacion').browse(cr, uid, afectacion_id, context=None)
            result['value'].update({'fiscalyear_siif_id': afectacion.fiscalyear_siif_id.id})
            result['value'].update({'inciso_siif_id': afectacion.inciso_siif_id.id})
            result['value'].update({'ue_siif_id': afectacion.ue_siif_id.id})

            result['value'].update({'siif_tipo_ejecucion': afectacion.siif_tipo_ejecucion.id})
            result['value'].update({'siif_concepto_gasto': afectacion.siif_concepto_gasto.id})
            result['value'].update({'siif_codigo_sir': afectacion.siif_codigo_sir.id})
            result['value'].update({'siif_financiamiento': afectacion.siif_financiamiento.id})
            result['value'].update({'siif_nro_fondo_rot': afectacion.siif_nro_fondo_rot.id})
            result['value'].update({'tipo_ejecucion_codigo_rel': afectacion.tipo_ejecucion_codigo_rel})
            result['value'].update({'operating_unit_id': afectacion.operating_unit_id.id})
            if afectacion.operating_unit_id and afectacion.operating_unit_id.unidad_ejecutora:
                unidad_ejecutora_ids = self.pool.get('unidad.ejecutora').search(cr, uid, [('codigo', '=', int(afectacion.operating_unit_id.unidad_ejecutora))], limit=1)
                if unidad_ejecutora_ids:
                    result['value'].update({'unidad_ejecutora_id': unidad_ejecutora_ids[0]})
            total= 0
            for llavep in afectacion.llpapg_ids:
                total += llavep.importe
            result['value'].update({'monto_afectado': total})

            llavep_ids = []
            if afectacion.llpapg_ids:
                for llave in afectacion.llpapg_ids:
                    llavep_ids.append((0,0,{
                        'programa' : llave.programa,
                        'odg' : llave.odg,
                        'auxiliar' : llave.auxiliar,
                        'disponible' :llave.disponible,
                        'proyecto' :llave.proyecto,
                        'fin' : llave.fin,
                        'mon' : llave.mon,
                        'tc' : llave.tc,
                        'importe' : llave.importe,
                        #MVARELA nuevos campos
                        'programa_id' : llave.programa_id.id,
                        'odg_id' : llave.odg_id.id,
                        'auxiliar_id' : llave.auxiliar_id.id,
                        'proyecto_id' :llave.proyecto_id.id,
                        'fin_id' : llave.fin_id.id,
                        'mon_id' : llave.mon_id.id,
                        'tc_id' : llave.tc_id.id,
                        }))
                    # cambios echaviano llave presupuestal
                    # llavep_ids.append(llave.id)
                result['value'].update({'llpapg_ids': llavep_ids})
            result['value'].update({'currency_oc': afectacion.currency_oc and afectacion.currency_oc.id or False,'nro_afectacion_siif': afectacion.nro_afectacion or False,'monto_autorizado_apg': afectacion.monto_divisa or 0})
        else:
            result['value'].update({'fiscalyear_siif_id': False})
            result['value'].update({'inciso_siif_id': False})
            result['value'].update({'ue_siif_id': False})

            result['value'].update({'siif_tipo_ejecucion': False})
            result['value'].update({'siif_concepto_gasto': False})
            result['value'].update({'siif_codigo_sir': False})
            result['value'].update({'siif_financiamiento': False})
            result['value'].update({'siif_nro_fondo_rot': False})
            result['value'].update({'tipo_ejecucion_codigo_rel': False})
            result['value'].update({'monto_afectado': 0})
            result['value'].update({'operating_unit_id': False})
        return result

    # def onchange_tipo_afectacion(self,cr,uid,ids,tipo_afectacion,context=None):
    #     if tipo_afectacion == 'apg':
    #         return {'value': {'afectacion_id':False}}
    #     elif tipo_afectacion == 'afectacion':
    #         return {'value': {'apg_id':False}}
    #     else:
    #         return {'value': {'afectacion_id':False, 'apg_id':False}}

    def onchange_partner_id(self,cr,uid,ids,partner_id,context=None):
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            return {'value': {'benef_es_inciso_default':partner.es_inciso_default}}

    def button_comprometer( self, cr, uid, ids, context = None ):
        estructura_obj = self.pool.get('presupuesto.estructura')
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for compromiso in self.browse(cr, uid, ids):
            if compromiso.nro_compromiso:
                raise osv.except_osv("Error", "Este documento ya ha sido enviado a SIIF. Por favor, actualice el navegador.")
            sum_llaves = 0
            validacion_ok = False
            for llave in compromiso.llpapg_ids:
                # Para control 3
                sum_llaves += llave.importe

                estructura = estructura_obj.obtener_estructura(cr, uid, compromiso.fiscalyear_siif_id.id, compromiso.inciso_siif_id.inciso,
                                                           compromiso.ue_siif_id.ue,
                                                           llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                           llave.fin, llave.odg, llave.auxiliar)

                # Control 1: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (compromiso.fiscalyear_siif_id.code, compromiso.inciso_siif_id.inciso, compromiso.ue_siif_id.ue,
                                  llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                    raise osv.except_osv(('Error'), (
                    u'No se encontró estructura con la llave presupuestal asociada al Compromiso: ' + desc_error))
                    # Mostrar error y salir del for

                # Control 2: que no alcance el disponible para el monto de la llave presupuestal
                #if estructura.disponible < llave.importe:
                #    raise osv.except_osv(('Error'), (
                #        'El disponible de la estructura no es suficiente para cubrir el importe de la llave presupuestal.'))
                #    # Mostrar error y salir del for

            # Control 3: que la sumatoria de llave no sea la misma que la OC
            #if sum_llaves != oc.amount_total_base:
            #    # Mostrar error y salir
            #    raise osv.except_osv(('Error'), (
            #        'La sumatoria de importes de llaves presupuestales no es igual al monto total de la Orden de Compra.'))

            res = False

            for llave in compromiso.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(cr, uid, compromiso.fiscalyear_siif_id.id, compromiso.inciso_siif_id.inciso,
                                               compromiso.ue_siif_id.ue,
                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                               llave.fin, llave.odg, llave.auxiliar)
                res = estructura_obj.comprometer(cr, uid, compromiso.id, 3, llave.importe,
                                                     estructura)  # 6 - TIPO_DOCUMENTO COMPROMISO
            if not res:
                return False

            if compromiso.partner_id.tipo_doc_rupe == '':
                raise osv.except_osv((''), (u'El proveedor debe tener configurado tipo y número de documento de RUPE.'))
            if compromiso.partner_id.nro_doc_rupe == '':
                raise osv.except_osv((''), (u'El proveedor debe tener configurado tipo y número de documento de RUPE.'))

            # se compromete contra el SIIF
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            integracion_siif = company.integracion_siif or False
            if not integracion_siif:
                self.write(cr, uid, [compromiso.id], {'state': 'comprometido'})
                return True

            #MVARELA se pasa el año fiscal para traer la secuencia de ese año
            if context is None:
                context = {}
            context=dict(context)
            context.update({'fiscalyear_id': compromiso.fiscalyear_siif_id.id})
            nro_comp_sist_aux = self.pool.get('ir.sequence').get(cr, uid, 'sec.siif.compromiso',context=context)
            nro_comp_sist_aux = nro_comp_sist_aux[4:]
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if compromiso.siif_financiamiento.exceptuado_sice or compromiso.siif_tipo_ejecucion.exceptuado_sice or compromiso.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in compromiso.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name','=',llave_pres.odg),('auxiliar','=',llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise osv.except_osv(('Error'),
                                             (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.')%(llave_pres.odg, llave_pres.auxiliar))

            xml_compromiso = generador_xml.gen_xml_compromiso(cr, uid, compromiso=compromiso,
                                                                    llaves_presupuestales=compromiso.llpapg_ids,
                                                                    importe=compromiso.monto_a_comprometer,
                                                                    nro_carga=nro_carga,
                                                                    tipo_doc_grp='02', nro_modif_grp=0,
                                                                    tipo_modificacion='A',
                                                                    nro_comp_sist_aux=nro_comp_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_compromiso)

            #conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_compromiso', None) is None:
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('resultado', None) is None:
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_compromiso', None) is None:
                    dicc_modif['siif_sec_compromiso'] = movimiento.find('sec_compromiso').text
                if dicc_modif.get('siif_ult_modif', None) is None:
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                #MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al comprometer en SIIF'),
                                     (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_compromiso', False) and dicc_modif.get('nro_compromiso', False).strip() and dicc_modif.get('resultado', False):
                    break

            # error en devolucion de numero de compromiso
            if not dicc_modif.get('nro_compromiso', None):
                raise osv.except_osv(('Error al comprometer en SIIF'),
                                     (descr_error or u'Error en devolución de número de compromiso por el SIIF'))

            dicc_modif['nro_comp_sist_aux'] = nro_comp_sist_aux
            res_write = self.write(cr, uid, compromiso.id, dicc_modif, context=context)

            if res_write:
                modif_compromiso_log_obj = self.pool.get('modif.compromiso.comp.siif.log')
                for llave in compromiso.llpapg_ids:
                    vals={
                        'compromiso_id': compromiso.id,
                        'tipo': 'A',
                        'fecha': fields.date.context_today(self,cr,uid,context=context),
                        'programa': llave.programa,
                        'proyecto': llave.proyecto,
                        'moneda': llave.mon,
                        'tipo_credito': llave.tc,
                        'financiamiento': llave.fin,
                        'objeto_gasto': llave.odg,
                        'auxiliar': llave.auxiliar,
                        'importe': llave.importe,
                        'siif_sec_compromiso': dicc_modif['siif_sec_compromiso'] if 'siif_sec_compromiso' in dicc_modif else False,
                        'siif_ult_modif': dicc_modif['siif_ult_modif'] if 'siif_ult_modif' in dicc_modif else False,
                    }
                    modif_compromiso_log_obj.create(cr, uid, vals, context=context)
                # Integracion SIIF Compromiso
        self.write(cr, uid, ids, {'state': 'comprometido'})
        return True


    def button_anular( self, cr, uid, ids, context = None ):
        # Integracion SIIF Compromiso
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True

    # Anular compromiso en SIIF
    def button_anular_compromiso( self, cr, uid, ids, context = None ):
        estructura_obj = self.pool.get('presupuesto.estructura')
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')

        # comprobar primero el presupuesto
        sum_llaves = 0
        validacion_ok = False
        id = ids[0]
        oc = self.browse(cr, uid, id, context)
        for llave in oc.llpapg_ids:
            # Para control 3
            sum_llaves += llave.importe

            estructura = estructura_obj.obtener_estructura(cr, uid, oc.fiscalyear_siif_id.id, oc.inciso_siif_id.inciso,
                                                           oc.ue_siif_id.ue,
                                                           llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                           llave.fin, llave.odg, llave.auxiliar)

            # Control 1: que no exista una estructura
            if estructura is None:
                desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                             (oc.fiscalyear_siif_id.code, oc.inciso_siif_id.inciso, oc.ue_siif_id.ue,
                              llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                raise osv.except_osv(('Error'), (
                    u'No se encontró estructura con la llave presupuestal asociada al Compromiso: ' + desc_error))
                # Mostrar error y salir del for

            # Control 2: que no alcance el disponible para el monto de la llave presupuestal
            #if estructura.disponible < llave.importe:
            #    raise osv.except_osv(('Error'), (
            #        'El disponible de la estructura no es suficiente para cubrir el importe de la llave presupuestal.'))
            #    # Mostrar error y salir del for

        # Control 3: que la sumatoria de llave no sea la misma que la OC
        #if sum_llaves != oc.amount_total_base:
        #    # Mostrar error y salir
        #    raise osv.except_osv(('Error'), (
        #        'La sumatoria de importes de llaves presupuestales no es igual al monto total de la Orden de Compra.'))

        res = False

        for llave in oc.llpapg_ids:
            estructura = estructura_obj.obtener_estructura(cr, uid, oc.fiscalyear_siif_id.id, oc.inciso_siif_id.inciso,
                                           oc.ue_siif_id.ue,
                                           llave.programa, llave.proyecto, llave.mon, llave.tc,
                                           llave.fin, llave.odg, llave.auxiliar)
            res = estructura_obj.comprometer(cr, uid, oc.id, 3, -1 * llave.importe,
                                                 estructura)  # 6 - TIPO_DOCUMENTO COMPROMISO
        if not res:
            return False

        for comp in self.browse(cr, uid, ids, context):
            if comp.siif_tipo_ejecucion and comp.siif_tipo_ejecucion.codigo == 'P' and not comp.siif_nro_fondo_rot:
                raise osv.except_osv(('Error'),
                                     (u'Si el tipo de ejecución es Fondo Rotatorio, se debe cargar Nro. de Fondo Rotatorio.'))

            #MVARELA 15-09: Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
            for llave_pres in comp.llpapg_ids:
                objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name','=',llave_pres.odg),('auxiliar','=',llave_pres.auxiliar)])
                if len(objeto_gasto_ids) > 0:
                    ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                    if not ogasto.exceptuado_sice:
                        enviar_datos_sice = True
                else:
                    raise osv.except_osv(('Error'),
                                         (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.')%(llave_pres.odg, llave_pres.auxiliar))

            nro_modif = comp.siif_ult_modif+1
            # se compromete contra el SIIF
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            integracion_siif = company.integracion_siif or False
            if not integracion_siif:
                self.write(cr, uid, [comp.id], {'state': 'anulada_siif'})
                return True

            if context is None:
                context = {}
            context=dict(context)
            context.update({'fiscalyear_id': comp.fiscalyear_siif_id.id})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif',context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            monto_desafectar = 0
            for llave in comp.llpapg_ids:
                monto_desafectar += llave.importe
            monto_desafectar *= -1

            # COMPROMETER ------------------
            xml_anulacion_compromiso = generador_xml.gen_xml_compromiso(cr, uid, compromiso=comp,
                                                              llaves_presupuestales=comp.llpapg_ids,
                                                              importe=monto_desafectar,
                                                              nro_carga=nro_carga,
                                                              tipo_doc_grp='02', nro_modif_grp=nro_modif,
                                                              tipo_modificacion='N', es_modif=True, motivo='Anulacion compromiso',
                                                              nro_comp_sist_aux=comp.nro_comp_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_anulacion_compromiso)

            #conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_compromiso', None) is None:
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('resultado', None) is None:
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_compromiso', None) is None:
                    dicc_modif['siif_sec_compromiso'] = movimiento.find('sec_compromiso').text
                if dicc_modif.get('siif_ult_modif', None) is None:
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                #MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al comprometer en SIIF'),
                                     (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_compromiso', False) and dicc_modif.get('nro_compromiso', False).strip() and dicc_modif.get('resultado', False):
                    break

            anulacion_comprom_log_obj = self.pool.get('compromiso.anulacion.siif.log')
            # anulacion_siif_log_ids
            vals_history={
                'compromiso_id': comp.id,
                'nro_afectacion_siif': comp.nro_afectacion_siif or 0,
                'nro_compromiso': comp.nro_compromiso or 0,
                'nro_comp_sist_aux': comp.nro_comp_sist_aux or False,
            }
            anulacion_comprom_log_obj.create(cr, uid, vals_history, context=context)
            # Borrando valores
            ids_log_delete = []
            for idm in comp.modif_compromiso_log_ids:
                ids_log_delete.append(idm.id)
            if ids_log_delete:
                self.pool.get('modif.compromiso.comp.siif.log').unlink(cr, uid, ids_log_delete)

            dicc_modif.update({'nro_comp_sist_aux':False, 'nro_compromiso': False, 'state':'anulada_siif'})
            res_write = self.write(cr, uid, comp.id, dicc_modif, context=context)
        return True

    def abrir_wizard_modif_compromiso_siif(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif', 'view_wizard_modif_compromiso_siif')
        res_id = res and res[1] or False
        ue_id = self.browse(cr, uid, ids[0]).ue_siif_id.id or False

        ctx = dict(context)
        ctx.update({
            'default_compromiso_id': ids[0],
            'default_ue_id': ue_id
        })
        return {
            'name': "Modificaciones",  # Name You want to display on wizard
            'view_mode': 'form',
            'view_id': res_id,
            'view_type': 'form',
            'res_model': 'wiz.modif.compromiso.compromiso.siif',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    def enviar_modificacion_siif(self, cr, uid, id, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        programa = context['programa']
        proyecto = context['proyecto']
        moneda = context['moneda']
        tipo_credito =  context['tipo_credito']
        tipo_modificacion = context['tipo_modificacion']
        financiamiento = context['financiamiento']
        objeto_gasto = context['objeto_gasto']
        auxiliar = context['auxiliar']
        importe = context['importe']
        fecha = context['fecha']
        motivo = context['motivo']
        auxiliar_id = context['auxiliar_id']
        fin_id = context['fin_id']
        mon_id = context['mon_id']
        odg_id = context['odg_id']
        programa_id = context['programa_id']
        proyecto_id = context['proyecto_id']
        tc_id = context['tc_id']

        compromiso = self.browse(cr, uid, id)
        #MVARELA 15-09: Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
        enviar_datos_sice = False
        if compromiso.siif_financiamiento.exceptuado_sice or compromiso.siif_tipo_ejecucion.exceptuado_sice or compromiso.siif_concepto_gasto.exceptuado_sice:
            enviar_datos_sice = False
        else:
            objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
            objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name','=',objeto_gasto),('auxiliar','=',auxiliar)])
            if len(objeto_gasto_ids) > 0:
                ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                if not ogasto.exceptuado_sice:
                    enviar_datos_sice = True
            else:
                raise osv.except_osv(('Error'),
                                     (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.')%(objeto_gasto, auxiliar))

        lineas_llavep_obj = self.pool.get('grp.compras.lineas.llavep')
        condicion=[]
        condicion.append(('compromiso_id','=',id))
        condicion.append(('programa','=',programa))
        condicion.append(('proyecto','=',proyecto))
        condicion.append(('odg','=',objeto_gasto))
        condicion.append(('auxiliar','=',auxiliar))
        condicion.append(('fin','=',financiamiento))
        condicion.append(('mon','=',moneda))
        condicion.append(('tc','=',tipo_credito))
        llavep_id = lineas_llavep_obj.search(cr, uid, condicion, context=context)
        if len(llavep_id) < 1:
            if tipo_modificacion != 'A':
                raise osv.except_osv(('Error'), (u'La llave presupuestal ingresada no se encuentra en el compromiso.'))
            else:
                vals = {
                    'compromiso_id': id,
                    'fin_id': fin_id,
                    'programa_id': programa_id,
                    'proyecto_id': proyecto_id,
                    'odg_id': odg_id,
                    'auxiliar_id': auxiliar_id,
                    'mon_id': mon_id,
                    'tc_id': tc_id,
                    'importe': 0,
                }
                llavep_id = lineas_llavep_obj.create(cr, uid, vals, context=context)
                llavep_id = [llavep_id]

        llavep = lineas_llavep_obj.browse(cr, uid, llavep_id, context=context)
        llavep = llavep[0]

        # SE AFECTA CONTRA LA ESTRUCTURA LOCAL
        estructura_obj = self.pool.get('presupuesto.estructura')
        estructura = estructura_obj.obtener_estructura(cr, uid, compromiso.fiscalyear_siif_id.id, compromiso.inciso_siif_id.inciso,
                                                           compromiso.ue_siif_id.ue,
                                                           programa, proyecto, moneda, tipo_credito,
                                                           financiamiento, objeto_gasto, auxiliar)
        if estructura is None:
            desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                         (compromiso.fiscalyear_siif_id.code, compromiso.inciso_siif_id.inciso, compromiso.ue_siif_id.ue,
                          objeto_gasto, auxiliar, financiamiento, programa, proyecto, moneda, tipo_credito)
            raise osv.except_osv(('Error'), (
                u'No se encontró estructura con la llave presupuestal asociada al Compromiso: ' + desc_error))

        #** Falta agregar controles **
        # res = estructura_obj.afectar(cr, uid, apg.id, TIPO_DOCUMENTO.APG, importe, estructura)
        res = estructura_obj.comprometer(cr, uid, compromiso.id, 3, importe, estructura)
        _logger.info("res modificacion compromiso: %s", res)

        if res['codigo']==1:
            # SE COMPROMETE CONTRA SIIF
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            integracion_siif = company.integracion_siif or False
            if not integracion_siif:
                return True

            if context is None:
                context = {}
            context=dict(context)
            context.update({'fiscalyear_id': compromiso.fiscalyear_siif_id.id})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif',context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_modif = compromiso.siif_ult_modif+1

            xml_modif_compromiso = generador_xml.gen_xml_compromiso(cr, uid, compromiso=compromiso,
                                                                        llaves_presupuestales=[llavep],
                                                                        importe=importe,
                                                                        nro_carga=nro_carga,
                                                                        tipo_doc_grp='02', nro_modif_grp=nro_modif,
                                                                        tipo_modificacion=tipo_modificacion, es_modif=True,
                                                                        motivo=motivo,
                                                                        nro_comp_sist_aux=compromiso.nro_comp_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_modif_compromiso)

            #conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):  # Es una lista si se afecta el mismo numero de carga una y otra vez
                if dicc_modif.get('nro_compromiso', None) is None:
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('resultado', None) is None:
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_compromiso', None) is None:
                    dicc_modif['siif_sec_compromiso'] = movimiento.find('sec_compromiso').text
                if dicc_modif.get('siif_ult_modif', None) is None:
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                #MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al comprometer en SIIF'),
                                     (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_compromiso', False) and dicc_modif.get('nro_compromiso', False).strip() and dicc_modif.get('resultado', False):
                    break
            # if dicc_modif.get('resultado', None) == 'E':
            #     raise osv.except_osv(('Error al comprometer en SIIF'),
            #                          (descr_error or u'Error no especificado por el SIIF'))

            res_write = self.write(cr, uid, compromiso.id, dicc_modif, context=context)

            if res_write:
                #Actualizar importe
                val_modif = {
                    'importe': importe+llavep.importe,
                }
                res_write = lineas_llavep_obj.write(cr, uid, llavep.id, val_modif, context=context)

                if res_write:
                    modif_log_obj = self.pool.get('modif.compromiso.comp.siif.log')
                    vals={
                        'compromiso_id': compromiso.id,
                        'tipo': tipo_modificacion,
                        'fecha': fecha,
                        'programa': programa,
                        'proyecto': proyecto,
                        'moneda': moneda,
                        'tipo_credito': tipo_credito,
                        'financiamiento': financiamiento,
                        'objeto_gasto': objeto_gasto,
                        'auxiliar': auxiliar,
                        'importe': importe,
                        'siif_sec_compromiso': dicc_modif['siif_sec_compromiso'] if 'siif_sec_compromiso' in dicc_modif else False,
                        'siif_ult_modif': dicc_modif['siif_ult_modif'] if 'siif_ult_modif' in dicc_modif else False,
                    }
                    modif_log_obj.create(cr, uid, vals, context=context)
        return True

grp_compromiso()


# Wizard para modificacion
class wiz_modificacion_compromiso_compromiso_siif(osv.osv_memory):
    _name = 'wiz.modif.compromiso.compromiso.siif'
    _description = "Wizard modificacion de compromiso SIIF"
    _columns = {
        'compromiso_id': fields.many2one('grp.compromiso','Compromiso'),
        'tipo': fields.selection(
            (('A', u'A - Aumento'),
             ('R', u'R - Reducción')),
             # ('C', u'C - Corrección'),
             # ('N', u'N - Anulación'),
             # ('D', u'D - Devolución')),
            'Tipo', required=True),
        'fecha': fields.date('Fecha', required=True),
        'importe': fields.integer('Importe', required=True),
        'motivo': fields.char('Motivo', required=True),

        'financiamiento': fields.related('fin_id', 'ff', type='char', string='Fin related', store=True, readonly=True),
        'programa': fields.related('programa_id', 'programa', type='char', string='Programa related', store=True, readonly=True),
        'proyecto': fields.related('proyecto_id', 'proyecto', type='char', string='Proyecto related', store=True, readonly=True),
        'objeto_gasto': fields.related('odg_id', 'odg', type='char', string='ODG related', store=True, readonly=True),
        'auxiliar' : fields.related('auxiliar_id', 'aux', type='char', string='Auxiliar related', store=True, readonly=True),
        'moneda' : fields.related('mon_id', 'moneda', type='char', string='Mon related', store=True, readonly=True),
        'tipo_credito' : fields.related('tc_id', 'tc', type='char', string='TC related', store=True, readonly=True),

        'ue_id': fields.many2one('grp.estruc_pres.ue', 'Unidad ejecutora'),
        'fin_id' : fields.many2one ('grp.estruc_pres.ff', 'Fin', required=True),
        'programa_id' : fields.many2one ('grp.estruc_pres.programa', 'Programa', required=True),
        'proyecto_id' : fields.many2one ('grp.estruc_pres.proyecto', 'Proyecto', required=True),
        'odg_id' : fields.many2one ('grp.estruc_pres.odg', 'ODG', required=True),
        'auxiliar_id' : fields.many2one ('grp.estruc_pres.aux', 'Auxiliar', required=True),
        'mon_id' : fields.many2one ('grp.estruc_pres.moneda', 'Mon', required=True),
        'tc_id' : fields.many2one ('grp.estruc_pres.tc', 'TC', required=True),
    }

    _defaults = {
        'fecha': fields.date.context_today,
    }

    #Consumir SIIF aca
    def send_modif(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        compromiso_obj = self.pool.get("grp.compromiso")

        ctx = dict(context)
        ctx.update({
            'es_modif': True,
            'compromiso_id': data['compromiso_id'],
            'tipo_modificacion': data['tipo'],
            'fecha': data['fecha'],
            'programa': data['programa'],
            'proyecto': data['proyecto'],
            'moneda': data['moneda'],
            'tipo_credito': data['tipo_credito'],
            'financiamiento': data['financiamiento'],
            'objeto_gasto': data['objeto_gasto'],
            'auxiliar': data['auxiliar'],
            'importe': data['importe'] if data['tipo']=='A' else data['importe']*-1,
            'motivo': data['motivo'],
            'auxiliar_id': data['auxiliar_id'][0],
            'fin_id': data['fin_id'][0],
            'mon_id': data['mon_id'][0],
            'odg_id': data['odg_id'][0],
            'programa_id': data['programa_id'][0],
            'proyecto_id': data['proyecto_id'][0],
            'tc_id': data['tc_id'][0],
        })
        return compromiso_obj.enviar_modificacion_siif(cr, uid, id=data['compromiso_id'][0], context=ctx)

wiz_modificacion_compromiso_compromiso_siif()

class grp_invoice_compromiso(osv.osv):

    _inherit = "account.invoice"

    _columns = {
        'compromiso_id': fields.many2one('grp.compromiso', 'Nro Compromiso'),
        'afectacion_id': fields.related('compromiso_id', 'afectacion_id', type="many2one", relation="grp.afectacion", readonly="1", string=u'Nro Afectación SIIF'),
    }

    def onchange_compromiso_id(self,cr,uid,ids,compromiso_id,context=None):
        result = {}
        result.setdefault('value', {})
        #105 - Incidencia
        if context.get('doc_type',False) == '3en1_invoice':
            return result
        #result['value'] = {'currency_id': False, 'nro_afectacion':False, 'monto_autorizado':0, 'monto_comprometido':0}
        # desvincular existentes
        if ids:
            self.write(cr, uid, ids, {'llpapg_ids':[(5,)]}, context=context)
        if compromiso_id:
            compromiso = self.pool.get('grp.compromiso').browse(cr, uid, compromiso_id, context=None)
            result['value'].update({'fiscalyear_siif_id': compromiso.fiscalyear_siif_id.id})
            result['value'].update({'inciso_siif_id': compromiso.inciso_siif_id.id})
            result['value'].update({'ue_siif_id': compromiso.ue_siif_id.id})
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
                                    'operating_unit_id':compromiso.operating_unit_id.id
                                    })
            llavep_ids = []
            #llavep_ids.append(5)
            if compromiso.llpapg_ids:
                for llave in compromiso.llpapg_ids:
                    llavep_ids.append((0,0,{
                        'disponible' :llave.disponible,
                        'importe' : llave.importe,
                        #MVARELA nuevos campos
                        'programa_id' : llave.programa_id.id,
                        'odg_id' : llave.odg_id.id,
                        'auxiliar_id' : llave.auxiliar_id.id,
                        'proyecto_id' :llave.proyecto_id.id,
                        'fin_id' : llave.fin_id.id,
                        'mon_id' : llave.mon_id.id,
                        'tc_id' : llave.tc_id.id,
                        }))
                result['value'].update({'llpapg_ids': llavep_ids})
            #result['value'].update({'currency_id': compromiso.moneda and compromiso.moneda.id or False,'nro_afectacion': compromiso.nro_afectacion_siif or False,'monto_autorizado': compromiso.monto_divisa or 0})
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
                        })
        return result

    def on_change_apg(self,cr,uid,ids,apg_id,context=None):
        if ids:
            self.write(cr, uid, ids, {'llpapg_ids':[(5,)],'invoice_line':[(5,)]}, context=context)
        result = {}
        result.setdefault('value', {})
        result['value'] = {'origin': False, 'nro_afectacion':False, 'monto_afectado':0.0, 'invoice_line':[], 'llpapg_ids':[]}
        if apg_id:
            apg = self.pool.get('grp.compras.apg').browse(cr, uid, apg_id, context=None)
            llavep_ids = []
            if apg.llpapg_ids:
                for llave in apg.llpapg_ids:
                    llavep_ids.append(({
                        'disponible' :llave.disponible,
                        'importe' : llave.importe,
                        #MVARELA nuevos campos
                        'programa_id' : llave.programa_id.id,
                        'odg_id' : llave.odg_id.id,
                        'auxiliar_id' : llave.auxiliar_id.id,
                        'proyecto_id' :llave.proyecto_id.id,
                        'fin_id' : llave.fin_id.id,
                        'mon_id' : llave.mon_id.id,
                        'tc_id' : llave.tc_id.id,
                        }))
                result['value'].update({'llpapg_ids': llavep_ids})
            lines = []
            if  apg.lprapg_ids:
                for line_resumen in apg.lprapg_ids:
                    res = self.pool.get('product.product').browse(cr, uid, line_resumen.product_id.id, context=context)
                    a = res.property_account_expense.id
                    if not a:
                        a = res.categ_id.property_account_expense_categ.id
                    lines.append((0,0,{
                        'name': line_resumen.product_id.name,
                        'origin': line_resumen.apg_id.name,
                        'invoice_line_tax_id': [(6, 0, [x.id for x in line_resumen.iva])],
                        'uos_id': line_resumen.uom_id.id,
                        'product_id': line_resumen.product_id.id,
                        'account_id': a,
                        'price_unit':line_resumen.precio_estimado,
                        'price_subtotal':line_resumen.subtotal_divisa,
                        'quantity':line_resumen.cantidad_a_comprar,
                    }))
                result['value'].update({'invoice_line': lines})
            result['value'].update({'descripcion': apg.descripcion or ''})
            result['value'].update({'origin': apg.name,'nro_afectacion': apg.nro_afectacion_siif or False})
            result['value'].update({'fiscalyear_siif_id':apg.fiscalyear_siif_id and apg.fiscalyear_siif_id.id or False})
            result['value'].update({'inciso_siif_id': apg.inciso_siif_id.id})
            result['value'].update({'ue_siif_id': apg.ue_siif_id.id})
            result['value'].update({'currency_id': apg.moneda.id})
        return result

grp_invoice_compromiso()
