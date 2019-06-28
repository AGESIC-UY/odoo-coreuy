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
import time
from presupuesto_estructura import TIPO_DOCUMENTO
from lxml import etree

# ================================================================
#       Autorización para gastar
# ================================================================

class grp_compras_apg(osv.osv):
    _inherit = 'grp.compras.apg'

    # def _get_default_fiscal_year(self, cr, uid, context=None):
    #     if context is None:
    #         context = {}
    #     fiscalyear_obj = self.pool.get('account.fiscalyear')
    #     fecha_hoy = time.strftime('%Y-%m-%d')
    #     uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
    #
    #     fiscal_year_id = fiscalyear_obj.search(cr, uid,
    #                                            [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
    #                                             ('company_id', '=', uid_company_id)], context=context)
    #     return fiscal_year_id and fiscal_year_id[0] or False

    # def _get_default_inciso(self, cr, uid, context=None):
    #     if context is None:
    #         context = {}
    #     fiscalyear_obj = self.pool.get('account.fiscalyear')
    #     pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')
    #     ids_pres_inciso = []  # inicializado por error en default
    #     fecha_hoy = time.strftime('%Y-%m-%d')
    #     user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
    #     uid_company_id = user.company_id.id
    #     inciso = user.company_id.inciso
    #
    #     fiscal_year_id = fiscalyear_obj.search(cr, uid,
    #                                            [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
    #                                             ('company_id', '=', uid_company_id)], context=context)
    #     fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
    #     if fiscal_year_id:
    #         ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id', '=', fiscal_year_id),('inciso','=',inciso)])
    #     return len(ids_pres_inciso) == 1 and ids_pres_inciso[0] or False

    # def _get_default_ue(self, cr, uid, context=None):
    #     if context is None:
    #         context = {}
    #     fiscalyear_obj = self.pool.get('account.fiscalyear')
    #     pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')
    #     pres_ue_obj = self.pool.get('grp.estruc_pres.ue')
    #
    #     fecha_hoy = time.strftime('%Y-%m-%d')
    #     user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
    #     uid_company_id = user.company_id.id
    #     inciso = user.company_id.inciso
    #
    #     fiscal_year_id = fiscalyear_obj.search(cr, uid,
    #                                            [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
    #                                             ('company_id', '=', uid_company_id)], context=context)
    #     fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
    #     ids_pres_ue = []
    #     if fiscal_year_id:
    #         ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id', '=', fiscal_year_id),('inciso','=',inciso)])
    #         if len(ids_pres_inciso) == 1:
    #             ids_pres_ue = pres_ue_obj.search(cr, uid, [('inciso_id', '=', ids_pres_inciso[0])])
    #     return len(ids_pres_ue) == 1 and ids_pres_ue[0] or False

    def _get_total_llavep(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for apg in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for llavep in apg.llpapg_ids:
                total += llavep.importe
            res[apg.id] = total
        return res

    def _get_llpapg_ids_editable(self, cr, uid, ids, name, args, context=None):
        res = {}
        in_grp = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_apg_Responsable_SIIF')
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = (record.state in ('en_financiero','desafectado')) and in_grp
        return res

    def _compromisos_count(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for apg in self.browse(cr, uid, ids, context=context):
            res[apg.id] = self.pool.get('grp.cotizaciones.compromiso.proveedor').search_count(cr,uid,[('apg_id', '=', apg.id)], context=context)
        return res

    _columns = {
        'llpapg_ids': fields.one2many('grp.compras.lineas.llavep', 'apg_id', string=u'Líneas presupuesto'),
        # , ondelete = 'cascade' ),
        'total_llavep': fields.function(_get_total_llavep, string='Total llave presupuestal', type='float',
                                        digits=(16, 0)),
        'llpapg_ids_editable': fields.function(_get_llpapg_ids_editable, type='boolean', store=False),
        'siif_tipo_ejecucion': fields.many2one('tipo.ejecucion.siif', u'Tipo de ejecución',
                                               domain=[('visible_documento', '=', True)]),
        'siif_concepto_gasto': fields.many2one('presupuesto.concepto', 'Concepto del gasto',
                                               domain=[('visible_documento', '=', True)]),
        'siif_codigo_sir': fields.many2one('codigo.sir.siif', u'Código SIR', domain=[('visible_documento', '=', True)]),
        'siif_financiamiento': fields.many2one('financiamiento.siif', 'Fuente de financiamiento',
                                               domain=[('visible_documento', '=', True)]),
        'siif_nro_fondo_rot': fields.many2one('fondo.rotatorio.siif', 'Nro doc. fondo rotatorio'),
        'siif_ult_modif': fields.integer(u'Última modificación'),
        'siif_sec_afectacion': fields.char(u'Secuencial afectación'),
        'siif_descripcion': fields.text(u"Descripción SIIF", size=100),
        'tipo_ejecucion_codigo_rel': fields.related("siif_tipo_ejecucion", "codigo", type="char",
                                                    string=u'Código tipo ejecución'),
        'fiscalyear_siif_id': fields.many2one('account.fiscalyear', u'Año fiscal'),
        'inciso_siif_id': fields.many2one('grp.estruc_pres.inciso', 'Inciso'),
        'ue_siif_id': fields.many2one('grp.estruc_pres.ue', 'Unidad ejecutora'),
        'nro_afect_sist_aux': fields.char(u'Nro Afectación Sist. aux'),
        'compromisos_count': fields.function(_compromisos_count, string="Compromisos", type='integer'),
    }


    _defaults = {
        # 'fiscalyear_siif_id': _get_default_fiscal_year,
        # 'inciso_siif_id': _get_default_inciso,
        # 'ue_siif_id': _get_default_ue,
    }

    def view_compromisos(self, cr, uid, ids, context):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'grp.cotizaciones.compromiso.proveedor',
            'domain': [('apg_id', 'in', ids)]
        }

    def onchange_fiscalyear_siif_id(self, cr, uid, ids, fiscalyear_siif_id):
        vals = {'value':{'inciso_siif_id': False, 'ue_siif_id': False} }
        if not fiscalyear_siif_id:
            return vals
        pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')
        pres_ue_obj = self.pool.get('grp.estruc_pres.ue')
        user = self.pool.get('res.users').browse(cr, uid, uid)
        company = user.company_id
        inciso = company.inciso
        if fiscalyear_siif_id:
            ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id','=', fiscalyear_siif_id),('inciso','=',inciso)])
            if ids_pres_inciso:
                vals['value'].update({'inciso_siif_id': ids_pres_inciso[0]})
                apg = self.browse(cr, uid, ids[0])
                ids_pres_ue = pres_ue_obj.search(cr, uid, [('inciso_id','=', ids_pres_inciso[0]),('ue','=', apg.operating_unit_id.unidad_ejecutora)])
                if ids_pres_ue:
                    vals['value'].update({'ue_siif_id': ids_pres_ue[0]})
        if ids:
            vals['value'].update({'llpapg_ids': []})
        return vals

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

    def onchange_siif_financiamiento(self, cr, uid, ids, siif_financiamiento_id):
        vals = {'value':{} }
        if not siif_financiamiento_id:
            return vals
        financiamiento_obj = self.pool.get('financiamiento.siif')
        codigo_sir_obj = self.pool.get('codigo.sir.siif')
        financ = financiamiento_obj.browse(cr, uid, siif_financiamiento_id)
        vals['value'].update({'siif_codigo_sir': False})
        #TODO: Revisar estos valores
        if financ.codigo == '11':
            cod_sir_id = codigo_sir_obj.search(cr, uid, [('codigo','=','05004111520028920'),('visible_documento','=',True)])
            cod_sir_id = cod_sir_id and cod_sir_id[0] or False
            vals['value'].update({'siif_codigo_sir': cod_sir_id})
        return vals

    #Se pasa el contexto para la secuencia por año fiscal
    def act_apg_en_financiero(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context=dict(context)
        for apg in self.browse(cr, uid, ids, context=context):
            # Se quita control, el control hace al afectar
            # #Control APGs por año fiscal
            # apg_ids_res = self.search(cr, uid, [('pc_id', '=', apg.pc_id.id),
            #                                     ('fiscalyear_siif_id', '=', apg.fiscalyear_siif_id.id),
            #                                     ('siif_tipo_ejecucion', '=', apg.siif_tipo_ejecucion.id),
            #                                     ('siif_concepto_gasto', '=', apg.siif_concepto_gasto.id),
            #                                     ('siif_financiamiento', '=', apg.siif_financiamiento.id),
            #                                     ('siif_codigo_sir', '=', apg.siif_codigo_sir.id),
            #                                     ('state', 'not in', ['nuevo','rechazado', 'anulada']),
            #                                     ('id','not in', ids)], context=context)
            # if apg_ids_res:
            #     raise osv.except_osv('Error!', u'Ya existe una APG enviada a financiero y no anulada para este '
            #                                    u'pedido de compra, año fiscal, tipo de ejecución, concepto de gasto, financiamiento y código SIR.')

            context.update({'fiscalyear_id': apg.fiscalyear_siif_id and apg.fiscalyear_siif_id.id or False})
            res = super(grp_compras_apg, self).act_apg_en_financiero(cr, uid, [apg.id], context=context)
        return True

    def apg_impactar_presupuesto(self, cr, uid, ids, context=None):
        estructura_obj = self.pool.get('presupuesto.estructura')
        controlar = True

        for apg in self.browse(cr, uid, ids, context=context):
            # Control 1: que la sumatoria de llave no sea la misma que el APG
            if apg.total_llavep <> apg.monto_fnc and controlar:
                # Mostrar error y salir
                raise osv.except_osv('Error',
                                     'La sumatoria de importes de llaves presupuestales no es igual al monto del APG.')

            for llave in apg.llpapg_ids:
                # Se obtiene la estructura
                estructura = estructura_obj.obtener_estructura(cr, uid, apg.fiscalyear_siif_id.id,
                                                               apg.inciso_siif_id.inciso,
                                                               apg.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                # Control 2: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (apg.fiscalyear_siif_id.code, apg.inciso_siif_id.inciso, apg.ue_siif_id.ue,
                                  llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon,
                                  llave.tc)
                    raise osv.except_osv(('Error'), (u'No se encontró estructura con la llave presupuestal asociada a la APG: ' + desc_error))

                # Control 3: que no alcance el disponible para el monto de la llave presupuestal
                # TODO: MVARELA, se comenta pero se deberia hacer el control con el campo Objeto específico
                # if estructura.disponible < llave.importe and controlar:
                #     raise osv.except_osv(('Error'), (
                #         'El disponible de la estructura no es suficiente para cubrir el importe de la llave presupuestal.'))

                # Se AFECTA la estructura
                res_afectar = estructura_obj.afectar(cr, uid, apg.id, TIPO_DOCUMENTO.APG, llave.importe, estructura)
        return True

    def apg_enviar_siif(self, cr, uid, ids, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for apg in self.browse(cr, uid, ids, context=context):
            if apg.nro_afectacion_siif:
                raise osv.except_osv("Error", "Este documento ya ha sido enviado a SIIF. Por favor, actualice el navegador.")
            # Control que si el tipo de ejecucion es fondo rotatorio este cargado el nro
            # VER SI EL VALOR ES "P"
            if apg.siif_tipo_ejecucion.codigo == 'P' and not apg.siif_nro_fondo_rot:
                raise osv.except_osv(('Error'),
                                     (u'Si el tipo de ejecución es Fondo Rotatorio, se debe cargar Nro. de Fondo Rotatorio.'))

            # MVARELA 15-09: Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if apg.siif_financiamiento.exceptuado_sice or apg.siif_tipo_ejecucion.exceptuado_sice or apg.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in apg.llpapg_ids:
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

            # MVARELA se pasa el año fiscal para traer la secuencia de ese año
            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': apg.fiscalyear_siif_id and apg.fiscalyear_siif_id.id or False})
            nro_afect_sist_aux = self.pool.get('ir.sequence').get(cr, uid, 'sec.siif.afectacion', context=context)
            nro_afect_sist_aux = nro_afect_sist_aux[4:]
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]

            xml_apg = generador_xml.gen_xml_apg(cr, uid, apg=apg, llaves_presupuestales=apg.llpapg_ids, importe=apg.monto_fnc, nro_carga=nro_carga, tipo_doc_grp='01', nro_modif_grp=0,
                                                                          tipo_modificacion='A', es_modif=False, motivo=False, enviar_datos_sice=enviar_datos_sice,
                                                                          nro_afect_sist_aux=nro_afect_sist_aux)
            resultado_siif = siif_proxy.put_solic(cr, uid, xml_apg)

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
                if dicc_modif.get('nro_afectacion_siif', None) is None and movimiento.find(
                        'nro_afectacion').text and movimiento.find('nro_afectacion').text.strip():
                    dicc_modif['nro_afectacion_siif'] = movimiento.find('nro_afectacion').text
                if dicc_modif.get('resultado', None) is None and movimiento.find('resultado').text and movimiento.find(
                        'resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_afectacion', None) is None and movimiento.find(
                        'sec_afectacion').text and movimiento.find('sec_afectacion').text.strip():
                    dicc_modif['siif_sec_afectacion'] = movimiento.find('sec_afectacion').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al afectar en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_afectacion_siif', False) and dicc_modif.get('resultado', False):
                    break

            # error en devolucion de numero de afectacion
            if not dicc_modif.get('nro_afectacion_siif', None):
                raise osv.except_osv(('Error al afectar en SIIF'),
                                     (descr_error or u'Error en devolución de número de afectación por el SIIF'))

            dicc_modif['nro_afect_sist_aux'] = nro_afect_sist_aux
            res_write = self.write(cr, uid, apg.id, dicc_modif, context=context)
            if res_write:
                modif_log_obj = self.pool.get('wiz.modificacion_apg_siif.log')
                for llave in apg.llpapg_ids:
                    vals = {
                        'apg_id': apg.id,
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
                        'siif_sec_afectacion': dicc_modif.get('siif_sec_afectacion', False),
                        'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                    }
                    modif_log_obj.create(cr, uid, vals, context=context)
        return True

    def controlar_apgs_anio(self, cr, uid, ids, context=None):
        for apg in self.browse(cr, uid, ids, context=context):
            # Control APGs por año fiscal
            apg_ids_res = self.search(cr, uid, [('pc_id', '=', apg.pc_id.id),
                                                ('fiscalyear_siif_id', '=', apg.fiscalyear_siif_id.id),
                                                ('siif_tipo_ejecucion', '=', apg.siif_tipo_ejecucion.id),
                                                ('siif_concepto_gasto', '=', apg.siif_concepto_gasto.id),
                                                ('siif_financiamiento', '=', apg.siif_financiamiento.id),
                                                ('siif_codigo_sir', '=', apg.siif_codigo_sir.id),
                                                ('state', '=', 'afectado'),
                                                ('id','not in', ids)], context=context)
            if apg_ids_res:
                for apg_controlar in self.browse(cr, uid, apg_ids_res, context=context):
                    if apg.llpapg_ids and apg_controlar.llpapg_ids and apg.llpapg_ids[0].mon == apg_controlar.llpapg_ids[0].mon:
                        raise osv.except_osv('Error!', u'Ya existe una APG Afectada y no anulada para este '
                                               u'pedido de compra, año fiscal, tipo de ejecución, concepto de gasto, financiamiento, código SIR y moneda.')
        return True

    def act_apg_afectado(self, cr, uid, ids, context=None):
        # PCAR realizar chequeo de campos requeridos
        self_obj = self.browse(cr, uid, ids[0])
        if not self_obj.fiscalyear_siif_id:
            raise osv.except_osv('Error!',
                                 u'Debe completar el campo Año fiscal.')
        if not self_obj.operating_unit_id:
            raise osv.except_osv('Error!',
                                 u'Debe completar el campo Unidad ejecutora responsable.')
        if not self_obj.siif_tipo_ejecucion:
            raise osv.except_osv('Error!',
                                 u'Debe completar el campo Tipo de ejecución.')
        if not self_obj.siif_concepto_gasto:
            raise osv.except_osv('Error!',
                                 u'Debe completar el campo Concepto del gasto.')
        if not self_obj.siif_financiamiento:
            raise osv.except_osv('Error!',
                                 u'Debe completar el campo Fuente de financiamiento.')
        if self_obj.tipo_ejecucion_codigo_rel != 'R' and not self_obj.siif_codigo_sir:
            raise osv.except_osv('Error!',
                                 u'Debe completar el campo Codigo SIR.')
        if not self_obj.siif_descripcion:
            raise osv.except_osv('Error!',
                                 u'Debe completar el campo Descripcion SIIF.')
        if not self_obj.inciso_siif_id:
            raise osv.except_osv('Error!',
                                 u'Debe completar el campo Inciso.')
        if not self_obj.ue_siif_id:
            raise osv.except_osv('Error!',
                                 u'Debe completar el campo Unidad ejecutora.')

        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        integracion_siif = company.integracion_siif or False
        if integracion_siif:
            for apg in self.browse(cr, uid, ids, context=context):
                if apg.nro_afectacion_siif:
                    raise osv.except_osv("Error", "Este documento ya ha sido enviado a SIIF. Por favor, actualice el navegador.")

        self.controlar_apgs_anio(cr, uid, ids, context=context)

        res = super(grp_compras_apg, self).act_apg_afectado(cr, uid, ids, context=context)

        self.apg_impactar_presupuesto(cr, uid, ids, context=context)

        if not integracion_siif:
            return res
        else:
            return self.apg_enviar_siif(cr, uid, ids, context=context)


    def apg_desafectar_presupuesto(self, cr, uid, ids, context=None):
        estructura_obj = self.pool.get('presupuesto.estructura')
        for apg in self.browse(cr, uid, ids, context=context):
            for llave in apg.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(cr, uid, apg.fiscalyear_siif_id.id,
                                                               apg.inciso_siif_id.inciso,
                                                               apg.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                if estructura is not None:
                    estructura_obj.afectar(cr, uid, apg.id, TIPO_DOCUMENTO.APG, llave.importe * -1,
                                                         estructura)
                else:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (apg.fiscalyear_siif_id.code, apg.inciso_siif_id.inciso, apg.ue_siif_id.ue,
                                  llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon,
                                  llave.tc)
                    raise osv.except_osv(('Error'), (u'No se encontró estructura con la llave presupuestal asociada a la APG: ' + desc_error))

        return True

    def apg_desafectar_siif(self, cr, uid, ids, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        for apg in self.browse(cr, uid, ids, context=context):
            if apg.siif_tipo_ejecucion.codigo == 'P' and not apg.siif_nro_fondo_rot:
                raise osv.except_osv(('Error'),
                                     (u'Si el tipo de ejecución es Fondo Rotatorio, se debe cargar Nro. de Fondo Rotatorio.'))

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if apg.siif_financiamiento.exceptuado_sice or apg.siif_tipo_ejecucion.exceptuado_sice or apg.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
                for llave_pres in apg.llpapg_ids:
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

            nro_modif = apg.siif_ult_modif + 1

            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': apg.fiscalyear_siif_id and apg.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            monto_desafectar = 0
            for llave in apg.llpapg_ids:
                monto_desafectar += llave.importe
            monto_desafectar *= -1

            xml_anular_apg = generador_xml.gen_xml_apg(cr, uid, apg=apg, llaves_presupuestales=apg.llpapg_ids,
                                                importe=monto_desafectar, nro_carga=nro_carga, tipo_doc_grp='01',
                                                nro_modif_grp=nro_modif, tipo_modificacion='N', es_modif=True,
                                                motivo="Anulacion de afectacion", enviar_datos_sice=enviar_datos_sice,
                                                nro_afect_sist_aux=apg.nro_afect_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_anular_apg)

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
                if dicc_modif.get('nro_afectacion_siif', None) is None and movimiento.find(
                        'nro_afectacion').text and movimiento.find('nro_afectacion').text.strip():
                    dicc_modif['nro_afectacion_siif'] = movimiento.find('nro_afectacion').text
                if dicc_modif.get('resultado', None) is None and movimiento.find('resultado').text and movimiento.find(
                        'resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_afectacion', None) is None and movimiento.find(
                        'sec_afectacion').text and movimiento.find('sec_afectacion').text.strip():
                    dicc_modif['siif_sec_afectacion'] = movimiento.find('sec_afectacion').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al anular afectacion en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_afectacion_siif', False) and dicc_modif.get('nro_afectacion_siif',
                                                                                   False).strip() and dicc_modif.get(
                        'resultado', False):
                    break

            anulacion_apg_log_obj = self.pool.get('apg.anulacion.siif.log')
            vals_history = {
                'apg_id': apg.id,
                'nro_afectacion_siif': apg.nro_afectacion_siif or 0,
                'nro_afect_sist_aux': apg.nro_afect_sist_aux or False,
            }
            anulacion_apg_log_obj.create(cr, uid, vals_history, context=context)
            # Borrando valores
            ids_delete = []
            for idm in apg.modif_log_ids:
                ids_delete.append(idm.id)
            if ids_delete:
                self.pool.get('wiz.modificacion_apg_siif.log').unlink(cr, uid, ids_delete)
            dicc_modif.update({'nro_afectacion_siif': 0, 'nro_afect_sist_aux': False})
            res_write = self.write(cr, uid, apg.id, dicc_modif, context=context)
        return True

    def act_apg_desafectado(self, cr, uid, ids, context=None):
        res = super(grp_compras_apg, self).act_apg_desafectado(cr, uid, ids, context=context)

        self.apg_desafectar_presupuesto(cr, uid, ids, context=context)

        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        integracion_siif = company.integracion_siif or False
        if not integracion_siif:
            return res
        else:
            return self.apg_desafectar_siif(cr, uid, ids, context=context)

    #TODO: Separar presupuesto y siif
    def enviar_modificacion_siif(self, cr, uid, id, context=None):
        generador_xml = self.pool.get('grp.siif.xml_generator')
        siif_proxy = self.pool.get('siif.proxy')
        apg = self.browse(cr, uid, id, context)
        programa = context['programa']
        proyecto = context['proyecto']
        moneda = context['moneda']
        tipo_credito = context['tipo_credito']
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

        # MVARELA 15-09: Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
        enviar_datos_sice = False
        if apg.siif_financiamiento.exceptuado_sice or apg.siif_tipo_ejecucion.exceptuado_sice or apg.siif_concepto_gasto.exceptuado_sice:
            enviar_datos_sice = False
        else:
            objeto_gasto_obj = self.pool.get('presupuesto.objeto.gasto')
            objeto_gasto_ids = objeto_gasto_obj.search(cr, uid, [('name', '=', objeto_gasto), ('auxiliar', '=', auxiliar)])
            if len(objeto_gasto_ids) > 0:
                ogasto = objeto_gasto_obj.browse(cr, uid, objeto_gasto_ids[0])
                if not ogasto.exceptuado_sice:
                    enviar_datos_sice = True
            else:
                raise osv.except_osv(('Error'),
                                     (u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                     objeto_gasto, auxiliar))

        lineas_llavep_obj = self.pool.get('grp.compras.lineas.llavep')
        condicion = []
        condicion.append(('apg_id', '=', id))
        condicion.append(('programa', '=', programa))
        condicion.append(('proyecto', '=', proyecto))
        condicion.append(('odg', '=', objeto_gasto))
        condicion.append(('auxiliar', '=', auxiliar))
        condicion.append(('fin', '=', financiamiento))
        condicion.append(('mon', '=', moneda))
        condicion.append(('tc', '=', tipo_credito))
        llavep_id = lineas_llavep_obj.search(cr, uid, condicion, context=context)
        if len(llavep_id) < 1:
            if tipo_modificacion != 'A':
                raise osv.except_osv(('Error'), (u'La llave presupuestal ingresada no se encuentra en la APG.'))
            else:
                vals = {
                    'apg_id': id,
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
        estructura = estructura_obj.obtener_estructura(cr, uid, apg.fiscalyear_siif_id.id, apg.inciso_siif_id.inciso,
                                                       apg.ue_siif_id.ue,
                                                       programa, proyecto, moneda, tipo_credito,
                                                       financiamiento, objeto_gasto, auxiliar)
        if estructura is None:
            desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                         (apg.fiscalyear_siif_id.code, apg.inciso_siif_id.inciso, apg.ue_siif_id.ue,
                          objeto_gasto, auxiliar, financiamiento, programa, proyecto, moneda,tipo_credito)
            raise osv.except_osv(('Error'),
                                 (u'No se encontró estructura con la llave presupuestal asociada a la APG: ' + desc_error))

        # ** Falta agregar controles **
        res = estructura_obj.afectar(cr, uid, apg, TIPO_DOCUMENTO.APG, importe, estructura)

        if res['codigo'] == 1:
            # SE AFECTA CONTRA SIIF
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            integracion_siif = company.integracion_siif or False
            if not integracion_siif:
                return True

            if context is None:
                context = {}
            context = dict(context)
            context.update({'fiscalyear_id': apg.fiscalyear_siif_id and apg.fiscalyear_siif_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(cr, uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_modif = apg.siif_ult_modif + 1

            xml_modificar_apg = generador_xml.gen_xml_apg(cr, uid, apg=apg, llaves_presupuestales=[llavep], importe=importe,
                                                          nro_carga=nro_carga, tipo_doc_grp='01', nro_modif_grp=nro_modif,
                                                          tipo_modificacion=tipo_modificacion,es_modif=True, motivo=motivo,
                                                          enviar_datos_sice=enviar_datos_sice, nro_afect_sist_aux=apg.nro_afect_sist_aux)

            resultado_siif = siif_proxy.put_solic(cr, uid, xml_modificar_apg)

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
                if dicc_modif.get('nro_afectacion_siif', None) is None and movimiento.find(
                        'nro_afectacion').text and movimiento.find('nro_afectacion').text.strip():
                    dicc_modif['nro_afectacion_siif'] = movimiento.find('nro_afectacion').text
                if dicc_modif.get('resultado', None) is None and movimiento.find('resultado').text and movimiento.find(
                        'resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_afectacion', None) is None and movimiento.find(
                        'sec_afectacion').text and movimiento.find('sec_afectacion').text.strip():
                    dicc_modif['siif_sec_afectacion'] = movimiento.find('sec_afectacion').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise osv.except_osv(('Error al afectar en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_afectacion_siif', False) and dicc_modif.get('nro_afectacion_siif',
                                                                                   False).strip() and dicc_modif.get(
                        'resultado', False):
                    break

            res_write_apg = self.write(cr, uid, id, dicc_modif, context=context)
            if res_write_apg:
                # Actualizar importe
                val_modif = {'importe': importe + llavep.importe}
                res_write = lineas_llavep_obj.write(cr, uid, llavep.id, val_modif, context=context)

                if res_write:
                    modif_log_obj = self.pool.get('wiz.modificacion_apg_siif.log')
                    vals = {
                        'apg_id': id,
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
                        'siif_sec_afectacion': dicc_modif.get('siif_sec_afectacion', False),
                        'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                    }
                    modif_log_obj.create(cr, uid, vals, context=context)
        return True
