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

from openerp.osv import osv
from lxml import etree
import time
from datetime import datetime
from suds.sax.text import Raw
from openerp import SUPERUSER_ID
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

from openerp import models, api

class siif_xml_generator(models.TransientModel):
    _name = 'grp.siif.xml_generator'

    #TODO: ver si los datos que van vacios tienen que ir o no los creo en el XML
    def gen_xml_afectacion(self, cr, uid, afectacion, llaves_presupuestales, importe, nro_carga, tipo_doc_grp, nro_modif_grp, tipo_modificacion, es_modif=False, motivo=False, nro_afect_sist_aux=False):
        _tipo_registro = '01'
        _tipo_registracion = '11' if es_modif else '01'
        _concepto_gasto= afectacion.siif_concepto_gasto.concepto
        _monto=str(int(round(importe,0)))

        estructura_obj = self.pool.get('presupuesto.estructura')

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'desc_tipo_mov').text = 'AFEC_ORIG_Y_MODIF'
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = afectacion.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = afectacion.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = afectacion.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp
        etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_afect_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(afectacion.nro_afectacion) if es_modif else ''
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = tipo_modificacion
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'monto_afectacion').text = _monto
        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = afectacion.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'S'
        etree.SubElement(e_movimiento_presup, 'tipo_documento')
        etree.SubElement(e_movimiento_presup, 'numero_documento').text=afectacion.name.split('-')[2]
        etree.SubElement(e_movimiento_presup, 'ano_doc_respaldo')
        etree.SubElement(e_movimiento_presup, 'fecha_doc_respaldo').text=datetime.strptime(afectacion.date, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = _concepto_gasto
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = afectacion.siif_financiamiento.codigo
        if afectacion.siif_tipo_ejecucion.codigo != 'R':
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = afectacion.siif_codigo_sir.codigo
        else:
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = ''
        etree.SubElement(e_movimiento_presup, 'partidas_mon_ext').text = 'N' if llaves_presupuestales[0].mon == '0' else 'S'
        etree.SubElement(e_movimiento_presup, 'resumen').text = afectacion.siif_descripcion or '' if not es_modif else motivo
        etree.SubElement(e_movimiento_presup, 'nro_doc_fondo_rotatorio').text = afectacion.siif_nro_fondo_rot.name or ''
        etree.SubElement(e_movimiento_presup, 'inciso_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transferencia')
        etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux')
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux')
        etree.SubElement(e_movimiento_presup, 'nro_compromiso')
        etree.SubElement(e_movimiento_presup, 'nro_obligacion')
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')
        etree.SubElement(e_movimiento_presup, 'clase_doc_benef')
        etree.SubElement(e_movimiento_presup, 'num_doc_benef')
        etree.SubElement(e_movimiento_presup, 'banco_cta_benef')
        etree.SubElement(e_movimiento_presup, 'agencia_cta_benef')
        etree.SubElement(e_movimiento_presup, 'nro_cta_benef')
        etree.SubElement(e_movimiento_presup, 'tipo_cta_benef')
        etree.SubElement(e_movimiento_presup, 'moneda_cta_benef')
        etree.SubElement(e_movimiento_presup, 'monto_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_compromiso')
        etree.SubElement(e_movimiento_presup, 'monto_obligacion')
        etree.SubElement(e_movimiento_presup, 'total_retenciones')
        etree.SubElement(e_movimiento_presup, 'liquido_pagable')
        etree.SubElement(e_movimiento_presup, 'serie_documento')
        etree.SubElement(e_movimiento_presup, 'secuencia_documento')
        etree.SubElement(e_movimiento_presup, 'fecha_recepcion')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento')
        etree.SubElement(e_movimiento_presup, 'tipo_cambio')
        etree.SubElement(e_movimiento_presup, 'anticipo')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transf_monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers_mon_ext')
        etree.SubElement(e_movimiento_presup, 'moneda')
        etree.SubElement(e_movimiento_presup, 'sec_compromiso')

        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in llaves_presupuestales:
            if llave.importe:
                estructura = estructura_obj.obtener_estructura(cr, uid, afectacion.fiscalyear_siif_id.id, afectacion.inciso_siif_id.inciso,
                                                                   afectacion.ue_siif_id.ue,
                                                                   llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                                   llave.fin, llave.odg, llave.auxiliar)

                e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
                etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                etree.SubElement(e_detalle_siif, 'tipo_registracion').text = _tipo_registracion  # 01 alta / 11 modif
                etree.SubElement(e_detalle_siif, 'programa').text = estructura.linea_programa
                etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text='PART_AFEC_ORIG_Y_MODIF_GRP'
                etree.SubElement(e_detalle_siif, 'proyecto').text = estructura.linea_proyecto
                etree.SubElement(e_detalle_siif, 'objeto_gasto').text = estructura.linea_og
                etree.SubElement(e_detalle_siif, 'auxiliar').text = estructura.linea_aux
                etree.SubElement(e_detalle_siif, 'financiamiento').text = estructura.linea_ff
                etree.SubElement(e_detalle_siif, 'moneda').text = estructura.linea_moneda
                etree.SubElement(e_detalle_siif, 'tipo_credito').text = estructura.linea_tc
                if es_modif:
                    if tipo_modificacion == 'N':
                        monto = str(int(-llave.importe))
                    else:
                        monto = _monto
                else:
                    monto = str(int(llave.importe))
                etree.SubElement(e_detalle_siif, 'importe').text = monto

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2

    def gen_xml_apg(self, cr, uid, apg, llaves_presupuestales, importe, nro_carga, tipo_doc_grp, nro_modif_grp, tipo_modificacion, es_modif=False, motivo=False, enviar_datos_sice=True, nro_afect_sist_aux=False):
        _tipo_registro = '01'
        _tipo_registracion = '11' if es_modif else '01'  # 01, 11
        _concepto_gasto= apg.siif_concepto_gasto.concepto
        _monto=str(int(round(importe,0)))

        estructura_obj = self.pool.get('presupuesto.estructura')

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        if not apg.llpapg_ids or not apg.llpapg_ids[0]:
            raise osv.except_osv(('Error'),
                                     (u'No se encontró llave presupuestal asociada al APG.'))

        estructura = estructura_obj.obtener_estructura(cr, uid, apg.fiscalyear_siif_id.id, apg.inciso_siif_id.inciso,
                                                               apg.ue_siif_id.ue,
                                                               apg.llpapg_ids[0].programa, apg.llpapg_ids[0].proyecto, apg.llpapg_ids[0].mon, apg.llpapg_ids[0].tc,
                                                               apg.llpapg_ids[0].fin, apg.llpapg_ids[0].odg, apg.llpapg_ids[0].auxiliar)

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'desc_tipo_mov').text = 'AFEC_ORIG_Y_MODIF'
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = apg.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = apg.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = apg.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp
        etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_afect_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(apg.nro_afectacion_siif) if es_modif else ''
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = tipo_modificacion
        # TODO: VER esta asignacion de fecha, si es mayor a las 21:00 va a dar el dia siguiente
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'monto_afectacion').text = _monto
        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = apg.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'S'
        etree.SubElement(e_movimiento_presup, 'tipo_documento')
        etree.SubElement(e_movimiento_presup, 'numero_documento').text=apg.name.split('-')[3]
        etree.SubElement(e_movimiento_presup, 'ano_doc_respaldo')
        etree.SubElement(e_movimiento_presup, 'fecha_doc_respaldo').text=datetime.strptime(apg.fecha, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = _concepto_gasto
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = apg.siif_financiamiento.codigo


        if apg.siif_tipo_ejecucion.codigo != 'R':
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = apg.siif_codigo_sir.codigo
        else:
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = ''
        etree.SubElement(e_movimiento_presup, 'partidas_mon_ext').text = 'N' if llaves_presupuestales[0].mon == '0' else 'S'

        #Exceptuado SICE no se envian algunos datos
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid).company_id
        exceptuado_sice = company.exceptuado_sice or False
        # Si esta en false, los controles se hacen como hasta ahora con el ODG
        if not exceptuado_sice:

            if apg.pc_id.ampliacion:
                etree.SubElement(e_movimiento_presup, 'ano_proc_compra').text = apg.pc_id.nro_adj.pedido_compra_id.name[:4] if apg.pc_id and apg.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''
            else:
                etree.SubElement(e_movimiento_presup, 'ano_proc_compra').text=datetime.strptime(apg.pc_id.date_start, '%Y-%m-%d').strftime('%Y') if apg.pc_id and apg.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            if apg.pc_id:
                if apg.pc_id.tipo_compra.idTipoCompra == 'CM':
                    etree.SubElement(e_movimiento_presup, 'inciso_proc_compra').text = apg.pc_id.inciso_proc_compra
                    etree.SubElement(e_movimiento_presup, 'unidad_ejec_proc_compra').text = apg.pc_id.unidad_ejec_proc_compra
                else:
                    etree.SubElement(e_movimiento_presup, 'inciso_proc_compra').text=estructura.linea_proy_inciso if apg.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
                    etree.SubElement(e_movimiento_presup, 'unidad_ejec_proc_compra').text = estructura.linea_ue if apg.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup, 'tipo_proc_compra').text=apg.pc_id.tipo_compra.idTipoCompra if apg.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''

            if apg.pc_id:
                if apg.pc_id.tipo_compra.idTipoCompra == 'CE' and apg.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice:
                    etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text= 'COM'
                else:
                    etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text=apg.pc_id and apg.pc_id.sub_tipo_compra and apg.pc_id.sub_tipo_compra.idSubtipoCompra or '' if apg.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            else:
                etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text=''
            etree.SubElement(e_movimiento_presup, 'nro_proc_compra').text=apg.pc_id and apg.pc_id.name.split('-')[3] or '' if apg.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup, 'nro_amp_proc_compra').text= str(apg.pc_id.nro_ampliacion) or '0' if apg.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''

        etree.SubElement(e_movimiento_presup, 'resumen').text = apg.siif_descripcion or '' if not es_modif else motivo
        etree.SubElement(e_movimiento_presup, 'nro_doc_fondo_rotatorio').text = apg.siif_nro_fondo_rot.name or ''
        etree.SubElement(e_movimiento_presup, 'inciso_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transferencia')
        etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux')
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux')
        etree.SubElement(e_movimiento_presup, 'nro_compromiso')
        etree.SubElement(e_movimiento_presup, 'nro_obligacion')
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')
        etree.SubElement(e_movimiento_presup, 'clase_doc_benef')
        etree.SubElement(e_movimiento_presup, 'num_doc_benef')
        etree.SubElement(e_movimiento_presup, 'banco_cta_benef')
        etree.SubElement(e_movimiento_presup, 'agencia_cta_benef')
        etree.SubElement(e_movimiento_presup, 'nro_cta_benef')
        etree.SubElement(e_movimiento_presup, 'tipo_cta_benef')
        etree.SubElement(e_movimiento_presup, 'moneda_cta_benef')
        etree.SubElement(e_movimiento_presup, 'monto_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_compromiso')
        etree.SubElement(e_movimiento_presup, 'monto_obligacion')
        etree.SubElement(e_movimiento_presup, 'total_retenciones')
        etree.SubElement(e_movimiento_presup, 'liquido_pagable')
        etree.SubElement(e_movimiento_presup, 'serie_documento')
        etree.SubElement(e_movimiento_presup, 'secuencia_documento')
        etree.SubElement(e_movimiento_presup, 'fecha_recepcion')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento')
        etree.SubElement(e_movimiento_presup, 'tipo_cambio')
        etree.SubElement(e_movimiento_presup, 'anticipo')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transf_monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers_mon_ext')
        etree.SubElement(e_movimiento_presup, 'moneda')
        etree.SubElement(e_movimiento_presup, 'sec_compromiso')

        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in llaves_presupuestales:
            if llave.importe:
                estructura = estructura_obj.obtener_estructura(cr, uid, apg.fiscalyear_siif_id.id, apg.inciso_siif_id.inciso,
                                                                   apg.ue_siif_id.ue,
                                                                   llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                                   llave.fin, llave.odg, llave.auxiliar)

                e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
                etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                etree.SubElement(e_detalle_siif, 'tipo_registracion').text = _tipo_registracion  # 01 alta / 11 modif
                etree.SubElement(e_detalle_siif, 'programa').text = estructura.linea_programa
                etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text='PART_AFEC_ORIG_Y_MODIF_GRP'
                etree.SubElement(e_detalle_siif, 'proyecto').text = estructura.linea_proyecto
                etree.SubElement(e_detalle_siif, 'objeto_gasto').text = estructura.linea_og
                etree.SubElement(e_detalle_siif, 'auxiliar').text = estructura.linea_aux
                etree.SubElement(e_detalle_siif, 'financiamiento').text = estructura.linea_ff
                etree.SubElement(e_detalle_siif, 'moneda').text = estructura.linea_moneda
                etree.SubElement(e_detalle_siif, 'tipo_credito').text = estructura.linea_tc
                if es_modif:
                    if tipo_modificacion == 'N':
                        monto = str(int(-llave.importe))
                    else:
                        monto = _monto
                else:
                    monto = str(int(llave.importe))
                etree.SubElement(e_detalle_siif, 'importe').text = monto

        e_retencion = etree.SubElement(e_movimiento_presup, 'Retenciones')

        e_ces_o_emb = etree.SubElement(e_movimiento_presup, 'CesionesOEmbargos')
        e_ces_o_emb_siif = etree.SubElement(e_ces_o_emb, 'Impuestos')

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2

    def gen_xml_compromiso(self, cr, uid, compromiso, llaves_presupuestales, importe, nro_carga, tipo_doc_grp, nro_modif_grp, tipo_modificacion, es_modif=False, motivo=False, enviar_datos_sice=True, nro_comp_sist_aux=False):
        _tipo_registro = '01'
        _tipo_registracion = '12' if es_modif else '02'  # 02, 12
        _concepto_gasto= compromiso.siif_concepto_gasto.concepto
        _monto=str(int(round(importe,0)))

        estructura_obj = self.pool.get('presupuesto.estructura')

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        estructura = estructura_obj.obtener_estructura(cr, uid, compromiso.fiscalyear_siif_id.id, compromiso.inciso_siif_id.inciso,
                                                               compromiso.ue_siif_id.ue,
                                                               compromiso.llpapg_ids[0].programa, compromiso.llpapg_ids[0].proyecto,
                                                               compromiso.llpapg_ids[0].mon, compromiso.llpapg_ids[0].tc,
                                                               compromiso.llpapg_ids[0].fin, compromiso.llpapg_ids[0].odg, compromiso.llpapg_ids[0].auxiliar)

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'desc_tipo_mov').text = 'COMP_ORIG_Y_MODIF_GRP'
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = compromiso.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = compromiso.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = compromiso.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp
        if compromiso.tipo_afectacion == 'apg' and compromiso.apg_id.id:
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = compromiso.apg_id.nro_afect_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(compromiso.apg_id.nro_afectacion_siif)
        elif compromiso.tipo_afectacion == 'afectacion' and compromiso.afectacion_id.id:
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = compromiso.afectacion_id.nro_afect_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(compromiso.afectacion_id.nro_afectacion)
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'sec_afectacion')
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = tipo_modificacion
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'monto_afectacion').text = _monto
        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = compromiso.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'S'
        etree.SubElement(e_movimiento_presup, 'tipo_documento').text = compromiso.siif_tipo_documento.codigo
        etree.SubElement(e_movimiento_presup, 'numero_documento').text = compromiso.name.split('-')[2]
        etree.SubElement(e_movimiento_presup, 'ano_doc_respaldo')
        etree.SubElement(e_movimiento_presup, 'fecha_doc_respaldo').text = datetime.strptime(compromiso.date, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = _concepto_gasto
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = compromiso.siif_financiamiento.codigo
        if compromiso.siif_tipo_ejecucion.codigo != 'R':
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = compromiso.siif_codigo_sir.codigo
        else:
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = ''
        etree.SubElement(e_movimiento_presup, 'partidas_mon_ext').text = 'N' if llaves_presupuestales[0].mon == '0' else 'S'

        #Exceptuado SICE no se envian algunos datos
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid).company_id
        exceptuado_sice = company.exceptuado_sice or False
        # Si esta en false, los controles se hacen como hasta ahora con el ODG
        if not exceptuado_sice and compromiso.tipo_afectacion == 'apg':
            etree.SubElement(e_movimiento_presup, 'ano_proc_compra').text=datetime.strptime(compromiso.pedido_compra_id.date_start, '%Y-%m-%d').strftime('%Y') if compromiso.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup, 'inciso_proc_compra').text=estructura.linea_proy_inciso if compromiso.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup, 'unidad_ejec_proc_compra').text=estructura.linea_ue if compromiso.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup, 'tipo_proc_compra').text=compromiso.pedido_compra_id.tipo_compra.idTipoCompra if compromiso.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            if compromiso.pedido_compra_id.tipo_compra.idTipoCompra == 'CE' and compromiso.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice:
                etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text= 'COM'
            else:
                etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text=compromiso.pedido_compra_id.sub_tipo_compra.idSubtipoCompra if compromiso.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup, 'nro_proc_compra').text = compromiso.pedido_compra_id.name.split('-')[3] if compromiso.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup, 'nro_amp_proc_compra').text= str(compromiso.pedido_compra_id.nro_ampliacion) or '0' if compromiso.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''

        etree.SubElement(e_movimiento_presup, 'resumen').text = compromiso.siif_descripcion or '' if not es_modif else motivo
        etree.SubElement(e_movimiento_presup, 'nro_doc_fondo_rotatorio').text = compromiso.siif_nro_fondo_rot.name or ''
        etree.SubElement(e_movimiento_presup, 'inciso_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transferencia')
        etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_comp_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux')
        etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = (str(compromiso.nro_compromiso) or '') if es_modif or tipo_modificacion == 'N' else ''
        etree.SubElement(e_movimiento_presup, 'nro_obligacion')
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')
        if compromiso.partner_id.es_inciso_default or compromiso.siif_tipo_ejecucion.codigo == 'P':
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text= 'T'
            # agregado el numero doc benef
            inciso = int(company.inciso) #TODO: Ver si se saca de algun lado o es fijo
            # u_e = int(company.u_e) #TODO: Ver si se saca de algun lado o es fijo
            u_e = compromiso.unidad_ejecutora_id.codigo
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text= '%s%s' % (str(inciso).zfill(2),str(u_e).zfill(3))
        else:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text= compromiso.partner_id.tipo_doc_rupe[0] if compromiso.partner_id.tipo_doc_rupe else ''
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text=compromiso.partner_id.nro_doc_rupe or ''
        etree.SubElement(e_movimiento_presup, 'banco_cta_benef')
        etree.SubElement(e_movimiento_presup, 'agencia_cta_benef')
        etree.SubElement(e_movimiento_presup, 'nro_cta_benef')
        etree.SubElement(e_movimiento_presup, 'tipo_cta_benef')
        etree.SubElement(e_movimiento_presup, 'moneda_cta_benef')
        etree.SubElement(e_movimiento_presup, 'monto_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_compromiso').text = _monto
        etree.SubElement(e_movimiento_presup, 'monto_obligacion')
        etree.SubElement(e_movimiento_presup, 'total_retenciones')
        etree.SubElement(e_movimiento_presup, 'liquido_pagable')
        etree.SubElement(e_movimiento_presup, 'serie_documento')
        etree.SubElement(e_movimiento_presup, 'secuencia_documento')
        etree.SubElement(e_movimiento_presup, 'fecha_recepcion')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento')
        etree.SubElement(e_movimiento_presup, 'tipo_cambio')
        etree.SubElement(e_movimiento_presup, 'anticipo')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transf_monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers_mon_ext')
        etree.SubElement(e_movimiento_presup, 'moneda')
        etree.SubElement(e_movimiento_presup, 'sec_compromiso')

        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in llaves_presupuestales:
            if llave.importe:
                estructura = estructura_obj.obtener_estructura(cr, uid, compromiso.fiscalyear_siif_id.id, compromiso.inciso_siif_id.inciso,
                                                                       compromiso.ue_siif_id.ue,
                                                                       llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                                       llave.fin, llave.odg, llave.auxiliar)
                e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
                etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                etree.SubElement(e_detalle_siif, 'tipo_registracion').text = _tipo_registracion  # 02 alta / 12 modif
                etree.SubElement(e_detalle_siif, 'programa').text = estructura.linea_programa
                etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text='PART_COMP_ORIG_Y_MODIF_GRP'
                etree.SubElement(e_detalle_siif, 'proyecto').text = estructura.linea_proyecto
                etree.SubElement(e_detalle_siif, 'objeto_gasto').text = estructura.linea_og
                etree.SubElement(e_detalle_siif, 'auxiliar').text = estructura.linea_aux
                etree.SubElement(e_detalle_siif, 'financiamiento').text = estructura.linea_ff
                etree.SubElement(e_detalle_siif, 'moneda').text = estructura.linea_moneda
                etree.SubElement(e_detalle_siif, 'tipo_credito').text = estructura.linea_tc
                if es_modif:
                    if tipo_modificacion == 'N':
                        monto = str(int(-llave.importe))
                    else:
                        monto = _monto
                else:
                    monto = str(int(llave.importe))
                etree.SubElement(e_detalle_siif, 'importe').text = monto

        e_retencion = etree.SubElement(e_movimiento_presup, 'Retenciones')

        e_ces_o_emb = etree.SubElement(e_movimiento_presup, 'CesionesOEmbargos')
        e_ces_o_emb_siif = etree.SubElement(e_ces_o_emb, 'Impuestos')

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2

    def gen_xml_oc(self, cr, uid, orden_compra, llaves_presupuestales, importe, nro_carga, tipo_doc_grp, nro_modif_grp, tipo_modificacion, es_modif=False, motivo=False, enviar_datos_sice=True, nro_comp_sist_aux=False):
        _tipo_registro = '01'
        _tipo_registracion = '12' if es_modif else '02'  # 02, 12
        _concepto_gasto= orden_compra.siif_concepto_gasto.concepto
        _monto=str(int(round(importe,0)))

        estructura_obj = self.pool.get('presupuesto.estructura')

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        estructura = estructura_obj.obtener_estructura(cr, uid, orden_compra.fiscalyear_siif_id.id, orden_compra.inciso_siif_id.inciso,
                                                               orden_compra.ue_siif_id.ue,
                                                               orden_compra.llpapg_ids[0].programa, orden_compra.llpapg_ids[0].proyecto,
                                                               orden_compra.llpapg_ids[0].mon, orden_compra.llpapg_ids[0].tc,
                                                               orden_compra.llpapg_ids[0].fin, orden_compra.llpapg_ids[0].odg, orden_compra.llpapg_ids[0].auxiliar)


        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'desc_tipo_mov').text = 'COMP_ORIG_Y_MODIF_GRP'
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = orden_compra.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = orden_compra.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = orden_compra.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp
        etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = orden_compra.pc_apg_id and orden_compra.pc_apg_id.nro_afect_sist_aux or ''
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = orden_compra.pc_apg_id and str(orden_compra.pc_apg_id.nro_afectacion_siif) or ''
        etree.SubElement(e_movimiento_presup, 'sec_afectacion')
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = tipo_modificacion
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'monto_afectacion').text = _monto
        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = orden_compra.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'S'
        etree.SubElement(e_movimiento_presup, 'tipo_documento').text = orden_compra.siif_tipo_documento.codigo
        etree.SubElement(e_movimiento_presup, 'numero_documento').text = orden_compra.name.split('-')[3]
        etree.SubElement(e_movimiento_presup, 'ano_doc_respaldo')
        etree.SubElement(e_movimiento_presup, 'fecha_doc_respaldo').text = datetime.strptime(orden_compra.date_order, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = _concepto_gasto
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = orden_compra.siif_financiamiento.codigo
        if orden_compra.siif_tipo_ejecucion.codigo != 'R':
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = orden_compra.siif_codigo_sir.codigo
        else:
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = ''
        etree.SubElement(e_movimiento_presup, 'partidas_mon_ext').text = 'N' if llaves_presupuestales[0].mon == '0' else 'S'

        #Exceptuado SICE no se envian algunos datos
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid).company_id
        exceptuado_sice = company.exceptuado_sice or False
        # Si esta en false, los controles se hacen como hasta ahora con el ODG
        if not exceptuado_sice:
            if orden_compra.pedido_compra_id.ampliacion:
                etree.SubElement(e_movimiento_presup, 'ano_proc_compra').text=orden_compra.doc_origen.pedido_compra_id.name[:4] if orden_compra.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            else:
                etree.SubElement(e_movimiento_presup, 'ano_proc_compra').text=datetime.strptime(orden_compra.pedido_compra_id.date_start, '%Y-%m-%d').strftime('%Y') if orden_compra.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup, 'inciso_proc_compra').text=estructura.linea_proy_inciso if orden_compra.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup, 'unidad_ejec_proc_compra').text=estructura.linea_ue if orden_compra.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup, 'tipo_proc_compra').text=orden_compra.pedido_compra_id.tipo_compra.idTipoCompra if orden_compra.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            if orden_compra.pedido_compra_id.tipo_compra.idTipoCompra == 'CE' and orden_compra.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice:
                etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text= 'COM'
            else:
                etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text=orden_compra.pedido_compra_id.sub_tipo_compra.idSubtipoCompra if orden_compra.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''

            etree.SubElement(e_movimiento_presup, 'nro_proc_compra').text = orden_compra.doc_origen.pedido_compra_id.name[orden_compra.doc_origen.pedido_compra_id.name.rfind('-')+1:] if orden_compra.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''


            etree.SubElement(e_movimiento_presup, 'nro_amp_proc_compra').text= str(orden_compra.pedido_compra_id.nro_ampliacion) or '0' if orden_compra.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
        etree.SubElement(e_movimiento_presup, 'resumen').text = orden_compra.siif_descripcion or '' if not es_modif else motivo
        etree.SubElement(e_movimiento_presup, 'nro_doc_fondo_rotatorio').text = orden_compra.siif_nro_fondo_rot.name or ''
        etree.SubElement(e_movimiento_presup, 'inciso_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transferencia')
        etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_comp_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux')
        etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(orden_compra.nro_compromiso) if es_modif or tipo_modificacion == 'N' else ''
        etree.SubElement(e_movimiento_presup, 'nro_obligacion')
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')
        context = {}
        if orden_compra.siif_tipo_ejecucion.codigo == 'P':
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text= 'T'
            inciso = int(company.inciso)
            # u_e = int(company.u_e)
            u_e = int(orden_compra.operating_unit_id.unidad_ejecutora)
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text= '%s%s' % (str(inciso).zfill(2),str(u_e).zfill(3))
        else:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text= orden_compra.partner_id.tipo_doc_rupe[0] if orden_compra.partner_id.tipo_doc_rupe else ''
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text=orden_compra.partner_id.nro_doc_rupe or ''
        etree.SubElement(e_movimiento_presup, 'banco_cta_benef')
        etree.SubElement(e_movimiento_presup, 'agencia_cta_benef')
        etree.SubElement(e_movimiento_presup, 'nro_cta_benef')
        etree.SubElement(e_movimiento_presup, 'tipo_cta_benef')
        etree.SubElement(e_movimiento_presup, 'moneda_cta_benef')
        etree.SubElement(e_movimiento_presup, 'monto_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_compromiso').text = _monto
        etree.SubElement(e_movimiento_presup, 'monto_obligacion')
        etree.SubElement(e_movimiento_presup, 'total_retenciones')
        etree.SubElement(e_movimiento_presup, 'liquido_pagable')
        etree.SubElement(e_movimiento_presup, 'serie_documento')
        etree.SubElement(e_movimiento_presup, 'secuencia_documento')
        etree.SubElement(e_movimiento_presup, 'fecha_recepcion')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento')
        etree.SubElement(e_movimiento_presup, 'tipo_cambio')
        etree.SubElement(e_movimiento_presup, 'anticipo')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transf_monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers_mon_ext')
        etree.SubElement(e_movimiento_presup, 'moneda')
        etree.SubElement(e_movimiento_presup, 'sec_compromiso')

        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in llaves_presupuestales:
            if llave.importe:
                estructura = estructura_obj.obtener_estructura(cr, uid, orden_compra.fiscalyear_siif_id.id, orden_compra.inciso_siif_id.inciso,
                                                                       orden_compra.ue_siif_id.ue,
                                                                       llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                                       llave.fin, llave.odg, llave.auxiliar)
                e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
                etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                etree.SubElement(e_detalle_siif, 'tipo_registracion').text = _tipo_registracion  # 02 alta / 12 modif
                etree.SubElement(e_detalle_siif, 'programa').text = estructura.linea_programa
                etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text='PART_COMP_ORIG_Y_MODIF_GRP'
                etree.SubElement(e_detalle_siif, 'proyecto').text = estructura.linea_proyecto
                etree.SubElement(e_detalle_siif, 'objeto_gasto').text = estructura.linea_og
                etree.SubElement(e_detalle_siif, 'auxiliar').text = estructura.linea_aux
                etree.SubElement(e_detalle_siif, 'financiamiento').text = estructura.linea_ff
                etree.SubElement(e_detalle_siif, 'moneda').text = estructura.linea_moneda
                etree.SubElement(e_detalle_siif, 'tipo_credito').text = estructura.linea_tc
                if es_modif:
                    if tipo_modificacion == 'N':
                        monto = str(int(-llave.importe))
                    else:
                        monto = _monto
                else:
                    monto = str(int(llave.importe))
                etree.SubElement(e_detalle_siif, 'importe').text = monto

        e_retencion = etree.SubElement(e_movimiento_presup, 'Retenciones')
        e_ces_o_emb = etree.SubElement(e_movimiento_presup, 'CesionesOEmbargos')
        e_ces_o_emb_siif = etree.SubElement(e_ces_o_emb, 'Impuestos')

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2

    def gen_xml_cotizacion_compromiso(self, cr, uid, cotizacion_compromiso, llaves_presupuestales, importe, nro_carga, tipo_doc_grp, nro_modif_grp,
                   tipo_modificacion, es_modif=False, motivo=False, enviar_datos_sice=True, nro_comp_sist_aux=False):
        _tipo_registro = '01'
        _tipo_registracion = '12' if es_modif else '02'  # 02, 12
        _concepto_gasto = cotizacion_compromiso.siif_concepto_gasto.concepto
        _monto = str(int(round(importe, 0)))

        estructura_obj = self.pool.get('presupuesto.estructura')

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        estructura = estructura_obj.obtener_estructura(cr, uid, cotizacion_compromiso.fiscalyear_id.id,
                                                       cotizacion_compromiso.inciso_siif_id.inciso,
                                                       cotizacion_compromiso.ue_siif_id.ue,
                                                       cotizacion_compromiso.llpapg_ids[0].programa,
                                                       cotizacion_compromiso.llpapg_ids[0].proyecto,
                                                       cotizacion_compromiso.llpapg_ids[0].mon, cotizacion_compromiso.llpapg_ids[0].tc,
                                                       cotizacion_compromiso.llpapg_ids[0].fin, cotizacion_compromiso.llpapg_ids[0].odg,
                                                       cotizacion_compromiso.llpapg_ids[0].auxiliar)

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'desc_tipo_mov').text = 'COMP_ORIG_Y_MODIF_GRP'
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = cotizacion_compromiso.fiscalyear_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = cotizacion_compromiso.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = cotizacion_compromiso.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp
        etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = cotizacion_compromiso.apg_id and cotizacion_compromiso.apg_id.nro_afect_sist_aux or ''
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = cotizacion_compromiso.apg_id and str(cotizacion_compromiso.apg_id.nro_afectacion_siif) or ''
        etree.SubElement(e_movimiento_presup, 'sec_afectacion')
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = tipo_modificacion
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'monto_afectacion').text = _monto
        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = cotizacion_compromiso.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'S'
        etree.SubElement(e_movimiento_presup, 'tipo_documento').text = cotizacion_compromiso.siif_tipo_documento.codigo
        etree.SubElement(e_movimiento_presup, 'numero_documento').text = cotizacion_compromiso.name.split('-')[2]
        etree.SubElement(e_movimiento_presup, 'ano_doc_respaldo')
        etree.SubElement(e_movimiento_presup, 'fecha_doc_respaldo').text = datetime.strptime(cotizacion_compromiso.date, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = _concepto_gasto
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = cotizacion_compromiso.siif_financiamiento.codigo

        if cotizacion_compromiso.siif_tipo_ejecucion.codigo != 'R':
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = cotizacion_compromiso.siif_codigo_sir.codigo
        else:
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = ''
        etree.SubElement(e_movimiento_presup, 'partidas_mon_ext').text = 'N' if llaves_presupuestales[0].mon == '0' else 'S'

        # Exceptuado SICE no se envian algunos datos
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid).company_id
        exceptuado_sice = company.exceptuado_sice or False
        # Si esta en false, los controles se hacen como hasta ahora con el ODG
        if not exceptuado_sice:
            if cotizacion_compromiso.pc_id.ampliacion:
                etree.SubElement(e_movimiento_presup,'ano_proc_compra').text = cotizacion_compromiso.cot_id.nro_pedido_original_id.name[:4] if cotizacion_compromiso.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            else:
                etree.SubElement(e_movimiento_presup, 'ano_proc_compra').text = datetime.strptime(cotizacion_compromiso.pc_id.date_start, '%Y-%m-%d').strftime('%Y') if cotizacion_compromiso.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''

            if cotizacion_compromiso.pc_id:
                if cotizacion_compromiso.pc_id.tipo_compra.idTipoCompra in ['CM']:
                    etree.SubElement(e_movimiento_presup, 'inciso_proc_compra').text = cotizacion_compromiso.pc_id.inciso_proc_compra
                    etree.SubElement(e_movimiento_presup, 'unidad_ejec_proc_compra').text = cotizacion_compromiso.pc_id.unidad_ejec_proc_compra
                else:
                    etree.SubElement(e_movimiento_presup,'inciso_proc_compra').text = estructura.linea_proy_inciso if cotizacion_compromiso.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''
                    etree.SubElement(e_movimiento_presup,'unidad_ejec_proc_compra').text = estructura.linea_ue if cotizacion_compromiso.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup,'tipo_proc_compra').text = cotizacion_compromiso.pc_id.tipo_compra.idTipoCompra if cotizacion_compromiso.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''
            if cotizacion_compromiso.pc_id.tipo_compra.idTipoCompra == 'CE' and cotizacion_compromiso.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice:
                etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text = 'COM'
            else:
                etree.SubElement(e_movimiento_presup,'subtipo_proc_compra').text = cotizacion_compromiso.pc_id.sub_tipo_compra.idSubtipoCompra if cotizacion_compromiso.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''
                # etree.SubElement(e_movimiento_presup, 'nro_proc_compra').text = orden_compra.pedido_compra_id.name.split('-')[3] if orden_compra.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
            etree.SubElement(e_movimiento_presup,'nro_proc_compra').text = cotizacion_compromiso.pc_id.name[cotizacion_compromiso.pc_id.name.rfind('-')+1:] if cotizacion_compromiso.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''


            etree.SubElement(e_movimiento_presup, 'nro_amp_proc_compra').text = str(cotizacion_compromiso.pc_id.nro_ampliacion) or '0' if cotizacion_compromiso.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''
        etree.SubElement(e_movimiento_presup,'resumen').text = cotizacion_compromiso.siif_descripcion or '' if not es_modif else motivo
        etree.SubElement(e_movimiento_presup,'nro_doc_fondo_rotatorio').text = cotizacion_compromiso.siif_nro_fondo_rot.name or ''
        etree.SubElement(e_movimiento_presup, 'inciso_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transferencia')
        etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_comp_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux')
        etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(cotizacion_compromiso.nro_compromiso) if es_modif or tipo_modificacion == 'N' else ''
        etree.SubElement(e_movimiento_presup, 'nro_obligacion')
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')
        context = {}
        if cotizacion_compromiso.siif_tipo_ejecucion.codigo == 'P':
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text = 'T'
            inciso = int(company.inciso)
            # u_e = int(company.u_e)
            u_e = int(cotizacion_compromiso.apg_id.operating_unit_id.unidad_ejecutora)
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text = '%s%s' % (str(inciso).zfill(2), str(u_e).zfill(3))
        else:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text = cotizacion_compromiso.provider_id.tipo_doc_rupe[0] if cotizacion_compromiso.provider_id.tipo_doc_rupe else ''
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text = cotizacion_compromiso.provider_id.nro_doc_rupe or ''
        etree.SubElement(e_movimiento_presup, 'banco_cta_benef')
        etree.SubElement(e_movimiento_presup, 'agencia_cta_benef')
        etree.SubElement(e_movimiento_presup, 'nro_cta_benef')
        etree.SubElement(e_movimiento_presup, 'tipo_cta_benef')
        etree.SubElement(e_movimiento_presup, 'moneda_cta_benef')
        etree.SubElement(e_movimiento_presup, 'monto_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_compromiso').text = _monto
        etree.SubElement(e_movimiento_presup, 'monto_obligacion')
        etree.SubElement(e_movimiento_presup, 'total_retenciones')
        etree.SubElement(e_movimiento_presup, 'liquido_pagable')
        etree.SubElement(e_movimiento_presup, 'serie_documento')
        etree.SubElement(e_movimiento_presup, 'secuencia_documento')
        etree.SubElement(e_movimiento_presup, 'fecha_recepcion')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento')
        etree.SubElement(e_movimiento_presup, 'tipo_cambio')
        etree.SubElement(e_movimiento_presup, 'anticipo')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transf_monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers_mon_ext')
        etree.SubElement(e_movimiento_presup, 'moneda')
        etree.SubElement(e_movimiento_presup, 'sec_compromiso')

        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in llaves_presupuestales:
            if llave.importe:
                estructura = estructura_obj.obtener_estructura(cr, uid, cotizacion_compromiso.fiscalyear_id.id,
                                                               cotizacion_compromiso.inciso_siif_id.inciso,
                                                               cotizacion_compromiso.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
                etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                etree.SubElement(e_detalle_siif, 'tipo_registracion').text = _tipo_registracion  # 02 alta / 12 modif
                etree.SubElement(e_detalle_siif, 'programa').text = estructura.linea_programa
                etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text = 'PART_COMP_ORIG_Y_MODIF_GRP'
                etree.SubElement(e_detalle_siif, 'proyecto').text = estructura.linea_proyecto
                etree.SubElement(e_detalle_siif, 'objeto_gasto').text = estructura.linea_og
                etree.SubElement(e_detalle_siif, 'auxiliar').text = estructura.linea_aux
                etree.SubElement(e_detalle_siif, 'financiamiento').text = estructura.linea_ff
                etree.SubElement(e_detalle_siif, 'moneda').text = estructura.linea_moneda
                etree.SubElement(e_detalle_siif, 'tipo_credito').text = estructura.linea_tc
                if es_modif:
                    if tipo_modificacion == 'N':
                        monto = str(int(-llave.importe))
                    else:
                        monto = _monto
                else:
                    monto = str(int(llave.importe))
                etree.SubElement(e_detalle_siif, 'importe').text = monto

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2

    def gen_xml_obligacion(self, cr, uid, factura, llaves_presupuestales, importe, nro_carga, tipo_doc_grp, nro_modif_grp, tipo_modificacion, es_modif=False, retenciones=False, motivo=False, enviar_datos_sice=True, nro_obl_sist_aux=False):
        _tipo_registracion= '03' if es_modif is False else '13'

        #enviar factura como 3en1
        if factura.doc_type=='3en1_invoice':
            _tipo_registracion= '04' if es_modif is False else '14'

        _tipo_registro = '01'
        _concepto_gasto = factura.siif_concepto_gasto.concepto
        _monto=str(int(round(importe,0)))

        estructura_obj = self.pool.get('presupuesto.estructura')

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        estructura = estructura_obj.obtener_estructura(cr, uid, factura.fiscalyear_siif_id.id,
                                                       factura.inciso_siif_id.inciso,
                                                       factura.ue_siif_id.ue,
                                                       llaves_presupuestales[0].programa,
                                                       llaves_presupuestales[0].proyecto,
                                                       llaves_presupuestales[0].mon,
                                                       llaves_presupuestales[0].tc,
                                                       llaves_presupuestales[0].fin,
                                                       llaves_presupuestales[0].odg,
                                                       llaves_presupuestales[0].auxiliar)

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'desc_tipo_mov').text = 'OBL_ORIG_Y_MODIF_GRP' #TODO: si es '3en1_invoice' mandar otra descripcion
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = factura.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = factura.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = factura.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp

        if factura.doc_type == 'obligacion_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = factura.afectacion_id.nro_afect_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = factura.compromiso_id.nro_comp_sist_aux
        elif factura.doc_type == '3en1_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_obl_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_obl_sist_aux
        else:
            #Enviar factura como 3en1
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text =  factura.compromiso_proveedor_id and factura.compromiso_proveedor_id.apg_id and factura.compromiso_proveedor_id.apg_id.nro_afect_sist_aux or ''
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text =  factura.compromiso_proveedor_id and factura.compromiso_proveedor_id.nro_comp_sist_aux or ''

        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'sec_afectacion')
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = tipo_modificacion
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'monto_afectacion')#.text = _monto
        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = factura.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'T' if factura.doc_type == '3en1_invoice' else 'S'
        etree.SubElement(e_movimiento_presup, 'tipo_documento').text = factura.siif_tipo_documento.codigo
        etree.SubElement(e_movimiento_presup, 'numero_documento').text= factura.supplier_invoice_number or '' if factura.siif_tipo_documento.codigo in ['22','21'] else '' # 22 - Factura, 21 - Nómina
        etree.SubElement(e_movimiento_presup, 'serie_documento').text = factura.serie_factura if factura.siif_tipo_documento.codigo == '22' else ''
        etree.SubElement(e_movimiento_presup, 'secuencia_documento').text = str(factura.sec_factura) if factura.siif_tipo_documento.codigo == '22' else ''
        etree.SubElement(e_movimiento_presup, 'fecha_doc_respaldo').text='' if factura.doc_type=='3en1_invoice' else datetime.strptime(factura.date_invoice, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = _concepto_gasto
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = factura.siif_financiamiento.codigo

        if factura.siif_tipo_ejecucion.codigo not in ['R','T']:
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = factura.siif_codigo_sir.codigo
        else:
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = ''
        etree.SubElement(e_movimiento_presup, 'partidas_mon_ext').text = 'N' if llaves_presupuestales[0].mon == '0' else 'S'
        #Exceptuado SICE no se envian algunos datos
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid).company_id
        exceptuado_sice = company.exceptuado_sice or False
        # Si esta en false, los controles se hacen como hasta ahora con el ODG
        if not exceptuado_sice:
            if factura.doc_type != 'obligacion_invoice':
                if factura.doc_type != '3en1_invoice' and factura.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice:
                    if factura.orden_compra_id and factura.orden_compra_id.pedido_compra_id and factura.orden_compra_id.pedido_compra_id.ampliacion:
                        etree.SubElement(e_movimiento_presup, 'ano_proc_compra').text = factura.orden_compra_id.doc_origen.nro_pedido_original_id.name[:4]
                    else:
                        etree.SubElement(e_movimiento_presup, 'ano_proc_compra').text = datetime.strptime(factura.orden_compra_id.pedido_compra_id.date_start, '%Y-%m-%d').strftime('%Y')
                else:
                    etree.SubElement(e_movimiento_presup, 'ano_proc_compra').text = ''

                if factura.orden_compra_id.pedido_compra_id.tipo_compra.idTipoCompra == 'CM':
                    etree.SubElement(e_movimiento_presup, 'inciso_proc_compra').text = factura.orden_compra_id.pedido_compra_id.inciso_proc_compra
                    etree.SubElement(e_movimiento_presup, 'unidad_ejec_proc_compra').text = factura.orden_compra_id.pedido_compra_id.unidad_ejec_proc_compra
                else:
                    etree.SubElement(e_movimiento_presup, 'inciso_proc_compra').text= estructura.linea_proy_inciso if factura.doc_type != '3en1_invoice' and factura.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
                    etree.SubElement(e_movimiento_presup, 'unidad_ejec_proc_compra').text= estructura.linea_ue if factura.doc_type != '3en1_invoice' and factura.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
                etree.SubElement(e_movimiento_presup, 'tipo_proc_compra').text= factura.orden_compra_id.pedido_compra_id.tipo_compra.idTipoCompra if factura.doc_type != '3en1_invoice' and factura.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
                if factura.doc_type != '3en1_invoice' and factura.orden_compra_id and factura.orden_compra_id.pedido_compra_id and factura.orden_compra_id.pedido_compra_id.tipo_compra.idTipoCompra == 'CE' and factura.orden_compra_id.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice:
                    etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text= 'COM'
                else:
                    etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text= factura.orden_compra_id.pedido_compra_id.sub_tipo_compra.idSubtipoCompra if factura.doc_type != '3en1_invoice' and factura.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
                etree.SubElement(e_movimiento_presup, 'nro_proc_compra').text = factura.orden_compra_id.pedido_compra_id.name.split('-')[3] if factura.doc_type != '3en1_invoice' and factura.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
                etree.SubElement(e_movimiento_presup, 'nro_amp_proc_compra').text= str(factura.orden_compra_id.pedido_compra_id.nro_ampliacion) if factura.doc_type != '3en1_invoice' and factura.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''

        etree.SubElement(e_movimiento_presup, 'resumen').text = factura.siif_descripcion or '' if not es_modif else motivo
        etree.SubElement(e_movimiento_presup, 'nro_doc_fondo_rotatorio').text = factura.siif_nro_fondo_rot.name or ''
        etree.SubElement(e_movimiento_presup, 'inciso_doc_optgn').text = factura.inciso_doc_optgn or '' if factura.siif_tipo_ejecucion.codigo == 'T' else ''
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_doc_optgn').text = factura.unidad_ejec_doc_optgn or '' if factura.siif_tipo_ejecucion.codigo == 'T' else ''
        etree.SubElement(e_movimiento_presup, 'nro_doc_optgn').text = factura.nro_doc_optgn or '' if factura.siif_tipo_ejecucion.codigo == 'T' else ''
        etree.SubElement(e_movimiento_presup, 'ano_doc_respaldo').text = factura.ano_doc_respaldo or '' if factura.siif_tipo_ejecucion.codigo == 'T' else ''

        if not es_modif and factura.doc_type == '3en1_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = ''
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = ''
        elif factura.doc_type == 'obligacion_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(factura.compromiso_id.nro_compromiso)
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(factura.afectacion_id.nro_afectacion)
        else:
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(factura.compromiso_proveedor_id.nro_compromiso)
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(factura.compromiso_proveedor_id.apg_id.nro_afectacion_siif)
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(factura.nro_obligacion) if es_modif or tipo_modificacion == 'N' else ''
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')

        #TODO: ver es_inciso
        if factura.beneficiario_siif_id.es_inciso_default:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text= 'T'
            inciso = company and int(company.inciso) #TODO: Ver si se saca de algun lado o es fijo
            # u_e = company and int(company.u_e) #TODO: Ver si se saca de algun lado o es fijo
            if factura.unidad_ejecutora_id.codigo:
                u_e = factura.unidad_ejecutora_id.codigo
            else:
                u_e = int(factura.operating_unit_id.unidad_ejecutora)

            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text= '%s%s' % (str(inciso).zfill(2),str(u_e).zfill(3))
            if factura.res_partner_bank_id:
                if not factura.res_partner_bank_id.bank_bic:
                    raise osv.except_osv(('Error'),
                                     (u'Debe especificar el código de la cuenta bancaria.'))
                etree.SubElement(e_movimiento_presup, 'banco_cta_benef').text = factura.res_partner_bank_id.bank_bic
                etree.SubElement(e_movimiento_presup, 'agencia_cta_benef').text = factura.res_partner_bank_id.agencia
                etree.SubElement(e_movimiento_presup, 'nro_cta_benef').text = factura.res_partner_bank_id.acc_number.replace('-','').replace(' ','') # MVARELA se manda como viene - .ljust(14,'0')
                etree.SubElement(e_movimiento_presup, 'tipo_cta_benef').text = 'A' if factura.res_partner_bank_id.state == 'caja de ahorros' else 'C'
                etree.SubElement(e_movimiento_presup, 'moneda_cta_benef').text = '0' if not factura.res_partner_bank_id.currency_id else '1'
            else:
                raise osv.except_osv(('Error'),
                                     (u'No se especificó la cuenta bancaria.'))
        elif factura.beneficiario_siif_id.es_inciso:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text= factura.beneficiario_siif_id.tipo_doc_rupe[0] if factura.beneficiario_siif_id.tipo_doc_rupe else ''
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text=factura.beneficiario_siif_id.nro_doc_rupe
            if factura.res_partner_bank_id:
                if not factura.res_partner_bank_id.bank_bic:
                    raise osv.except_osv(('Error'),
                                         (u'Debe especificar el código de la cuenta bancaria.'))
                etree.SubElement(e_movimiento_presup, 'banco_cta_benef').text = factura.res_partner_bank_id.bank_bic
                etree.SubElement(e_movimiento_presup, 'agencia_cta_benef').text = factura.res_partner_bank_id.agencia
                etree.SubElement(e_movimiento_presup,
                                 'nro_cta_benef').text = factura.res_partner_bank_id.acc_number.replace('-','').replace(' ','')  # MVARELA se manda como viene - .ljust(14,'0')
                etree.SubElement(e_movimiento_presup,
                                 'tipo_cta_benef').text = 'A' if factura.res_partner_bank_id.state == 'caja de ahorros' else 'C'
                etree.SubElement(e_movimiento_presup,
                                 'moneda_cta_benef').text = '0' if not factura.res_partner_bank_id.currency_id else '1'
            else:
                raise osv.except_osv(('Error'),
                                     (u'No se especificó la cuenta bancaria.'))
        else:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text= factura.beneficiario_siif_id.tipo_doc_rupe[0] if factura.beneficiario_siif_id.tipo_doc_rupe else ''
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text=factura.beneficiario_siif_id.nro_doc_rupe
            if factura.rupe_cuenta_bancaria_id:
                etree.SubElement(e_movimiento_presup, 'banco_cta_benef').text = factura.rupe_cuenta_bancaria_id.codigo_banco
                etree.SubElement(e_movimiento_presup, 'agencia_cta_benef').text = factura.rupe_cuenta_bancaria_id.codigo_sucursal
                #MVARELA nros de cuentas dependen del banco si hay que completarlas o mandarlas como estan
                #Si es "1": BROU, relleno hasta 14 con 0s a la derecha
                if factura.rupe_cuenta_bancaria_id.codigo_banco == '1':
                    etree.SubElement(e_movimiento_presup, 'nro_cta_benef').text = factura.rupe_cuenta_bancaria_id.cnt_nro_cuenta.replace('-','').replace(' ','').ljust(14,'0')
                #Sino la mando como va
                else:
                    etree.SubElement(e_movimiento_presup, 'nro_cta_benef').text = factura.rupe_cuenta_bancaria_id.cnt_nro_cuenta.replace('-','').replace(' ','')
                etree.SubElement(e_movimiento_presup, 'tipo_cta_benef').text = factura.rupe_cuenta_bancaria_id.codigo_tipo_cuenta[1]
                etree.SubElement(e_movimiento_presup, 'moneda_cta_benef').text = '0' if factura.rupe_cuenta_bancaria_id.codigo_moneda == 'UYU' else '1'

            else:
                raise osv.except_osv(('Error'),
                                     (u'No se especificó la cuenta bancaria.'))

        etree.SubElement(e_movimiento_presup, 'monto_compromiso')
        # Antes estaba asi
        # Si es fondo rotatorio, liquido_pagable y monto_obligacion
        if factura.siif_tipo_ejecucion.codigo == 'P':
            #calcular el total pagado
            # SI Factura en MONEDA EXTRANJERA - USD..
            if factura.currency_id.id != factura.company_id.currency_id.id:
                total_reponer = factura.total_reponer or 0.0
                #TODO, Se asume que si se obliga una factura y es fondo rotatorio, debe estar en estado Pagado Total (por eso no se valida)
                etree.SubElement(e_movimiento_presup, 'monto_obligacion').text = str(int(round(total_reponer,0))) if not es_modif else _monto
                etree.SubElement(e_movimiento_presup, 'liquido_pagable').text = str(int(round(total_reponer,0))) if not es_modif else _monto
                etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text= ''
            else:
                # En pesos UYU
                etree.SubElement(e_movimiento_presup, 'monto_obligacion').text = str(int(round(factura.total_nominal,0))) if not es_modif else _monto
                etree.SubElement(e_movimiento_presup, 'liquido_pagable').text = str(int(round(factura.total_nominal,0))) if not es_modif else _monto
                etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text= str(int(round(factura.amount_total))) if factura.currency_id.name <>'UYU' else ''
            # No informar retenciones para Fondo Rotatorio P
            etree.SubElement(e_movimiento_presup, 'total_retenciones').text='0'
            #ENVIAR SIEMPRE COMO SI FUERA PESOS SI ES Fondo Rotatorio
            etree.SubElement(e_movimiento_presup, 'moneda').text='0' #SIEMPRE ENVIA COMO PESOS
        else:
            # NO es fondo rotatorio, liquido_pagable y monto_obligacion
            etree.SubElement(e_movimiento_presup, 'monto_obligacion').text = str(int(round(factura.total_nominal,0))) if not es_modif else _monto
            etree.SubElement(e_movimiento_presup, 'total_retenciones').text= str(int(round(factura.amount_ttal_ret_pesos,0))) if not es_modif else '0'
            etree.SubElement(e_movimiento_presup, 'liquido_pagable').text = _monto #pasando monto siempre 16/03
            etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text= str(int(round(factura.amount_total))) if factura.currency_id.name <>'UYU' else ''
            # etree.SubElement(e_movimiento_presup, 'moneda').text= '1' if factura.currency_id.name =='USD' else '0' #'1' - Dolar USA Billete en SIIF - 36
            etree.SubElement(e_movimiento_presup, 'moneda').text = str(factura.currency_id.codigo_siif)

        etree.SubElement(e_movimiento_presup, 'fecha_recepcion').text=datetime.strptime(factura.date_invoice, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento').text=datetime.strptime(factura.date_due, '%Y-%m-%d').strftime('%Y%m%d') if factura.date_due else datetime.strptime(factura.date_invoice, '%Y-%m-%d').strftime('%Y%m%d')
        tipo_cambio = ''
        if factura.currency_id.name <>'UYU' and factura.siif_tipo_ejecucion.codigo != 'P':
            monto_cambio = int(round(factura.tc_presupuesto * 10000))
            tipo_cambio = str(monto_cambio)
        etree.SubElement(e_movimiento_presup, 'tipo_cambio').text= tipo_cambio
        etree.SubElement(e_movimiento_presup, 'anticipo').text = 'N'
        etree.SubElement(e_movimiento_presup, 'nro_doc_transf_monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers_mon_ext')

        etree.SubElement(e_movimiento_presup, 'sec_compromiso')

        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in llaves_presupuestales:
            if llave.importe:
                estructura = estructura_obj.obtener_estructura(cr, uid, factura.fiscalyear_siif_id.id, factura.inciso_siif_id.inciso,
                                                                           factura.ue_siif_id.ue,
                                                                           llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                                           llave.fin, llave.odg, llave.auxiliar)
                e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
                if estructura:
                    etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                    etree.SubElement(e_detalle_siif, 'tipo_registracion').text = _tipo_registracion
                    etree.SubElement(e_detalle_siif, 'programa').text = estructura.linea_programa
                    etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text='PART_OBL_ORIG_Y_MODIF_GRP'
                    etree.SubElement(e_detalle_siif, 'proyecto').text = estructura.linea_proyecto
                    etree.SubElement(e_detalle_siif, 'objeto_gasto').text = estructura.linea_og
                    etree.SubElement(e_detalle_siif, 'auxiliar').text = estructura.linea_aux
                    etree.SubElement(e_detalle_siif, 'financiamiento').text = estructura.linea_ff
                    etree.SubElement(e_detalle_siif, 'moneda').text = estructura.linea_moneda
                    etree.SubElement(e_detalle_siif, 'tipo_credito').text = estructura.linea_tc
                if es_modif:
                    if tipo_modificacion == 'N':
                        monto = str(int(-llave.importe))
                    else:
                        monto = _monto
                else:
                    monto = str(int(llave.importe))
                etree.SubElement(e_detalle_siif, 'importe').text = monto

        e_retencion = etree.SubElement(e_movimiento_presup, 'Retenciones')
        for retencion in retenciones:
            if retencion['monto'] != 0:
                e_retencion_siif = etree.SubElement(e_retencion, 'RetencionSIIF')
                etree.SubElement(e_retencion_siif, 'tipo_registro').text = '03'
                etree.SubElement(e_retencion_siif, 'tipo_registracion').text = _tipo_registracion
                etree.SubElement(e_retencion_siif, 'grupo_acreedor').text = retencion['grupo'] and str(retencion['grupo']) or ''
                etree.SubElement(e_retencion_siif, 'acreedor').text = retencion['acreedor'] and str(retencion['acreedor']) or ''
                etree.SubElement(e_retencion_siif, 'importe').text = str(int(round(retencion['monto'],0)))

        e_ces_o_emb = etree.SubElement(e_movimiento_presup, 'CesionesOEmbargos')
        if factura.cesion_embargo and factura.cesion_ids:
            for cesion in factura.cesion_ids:
                e_ces_o_emb_siif = etree.SubElement(e_ces_o_emb, 'CesionOEmbargoSIIF')
                etree.SubElement(e_ces_o_emb_siif, 'tipo_registro').text = '04'
                etree.SubElement(e_ces_o_emb_siif, 'tipo_registracion').text = _tipo_registracion
                if cesion.cesion_partner_id.es_inciso_default:
                    etree.SubElement(e_ces_o_emb_siif, 'clase_doc_benef').text = 'T'
                    inciso = company and int(company.inciso)
                    u_e = cesion.unidad_ejecutora_id.codigo
                    etree.SubElement(e_ces_o_emb_siif, 'num_doc_benef').text = '%s%s' % (str(inciso).zfill(2), str(u_e).zfill(3))
                else:
                    etree.SubElement(e_ces_o_emb_siif, 'clase_doc_benef').text = cesion.cesion_partner_id.tipo_doc_rupe[0] if cesion.cesion_partner_id.tipo_doc_rupe else ''
                    etree.SubElement(e_ces_o_emb_siif, 'num_doc_benef').text = cesion.cesion_partner_id.nro_doc_rupe
                if cesion.cesion_partner_id.es_inciso_default or cesion.cesion_partner_id.es_inciso:
                    if cesion.cesion_res_partner_bank_id:
                        if not cesion.cesion_res_partner_bank_id.bank_bic:
                            raise osv.except_osv(('Error'), (u'Debe especificar el código de la cuenta bancaria.'))
                        etree.SubElement(e_ces_o_emb_siif, 'banco_cta_benef').text = cesion.cesion_res_partner_bank_id.bank_bic
                        etree.SubElement(e_ces_o_emb_siif, 'agencia_cta_benef').text = cesion.cesion_res_partner_bank_id.agencia
                        etree.SubElement(e_ces_o_emb_siif, 'nro_cta_benef').text = cesion.cesion_res_partner_bank_id.acc_number.replace('-','').replace(' ','')
                        etree.SubElement(e_ces_o_emb_siif, 'tipo_cta_benef').text = 'A' if cesion.cesion_res_partner_bank_id.state == 'caja de ahorros' else 'C'
                        etree.SubElement(e_ces_o_emb_siif, 'moneda_cta_benef').text = '0' if not cesion.cesion_res_partner_bank_id.currency_id else '1'
                    else:
                        raise osv.except_osv(('Error'), (u'No se especificó la cuenta bancaria.'))
                else:
                    if cesion.cesion_rupe_cta_bnc_id:
                        etree.SubElement(e_ces_o_emb_siif, 'banco_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.codigo_banco
                        etree.SubElement(e_ces_o_emb_siif, 'agencia_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.codigo_sucursal
                        # MVARELA nros de cuentas dependen del banco si hay que completarlas o mandarlas como estan
                        # Si es "1": BROU, relleno hasta 14 con 0s a la derecha
                        if cesion.cesion_rupe_cta_bnc_id.codigo_banco == '1':
                            etree.SubElement(e_ces_o_emb_siif, 'nro_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.cnt_nro_cuenta.replace('-','').replace(' ','').ljust(14, '0')
                        # Sino la mando como va
                        else:
                            etree.SubElement(e_ces_o_emb_siif, 'nro_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.cnt_nro_cuenta.replace('-','').replace(' ','')
                        etree.SubElement(e_ces_o_emb_siif, 'tipo_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.codigo_tipo_cuenta[1]
                        etree.SubElement(e_ces_o_emb_siif, 'moneda_cta_benef').text = '0' if cesion.cesion_rupe_cta_bnc_id.codigo_moneda == 'UYU' else '1'
                    else:
                        raise osv.except_osv(('Error'), (u'No se especificó la cuenta bancaria.'))
                etree.SubElement(e_ces_o_emb_siif, 'clase_doc_cedente').text = factura.beneficiario_siif_id.tipo_doc_rupe
                etree.SubElement(e_ces_o_emb_siif, 'num_doc_cedente').text = factura.beneficiario_siif_id.nro_doc_rupe
                etree.SubElement(e_ces_o_emb_siif, 'cesion_o_embargo').text = cesion.tipo_ces_emb
                etree.SubElement(e_ces_o_emb_siif, 'importe').text = str(cesion.monto_cedido_embargado)

        e_impuestos = etree.SubElement(e_movimiento_presup, 'Impuestos')
        # Probar sin retenciones
        if not factura.siif_tipo_ejecucion.codigo == 'P':
            for retencion in retenciones:
                if not retencion['es_manual']:
                    e_impuesto_siif = etree.SubElement(e_impuestos, 'ImpuestoSIIF')
                    etree.SubElement(e_impuesto_siif, 'tipo_registro').text = '05'
                    etree.SubElement(e_impuesto_siif, 'tipo_registracion').text = _tipo_registracion
                    etree.SubElement(e_impuesto_siif, 'tipo_impuesto').text = str(retencion['acreedor'])
                    if 'base_impuesto' in retencion:
                        etree.SubElement(e_impuesto_siif, 'monto_calculo').text = str(int(round(retencion['base_impuesto']))) if tipo_modificacion != 'N' else str(-int(round(retencion['base_impuesto'])))
                    if 'base_impuesto_mont_ext' in retencion:
                        etree.SubElement(e_impuesto_siif, 'monto_calculo_mon_ext').text = str(int(round(retencion['base_impuesto_mont_ext']))) if tipo_modificacion != 'N' else str(-int(round(retencion['base_impuesto_mont_ext'])))

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2

    def gen_xml_borrado_obligacion(self, cr, uid, factura, nro_carga, tipo_doc_grp, nro_modif_grp, nro_obl_sist_aux=False):

        if factura.doc_type == '3en1_invoice':
            _tipo_registracion= '24'
        else:
            _tipo_registracion= '23'

        _tipo_registro = '01'

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')


        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = factura.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = factura.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = factura.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp
        if factura.doc_type == 'obligacion_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = factura.afectacion_id.nro_afect_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = factura.compromiso_id.nro_comp_sist_aux
        elif factura.doc_type == '3en1_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_obl_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_obl_sist_aux
        else:
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text =  factura.compromiso_proveedor_id and factura.compromiso_proveedor_id.apg_id and factura.compromiso_proveedor_id.apg_id.nro_afect_sist_aux or ''
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text =  factura.compromiso_proveedor_id and factura.compromiso_proveedor_id.nro_comp_sist_aux or ''
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text= str(factura.nro_afectacion)
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = factura.siif_financiamiento.codigo
        etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(factura.nro_compromiso)
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(factura.nro_obligacion)
        etree.SubElement(e_movimiento_presup, 'sec_obligacion').text = factura.siif_sec_obligacion or ''

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2

    def gen_xml_borrado_modif_obligacion(self, cr, uid, factura, factura_original, nro_carga, tipo_doc_grp, nro_modif_grp, nro_obl_sist_aux=False):

        if factura_original.doc_type == '3en1_invoice':
            _tipo_registracion = '24'
        else:
            _tipo_registracion = '23'

        _tipo_registro = '01'

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = factura.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = factura.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = factura.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp
        if factura_original.doc_type == 'obligacion_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = factura_original.afectacion_id.nro_afect_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = factura_original.compromiso_id.nro_comp_sist_aux
        elif factura_original.doc_type == '3en1_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_obl_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_obl_sist_aux
        else:
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = factura_original.compromiso_proveedor_id and factura_original.compromiso_proveedor_id.apg_id and factura_original.compromiso_proveedor_id.apg_id.nro_afect_sist_aux or ''
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = factura_original.compromiso_proveedor_id and factura_original.compromiso_proveedor_id.nro_comp_sist_aux or ''
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(factura_original.nro_afectacion)
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = factura.siif_financiamiento.codigo
        etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(factura_original.nro_compromiso)
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(factura_original.nro_obligacion)
        etree.SubElement(e_movimiento_presup, 'sec_obligacion').text = factura.siif_sec_obligacion or ''

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2

    def gen_xml_borrado_correccion_obligacion(self, cr, uid, correccion, factura_original, nro_carga, tipo_doc_grp, nro_modif_grp, nro_obl_sist_aux=False):

        if factura_original.doc_type == '3en1_invoice':
            _tipo_registracion = '24'
        else:
            _tipo_registracion = '23'

        _tipo_registro = '01'

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = correccion.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = correccion.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = correccion.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp
        if factura_original.doc_type == 'obligacion_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = factura_original.afectacion_id.nro_afect_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = factura_original.compromiso_id.nro_comp_sist_aux
        elif factura_original.doc_type == '3en1_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_obl_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_obl_sist_aux
        else:
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = factura_original.compromiso_proveedor_id and factura_original.compromiso_proveedor_id.apg_id and factura_original.compromiso_proveedor_id.apg_id.nro_afect_sist_aux or ''
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = factura_original.compromiso_proveedor_id and factura_original.compromiso_proveedor_id.nro_comp_sist_aux or ''
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(factura_original.nro_afectacion)
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = correccion.invoice_id.siif_financiamiento.codigo
        etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(factura_original.nro_compromiso)
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(factura_original.nro_obligacion)
        etree.SubElement(e_movimiento_presup, 'sec_obligacion').text = correccion.siif_sec_obligacion or ''

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2

    def gen_xml_estado_solicitud(self, anio_fiscal, inciso, unidad_ejecutora, nro_carga):
        root = etree.Element('ConsultaWS')
        e_movimiento = etree.SubElement(root, 'movimiento')
        etree.SubElement(e_movimiento, 'nro_carga').text = nro_carga
        etree.SubElement(e_movimiento, 'ano_fiscal').text = anio_fiscal.name
        etree.SubElement(e_movimiento, 'inciso').text = inciso
        etree.SubElement(e_movimiento, 'unidad_ejecutora').text = unidad_ejecutora
        xml = etree.tostring(root, pretty_print=False, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2


    def gen_xml_obligacion_3en1_rc(self, cr, uid, regularizacion_clearing, llaves_presupuestales, importe, nro_carga, tipo_doc_grp, nro_modif_grp, tipo_modificacion, es_modif=False, motivo=False, enviar_datos_sice=True, nro_obl_sist_aux=False):

        _tipo_registro = '01'
        _tipo_registracion= '04' if es_modif is False else '14'
        _concepto_gasto = regularizacion_clearing.siif_concepto_gasto.concepto
        _monto=str(int(round(importe,0)))

        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid).company_id

        estructura_obj = self.pool.get('presupuesto.estructura')

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        estructura = estructura_obj.obtener_estructura(cr, uid, regularizacion_clearing.fiscalyear_id.id,
                                                       regularizacion_clearing.inciso_siif_id.inciso,
                                                       regularizacion_clearing.ue_siif_id.ue,
                                                       llaves_presupuestales[0].programa,
                                                       llaves_presupuestales[0].proyecto,
                                                       llaves_presupuestales[0].mon,
                                                       llaves_presupuestales[0].tc,
                                                       llaves_presupuestales[0].fin,
                                                       llaves_presupuestales[0].odg,
                                                       llaves_presupuestales[0].auxiliar)

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'desc_tipo_mov').text = 'OBL_ORIG_Y_MODIF_GRP'
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = regularizacion_clearing.fiscalyear_id.name

        etree.SubElement(e_movimiento_presup, 'inciso').text = regularizacion_clearing.inciso_siif_id.inciso or ''
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = regularizacion_clearing.ue_siif_id.ue or ''

        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp

        # En 3en1 nro_afect_sist_aux, nro_comp_sist_aux y nro_obl_sist_aux son nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = nro_obl_sist_aux

        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)

        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(regularizacion_clearing.nro_afectacion) if es_modif else ''
        etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(regularizacion_clearing.nro_compromiso) if es_modif else ''
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(regularizacion_clearing.nro_obligacion) if es_modif or tipo_modificacion == 'N' else ''
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = tipo_modificacion
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')

        etree.SubElement(e_movimiento_presup, 'monto_obligacion').text = str(int(round(regularizacion_clearing.total_nominal,0)))
        etree.SubElement(e_movimiento_presup, 'total_retenciones').text = str(int(round(regularizacion_clearing.amount_ttal_ret_pesos,0)))
        etree.SubElement(e_movimiento_presup, 'liquido_pagable').text = str(int(round(regularizacion_clearing.amount_ttal_liq_pesos,0)))

        #Regularizacion Clearing siempre es Moneda Nacional
        etree.SubElement(e_movimiento_presup, 'partidas_mon_ext').text = 'N'
        etree.SubElement(e_movimiento_presup, 'monto_mon_ext')

        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = regularizacion_clearing.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'T'
        etree.SubElement(e_movimiento_presup, 'tipo_documento').text = regularizacion_clearing.siif_tipo_documento.codigo or ''

        etree.SubElement(e_movimiento_presup, 'numero_documento')
        etree.SubElement(e_movimiento_presup, 'ano_doc_respaldo')
        etree.SubElement(e_movimiento_presup, 'fecha_doc_respaldo')
        etree.SubElement(e_movimiento_presup, 'serie_documento')
        etree.SubElement(e_movimiento_presup, 'secuencia_documento')
        etree.SubElement(e_movimiento_presup, 'fecha_recepcion').text = datetime.strptime(regularizacion_clearing.date, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento').text = datetime.strptime(regularizacion_clearing.fecha_vencimiento, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text = regularizacion_clearing.beneficiario_siif_id.tipo_doc_rupe[0] if regularizacion_clearing.beneficiario_siif_id.tipo_doc_rupe else ''

        etree.SubElement(e_movimiento_presup, 'num_doc_benef').text = regularizacion_clearing.beneficiario_siif_id.nro_doc_rupe
        if regularizacion_clearing.rupe_cuenta_bancaria_id:
            etree.SubElement(e_movimiento_presup, 'banco_cta_benef').text = regularizacion_clearing.rupe_cuenta_bancaria_id.codigo_banco
            etree.SubElement(e_movimiento_presup,'agencia_cta_benef').text = regularizacion_clearing.rupe_cuenta_bancaria_id.codigo_sucursal
            # MVARELA nros de cuentas dependen del banco si hay que completarlas o mandarlas como estan
            # Si es "1": BROU, relleno hasta 14 con 0s a la derecha
            if regularizacion_clearing.rupe_cuenta_bancaria_id.codigo_banco == '1':
                etree.SubElement(e_movimiento_presup,'nro_cta_benef').text = regularizacion_clearing.rupe_cuenta_bancaria_id.cnt_nro_cuenta.replace('-','').replace(' ','').ljust(14, '0')
            # Sino la mando como va
            else:
                etree.SubElement(e_movimiento_presup,'nro_cta_benef').text = regularizacion_clearing.rupe_cuenta_bancaria_id.cnt_nro_cuenta.replace('-','').replace(' ','')
            etree.SubElement(e_movimiento_presup, 'tipo_cta_benef').text = regularizacion_clearing.rupe_cuenta_bancaria_id.codigo_tipo_cuenta[1]
            etree.SubElement(e_movimiento_presup,'moneda_cta_benef').text = '0' if regularizacion_clearing.rupe_cuenta_bancaria_id.codigo_moneda == 'UYU' else '1'
        else:
            raise osv.except_osv(('Error'),
                                 (u'No se especificó la cuenta bancaria.'))

        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = _concepto_gasto

        etree.SubElement(e_movimiento_presup, 'financiamiento').text = regularizacion_clearing.siif_financiamiento.codigo
        # etree.SubElement(e_movimiento_presup, 'codigo_sir').text = ''

        # Se envian vacios los siguientes datos ya que Regularizacion Clearing es Exceptuado SICE = True
        etree.SubElement(e_movimiento_presup, 'ano_proc_compra')
        etree.SubElement(e_movimiento_presup, 'inciso_proc_compra')
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_proc_compra')
        etree.SubElement(e_movimiento_presup, 'tipo_proc_compra')
        etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra')
        etree.SubElement(e_movimiento_presup, 'nro_proc_compra')
        etree.SubElement(e_movimiento_presup, 'nro_amp_proc_compra')

        etree.SubElement(e_movimiento_presup, 'tipo_cambio')
        etree.SubElement(e_movimiento_presup, 'anticipo').text = 'N'
        etree.SubElement(e_movimiento_presup, 'moneda').text = '0'

        etree.SubElement(e_movimiento_presup, 'resumen').text = regularizacion_clearing.siif_descripcion or '' if not es_modif else motivo
        etree.SubElement(e_movimiento_presup, 'nro_doc_fondo_rotatorio')
        etree.SubElement(e_movimiento_presup, 'inciso_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transferencia')

        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in llaves_presupuestales:
            if llave.importe:
                estructura = estructura_obj.obtener_estructura(cr, uid, regularizacion_clearing.fiscalyear_id.id, regularizacion_clearing.inciso_siif_id.inciso,
                                                               regularizacion_clearing.ue_siif_id.ue,
                                                                           llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                                           llave.fin, llave.odg, llave.auxiliar)
                e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
                if estructura:
                    etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                    etree.SubElement(e_detalle_siif, 'tipo_registracion').text = _tipo_registracion
                    etree.SubElement(e_detalle_siif, 'programa').text = estructura.linea_programa
                    etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text='PART_OBL_ORIG_Y_MODIF_GRP'
                    etree.SubElement(e_detalle_siif, 'proyecto').text = estructura.linea_proyecto
                    etree.SubElement(e_detalle_siif, 'objeto_gasto').text = estructura.linea_og
                    etree.SubElement(e_detalle_siif, 'auxiliar').text = estructura.linea_aux
                    etree.SubElement(e_detalle_siif, 'financiamiento').text = estructura.linea_ff
                    etree.SubElement(e_detalle_siif, 'moneda').text = estructura.linea_moneda
                    etree.SubElement(e_detalle_siif, 'tipo_credito').text = estructura.linea_tc
                if es_modif:
                    if tipo_modificacion == 'N':
                        monto = str(int(-llave.importe))
                    else:
                        monto = _monto
                else:
                    monto = str(int(llave.importe))
                etree.SubElement(e_detalle_siif, 'importe').text = monto

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')

        return xml2


    def gen_xml_borrado_3en1_rc(self, cr, uid, regularizacion_clearing, nro_carga, tipo_doc_grp, nro_modif_grp,
                                    nro_obl_sist_aux=False):

        _tipo_registracion = '24'
        _tipo_registro = '01'

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = regularizacion_clearing.fiscalyear_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = regularizacion_clearing.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = regularizacion_clearing.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp
        etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)

        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(regularizacion_clearing.nro_afectacion)
        etree.SubElement(e_movimiento_presup,
                         'financiamiento').text = regularizacion_clearing.siif_financiamiento.codigo
        etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(regularizacion_clearing.nro_compromiso)
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(regularizacion_clearing.nro_obligacion)
        etree.SubElement(e_movimiento_presup, 'sec_obligacion').text = regularizacion_clearing.siif_sec_obligacion or ''

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2



    def gen_xml_obligacion_modif(self, cr, uid, factura, llaves_presupuestales, importe, nro_carga, tipo_doc_grp, nro_modif_grp, tipo_modificacion, es_modif=False, retenciones=False, motivo=False, enviar_datos_sice=True, nro_obl_sist_aux=False):

        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid).company_id
        inciso = company and int(company.inciso)    # TODO: Ver si se saca de algun lado o es fijo
        # u_e = company and int(company.u_e)          # TODO: Ver si se saca de algun lado o es fijo

        if factura.factura_original.unidad_ejecutora_id.codigo:
            u_e = factura.factura_original.unidad_ejecutora_id.codigo
        else:
            u_e = int(factura.factura_original.operating_unit_id.unidad_ejecutora)

        if factura.factura_original.doc_type == '3en1_invoice':
            _tipo_registracion= '14'
        else:
            _tipo_registracion = '13'

        _tipo_registro = '01'
        _concepto_gasto = factura.siif_concepto_gasto.concepto

        _monto=str(int(round(importe,0)))

        estructura_obj = self.pool.get('presupuesto.estructura')

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        estructura = estructura_obj.obtener_estructura(cr, uid, factura.fiscalyear_siif_id.id,
                                                       factura.inciso_siif_id.inciso,
                                                       factura.ue_siif_id.ue,
                                                       llaves_presupuestales[0].programa,
                                                       llaves_presupuestales[0].proyecto,
                                                       llaves_presupuestales[0].mon,
                                                       llaves_presupuestales[0].tc,
                                                       llaves_presupuestales[0].fin,
                                                       llaves_presupuestales[0].odg,
                                                       llaves_presupuestales[0].auxiliar)

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'desc_tipo_mov').text = 'OBL_ORIG_Y_MODIF_GRP' #TODO: si es '3en1_invoice' mandar otra descripcion
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = factura.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = factura.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = factura.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp

        if factura.factura_original.doc_type == 'obligacion_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = factura.factura_original.afectacion_id.nro_afect_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = factura.factura_original.compromiso_id.nro_comp_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(factura.factura_original.compromiso_id.nro_compromiso)
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(factura.factura_original.afectacion_id.nro_afectacion)

        elif factura.factura_original.doc_type == '3en1_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_obl_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_obl_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(factura.factura_original.nro_compromiso)
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(factura.factura_original.nro_afectacion)

        else:
            #'invoice' Enviar factura como 3en1
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text =  factura.factura_original.compromiso_proveedor_id and factura.factura_original.compromiso_proveedor_id.apg_id and factura.factura_original.compromiso_proveedor_id.apg_id.nro_afect_sist_aux or ''
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text =  factura.factura_original.compromiso_proveedor_id and factura.factura_original.compromiso_proveedor_id.nro_comp_sist_aux or ''
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(factura.factura_original.compromiso_proveedor_id.nro_compromiso)
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(factura.factura_original.compromiso_proveedor_id.apg_id.nro_afectacion_siif)

        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(factura.factura_original.nro_obligacion)
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = tipo_modificacion
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = factura.factura_original.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'T' if factura.factura_original.doc_type == '3en1_invoice' else 'S'
        etree.SubElement(e_movimiento_presup, 'fecha_recepcion').text=datetime.strptime(factura.date_invoice, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento').text=datetime.strptime(factura.date_due, '%Y-%m-%d').strftime('%Y%m%d') if factura.date_due else datetime.strptime(factura.date_invoice, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = _concepto_gasto
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = factura.factura_original.siif_financiamiento.codigo

        if factura.currency_id.name <>'UYU' and factura.siif_tipo_ejecucion.codigo != 'P':
            monto_cambio = int(round(factura.tc_presupuesto * 10000))
            tipo_cambio = str(monto_cambio)
            etree.SubElement(e_movimiento_presup, 'tipo_cambio').text= tipo_cambio
        else:
            etree.SubElement(e_movimiento_presup, 'tipo_cambio')

        etree.SubElement(e_movimiento_presup, 'anticipo').text = 'N'
        # etree.SubElement(e_movimiento_presup, 'moneda').text= '1' if factura.currency_id.name =='USD' else '0' #'1' - Dolar USA Billete en SIIF - 36
        etree.SubElement(e_movimiento_presup, 'moneda').text= str(factura.currency_id.codigo_siif)
        etree.SubElement(e_movimiento_presup, 'resumen').text = factura.siif_descripcion

        #TODO: ver es_inciso
        if factura.factura_original.beneficiario_siif_id.es_inciso_default:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text= 'T'
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text= '%s%s' % (str(inciso).zfill(2),str(u_e).zfill(3))
        else:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text= factura.beneficiario_siif_id.tipo_doc_rupe[0] if factura.beneficiario_siif_id.tipo_doc_rupe else ''
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text=factura.beneficiario_siif_id.nro_doc_rupe

        # NO es fondo rotatorio, liquido_pagable y monto_obligacion, verifico Reduccion
        if tipo_modificacion in ('R','D'):
            monto_obligacion = str(int(round(-factura.total_nominal,0)))
            liquido_pagable = str(int(round(-factura.amount_ttal_liq_pesos,0)))
            total_retenciones = str(int(round(-factura.amount_ttal_ret_pesos,0)))
        else:
            monto_obligacion = str(int(round(factura.total_nominal,0)))
            liquido_pagable = str(int(round(factura.amount_ttal_liq_pesos,0)))
            total_retenciones = str(int(round(factura.amount_ttal_ret_pesos, 0)))

        etree.SubElement(e_movimiento_presup, 'monto_obligacion').text = monto_obligacion
        etree.SubElement(e_movimiento_presup, 'liquido_pagable').text = liquido_pagable
        etree.SubElement(e_movimiento_presup, 'total_retenciones').text= total_retenciones

        if factura.currency_id.name <> 'UYU':
            if tipo_modificacion in ('R','D'):
                etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = str(int(round(-factura.amount_total)))
            else:
                etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = str(int(round(factura.amount_total)))
        else:
            etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = ''

        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in llaves_presupuestales:
            if llave.importe:
                estructura = estructura_obj.obtener_estructura(cr, uid, factura.fiscalyear_siif_id.id, factura.inciso_siif_id.inciso,
                                                                           factura.ue_siif_id.ue,
                                                                           llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                                           llave.fin, llave.odg, llave.auxiliar)
                e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
                if estructura:
                    etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                    etree.SubElement(e_detalle_siif, 'tipo_registracion').text = _tipo_registracion
                    etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text='PART_OBL_ORIG_Y_MODIF_GRP'
                    etree.SubElement(e_detalle_siif, 'objeto_gasto').text = estructura.linea_og
                    etree.SubElement(e_detalle_siif, 'auxiliar').text = estructura.linea_aux
                    etree.SubElement(e_detalle_siif, 'financiamiento').text = estructura.linea_ff
                    etree.SubElement(e_detalle_siif, 'programa').text = estructura.linea_programa
                    etree.SubElement(e_detalle_siif, 'proyecto').text = estructura.linea_proyecto
                    etree.SubElement(e_detalle_siif, 'moneda').text = estructura.linea_moneda
                    etree.SubElement(e_detalle_siif, 'tipo_credito').text = estructura.linea_tc
                if tipo_modificacion in ('R','D'):
                    importe = str(int(-llave.importe))
                else:
                    importe = str(int(llave.importe))
                etree.SubElement(e_detalle_siif, 'importe').text = importe

        e_retencion = etree.SubElement(e_movimiento_presup, 'Retenciones')
        for retencion in retenciones:
            if retencion['monto'] != 0:
                e_retencion_siif = etree.SubElement(e_retencion, 'RetencionSIIF')
                etree.SubElement(e_retencion_siif, 'tipo_registro').text = '03'
                etree.SubElement(e_retencion_siif, 'tipo_registracion').text = _tipo_registracion
                etree.SubElement(e_retencion_siif, 'grupo_acreedor').text = retencion['grupo'] and str(retencion['grupo']) or ''
                etree.SubElement(e_retencion_siif, 'acreedor').text = retencion['acreedor'] and str(retencion['acreedor']) or ''
                if tipo_modificacion in ('R', 'D'):
                    etree.SubElement(e_retencion_siif, 'importe').text = str(int(round(-retencion['monto'], 0)))
                else:
                    etree.SubElement(e_retencion_siif, 'importe').text = str(int(round(retencion['monto'],0)))

        e_ces_o_emb = etree.SubElement(e_movimiento_presup, 'CesionesOEmbargos')
        if factura.cesion_embargo and factura.cesion_ids:
            for cesion in factura.cesion_ids:
                e_ces_o_emb_siif = etree.SubElement(e_ces_o_emb, 'CesionOEmbargoSIIF')
                etree.SubElement(e_ces_o_emb_siif, 'tipo_registro').text = '04'
                etree.SubElement(e_ces_o_emb_siif, 'tipo_registracion').text = _tipo_registracion
                if cesion.cesion_partner_id.es_inciso_default:
                    etree.SubElement(e_ces_o_emb_siif, 'clase_doc_benef').text = 'T'
                    inciso = company and int(company.inciso)
                    u_e = cesion.unidad_ejecutora_id.codigo
                    etree.SubElement(e_ces_o_emb_siif, 'num_doc_benef').text = '%s%s' % (str(inciso).zfill(2), str(u_e).zfill(3))
                else:
                    etree.SubElement(e_ces_o_emb_siif, 'clase_doc_benef').text = cesion.cesion_partner_id.tipo_doc_rupe[0] if cesion.cesion_partner_id.tipo_doc_rupe else ''
                    etree.SubElement(e_ces_o_emb_siif, 'num_doc_benef').text = cesion.cesion_partner_id.nro_doc_rupe
                if cesion.cesion_partner_id.es_inciso_default or cesion.cesion_partner_id.es_inciso:
                    if cesion.cesion_res_partner_bank_id:
                        if not cesion.cesion_res_partner_bank_id.bank_bic:
                            raise osv.except_osv(('Error'), (u'Debe especificar el código de la cuenta bancaria.'))
                        etree.SubElement(e_ces_o_emb_siif, 'banco_cta_benef').text = cesion.cesion_res_partner_bank_id.bank_bic
                        etree.SubElement(e_ces_o_emb_siif, 'agencia_cta_benef').text = cesion.cesion_res_partner_bank_id.agencia
                        etree.SubElement(e_ces_o_emb_siif, 'nro_cta_benef').text = cesion.cesion_res_partner_bank_id.acc_number.replace('-','').replace(' ','')
                        etree.SubElement(e_ces_o_emb_siif, 'tipo_cta_benef').text = 'A' if cesion.cesion_res_partner_bank_id.state == 'caja de ahorros' else 'C'
                        etree.SubElement(e_ces_o_emb_siif, 'moneda_cta_benef').text = '0' if not cesion.cesion_res_partner_bank_id.currency_id else '1'
                    else:
                        raise osv.except_osv(('Error'), (u'No se especificó la cuenta bancaria.'))
                else:
                    if cesion.cesion_rupe_cta_bnc_id:
                        etree.SubElement(e_ces_o_emb_siif, 'banco_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.codigo_banco
                        etree.SubElement(e_ces_o_emb_siif, 'agencia_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.codigo_sucursal
                        # MVARELA nros de cuentas dependen del banco si hay que completarlas o mandarlas como estan
                        # Si es "1": BROU, relleno hasta 14 con 0s a la derecha
                        if cesion.cesion_rupe_cta_bnc_id.codigo_banco == '1':
                            etree.SubElement(e_ces_o_emb_siif, 'nro_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.cnt_nro_cuenta.replace('-','').replace(' ','').ljust(14, '0')
                        # Sino la mando como va
                        else:
                            etree.SubElement(e_ces_o_emb_siif, 'nro_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.cnt_nro_cuenta.replace('-','').replace(' ','')
                        etree.SubElement(e_ces_o_emb_siif, 'tipo_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.codigo_tipo_cuenta[1]
                        etree.SubElement(e_ces_o_emb_siif, 'moneda_cta_benef').text = '0' if cesion.cesion_rupe_cta_bnc_id.codigo_moneda == 'UYU' else '1'
                    else:
                        raise osv.except_osv(('Error'), (u'No se especificó la cuenta bancaria.'))
                etree.SubElement(e_ces_o_emb_siif, 'clase_doc_cedente').text = factura.beneficiario_siif_id.tipo_doc_rupe
                etree.SubElement(e_ces_o_emb_siif, 'num_doc_cedente').text = factura.beneficiario_siif_id.nro_doc_rupe
                etree.SubElement(e_ces_o_emb_siif, 'cesion_o_embargo').text = cesion.tipo_ces_emb
                if tipo_modificacion in ('R', 'D'):
                    etree.SubElement(e_ces_o_emb_siif, 'importe').text =  str(-cesion.monto_cedido_embargado)
                else:
                    etree.SubElement(e_ces_o_emb_siif, 'importe').text = str(cesion.monto_cedido_embargado)

        e_impuestos = etree.SubElement(e_movimiento_presup, 'Impuestos')
        # Probar sin retenciones
        if not factura.siif_tipo_ejecucion.codigo == 'P':
            for retencion in retenciones:
                if not retencion['es_manual']:
                    e_impuesto_siif = etree.SubElement(e_impuestos, 'ImpuestoSIIF')
                    etree.SubElement(e_impuesto_siif, 'tipo_registro').text = '05'
                    etree.SubElement(e_impuesto_siif, 'tipo_registracion').text = _tipo_registracion
                    etree.SubElement(e_impuesto_siif, 'tipo_impuesto').text = str(retencion['acreedor'])
                    if 'base_impuesto' in retencion:
                        etree.SubElement(e_impuesto_siif, 'monto_calculo').text = str(int(round(retencion['base_impuesto']))) if tipo_modificacion not in ('R', 'D') else str(-int(round(retencion['base_impuesto'])))
                    if 'base_impuesto_mont_ext' in retencion:
                        etree.SubElement(e_impuesto_siif, 'monto_calculo_mon_ext').text = str(int(round(retencion['base_impuesto_mont_ext']))) if tipo_modificacion not in ('R', 'D') else str(-int(round(retencion['base_impuesto_mont_ext'])))

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2

    def gen_xml_correccion_obligacion(self, cr, uid, correccion, nro_carga, tipo_doc_grp, tipo_registracion, nro_modif_grp):
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid).company_id
        inciso = company and int(company.inciso)

        if correccion.invoice_id.unidad_ejecutora_id.codigo:
            u_e = correccion.invoice_id.unidad_ejecutora_id.codigo
        else:
            u_e = int(correccion.invoice_id.operating_unit_id.unidad_ejecutora)

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = '1' #1: Cabezal
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = tipo_registracion
        etree.SubElement(e_movimiento_presup, 'desc_tipo_mov').text = 'OBL_CORREC_GRP'
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = correccion.invoice_id.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = correccion.invoice_id.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = correccion.invoice_id.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp

        if correccion.invoice_id.doc_type == 'obligacion_invoice':
            etree.SubElement(e_movimiento_presup,'nro_afect_sist_aux').text = correccion.invoice_id.afectacion_id.nro_afect_sist_aux
            etree.SubElement(e_movimiento_presup,'nro_comp_sist_aux').text = correccion.invoice_id.compromiso_id.nro_comp_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(correccion.invoice_id.compromiso_id.nro_compromiso)
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(correccion.invoice_id.afectacion_id.nro_afectacion)
        elif correccion.invoice_id.doc_type == '3en1_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = correccion.invoice_id.nro_obl_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = correccion.invoice_id.nro_obl_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(correccion.invoice_id.nro_compromiso)
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(correccion.invoice_id.nro_afectacion)
        else:
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = correccion.invoice_id.compromiso_proveedor_id and correccion.invoice_id.compromiso_proveedor_id.apg_id and correccion.invoice_id.compromiso_proveedor_id.apg_id.nro_afect_sist_aux or ''
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = correccion.invoice_id.compromiso_proveedor_id and correccion.invoice_id.compromiso_proveedor_id.nro_comp_sist_aux or ''
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(correccion.invoice_id.compromiso_proveedor_id.nro_compromiso)
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(correccion.invoice_id.compromiso_proveedor_id.apg_id.nro_afectacion_siif)

        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = correccion.invoice_id.nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(correccion.invoice_id.nro_obligacion)
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = 'C' #C - Correccion
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = correccion.invoice_id.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'T' if correccion.invoice_id.doc_type == '3en1_invoice' else 'S'
        etree.SubElement(e_movimiento_presup, 'fecha_recepcion').text = datetime.strptime(correccion.invoice_id.date_invoice, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento').text = datetime.strptime(correccion.invoice_id.date_due, '%Y-%m-%d').strftime('%Y%m%d') if correccion.invoice_id.date_due else datetime.strptime(correccion.invoice_id.date_invoice, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = correccion.invoice_id.siif_concepto_gasto.concepto
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = correccion.invoice_id.siif_financiamiento.codigo
        etree.SubElement(e_movimiento_presup, 'anticipo').text = 'N'
        # etree.SubElement(e_movimiento_presup, 'moneda').text = '1' if correccion.invoice_id.currency_id.name == 'USD' else '0'  # '1' - Dolar USA Billete en SIIF - 36
        etree.SubElement(e_movimiento_presup, 'moneda').text = str(correccion.invoice_id.currency_id.codigo_siif)

        etree.SubElement(e_movimiento_presup, 'resumen').text = correccion.siif_descripcion

        # TODO: ver es_inciso
        if correccion.invoice_id.beneficiario_siif_id.es_inciso_default:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text = 'T'
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text = '%s%s' % (str(inciso).zfill(2), str(u_e).zfill(3))
        else:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text = correccion.invoice_id.beneficiario_siif_id.tipo_doc_rupe[0] if correccion.invoice_id.beneficiario_siif_id.tipo_doc_rupe else ''
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text = correccion.invoice_id.beneficiario_siif_id.nro_doc_rupe

        # if factura.currency_id.name <> 'UYU':
        #     if tipo_modificacion in ('R', 'D'):
        #         etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = str(int(round(-factura.amount_total)))
        #     else:
        #         etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = str(int(round(factura.amount_total)))
        # else:
        #     etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = ''


        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in correccion.linea_ids:
            if llave.importe:
                e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
                etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                etree.SubElement(e_detalle_siif, 'tipo_registracion').text = tipo_registracion
                etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text = 'PART_CORREC_GRP'
                etree.SubElement(e_detalle_siif, 'objeto_gasto').text = llave.odg
                etree.SubElement(e_detalle_siif, 'auxiliar').text = llave.auxiliar
                etree.SubElement(e_detalle_siif, 'financiamiento').text = llave.fin
                etree.SubElement(e_detalle_siif, 'programa').text = llave.programa
                etree.SubElement(e_detalle_siif, 'proyecto').text = llave.proyecto
                etree.SubElement(e_detalle_siif, 'moneda').text = llave.mon
                etree.SubElement(e_detalle_siif, 'tipo_credito').text = llave.tc
                etree.SubElement(e_detalle_siif, 'importe').text = str(llave.importe)

        total_retenciones = 0
        e_retencion = etree.SubElement(e_movimiento_presup, 'Retenciones')
        for retencion in correccion.retencion_ids:
            if retencion.importe:
                e_retencion_siif = etree.SubElement(e_retencion, 'RetencionSIIF')
                etree.SubElement(e_retencion_siif, 'tipo_registro').text = '03'
                etree.SubElement(e_retencion_siif, 'tipo_registracion').text = tipo_registracion
                etree.SubElement(e_retencion_siif, 'grupo_acreedor').text = str(retencion.group_id.grupo)
                etree.SubElement(e_retencion_siif, 'acreedor').text = retencion.creditor_id.acreedor
                etree.SubElement(e_retencion_siif, 'importe').text = str(retencion.importe)
                total_retenciones += retencion.importe

        etree.SubElement(e_movimiento_presup, 'monto_obligacion').text = '0'
        etree.SubElement(e_movimiento_presup, 'liquido_pagable').text = str(-total_retenciones)
        etree.SubElement(e_movimiento_presup, 'total_retenciones').text = str(total_retenciones)
        if correccion.invoice_id.currency_id.name <> 'UYU' and correccion.invoice_id.siif_tipo_ejecucion.codigo != 'P':
            monto_cambio = int(round(correccion.invoice_id.tc_presupuesto * 10000))
            tipo_cambio = str(monto_cambio)
            etree.SubElement(e_movimiento_presup, 'tipo_cambio').text = tipo_cambio
            monto_mon_ext = -int(round(total_retenciones * 10000.0 / monto_cambio))
            etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = str(monto_mon_ext)
        else:
            etree.SubElement(e_movimiento_presup, 'tipo_cambio')
            etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = ''
        e_ces_o_emb = etree.SubElement(e_movimiento_presup, 'CesionesOEmbargos')
        e_impuestos = etree.SubElement(e_movimiento_presup, 'Impuestos')

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2


    def gen_xml_obligacion_consolidado(self, cr, uid, nota_credito, llaves_presupuestales, nro_carga, tipo_doc_grp, nro_modif_grp,
                           tipo_modificacion, es_modif=False, retenciones=False, motivo=False, enviar_datos_sice=True,
                           nro_obl_sist_aux=False):
        factura_original = nota_credito.factura_original

        importe = factura_original.amount_ttal_liq_pesos
        if nota_credito.tipo_nota_credito in ('R','D'):
            importe -= nota_credito.amount_ttal_liq_pesos
        else:
            importe += nota_credito.amount_ttal_liq_pesos

        _tipo_registracion = '03' if es_modif is False else '13'
        # enviar factura como 3en1
        if factura_original.doc_type == '3en1_invoice':
            _tipo_registracion = '04' if es_modif is False else '14'

        _tipo_registro = '01'
        _concepto_gasto = factura_original.siif_concepto_gasto.concepto
        _monto = str(int(round(importe, 0)))

        estructura_obj = self.pool.get('presupuesto.estructura')

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        estructura = estructura_obj.obtener_estructura(cr, uid, factura_original.fiscalyear_siif_id.id,
                                                       factura_original.inciso_siif_id.inciso,
                                                       factura_original.ue_siif_id.ue,
                                                       factura_original.llpapg_ids[0].programa,
                                                       factura_original.llpapg_ids[0].proyecto,
                                                       factura_original.llpapg_ids[0].mon,
                                                       factura_original.llpapg_ids[0].tc,
                                                       factura_original.llpapg_ids[0].fin,
                                                       factura_original.llpapg_ids[0].odg,
                                                       factura_original.llpapg_ids[0].auxiliar)

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup,'desc_tipo_mov').text = 'OBL_ORIG_Y_MODIF_GRP'
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = factura_original.fiscalyear_siif_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = factura_original.inciso_siif_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = factura_original.ue_siif_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp

        if factura_original.doc_type == 'obligacion_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = factura_original.afectacion_id.nro_afect_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = factura_original.compromiso_id.nro_comp_sist_aux
        elif factura_original.doc_type == '3en1_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_obl_sist_aux
            etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_obl_sist_aux
        else:
            # Enviar factura como 3en1
            etree.SubElement(e_movimiento_presup,
                             'nro_afect_sist_aux').text = factura_original.compromiso_proveedor_id and factura_original.compromiso_proveedor_id.apg_id and factura_original.compromiso_proveedor_id.apg_id.nro_afect_sist_aux or ''
            etree.SubElement(e_movimiento_presup,
                             'nro_comp_sist_aux').text = factura_original.compromiso_proveedor_id and factura_original.compromiso_proveedor_id.nro_comp_sist_aux or ''

        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'sec_afectacion')
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = tipo_modificacion
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'monto_afectacion')  # .text = _monto
        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = factura_original.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'T' if factura_original.doc_type == '3en1_invoice' else 'S'
        etree.SubElement(e_movimiento_presup, 'tipo_documento').text = factura_original.siif_tipo_documento.codigo
        etree.SubElement(e_movimiento_presup,'numero_documento').text = factura_original.supplier_invoice_number or '' if factura_original.siif_tipo_documento.codigo in ['22', '21'] else ''  # 22 - Factura, 21 - Nómina
        etree.SubElement(e_movimiento_presup,'serie_documento').text = factura_original.serie_factura if factura_original.siif_tipo_documento.codigo == '22' else ''
        etree.SubElement(e_movimiento_presup, 'secuencia_documento').text = str(factura_original.sec_factura) if factura_original.siif_tipo_documento.codigo == '22' else ''
        etree.SubElement(e_movimiento_presup,'fecha_doc_respaldo').text = '' if factura_original.doc_type == '3en1_invoice' else datetime.strptime(factura_original.date_invoice, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = _concepto_gasto
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = factura_original.siif_financiamiento.codigo

        if factura_original.siif_tipo_ejecucion.codigo not in ['R', 'T']:
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = factura_original.siif_codigo_sir.codigo
        else:
            etree.SubElement(e_movimiento_presup, 'codigo_sir').text = ''
        etree.SubElement(e_movimiento_presup, 'partidas_mon_ext').text = 'N' if factura_original.llpapg_ids[0].mon == '0' else 'S'
        # Exceptuado SICE no se envian algunos datos
        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid).company_id
        exceptuado_sice = company.exceptuado_sice or False
        # Si esta en false, los controles se hacen como hasta ahora con el ODG
        if not exceptuado_sice:
            if factura_original.doc_type != 'obligacion_invoice':
                if factura_original.doc_type != '3en1_invoice' and factura_original.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice:
                    if factura_original.orden_compra_id and factura_original.orden_compra_id.pedido_compra_id and factura_original.orden_compra_id.pedido_compra_id.ampliacion:
                        etree.SubElement(e_movimiento_presup,'ano_proc_compra').text = factura_original.orden_compra_id.doc_origen.nro_pedido_original_id.name[:4]
                    else:
                        etree.SubElement(e_movimiento_presup,'ano_proc_compra').text = factura_original.orden_compra_id.pedido_compra_id.name[:4]
                else:
                    etree.SubElement(e_movimiento_presup, 'ano_proc_compra').text = ''

                if factura_original.orden_compra_id.pedido_compra_id.tipo_compra.idTipoCompra == 'CM':
                    etree.SubElement(e_movimiento_presup,'inciso_proc_compra').text = factura_original.orden_compra_id.pedido_compra_id.inciso_proc_compra
                    etree.SubElement(e_movimiento_presup,'unidad_ejec_proc_compra').text = factura_original.orden_compra_id.pedido_compra_id.unidad_ejec_proc_compra
                else:
                    etree.SubElement(e_movimiento_presup,'inciso_proc_compra').text = estructura.linea_proy_inciso if factura_original.doc_type != '3en1_invoice' and factura_original.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''
                    etree.SubElement(e_movimiento_presup,'unidad_ejec_proc_compra').text = estructura.linea_ue if factura_original.doc_type != '3en1_invoice' and factura_original.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''
                etree.SubElement(e_movimiento_presup,'tipo_proc_compra').text = factura_original.orden_compra_id.pedido_compra_id.tipo_compra.idTipoCompra if factura_original.doc_type != '3en1_invoice' and factura_original.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''
                if factura_original.doc_type != '3en1_invoice' and factura_original.orden_compra_id and factura_original.orden_compra_id.pedido_compra_id and factura_original.orden_compra_id.pedido_compra_id.tipo_compra.idTipoCompra == 'CE' and factura_original.orden_compra_id.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice:
                    etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra').text = 'COM'
                else:
                    etree.SubElement(e_movimiento_presup,'subtipo_proc_compra').text = factura_original.orden_compra_id.pedido_compra_id.sub_tipo_compra.idSubtipoCompra if factura_original.doc_type != '3en1_invoice' and factura_original.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''
                etree.SubElement(e_movimiento_presup, 'nro_proc_compra').text = factura_original.orden_compra_id.pedido_compra_id.name.split('-')[3] if factura_original.doc_type != '3en1_invoice' and factura_original.siif_tipo_ejecucion.codigo not in ['P','R'] and enviar_datos_sice else ''
                etree.SubElement(e_movimiento_presup, 'nro_amp_proc_compra').text = str(factura_original.orden_compra_id.pedido_compra_id.nro_ampliacion) if factura_original.doc_type != '3en1_invoice' and factura_original.siif_tipo_ejecucion.codigo not in ['P', 'R'] and enviar_datos_sice else ''

        etree.SubElement(e_movimiento_presup, 'resumen').text = nota_credito.siif_descripcion or '' if not es_modif else motivo
        etree.SubElement(e_movimiento_presup, 'nro_doc_fondo_rotatorio').text = factura_original.siif_nro_fondo_rot.name or ''
        etree.SubElement(e_movimiento_presup, 'inciso_doc_optgn').text = factura_original.inciso_doc_optgn or '' if factura_original.siif_tipo_ejecucion.codigo == 'T' else ''
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_doc_optgn').text = factura_original.unidad_ejec_doc_optgn or '' if factura_original.siif_tipo_ejecucion.codigo == 'T' else ''
        etree.SubElement(e_movimiento_presup, 'nro_doc_optgn').text = factura_original.nro_doc_optgn or '' if factura_original.siif_tipo_ejecucion.codigo == 'T' else ''
        etree.SubElement(e_movimiento_presup, 'ano_doc_respaldo').text = factura_original.ano_doc_respaldo or '' if factura_original.siif_tipo_ejecucion.codigo == 'T' else ''

        if not es_modif and factura_original.doc_type == '3en1_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = ''
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = ''
        elif factura_original.doc_type == 'obligacion_invoice':
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(factura_original.compromiso_id.nro_compromiso)
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(factura_original.afectacion_id.nro_afectacion)
        else:
            etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(factura_original.compromiso_proveedor_id.nro_compromiso)
            etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(factura_original.compromiso_proveedor_id.apg_id.nro_afectacion_siif)
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(factura_original.nro_obligacion) if es_modif or tipo_modificacion == 'N' else ''
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')

        # TODO: ver es_inciso
        if factura_original.beneficiario_siif_id.es_inciso_default:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text = 'T'
            inciso = company and int(company.inciso)  # TODO: Ver si se saca de algun lado o es fijo
            # u_e = company and int(company.u_e) #TODO: Ver si se saca de algun lado o es fijo
            if factura_original.unidad_ejecutora_id.codigo:
                u_e = factura_original.unidad_ejecutora_id.codigo
            else:
                u_e = int(factura_original.operating_unit_id.unidad_ejecutora)

            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text = '%s%s' % (str(inciso).zfill(2), str(u_e).zfill(3))
            if factura_original.res_partner_bank_id:
                if not factura_original.res_partner_bank_id.bank_bic:
                    raise osv.except_osv('Error', u'Debe especificar el código de la cuenta bancaria.')
                etree.SubElement(e_movimiento_presup, 'banco_cta_benef').text = factura_original.res_partner_bank_id.bank_bic
                etree.SubElement(e_movimiento_presup, 'agencia_cta_benef').text = factura_original.res_partner_bank_id.agencia
                etree.SubElement(e_movimiento_presup, 'nro_cta_benef').text = factura_original.res_partner_bank_id.acc_number.replace('-','').replace(' ','').ljust(14,'0')  # MVARELA se manda como viene - .ljust(14,'0')
                etree.SubElement(e_movimiento_presup, 'tipo_cta_benef').text = 'A' if factura_original.res_partner_bank_id.state == 'caja de ahorros' else 'C'
                etree.SubElement(e_movimiento_presup, 'moneda_cta_benef').text = '0' if not factura_original.res_partner_bank_id.currency_id else '1'
            else:
                raise osv.except_osv('Error', u'No se especificó la cuenta bancaria.')
        elif factura_original.beneficiario_siif_id.es_inciso:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text = factura_original.beneficiario_siif_id.tipo_doc_rupe[0] if factura_original.beneficiario_siif_id.tipo_doc_rupe else ''
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text = factura_original.beneficiario_siif_id.nro_doc_rupe
            if factura_original.res_partner_bank_id:
                if not factura_original.res_partner_bank_id.bank_bic:
                    raise osv.except_osv('Error', u'Debe especificar el código de la cuenta bancaria.')
                etree.SubElement(e_movimiento_presup,'banco_cta_benef').text = factura_original.res_partner_bank_id.bank_bic
                etree.SubElement(e_movimiento_presup,'agencia_cta_benef').text = factura_original.res_partner_bank_id.agencia
                etree.SubElement(e_movimiento_presup,'nro_cta_benef').text = factura_original.res_partner_bank_id.acc_number.replace('-','').replace(' ','')  # MVARELA se manda como viene - .ljust(14,'0')
                etree.SubElement(e_movimiento_presup,'tipo_cta_benef').text = 'A' if factura_original.res_partner_bank_id.state == 'caja de ahorros' else 'C'
                etree.SubElement(e_movimiento_presup,'moneda_cta_benef').text = '0' if not factura_original.res_partner_bank_id.currency_id else '1'
            else:
                raise osv.except_osv('Error', u'No se especificó la cuenta bancaria.')
        else:
            etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text = factura_original.beneficiario_siif_id.tipo_doc_rupe[0] if factura_original.beneficiario_siif_id.tipo_doc_rupe else ''
            etree.SubElement(e_movimiento_presup, 'num_doc_benef').text = factura_original.beneficiario_siif_id.nro_doc_rupe
            if factura_original.rupe_cuenta_bancaria_id:
                etree.SubElement(e_movimiento_presup, 'banco_cta_benef').text = factura_original.rupe_cuenta_bancaria_id.codigo_banco
                etree.SubElement(e_movimiento_presup,'agencia_cta_benef').text = factura_original.rupe_cuenta_bancaria_id.codigo_sucursal
                # MVARELA nros de cuentas dependen del banco si hay que completarlas o mandarlas como estan
                # Si es "1": BROU, relleno hasta 14 con 0s a la derecha
                if factura_original.rupe_cuenta_bancaria_id.codigo_banco == '1':
                    etree.SubElement(e_movimiento_presup,'nro_cta_benef').text = factura_original.rupe_cuenta_bancaria_id.cnt_nro_cuenta.replace('-','').replace(' ','').ljust(14, '0')
                # Sino la mando como va
                else:
                    etree.SubElement(e_movimiento_presup,'nro_cta_benef').text = factura_original.rupe_cuenta_bancaria_id.cnt_nro_cuenta.replace('-','').replace(' ','')
                etree.SubElement(e_movimiento_presup, 'tipo_cta_benef').text = factura_original.rupe_cuenta_bancaria_id.codigo_tipo_cuenta[1]
                etree.SubElement(e_movimiento_presup, 'moneda_cta_benef').text = '0' if factura_original.rupe_cuenta_bancaria_id.codigo_moneda == 'UYU' else '1'

            else:
                raise osv.except_osv(('Error'), (u'No se especificó la cuenta bancaria.'))

        etree.SubElement(e_movimiento_presup, 'monto_compromiso')

        if nota_credito.tipo_nota_credito in ('R','D'):
            monto_obligacion = str(int(round(factura_original.total_nominal - nota_credito.total_nominal, 0)))
            liquido_pagable = str(int(round(factura_original.amount_ttal_liq_pesos - nota_credito.amount_ttal_liq_pesos, 0)))
            total_retenciones = str(int(round(factura_original.amount_ttal_ret_pesos - nota_credito.amount_ttal_ret_pesos, 0)))
        else:
            monto_obligacion = str(int(round(factura_original.total_nominal + nota_credito.total_nominal, 0)))
            liquido_pagable = str(int(round(factura_original.amount_ttal_liq_pesos + nota_credito.amount_ttal_liq_pesos, 0)))
            total_retenciones = str(int(round(factura_original.amount_ttal_ret_pesos + nota_credito.amount_ttal_ret_pesos, 0)))

        etree.SubElement(e_movimiento_presup, 'monto_obligacion').text = monto_obligacion
        etree.SubElement(e_movimiento_presup, 'liquido_pagable').text = liquido_pagable
        etree.SubElement(e_movimiento_presup, 'total_retenciones').text = total_retenciones

        if factura_original.currency_id.name <> 'UYU':
            if nota_credito.tipo_nota_credito in ('R', 'D'):
                etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = str(int(round(factura_original.amount_total - nota_credito.amount_total)))
            else:
                etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = str(int(round(factura_original.amount_total + nota_credito.amount_total)))
        else:
            etree.SubElement(e_movimiento_presup, 'monto_mon_ext').text = ''

        etree.SubElement(e_movimiento_presup, 'moneda').text = str(factura_original.currency_id.codigo_siif)
        etree.SubElement(e_movimiento_presup, 'fecha_recepcion').text = datetime.strptime(factura_original.date_invoice,'%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento').text = datetime.strptime(factura_original.date_due,'%Y-%m-%d').strftime('%Y%m%d') if factura_original.date_due else datetime.strptime(factura_original.date_invoice, '%Y-%m-%d').strftime('%Y%m%d')
        tipo_cambio = ''
        if factura_original.currency_id.name <> 'UYU':
            monto_cambio = int(round(factura_original.tc_presupuesto * 10000))
            tipo_cambio = str(monto_cambio)
        etree.SubElement(e_movimiento_presup, 'tipo_cambio').text = tipo_cambio
        etree.SubElement(e_movimiento_presup, 'anticipo').text = 'N'
        etree.SubElement(e_movimiento_presup, 'nro_doc_transf_monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers_mon_ext')

        etree.SubElement(e_movimiento_presup, 'sec_compromiso')

        # TODO: unir llaves entre factura y NC
        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in llaves_presupuestales:
            if llave['importe']:
                e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
                etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                etree.SubElement(e_detalle_siif, 'tipo_registracion').text = _tipo_registracion
                etree.SubElement(e_detalle_siif, 'programa').text = llave['programa']
                etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text = 'PART_OBL_ORIG_Y_MODIF_GRP'
                etree.SubElement(e_detalle_siif, 'proyecto').text = llave['proyecto']
                etree.SubElement(e_detalle_siif, 'objeto_gasto').text = llave['objeto_gasto']
                etree.SubElement(e_detalle_siif, 'auxiliar').text = llave['auxiliar']
                etree.SubElement(e_detalle_siif, 'financiamiento').text = llave['financiamiento']
                etree.SubElement(e_detalle_siif, 'moneda').text = llave['moneda']
                etree.SubElement(e_detalle_siif, 'tipo_credito').text = llave['tipo_credito']
                etree.SubElement(e_detalle_siif, 'importe').text = str(llave['importe'])

        e_retencion = etree.SubElement(e_movimiento_presup, 'Retenciones')
        for retencion in retenciones:
            if retencion['monto'] != 0:
                e_retencion_siif = etree.SubElement(e_retencion, 'RetencionSIIF')
                etree.SubElement(e_retencion_siif, 'tipo_registro').text = '03'
                etree.SubElement(e_retencion_siif, 'tipo_registracion').text = _tipo_registracion
                etree.SubElement(e_retencion_siif, 'grupo_acreedor').text = retencion['grupo'] and str(retencion['grupo']) or ''
                etree.SubElement(e_retencion_siif, 'acreedor').text = retencion['acreedor'] and str(retencion['acreedor']) or ''
                etree.SubElement(e_retencion_siif, 'importe').text = str(int(round(retencion['monto'], 0)))

        e_ces_o_emb = etree.SubElement(e_movimiento_presup, 'CesionesOEmbargos')
        if factura_original.cesion_embargo and factura_original.cesion_ids:
            for cesion in factura_original.cesion_ids:
                e_ces_o_emb_siif = etree.SubElement(e_ces_o_emb, 'CesionOEmbargoSIIF')
                etree.SubElement(e_ces_o_emb_siif, 'tipo_registro').text = '04'
                etree.SubElement(e_ces_o_emb_siif, 'tipo_registracion').text = _tipo_registracion
                if cesion.cesion_partner_id.es_inciso_default:
                    etree.SubElement(e_ces_o_emb_siif, 'clase_doc_benef').text = 'T'
                    inciso = company and int(company.inciso)
                    u_e = cesion.unidad_ejecutora_id.codigo
                    etree.SubElement(e_ces_o_emb_siif, 'num_doc_benef').text = '%s%s' % (str(inciso).zfill(2), str(u_e).zfill(3))
                else:
                    etree.SubElement(e_ces_o_emb_siif, 'clase_doc_benef').text = cesion.cesion_partner_id.tipo_doc_rupe[0] if cesion.cesion_partner_id.tipo_doc_rupe else ''
                    etree.SubElement(e_ces_o_emb_siif, 'num_doc_benef').text = cesion.cesion_partner_id.nro_doc_rupe
                if cesion.cesion_partner_id.es_inciso_default or cesion.cesion_partner_id.es_inciso:
                    if cesion.cesion_res_partner_bank_id:
                        if not cesion.cesion_res_partner_bank_id.bank_bic:
                            raise osv.except_osv(('Error'), (u'Debe especificar el código de la cuenta bancaria.'))
                        etree.SubElement(e_ces_o_emb_siif,'banco_cta_benef').text = cesion.cesion_res_partner_bank_id.bank_bic
                        etree.SubElement(e_ces_o_emb_siif,'agencia_cta_benef').text = cesion.cesion_res_partner_bank_id.agencia
                        etree.SubElement(e_ces_o_emb_siif,'nro_cta_benef').text = cesion.cesion_res_partner_bank_id.acc_number.replace('-','').replace(' ','')
                        etree.SubElement(e_ces_o_emb_siif,'tipo_cta_benef').text = 'A' if cesion.cesion_res_partner_bank_id.state == 'caja de ahorros' else 'C'
                        etree.SubElement(e_ces_o_emb_siif,'moneda_cta_benef').text = '0' if not cesion.cesion_res_partner_bank_id.currency_id else '1'
                    else:
                        raise osv.except_osv(('Error'), (u'No se especificó la cuenta bancaria.'))
                else:
                    if cesion.cesion_rupe_cta_bnc_id:
                        etree.SubElement(e_ces_o_emb_siif,'banco_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.codigo_banco
                        etree.SubElement(e_ces_o_emb_siif,'agencia_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.codigo_sucursal
                        # MVARELA nros de cuentas dependen del banco si hay que completarlas o mandarlas como estan
                        # Si es "1": BROU, relleno hasta 14 con 0s a la derecha
                        if cesion.cesion_rupe_cta_bnc_id.codigo_banco == '1':
                            etree.SubElement(e_ces_o_emb_siif, 'nro_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.cnt_nro_cuenta.replace('-','').replace(' ','').ljust(14,'0')
                        # Sino la mando como va
                        else:
                            etree.SubElement(e_ces_o_emb_siif,'nro_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.cnt_nro_cuenta.replace('-','').replace(' ','')
                        etree.SubElement(e_ces_o_emb_siif, 'tipo_cta_benef').text = cesion.cesion_rupe_cta_bnc_id.codigo_tipo_cuenta[1]
                        etree.SubElement(e_ces_o_emb_siif, 'moneda_cta_benef').text = '0' if cesion.cesion_rupe_cta_bnc_id.codigo_moneda == 'UYU' else '1'
                    else:
                        raise osv.except_osv(('Error'), (u'No se especificó la cuenta bancaria.'))
                etree.SubElement(e_ces_o_emb_siif, 'clase_doc_cedente').text = factura_original.beneficiario_siif_id.tipo_doc_rupe
                etree.SubElement(e_ces_o_emb_siif, 'num_doc_cedente').text = factura_original.beneficiario_siif_id.nro_doc_rupe
                etree.SubElement(e_ces_o_emb_siif, 'cesion_o_embargo').text = cesion.tipo_ces_emb
                etree.SubElement(e_ces_o_emb_siif, 'importe').text = str(cesion.monto_cedido_embargado)

        e_impuestos = etree.SubElement(e_movimiento_presup, 'Impuestos')
        # Probar sin retenciones
        for retencion in retenciones:
            if not retencion['es_manual']:
                e_impuesto_siif = etree.SubElement(e_impuestos, 'ImpuestoSIIF')
                etree.SubElement(e_impuesto_siif, 'tipo_registro').text = '05'
                etree.SubElement(e_impuesto_siif, 'tipo_registracion').text = _tipo_registracion
                etree.SubElement(e_impuesto_siif, 'tipo_impuesto').text = str(retencion['acreedor'])
                if 'base_impuesto' in retencion:
                    etree.SubElement(e_impuesto_siif, 'monto_calculo').text = str(
                        int(round(retencion['base_impuesto']))) if tipo_modificacion != 'N' else str(
                        -int(round(retencion['base_impuesto'])))
                if 'base_impuesto_mont_ext' in retencion:
                    etree.SubElement(e_impuesto_siif, 'monto_calculo_mon_ext').text = str(
                        int(round(retencion['base_impuesto_mont_ext']))) if tipo_modificacion != 'N' else str(
                        -int(round(retencion['base_impuesto_mont_ext'])))

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2
