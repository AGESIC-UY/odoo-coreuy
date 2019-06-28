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

import time
from openerp.osv import osv, fields
from lxml import etree
from openerp import api


import logging
_logger = logging.getLogger(__name__)

class modif_afectacion_siif_log(osv.osv):
    _name = 'modif.afectacion.siif.log'
    _description = "Log de modificaciones de afectacion"
    _columns = {
        'afectacion_id': fields.many2one('grp.afectacion', u'Afectación', required=True),
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
        'siif_sec_afectacion': fields.char(u'Secuencial afectacion'),
        'siif_ult_modif': fields.integer(u'Última modificación'),
    }

modif_afectacion_siif_log()

class afectacion_anulaciones_siif_log(osv.osv):
    _name = 'afectacion.anulacion.siif.log'
    _description = "Log afectacion anulaciones"

    _columns = {
        'afectacion_id': fields.many2one('grp.afectacion', u'Afectación', required=True, ondelete='cascade'),
        'fecha': fields.date('Fecha', required=True),
        'nro_afectacion': fields.char(u'Nro afectacion', size=6),
        'nro_afect_sist_aux': fields.char(u'Nro Afectacion Sistema Aux', size=6),
    }

    _defaults = {
        'fecha': fields.date.context_today,
    }

afectacion_anulaciones_siif_log()

class grp_afectacion(osv.osv):

    _name = "grp.afectacion"
    _description = "GRP Afectacion Siif"
    _order = 'date desc, id desc'

    STATE_SELECTION = [
        ('draft','Borrador'),
        ('afectado','Afectada'),
        ('cancel','Anulada'),
        # ('anulada_siif','Anulada en SIIF')
    ]

    @api.model
    def _update_prefix(self):
        sequence= self.env['ir.sequence']
        seq_tres_en_uno = sequence.search([('code','=','sec.3en1')])
        seq_cod_obli = sequence.search([('code','=','sec.obligacion')])
        if seq_tres_en_uno:
            if seq_tres_en_uno.prefix != '%(fy)s-3en1-':
                seq_tres_en_uno.write({'prefix':'%(fy)s-3en1-'})

        if seq_cod_obli:
            if seq_cod_obli.prefix != '%(fy)s-OBL-':
                seq_cod_obli.write({'prefix':'%(fy)s-OBL-'})

        return True

    def _get_default_fiscal_year(self, cr, uid, context=None):
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id

        fiscal_year_id = fiscalyear_obj.search(cr, uid, [('date_start','<=',fecha_hoy),('date_stop','>=',fecha_hoy),('company_id','=',uid_company_id)], context=context)
        return fiscal_year_id and fiscal_year_id[0] or False

    def _get_default_inciso(self, cr, uid, context=None):
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')

        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id

        fiscal_year_id = fiscalyear_obj.search(cr, uid, [('date_start','<=',fecha_hoy),('date_stop','>=',fecha_hoy),('company_id','=',uid_company_id)], context=context)
        fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
        ids_pres_inciso = []
        if fiscal_year_id:
            ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id','=', fiscal_year_id)])
        return len(ids_pres_inciso) == 1 and ids_pres_inciso[0] or False

    def _get_default_ue(self, cr, uid, context=None):
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')
        pres_ue_obj = self.pool.get('grp.estruc_pres.ue')

        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id

        fiscal_year_id = fiscalyear_obj.search(cr, uid, [('date_start','<=',fecha_hoy),('date_stop','>=',fecha_hoy),('company_id','=',uid_company_id)], context=context)
        fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
        ids_pres_ue = []
        if fiscal_year_id:
            ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id','=', fiscal_year_id)])
            if len(ids_pres_inciso) == 1:
                ids_pres_ue = pres_ue_obj.search(cr, uid, [('inciso_id','=', ids_pres_inciso[0])])
        return len(ids_pres_ue) == 1 and ids_pres_ue[0] or False

    def _get_importes_llavep( self, cr, uid, ids, fieldname, args, context = None ):
        res = { }
        for afectacion in self.browse ( cr, uid, ids, context = context ):
            total = 0
            for llavep in afectacion.llpapg_ids:
                total += llavep.importe
            res[afectacion.id] = total
        return res

    _columns = {
        'name': fields.char('Nro. Afectacion', size=64, required=True, select=True, help=u"Número único, se calcula automáticamente cuando la afectación es creada."),
        'partner_id':fields.many2one('res.partner', 'Beneficiario', required=False),
        'state': fields.selection(STATE_SELECTION, 'Estado', size=86, readonly=True),
        'descripcion':fields.char(u'Descripción',size=300),
        'date':fields.date('Fecha', required=True, select=True),
        'currency_oc':fields.many2one('res.currency','Moneda'),
        'fecha_tipo_cambio':fields.date('Fecha de tipo de cambio'),
        'company_id': fields.many2one('res.company',u'Compañía'),
        'monto_divisa': fields.integer('Monto a autorizar divisa'),
        'monto_a_afectar': fields.function(_get_importes_llavep, string='Monto a afectar',type='integer'),
        'nro_afectacion': fields.integer(u'Nro. Afectación SIIF'),
        'siif_tipo_ejecucion': fields.many2one("tipo.ejecucion.siif", u'Tipo de ejecución', required=True),
        'siif_concepto_gasto': fields.many2one("presupuesto.concepto", 'Concepto del gasto', required=True),
        'siif_codigo_sir': fields.many2one("codigo.sir.siif", u'Código SIR', required=True),
        'siif_financiamiento': fields.many2one("financiamiento.siif", 'Fuente de financiamiento', required=True),
        'siif_tipo_documento': fields.many2one('tipo.documento.siif', u'Tipo de documento', domain=[('visible_documento_afectacion','=',True)]),
        'siif_nro_fondo_rot': fields.many2one("fondo.rotatorio.siif", 'Nro doc. fondo rotatorio'),
        'siif_ult_modif': fields.integer(u'Última modificación'),
        'siif_sec_afectacion': fields.char(u'Secuencial afectacion'),
        'siif_descripcion': fields.text(u"Descripción SIIF", size=100),
        'tipo_ejecucion_codigo_rel': fields.related("siif_tipo_ejecucion", "codigo", type="char", string=u'Código tipo ejecución'),
        'company_currency_id': fields.related('company_id','currency_id',  type='many2one', relation='res.currency', string='Moneda empresa',store=False, readonly=True),
        # Pestaña Llave Presupuestal
        'llpapg_ids' : fields.one2many ('grp.compras.lineas.llavep', 'afectacion_id', string = u'Líneas presupuesto' ), # , ondelete = 'cascade' ),
        'modif_afectacion_log_ids': fields.one2many(
            'modif.afectacion.siif.log',
            'afectacion_id',
            'Log'),
        'anulacion_siif_log_ids': fields.one2many(
            'afectacion.anulacion.siif.log',
            'afectacion_id',
            'Log anulaciones'),
        'fiscalyear_siif_id': fields.many2one('account.fiscalyear', u'Año fiscal', required=True),
        'inciso_siif_id': fields.many2one('grp.estruc_pres.inciso', u'Inciso', required=True),
        'ue_siif_id': fields.many2one('grp.estruc_pres.ue', u'Unidad ejecutora', required=True),
        'nro_afect_sist_aux': fields.char(u'Nro Afectación Sist. aux'),
    }


    _defaults = {
        'date': fields.date.context_today,
        'fecha_tipo_cambio': fields.date.context_today,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'grp.afectacion', context=c),
        'state': 'draft',
        'name': lambda obj, cr, uid, context: '/',
        'fiscalyear_siif_id': _get_default_fiscal_year,
        'inciso_siif_id': _get_default_inciso,
        'ue_siif_id': _get_default_ue,
    }

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

    def onchange_siif_financiamiento(self, cr, uid, ids, siif_financiamiento):
        vals = {'value':{} }
        if not siif_financiamiento:
            return vals
        financiamiento_obj = self.pool.get('financiamiento.siif')
        codigo_sir_obj = self.pool.get('codigo.sir.siif')
        financ = financiamiento_obj.browse(cr, uid, siif_financiamiento)
        vals['value'].update({'siif_codigo_sir': False})
        if financ.codigo == '11':
            cod_sir_id = codigo_sir_obj.search(cr, uid, [('codigo','=','05004111520028920'),('visible_documento','=',True)])
            cod_sir_id = cod_sir_id and cod_sir_id[0] or False
            vals['value'].update({'siif_codigo_sir': cod_sir_id})
        return vals

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        context=dict(context)
        fiscal_year = vals.get('fiscalyear_siif_id',False)
        context.update({'fiscalyear_id':fiscal_year})
        if vals.get('name','/')=='/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'grp.afectacion',context=context) or '/'
        order = super(grp_afectacion, self).create(cr, uid, vals, context=context)
        return order

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'nro_afect_sist_aux': False,
            'modif_afectacion_log_ids': False,
            'anulacion_siif_log_ids': False,
            'name': '/',
            'nro_afectacion': False,
            'siif_ult_modif': False,
            'siif_sec_afectacion': False,
        })
        return super(grp_afectacion, self).copy(cr, uid, id, default, context=context)

    def button_afectar( self, cr, uid, ids, context = None ):
        estructura_obj = self.pool.get('presupuesto.estructura')
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for afectacion in self.browse(cr, uid, ids):
            if afectacion.nro_afectacion:
                raise osv.except_osv("Error", "Este documento ya ha sido enviado a SIIF. Por favor, actualice el navegador.")
            sum_llaves = 0
            validacion_ok = False
            for llave in afectacion.llpapg_ids:
                # Para control 3
                sum_llaves += llave.importe

                estructura = estructura_obj.obtener_estructura(cr, uid, afectacion.fiscalyear_siif_id.id, afectacion.inciso_siif_id.inciso,
                                                           afectacion.ue_siif_id.ue,
                                                           llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                           llave.fin, llave.odg, llave.auxiliar)

                # Control 1: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (afectacion.fiscalyear_siif_id.code, afectacion.inciso_siif_id.inciso, afectacion.ue_siif_id.ue,
                                  llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon,
                                  llave.tc)
                    raise osv.except_osv(('Error'), (
                    u'No se encontró estructura con la llave presupuestal asociada a la Afectación: ' + desc_error))
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

            for llave in afectacion.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(cr, uid, afectacion.fiscalyear_siif_id.id, afectacion.inciso_siif_id.inciso,
                                               afectacion.ue_siif_id.ue,
                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                               llave.fin, llave.odg, llave.auxiliar)
                res = estructura_obj.afectar(cr, uid, afectacion.id, 1, llave.importe,
                                                     estructura)
            if not res:
                return False

            if afectacion.partner_id.tipo_doc_rupe == '':
                raise osv.except_osv((''), (u'El proveedor debe tener configurado tipo y número de documento de RUPE.'))
            if afectacion.partner_id.nro_doc_rupe == '':
                raise osv.except_osv((''), (u'El proveedor debe tener configurado tipo y número de documento de RUPE.'))

            # se afecta contra el SIIF
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            integracion_siif = company.integracion_siif or False
            if not integracion_siif:
                self.write(cr, uid, [afectacion.id], {'state': 'afectado'})
                return True

            #Se pasa el año fiscal para traer la secuencia de ese año
            if context is None:
                context = {}
            context=dict(context)
            context.update({'fiscalyear_id': afectacion.fiscalyear_siif_id and afectacion.fiscalyear_siif_id.id or False})
            nro_afect_sist_aux = self.pool.get('ir.sequence').get(cr, uid, 'sec.siif.afectacion',context=context)
            nro_afect_sist_aux = nro_afect_sist_aux[4:]
            #002 - ECHAVIANO, pasar contexto
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif',context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            #MVARELA 15-09: Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if afectacion.siif_financiamiento.exceptuado_sice or afectacion.siif_tipo_ejecucion.exceptuado_sice or afectacion.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in afectacion.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name','=',llave_pres.odg),('auxiliar','=',llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise osv.except_osv(('Error'),
                                             (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.')%(llave_pres.odg, llave_pres.auxiliar))

            xml_afectacion = generador_xml.gen_xml_afectacion(cr, uid, afectacion=afectacion, llaves_presupuestales=afectacion.llpapg_ids,
                                                              importe=afectacion.monto_a_afectar, nro_carga=nro_carga, tipo_doc_grp='02',
                                                              nro_modif_grp=0, tipo_modificacion='A', nro_afect_sist_aux=nro_afect_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_afectacion)

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
                if dicc_modif.get('nro_afectacion', None) is None:
                    dicc_modif['nro_afectacion'] = movimiento.find('nro_afectacion').text
                if dicc_modif.get('resultado', None) is None:
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_afectacion', None) is None:
                    dicc_modif['siif_sec_afectacion'] = movimiento.find('sec_afectacion').text
                if dicc_modif.get('siif_ult_modif', None) is None:
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                #MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al afectar en SIIF'),
                                     (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_afectacion', False) and dicc_modif.get('nro_afectacion', False).strip() and dicc_modif.get('resultado', False):
                    break

            # error en devolucion de numero de afectacion
            if not dicc_modif.get('nro_afectacion', None):
                raise osv.except_osv(('Error al afectar en SIIF'),
                                     (descr_error or u'Error en devolución de número de afectación por el SIIF'))

            dicc_modif['nro_afect_sist_aux'] = nro_afect_sist_aux
            res_write = self.write(cr, uid, afectacion.id, dicc_modif, context=context)

            if res_write:
                modif_afectacion_log_obj = self.pool.get('modif.afectacion.siif.log')
                for llave in afectacion.llpapg_ids:
                    vals={
                        'afectacion_id': afectacion.id,
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
                        'siif_sec_afectacion': dicc_modif['siif_sec_afectacion'] if 'siif_sec_afectacion' in dicc_modif else False,
                        'siif_ult_modif': dicc_modif['siif_ult_modif'] if 'siif_ult_modif' in dicc_modif else False,
                    }
                    modif_afectacion_log_obj.create(cr, uid, vals, context=context)
        self.write(cr, uid, ids, {'state': 'afectado'})
        return True

    def button_anular( self, cr, uid, ids, context = None ):
        # Integracion SIIF afectacion
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True

    # Anular afectacion en SIIF
    def button_anular_afectacion( self, cr, uid, ids, context = None ):
        estructura_obj = self.pool.get('presupuesto.estructura')
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')

        # comprobar primero el presupuesto
        sum_llaves = 0
        validacion_ok = False
        id = ids[0]
        afectacion = self.browse(cr, uid, id, context)
        for llave in afectacion.llpapg_ids:
            # Para control 3
            sum_llaves += llave.importe

            estructura = estructura_obj.obtener_estructura(cr, uid, afectacion.fiscalyear_siif_id.id, afectacion.inciso_siif_id.inciso,
                                                           afectacion.ue_siif_id.ue,
                                                           llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                           llave.fin, llave.odg, llave.auxiliar)

            # Control 1: que no exista una estructura
            if estructura is None:
                raise osv.except_osv(('Error'), (
                    u'No se encontró  estructura con la llave presupuestal asociada a la Afectación.'))
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

        for llave in afectacion.llpapg_ids:
            estructura = estructura_obj.obtener_estructura(cr, uid, afectacion.fiscalyear_siif_id.id, afectacion.inciso_siif_id.inciso,
                                           afectacion.ue_siif_id.ue,
                                           llave.programa, llave.proyecto, llave.mon, llave.tc,
                                           llave.fin, llave.odg, llave.auxiliar)
            res = estructura_obj.afectar(cr, uid, afectacion.id, 1, -1 * llave.importe,
                                                 estructura)
        if not res:
            return False

        for afectacion in self.browse(cr, uid, ids, context):
            if afectacion.siif_tipo_ejecucion and afectacion.siif_tipo_ejecucion.codigo == 'P' and not afectacion.siif_nro_fondo_rot:
                raise osv.except_osv(('Error'),
                                     (u'Si el tipo de ejecución es Fondo Rotatorio, se debe cargar Nro. de Fondo Rotatorio.'))

            #MVARELA 15-09: Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
            for llave_pres in afectacion.llpapg_ids:
                objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name','=',llave_pres.odg),('auxiliar','=',llave_pres.auxiliar)])
                if len(objeto_gasto_ids) > 0:
                    ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                    if not ogasto.exceptuado_sice:
                        enviar_datos_sice = True
                else:
                    raise osv.except_osv(('Error'),
                                         (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.')%(llave_pres.odg, llave_pres.auxiliar))

            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            integracion_siif = company.integracion_siif or False
            if not integracion_siif:
                self.write(cr, uid, [afectacion.id], {'state': 'cancel'})
                return True

            nro_modif = afectacion.siif_ult_modif+1
            # se afecta contra el SIIF
            if context is None:
                context = {}
            context=dict(context)
            context.update({'fiscalyear_id': afectacion.fiscalyear_siif_id and afectacion.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            monto_desafectar = 0
            for llave in afectacion.llpapg_ids:
                monto_desafectar += llave.importe
            monto_desafectar *= -1

            xml_anula_afectacion = generador_xml.gen_xml_afectacion(cr, uid, afectacion=afectacion,
                                                              llaves_presupuestales=afectacion.llpapg_ids,
                                                              importe=monto_desafectar, nro_carga=nro_carga,
                                                              tipo_doc_grp='02', nro_modif_grp=nro_modif, tipo_modificacion='N',
                                                              es_modif=True, motivo='Anulacion afectacion',
                                                              nro_afect_sist_aux=afectacion.nro_afect_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_anula_afectacion)

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
                if dicc_modif.get('nro_afectacion', None) is None:
                    dicc_modif['nro_afectacion'] = movimiento.find('nro_afectacion').text
                if dicc_modif.get('resultado', None) is None:
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_afectacion', None) is None:
                    dicc_modif['siif_sec_afectacion'] = movimiento.find('sec_afectacion').text
                if dicc_modif.get('siif_ult_modif', None) is None:
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                #MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al afectar en SIIF'),
                                     (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_afectacion', False) and dicc_modif.get('nro_afectacion', False).strip() and dicc_modif.get('resultado', False):
                    break

            anulacion_afect_log_obj = self.pool.get('afectacion.anulacion.siif.log')
            # anulacion_siif_log_ids
            vals_history={
                'afectacion_id': afectacion.id,
                'nro_afectacion': afectacion.nro_afectacion or 0,
                'nro_afect_sist_aux': afectacion.nro_afect_sist_aux or False,
            }
            anulacion_afect_log_obj.create(cr, uid, vals_history, context=context)
            # Borrando valores
            ids_log_delete = []
            for idm in afectacion.modif_afectacion_log_ids:
                ids_log_delete.append(idm.id)
            if ids_log_delete:
                self.pool.get('modif.afectacion.siif.log').unlink(cr, uid, ids_log_delete)

            dicc_modif.update({'nro_afect_sist_aux':False, 'nro_afectacion': False, 'state':'cancel'})
            res_write = self.write(cr, uid, afectacion.id, dicc_modif, context=context)
        return True

    def abrir_wizard_modif_afectacion_siif(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif', 'view_wizard_modif_afectacion_siif')
        res_id = res and res[1] or False
        ue_id = self.browse(cr, uid, ids[0]).ue_siif_id.id or False

        ctx = dict(context)
        ctx.update({
            'default_afectacion_id': ids[0],
            'default_ue_id': ue_id
        })
        return {
            'name': "Modificaciones",  # Name You want to display on wizard
            'view_mode': 'form',
            'view_id': res_id,
            'view_type': 'form',
            'res_model': 'wiz.modif.afectacion.siif',
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

        afectacion = self.browse(cr, uid, id)
        #MVARELA 15-09: Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
        enviar_datos_sice = False
        if afectacion.siif_financiamiento.exceptuado_sice or afectacion.siif_tipo_ejecucion.exceptuado_sice or afectacion.siif_concepto_gasto.exceptuado_sice:
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
        condicion.append(('afectacion_id','=',id))
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
                raise osv.except_osv(('Error'), (u'La llave presupuestal ingresada no se encuentra en la afectacion.'))
            else:
                vals = {
                    'afectacion_id': id,
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
        estructura = estructura_obj.obtener_estructura(cr, uid, afectacion.fiscalyear_siif_id.id, afectacion.inciso_siif_id.inciso,
                                                           afectacion.ue_siif_id.ue,
                                                           programa, proyecto, moneda, tipo_credito,
                                                           financiamiento, objeto_gasto, auxiliar)
        if estructura is None:
            desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                         (afectacion.fiscalyear_siif_id.code, afectacion.inciso_siif_id.inciso, afectacion.ue_siif_id.ue,
                         objeto_gasto, auxiliar, financiamiento, programa, proyecto, moneda, tipo_credito)
            raise osv.except_osv(('Error'), (u'No se encontró estructura con la llave presupuestal asociada a la Afectación: ' + desc_error))

        #** Falta agregar controles **
        res = estructura_obj.afectar(cr, uid, afectacion.id, 1, importe, estructura)

        if res['codigo']==1:
            # SE AFECTA CONTRA SIIF
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            integracion_siif = company.integracion_siif or False
            if not integracion_siif:
                return True

            if context is None:
                context = {}
            context=dict(context)
            context.update({'fiscalyear_id': afectacion.fiscalyear_siif_id and afectacion.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_modif = afectacion.siif_ult_modif+1

            xml_modif_afectacion = generador_xml.gen_xml_afectacion(cr, uid, afectacion=afectacion,
                                                                    llaves_presupuestales=[llavep],
                                                                    importe=importe, nro_carga=nro_carga,
                                                                    tipo_doc_grp='02', nro_modif_grp=nro_modif,
                                                                    tipo_modificacion=tipo_modificacion,
                                                                    es_modif=True, motivo=motivo,
                                                                    nro_afect_sist_aux=afectacion.nro_afect_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_modif_afectacion)

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
                if dicc_modif.get('nro_afectacion', None) is None:
                    dicc_modif['nro_afectacion'] = movimiento.find('nro_afectacion').text
                if dicc_modif.get('resultado', None) is None:
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_afectacion', None) is None:
                    dicc_modif['siif_sec_afectacion'] = movimiento.find('sec_afectacion').text
                if dicc_modif.get('siif_ult_modif', None) is None:
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                #MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al afectar en SIIF'),
                                     (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_afectacion', False) and dicc_modif.get('nro_afectacion', False).strip() and dicc_modif.get('resultado', False):
                    break

            res_write = self.write(cr, uid, afectacion.id, dicc_modif, context=context)

            if res_write:
                #Actualizar importe
                val_modif = {
                    'importe': importe+llavep.importe,
                }
                res_write = lineas_llavep_obj.write(cr, uid, llavep.id, val_modif, context=context)

                if res_write:
                    modif_log_obj = self.pool.get('modif.afectacion.siif.log')
                    vals={
                        'afectacion_id': afectacion.id,
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
                        'siif_sec_afectacion': dicc_modif['siif_sec_afectacion'] if 'siif_sec_afectacion' in dicc_modif else False,
                        'siif_ult_modif': dicc_modif['siif_ult_modif'] if 'siif_ult_modif' in dicc_modif else False,
                    }
                    modif_log_obj.create(cr, uid, vals, context=context)
        return True

    _sql_constraints = [
        ('name_afectacion_uniq', 'unique(name, company_id)', u'Referencia de afectación debe ser único por Compañía!'),
    ]

grp_afectacion()


# Wizard para modificacion
class wiz_modificacion_afectacion_siif(osv.osv_memory):
    _name = 'wiz.modif.afectacion.siif'
    _description = "Wizard modificación de afectacion SIIF"
    _columns = {
        'afectacion_id': fields.many2one('grp.afectacion',u'Afectación'),
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
        afectacion_obj = self.pool.get("grp.afectacion")

        ctx = dict(context)
        ctx.update({
            'es_modif': True,
            'afectacion_id': data['afectacion_id'],
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
        return afectacion_obj.enviar_modificacion_siif(cr, uid, id=data['afectacion_id'][0], context=ctx)

wiz_modificacion_afectacion_siif()
