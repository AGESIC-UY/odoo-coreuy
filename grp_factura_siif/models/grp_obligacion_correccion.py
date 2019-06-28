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

from openerp import api, exceptions, fields, models
from lxml import etree
import logging
_logger = logging.getLogger(__name__)
from presupuesto_estructura import TIPO_DOCUMENTO

class grpObligacionCorreccion(models.Model):
    _name = 'grp.obligacion.correccion'
    _description = u"Corrección de obligación"
    _rec_name = 'invoice_id'

    linea_ids = fields.One2many('grp.obligacion.correccion.linea', 'correccion_id', string=u"Líneas de llave presupuestal")
    retencion_ids = fields.One2many('grp.obligacion.correccion.retencion', 'correccion_id', string=u"Retenciones")
    invoice_id = fields.Many2one("account.invoice", string=u"Obligación", domain="[('nro_obligacion','>',0)]", required=True)
    state = fields.Selection([('draft', 'Borrador'), ('obligada', 'Obligada')], string='Estado', default='draft')
    siif_descripcion = fields.Char(string='Motivo', size=100, required=True)
    nro_carga = fields.Char(string="Nro de carga SIIF")
    siif_sec_obligacion = fields.Char(string=u"Secuencial obligación SIIF")
    siif_ult_modif = fields.Integer(u'Última modificación')
    nro_afectacion = fields.Integer(related='invoice_id.nro_afectacion_fnc', string=u'Nro afectación', readonly=True)
    nro_compromiso = fields.Integer(related='invoice_id.nro_compromiso_fnc', string=u'Nro compromiso', readonly=True)
    nro_obligacion = fields.Integer(related='invoice_id.nro_obligacion', string=u'Nro obligación', readonly=True)
    monto_afectado = fields.Integer(related='invoice_id.monto_afectado_fnc', string=u'Monto afectado', readonly=True)
    monto_comprometido = fields.Integer(related='invoice_id.monto_comprometido_fnc', string=u'Monto comprometido', readonly=True)
    fiscalyear_siif_id = fields.Many2one('account.fiscalyear', related='invoice_id.fiscalyear_siif_id', string=u'Año fiscal', readonly=True)
    inciso_siif_id = fields.Many2one('grp.estruc_pres.inciso', related='invoice_id.inciso_siif_id', string='Inciso', readonly=True)
    ue_siif_id = fields.Many2one('grp.estruc_pres.ue', related='invoice_id.ue_siif_id', string='Unidad ejecutora', readonly=True)

    @api.constrains('linea_ids')
    def check_monto_llaves(self):
        for record in self:
            total= 0
            for linea in record.linea_ids:
                total += linea.importe
            if total != 0:
                raise exceptions.ValidationError(u'El total de las llaves debe ser igual a 0.')

    @api.multi
    def correccion_impactar_presupuesto(self):
        context = dict(self._context)
        estructura_obj = self.env['presupuesto.estructura']
        for correccion in self:
            for llave in correccion.linea_ids:

                estructura = estructura_obj.obtener_estructura(correccion.fiscalyear_siif_id.id,
                                                               correccion.inciso_siif_id.inciso,
                                                               correccion.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto,
                                                               llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)

                # Control 2: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                        (correccion.fiscalyear_siif_id.code, correccion.inciso_siif_id.inciso, correccion.ue_siif_id.ue,
                         llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                    raise exceptions.ValidationError(u'Error ! No se encontró estructura con la llave presupuestal '
                                                     u'asociada a la factura: %s' % desc_error)

                #Se cambia el importe a negativo si es reduccion o devolucion al credito
                if correccion.invoice_id.tipo_nota_credito in ('R', 'D'):
                    importe = -llave.importe
                else:
                    importe = llave.importe

                # Se obliga en el presupuesto, si es 3en1 se afecta, compromete y obliga
                if correccion.invoice_id.doc_type == '3en1_invoice' or (correccion.invoice_id.doc_type == 'ajuste_invoice' and correccion.invoice_id.factura_original.doc_type == '3en1_invoice'):
                    res_af = estructura_obj.afectar(correccion.invoice_id.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                    importe,
                                                    estructura)
                    res_comp = estructura_obj.comprometer(correccion.invoice_id.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                          importe,
                                                          estructura)
                    res_obligar = estructura_obj.obligar(correccion.invoice_id.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                         importe,
                                                         estructura)
                else:
                    res_obligar = estructura_obj.obligar(correccion.invoice_id.id, TIPO_DOCUMENTO.FACTURA,
                                                         importe,
                                                         estructura)
            correccion.write({'state': 'obligada'})
        return True

    @api.multi
    def correccion_cancel_presupuesto(self):
        estructura_obj = self.env['presupuesto.estructura']
        for correccion in self:
            for llave in correccion.linea_ids:
                estructura = estructura_obj.obtener_estructura(correccion.fiscalyear_siif_id.id,
                                                               correccion.inciso_siif_id.inciso,
                                                               correccion.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                # Control 2: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (correccion.fiscalyear_siif_id.code, correccion.inciso_siif_id.inciso, correccion.ue_siif_id.ue,
                                  llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                    raise exceptions.ValidationError(u'Error ! No se encontró estructura con la llave presupuestal '
                                                     u'asociada a la factura: %s' % desc_error)

                #Se cambia el importe a negativo si es reduccion o devolucion al credito
                if correccion.invoice_id.tipo_nota_credito in ('R', 'D'):
                    importe = -llave.importe
                else:
                    importe = llave.importe

                # Se obliga en el presupuesto (* -1), si es 3en1 se afecta, compromete y obliga
                if correccion.invoice_id.doc_type == '3en1_invoice' or (correccion.invoice_id.doc_type == 'ajuste_invoice' and correccion.invoice_id.factura_original.doc_type == '3en1_invoice'):
                    res_af = estructura_obj.afectar(correccion.invoice_id.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                    -1 * importe, estructura)
                    res_comp = estructura_obj.comprometer(correccion.invoice_id.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                          -1 * importe, estructura)
                    res_obligar = estructura_obj.obligar(correccion.invoice_id.id, TIPO_DOCUMENTO.TRES_EN_UNO,
                                                         -1 * importe, estructura)
                else:
                    res_obligar = estructura_obj.obligar(correccion.invoice_id.id, TIPO_DOCUMENTO.FACTURA,
                                                         -1 * importe, estructura)
            correccion.write({'state': 'draft'})
        return True

    @api.multi
    def action_borrar_correccion_obligacion(self):
        self.correccion_cancel_presupuesto()
        # for invoice in self:
            # wf_service = netsvc.LocalService('workflow')
            # wf_service.trg_validate(uid, 'account.invoice', invoice.id, 'invoice_cancel', cr)
            # self.action_cancel_draft([invoice.id])
            #Para poder borrar la factura en estado borrador
            # self.write(cr, uid, [invoice.id], {'internal_number': False}, context=context)
            # state = 'draft'
            # if invoice.doc_type in ('obligacion_invoice', '3en1_invoice'):  # Obligacion y 3en1
            #     state = 'draft'
            # elif invoice.doc_type == 'invoice':  # Factura de Proveedor
            #     state = 'sice'
            # self.write(cr, uid, [invoice.id], {'state': state}, context=context)
        company = self.env.user.company_id
        integracion_siif = company.integracion_siif or False
        if not integracion_siif:
            return True
        else:
            return self.correccion_borrar_modif_siif()

    @api.multi
    def correccion_borrar_modif_siif(self):
        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']
        for correccion in self:
            nro_carga = self.env['ir.sequence'].with_context(fiscalyear_id=correccion.fiscalyear_siif_id.id).get('num_carga_siif')  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            # SE OBLIGA CONTRA SIIF
            nro_modif_grp = correccion.siif_ult_modif
            # Tipo de documento: Modificación de obligacion
            # if correccion.invoice_id.doc_type == '3en1_invoice':
            #     tipo_doc_grp = '14'
            # else:
            #     tipo_doc_grp = '13'
            tipo_doc_grp = '15'

            xml_borrar_obligacion = generador_xml.gen_xml_borrado_correccion_obligacion(correccion=correccion,
                                                                             factura_original=correccion.invoice_id,
                                                                             nro_carga=nro_carga,
                                                                             tipo_doc_grp=tipo_doc_grp,
                                                                             nro_modif_grp=nro_modif_grp,
                                                                             nro_obl_sist_aux=correccion.invoice_id.nro_obl_sist_aux)
            resultado_siif = siif_proxy.put_solic(xml_borrar_obligacion)

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
                    dicc_modif['siif_sec_obligacion'] = False
                    dicc_modif['siif_ult_modif'] = False
                    correccion.write(dicc_modif)
                else:
                    descr_error = movimiento.find('comentario').text
                    raise exceptions.ValidationError((u'Error al intentar borrar obligación en SIIF '
                                                     u'asociada a la corrección: %s'),
                                                     (descr_error or u'Error no especificado por el SIIF'))
            correccion.write({'state': 'draft'})

            return True

    @api.multi
    def enviar_siif(self):
        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']
        #impactar presupuesto???
        self.correccion_impactar_presupuesto()
        #impactar contabilidad???
        #controles montos, llaves, etc
        #actualizar documentos, original y correccion
        #actualizar llaves y log original
        for record in self:
            # Tipo de documento
            tipo_doc_grp = '15' #15 - Correcciones, pendiente definir tipos GRP
            if record.linea_ids:
                tipo_registracion = '14'
            else:
                tipo_registracion = '13'

            nro_modif_grp = record.invoice_id.siif_ult_modif + 1
            #TODO: revisar que pasa con estos valores en caso de correccion

            nro_carga = self.env['ir.sequence'].with_context(fiscalyear_id=record.invoice_id.fiscalyear_siif_id.id).get('num_carga_siif')  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            xml_correccion_obligacion = generador_xml.gen_xml_correccion_obligacion(correccion=record, nro_carga=nro_carga, tipo_doc_grp=tipo_doc_grp, tipo_registracion=tipo_registracion, nro_modif_grp=nro_modif_grp)

            resultado_siif = siif_proxy.put_solic(xml_correccion_obligacion)

            _logger.info('RESULTADO: %s', resultado_siif)

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
                # if dicc_modif.get('resultado', None) is None and movimiento.find('resultado').text and movimiento.find('resultado').text.strip():
                #     dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_obligacion', None) is None and movimiento.find('sec_obligacion').text and movimiento.find('sec_obligacion').text.strip():
                    dicc_modif['siif_sec_obligacion'] = movimiento.find('sec_obligacion').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find('nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if dicc_modif.get('nro_carga', None) is None and movimiento.find('nro_carga').text and movimiento.find('nro_carga').text.strip():
                    dicc_modif['nro_carga'] = movimiento.find('nro_carga').text.strip()
                # if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                #     descr_error = movimiento.find('comentario').text
                #
                # # Si viene E en alguno de los movimientos se larga el error
                # if movimiento.find('resultado').text == 'E':
                #     raise osv.except_osv(('Error al obligar en SIIF'), (descr_error or u'Error no especificado por el SIIF'))

            # error en devolucion de numero de obligacion
            if not nro_obligacion_devuelto:
                raise exceptions.ValidationError('Error al obligar en SIIF: %s' % (descr_error or u'Error en devolución de número de obligación por el SIIF'))


            # # Agregar log en historico de llave presupuestal de nota de credito
            # # -----------------------------------------------------------------
            # modif_obligacion_log_obj = self.env['wiz.modif_obligacion_siif_log']
            # for llave in record.linea_ids:
            #     # Nota de Credito
            #     vals = {
            #         'invoice_id': nota_credito.id,
            #         'tipo': nota_credito.tipo_nota_credito,
            #         'fecha': fields.date.context_today(self, cr, uid, context=context),
            #         'programa': llave.programa,
            #         'proyecto': llave.proyecto,
            #         'moneda': llave.mon,
            #         'tipo_credito': llave.tc,
            #         'financiamiento': llave.fin,
            #         'objeto_gasto': llave.odg,
            #         'auxiliar': llave.auxiliar,
            #         'importe': llave.importe if nota_credito.tipo_nota_credito not in (
            #         'R', 'D') else -llave.importe,
            #         'siif_sec_obligacion': dicc_modif.get('siif_sec_obligacion', False),
            #         'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
            #     }
            #     modif_obligacion_log_obj.create(cr, uid, vals, context=context)
            #     # Factura original
            #     vals = {
            #         'invoice_id': nota_credito.factura_original.id,
            #         'tipo': nota_credito.tipo_nota_credito,
            #         'fecha': fields.date.context_today(self, cr, uid, context=context),
            #         'programa': llave.programa,
            #         'proyecto': llave.proyecto,
            #         'moneda': llave.mon,
            #         'tipo_credito': llave.tc,
            #         'financiamiento': llave.fin,
            #         'objeto_gasto': llave.odg,
            #         'auxiliar': llave.auxiliar,
            #         'importe': llave.importe if nota_credito.tipo_nota_credito not in ('R', 'D') else -llave.importe,
            #         'siif_sec_obligacion': dicc_modif.get('siif_sec_obligacion', False),
            #         'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
            #     }
            #     modif_obligacion_log_obj.create(cr, uid, vals, context=context)
            #
            #     # Actualizar datos en factura original
            #     # --------------------------------------
            #     # Número de última modificación
            #     invoice_obj = self.pool.get('account.invoice')
            #     res_write_invoice = invoice_obj.write(cr, uid, [nota_credito.factura_original.id], dicc_modif, context=context)
            #
            #     # Importe de llave presupuestal
            #     condicion = []
            #     condicion.append(('invoice_id', '=', nota_credito.factura_original.id))
            #     condicion.append(('odg', '=', llave.odg))
            #     condicion.append(('auxiliar', '=', llave.auxiliar))
            #     condicion.append(('fin', '=', llave.fin))
            #     condicion.append(('programa', '=', llave.programa))
            #     condicion.append(('proyecto', '=', llave.proyecto))
            #     condicion.append(('mon', '=', llave.mon))
            #     condicion.append(('tc', '=', llave.tc))
            #
            #     lineas_llavep_obj = self.pool.get('grp.compras.lineas.llavep')
            #     llavep_id = lineas_llavep_obj.search(cr, uid, condicion, context=context)
            #
            #     if len(llavep_id) < 1:
            #         if nota_credito.tipo_nota_credito != 'A':
            #             raise exceptions.ValidationError(u'Error: La llave presupuestal buscada no se encuentra en la factura.')
            #         else:
            #             vals = {
            #                 'invoice_id': nota_credito.factura_original.id,
            #                 'fin_id': llave.fin_id.id,
            #                 'programa_id': llave.programa_id.id,
            #                 'proyecto_id': llave.proyecto_id.id,
            #                 'odg_id': llave.odg_id.id,
            #                 'auxiliar_id': llave.auxiliar_id.id,
            #                 'mon_id': llave.mon_id.id,
            #                 'tc_id': llave.tc_id.id,
            #                 'importe': 0,
            #             }
            #             llavep_id = lineas_llavep_obj.create(cr, uid, vals, context=context)
            #             llavep_id = [llavep_id]
            #
            #     llavep = lineas_llavep_obj.browse(cr, uid, llavep_id, context=context)
            #     llavep = llavep[0]
            #
            #     dicc_modif = {}
            #     if nota_credito.tipo_nota_credito in ('R', 'D'):
            #         dicc_modif['importe'] = llavep.importe - llave.importe
            #     else:
            #         dicc_modif['importe'] = llavep.importe + llave.importe
            #
            #     res_write_invoice = lineas_llavep_obj.write(cr, uid, [llavep.id], dicc_modif, context=context)

            #Actualizo en la factura original los secuenciales
            record.invoice_id.write({'siif_sec_obligacion': dicc_modif['siif_sec_obligacion'], 'siif_ult_modif': dicc_modif['siif_ult_modif']})

            # Actualizo en la correccion: estado, Nro carga, siif_sec_obligacion y siif_ult_modif
            dicc_modif['state'] = 'obligada'
            record.write(dicc_modif)


class grpObligacionCorreccionLinea(models.Model):
    _name = 'grp.obligacion.correccion.linea'
    _description = u"Línea de corrección"

    correccion_id = fields.Many2one('grp.obligacion.correccion', string=u"Corrección de obligación", required=True)
    odg_id = fields.Many2one('grp.estruc_pres.odg', 'ODG', required=True)
    auxiliar_id = fields.Many2one('grp.estruc_pres.aux', 'Auxiliar', required=True)
    fin_id = fields.Many2one('grp.estruc_pres.ff', 'Fin', required=True)
    programa_id = fields.Many2one('grp.estruc_pres.programa', 'Programa', required=True)
    proyecto_id = fields.Many2one('grp.estruc_pres.proyecto', 'Proyecto', required=True)
    mon_id = fields.Many2one('grp.estruc_pres.moneda', 'Mon', required=True)
    tc_id = fields.Many2one('grp.estruc_pres.tc', 'TC', required=True)
    importe = fields.Integer('Importe', required=True)
    # Campos related
    odg = fields.Char(related='odg_id.odg', string='ODG related', store=True, readonly=True)
    auxiliar = fields.Char(related='auxiliar_id.aux', string='Auxiliar related', store=True, readonly=True)
    fin = fields.Char(related='fin_id.ff', string='Fin related', store=True, readonly=True)
    programa = fields.Char(related='programa_id.programa', string='Programa related', store=True, readonly=True)
    proyecto = fields.Char(related='proyecto_id.proyecto', string='Proyecto related', store=True, readonly=True)
    mon = fields.Char(related='mon_id.moneda', string='Mon related', store=True, readonly=True)
    tc = fields.Char(related='tc_id.tc', string='TC related', store=True, readonly=True)

    # On_change llaves presupuestal
    @api.onchange('odg_id')
    def onchange_objeto_del_gasto(self):
        auxiliar_id = False
        if self.odg_id:
            auxiliar_ids = self.env['grp.estruc_pres.aux'].search([('odg_id', '=', self.odg_id.id)])
            if len(auxiliar_ids) == 1:
                auxiliar_id = auxiliar_ids.id
        self.auxiliar_id = auxiliar_id
        # self.fin_id = False
        # self.programa_id = False
        # self.proyecto_id = False
        # self.mon_id = False
        # self.tc_id = False

    @api.onchange('auxiliar_id')
    def onchange_auxiliar(self):
        fin_id = False
        if self.auxiliar_id:
            fin_ids = self.env['grp.estruc_pres.ff'].search([('aux_id', '=', self.auxiliar_id.id)])
            if len(fin_ids) == 1:
                fin_id = fin_ids.id
        self.fin_id = fin_id
        # self.programa_id = False
        # self.proyecto_id = False
        # self.mon_id = False
        # self.tc_id = False

    @api.onchange('fin_id')
    def onchange_fuente_de_financiamiento(self):
        programa_id = False
        if self.fin_id:
            programa_ids = self.env['grp.estruc_pres.programa'].search([('ff_id', '=', self.fin_id.id)])
            if len(programa_ids) == 1:
                programa_id = programa_ids.id
        self.programa_id = programa_id
        # self.proyecto_id = False
        # self.mon_id = False
        # self.tc_id = False

    @api.onchange('programa_id')
    def onchange_programa(self):
        proyecto_id = False
        if self.programa_id:
            proyecto_ids = self.env['grp.estruc_pres.proyecto'].search([('programa_id', '=', self.programa_id.id)])
            if len(proyecto_ids) == 1:
                proyecto_id = proyecto_ids.id
        self.proyecto_id = proyecto_id
        # self.mon_id = False
        # self.tc_id = False

    @api.onchange('proyecto_id')
    def onchange_proyecto(self):
        mon_id = False
        if self.proyecto_id:
            mon_ids = self.env['grp.estruc_pres.moneda'].search([('proyecto_id', '=', self.proyecto_id.id)])
            if len(mon_ids) == 1:
                mon_id = mon_ids.id
        self.mon_id = mon_id
        # self.tc_id = False

    @api.onchange('mon_id')
    def onchange_moneda(self):
        tc_id = False
        if self.mon_id:
            tc_ids = self.env['grp.estruc_pres.tc'].search([('moneda_id', '=', self.mon_id.id)])
            if len(tc_ids) == 1:
                tc_id = tc_ids.id
        self.tc_id = tc_id


class grpObligacionCorreccionRetencion(models.Model):
    _name = 'grp.obligacion.correccion.retencion'
    _description = u"Retención de corrección"

    correccion_id = fields.Many2one('grp.obligacion.correccion', string=u"Corrección de obligación", required=True)
    group_id = fields.Many2one('account.group.creditors', string='Grupo', required=True)
    creditor_id = fields.Many2one('account.retention.creditors', string='Acreedor', required=True, domain="[('group_id', '=', group_id)]")
    importe = fields.Integer(string="Importe", required=True)
