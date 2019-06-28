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

from openerp import models, fields, api, exceptions, _
from openerp.osv import osv
import time
from openerp import netsvc
from presupuesto_estructura import TIPO_DOCUMENTO
from lxml import etree

# TODO: SPRING 8 GAP 236.237 M

class RegularizacionClearing(models.Model):
    _name = 'regularizacion.clearing'
    _description = u"Regularización clearing"


    def _default_tipo_ejecucion(self):
        tipo_ejecucion_id = self.env['tipo.ejecucion.siif'].search([('codigo','=','R')])
        return tipo_ejecucion_id and tipo_ejecucion_id[0].id or False

    def _default_financiamiento(self):
        financiamiento_id = self.env['financiamiento.siif'].search([('codigo','=','11')])
        return financiamiento_id and financiamiento_id[0].id or False

    def _default_tipo_documento(self):
        tipo_documento = self.env['tipo.documento.siif'].search([('codigo','=','60')])
        return tipo_documento and tipo_documento[0].id or False

    # TODO: Agregando por defecto el año fiscal actual ya que este campo se utiliza en la sequencia de esta clase
    def default_fiscalyear(self):
        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.env['res.users'].browse(self._uid).company_id.id
        fiscalyear_id = self.env['account.fiscalyear'].search(
            [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
             ('company_id', '=', uid_company_id)])
        return fiscalyear_id and fiscalyear_id[0].id or False

    def default_inciso_siif(self, fiscalyear_id):
        if fiscalyear_id:
            ids_pres_inciso = self.env['grp.estruc_pres.inciso'].search([('fiscal_year_id', '=', fiscalyear_id)])
        return ids_pres_inciso and ids_pres_inciso[0].id or False

    def default_ue_siif(self, ids_pres_inciso):
        if ids_pres_inciso:
            ids_pres_ue = self.env['grp.estruc_pres.ue'].search([('inciso_id', '=', ids_pres_inciso)])
        return ids_pres_ue and ids_pres_ue[0].id or False

    @api.model
    def default_get(self, fields):
        res = super(RegularizacionClearing, self).default_get(fields)
        res['siif_tipo_ejecucion'] = self._default_tipo_ejecucion()
        res['siif_financiamiento'] = self._default_financiamiento()
        res['siif_tipo_documento'] = self._default_tipo_documento()
        res['fiscalyear_id'] = self.default_fiscalyear()
        res['inciso_siif_id'] = self.default_inciso_siif(res['fiscalyear_id'])
        res['ue_siif_id'] = self.default_ue_siif(res['inciso_siif_id'])
        return res


    name = fields.Char(string=u'Regularización clearing', readonly=True, default='RC Borrador')
    beneficiario_siif_id = fields.Many2one('res.partner', u'Beneficiario SIIF',readonly=True)
    id_rupe_benef = fields.Integer(compute='_get_rupe_beneficiario', string='ID RUPE Beneficiario', store=True)
    rupe_cuenta_bancaria_id = fields.Many2one('rupe.cuentas.bancarias', u'Cuenta Bancaria',readonly=True,states={'draft': [('readonly', False)]})
    date = fields.Date(u'Fecha', readonly=True, states={'draft': [('readonly', False)]})
    fecha_vencimiento = fields.Date('Fecha vencimiento', readonly=True, states={'draft': [('readonly', False)]})
    fiscalyear_id = fields.Many2one('account.fiscalyear', u'Año fiscal',readonly=True,states={'draft': [('readonly', False)]})

    nro_afectacion = fields.Integer(u'Nº afectación')
    monto_autorizado = fields.Integer(u'Monto autorizado')
    nro_obligacion = fields.Integer(u'Nº obligación')
    nro_compromiso = fields.Integer(u'Nº compromiso')
    monto_comprometido = fields.Integer(u'Monto comprometido')

    papa_tng = fields.Boolean(u"Obligación paga por TGN")
    siif_tipo_ejecucion = fields.Many2one('tipo.ejecucion.siif', u'Tipo de ejecución')
    siif_concepto_gasto = fields.Many2one('presupuesto.concepto', u'Concepto del gasto', readonly=True, states={'draft': [('readonly', False)]})
    siif_financiamiento = fields.Many2one('financiamiento.siif', u'Fuente de financiamiento', readonly=True, states={'draft': [('readonly', False)]})
    siif_tipo_documento = fields.Many2one('tipo.documento.siif', u'Tipo de documento', readonly=True,states={'draft': [('readonly', False)]})
    siif_descripcion = fields.Text(u"Descripción SIIF", size=100, readonly=True, states={'draft': [('readonly', False)]})

    account_invoice_ids = fields.Many2many('account.invoice', 'account_invoice_regularizacion_rel',
                                            'invoice_id', 'regularizacion_id', string=u'Facturas de suministro',
                                                readonly=True, states={'draft': [('readonly', False)]})

    total_nominal = fields.Float(compute='_get_total_nominal', string=u'Total nominal en pesos')
    amount_ttal_impuestos_pesos = fields.Float(compute='_get_total_impuesto', string=u'Impuestos en pesos')
    amount_ttal_ret_pesos = fields.Float(compute='_get_total_ret', string=u'Total retenciones')
    amount_ttal_liq_pesos =fields.Float(compute='_get_total_liq', string=u'Líquido pagable')

    inciso_siif_id = fields.Many2one('grp.estruc_pres.inciso', u'Inciso', readonly=True, states={'draft': [('readonly', False)]})
    ue_siif_id = fields.Many2one('grp.estruc_pres.ue', u'Unidad ejecutora', readonly=True, states={'draft': [('readonly', False)]})
    llpapg_ids = fields.One2many('regularizacion.clearing.llavep', 'regularizacion_id', string=u'Líneas presupuesto',
                                 readonly=True, states={'draft': [('readonly', False)]})
    total_llavep = fields.Float(compute='_get_total_llavep', string='Total llave presupuestal',
                                    digits=(16, 0))

    state = fields.Selection([('draft', u'Borrador'), ('confirm', u'Confirmado'), ('forced', u'Obligado'),
                              ('intervened', u'Intervenido'), ('cancel', u'Cancelado')], u'Estado', readonly=True, default='draft')

    intervenido_con_observ = fields.Boolean(u"Intervenido con observaciones")
    observacion_ids = fields.One2many('grp.observacion.tc.regularizacion', 'regularizacion_id', u'Observación')


    @api.one
    @api.constrains('date','fecha_vencimiento')
    def _check_fechas(self):

        if self.date and self.fecha_vencimiento and (self.date > self.fecha_vencimiento):
            raise exceptions.ValidationError('La fecha de vencimiento no puede ser menor al campo fecha ')

    # TODO: Agregando el campo operating_unit_id ya que es uno de los parametros a tener en cuenta en el agrupador de suministros
    operating_unit_id = fields.Many2one('operating.unit', string=u'Unidad ejecutora', readonly=True, states={'draft': [('readonly', False)]})

    nro_obl_sist_aux = fields.Char(u'Nro Obligación Sist. Aux')
    siif_ult_modif = fields.Integer(u'Última modificación')
    siif_sec_obligacion = fields.Char(u'Secuencial obligación')

    anulacion_siif_log_ids = fields.One2many('obligacion.rc.anulacion.siif.log', 'regularizacion_id', 'Log anulaciones')

    @api.one
    @api.depends('beneficiario_siif_id')
    def _get_rupe_beneficiario(self):
        self.id_rupe_benef = self.beneficiario_siif_id and self.beneficiario_siif_id.id_rupe or False

    @api.one
    @api.depends('beneficiario_siif_id')
    def _get_es_inciso_default_beneficiario(self):
        self.benef_es_inciso_default = self.beneficiario_siif_id and self.beneficiario_siif_id.es_inciso_default or False

    @api.one
    @api.depends('beneficiario_siif_id')
    def _get_es_inciso_beneficiario(self):
        self.benef_es_inciso = self.beneficiario_siif_id and self.beneficiario_siif_id.es_inciso or False

    @api.multi
    def _get_total_nominal(self):
        for rec in self:
            rec.total_nominal = 0.0
            if rec.account_invoice_ids:
                rec.total_nominal = sum(map(lambda x: x.total_nominal, rec.account_invoice_ids))

    @api.multi
    def _get_total_impuesto(self):
        for rec in self:
            rec.amount_ttal_impuestos_pesos = 0.0
            if rec.account_invoice_ids:
                rec.amount_ttal_impuestos_pesos = sum(
                    map(lambda x: x.amount_ttal_impuestos_pesos, rec.account_invoice_ids))

    @api.multi
    def _get_total_ret(self):
        for rec in self:
            rec.amount_ttal_ret_pesos = 0.0
            if rec.account_invoice_ids:
                rec.amount_ttal_ret_pesos = sum(
                    map(lambda x: x.amount_ttal_ret_pesos, rec.account_invoice_ids))

    @api.multi
    def _get_total_liq(self):
        for rec in self:
            rec.amount_ttal_liq_pesos = rec.total_nominal - rec.amount_ttal_ret_pesos

    @api.multi
    def _get_total_llavep(self):
        for rec in self:
            rec.total_llavep = 0.0
            if rec.llpapg_ids:
                rec.total_llavep = sum(map(lambda x: x.importe, rec.llpapg_ids))

    # TODO SPRING 8 GAP 236.237 M Implementando mismo comportamiento que la modelo account.invoice
    @api.onchange('fiscalyear_id')
    def onchange_fiscalyear_id(self):
        self.inciso_siif_id = False
        self.ue_siif_id = False

        pres_inciso_obj = self.env['grp.estruc_pres.inciso']
        pres_ue_obj = self.env['grp.estruc_pres.ue']
        if self.fiscalyear_id:
            ids_pres_inciso = pres_inciso_obj.search([('fiscal_year_id','=', self.fiscalyear_id.id)])
            if ids_pres_inciso:
                self.inciso_siif_id = ids_pres_inciso[0].id
                ids_pres_ue = pres_ue_obj.search([('inciso_id','=', ids_pres_inciso[0].id)])
                if ids_pres_ue:
                    self.ue_siif_id = ids_pres_ue[0].id

    @api.multi
    def btn_confirm(self):
        for rec in self:
            name = self.env['ir.sequence'].with_context(fiscalyear_id=rec.fiscalyear_id.id).get('regularizacion.clearing.siif')
            rec.write({'state': 'confirm', 'name': name})
        return True

    @api.multi
    def btn_cancel(self):
        for rec in self:
            if rec.account_invoice_ids:
                for invoice in rec.account_invoice_ids:
                    invoice.write({'in_regulation_clearing': False, 'regularizacion_id': False})
        return self.write({'state': 'cancel'})

    @api.multi
    def btn_cancel_draft(self):
        for rec in self:
            if rec.account_invoice_ids:
                for invoice in rec.account_invoice_ids:
                    invoice.write({'in_regulation_clearing': True, 'regularizacion_id': rec.id})
        return self.write({'state': 'draft', 'name': 'RC Borrador'})

    @api.multi
    def write(self, values):
        if 'account_invoice_ids' in values and values['account_invoice_ids'][0][0] == 6:
            invoice_ids = list(set(self.account_invoice_ids.ids) - set(values['account_invoice_ids'][0][2]))
            if len(invoice_ids):
                invoices = self.env['account.invoice'].browse(invoice_ids)
            else:
                invoices = self.env['account.invoice'].browse(values['account_invoice_ids'][0][2])
            if invoices:
                for invoice in invoices:
                    invoice.write({'in_regulation_clearing': False, 'regularizacion_id': False})
        if 'account_invoice_ids' in values and values['account_invoice_ids'][0][0] == 3:
            invoice_ids = list(set(values['account_invoice_ids'][0][1]))
            invoices = []
            if len(invoice_ids):
                invoices = self.env['account.invoice'].browse(invoice_ids)
            if invoices:
                for invoice in invoices:
                    invoice.write({'in_regulation_clearing': False, 'regularizacion_id': False})

        return super(RegularizacionClearing, self).write(values)

    @api.multi
    def unlink(self):
        for rec in self:
            for line in rec.account_invoice_ids:
                line.write({'in_regulation_clearing': False, 'regularizacion_id': False})
        return super(RegularizacionClearing, self).unlink()


    @api.multi
    def regularizacion_clearing_impactar_presupuesto(self):
        estructura_obj = self.env['presupuesto.estructura']
        for rc in self:

            # Control 1: que la sumatoria de llave sea igual al totoal a reponer
            if rc.total_llavep <> rc.total_nominal:
                raise osv.except_osv(('Error'), (
                'La sumatoria de importes de llaves presupuestales no es igual al total nominal.'))

            for llave in rc.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(rc.fiscalyear_id.id,
                                                               rc.inciso_siif_id.inciso,
                                                               rc.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto,
                                                               llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)

                # Control: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (rc.fiscalyear_id.code, rc.inciso_siif_id.inciso, rc.ue_siif_id.ue, llave.odg,
                                  llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                    raise exceptions.ValidationError(
                        u'No se encontró estructura con la llave presupuestal asociada a la regularización clearing: ' + desc_error)

                # Se obliga en el presupuesto (es 3en1 se afecta, compromete y obliga)
                res_af = estructura_obj.afectar(rc.id, 9, llave.importe, estructura)
                res_comp = estructura_obj.comprometer(rc.id, 9, llave.importe, estructura)
                res_obligar = estructura_obj.obligar(rc.id, 9, llave.importe, estructura)
        return True


    def regularizacion_clearing_enviar_siif(self):
        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']

        #TODO revisar tipos de documento grp, dato a enviar a siif pero que no esta clara su definicion en grp
        tipo_doc_grp = '04'

        for rc in self:

            # Control de no enviar llave presupuestal vacia
            if len(rc.llpapg_ids) == 0:
                raise exceptions.ValidationError(_(u'Debe cargar al menos una llave presupuestal.'))

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if rc.siif_financiamiento.exceptuado_sice or rc.siif_tipo_ejecucion.exceptuado_sice or rc.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.env['presupuesto.objeto.gasto']
                for llave_pres in rc.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search([('name', '=', llave_pres.odg),
                                                                         ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise exceptions.ValidationError(_(u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                             llave_pres.odg, llave_pres.auxiliar))

            # se obliga contra el SIIF
            context = dict(self._context or {})
            context.update({'fiscalyear_id': rc.fiscalyear_id and rc.fiscalyear_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(self._cr, self._uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_obl_sist_aux = self.pool.get('ir.sequence').get(self._cr, self._uid,'sec.siif.obligacion', context=context)
            nro_obl_sist_aux = nro_obl_sist_aux[4:]

            xml_obligacion = generador_xml.gen_xml_obligacion_3en1_rc(regularizacion_clearing=rc, llaves_presupuestales=rc.llpapg_ids,
                                              importe=rc.amount_ttal_liq_pesos, nro_carga=nro_carga, tipo_doc_grp=tipo_doc_grp,
                                              nro_modif_grp=0,
                                              tipo_modificacion='A',
                                              enviar_datos_sice=enviar_datos_sice,
                                              nro_obl_sist_aux=nro_obl_sist_aux)

            resultado_siif = siif_proxy.put_solic(xml_obligacion)

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
                    raise exceptions.ValidationError(_(descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_obligacion', None) and dicc_modif.get('nro_compromiso', None) \
                        and dicc_modif.get('nro_afectacion', None) and dicc_modif.get('resultado', None):
                    break

            # error en devolucion de numero de obligacion
            if not dicc_modif.get('nro_obligacion', None):
                raise exceptions.ValidationError(_(descr_error or u'Error en devolución de número de obligación por el SIIF'))

            # Enviar factura como 3 en 1, actualizar Monto Autorizado y Comprometido, condicion de factura y etapa del gasto = 3en1
            dicc_modif['monto_afectado'] = int(round(rc.total_nominal, 0))
            dicc_modif['monto_comprometido'] = int(round(rc.total_nominal, 0))
            dicc_modif['nro_obl_sist_aux'] = nro_obl_sist_aux

            res_write_rc = rc.write(dicc_modif)

            if res_write_rc:
                modif_obligacion_log_obj = self.env['wiz.modif_regularizacion_siif_log']
                for llave in rc.llpapg_ids:
                    vals = {
                        'regularizacion_id': rc.id,
                        'tipo': 'A',
                        'fecha': fields.Date.today(),
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
                    modif_obligacion_log_obj.create(vals)
        return True



    @api.multi
    def btn_obligar(self):
        self.regularizacion_clearing_impactar_presupuesto()
        company = self.env['res.users'].browse(self._uid).company_id
        integracion_siif = company.integracion_siif or False
        if integracion_siif:
            self.regularizacion_clearing_enviar_siif()
        self.state = 'forced'
        return True


    @api.multi
    def regularizacion_clearing_cancel_presupuesto(self):
        estructura_obj = self.env['presupuesto.estructura']

        for regularizacion_clearing in self:

            for llave in regularizacion_clearing.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(regularizacion_clearing.fiscalyear_id.id,
                                                               regularizacion_clearing.inciso_siif_id.inciso,
                                                               regularizacion_clearing.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                # Control: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (regularizacion_clearing.fiscalyear_id.code, regularizacion_clearing.inciso_siif_id.inciso,
                                  regularizacion_clearing.ue_siif_id.ue, llave.odg, llave.auxiliar, llave.fin, llave.programa,
                                  llave.proyecto, llave.mon, llave.tc)
                    raise exceptions.ValidationError(
                        u'No se encontró estructura con la llave presupuestal asociada a la regularización clearing: ' + desc_error)

                # Se obliga en el presupuesto (* -1), si es 3en1 se afecta, compromete y obliga
                res_af = estructura_obj.afectar(regularizacion_clearing.id, 9, -1 * llave.importe, estructura)
                res_comp = estructura_obj.comprometer(regularizacion_clearing.id, 9, -1 * llave.importe, estructura)
                res_obligar = estructura_obj.obligar(regularizacion_clearing.id, 9, -1 * llave.importe, estructura)
        return True


    def regularizacion_clearing_borrar_siif(self):
        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']

        tipo_doc_grp = '04'

        for regularizacion_clearing in self:

            context = dict(self._context or {})
            context.update({'fiscalyear_id': regularizacion_clearing.fiscalyear_id and regularizacion_clearing.fiscalyear_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(self._cr, self._uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_obl_sist_aux = self.pool.get('ir.sequence').get(self._cr, self._uid,'sec.siif.obligacion', context=context)
            nro_obl_sist_aux = nro_obl_sist_aux[4:]

            # SE OBLIGA CONTRA SIIF
            nro_modif_grp = regularizacion_clearing.siif_ult_modif

            enviar_datos_sice = False
            if regularizacion_clearing.siif_financiamiento.exceptuado_sice or regularizacion_clearing.siif_tipo_ejecucion.exceptuado_sice or regularizacion_clearing.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.env['presupuesto.objeto.gasto']
                for llave_pres in regularizacion_clearing.llpapg_ids:

                    objeto_gasto_ids = objeto_gasto_obj.search([('name', '=', llave_pres.odg),
                                                                         ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise exceptions.ValidationError(
                            _(u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                llave_pres.odg, llave_pres.auxiliar))

            xml_borrar_obligacion = generador_xml.gen_xml_borrado_3en1_rc(regularizacion_clearing=regularizacion_clearing, nro_carga=nro_carga,
                                                                          tipo_doc_grp=tipo_doc_grp, nro_modif_grp=nro_modif_grp,
                                                                          nro_obl_sist_aux=regularizacion_clearing.nro_obl_sist_aux)
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
                    dicc_modif['nro_afectacion'] = False
                    dicc_modif['nro_compromiso'] = False
                    dicc_modif['nro_obligacion'] = False
                    dicc_modif['siif_sec_obligacion'] = False
                    dicc_modif['siif_ult_modif'] = False
                    dicc_modif['nro_obl_sist_aux'] = False
                    dicc_modif['monto_comprometido'] = False

                    # Historico
                    anulacion_rc_log_obj = self.env['obligacion.rc.anulacion.siif.log']

                    # anulacion_siif_log_ids
                    vals_history = {
                        'regularizacion_id': regularizacion_clearing.id,
                        'fecha': fields.Date.today(),
                        'nro_afectacion_siif': regularizacion_clearing.nro_afectacion or 0,
                        'nro_compromiso': regularizacion_clearing.nro_compromiso or 0,
                        'nro_obligacion': regularizacion_clearing.nro_obligacion or 0,
                        'nro_obl_sist_aux': regularizacion_clearing.nro_obl_sist_aux or False,
                    }
                    id = anulacion_rc_log_obj.create(vals_history)

                    # Borrando valores (log de llave presupuestal)
                    if regularizacion_clearing.modif_regularizacion_log_ids:
                        regularizacion_clearing.modif_regularizacion_log_ids.unlink()

                    regularizacion_clearing.write(dicc_modif)

                else:
                    descr_error = movimiento.find('comentario').text
                    raise exceptions.ValidationError(
                        _(u'Error al intentar borrar obligación en SIIF'), (descr_error or u'Error no especificado por el SIIF'))
            return True


    @api.multi
    def btn_borrar_obligacion(self):
        self.regularizacion_clearing_cancel_presupuesto()

        company = self.env['res.users'].browse(self._uid).company_id
        integracion_siif = company.integracion_siif or False
        if integracion_siif:
            self.regularizacion_clearing_borrar_siif()
        self.state = 'confirm'
        return True


    def regularizacion_clearing_cancel_siif(self):

        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']

        tipo_doc_grp = '04'

        for regularizacion_clearing in self:

            context = dict(self._context or {})
            context.update({'fiscalyear_id': regularizacion_clearing.fiscalyear_id and regularizacion_clearing.fiscalyear_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(self._cr, self._uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]

            monto_desobligar = 0
            for llave in regularizacion_clearing.llpapg_ids:
                monto_desobligar += llave.importe
            monto_desobligar *= -1

            nro_modif_grp = regularizacion_clearing.siif_ult_modif + 1

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if regularizacion_clearing.siif_financiamiento.exceptuado_sice or regularizacion_clearing.siif_tipo_ejecucion.exceptuado_sice or regularizacion_clearing.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.env['presupuesto.objeto.gasto']

                for llave_pres in regularizacion_clearing.llpapg_ids:

                    objeto_gasto_ids = objeto_gasto_obj.search([('name', '=', llave_pres.odg),
                                                                ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise exceptions.ValidationError(
                            _(u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                llave_pres.odg, llave_pres.auxiliar))

            retenciones = []

            xml_cancel_obligacion = generador_xml.gen_xml_obligacion_3en1_rc(regularizacion_clearing=regularizacion_clearing,
                                                                             llaves_presupuestales=regularizacion_clearing.llpapg_ids,
                                                                             importe=monto_desobligar,
                                                                             nro_carga=nro_carga,
                                                                             tipo_doc_grp=tipo_doc_grp,
                                                                             nro_modif_grp=nro_modif_grp,
                                                                             tipo_modificacion='N',
                                                                             es_modif=True,
                                                                             motivo="Anulacion Obligacion 3en1 Regularizacion Clearing",
                                                                             retenciones=retenciones,
                                                                             enviar_datos_sice=enviar_datos_sice,
                                                                             nro_obl_sist_aux=regularizacion_clearing.nro_obl_sist_aux)
            resultado_siif = siif_proxy.put_solic(xml_cancel_obligacion)

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
                    raise osv.except_osv((u'Error al anular obligación 3e1 Regularizacion Clearing en SIIF'),
                                         (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_obligacion', None) and dicc_modif.get('resultado', None):
                    break

            # Historico
            anulacion_rc_log_obj = self.env['obligacion.rc.anulacion.siif.log']

            # anulacion_siif_log_ids
            vals_history = {
                'regularizacion_clearing_id': regularizacion_clearing.id,
                'fecha': fields.Date.today(),
                'nro_afectacion_siif': regularizacion_clearing.nro_afectacion or 0,
                'nro_compromiso': regularizacion_clearing.nro_compromiso or 0,
                'nro_obligacion': regularizacion_clearing.nro_obligacion or 0,
                'nro_obl_sist_aux': regularizacion_clearing.nro_obl_sist_aux or False,
            }
            id = anulacion_rc_log_obj.create(vals_history)

            modif_obligacion_log_obj = self.env['modif_obligacion_siif_rc_log']
            for llave in regularizacion_clearing.llpapg_ids:
                vals = {
                    'regularizacion_clearing_id': regularizacion_clearing.id,
                    'tipo': 'N',
                    'fecha': fields.Date.today(),
                    'programa': llave.programa,
                    'proyecto': llave.proyecto,
                    'moneda': llave.mon,
                    'tipo_credito': llave.tc,
                    'financiamiento': llave.fin,
                    'objeto_gasto': llave.odg,
                    'auxiliar': llave.auxiliar,
                    'importe': -llave.importe,
                    'siif_sec_obligacion': dicc_modif.get('siif_sec_obligacion', False),
                    'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                }
                modif_obligacion_log_obj.create(vals)

            dicc_modif.update({'nro_obl_sist_aux': False, 'nro_obligacion': False, 'state': 'cancel'})

            regularizacion_clearing.write(dicc_modif)
        return True


    @api.multi
    def btn_observ_tribunal(self):
        siif_proxy = self.env['siif.proxy']
        motivo_intervencion = self.env['motivo.intervencion.tc']
        observacion = self.env['grp.observacion.tc.regularizacion']

        for rec in self:
            # _logger.info('rec.state: %s', rec.state)
            # _logger.info('rec.fiscalyear_id: %s', rec.fiscalyear_id.name)
            # _logger.info('rec.nro_afectacion: %s', rec.nro_afectacion)
            # _logger.info('rec.nro_compromiso: %s', rec.nro_compromiso)
            # _logger.info('rec.nro_obligacion: %s', rec.nro_obligacion)
            # _logger.info('rec.inciso_siif_id: %s', rec.inciso_siif_id.inciso)
            # _logger.info('rec.ue_siif_id: %s', rec.ue_siif_id.ue)

            intervencion = siif_proxy.get_intervenciones(rec.fiscalyear_id.name, rec.inciso_siif_id.inciso, rec.ue_siif_id.ue, rec.nro_afectacion, rec.nro_compromiso, rec.nro_obligacion, 0)
            # intervencion = siif_proxy.get_intervenciones('2017', '12', '001', '297', '1', '1', '0')
            # _logger.info('intervencion: %s', intervencion)

            if intervencion.resultado == 1:

                # _logger.info('intervencion.motivoDeIntervencion: %s', intervencion.motivoDeIntervencion)
                # _logger.info('intervencion.descripcionMotivoIntervencion: %s',
                #              intervencion.descripcionMotivoIntervencion)
                # _logger.info('intervencion.observacionInterv: %s', intervencion.observacionInterv)

                motivo = motivo_intervencion.search([('codigo', '=', intervencion.motivoDeIntervencion)])
                if not motivo:
                    raise exceptions.ValidationError(_(
                        u'No se ha encontrado motivo de intervención en el catálogo de Motivo Intervenciones para el código %s retornado por SIIF') % (
                        intervencion.motivoDeIntervencion))
                else:
                    if motivo.impacta_documento:
                        # Crear registro en grilla de Observaciones
                        obs = {
                            'regularizacion_id': self.id,
                            'motivo_intervencion_id': motivo.id,
                            # 'observacion': intervencion.observacionInterv,
                        }
                        obs = observacion.create(obs)

                        # Marcar campo 'Intervenido con Observaciones'
                        self.write({'intervenido_con_observ': True})
                    else:
                        # Desmarcar campo 'Intervenido con Observaciones'
                        if rec.intervenido_con_observ:
                            self.write({'intervenido_con_observ': False})


    @api.multi
    def btn_cancel_obligacion(self):
        self.regularizacion_clearing_cancel_presupuesto()

        company = self.env['res.users'].browse(self._uid).company_id
        integracion_siif = company.integracion_siif or False
        if integracion_siif:
            self.regularizacion_clearing_cancel_siif()
        self.state = 'cancel'
        return True


class RegularizacionClearingLlavep(models.Model):
    _name = 'regularizacion.clearing.llavep'

    def _check_linea_llavep_programa(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.programa:
                if not llp.programa.isdigit():
                    return False
        return True

    def _check_linea_llavep_odg(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.odg:
                if not llp.odg.isdigit():
                    return False
        return True

    def _check_linea_llavep_auxiliar(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.auxiliar:
                if not llp.auxiliar.isdigit():
                    return False
        return True

    def _check_linea_llavep_disponible(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.disponible:
                if not llp.disponible.isdigit():
                    return False
        return True

    def _check_linea_llavep_proyecto(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.proyecto:
                if not llp.proyecto.isdigit():
                    return False
        return True

    def _check_linea_llavep_fin(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.fin:
                if not llp.fin.isdigit():
                    return False
        return True

    def _check_linea_llavep_mon(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.mon:
                if not llp.mon.isdigit():
                    return False
        return True

    def _check_linea_llavep_tc(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.tc:
                if not llp.tc.isdigit():
                    return False
        return True

    regularizacion_id = fields.Many2one('regularizacion.clearing', u'Regularización clearing', ondelete='cascade')
    #Campos de la estructura
    odg_id = fields.Many2one('grp.estruc_pres.odg', 'ODG', required=True)
    auxiliar_id = fields.Many2one('grp.estruc_pres.aux', 'Auxiliar', required=True)
    fin_id = fields.Many2one('grp.estruc_pres.ff', 'Fin', required=True)
    programa_id = fields.Many2one('grp.estruc_pres.programa', 'Programa', required=True)
    proyecto_id = fields.Many2one('grp.estruc_pres.proyecto', 'Proyecto', required=True)
    mon_id = fields.Many2one('grp.estruc_pres.moneda', 'Mon', required=True)
    tc_id = fields.Many2one('grp.estruc_pres.tc', 'TC', required=True)
    # Campos related
    odg = fields.Char(related='odg_id.odg', string='ODG related', store=True, readonly=True)
    auxiliar = fields.Char(related='auxiliar_id.aux', string='Auxiliar related', store=True, readonly=True)
    fin = fields.Char(related='fin_id.ff', string='Fin related', store=True, readonly=True)
    programa = fields.Char(related='programa_id.programa', string='Programa related', store=True, readonly=True)
    proyecto = fields.Char(related='proyecto_id.proyecto', string='Proyecto related', store=True, readonly=True)
    mon = fields.Char(related='mon_id.moneda', string='Mon related', store=True, readonly=True)
    tc = fields.Char(related='tc_id.tc', string='TC related', store=True, readonly=True)
    # montos
    disponible = fields.Char('Disponible', size=3)
    importe = fields.Integer('Importe')

    # On_change llaves presupuestal
    def onchange_objeto_del_gasto(self, cr, uid, ids, odg_id, context=None):
        auxiliar_id = False
        if odg_id:
            auxiliar_ids = self.pool.get('grp.estruc_pres.aux').search(cr, uid, [('odg_id', '=', odg_id)])
            if len(auxiliar_ids) == 1:
                auxiliar_id = auxiliar_ids[0]
        return {'value': {
            'auxiliar_id': auxiliar_id,
            'fin_id': False,
            'programa_id': False,
            'proyecto_id': False,
            'mon_id': False,
            'tc_id': False,
        }}

    def onchange_auxiliar(self, cr, uid, ids, auxiliar_id, context=None):
        fin_id = False
        if auxiliar_id:
            fin_ids = self.pool.get('grp.estruc_pres.ff').search(cr, uid, [('aux_id', '=', auxiliar_id)])
            if len(fin_ids) == 1:
                fin_id = fin_ids[0]
        return {'value': {
            'fin_id': fin_id,
            'programa_id': False,
            'proyecto_id': False,
            'mon_id': False,
            'tc_id': False
        }}

    def onchange_fuente_de_financiamiento(self, cr, uid, ids, fin_id, context=None):
        programa_id = False
        if fin_id:
            programa_ids = self.pool.get('grp.estruc_pres.programa').search(cr, uid, [('ff_id', '=', fin_id)])
            if len(programa_ids) == 1:
                programa_id = programa_ids[0]
        return {'value': {
            'programa_id': programa_id,
            'proyecto_id': False,
            'mon_id': False,
            'tc_id': False,
        }}

    def onchange_programa(self, cr, uid, ids, programa_id, context=None):
        proyecto_id = False
        if programa_id:
            proyecto_ids = self.pool.get('grp.estruc_pres.proyecto').search(cr, uid,[('programa_id', '=', programa_id)])
            if len(proyecto_ids) == 1:
                proyecto_id = proyecto_ids[0]
        return {'value': {
            'proyecto_id': proyecto_id,
            'mon_id': False,
            'tc_id': False,
        }}

    def onchange_proyecto(self, cr, uid, ids, proyecto_id, context=None):
        mon_id = False
        if proyecto_id:
            mon_ids = self.pool.get('grp.estruc_pres.moneda').search(cr, uid, [('proyecto_id', '=', proyecto_id)])
            if len(mon_ids) == 1:
                mon_id = mon_ids[0]
        return {'value': {
            'mon_id': mon_id,
            'tc_id': False,
        }}

    def onchange_moneda(self, cr, uid, ids, mon_id, context=None):
        tc_id = False
        if mon_id:
            tc_ids = self.pool.get('grp.estruc_pres.tc').search(cr, uid, [('moneda_id', '=', mon_id)])
            if len(tc_ids) == 1:
                tc_id = tc_ids[0]
        return {'value': {
            'tc_id': tc_id
        }}

    def _check_llavep_unica(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            lineas_duplicadas = self.search(cr, uid, [('regularizacion_id', '=', line.regularizacion_id.id),
                                                      ('fin_id', '=', line.fin_id.id),
                                                      ('mon_id', '=', line.mon_id.id),
                                                      ('odg_id', '=', line.odg_id.id),
                                                      ('programa_id', '=', line.programa_id.id),
                                                      ('proyecto_id', '=', line.proyecto_id.id),
                                                      ('tc_id', '=', line.tc_id.id),
                                                      ('id', 'not in', ids)
                                                      ], context=context)
            if lineas_duplicadas:
                raise osv.except_osv(
                    _(u'Línea duplicada'),
                    _(u'No se pueden ingresar 2 líneas iguales para el mismo registro.'))
        return True



    _constraints = [
        (_check_llavep_unica, u'Línea duplicada',
         ['auxiliar_id', 'regularizacion_id', 'fin_id', 'mon_id', 'odg_id',
          'programa_id', 'proyecto_id', 'tc_id']),
        (_check_linea_llavep_programa, u'Campo no es numérico', ['programa']),
        (_check_linea_llavep_odg, u'Campo no es numérico', ['odg']),
        (_check_linea_llavep_auxiliar, u'Campo no es numérico', ['auxiliar']),
        (_check_linea_llavep_disponible, u'Campo no es numérico', ['disponible']),
        # incidencias
        (_check_linea_llavep_proyecto, u'Campo no es numérico', ['proyecto']),
        (_check_linea_llavep_fin, u'Campo no es numérico', ['fin']),
        (_check_linea_llavep_mon, u'Campo no es numérico', ['mon']),
        (_check_linea_llavep_tc, u'Campo no es numérico', ['tc']),
    ]


class obligacion_rc_anulaciones_siif_log(models.Model):
    _name = 'obligacion.rc.anulacion.siif.log'
    _description = "Log de anulaciones de obligaciones de regularizacion clearing"

    regularizacion_id = fields.Many2one('regularizacion.clearing', u'Regularización clearing', required=True, ondelete='cascade')
    fecha = fields.Date('Fecha', required=True)
    nro_afectacion_siif = fields.Integer(u'Nro Afectación SIIF')
    nro_compromiso = fields.Char(u'Nro Compromiso')
    nro_obligacion = fields.Char(u'Nro Obligación')
    nro_obl_sist_aux = fields.Char(u'Nro Obligación Sistema Aux')


class grp_observacion_tc_regularizacion(models.Model):
    _name = 'grp.observacion.tc.regularizacion'

    regularizacion_id = fields.Many2one('regularizacion.clearing', string=u'Regularización')
    motivo_intervencion_id = fields.Many2one('motivo.intervencion.tc', string='Motivo')
    descripcion = fields.Char(related='motivo_intervencion_id.descripcion')
    observacion = fields.Char(string=u'Observación', size=100)

    _sql_constraints = [
        ('observacion_reg_unique', 'unique(regularizacion_id,motivo_intervencion_id,observacion)', u'Ya existe una intervención con la misma observación')
    ]
